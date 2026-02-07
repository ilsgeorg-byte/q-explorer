from flask import Flask, render_template, request, jsonify
from api_clients import (
    search_itunes, 
    lookup_itunes, 
    get_true_artist_image, 
    get_lastfm_artist_data, # <--- Обновленная функция
    get_lastfm_album_stats, 
    get_similar_artists
)
from utils import generate_spotify_link, sort_albums

app = Flask(__name__)

@app.route('/')
def index():
    query = request.args.get('q')
    if not query:
        return render_template('index.html', view='home')
    
    results = {'artists': [], 'albums': [], 'songs': []}
    ql = query.lower()

    # 1. Artists (Главная: берем 4 лучших, фильтруем дубликаты)
    seen_ids = set()
    # Запрашиваем с запасом (15)
    for art in search_itunes(query, 'musicArtist', 15):
        aid = art.get('artistId')
        name = art.get('artistName', '')
        
        # Пропускаем без ID или уже виденных
        if not aid or aid in seen_ids: continue
        # Пропускаем, если имя совсем не похоже (мусор в поиске)
        if ql not in (name or "").lower(): continue

        # Для главной страницы (всего 4 шт) грузим картинку сразу (синхронно)
        # Это замедлит поиск на ~1 сек, но зато красиво.
        art['image'] = get_true_artist_image(aid)
        
        # Берем данные с Last.fm (stats + tags)
        lf_data = get_lastfm_artist_data(name)
        art['stats'] = lf_data.get('stats') if lf_data else None
        
        results['artists'].append(art)
        seen_ids.add(aid)
        
        if len(results['artists']) >= 4: break
    
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
    
    for item in data:
        if type == 'artists':
            aid = item.get('artistId')
            name = item.get('artistName', '')
            
            if not aid or aid in seen_ids: continue
            if ql not in (name or "").lower(): continue

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
    data = lookup_itunes(artist_id)
    if not data: return "Artist not found"
    
    artist = data[0]
    
    # 1. Last.fm Data
    lf_data = get_lastfm_artist_data(artist.get('artistName', ''))
    if lf_data:
        artist['stats'] = lf_data.get('stats')
        artist['bio'] = lf_data.get('bio')
        artist['tags'] = lf_data.get('tags')
    else:
        artist['stats'] = None
        artist['bio'] = None
        artist['tags'] = []
    
    similar = get_similar_artists(artist.get('artistName', ''))
    
    # 2. Топ Песни (Top Songs) - УЛУЧШЕННАЯ ЛОГИКА
    # Запрашиваем 50 треков, чтобы точно найти нужные среди мусора
    top_songs_raw = search_itunes(artist.get('artistName', ''), 'song', 50)
    top_songs = []
    
    # Множество для защиты от дубликатов (чтобы не было 3 версии одной песни)
    seen_titles = set()
    target_id = int(artist_id)
    # Имя артиста в нижнем регистре для мягкого поиска
    target_name_lower = artist.get('artistName', '').lower()
    
    def add_song(s):
        # "Clean" название для проверки дублей: "Song (Remaster)" -> "song"
        clean_title = s.get('trackName', '').lower().split('(')[0].split('-')[0].strip()
        if clean_title in seen_titles: return
        
        s['spotify_link'] = generate_spotify_link(f"{s.get('artistName')} {s.get('trackName')}")
        if 'artworkUrl100' in s:
            s['artworkUrl100'] = s['artworkUrl100'].replace('100x100bb', '300x300bb')
            
        top_songs.append(s)
        seen_titles.add(clean_title)

    # Проход 1: СТРОГИЙ (Точное совпадение ID)
    for s in top_songs_raw:
        if s.get('artistId') == target_id:
            add_song(s)
            if len(top_songs) >= 5: break
            
    # Проход 2: МЯГКИЙ (Если песен мало, ищем по Имени)
    # Это спасет коллаборации (Queen & Bowie) и кривые тэги iTunes
    if len(top_songs) < 5:
        for s in top_songs_raw:
            if len(top_songs) >= 5: break
            # Пропускаем, если ID совпадает (уже добавили в 1 проходе)
            if s.get('artistId') == target_id: continue
            
            song_artist = s.get('artistName', '').lower()
            # Если имя нашего артиста есть внутри исполнителя трека
            if target_name_lower in song_artist:
                add_song(s)

    # 3. Дискография (без изменений)
    raw_albums = [x for x in lookup_itunes(artist_id, 'album', 200) if x.get('collectionType') == 'Album' and x.get('artistId') == int(artist_id)]
    discography = sort_albums(raw_albums)
    
    artist_image = discography['albums'][0]['artworkUrl100'] if discography['albums'] else None
    if not artist_image and discography['singles']:
         artist_image = discography['singles'][0]['artworkUrl100']
    
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

if __name__ == '__main__':
    app.run(debug=True)
