from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import urllib.parse

app = Flask(__name__)

def generate_qobuz_link(query):
    """Генерирует ссылку на поиск Qobuz"""
    encoded_query = urllib.parse.quote(query)
    return f"https://www.qobuz.com/us-en/search?q={encoded_query}"

def check_hires(query):
    """
    Парсит страницу поиска Qobuz, чтобы узнать, 
    есть ли там значки Hi-Res для этого альбома.
    (Простой парсинг, может не всегда работать идеально, но полезно)
    """
    try:
        url = generate_qobuz_link(query)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        r = requests.get(url, headers=headers, timeout=3)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Ищем специфические классы Qobuz, отвечающие за значки качества
        hires_badges = soup.find_all(class_='logo-hires')
        return len(hires_badges) > 0
    except:
        return False

@app.route('/')
def index():
    query = request.args.get('q')
    if query:
        # Поиск альбомов через iTunes API
        try:
            url = f"https://itunes.apple.com/search?term={query}&entity=album&limit=12"
            response = requests.get(url)
            data = response.json()
            return render_template('index.html', view='results', results=data.get('results', []))
        except Exception as e:
            return f"Error connecting to iTunes API: {e}"
    
    # Если поиска нет, показываем пустую страницу
    return render_template('index.html', view='home')

@app.route('/album/<int:album_id>')
def album_page(album_id):
    try:
        # Получаем детали альбома и список треков
        # entity=song возвращает и инфо об альбоме (первый элемент), и треки
        url = f"https://itunes.apple.com/lookup?id={album_id}&entity=song"
        response = requests.get(url)
        data = response.json()
        
        if data['resultCount'] > 0:
            # Первый элемент — это сам альбом
            album_info = data['results'][0]
            
            # Остальные элементы — это треки
            songs = []
            
            # Проходимся по всем трекам, чтобы добавить им ссылки
            for item in data['results'][1:]:
                if item.get('kind') == 'song': # На всякий случай проверяем, что это песня
                    # Формируем точный запрос для поиска конкретного трека
                    track_query = f"{item['artistName']} {item['collectionName']} {item['trackName']}"
                    item['qobuz_link'] = generate_qobuz_link(track_query)
                    songs.append(item)
            
            # Улучшаем качество обложки (iTunes отдает 100x100, меняем на 600x600)
            album_info['artworkUrl100'] = album_info.get('artworkUrl100', '').replace('100x100bb', '600x600bb')
            
            # Генерируем ссылку для всего альбома
            album_query = f"{album_info['artistName']} {album_info['collectionName']}"
            main_qobuz_link = generate_qobuz_link(album_query)
            
            # Проверяем наличие Hi-Res (парсинг)
            is_hires = check_hires(album_query)
            
            return render_template(
                'index.html', 
                view='album', 
                album=album_info, 
                songs=songs, 
                is_hires=is_hires, 
                qobuz_link=main_qobuz_link
            )
            
    except Exception as e:
        print(f"Error: {e}")
        pass
        
    return "Album not found or API error"

if __name__ == '__main__':
    app.run(debug=True)
