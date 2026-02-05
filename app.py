from flask import Flask, render_template, request, redirect, url_for
import requests
import urllib.parse
import cloudscraper
import re

app = Flask(__name__)
scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

def check_hires(query):
    """Проверка Hi-Res на Qobuz"""
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.qobuz.com/us-en/search?q={encoded_query}"
        response = scraper.get(url, timeout=3)
        if response.status_code == 200:
            html = response.text.lower()
            markers = ['hi-res', '24-bit', '24 bit', 'studio master', '96khz', '192khz']
            for m in markers:
                if m in html: return True
        return False
    except:
        return False

def get_smart_artist_image(albums):
    """
    Ищет обложку для артиста, ИГНОРИРУЯ сборники и лайвы.
    Берет первый попавшийся 'чистый' студийный альбом.
    """
    for album in albums:
        title = album.get('collectionName', '').lower()
        # Фильтр стоп-слов для обложки артиста
        if any(x in title for x in ['best of', 'greatest', 'collection', 'live', 'hits', 'tour', 'anthology', 'essential']):
            continue
        # Если нашли нормальный альбом - возвращаем его обложку
        return album.get('artworkUrl100', '').replace('100x100bb', '600x600bb')
    
    # Если ничего не нашли (только сборники), возвращаем первый попавшийся
    if albums:
        return albums[0].get('artworkUrl100', '').replace('100x100bb', '600x600bb')
    return None

def categorize_album(album):
    """Определяет категорию альбома для сортировки"""
    title = album.get('collectionName', '').lower()
    track_count = album.get('trackCount', 0)
    
    if any(x in title for x in ['live', 'concert', 'tour', ' at ']):
        return 'live'
    elif any(x in title for x in ['greatest hits', 'best of', 'collection', 'anthology', 'essential', 'platinum', 'gold']):
        return 'compilation'
    elif track_count <= 4 or 'single' in title or ' ep' in title: # EP часто 4-6 треков, но тут упростим
        return 'single'
    else:
        return 'album'

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        query = request.form.get('query')
        search_type = request.form.get('type')
        return redirect(url_for('search_results', query=query, stype=search_type))
    return render_template('index.html', view='home')

@app.route('/search')
def search_results():
    query = request.args.get('query')
    stype = request.args.get('stype')
    entity = {'artist': 'musicArtist', 'album': 'album', 'song': 'song'}.get(stype, 'album')
    
    try:
        data = requests.get("https://itunes.apple.com/search", params={"term": query, "media": "music", "entity": entity, "limit": 12}).json()
        results = []
        
        for item in data.get('results', []):
            if stype == 'artist':
                # Делаем быстрый доп. запрос, чтобы найти нормальную обложку
                artist_id = item['artistId']
                try:
                    # Запрашиваем 5 альбомов, чтобы было из чего выбрать
                    lookup = requests.get(f"https://itunes.apple.com/lookup?id={artist_id}&entity=album&limit=5", timeout=2).json()
                    image = get_smart_artist_image(lookup.get('results', [])[1:])
                except:
                    image = None
                
                results.append({
                    'id': artist_id,
                    'name': item['artistName'],
                    'sub': item.get('primaryGenreName', 'Music'),
                    'image': image, 
                    'type': 'artist'
                })
            elif stype == 'album' or stype == 'song':
                # Для альбомов и песен логика стандартная
                artwork = item.get('artworkUrl100', '').replace('100x100bb', '600x600bb')
                res = {
                    'id': item.get('collectionId' if stype=='album' else 'trackId'),
                    'name': item.get('collectionName' if stype=='album' else 'trackName'),
                    'sub': item['artistName'],
                    'image': artwork,
                    'type': stype
                }
                if stype == 'song':
                    res['album_id'] = item['collectionId']
                    res['qobuz_link'] = f"https://play.qobuz.com/search?q={urllib.parse.quote(item['artistName'] + ' ' + item['trackName'])}"
                results.append(res)
                
        return render_template('index.html', view='results', results=results, stype=stype, query=query)
    except Exception as e:
        print(e)
        return render_template('index.html', view='error', message="Search failed")

@app.route('/artist/<int:artist_id>')
def artist_page(artist_id):
    # Качаем МНОГО альбомов (до 200), чтобы точно всё найти
    data = requests.get(f"https://itunes.apple.com/lookup?id={artist_id}&entity=album&limit=200").json()
    
    if data['resultCount'] > 0:
        artist_info = data['results'][0]
        raw_albums = data['results'][1:]
        
        # Словарь для разделения по секциям
        discography = {
            'album': [],
            'single': [],
            'live': [],
            'compilation': []
        }
        
        # Получаем красивую обложку для артиста (из студийных альбомов)
        artist_image = get_smart_artist_image(raw_albums)
        
        for a in raw_albums:
            if a.get('collectionType') == 'Album':
                a['artworkUrl100'] = a.get('artworkUrl100', '').replace('100x100bb', '600x600bb')
                cat = categorize_album(a)
                discography[cat].append(a)
        
        # Сортируем каждую категорию по дате (сначала новые)
        for cat in discography:
            discography[cat].sort(key=lambda x: x.get('releaseDate', ''), reverse=True)
            
        return render_template('index.html', view='artist', artist=artist_info, discography=discography, artist_image=artist_image)
    return "Artist not found"

@app.route('/album/<int:album_id>')
def album_page(album_id):
    data = requests.get(f"https://itunes.apple.com/lookup?id={album_id}&entity=song").json()
    if data['resultCount'] > 0:
        album_info = data['results'][0]
        songs = data['results'][1:]
        album_info['artworkUrl100'] = album_info.get('artworkUrl100', '').replace('100x100bb', '600x600bb')
        
        search_term = f"{album_info['artistName']} {album_info['collectionName']}"
        is_hires = check_hires(search_term)
        q_link = f"https://play.qobuz.com/search?q={urllib.parse.quote(search_term)}"
        
        return render_template('index.html', view='album', album=album_info, songs=songs, is_hires=is_hires, qobuz_link=q_link)
    return "Album not found"

if __name__ == '__main__':
    app.run(debug=True, port=5000)
