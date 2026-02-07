from flask import Flask, render_template, request, jsonify
from api_clients import (
    search_itunes, lookup_itunes, get_true_artist_image, 
    get_lastfm_artist_data, get_lastfm_album_stats, get_similar_artists,
    get_tag_info, get_tag_artists, search_deezer_artists
)
from utils import generate_spotify_link, sort_albums
from urllib.parse import unquote 

app = Flask(__name__)

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

        # Для главной страницы (всего 4 шт) грузим картинку сразу (синхронно)
        # Это замедлит поиск на ~1 сек, но зато красиво.
        art['image'] = get_true_artist_image(aid)
        
        # 1. Пробуем найти красивое фото через Deezer
        deezer_res = search_deezer_artists(name, 1)
        if deezer_res:
            art['image'] = deezer_res[0]['image']
        else:
            # 2. Если не вышло, берем обложку из iTunes
            art['image'] = get_true_artist_image(aid)
        
        # Берем данные с Last.fm (stats + tags)
        lf_data = get_lastfm_artist_data(name)
        art['stats'] = lf_data.get('stats') if lf_data else None
        
        results['artists'].append(art)
        seen_ids.add(aid)
        
        if len(results['artists']) >= 8: break
    
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
    
    # 2. Обрабатываем Топ Песни
    top_songs = []
    seen_titles = set()
    target_id = int(artist_id)
    target_name_lower = artist_name.lower()
    
    def add_song(s):
        clean_title = s.get('trackName', '').lower().split('(')[0].split('-')[0].strip()
        if clean_title in seen_titles: return
        
        s['spotify_link'] = generate_spotify_link(f"{s.get('artistName')} {s.get('trackName')}")
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
    data = lookup_itunes(collection_id, 'song')
    if not data: return "Album not found"
    
    album_info = data[0]
    album_info['artworkUrl100'] = album_info.get('artworkUrl100', '').replace('100x100bb', '600x600bb')
    
    date = album_info.get('releaseDate', '')
    album_info['year'] = date[:4] if date else ''
    
    album_stats = get_lastfm_album_stats(album_info.get('artistName'), album_info.get('collectionName'))
    spotify_link = generate_spotify_link(f"{album_info.get('artistName')} {album_info.get('collectionName')}")
    
    songs = []
    for item in data[1:]:
        if item.get('kind') == 'song':
            item['spotify_link'] = generate_spotify_link(f"{item.get('artistName')} {item.get('trackName')}")
            songs.append(item)
            
    return render_template('index.html', view='album_detail', album=album_info, songs=songs, spotify_link=spotify_link, album_stats=album_stats)

# API для JS (Lazy Loading картинок)
@app.route('/api/get-artist-image/<artist_id>')
def api_get_artist_image(artist_id):
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
    
    # 1. Ищем артиста в iTunes по имени
    # 1. Сначала пробуем Deezer (быстрее и красивее)
    try:
        dz = search_deezer_artists(name, 1)
        if dz: return jsonify({'image': dz[0]['image']})
    except: pass
    
    # 2. Если нет, ищем в iTunes
    try:
        results = search_itunes(name, 'musicArtist', 1)
        if results:
            artist_id = results[0].get('artistId')
            # 2. Получаем его качественное фото
            img = get_true_artist_image(artist_id)
            return jsonify({'image': img})
    except:
        pass
        
    return jsonify({'image': None})

if __name__ == '__main__':
    app.run(debug=True)
