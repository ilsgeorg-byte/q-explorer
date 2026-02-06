import requests
import urllib.parse
from utils import clean_name_for_search

LASTFM_API_KEY = "23579f4b7b17523bef4d3a1fd3edc8ce"

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
