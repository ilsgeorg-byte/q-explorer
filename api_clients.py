import requests
import urllib.parse
from utils import clean_name

# --- CONFIGURATION ---
ITUNES_API_URL = "https://itunes.apple.com"
LASTFM_API_KEY = "2c19989f6498c0a876a3e5950543793e" # Public demo key
LASTFM_URL = "http://ws.audioscrobbler.com/2.0/"

def search_itunes(query, entity='album', limit=20):
    """
    Поиск в iTunes Store.
    entity: 'musicArtist', 'album', 'song'
    """
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
    """
    Получение деталей по ID (Artist ID или Collection ID).
    """
    try:
        url = f"{ITUNES_API_URL}/lookup?id={id}&country=US"
        if entity:
            url += f"&entity={entity}&limit={limit}"
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json().get('results', [])
    except Exception as e:
        print(f"Error looking up iTunes: {e}")
        return []

def get_true_artist_image(artist_id):
    """
    Пытается найти настоящее фото артиста.
    iTunes API не дает фото артиста напрямую, поэтому мы хитрим:
    ищем альбомы артиста и берем обложку самого свежего.
    """
    try:
        # Ищем 5 последних альбомов
        url = f"{ITUNES_API_URL}/lookup?id={artist_id}&entity=album&limit=5"
        data = requests.get(url, timeout=3).json()
        
        results = data.get('results', [])
        # Первый элемент results - это сам артист (без фото), пропускаем его
        albums = [x for x in results if x.get('collectionType') == 'Album']
        
        if albums:
            # Сортируем по дате, чтобы взять самый свежий (там актуальное фото)
            albums.sort(key=lambda x: x.get('releaseDate', ''), reverse=True)
            # Берем самую большую картинку
            return albums[0].get('artworkUrl100', '').replace('100x100bb', '600x600bb')
            
    except:
        pass
    return None

def get_lastfm_artist_data(artist_name):
    """
    Возвращает словарь с данными Last.fm:
    {
        'stats': строка "X listeners",
        'bio': краткая биография (summary),
        'tags': список тегов (жанров)
    }
    """
    try:
        if not artist_name: return None
        # Очищаем имя от мусора (Deluxe и т.д.) для лучшего поиска
        clean = clean_name(artist_name)
        url = f"{LASTFM_URL}?method=artist.getinfo&artist={urllib.parse.quote(clean)}&api_key={LASTFM_API_KEY}&format=json"
        
        data = requests.get(url, timeout=2).json()
        
        result = {'stats': '', 'bio': '', 'tags': []}
        
        if 'artist' in data:
            art = data['artist']
            
            # 1. Stats (Listeners)
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
                # Убираем ссылку <a href="...">Read more on Last.fm</a>
                summary = summary.split('<a href')[0]
                result['bio'] = summary.strip()
                
            # 3. Tags
            if 'tags' in art and 'tag' in art['tags']:
                tags = art['tags']['tag']
                # Если тег один - API может вернуть словарь, а не список. Проверяем type.
                if isinstance(tags, list):
                    # Берем первые 3-4 тега
                    result['tags'] = [t['name'] for t in tags[:4]]
                elif isinstance(tags, dict):
                     result['tags'] = [tags['name']]
                
        return result
    except Exception as e:
        print(f"LastFM Error: {e}")
        return None

def get_lastfm_album_stats(artist, album):
    """
    Получает количество прослушиваний конкретного альбома.
    """
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
    except:
        pass
    return ""

def get_similar_artists(artist_name):
    """
    Возвращает список похожих артистов (имя + картинка-заглушка).
    """
    try:
        url = f"{LASTFM_URL}?method=artist.getsimilar&artist={urllib.parse.quote(artist_name)}&api_key={LASTFM_API_KEY}&limit=4&format=json"
        data = requests.get(url, timeout=2).json()
        
        similar = []
        if 'similarartists' in data and 'artist' in data['similarartists']:
            for art in data['similarartists']['artist']:
                # LastFM дает плохие картинки, но у нас нет выбора для списка
                # Берем medium image если есть
                img = next((x['#text'] for x in art.get('image', []) if x['size'] == 'medium'), '')
                
                similar.append({
                    'name': art['name'],
                    'image': img  # Часто пустая или белая заглушка
                })
        return similar
    except:
        return []

def get_tag_info(tag):
    """
    Получает описание тега (жанра).
    """
    try:
        url = f"{LASTFM_URL}?method=tag.getinfo&tag={urllib.parse.quote(tag)}&api_key={LASTFM_API_KEY}&format=json"
        data = requests.get(url, timeout=2).json()
        if 'tag' in data and 'wiki' in data['tag']:
            summary = data['tag']['wiki'].get('summary', '')
            return summary.split('<a href')[0].strip()
    except:
        return ""
    return ""

def get_tag_artists(tag, page=1, limit=20):
    """
    Получает топ артистов по тегу (жанру) с пагинацией.
    """
    try:
        url = f"{LASTFM_URL}?method=tag.gettopartists&tag={urllib.parse.quote(tag)}&api_key={LASTFM_API_KEY}&format=json&page={page}&limit={limit}"
        data = requests.get(url, timeout=3).json()
        
        artists = []
        if 'topartists' in data and 'artist' in data['topartists']:
            for art in data['topartists']['artist']:
                artists.append({
                    'artistName': art['name'],
                    'artistId': None, # ID нет, будем искать при клике или через JS
                    'url': art['url'],
                    'listeners': int(art.get('listeners', 0))
                })
        return artists
    except:
        return []
