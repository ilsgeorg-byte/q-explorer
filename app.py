from flask import Flask, render_template, request
import requests
import urllib.parse

app = Flask(__name__)

def generate_spotify_link(query):
    return f"https://open.spotify.com/search/{urllib.parse.quote(query)}"

def get_image_for_artist(artist_name):
    # Хак: ищем 1 альбом артиста, чтобы взять его картинку
    try:
        r = requests.get(f"https://itunes.apple.com/search?term={artist_name}&entity=album&limit=1").json()
        if r['resultCount'] > 0:
            return r['results'][0]['artworkUrl100']
    except:
        pass
    return None

def sort_albums(albums_list):
    """Сортирует альбомы по категориям"""
    categorized = {
        'albums': [],
        'singles': [],
        'live': [],
        'compilations': []
    }
    
    seen_names = set() # Чтобы убрать дубликаты
    
    for alb in albums_list:
        name = alb['collectionName']
        lower_name = name.lower()
        
        # Пропускаем дубликаты (иногда iTunes дает одно и то же)
        if name in seen_names: continue
        seen_names.add(name)
        
        # Улучшаем картинку
        alb['artworkUrl100'] = alb.get('artworkUrl100', '').replace('100x100bb', '400x400bb')
        
        track_count = alb.get('trackCount', 0)

        # ЛОГИКА СОРТИРОВКИ
        if 'live' in lower_name or 'concert' in lower_name or 'tour' in lower_name:
            categorized['live'].append(alb)
        elif 'greatest hits' in lower_name or 'best of' in lower_name or 'collection' in lower_name or 'anthology' in lower_name:
            categorized['compilations'].append(alb)
        elif track_count < 5 or 'single' in lower_name or 'ep' in lower_name:
            # Считаем синглами всё, где мало треков
            categorized['singles'].append(alb)
        else:
            # Остальное - студийные альбомы
            categorized['albums'].append(alb)
            
    # Сортируем внутри категорий по дате (свежие сверху)
    for key in categorized:
        categorized[key].sort(key=lambda x: x.get('releaseDate', ''), reverse=True)
        
    return categorized

@app.route('/')
def index():
    query = request.args.get('q')
    if not query:
        return render_template('index.html', view='home')

    results = {'artists': [], 'albums': [], 'songs': []}
    
    try:
        # 1. ARTISTS (Ищем больше, чтобы потом отфильтровать мусор)
        r_art = requests.get(f"https://itunes.apple.com/search?term={query}&entity=musicArtist&limit=10").json()
        raw_artists = r_art.get('results', [])
        
        # Фильтруем: оставляем только тех, чье имя похоже на запрос
        # (чтобы убрать Smashing Pumpkins по запросу Machine Head)
        clean_artists = []
        for art in raw_artists:
            if query.lower() in art['artistName'].lower():
                # Пробуем найти картинку
                art['image'] = get_image_for_artist(art['artistName'])
                clean_artists.append(art)
        
        results['artists'] = clean_artists[:4] # Берем топ-4 самых релевантных

        # 2. ALBUMS
        r_alb = requests.get(f"https://itunes.apple.com/search?term={query}&entity=album&limit=25").json()
        raw_albums = r_alb.get('results', [])
        
        # Фильтр: показываем только альбомы, где Исполнитель совпадает с запросом
        clean_albums = []
        for alb in raw_albums:
            if query.lower() in alb['artistName'].lower():
                alb['artworkUrl100'] = alb.get('artworkUrl100', '').replace('100x100bb', '300x300bb')
                clean_albums.append(alb)
                
        results['albums'] = clean_albums[:8] # Топ-8 альбомов

        # 3. SONGS
        r_song = requests.get(f"https://itunes.apple.com/search?term={query}&entity=song&limit=15").json()
        raw_songs = r_song.get('results', [])
        
        clean_songs = []
        for song in raw_songs:
            # Тоже фильтруем, чтобы не было каверов от левых групп
            if query.lower() in song['artistName'].lower() or query.lower() in song['trackName'].lower():
                q = f"{song['artistName']} {song['trackName']}"
                song['spotify_link'] = generate_spotify_link(q)
                clean_songs.append(song)
                
        results['songs'] = clean_songs[:10]

    except Exception as e:
        print(e)

    return render_template('index.html', view='results', data=results, query=query)

@app.route('/artist/<int:artist_id>')
def artist_page(artist_id):
    try:
        # Инфо об артисте
        lookup = requests.get(f"https://itunes.apple.com/lookup?id={artist_id}").json()
        artist = lookup['results'][0]
        
        # Загружаем ВСЕ альбомы (limit=200)
        albums_req = requests.get(f"https://itunes.apple.com/lookup?id={artist_id}&entity=album&limit=200").json()
        
        # Фильтруем (убираем самого артиста из списка и чужие сборники)
        raw_albums = [x for x in albums_req.get('results', []) if x.get('collectionType') == 'Album' and x.get('artistId') == artist_id]
        
        # СОРТИРУЕМ ПО КАТЕГОРИЯМ
        discography = sort_albums(raw_albums)
        
        # Ищем картинку артиста (через последний альбом)
        artist_image = None
        if discography['albums']:
            artist_image = discography['albums'][0]['artworkUrl100']
        elif raw_albums:
            artist_image = raw_albums[0]['artworkUrl100'].replace('100x100bb', '400x400bb')

        return render_template('index.html', view='artist_detail', artist=artist, discography=discography, artist_image=artist_image)
    except Exception as e:
        return f"Error: {e}"

@app.route('/album/<int:collection_id>')
def album_page(collection_id):
    # (Эта часть без изменений, она работает хорошо)
    try:
        url = f"https://itunes.apple.com/lookup?id={collection_id}&entity=song"
        data = requests.get(url).json()
        if data['resultCount'] > 0:
            album_info = data['results'][0]
            songs = []
            for item in data['results'][1:]:
                if item.get('kind') == 'song':
                    track_query = f"{item['artistName']} {item['trackName']}"
                    item['spotify_link'] = generate_spotify_link(track_query)
                    songs.append(item)
            
            album_info['artworkUrl100'] = album_info.get('artworkUrl100', '').replace('100x100bb', '600x600bb')
            album_query = f"{album_info['artistName']} {album_info['collectionName']}"
            spotify_link = generate_spotify_link(album_query)
            
            return render_template('index.html', view='album_detail', album=album_info, songs=songs, spotify_link=spotify_link)
    except:
        pass
    return "Album not found"

if __name__ == '__main__':
    app.run(debug=True)
