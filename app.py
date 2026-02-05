from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import urllib.parse

app = Flask(__name__)

def generate_qobuz_link(query):
    encoded_query = urllib.parse.quote(query)
    return f"https://www.qobuz.com/us-en/search?q={encoded_query}"

def generate_spotify_link(query):
    # Используем https ссылку, она умная: если есть приложение - откроет его, если нет - веб
    encoded_query = urllib.parse.quote(query)
    return f"https://open.spotify.com/search/{encoded_query}"

def check_hires(query):
    try:
        url = generate_qobuz_link(query)
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=2)
        soup = BeautifulSoup(r.text, 'html.parser')
        return len(soup.find_all(class_='logo-hires')) > 0
    except:
        return False

@app.route('/')
def index():
    query = request.args.get('q')
    search_type = request.args.get('type', 'album') # По умолчанию ищем альбомы

    if query:
        # Настройка сущности поиска для iTunes
        entity_map = {
            'album': 'album',
            'artist': 'musicArtist',
            'song': 'song'
        }
        entity = entity_map.get(search_type, 'album')

        try:
            # Если ищем артиста, лимит поменьше, результаты другие
            url = f"https://itunes.apple.com/search?term={query}&entity={entity}&limit=24"
            response = requests.get(url)
            data = response.json()
            results = data.get('results', [])
            
            # Фильтрация: иногда iTunes выдает мусор, если ищем артиста, убираем треки без artistId
            if search_type == 'artist':
                results = [r for r in results if r.get('artistType') == 'Artist']

            return render_template('index.html', view='results', results=results, search_type=search_type)
        except Exception as e:
            print(f"Error: {e}")
            pass
    
    return render_template('index.html', view='home')

@app.route('/album/<int:collection_id>')
def album_page(collection_id):
    try:
        # Получаем данные альбома
        url = f"https://itunes.apple.com/lookup?id={collection_id}&entity=song"
        data = requests.get(url).json()
        
        if data['resultCount'] > 0:
            album_info = data['results'][0]
            songs = []
            
            # Обрабатываем песни
            for item in data['results'][1:]:
                if item.get('kind') == 'song':
                    # Ссылки для каждой песни
                    track_query = f"{item['artistName']} {item['trackName']}"
                    item['qobuz_link'] = generate_qobuz_link(track_query)
                    item['spotify_link'] = generate_spotify_link(track_query)
                    songs.append(item)
            
            # Улучшаем обложку
            album_info['artworkUrl100'] = album_info.get('artworkUrl100', '').replace('100x100bb', '600x600bb')
            
            # Генерируем запросы для кнопок альбома
            album_query = f"{album_info['artistName']} {album_info['collectionName']}"
            
            qobuz_link = generate_qobuz_link(album_query)
            spotify_link = generate_spotify_link(album_query)
            
            # Проверяем Hi-Res
            is_hires = check_hires(album_query)
            
            return render_template(
                'index.html', 
                view='album', 
                album=album_info, 
                songs=songs, 
                is_hires=is_hires, 
                qobuz_link=qobuz_link,
                spotify_link=spotify_link
            )
    except:
        pass
    
    return "Album not found"

if __name__ == '__main__':
    app.run(debug=True)
