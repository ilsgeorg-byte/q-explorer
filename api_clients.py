import requests
import urllib.parse
from utils import clean_name
import requests_cache
import os
import tempfile
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# Setup cache
# Vercel has Read-Only file system, except /tmp
# So we try to write to /tmp, if fail — use memory.

cache_path = 'q_cache_v3'
backend = 'sqlite'

# Check if we can write to current directory
if not os.access('.', os.W_OK):
    # If not (e.g. on Vercel), use temp folder
    cache_path = os.path.join(tempfile.gettempdir(), 'q_cache')

try:
    requests_cache.install_cache(cache_name=cache_path, backend=backend, expire_after=86400)
except Exception:
    # If everything is bad (e.g. no disk access) — use memory
    requests_cache.install_cache(backend='memory', expire_after=86400)

LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
LASTFM_URL = "http://ws.audioscrobbler.com/2.0/"

def search_itunes(query, entity, limit):
    try:
        url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity={entity}&limit={limit}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json().get('results', [])
    except Exception as e:
        print(f"Error searching iTunes: {e}")
        return []

# NEW FUNCTION: Search via Deezer (gives images!)
def search_deezer_artists(query, limit):
    try:
        url = f"https://api.deezer.com/search/artist?q={urllib.parse.quote(query)}&limit={limit}"
        response = requests.get(url, timeout=5)
        data = response.json().get('data', [])
        
        # Transform Deezer format to our format (similar to iTunes)
        results = []
        for item in data:
            # Format fan count
            fans = item.get('nb_fan', 0)
            stats = ""
            if fans > 1000000:
                stats = f"👥 {fans/1000000:.1f}M Deezer fans"
            elif fans > 1000:
                stats = f"👥 {fans/1000:.0f}K Deezer fans"
            elif fans > 0:
                stats = f"👥 {fans} Deezer fans"

            results.append({
                'artistId': item['id'], # This is Deezer ID, but works for image lookup
                'artistName': item['name'],
                'image': item.get('picture_xl') or item.get('picture_big') or item.get('picture_medium'),
                'primaryGenreName': 'Music',
                'source': 'deezer', # Label that this is Deezer
                'stats': stats
            })
        return results
    except Exception as e:
        print(f"Error searching Deezer: {e}")
        return []

def lookup_itunes(id, entity=None, limit=None):
    try:
        url = f"https://itunes.apple.com/lookup?id={id}"
        if entity: url += f"&entity={entity}"
        if limit: url += f"&limit={limit}"
        response = requests.get(url, timeout=5)
        return response.json().get('results', [])
    except: return []

def get_true_artist_image(artist_id):
    # This function remains for iTunes (if Deezer fails)
    try:
        if not artist_id: return None
        # Search more albums (60) to skip "black square" covers (Donda, Vultures)
        results = lookup_itunes(artist_id, 'album', 60)
        for item in results:
            if item.get('collectionType') == 'Album' and item.get('artworkUrl100'):
                # Filter for Kanye West: skip Donda album (black cover)
                cname = item.get('collectionName', '').lower()
                if 'donda' in cname or 'vultures' in cname: continue
                return item['artworkUrl100'].replace('100x100bb', '400x400bb')
    except: pass
    return None

