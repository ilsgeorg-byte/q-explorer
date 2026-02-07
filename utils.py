import re
import urllib.parse
from datetime import datetime

def clean_name(name):
    if not name: return ""
    # Убираем всё в скобках: " (Deluxe)", " [Remastered]", " (2011 Version)"
    clean = re.sub(r'\s*[\(\[].*?[\)\]]', '', name)
    return clean.strip()

def normalize_title(title):
    """
    Делает название "чистым" для сравнения версий.
    Leviathan (Deluxe) -> leviathan
    """
    if not title: return ""
    # Убираем скобки
    clean = re.sub(r'\s*[\(\[].*?[\)\]]', '', title)
    # Убираем мусор и приводим к нижнему регистру
    clean = clean.lower().strip()
    # Убираем спецсимволы, оставляем только буквы и цифры
    clean = re.sub(r'[^a-z0-9]', '', clean)
    return clean

def generate_spotify_link(query):
    if not query: return "#"
    return f"https://open.spotify.com/search/{urllib.parse.quote(query)}"

def sort_albums(albums):
    """
    Сортирует и чистит альбомы:
    1. Распределяет по категориям (Live, Compilations, Singles, Albums).
    2. Для Studio Albums делает дедупликацию (оставляет только оригиналы).
    """
    categories = {
        'albums': [],       # Сюда попадут только уникальные студийные
        'live': [],
        'compilations': [],
        'singles': []
    }
    
    # Словарь для дедупликации студийных альбомов
    # Ключ: нормализованное название, Значение: альбом
    unique_studio = {} 

    for alb in albums:
        title = alb.get('collectionName', '').strip()
        if not title: continue
        
        # Улучшаем картинку сразу
        if 'artworkUrl100' in alb:
            alb['artworkUrl100'] = alb['artworkUrl100'].replace('100x100bb', '300x300bb')
            
        date_str = alb.get('releaseDate', '')
        alb['year'] = date_str[:4] if date_str else ''
        
        lower_title = title.lower()
        track_count = alb.get('trackCount', 0)
        
        # --- ЛОГИКА ФИЛЬТРАЦИИ ---

        # 1. Singles & EPs
        # Если в названии есть " EP" (с пробелом) или заканчивается на "EP"
        is_explicit_ep = ' ep' in lower_title or lower_title.endswith('ep')
        is_single = ' - single' in lower_title
        
        if track_count < 5 or is_single or is_explicit_ep:
            categories['singles'].append(alb)
            continue
            
        # 2. Live Albums
        if any(x in lower_title for x in ['live', 'concert', 'tour', 'wembley', 'bowl', 'montreal', 'budokan', 'at the']):
            categories['live'].append(alb)
            continue
            
        # 3. Compilations
        if any(x in lower_title for x in ['greatest hits', 'best of', 'anthology', 'collection', 'essential', 'platinum', 'gold', 'years', 'hits', 'box set']):
            categories['compilations'].append(alb)
            continue
            
        # 4. STUDIO ALBUMS (С Дедупликацией)
        # Если мы дошли сюда, это скорее всего студийный альбом.
        
        norm_key = normalize_title(title)
        
        if norm_key in unique_studio:
            # У нас уже есть альбом с таким названием (например, лежит Deluxe, а пришел Original)
            existing_alb = unique_studio[norm_key]
            
            # Сравниваем даты: оставляем тот, который СТАРШЕ (Original)
            existing_date = existing_alb.get('releaseDate', '9999')
            current_date = alb.get('releaseDate', '9999')
            
            if current_date < existing_date:
                # Текущий альбом старше - заменяем им то, что было в словаре
                unique_studio[norm_key] = alb
            # Иначе: оставляем старый, текущий (более новый ремастер/делюкс) игнорируем
        else:
            # Новый уникальный альбом
            unique_studio[norm_key] = alb

    # Перекладываем уникальные студийные альбомы из словаря в список
    categories['albums'] = list(unique_studio.values())

    # Сортируем каждую категорию по дате (Новые сверху)
    for key in categories:
        categories[key].sort(key=lambda x: x.get('releaseDate', ''), reverse=True)
        
    return categories
