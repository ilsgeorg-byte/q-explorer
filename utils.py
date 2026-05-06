import re
import urllib.parse

def clean_name(name):
    """
    Transforms "In Rock (2018 Remastered Version)" -> "In Rock"
    Removes junk in parentheses and after hyphens if it is technical info.
    """
    if not name: return ""
    
    # 1. Remove contents of () and []
    # Example: "Deep Purple In Rock (2018 Remastered Version)" -> "Deep Purple In Rock"
    clean = re.sub(r'\s*[\(\[].*?[\)\]]', '', name)
    
    # 2. Remove " - Remastered" etc. if they are without parentheses (rare but happens)
    # Example: "Album Name - Deluxe Edition" -> "Album Name"
    clean = re.sub(r'\s-\s.*(Remaster|Deluxe|Edition|Version|Remix).*', '', clean, flags=re.IGNORECASE)
    
    return clean.strip()

def normalize_title(title):
    """
    For comparison (deduplication).
    Remove everything, leave only letters/numbers to find duplicates.
    """
    if not title: return ""
    clean = re.sub(r'\s*[\(\[].*?[\)\]]', '', title)
    clean = clean.lower().strip()
    # Leave only a-z and 0-9
    clean = re.sub(r'[^a-z0-9]', '', clean)
    return clean

def generate_spotify_link(query):
    if not query: return "#"
    return f"https://open.spotify.com/search/{urllib.parse.quote(query)}"

def generate_youtube_link(query):
    if not query: return "#"
    return f"https://music.youtube.com/search?q={urllib.parse.quote(query)}"

def filter_and_process_artists(items, query_lower, limit=None):
    """Extract and deduplicate artists from search results."""
    seen_ids = set()
    seen_names = set()
    results = []
    
    for item in items:
        aid = item.get('artistId')
        name = item.get('artistName', '')
        
        if not aid or aid in seen_ids: continue
        if query_lower not in (name or "").lower(): continue
        if name.lower() in seen_names: continue
        
        seen_names.add(name.lower())
        seen_ids.add(aid)
        item['image'] = None  # Will load via JS
        results.append(item)
        
        if limit and len(results) >= limit:
            break
    
    return results

def filter_and_process_albums(items, query_lower, limit=None):
    """Extract and process albums from search results."""
    results = []
    
    for item in items:
        if item.get('collectionName') and query_lower in item.get('collectionName', '').lower():
            item['artworkUrl100'] = item.get('artworkUrl100', '').replace('100x100bb', '300x300bb')
            date = item.get('releaseDate', '')
            item['year'] = date[:4] if date else ''
            results.append(item)
            
            if limit and len(results) >= limit:
                break
    
    return results

def filter_and_process_songs(items, query_lower, limit=None):
    """Extract and process songs from search results."""
    results = []
    
    for item in items:
        if item.get('trackName') and query_lower in item.get('trackName', '').lower():
            q = f"{item.get('artistName', '')} {item.get('trackName', '')}"
            item['spotify_link'] = generate_spotify_link(q)
            item['youtube_link'] = generate_youtube_link(q)
            results.append(item)
            
            if limit and len(results) >= limit:
                break
    
    return results

def sort_albums(albums, sort_by='date', category_filter=None):
    """
    Sort and categorize albums by type (studio, singles, live, compilations).
    
    Args:
        albums: List of album items
        sort_by: 'date' (default), 'name', 'year'
        category_filter: None (all), or specific category like 'albums', 'singles'
    
    Returns:
        dict with 'albums', 'singles', 'live', 'compilations' categories
    """
    unique_studio = {}
    unique_singles = {}
    unique_live = {}
    unique_compilations = {}

    for alb in albums:
        original_title = alb.get('collectionName', '').strip()
        if not original_title: continue
        
        # Improve artwork quality
        if 'artworkUrl100' in alb:
            alb['artworkUrl100'] = alb['artworkUrl100'].replace('100x100bb', '300x300bb')
            
        date_str = alb.get('releaseDate', '')
        alb['year'] = date_str[:4] if date_str else ''
        
        lower_title = original_title.lower()
        track_count = alb.get('trackCount', 0)
        
        # Generate key for deduplication
        norm_key = normalize_title(original_title)
        
        # Clean title
        alb['collectionName'] = clean_name(original_title)
        
        # --- CLASSIFICATION LOGIC ---
        target_dict = unique_studio  # Default
        
        # Singles & EPs (< 5 tracks or explicit EP/Single label)
        if track_count < 5 or ' - single' in lower_title or re.search(r'\bep\b', lower_title):
            target_dict = unique_singles
        # Live Albums (concert/tour keywords)
        elif any(x in lower_title for x in ['live', 'concert', 'tour', 'wembley', 'bowl', 'montreal', 'budokan', 'at the', 'bbc']):
            target_dict = unique_live
        # Compilations (best of, greatest hits, etc.)
        elif any(x in lower_title for x in ['greatest hits', 'best of', 'anthology', 'collection', 'essential', 'platinum', 'gold', 'years', 'hits', 'box set', 'decade', 'definitive', 'ultimate', 'rarities', 'retrospective', 'archive', 'sessions', 'very best']):
            target_dict = unique_compilations

        # --- DEDUPLICATION (keep earliest release) ---
        if norm_key in target_dict:
            existing_date = target_dict[norm_key].get('releaseDate', '9999')
            current_date = alb.get('releaseDate', '9999')
            if current_date < existing_date:
                target_dict[norm_key] = alb
        else:
            target_dict[norm_key] = alb

    # Export lists
    categories = {
        'albums': list(unique_studio.values()),
        'singles': list(unique_singles.values()),
        'live': list(unique_live.values()),
        'compilations': list(unique_compilations.values())
    }

    # Apply sorting
    sort_key_map = {
        'date': lambda x: x.get('releaseDate', ''),
        'name': lambda x: x.get('collectionName', '').lower(),
        'year': lambda x: x.get('year', '')
    }
    sort_func = sort_key_map.get(sort_by, sort_key_map['date'])
    
    for key in categories:
        categories[key].sort(key=sort_func, reverse=(sort_by == 'date'))
    
    # Filter by category if requested
    if category_filter and category_filter in categories:
        return {category_filter: categories[category_filter]}
    
    return categories
