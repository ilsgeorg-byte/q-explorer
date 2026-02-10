from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Favorite
from api_clients import (
    search_itunes, lookup_itunes, get_true_artist_image, 
    get_lastfm_artist_data, get_lastfm_album_stats, get_similar_artists,
    get_tag_info, get_tag_artists, search_deezer_artists
)
from utils import generate_spotify_link, generate_youtube_link, sort_albums
from urllib.parse import unquote 
from concurrent.futures import ThreadPoolExecutor
import os

app = Flask(__name__)

# --- CONFIGURATION ---
# Vercel: Use environment variables for production. 
# SECRET_KEY must be stable across restarts to avoid session loss.
secret_key = os.environ.get('SECRET_KEY')
if not secret_key:
    print("WARNING: SECRET_KEY environment variable is not set! Using a temporary key.")
    # Use a fallback that is stable for the duration of the process
    secret_key = 'dev-key-please-set-in-vercel'
app.config['SECRET_KEY'] = secret_key

# Vercel: Use DATABASE_URL if provided, else fall back to a writable path in /tmp for SQLite
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    print("WARNING: DATABASE_URL is not set. Falling back to temporary SQLite.")
    # /tmp is the only writable directory on Vercel
    database_url = 'sqlite:///' + os.path.join('/tmp', 'users.db')
else:
    # Fix for SQLAlchemy 1.4+ (Postgres URI must start with postgresql://)
    database_url = database_url.replace('postgres://', 'postgresql://')

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Session Security (Crucial for HTTPS on Vercel)
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Создаем таблицы при запуске (если их нет)
# На Vercel с SQLite это может вызвать ошибку, так как ФС только для чтения.
# Если используется внешняя БД, это сработает.
try:
    with app.app_context():
        db.create_all()
except Exception as e:
    print(f"Database initialization error: {e}")

@app.route('/')
def index():
    query = request.args.get('q')
    if not query:
        return render_template('index.html', view='home')
    
    results = {'artists': [], 'albums': [], 'songs': []}
    ql = query.lower()

    # 1. Artists (Главная: берем 8 лучших, фильтруем дубликаты)
    seen_ids = set()
    seen_names = set()
    
    # Сначала собираем кандидатов (быстро)
    candidates = []
    # Запрашиваем с запасом (25)
    for art in search_itunes(query, 'musicArtist', 25):
        aid = art.get('artistId')
        name = art.get('artistName', '')
        
        # Пропускаем без ID или уже виденных
        if not aid or aid in seen_ids: continue
        # Пропускаем, если имя совсем не похоже (мусор в поиске)
        if ql not in (name or "").lower(): continue
        
        # Фильтруем дубликаты по имени (iTunes иногда возвращает несколько "Queen" с разными ID)
        if name.lower() in seen_names: continue
        seen_names.add(name.lower())
        
        candidates.append(art)
        seen_ids.add(aid)
        
        if len(candidates) >= 8: break
    
    # Теперь обогащаем данные ПАРАЛЛЕЛЬНО (Deezer + Last.fm)
    def enrich_artist(art):
        name = art.get('artistName', '')
        aid = art.get('artistId')
        
        # 1. Картинка и Статистика (Deezer)
        dz = search_deezer_artists(name, 1)
        deezer_stats = None
        if dz:
            art['image'] = dz[0]['image']
            deezer_stats = dz[0].get('stats')
        else:
            art['image'] = get_true_artist_image(aid)
            
        # 2. Статистика (Last.fm)
        lf = get_lastfm_artist_data(name)
        # Если Last.fm вернул пустоту, берем Deezer
        art['stats'] = lf.get('stats') if lf and lf.get('stats') else deezer_stats
        return art

    with ThreadPoolExecutor() as executor:
        results['artists'] = list(executor.map(enrich_artist, candidates))
    
    # 2. Albums
    for alb in search_itunes(query, 'album', 15):
        if ql in (alb.get('collectionName', '') or '').lower():
            alb['artworkUrl100'] = alb.get('artworkUrl100', '').replace('100x100bb', '300x300bb')
            date = alb.get('releaseDate', '')
            alb['year'] = date[:4] if date else ''
            results['albums'].append(alb)
    results['albums'] = results['albums'][:8]
    
    # 3. Songs
    for song in search_itunes(query, 'song', 15):
        if ql in (song.get('trackName', '') or '').lower():
            q = f"{song.get('artistName', '')} {song.get('trackName', '')}"
            song['spotify_link'] = generate_spotify_link(q)
            song['youtube_link'] = generate_youtube_link(q)
            results['songs'].append(song)
    results['songs'] = results['songs'][:10]
        
    return render_template('index.html', view='results', data=results, query=query)

