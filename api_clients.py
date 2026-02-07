import requests
import urllib.parse
from utils import clean_name

# --- CONFIGURATION ---
ITUNES_API_URL = "https://itunes.apple.com"
LASTFM_API_KEY = "2c19989f6498c0a876a3e5950543793e" # Public demo key
LASTFM_URL = "http://ws.audioscrobbler.com/2.0/"

def search_itunes(query, entity='album', limit=20):
    try:
        clean_query = urllib.parse.quote(query)
        url = f"{ITUNES_API_URL}/search?term={clean_query}&entity={entity}&limit={limit}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json().get('results', [])
    except Exception as e:
        print(f"Error searching iTunes: {e}")
        return []

def lookup_itunes(id, entity=None, limit=200):
    try:
        url = f"{ITUNES_API_URL}/lookup?id={id}&country=US"
        if entity:
            url += f"&entity={entity}&limit={limit}"
        response = requests.get(url, timeout=5)
        return response.json().get('results', [])
    except:
        return []

def get_true_artist_image(artist_id):
    """Ищет обложку последнего альбома, чтобы использовать как фото артиста"""
    try:
        url = f"{ITUNES_API_URL}/lookup?id={artist_id}&entity=album&limit=5"
        data = requests.get(url, timeout=3).json()
        results = data.get('results', [])
        albums = [x for x in results if x.get('collectionType') == 'Album']
        if albums:
            albums.sort(key=lambda x: x.get('releaseDate', ''), reverse=True)
            return albums[0].get('artworkUrl100', '').replace('100x100bb', '600x600bb')
    except:
        pass
    return None

def get_lastfm_artist_data(artist_name):
    """Возвращает stats, bio, tags"""
    try:
        if not artist_name: return None
        clean = clean_name(artist_name)
        url = f"{LASTFM_URL}?method=artist.getinfo&artist={urllib.parse.quote(clean)}&api_key={LASTFM_API_KEY}&format=json"
        data = requests.get(url, timeout=2).json()
        
        result = {'stats': '', 'bio': '', 'tags': []}
        
        if 'artist' in data:
            art = data['artist']
            # Stats
            if 'stats' in art:
                listeners = int(art['stats'].get('listeners', 0))
                if listeners > 1000000: result['stats'] = f"👥 {listeners/1000000:.1f}M Last.fm listeners"
                elif listeners > 1000: result['stats'] = f"👥 {listeners/1000:.0f}K Last.fm listeners"
                else: result['stats'] = f"👥 {listeners} Last.fm listeners"
            # Bio
            if 'bio' in art and 'summary' in art['bio']:
                summary = art['bio']['summary'].split('<a href')[0]
                result['bio'] = summary.strip()
            # Tags
            if 'tags' in art and 'tag' in art['tags']:
                tags = art['tags']['tag']
                if isinstance(tags, list): result['tags'] = [t['name'] for t in tags[:4]]
                elif isinstance(tags, dict): result['tags'] = [tags['name']]
        return result
    except:
        return None

def get_lastfm_album_stats(artist, album):
    try:
        clean_art = clean_name(artist)
        clean_alb = clean_name(album)
        url = f"{LASTFM_URL}?method=album.getinfo&api_key={LASTFM_API_KEY}&artist={urllib.parse.quote(clean_art)}&album={urllib.parse.quote(clean_alb)}&format=json"
        data = requests.get(url, timeout=2).json()
        if 'album' in data and 'listeners' in data['album']:
            listeners = int(data['album']['listeners'])
            if listeners > 1000000: return f"🔥 {listeners/1000000:.1f}M scrobbles"
            if listeners > 1000: return f"🔥 {listeners/1000:.0f}K scrobbles"
            return f"🔥 {listeners} scrobbles"
    except: pass
    return ""

def get_similar_artists(artist_name):
    try:
        url = f"{LASTFM_URL}?method=artist.getsimilar&artist={urllib.parse.quote(artist_name)}&api_key={LASTFM_API_KEY}&limit=4&format=json"
        data = requests.get(url, timeout=2).json()
        similar = []
        if 'similarartists' in data and 'artist' in data['similarartists']:
            for art in data['similarartists']['artist']:
                similar.append({'name': art['name']})
        return similar
    except: return []

def get_tag_info(tag):
    try:
        url = f"{LASTFM_URL}?method=tag.getinfo&tag={urllib.parse.quote(tag)}&api_key={LASTFM_API_KEY}&format=json"
        data = requests.get(url, timeout=2).json()
        if 'tag' in data and 'wiki' in data['tag']:
            return data['tag']['wiki'].get('summary', '').split('<a href')[0].strip()
    except: return ""
    return ""

def get_tag_artists(tag, page=1, limit=20):
    try:
        url = f"{LASTFM_URL}?method=tag.gettopartists&tag={urllib.parse.quote(tag)}&api_key={LASTFM_API_KEY}&format=json&page={page}&limit={limit}"
        data = requests.get(url, timeout=3).json()
        artists = []
        if 'topartists' in data and 'artist' in data['topartists']:
            for art in data['topartists']['artist']:
                artists.append({
                    'artistName': art['name'],
                    'listeners': int(art.get('listeners', 0))
                })
        return artists
    except: return []
