from flask import Flask, render_template, request
import requests
import urllib.parse
import re

app = Flask(__name__)

# LAST.FM API KEY
LASTFM_API_KEY = "23579f4b7b17523bef4d3a1fd3edc8ce"

def clean_name_for_search(text):
    """
    Очищает название от мусора, который мешает поиску в Last.fm.
    Пример: "Deep Purple (Remastered 2002)" -> "Deep Purple"
    """
    if not text: return ""
    # Убираем всё в скобках () и квадратных скобках []
    text = re.sub(r'\s*\(.*?\)', '', text)
    text = re.sub(r'\s*\[.*?\]', '', text)
    # Убираем "Deluxe Edition", "Remastered" если они без скобок
    text = re.sub(r'(?i)\s(deluxe|remastered|expanded|anniversary)\s+edition', '', text)
    return text.strip()

def get_lastfm_artist_stats(artist_name):
    """Получает статистику артиста с Last.fm"""
    try:
        clean_name = clean_name_for_search(artist_name)
        # Timeout 2.0 сек - баланс между скоростью и надежностью
        url = f"http://ws.audioscrobbler.com/2.0/?method=artist.getinfo&artist={urllib.parse.quote(clean_name)}&api_key={LASTFM_API_KEY}&format=json"
        data = requests.get(url, timeout=2.0).json()
        
        if 'artist' in data and 'stats' in data['artist']:
            stats = data['artist']['stats']
            listeners = int(stats['listeners'])
            
            # Форматируем число (1.2M, 500K)
            val = ""
            if listeners > 1000000:
                val = f"{listeners/1000000:.1f}M"
            elif listeners > 1000:
                val = f"{listeners/1000:.0f}K"
            else:
                val = str(listeners)
            
            return f"👥 {val} listeners"
    except:
        pass
    return None

def get_lastfm_album_stats(artist_name, album_name):
    """Получает статистику альбома"""
    try:
        clean_art = clean_name_for_search(artist_name)
        clean_alb = clean_name_for_search(album_name)

        url = f"http://ws.audioscrobbler.com/2.0/?method=album.getinfo&api_key={LASTFM_API_KEY}&artist={urllib.parse.quote(clean_art)}&album={urllib.parse.quote(clean_alb)}&format=json"
        data = requests.get(url, timeout=2.0).json()
        
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
        pass
    return None

def generate_spotify_link(query):
    return f"https://open.spotify.com/search/{urllib.parse.quote(query)}"

def get_true_artist_image(artist_id):
    try:
        url = f"https://itunes.apple.com/lookup?id={artist_id}&entity=album&limit=1"
        r = requests.get(url, timeout=2).json()
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
    
    for k in categorized: categorized[k].sort(key=lambda x: x.get('releaseDate', ''), reverse=True)
    return categorized

@app.route('/')
def index():
    query = request.args.get('q')
    if not query: return render_template('index.html', view='home')

    results = {'artists': [], 'albums': [], 'songs': []}
    
    try:
        # 1. ARTISTS
        r_art = requests.get(f"https://itunes.apple.com/search?term={query}&entity=musicArtist&limit=5", timeout=3).json()
        for art in r_art.get('results', []):
            if query.lower() in art['artistName'].lower():
                art['image'] = get_true_artist_image(art['artistId'])
                # Получаем статистику с Last.fm
                art['stats'] = get_lastfm_artist_stats(art['artistName'])
                results['artists'].append(art)

        # 2. ALBUMS (Строгий фильтр)
        r_alb = requests.get(f"https://itunes.apple.com/search?term={query}&entity=album&limit=20", timeout=3).json()
        for alb in r_alb.get('results', []):
            if query.lower() in alb['collectionName'].lower():
                alb['artworkUrl100'] = alb.get('artworkUrl100', '').replace('100x100bb', '300x300bb')
                results['albums'].append(alb)
        results['albums'] = results['albums'][:8]

        # 3. SONGS (Строгий фильтр)
        r_song = requests.get(f"https://itunes.apple.com/search?term={query}&entity=song&limit=20", timeout=3).json()
        for song in r_song.get('results', []):
            if query.lower() in song['trackName'].lower():
                q = f"{song['artistName']} {song['trackName']}"
                song['spotify_link'] = generate_spotify_link(q)
                results['songs'].append(song)
        results['songs'] = results['songs'][:10]

    except Exception as e:
        print(f"Search Error: {e}")

    return render_template('index.html', view='results', data=results, query=query)

@app.route('/see-all/<type>')
def see_all(type):
    query = request.args.get('q')
    results = []
    entity_map = {'artists': 'musicArtist', 'albums': 'album', 'songs': 'song'}
    entity = entity_map.get(type, 'album')
    
    try:
        url = f"https://itunes.apple.com/search?term={query}&entity={entity}&limit=50"
        data = requests.get(url, timeout=5).json()
        
        for item in data.get('results', []):
            match = False
            if type == 'artists':
                if query.lower() in item['artistName'].lower():
                    item['image'] = get_true_artist_image(item['artistId'])
                    item['stats'] = get_lastfm_artist_stats(item['artistName'])
                    match = True
            elif type == 'albums':
                if query.lower() in item['collectionName'].lower():
                    item['artworkUrl100'] = 
