from flask import Flask, render_template, request
import requests
import urllib.parse
import re

app = Flask(__name__)

# LAST.FM API KEY
LASTFM_API_KEY = "23579f4b7b17523bef4d3a1fd3edc8ce"

def clean_name_for_search(text):
    if not text: return ""
    text = re.sub(r'\s*\(.*?\)', '', text)
    text = re.sub(r'\s*\[.*?\]', '', text)
    text = re.sub(r'(?i)\s(deluxe|remastered|expanded|anniversary)\s+edition', '', text)
    return text.strip()

def get_lastfm_artist_stats(artist_name):
    try:
        clean_name = clean_name_for_search(artist_name)
        # ВАЖНО: Уменьшили timeout до 1.5 сек. Vercel не любит долгие запросы.
        url = f"http://ws.audioscrobbler.com/2.0/?method=artist.getinfo&artist={urllib.parse.quote(clean_name)}&api_key={LASTFM_API_KEY}&format=json"
        data = requests.get(url, timeout=1.5).json()
        
        if 'artist' in data and 'stats' in data['artist']:
            stats = data['artist']['stats']
            listeners = int(stats['listeners'])
            val = ""
            if listeners > 1000000:
                val = f"{listeners/1000000:.1f}M"
            elif listeners > 1000:
                val = f"{listeners/1000:.0f}K"
            else:
                val = str(listeners)
            return f"👥 {val} listeners"
    except:
        return None # Если ошибка или таймаут, просто возвращаем None
    return None

def get_lastfm_album_stats(artist_name, album_name):
    try:
        clean_art = clean_name_for_search(artist_name)
        clean_alb = clean_name_for_search(album_name)
        # Timeout 1.5 сек
        url = f"http://ws.audioscrobbler.com/2.0/?method=album.getinfo&api_key={LASTFM_API_KEY}&artist={urllib.parse.quote(clean_art)}&album={urllib.parse.quote(clean_alb)}&format=json"
        data = requests.get(url, timeout=1.5).json()
        
        if 'album' in data:
            playcount = int(data['album'].get('playcount', 0))
            if playcount > 0:
                val = ""
                if playcount > 1000000:
                    val = f"{playcount/1000000:.1f}M"
                elif playcount > 1000:
                    val = f"{playcount/1000:.0f}K"
                else:
                    val = str(playcount)
                return f"🔥 {val} plays"
    except:
        return None
    return None

def generate_spotify_link(query):
    return f"https://open.spotify.com/search/{urllib.parse.quote(query)}"

def get_true_artist_image(artist_id):
    try:
        # Timeout 2.0 сек
        url = f"https://itunes.apple.com/lookup?id={artist_id}&entity=album&limit=1"
        r = requests.get(url, timeout=2.0).json()
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
        
        # Получаем статистику для каждого альбома в дискографии (осторожно с таймаутами!)
        # Чтобы не висело, можно временно отключить stats здесь или делать это очень быстро
        # alb['stats'] = get_lastfm_album_stats(alb['artistName'], alb['collectionName']) 
        # ^ ВЫКЛЮЧИЛ это внутри цикла дискографии, иначе 50 альбомов * 1.5 сек = 75 сек (ошибка 500)
        
        if 'live' in name or 'concert' in name: categorized['live'].append(alb)
        elif 'greatest' in name or 'best of' in name or 'anthology' in name: categorized['compilations'].append(alb)
        elif cnt < 5 or 'single' in name or 'ep' in name: categorized['singles'].append(alb)
        else: categorized['albums'].append(alb)
    
    for k in categorized: categorized[k].sort(key=lambda x: x.get('releaseDate', ''), reverse=True)
    return categorized