@app.route('/see-all/<type>') 
def see_all(type):
    query = request.args.get('q')
    if not query: return "No query provided", 400
        
    results = []
    ql = query.lower()
    
    entity_map = {'artists': 'musicArtist', 'albums': 'album', 'songs': 'song'}
    entity = entity_map.get(type, 'album')
    
    # Большой лимит для списка "Все"
    data = search_itunes(query, entity, 60)
    
    seen_ids = set()
    seen_names = set()
    
    for item in data:
        if type == 'artists':
            aid = item.get('artistId')
            name = item.get('artistName', '')
            
            if not aid or aid in seen_ids: continue
            if ql not in (name or "").lower(): continue

            if name.lower() in seen_names: continue
            seen_names.add(name.lower())

            # ВАЖНО: Тут image = None. Картинки подгрузятся через JS (Lazy Loading)
            item['image'] = None 
            
            # Статистику для списка "Все" не грузим (долго), только имя
            item['stats'] = None
            
            results.append(item)
            seen_ids.add(aid)
            
        elif type == 'albums':
            if item.get('collectionName') and ql in item.get('collectionName', '').lower():
                item['artworkUrl100'] = item.get('artworkUrl100', '').replace('100x100bb', '300x300bb')
                date = item.get('releaseDate', '')
                item['year'] = date[:4] if date else ''
                results.append(item)
                
        elif type == 'songs':
            if item.get('trackName') and ql in item.get('trackName', '').lower():
                item['spotify_link'] = generate_spotify_link(f"{item.get('artistName')} {item.get('trackName')}")
                results.append(item)

    return render_template('index.html', view='see_all', results=results, type=type, query=query)

@app.route('/artist/<artist_id>')
def artist_page(artist_id):
    # Сначала получаем базовую инфу (это быстро, 1 запрос)
    data = lookup_itunes(artist_id)
    if not data: return "Artist not found"
    
    artist = data[0]
    artist_name = artist.get('artistName', '')
    
    # ПАРАЛЛЕЛЬНАЯ ЗАГРУЗКА (ThreadPoolExecutor)
    # Запускаем 4 тяжелых запроса одновременно
    from concurrent.futures import ThreadPoolExecutor
    
    with ThreadPoolExecutor() as executor:
        # 1. Last.fm Info
        future_lf = executor.submit(get_lastfm_artist_data, artist_name)
        # 2. Similar Artists
        future_sim = executor.submit(get_similar_artists, artist_name)
        # 3. Top Songs (Raw)
        future_songs = executor.submit(search_itunes, artist_name, 'song', 50)
        # 4. Albums (Raw)
        future_albums = executor.submit(lookup_itunes, artist_id, 'album', 200)
        # 5. Deezer Image (Красивое фото артиста)
        future_deezer = executor.submit(search_deezer_artists, artist_name, 1)
        
        # Собираем результаты
        lf_data = future_lf.result()
        similar = future_sim.result()
        top_songs_raw = future_songs.result()
        raw_albums_data = future_albums.result()
        deezer_data = future_deezer.result()

    # --- ОБРАБОТКА ПОЛУЧЕННЫХ ДАННЫХ ---
    
    # 1. Применяем Last.fm
    if lf_data:
        artist['stats'] = lf_data.get('stats')
        artist['bio'] = lf_data.get('bio')
        artist['tags'] = lf_data.get('tags')
    else:
        artist['stats'] = None
        artist['bio'] = None
        artist['tags'] = []
        
    # Если Last.fm не дал статистику, пробуем взять из Deezer
    if not artist['stats'] and deezer_data:
        artist['stats'] = deezer_data[0].get('stats')
    
    # 2. Обрабатываем Топ Песни
    top_songs = []
    seen_titles = set()
    target_id = int(artist_id)
    target_name_lower = artist_name.lower()
    
    def add_song(s):
        clean_title = s.get('trackName', '').lower().split('(')[0].split('-')[0].strip()
        if clean_title in seen_titles: return
        
        s['spotify_link'] = generate_spotify_link(f"{s.get('artistName')} {s.get('trackName')}")
        s['youtube_link'] = generate_youtube_link(f"{s.get('artistName')} {s.get('trackName')}")
        if 'artworkUrl100' in s:
            s['artworkUrl100'] = s['artworkUrl100'].replace('100x100bb', '300x300bb')
            
        top_songs.append(s)
        seen_titles.add(clean_title)

    # Проход 1: СТРОГИЙ
    for s in top_songs_raw:
        if s.get('artistId') == target_id:
            add_song(s)
            if len(top_songs) >= 5: break
            
    # Проход 2: МЯГКИЙ
    if len(top_songs) < 5:
        for s in top_songs_raw:
            if len(top_songs) >= 5: break
            if s.get('artistId') == target_id: continue
            
            song_artist = s.get('artistName', '').lower()
            if target_name_lower in song_artist:
                add_song(s)

    # 3. Обрабатываем Альбомы
    # Фильтруем только альбомы (wrapperType='collection', collectionType='Album')
    # Убираем проверку artistId, так как lookup по ID уже вернул релевантные альбомы
    if raw_albums_data:
        raw_albums = [x for x in raw_albums_data if x.get('collectionType') == 'Album']
    else:
        raw_albums = []

    discography = sort_albums(raw_albums)
    
    # Выбираем лучшее изображение для шапки
    artist_image = None
    if discography['albums']:
        artist_image = discography['albums'][0].get('artworkUrl100')
    elif discography['singles']:
         artist_image = discography['singles'][0].get('artworkUrl100')
    
    if deezer_data:
        artist_image = deezer_data[0]['image']
    else:
        if discography['albums']:
            artist_image = discography['albums'][0].get('artworkUrl100')
        elif discography['singles']:
             artist_image = discography['singles'][0].get('artworkUrl100')
    
    return render_template('index.html', view='artist_detail', artist=artist, discography=discography, artist_image=artist_image, similar=similar, top_songs=top_songs)

