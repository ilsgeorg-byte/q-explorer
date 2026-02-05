from flask import Flask, render_template, request
import requests
import urllib.parse

app = Flask(__name__)

def generate_spotify_link(query, type='search'):
    """
    type: 'search' (поиск), 'track' (играть трек), 'artist' (открыть артиста)
    """
    encoded_query = urllib.parse.quote(query)
    # Используем универсальную веб-ссылку, она сама решает, открыть приложение или сайт
    return f"https://open.spotify.com/search/{encoded_query}"

@app.route('/')
def index():
    query = request.args.get('q')
    
    if not query:
        return render_template('index.html', view='home')

    # Делаем 3 параллельных запроса, чтобы получить красивые секции
    results = {'artists': [], 'albums': [], 'songs': []}
    
    try:
        # 1. Artists
        r_art = requests.get(f"https://itunes.apple.com/search?term={query}&entity=musicArtist&limit=4").json()
        results['artists'] = r_art.get('results', [])

        # 2. Albums
        r_alb = requests.get(f"https://itunes.apple.com/search?term={query}&entity=album&limit=8").json()
        results['albums'] = r_alb.get('results', [])

        # 3. Songs
        r_song = requests.get(f"https://itunes.apple.com/search?term={query}&entity=song&limit=10").json()
        
        # Для песен сразу генерируем ссылки на Spotify
        for song in r_song.get('results', []):
            q = f"{song['artistName']} {song['trackName']}"
            song['spotify_link'] = generate_spotify_link(q)
            results['songs'].append(song)

    except Exception as e:
        print(e)

    return render_template('index.html', view='results', data=results, query=query)

@app.route('/artist/<int:artist_id>')
def artist_page(artist_id):
    # Страница артиста: показывает его топ альбомы
    try:
        # Сначала узнаем имя артиста
        lookup = requests.get(f"https://itunes.apple.com/lookup?id={artist_id}").json()
        if not lookup['resultCount']:
            return "Artist not found"
        
        artist = lookup['results'][0]
        
        # Теперь ищем его альбомы
        albums_req = requests.get(f"https://itunes.apple.com/lookup?id={artist_id}&entity=album&limit=20").json()
        # Первый результат в lookup&entity=album - это сам артист, отфильтруем его
        albums = [x for x in albums_req.get('results', []) if x.get('collectionType') == 'Album']
        
        return render_template('index.html', view='artist_detail', artist=artist, albums=albums)
    except:
        return "Error loading artist"

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
            
            # Ссылка на альбом в Spotify
            album_query = f"{album_info['artistName']} {album_info['collectionName']}"
            spotify_link = generate_spotify_link(album_query)
            
            return render_template(
                'index.html', 
                view='album_detail', 
                album=album_info, 
                songs=songs, 
                spotify_link=spotify_link
            )
    except:
        pass
    return "Album not found"

if __name__ == '__main__':
    app.run(debug=True)
