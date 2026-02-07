import re
import urllib.parse

def clean_name(name):
    """
    Очищает название от мусора.
    Пример: "In Rock (2018 Remastered Version)" -> "In Rock"
    """
    if not name: return ""
    
    # 1. Убираем всё в скобках () и []
    clean = re.sub(r'\s*[\(\[].*?[\)\]]', '', name)
    
    # 2. Убираем хвосты типа " - Remastered", " - Deluxe" без скобок
    clean = re.sub(r'\s-\s.*(Remaster|Deluxe|Edition|Version|Remix).*', '', clean, flags=re.IGNORECASE)
    
    return clean.strip()

def normalize_title(title):
    """
    Превращает название в "ключ" для поиска дубликатов.
    "The Dark Side of the Moon (Remaster)" -> "thedarksideofthemoon"
    """
    if not title: return ""
    clean = re.sub(r'\s*[\(\[].*?[\)\]]', '', title) # Убираем скобки
    clean = clean.lower().strip()
    clean = re.sub(r'[^a-z0-9]', '', clean) # Оставляем только буквы и цифры
    return clean

def generate_spotify_link(query):
    if not query: return "#"
    return f"https://open.spotify.com/search/{urllib.parse.quote(query)}"

def sort_albums(albums):
    """
    Сортирует альбомы по категориям и удаляет дубликаты (оставляя ранние версии).
    """
    categories = {
        'albums': [],       # Студийные
        'live': [],         # Концертные
        'compilations': [], # Сборники
        'singles': []       # Синглы и EP
    }
    
    unique_studio = {} # Для дедупликации студийных

    for alb in albums:
        original_title = alb.get('collectionName', '').strip()
        if not original_title: continue
        
        # Улучшаем качество обложки
        if 'artworkUrl100' in alb:
            alb['artworkUrl100'] = alb['artworkUrl100'].replace('100x100bb', '300x300bb')
            
        date_str = alb.get('releaseDate', '')
        alb['year'] = date_str[:4] if date_str else ''
        
        lower_title = original_title.lower()
        track_count = alb.get('trackCount', 0)
        
        # --- ЛОГИКА РАСПРЕДЕЛЕНИЯ ---

        # 1. Singles & EPs
        # Ищем 'EP' как отдельное слово или явный маркер ' - single'
        is_explicit_ep = bool(re.search(r'\bep\b', lower_title))
        is_single = ' - single' in lower_title
        
        if track_count < 5 or is_single or is_explicit_ep:
            alb['collectionName'] = clean_name(original_title)
            categories['singles'].append(alb)
            continue
            
        # 2. Live Albums
        if any(x in lower_title for x in ['live', 'concert', 'tour', 'wembley', 'bowl', 'montreal', 'budokan', 'at the', 'bbc']):
            alb['collectionName'] = clean_name(original_title)
            categories['live'].append(alb)
            continue
            
        # 3. Compilations
        if any(x in lower_title for x in ['greatest hits', 'best of', 'anthology', 'collection', 'essential', 'platinum', 'gold', 'years', 'hits', 'box set']):
            alb['collectionName'] = clean_name(original_title)
            categories['compilations'].append(alb)
            continue
            
        # 4. STUDIO ALBUMS (С Дедупликацией)
        
        # Нормализуем ключ для проверки на дубликат
        norm_key = normalize_title(original_title)
        
        # Очищаем название для показа (убираем Remastered 2011)
        alb['collectionName'] = clean_name(original_title)
        
        if norm_key in unique_studio:
            existing_alb = unique_studio[norm_key]
            
            # Если текущий альбом старше (меньше год выпуска), берем его как оригинал
            existing_date = existing_alb.get('releaseDate', '9999')
            current_date = alb.get('releaseDate', '9999')
            
            if current_date < existing_date:
                unique_studio[norm_key] = alb
        else:
            unique_studio[norm_key] = alb

    # Добавляем уникальные студийные
    categories['albums'] = list(unique_studio.values())

    # Сортируем все списки по дате (свежие сверху)
    for key in categories:
        categories[key].sort(key=lambda x: x.get('releaseDate', ''), reverse=True)
        
    return categories