@app.route('/album/<collection_id>')
def album_page(collection_id):
    # Увеличиваем лимит до 200, так как бокс-сеты могут содержать много треков
    data = lookup_itunes(collection_id, 'song', 200)
    if not data: return "Album not found"
    
    album_info = data[0]
    album_info['artworkUrl100'] = album_info.get('artworkUrl100', '').replace('100x100bb', '600x600bb')
    
    date = album_info.get('releaseDate', '')
    album_info['year'] = date[:4] if date else ''
    
    album_stats = get_lastfm_album_stats(album_info.get('artistName'), album_info.get('collectionName'))
    spotify_link = generate_spotify_link(f"{album_info.get('artistName')} {album_info.get('collectionName')}")
    youtube_link = generate_youtube_link(f"{album_info.get('artistName')} {album_info.get('collectionName')}")
    
    songs = []
    for item in data[1:]:
        if item.get('kind') == 'song':
            item['spotify_link'] = generate_spotify_link(f"{item.get('artistName')} {item.get('trackName')}")
            item['youtube_link'] = generate_youtube_link(f"{item.get('artistName')} {item.get('trackName')}")
            songs.append(item)
            
    # Сортируем по номеру диска и трека (важно для бокс-сетов)
    songs.sort(key=lambda x: (x.get('discNumber', 1), x.get('trackNumber', 1)))
            
    return render_template('index.html', view='album_detail', album=album_info, songs=songs, spotify_link=spotify_link, youtube_link=youtube_link, album_stats=album_stats)

# API для JS (Lazy Loading картинок)
@app.route('/api/get-artist-image/<artist_id>')
def api_get_artist_image(artist_id):
    # 1. Сначала пробуем Deezer (нужно имя артиста)
    try:
        data = lookup_itunes(artist_id)
        if data:
            name = data[0].get('artistName')
            if name:
                dz = search_deezer_artists(name, 1)
                if dz: return jsonify({'image': dz[0]['image']})
    except: pass

    # 2. Если не вышло — берем обложку из iTunes
    image_url = get_true_artist_image(artist_id)
    return jsonify({'image': image_url})

@app.route('/tag/<tag_name>')
def tag_page(tag_name):
    # Декодируем: "Glam%20rock" -> "Glam rock"
    decoded_tag = unquote(tag_name)
    
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort', 'popularity')
    
    # Используем decoded_tag для запросов
    description = get_tag_info(decoded_tag)
    artists = get_tag_artists(decoded_tag, page, 30)
    
    if sort_by == 'alpha':
        artists.sort(key=lambda x: x['artistName'].lower())
    else:
        artists.sort(key=lambda x: x['listeners'], reverse=True)
        
    return render_template('index.html', 
                           view='tag_detail', 
                           tag_name=decoded_tag,  # <--- Передаем "чистое" имя
                           description=description, 
                           artists=artists, 
                           page=page, 
                           sort_by=sort_by)

