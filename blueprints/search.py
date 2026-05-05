from flask import Blueprint, render_template, request
from flask_login import current_user
from api_clients import search_itunes
from utils import generate_spotify_link, generate_youtube_link
from concurrent.futures import ThreadPoolExecutor
import re

search_bp = Blueprint('search', __name__)

@search_bp.route('/')
def index():
    query = request.args.get('q')
    if not query:
        return render_template('index.html', view='home')
    
    # Cache the search results
    from flask import current_app
    cache = current_app.cache
    cache_key = f"search_{query}_{current_user.id if current_user.is_authenticated else 'anon'}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    results = {'artists': [], 'albums': [], 'songs': []}
    ql = query.lower()

    # 1. Artists (Main: take top 8, filter duplicates)
    seen_ids = set()
    seen_names = set()
    
    # First collect candidates (fast)
    candidates = []
    # Request with margin (25)
    for art in search_itunes(query, 'musicArtist', 25):
        aid = art.get('artistId')
        name = art.get('artistName', '')
        
        # Skip if ID missing or already seen
        if not aid or aid in seen_ids: continue
        # Skip if name is completely different (search noise)
        if ql not in (name or "").lower(): continue
        
        # Filter duplicates by name (iTunes sometimes returns several "Queen" with different IDs)
        if name.lower() in seen_names: continue
        seen_names.add(name.lower())
        
        candidates.append(art)
        seen_ids.add(aid)
        
        if len(candidates) >= 8: break
    
    # Now enrich data PARALLELY (Deezer + Last.fm)
    def enrich_artist(art):
        from api_clients import search_deezer_artists, get_lastfm_artist_data
        name = art.get('artistName', '')
        aid = art.get('artistId')
        
        # 1. Image and Stats (Deezer)
        dz = search_deezer_artists(name, 1)
        deezer_stats = None
        if dz:
            art['image'] = dz[0]['image']
            deezer_stats = dz[0].get('stats')
        else:
            from api_clients import get_true_artist_image
            art['image'] = get_true_artist_image(aid)
            
        # 2. Last.fm stats
        lf = get_lastfm_artist_data(name)
            # If Last.fm returned nothing, take Deezer stats
        art['stats'] = lf.get('stats') if lf and lf.get('stats') else deezer_stats
        return art

    with ThreadPoolExecutor() as executor:
        results['artists'] = list(executor.map(enrich_artist, candidates))[:6]
    
    # 2. Albums
    for alb in search_itunes(query, 'album', 15):
        if ql in (alb.get('collectionName', '') or '').lower():
            alb['artworkUrl100'] = alb.get('artworkUrl100', '').replace('100x100bb', '300x300bb')
            date = alb.get('releaseDate', '')
            alb['year'] = date[:4] if date else ''
            results['albums'].append(alb)
    results['albums'] = results['albums'][:6]
    
    # 3. Songs
    for song in search_itunes(query, 'song', 15):
        if ql in (song.get('trackName', '') or '').lower():
            q = f"{song.get('artistName', '')} {song.get('trackName', '')}"
            song['spotify_link'] = generate_spotify_link(q)
            song['youtube_link'] = generate_youtube_link(q)
            results['songs'].append(song)
    results['songs'] = results['songs'][:6]
        
    rendered = render_template('index.html', view='results', data=results, query=query)
    cache.set(cache_key, rendered, timeout=1800)  # Cache for 30 minutes
    return rendered

@search_bp.route('/see-all/<type>')
def see_all(type):
    query = request.args.get('q')
    if not query: return "No query provided", 400
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    sort_by = request.args.get('sort', 'relevance')
    
    results = []
    ql = query.lower()
    
    entity_map = {'artists': 'musicArtist', 'albums': 'album', 'songs': 'song'}
    entity = entity_map.get(type, 'album')
    
    # Large limit for "See All" list
    data = search_itunes(query, entity, 200)  # Increased limit to support pagination
    
    seen_ids = set()
    seen_names = set()
    
    for item in data:
        if type == 'artists':
            aid = item.get('artistId')
            name = item.get('artistName', '')
            
            if not aid or aid in seen_ids: continue
            if ql not in (name or "").lower(): continue

            if name.lower() in seen_names: continue
            seen_names.add(name.lower())

            # IMPORTANT: image = None here. Images will load via JS (Lazy Loading)
            item['image'] = None
            results.append(item)
            seen_ids.add(aid)
            
        elif type == 'albums':
            if item.get('collectionName') and ql in item.get('collectionName', '').lower():
                item['artworkUrl100'] = item.get('artworkUrl100', '').replace('100x100bb', '300x300bb')
                date = item.get('releaseDate', '')
                item['year'] = date[:4] if date else ''
                results.append(item)
                
        elif type == 'songs':
            if item.get('trackName') and ql in item.get('trackName', '').lower():
                item['spotify_link'] = generate_spotify_link(f"{item.get('artistName')} {item.get('trackName')}")
                results.append(item)

    # Apply sorting
    if sort_by == 'name':
        if type == 'artists':
            results.sort(key=lambda x: x.get('artistName', '').lower())
        elif type == 'albums':
            results.sort(key=lambda x: x.get('collectionName', '').lower())
        elif type == 'songs':
            results.sort(key=lambda x: x.get('trackName', '').lower())
    elif sort_by == 'year' and type in ['albums', 'songs']:
        results.sort(key=lambda x: x.get('releaseDate', '')[:4], reverse=True)
    # Default 'relevance' - no sorting, keep original order

    # Apply pagination
    total_results = len(results)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_results = results[start:end]
    
    has_next = end < total_results
    has_prev = page > 1
    
    return render_template('index.html', view='see_all', results=paginated_results, type=type, query=query, 
                          page=page, per_page=per_page, has_next=has_next, has_prev=has_prev, total=total_results, sort_by=sort_by)

@search_bp.route('/tag/<encoded_tag>')
def tag_page(encoded_tag):
    from urllib.parse import unquote
    from api_clients import get_tag_info, get_tag_artists
    
    decoded_tag = unquote(encoded_tag)
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort', 'popularity')
    
    # Use decoded_tag for requests
    description = get_tag_info(decoded_tag)
    artists = get_tag_artists(decoded_tag, page, 30)
    
    if sort_by == 'alpha':
        artists.sort(key=lambda x: x['artistName'].lower())
    else:
        artists.sort(key=lambda x: x['listeners'], reverse=True)
        
    return render_template('index.html', 
                           view='tag_detail', 
                           tag_name=decoded_tag,  # Pass the clean name
                           description=description, 
                           artists=artists, 
                           page=page, 
                           sort_by=sort_by)