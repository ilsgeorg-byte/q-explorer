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

def generate_youtube_link(query):
    if not query: return "#"
    return f"https://music.youtube.com/search?q={urllib.parse.quote(query)}"

def sort_albums(albums):
    # Словари для дедупликации каждой категории
    unique_studio = {}
    unique_singles = {}
    unique_live = {}
    unique_compilations = {}

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
        
        # Генерируем ключ для дедупликации
        norm_key = normalize_title(original_title)
        
        # Чистим название сразу
        # ВАЖНО: Делаем копию названия БЕЗ модификации исходного в цикле, если вдруг потребуется оригинал
        # Но здесь мы меняем объект 'alb' напрямую, так что ОК.
        alb['collectionName'] = clean_name(original_title)
        
        # --- ЛОГИКА ФИЛЬТРАЦИИ И РАСПРЕДЕЛЕНИЯ ---
        target_dict = unique_studio # По умолчанию считаем студийным

        # 1. Singles & EPs
        is_explicit_ep = bool(re.search(r'\bep\b', lower_title))
        is_single = ' - single' in lower_title
        
        if track_count < 5 or is_single or is_explicit_ep:
            target_dict = unique_singles
            
        # 2. Live Albums (Приоритет над синглами? Нет, лайв может быть синглом, но обычно лайв альбомы длинные. 
        # Если лайв короткий - пусть будет синглом? Или лайвом? 
        # Обычно пользователь хочет видеть концерты отдельно.
        # Давайте проверим: если в названии "Live", то это скорее Live, даже если короткий.)
        elif any(x in lower_title for x in ['live', 'concert', 'tour', 'wembley', 'bowl', 'montreal', 'budokan', 'at the', 'bbc']):
             target_dict = unique_live
            
        # 3. Compilations
        elif any(x in lower_title for x in ['greatest hits', 'best of', 'anthology', 'collection', 'essential', 'platinum', 'gold', 'years', 'hits', 'box set', 'decade', 'definitive', 'ultimate', 'rarities', 'retrospective', 'archive', 'sessions', 'very best']):
            target_dict = unique_compilations

        # --- ДЕДУПЛИКАЦИЯ ---
        # Если такой альбом уже есть в целевой категории
        if norm_key in target_dict:
            existing_alb = target_dict[norm_key]
            
            # Сравниваем даты: оставляем более РАННИЙ релиз (оригинал), а не переиздание
            # Или наоборот? Обычно хотят оригинал.
            existing_date = existing_alb.get('releaseDate', '9999')
            current_date = alb.get('releaseDate', '9999')
            
            if current_date < existing_date:
                target_dict[norm_key] = alb
            # Иначе оставляем старый
        else:
            target_dict[norm_key] = alb

    # Выгружаем списки
    categories = {
        'albums': list(unique_studio.values()),
        'singles': list(unique_singles.values()),
        'live': list(unique_live.values()),
        'compilations': list(unique_compilations.values())
    }

    # Финальная сортировка по дате (от новых к старым)
    for key in categories:
        categories[key].sort(key=lambda x: x.get('releaseDate', ''), reverse=True)
        
    return categories