# ... (предыдущий код)

@app.route('/api/get-artist-image-by-name')
def api_get_artist_image_by_name():
    name = request.args.get('name')
    if not name: return jsonify({'image': None})
    
    # 1. Сначала пробуем Deezer (быстрее и красивее)
    try:
        dz = search_deezer_artists(name, 1)
        if dz: return jsonify({'image': dz[0]['image']})
    except: pass
    
    # 2. Если нет, ищем в iTunes (через Artist ID -> Album)
    try:
        results = search_itunes(name, 'musicArtist', 1)
        if results:
            artist_id = results[0].get('artistId')
            img = get_true_artist_image(artist_id)
            if img: return jsonify({'image': img})
    except:
        pass

    # 3. Fallback: Если фото артиста нет, берем обложку первого попавшегося альбома
    try:
        albums = search_itunes(name, 'album', 60)
        for alb in albums:
            if alb.get('artworkUrl100'):
                # Пропускаем Donda и Vultures (часто темные/пустые обложки)
                cname = alb.get('collectionName', '').lower()
                if 'donda' in cname or 'vultures' in cname: continue
                return jsonify({'image': alb['artworkUrl100'].replace('100x100bb', '400x400bb')})
    except:
        pass
        
    return jsonify({'image': None})

# НОВЫЙ МАРШРУТ: Умный редирект по имени артиста
@app.route('/redirect-artist')
def redirect_artist():
    name = request.args.get('name')
    if not name: return redirect(url_for('index'))

    # Ищем артиста в iTunes (берем первого попавшегося)
    results = search_itunes(name, 'musicArtist', 1)
    if results:
        # Если нашли — сразу идем на его страницу
        return redirect(url_for('artist_page', artist_id=results[0]['artistId']))

    # Если не нашли — отправляем в обычный поиск
    return redirect(url_for('index', q=name))

# --- AUTH ROUTES ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
            
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        return redirect(url_for('index'))
        
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password')
            
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    # Загружаем избранное
    fav_artists = Favorite.query.filter_by(user_id=current_user.id, type='artist').all()
    fav_albums = Favorite.query.filter_by(user_id=current_user.id, type='album').all()
    fav_tracks = Favorite.query.filter_by(user_id=current_user.id, type='song').all()
    
    return render_template('index.html', view='profile', user=current_user, 
                           fav_artists=fav_artists, 
                           fav_albums=fav_albums, 
                           fav_tracks=fav_tracks)

@app.route('/favorites')
@login_required
def favorites():
    # Загружаем избранное
    fav_artists = Favorite.query.filter_by(user_id=current_user.id, type='artist').all()
    fav_albums = Favorite.query.filter_by(user_id=current_user.id, type='album').all()
    fav_tracks = Favorite.query.filter_by(user_id=current_user.id, type='song').all()
    
    return render_template('index.html', view='favorites',
                           fav_artists=fav_artists, 
                           fav_albums=fav_albums, 
                           fav_tracks=fav_tracks)

@app.route('/api/favorite', methods=['POST'])
@login_required
def toggle_favorite():
    data = request.json
    item_type = data.get('type')
    item_id = data.get('id')
    
    if not item_type or not item_id:
        return jsonify({'error': 'Missing data'}), 400
        
    # Проверяем, есть ли уже в избранном
    existing = Favorite.query.filter_by(user_id=current_user.id, type=item_type, item_id=item_id).first()
    
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'status': 'removed'})
    else:
        new_fav = Favorite(
            user_id=current_user.id,
            type=item_type,
            item_id=item_id,
            name=data.get('title'),
            image_url=data.get('img'),
            sub_title=data.get('sub'),
            link=data.get('link')
        )
        db.session.add(new_fav)
        db.session.commit()
        return jsonify({'status': 'added'})

@app.route('/api/check_favorites')
def check_favorites():
    if not current_user.is_authenticated:
        return jsonify([])
    
    favs = Favorite.query.filter_by(user_id=current_user.id).all()
    return jsonify([f.item_id for f in favs])

if __name__ == '__main__':
    app.run(debug=True)
