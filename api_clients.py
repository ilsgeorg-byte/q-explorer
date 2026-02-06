import requests
import urllib.parse
from utils import clean_name

# Твой API ключ (если он другой, замени)
LASTFM_API_KEY = "23579f4b7b17523bef4d3a1fd3edc8ce"
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

def lookup_itunes(id, entity=None, limit=None):
    try:
        url = f"https://itunes.apple.com/lookup?id={id}"
        if entity:
            url += f"&entity={entity}"
        if limit:
            url += f"&limit={limit}"
        response = requests.get(url, timeout=5)
        return response.json().get('results', [])
    except Exception as e:
        print(f"Error lookup iTunes: {e}")
        return []

def get_true_artist_image(artist_id):
    """
    Пытается найти нормальное фото артиста через его первый альбом,
    так как iTunes API не отдает фото артиста напрямую.
    """
    try:
        if not artist_id: return None
        # Ищем 1 альбом этого артиста
        results = lookup_itunes(artist_id, 'album', 1)
        for item in results:
            if item.get('collectionType') == 'Album' and item.get('artworkUrl100'):
                # Берем обложку альбома как фото артиста (лучше чем ничего)
                return item['artworkUrl100'].replace('100x100bb', '400x400bb')
    except:
        pass
    return None

def get_lastfm_artist_stats(artist_name):
    try:
        if not artist_name: return None
        clean = clean_name(artist_name)
        url = f"{LASTFM_URL}?method=artist.getinfo&artist={urllib.parse.quote(clean)}&api_key={LASTFM_API_KEY}&format=json"
        data = requests.get(url, timeout=2).json()
        
        if 'artist' in data and 'stats' in data['artist']:
            listeners = int(data['artist']['stats']['listeners'])
            # Форматируем красиво: 1.2M или 500K
            if listeners > 1000000:
                return f"👥 {listeners/1000000:.1f}M listeners"
            elif listeners > 1000:
                return f"👥 {listeners/1000:.0f}K listeners"
            else:
                return f"👥 {listeners} listeners"
    except:
        return None
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
            if playcount > 1000000:
                return f"🔥 {playcount/1000000:.1f}M plays"
            elif playcount > 1000:
                return f"🔥 {playcount/1000:.0f}K plays"
            else:
                return f"🔥 {playcount} plays"
    except:
        return None
    return None

# ВОТ ЭТА ФУНКЦИЯ БЫЛА ПОТЕРЯНА
def get_similar_artists(artist_name, limit=5):
    try:
        if not artist_name: return []
        clean = clean_name(artist_name)
        url = f"{LASTFM_URL}?method=artist.getsimilar&artist={urllib.parse.quote(clean)}&api_key={LASTFM_API_KEY}&format=json&limit={limit}"
        data = requests.get(url, timeout=3).json()
        
        if 'similarartists' in data and 'artist' in data['similarartists']:
            # Возвращаем список словарей с именами
            return data['similarartists']['artist']
    except:
        return []
    return []
