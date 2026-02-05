from flask import Flask, render_template, request
import requests
import urllib.parse

app = Flask(__name__)

def generate_spotify_link(query):
    return f"https://open.spotify.com/search/{urllib.parse.quote(query)}"

def get_true_artist_image(artist_id):
    """
    Ищет картинку артиста, проверяя artistId, чтобы не взять чужой альбом.
    """
    try:
        # Ищем альбомы конкретно этого artistId
        url = f"https://itunes.apple.com/lookup?id={artist_id}&entity=album&limit=1"
        r = requests.get(url).json()
        
        # Результат 0 - это артист, результаты 1..N - альбомы
        results = r.get('results', [])
        for item in results:
            if item.get('collectionType') == 'Album' and item.get('artworkUrl100'):
                 return item['artworkUrl100'].replace('100x100bb', '400x400bb')
    except:
        pass
    return None

def sort_albums(albums_list):
    categorized = {'albums': [], 'singles': [], 'live': [], 'compilations': []}
    seen = set()
    
    for alb in albums_list:
        if alb['collectionName'] in seen: continue
        seen.add(alb['collectionName'])
        
        alb['artworkUrl100'] = alb.get('artworkUrl100', '').replace('100x100bb', '400x400bb')
        name = alb['collectionName'].lower()
        cnt = alb.get('trackCount', 0)
        
        if 'live' in name or 'concert' in name: categorized['live'].append(alb)
        elif 'greatest' in name or 'best of' in name or 'anthology' in name: categorized['compilations'].append(alb)
        elif cnt < 5 or 'single' in name or 'ep' in name: categorized['singles'].append(alb)
        else: categorized['albums'].append(alb)
    
    for k in categorized:
        categorized[k].sort(key=lambda x: x.get('releaseDate', ''), reverse=True)
    return categorized

@app.route('/')
def index():
    query = request.args.get('q')
    if not query:
        return render_template('index.html', view='home')

    # Основной поиск (ограниченный)
    results = {'artists': [], 'albums': [], 'songs': []}
    
    try:
        # 1. ARTISTS
        r_art = requests.get(f"https://itunes.apple.com/search?term={query}&entity=musicArtist&limit=5").json()
        for art in r_art.get('results', []):
            # Строгая проверка: имя должно содержать запрос
            if query.lower() in art['artistName'].lower():
                art['image'] = get_true_artist_image(art['artistId'])
                results['artists'].append(art)

        # 2. ALBUMS
        r_alb = requests.get(f"https://itunes.apple.com/search?term={query}&entity=album&limit=10").json()
        for alb in r_alb.get('results', []):
            # Строгая проверка: либо в имени артиста, либо в названии альбома есть запрос
            if query.lower() in alb['artistName'].lower() or query.lower() in alb['collectionName'].lower():
                alb['artworkUrl100'] = alb.get('artworkUrl100', '').replace('100x100bb', '300x300bb')
                results['albums'].append(alb)

        # 3. SONGS
        r_song = requests.get(f"https://itunes.apple.com/search?term={query}&entity=song&limit=10").json()
        for song in r_song.get('results', []):
            if query.lower() in song['artistName'].lower() or query.lower() in song['trackName'].lower():
                q = f"{song['artistName']} {song['trackName']}"
                song['spotify_link'] = generate_spotify_link(q)
                results['songs'].append(song)

    except Exception as e:
        print(e)

    return render_template('index.html', view='results', data=results, query=query)

# СТРАНИЦА "SEE ALL"
@app.route('/see-all/<type>')
def see_all(type):
    query = request.args.get('q')
    results = []
    
    entity_map = {
        'artists': 'musicArtist',
        'albums': 'album',
        'songs': 'song'
    }
    entity = entity_map.get(type, 'album')
    
    try:
        url = f"https://itunes.apple.com/search?term={query}&entity={entity}&limit=50"
        data = requests.get(url).json()
        raw = data.get('results', [])
        
        # Применяем ту же строгую фильтрацию
        for item in raw:
            match = False
            if type == 'artists':
                if query.lower() in item['artistName'].lower():
                    item['image'] = get_true_artist_image(item['artistId'])
                    match = True
            elif type == 'albums':
                if query.lower() in item['artistName'].lower() or query.lower() in item['collectionName'].lower():
                    item['artworkUrl100'] = item.get('artworkUrl100', '').replace('100x100bb', '300x300bb')
                    match = True
            elif type == 'songs':
                if query.lower() in item['artistName'].lower() or query.lower() in item['trackName'].lower():
                    q = f"{item['artistName']} {item['trackName']}"
                    item['spotify_link'] = generate_spotify_link(q)
                    match = True
            
            if match:
                results.append(item)
                
    except:
        pass
        
    return render_template('index.html', view='see_all', results=results, type=type, query=query)

@app.route('/artist/<int:artist_id>')
def artist_page(artist_id):
    try:
        lookup = requests.get(f"https://itunes.apple.com/lookup?id={artist_id}").json()
        artist = lookup['results'][0]
        
        albums_req = requests.get(f"https://itunes.apple.com/lookup?id={artist_id}&entity=album&limit=200").json()
        raw_albums = [x for x in albums_req.get('results', []) if x.get('collectionType') == 'Album' and x.get('artistId') == artist_id]
        
        discography = sort_albums(raw_albums)
        artist_image = None
        if discography['albums']: artist_image = discography['albums'][0]['artworkUrl100']
        
        return render_template('index.html', view='artist_detail', artist=artist, discography=discography, artist_image=artist_image)
    except:
        return "Error"

@app.route('/album/<int:collection_id>')
def album_page(collection_id):
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
