from flask import Flask, render_template, request
import requests
import urllib.parse
import re

app = Flask(__name__)

# --- CONFIG ---
LASTFM_API_KEY = "23579f4b7b17523bef4d3a1fd3edc8ce"

# --- UTILS ---
def clean_name_for_search(text):
    if not text: return ""
    text = re.sub(r'\s*\(.*?\)', '', text)
    text = re.sub(r'\s*\[.*?\]', '', text)
    text = re.sub(r'(?i)\s(deluxe|remastered|expanded|anniversary)\s+edition', '', text)
    return text.strip()

def generate_spotify_link(query):
    return f"https://open.spotify.com/search/{urllib.parse.quote(query)}"

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
    
    for k in categorized: categorized[k].sort(key=lambda x: x.get('releaseDate', ''), reverse=True)
    return categorized

# --- API CLIENTS ---
def get_lastfm_artist_stats(artist_name):
    try:
        clean_name = clean_name_for_search(artist_name)
        url = f"http://ws.audioscrobbler.com/2.0/?method=artist.getinfo&artist={urllib.parse.quote(clean_name)}&api_key={LASTFM_API_KEY}&format=json"
        data = requests.get(url, timeout=1.5).json()
        if 'artist' in data and 'stats' in data['artist']:
            listeners = int(data['artist']['stats']['listeners'])
            if listeners > 1000000: return f"👥 {listeners/1000000:.1f}M listeners"
            if listeners > 1000: return f"👥 {listeners/1000:.0f}K listeners"
            return f"👥 {listeners} listeners"
    except: return None

def get_lastfm_album_stats(artist_name, album_name):
    try:
        clean_art = clean_name_for_search(artist_name)
        clean_alb = clean_name_for_search(album_name)
        url = f"http://ws.audioscrobbler.com/2.0/?method=album.getinfo&api_key={LASTFM_API_KEY}&artist={urllib.parse.quote(clean_art)}&album={urllib.parse.quote(clean_alb)}&format=json"
        data = requests.get(url, timeout=1.5).json()
        if 'album' in data:
            playcount = int(data['album'].get('playcount', 0))
            if playcount > 1000000: return f"🔥 {playcount/1000000:.1f}M plays"
            if playcount > 1000: return f"🔥 {playcount/1000:.0f}K plays"
            return f"🔥 {playcount} plays"
    except: return None

def get_true_artist_image(artist_id):
    try:
        url = f"https://itunes.apple.com/lookup?id={artist_id}&entity=album&limit=1"
        r = requests.get(url, timeout=2.0).json()
        for item in r.get('results', []):
            if item.get('collectionType') == 'Album' and item.get('artworkUrl100'):
                 return item['artworkUrl100'].replace('100x100bb', '400x400bb')
    except: pass
    return None

def search_itunes(query, entity, limit):
    try:
        url = f"https://itunes.apple.com/search?term={query}&entity={entity}&limit={limit}"
        return requests.get(url, timeout=3).json().get('results', [])
    except: return []

def lookup_itunes(id, entity=None, limit=None):
    try:
        url = f"https://itunes.apple.com/lookup?id={id}"
        if entity: url += f"&entity={entity}"
        if limit: url += f"&limit={limit}"
        return requests.get(url, timeout=4).json().get('results', [])
    except: return []

# --- ROUTES ---
@app.route('/')
def index():
    query = request.args.get('q')
    if not query: return render_template('index.html', view='home')

    results = {'artists': [], 'albums': [], 'songs': []}
    
    # 1. Artists
    for art in search_itunes(query, 'musicArtist', 4):
        if query.lower() in art['artistName'].lower():
            art['image'] = get_true_artist_image(art['artistId'])
            art['stats'] = get_lastfm_artist_stats(art['artistName'])
            results['artists'].append(art)

    # 2. Albums
    for alb in search_itunes(query, 'album', 15):
        if query.lower() in alb['collectionName'].lower():
            alb['artworkUrl100'] = alb.get('artworkUrl100', '').replace('100x100bb', '300x300bb')
            results['albums'].append(alb)
    results['albums'] = results['albums'][:8]

    # 3. Songs
    for song in search_itunes(query, 'song', 15):
        if query.lower() in song['trackName'].lower():
            q = f"{song['artistName']} {song['trackName']}"
            song['spotify_link'] = generate_spotify_link(q)
            results['songs'].append(song)
    results['songs'] = results['songs'][:10]

    return render_template('index.html', view='results', data=results, query=query)

@app.route('/see-all/<type>')
def see_all(type):
    query = request.args.get('q')
    results = []
    entity_map = {'artists': 'musicArtist', 'albums': 'album', 'songs': 'song'}
    entity = entity_map.get(type, 'album')
    
    for item in search_itunes(query, entity, 50):
        match = False
        if type == 'artists' and query.lower() in item['artistName'].lower():
            item['image'] = get_true_artist_image(item['artistId'])
            item['stats'] = get_lastfm_artist_stats(item['artistName'])
            match = True
        elif type == 'albums' and query.lower() in item['collectionName'].lower():
            item['artworkUrl100'] = item.get('artworkUrl100', '').replace('100x100bb', '300x300bb')
            match = True
        elif type == 'songs' and query.lower() in item['trackName'].lower():
            item['spotify_link'] = generate_spotify_link(f"{item['artistName']} {item['trackName']}")
            match = True
        
        if match: results.append(item)
        
    return render_template('index.html', view='see_all', results=results, type=type, query=query)

@app.route('/artist/<int:artist_id>')
def artist_page(artist_id):
    data = lookup_itunes(artist_id)
    if not data: return "Artist not found"
    artist = data[0]
    artist['stats'] = get_lastfm_artist_stats(artist['artistName'])
    
    raw_albums = [x for x in lookup_itunes(artist_id, 'album', 200) if x.get('collectionType') == 'Album' and x.get('artistId') == artist_id]
    discography = sort_albums(raw_albums)
    
    artist_image = discography['albums'][0]['artworkUrl100'] if discography['albums'] else None
    return render_template('index.html', view='artist_detail', artist=artist, discography=discography, artist_image=artist_image)

@app.route('/album/<int:collection_id>')
def album_page(collection_id):
    data = lookup_itunes(collection_id, 'song')
    if not data: return "Album not found"
    
    album_info = data[0]
    album_info['artworkUrl100'] = album_info.get('artworkUrl100', '').replace('100x100bb', '600x600bb')
    album_stats = get_lastfm_album_stats(album_info['artistName'], album_info['collectionName'])
    spotify_link = generate_spotify_link(f"{album_info['artistName']} {album_info['collectionName']}")
    
    songs = []
    for item in data[1:]:
        if item.get('kind') == 'song':
            item['spotify_link'] = generate_spotify_link(f"{item['artistName']} {item['trackName']}")
            songs.append(item)
            
    return render_template('index.html', view='album_detail', album=album_info, songs=songs, spotify_link=spotify_link, album_stats=album_stats)

if __name__ == '__main__':
    app.run(debug=True)
