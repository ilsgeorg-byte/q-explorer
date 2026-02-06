import re
import urllib.parse

def clean_name(name):
    """
    Удаляет текст в скобках для лучшего поиска в Last.fm.
    Пример: "Bohemian Rhapsody (Remastered 2011)" -> "Bohemian Rhapsody"
    """
    if not name: return ""
    # Удаляем всё, что в круглых () или квадратных [] скобках
    return re.sub(r'\s*[\(\[].*?[\)\]]', '', name).strip()

def generate_spotify_link(query):
    if not query: return "#"
    return f"https://open.spotify.com/search/{urllib.parse.quote(query)}"

def sort_albums(albums):
    """
    Сортирует альбомы: сначала свежие, разделяет на LP и Синглы.
    """
    lps = []
    singles = []
    
    for alb in albums:
        # Улучшаем качество обложки сразу
        if 'artworkUrl100' in alb:
            alb['artworkUrl100'] = alb['artworkUrl100'].replace('100x100bb', '300x300bb')
        
        # Определяем год
        date_str = alb.get('releaseDate', '')
        alb['year'] = date_str[:4] if date_str else ''
        
        # Логика: если меньше 4 треков или в названии "Single/EP" - это сингл
        track_count = alb.get('trackCount', 0)
        title = alb.get('collectionName', '').lower()
        
        if track_count < 4 or 'single' in title or 'ep' in title:
            singles.append(alb)
        else:
            lps.append(alb)
            
    # Сортировка: новые сверху
    lps.sort(key=lambda x: x.get('releaseDate', ''), reverse=True)
    singles.sort(key=lambda x: x.get('releaseDate', ''), reverse=True)
    
    return {'albums': lps, 'singles': singles}