@app.route('/')
def index():
    query = request.args.get('q')
    if not query: return render_template('index.html', view='home')
    results = {'artists': [], 'albums': [], 'songs': []}
    
    try:
        # 1. ARTISTS (Максимум 4, чтобы не висело)
        r_art = requests.get(f"https://itunes.apple.com/search?term={query}&entity=musicArtist&limit=4", timeout=3).json()
        for art in r_art.get('results', []):
            if query.lower() in art['artistName'].lower():
                art['image'] = get_true_artist_image(art['artistId'])
                # Получаем статистику (отдельный запрос)
                art['stats'] = get_lastfm_artist_stats(art['artistName'])
                results['artists'].append(art)

        # 2. ALBUMS
        r_alb = requests.get(f"https://itunes.apple.com/search?term={query}&entity=album&limit=15", timeout=3).json()
        for alb in r_alb.get('results', []):
            if query.lower() in alb['collectionName'].lower():
                alb['artworkUrl100'] = alb.get('artworkUrl100', '').replace('100x100bb', '300x300bb')
                results['albums'].append(alb)
        results['albums'] = results['albums'][:8]

        # 3. SONGS
        r_song = requests.get(f"https://itunes.apple.com/search?term={query}&entity=song&limit=15", timeout=3).json()
        for song in r_song.get('results', []):
            if query.lower() in song['trackName'].lower():
                q = f"{song['artistName']} {song['trackName']}"
                song['spotify_link'] = generate_spotify_link(q)
                results['songs'].append(song)
        results['songs'] = results['songs'][:10]

    except Exception as e:
        print(f"Error: {e}")

    return render_template('index.html', view='results', data=results, query=query)

@app.route('/see-all/<type>')
def see_all(type):
    query = request.args.get('q')
    results = []
    entity_map = {'artists': 'musicArtist', 'albums': 'album', 'songs': 'song'}
    entity = entity_map.get(type, 'album')
    
    try:
        url = f"https://itunes.apple.com/search?term={query}&entity={entity}&limit=50"
        data = requests.get(url, timeout=4).json()
        
        for item in data.get('results', []):
            match = False
            if type == 'artists':
                if query.lower() in item['artistName'].lower():
                    item['image'] = get_true_artist_image(item['artistId'])
                    # Здесь тоже зовем Last.fm, но осторожно
                    item['stats'] = get_lastfm_artist_stats(item['artistName'])
                    match = True
            elif type == 'albums':
                if query.lower() in item['collectionName'].lower():
                    item['artworkUrl100'] = item.get('artworkUrl100', '').replace('100x100bb', '300x300bb')
                    match = True
            elif type == 'songs':
                if query.lower() in item['trackName'].lower():
                    item['spotify_link'] = generate_spotify_link(f"{item['artistName']} {item['trackName']}")
                    match = True
            if match: results.append(item)
    except: pass
    return render_template('index.html', view='see_all', results=results, type=type, query=query)

@app.route('/artist/<int:artist_id>')
def artist_page(artist_id):
    try:
        lookup = requests.get(f"https://itunes.apple.com/lookup?id={artist_id}", timeout=3).json()
        artist = lookup['results'][0]
        artist['stats'] = get_lastfm_artist_stats(artist['artistName'])
        
        albums_req = requests.get(f"https://itunes.apple.com/lookup?id={artist_id}&entity=album&limit=200", timeout=4).json()
        raw_albums = [x for x in albums_req.get('results', []) if x.get('collectionType') == 'Album' and x.get('artistId') == artist_id]
        
        discography = sort_albums(raw_albums)
        
        artist_image = None
        if discography['albums']: artist_image = discography['albums'][0]['artworkUrl100']
        
        return render_template('index.html', view='artist_detail', artist=artist, discography=discography, artist_image=artist_image)
    except:
        return "Error loading artist"

@app.route('/album/<int:collection_id>')
def album_page(collection_id):
    try:
        url = f"https://itunes.apple.com/lookup?id={collection_id}&entity=song"
        data = requests.get(url, timeout=3).json()
        
        if data['resultCount'] > 0:
            album_info = data['results'][0]
            songs = []
            for item in data['results'][1:]:
                if item.get('kind') == 'song':
                    item['spotify_link'] = generate_spotify_link(f"{item['artistName']} {item['trackName']}")
                    songs.append(item)
            
            album_info['artworkUrl100'] = album_info.get('artworkUrl100', '').replace('100x100bb', '600x600bb')
            
            # Статистика альбома (здесь можно, так как это ОДИН запрос)
            album_stats = get_lastfm_album_stats(album_info['artistName'], album_info['collectionName'])
            
            spotify_link = generate_spotify_link(f"{album_info['artistName']} {album_info['collectionName']}")
            
            return render_template('index.html', view='album_detail', album=album_info, songs=songs, spotify_link=spotify_link, album_stats=album_stats)
    except:
        pass
    return "Album not found"

if __name__ == '__main__':
    app.run(debug=True)
