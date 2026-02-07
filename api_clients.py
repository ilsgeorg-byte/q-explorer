import requests
import urllib.parse
from utils import clean_name

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

# НОВАЯ ФУНКЦИЯ: Поиск через Deezer (дает картинки!)
def search_deezer_artists(query, limit):
    try:
        url = f"https://api.deezer.com/search/artist?q={urllib.parse.quote(query)}&limit={limit}"
        response = requests.get(url, timeout=5)
        data = response.json().get('data', [])
        
        # Превращаем формат Deezer в наш формат (похожий на iTunes)
        results = []
        for item in data:
            results.append({
                'artistId': item['id'], # Это ID Deezer, но нам для картинки пойдет
                'artistName': item['name'],
                'image': item['picture_medium'], # ВОТ ОНА, КАРТИНКА!
                'primaryGenreName': 'Music',
                'source': 'deezer' # Метка, что это Deezer
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
    # Эта функция остается для iTunes (если вдруг Deezer не сработал)
    try:
        if not artist_id: return None
        results = lookup_itunes(artist_id, 'album', 1)
        for item in results:
            if item.get('collectionType') == 'Album' and item.get('artworkUrl100'):
                return item['artworkUrl100'].replace('100x100bb', '400x400bb')
    except: pass
    return None

def get_lastfm_artist_data(artist_name):
    """
    Возвращает словарь с данными Last.fm:
    {
        'stats': строка "X Last.fm listeners",
        'bio': краткая биография,
        'tags': список тегов
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
            
            # 1. Stats (ДОБАВЛЯЕМ "Last.fm")
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
    """Получает описание жанра"""
    try:
        url = f"{LASTFM_URL}?method=tag.getinfo&tag={urllib.parse.quote(tag)}&api_key={LASTFM_API_KEY}&format=json"
        data = requests.get(url, timeout=2).json()
        if 'tag' in data and 'wiki' in data['tag']:
            return data['tag']['wiki'].get('summary', '').split('<a href')[0].strip()
    except: return ""
    return ""

def get_tag_artists(tag, page=1, limit=30):
    """Получает топ артистов жанра"""
    try:
        url = f"{LASTFM_URL}?method=tag.gettopartists&tag={urllib.parse.quote(tag)}&api_key={LASTFM_API_KEY}&format=json&page={page}&limit={limit}"
        response = requests.get(url, timeout=3)
        data = response.json()
        
        # ДЕБАГ: Если снова увидите 0, посмотрите в консоль (терминал), что там печатается
        # print(f"DEBUG TAG DATA: {data}") 
        
        artists = []
        if 'topartists' in data and 'artist' in data['topartists']:
            for art in data['topartists']['artist']:
                # Пробуем достать listeners разными способами
                raw_listeners = art.get('listeners', 0)
                
                # Иногда это словарь {'#text': '123'}, иногда строка, иногда число
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

