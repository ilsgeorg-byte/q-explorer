import re
import urllib.parse

def clean_name(name):
    """
    Превращает "In Rock (2018 Remastered Version)" -> "In Rock"
    Убирает мусор в скобках и после дефисов, если это техническая инфа.
    """
    if not name: return ""
    
    # 1. Убираем содержимое скобок () и []
    # Было: "Deep Purple In Rock (2018 Remastered Version)" -> "Deep Purple In Rock"
    clean = re.sub(r'\s*[\(\[].*?[\)\]]', '', name)
    
    # 2. Убираем " - Remastered" и прочее, если оно без скобок (редко, но бывает)
    # Пример: "Album Name - Deluxe Edition" -> "Album Name"
    clean = re.sub(r'\s-\s.*(Remaster|Deluxe|Edition|Version|Remix).*', '', clean, flags=re.IGNORECASE)
    
    return clean.strip()

def normalize_title(title):
    """
    Для сравнения (дедупликации).
    Убираем вообще всё, оставляем только буквы/цифры, чтобы найти дубли.
    """
    if not title: return ""
    clean = re.sub(r'\s*[\(\[].*?[\)\]]', '', title)
    clean = clean.lower().strip()
    # Оставляем только a-z и 0-9
    clean = re.sub(r'[^a-z0-9]', '', clean)
    return clean

def generate_spotify_link(query):
    if not query: return "#"
    return f"https://open.spotify.com/search/{urllib.parse.quote(query)}"

def sort_albums(albums):
    categories = {
        'albums': [],
        'live': [],
        'compilations': [],
        'singles': []
    }
    
    # Словарь для дедупликации студийных альбомов
    unique_studio = {} 

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
        
        # --- ЛОГИКА ФИЛЬТРАЦИИ ---

        # 1. Singles & EPs
        # Ищем слово "EP" как отдельное слово (через границы слова \b),
        # чтобы не реагировать на "Deep", "Sleep", "Keep".
        is_explicit_ep = bool(re.search(r'\bep\b', lower_title))
        is_single = ' - single' in lower_title
        
        if track_count < 5 or is_single or is_explicit_ep:
            # Даже если это EP, название тоже стоит почистить (убрать "(EP)")
            alb['collectionName'] = clean_name(original_title)
            categories['singles'].append(alb)
            continue
            
        # 2. Live Albums
        # Ищем ключевые слова для концертов
        if any(x in lower_title for x in ['live', 'concert', 'tour', 'wembley', 'bowl', 'montreal', 'budokan', 'at the', 'bbc']):
            alb['collectionName'] = clean_name(original_title)
            categories['live'].append(alb)
            continue
            
        # 3. Compilations
        if any(x in lower_title for x in ['greatest hits', 'best of', 'anthology', 'collection', 'essential', 'platinum', 'gold', 'years', 'hits', 'box set']):
            alb['collectionName'] = clean_name(original_title)
            categories['compilations'].append(alb)
            continue
            
        # 4. STUDIO ALBUMS (С Дедупликацией и Чисткой)
        
        # Сначала генерируем "чистый ключ" для поиска дубликатов
        norm_key = normalize_title(original_title)
        
        # ВАЖНО: Сразу чистим название для отображения на сайте!
        # Теперь "In Rock (2018 Remaster)" станет просто "In Rock" прямо в объекте
        alb['collectionName'] = clean_name(original_title)
        
        if norm_key in unique_studio:
            existing_alb = unique_studio[norm_key]
            
            # Сравниваем даты: если текущий старше (меньше год), берем его
            existing_date = existing_alb.get('releaseDate', '9999')
            current_date = alb.get('releaseDate', '9999')
            
            if current_date < existing_date:
                unique_studio[norm_key] = alb
        else:
            unique_studio[norm_key] = alb

    # Выгружаем уникальные студийные
    categories['albums'] = list(unique_studio.values())

    # Финальная сортировка по дате
    for key in categories:
        categories[key].sort(key=lambda x: x.get('releaseDate', ''), reverse=True)
        
    return categories
