from flask import Flask, render_template, request, redirect, url_for
import requests
import urllib.parse
import cloudscraper
import re

app = Flask(__name__)
scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

def clean_query(text):
    """Убирает мусор из названия для более точного поиска в Qobuz"""
    # Убираем всё в скобках (Remastered, Live, etc)
    text = re.sub(r'\(.*?\)', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    # Убираем feat. и прочее
    text = text.replace('feat.', '').replace('ft.', '')
    # Убираем лишние пробелы
    return " ".join(text.split())

def generate_qobuz_link(query):
    clean = clean_query(query)
    # Добавляем site:qobuz.com чтобы искать прицельно
    encoded = urllib.parse.quote(f"site:qobuz.com {clean}")
    return f"https://www.google.com/search?q={encoded}&btnI" # btnI = I'm Feeling Lucky


def check_hires(query):
    try:
        url = f"https://www.qobuz.com/us-en/search?q={urllib.parse.quote(query)}"
        response = scraper.get(url, timeout=3)
        if response.status_code == 200:
            html = response.text.lower()
            markers = ['hi-res', '24-bit', 'studio master', '96khz', '192khz']
            for m in markers:
                if m in html: return True
        return False
    except:
        return False

# ... (Остальные функции get_artist_image и т.д. остаются без изменений) ...
# ... (Но внутри search_results и album_page нужно обновить вызов ссылки) ...

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
            res = {
                'id': item.get('artistId' if stype=='artist' else ('collectionId' if stype=='album' else 'trackId')),
                'name': item.get('artistName' if stype=='artist' else ('collectionName' if stype=='album' else 'trackName')),
                'sub': item.get('primaryGenreName' if stype=='artist' else 'artistName'),
                'image': item.get('artworkUrl100', '').replace('100x100bb', '600x600bb'),
                'type': stype
            }
            if stype == 'song':
                res['album_id'] = item['collectionId']
                # ОБНОВЛЕНИЕ: Чистим запрос для ссылки
                search_q = f"{item['artistName']} {item['trackName']}"
                res['qobuz_link'] = generate_qobuz_link(search_q)
            
            results.append(res)
        return render_template('index.html', view='results', results=results, stype=stype, query=query)
    except:
        return render_template('index.html', view='error', message="Search failed")

# ... (Artist route без изменений) ...

@app.route('/album/<int:album_id>')
def album_page(album_id):
    data = requests.get(f"https://itunes.apple.com/lookup?id={album_id}&entity=song").json()
    if data['resultCount'] > 0:
        album_info = data['results'][0]
        songs = data['results'][1:]
        album_info['artworkUrl100'] = album_info.get('artworkUrl100', '').replace('100x100bb', '600x600bb')
        
        # ОБНОВЛЕНИЕ: Чистим запрос для ссылки
        search_term = f"{album_info['artistName']} {album_info['collectionName']}"
        q_link = generate_qobuz_link(search_term)
        is_hires = check_hires(search_term)
        
        return render_template('index.html', view='album', album=album_info, songs=songs, is_hires=is_hires, qobuz_link=q_link)
    return "Album not found"

if __name__ == '__main__':
    app.run(debug=True, port=5000)