def get_lastfm_artist_data(artist_name):
    """
    Returns dict with Last.fm data:
    {
        'stats': string "X Last.fm listeners",
        'bio': short bio,
        'tags': list of tags
    }
    """
    try:
        if not artist_name: return None
        clean = clean_name(artist_name)
        url = f"{LASTFM_URL}?method=artist.getinfo&artist={urllib.parse.quote(clean)}&api_key={LASTFM_API_KEY}&format=json"
        data = requests.get(url, timeout=2).json()
        
        result = {'stats': '', 'bio': '', 'tags': []}
        
        if 'artist' in data:
            art = data['artist']
            
            # 1. Stats (ADD "Last.fm")
            if 'stats' in art:
                listeners = int(art['stats'].get('listeners', 0))
                if listeners > 1000000: 
                    result['stats'] = f"👥 {listeners/1000000:.1f}M Last.fm listeners"
                elif listeners > 1000: 
                    result['stats'] = f"👥 {listeners/1000:.0f}K Last.fm listeners"
                else: 
                    result['stats'] = f"👥 {listeners} Last.fm listeners"
            
            # 2. Bio
            if 'bio' in art and 'summary' in art['bio']:
                summary = art['bio']['summary']
                summary = summary.split('<a href')[0]
                result['bio'] = summary.strip()
                
            # 3. Tags
            if 'tags' in art and 'tag' in art['tags']:
                tags = art['tags']['tag']
                if isinstance(tags, list):
                    result['tags'] = [t['name'] for t in tags[:4]]
                elif isinstance(tags, dict):
                     result['tags'] = [tags['name']]
                     
        return result
    except Exception as e:
        print(f"LastFM Error: {e}")
        return None


def get_lastfm_album_stats(artist_name, album_name):
    try:
        if not artist_name or not album_name: return None
        clean_art = clean_name(artist_name)
        clean_alb = clean_name(album_name)
        url = f"{LASTFM_URL}?method=album.getinfo&api_key={LASTFM_API_KEY}&artist={urllib.parse.quote(clean_art)}&album={urllib.parse.quote(clean_alb)}&format=json"
        data = requests.get(url, timeout=2).json()
        if 'album' in data:
            playcount = int(data['album'].get('playcount', 0))
            if playcount > 1000000: return f"🔥 {playcount/1000000:.1f}M plays"
            elif playcount > 1000: return f"🔥 {playcount/1000:.0f}K plays"
            else: return f"🔥 {playcount} plays"
    except: return None

def get_similar_artists(artist_name, limit=5):
    try:
        if not artist_name: return []
        clean = clean_name(artist_name)
        url = f"{LASTFM_URL}?method=artist.getsimilar&artist={urllib.parse.quote(clean)}&api_key={LASTFM_API_KEY}&format=json&limit={limit}"
        data = requests.get(url, timeout=3).json()
        if 'similarartists' in data and 'artist' in data['similarartists']:
            return data['similarartists']['artist']
    except: return []
    return []

def get_tag_info(tag):
    """Gets genre description"""
    try:
        url = f"{LASTFM_URL}?method=tag.getinfo&tag={urllib.parse.quote(tag)}&api_key={LASTFM_API_KEY}&format=json"
        data = requests.get(url, timeout=2).json()
        if 'tag' in data and 'wiki' in data['tag']:
            return data['tag']['wiki'].get('summary', '').split('<a href')[0].strip()
    except: return ""
    return ""

def get_tag_artists(tag, page=1, limit=30):
    """Gets top artists of a genre"""
    try:
        url = f"{LASTFM_URL}?method=tag.gettopartists&tag={urllib.parse.quote(tag)}&api_key={LASTFM_API_KEY}&format=json&page={page}&limit={limit}"
        response = requests.get(url, timeout=3)
        data = response.json()
        
        # DEBUG: If you see 0 again, check console (terminal) for printed data
        # print(f"DEBUG TAG DATA: {data}") 
        
        artists = []
        if 'topartists' in data and 'artist' in data['topartists']:
            for art in data['topartists']['artist']:
                # Try to get listeners in different ways
                raw_listeners = art.get('listeners', 0)
                
                # Sometimes it is a dict {'#text': '123'}, sometimes string, sometimes number
                if isinstance(raw_listeners, dict):
                    raw_listeners = raw_listeners.get('#text', 0)
                
                try:
                    listeners = int(raw_listeners)
                except:
                    listeners = 0
                    
                artists.append({
                    'artistName': art['name'],
                    'listeners': listeners
                })
        return artists
    except Exception as e:
        print(f"Error fetching tag artists: {e}")
        return []
