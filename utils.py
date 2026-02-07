import re
import urllib.parse

def clean_name(name):
    """
    Очищает название: "In Rock (2018 Remastered)" -> "In Rock"
    """
    if not name: return ""
    clean = re.sub(r'\s*[\(\[].*?[\)\]]', '', name)
    clean = re.sub(r'\s-\s.*(Remaster|Deluxe|Edition|Version|Remix).*', '', clean, flags=re.IGNORECASE)
    return clean.strip()

def normalize_title(title):
    """
    Ключ для поиска дубликатов: "The Wall [Remaster]" -> "thewall"
    """
    if not title: return ""
    clean = re.sub(r'\s*[\(\[].*?[\)\]]', '', title)
    clean = clean.lower().strip()
    clean = re.sub(r'[^a-z0-9]', '', clean)
    return clean

def generate_spotify_link(query):
    if not query: return "#"
    return f"https://open.spotify.com/search/{urllib.parse.quote(query)}"

def sort_albums(albums):
    categories = {
        'albums': [],       # Студийные
        'live': [],         # Live
        'compilations': [], # Сборники
        'singles': []       # Синглы и EP
    }
    
    unique_studio = {} 

    for alb in albums:
        original_title = alb.get('collectionName', '').strip()
        if not original_title: continue
        
        # Картинка лучше
        if 'artworkUrl100' in alb:
            alb['artworkUrl100'] = alb['artworkUrl100'].replace('100x100bb', '300x300bb')
            
        date_str = alb.get('releaseDate', '')
        alb['year'] = date_str[:4] if date_str else ''
        
        lower_title = original_title.lower()
        track_count = alb.get('trackCount', 0)
        
        # 1. Singles & EPs
        is_explicit_ep = bool(re.search(r'\bep\b', lower_title))
        is_single = ' - single' in lower_title
        
        if track_count < 5 or is_single or is_explicit_ep:
            alb['collectionName'] = clean_name(original_title)
            categories['singles'].append(alb)
            continue
            
        # 2. Live
        if any(x in lower_title for x in ['live', 'concert', 'tour', 'wembley', 'bowl', 'montreal', 'budokan', 'at the', 'bbc']):
            alb['collectionName'] = clean_name(original_title)
            categories['live'].append(alb)
            continue
            
        # 3. Compilations
        if any(x in lower_title for x in ['greatest hits', 'best of', 'anthology', 'collection', 'essential', 'platinum', 'gold', 'years', 'hits', 'box set']):
            alb['collectionName'] = clean_name(original_title)
            categories['compilations'].append(alb)
            continue
            
        # 4. Studio Albums (Дедупликация)
        norm_key = normalize_title(original_title)
        alb['collectionName'] = clean_name(original_title)
        
        if norm_key in unique_studio:
            existing = unique_studio[norm_key]
            if alb.get('releaseDate', '9999') < existing.get('releaseDate', '9999'):
                unique_studio[norm_key] = alb
        else:
            unique_studio[norm_key] = alb

    categories['albums'] = list(unique_studio.values())

    for key in categories:
        categories[key].sort(key=lambda x: x.get('releaseDate', ''), reverse=True)
        
    return categories
