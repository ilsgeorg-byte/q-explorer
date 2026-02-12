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

def sort_albums(albums):
    # Dictionaries for deduplication of each category
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
        
        # Clean title immediately
        # IMPORTANT: We modify the 'alb' object directly here, which is fine.
        alb['collectionName'] = clean_name(original_title)
        
        # --- FILTERING AND DISTRIBUTION LOGIC ---
        target_dict = unique_studio # Default to studio album

        # 1. Singles & EPs
        is_explicit_ep = bool(re.search(r'\bep\b', lower_title))
        is_single = ' - single' in lower_title
        
        if track_count < 5 or is_single or is_explicit_ep:
            target_dict = unique_singles
            
        # 2. Live Albums (Priority over singles? No, live can be a single, but usually live albums are long.
        # If live is short - let it be a single? Or live?
        # Usually users want to see concerts separately.
        # Check: if the title contains "Live", it's likely a Live album, even if short.)
        elif any(x in lower_title for x in ['live', 'concert', 'tour', 'wembley', 'bowl', 'montreal', 'budokan', 'at the', 'bbc']):
             target_dict = unique_live
            
        # 3. Compilations
        elif any(x in lower_title for x in ['greatest hits', 'best of', 'anthology', 'collection', 'essential', 'platinum', 'gold', 'years', 'hits', 'box set', 'decade', 'definitive', 'ultimate', 'rarities', 'retrospective', 'archive', 'sessions', 'very best']):
            target_dict = unique_compilations

        # --- DEDUPLICATION ---
        # If such album is already in the target category
        if norm_key in target_dict:
            existing_alb = target_dict[norm_key]
            
            # Compare dates: keep EARLIER release (original), not reissue
            existing_date = existing_alb.get('releaseDate', '9999')
            current_date = alb.get('releaseDate', '9999')
            
            if current_date < existing_date:
                target_dict[norm_key] = alb
            # Otherwise keep old one
        else:
            target_dict[norm_key] = alb

    # Export lists
    categories = {
        'albums': list(unique_studio.values()),
        'singles': list(unique_singles.values()),
        'live': list(unique_live.values()),
        'compilations': list(unique_compilations.values())
    }

    # Final sort by date (new to old)
    for key in categories:
        categories[key].sort(key=lambda x: x.get('releaseDate', ''), reverse=True)
        
    return categories
