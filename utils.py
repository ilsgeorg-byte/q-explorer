import re
import urllib.parse

def clean_name(name):
    if not name: return ""
    return re.sub(r'\s*[\(\[].*?[\)\]]', '', name).strip()

def generate_spotify_link(query):
    if not query: return "#"
    return f"https://open.spotify.com/search/{urllib.parse.quote(query)}"

def sort_albums(albums):
    """
    Сортирует альбомы по категориям:
    - Albums (Студийные)
    - Live (Live, Concert, Tour)
    - Compilations (Greatest Hits, Best Of, Anthology)
    - Singles & EPs
    """
    categories = {
        'albums': [],
        'live': [],
        'compilations': [],
        'singles': []
    }
    
    seen = set() # Чтобы убрать дубликаты
    
    for alb in albums:
        # Уникальность по названию (игнорируем регистр)
        title = alb.get('collectionName', '').strip()
        if not title: continue
        
        # Ключ уникальности: название + год (чтобы не путать ремастеры разных лет)
        key = (title.lower(), alb.get('releaseDate', '')[:4])
        if key in seen: continue
        seen.add(key)
        
        # Улучшаем картинку
        if 'artworkUrl100' in alb:
            alb['artworkUrl100'] = alb['artworkUrl100'].replace('100x100bb', '300x300bb')
        
        # Год
        date_str = alb.get('releaseDate', '')
        alb['year'] = date_str[:4] if date_str else ''
        
        track_count = alb.get('trackCount', 0)
        lower_title = title.lower()
        
        # ЛОГИКА СОРТИРОВКИ
        
        # 1. Singles / EP
        if track_count < 5 or ' - single' in lower_title or ' - ep' in lower_title:
            categories['singles'].append(alb)
            continue
            
        # 2. Live Albums
        if any(x in lower_title for x in ['live', 'concert', 'tour', 'wembley', 'bowl', 'montreal', 'budokan']):
            categories['live'].append(alb)
            continue
            
        # 3. Compilations
        if any(x in lower_title for x in ['greatest hits', 'best of', 'anthology', 'collection', 'essential', 'platinum', 'gold', 'years', 'hits']):
            categories['compilations'].append(alb)
            continue
            
        # 4. Остальное - Студийные альбомы
        categories['albums'].append(alb)

    # Сортируем каждую категорию по дате (новые сверху)
    for key in categories:
        categories[key].sort(key=lambda x: x.get('releaseDate', ''), reverse=True)
        
    return categories
