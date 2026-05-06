from flask import Blueprint, render_template, request, redirect, url_for
from api_clients import lookup_itunes, get_lastfm_artist_data, get_similar_artists, search_deezer_artists, get_true_artist_image, search_itunes
from utils import sort_albums
from concurrent.futures import ThreadPoolExecutor

artist_bp = Blueprint('artist', __name__)

@artist_bp.route('/artist/<artist_id>')
def artist_page(artist_id):
    # Cache artist page
    from flask import current_app
    cache = current_app.cache
    cache_key = f"artist_{artist_id}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    # First get basic info (fast, 1 request)
    data = lookup_itunes(artist_id)
    if not data: return "Artist not found"
    
    artist = data[0]
    artist_name = artist.get('artistName', '')
    
    # PARALLEL LOADING (ThreadPoolExecutor)
    # Start 5 heavy requests simultaneously
    with ThreadPoolExecutor() as executor:
        # 1. Last.fm Info
        future_lf = executor.submit(get_lastfm_artist_data, artist_name)
        # 2. Similar Artists
        future_sim = executor.submit(get_similar_artists, artist_name)
        # 3. Deezer Info
        future_dz = executor.submit(search_deezer_artists, artist_name, 1)
        # 4. Artist Image
        future_img = executor.submit(get_true_artist_image, artist_id)
        # 5. Get all discography (separate request)
        future_albums = executor.submit(lookup_itunes, artist_id, 'album', 200)
        
        lf = future_lf.result()
        similar = future_sim.result()
        dz = future_dz.result()
        artist_image = future_img.result()
        albums_data = future_albums.result()
    
    # Process Last.fm data
    if lf:
        artist['bio'] = lf.get('bio', '')
        artist['stats'] = lf.get('stats')
        artist['tags'] = lf.get('tags', [])
    
    # Process Deezer data
    deezer_data = dz[0] if dz else None
    if deezer_data:
        # If no Last.fm bio, use Deezer
        if not artist.get('bio') and deezer_data.get('bio'):
            artist['bio'] = deezer_data['bio']
        # If no image, use Deezer
        if not artist_image and deezer_data.get('image'):
            artist_image = deezer_data['image']
    
    # If Last.fm didn't provide stats, try Deezer
    if not artist.get('stats') and deezer_data:
        artist['stats'] = deezer_data.get('stats')
    
    # 2. Process Top Songs
    top_songs = []
    seen_titles = set()
    target_id = int(artist_id)
    target_name_lower = artist_name.lower()
    
    # Get songs from iTunes (limit 200 for box sets)
    songs_data = lookup_itunes(artist_id, 'song', 200)
    if songs_data:
        for song in songs_data:
            if song.get('artistId') == target_id or song.get('artistName', '').lower() == target_name_lower:
                title = song.get('trackName', '')
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    song['spotify_link'] = f"https://open.spotify.com/search/{artist_name} {title}".replace(' ', '%20')
                    song['youtube_link'] = f"https://www.youtube.com/results?search_query={artist_name} {title}".replace(' ', '+')
                    top_songs.append(song)
                    if len(top_songs) >= 10: break
    
    # 3. Process Discography (from separate albums request)
    raw_albums = [x for x in albums_data if x.get('collectionType') == 'Album'] if albums_data else []
    discography = sort_albums(raw_albums)
    
    rendered = render_template('index.html', view='artist_detail', artist=artist, discography=discography, artist_image=artist_image, similar=similar, top_songs=top_songs)
    cache.set(cache_key, rendered, timeout=3600)  # Cache for 1 hour
    return rendered

@artist_bp.route('/artist/<artist_id>/discography/<category>')
def artist_discography(artist_id, category):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    sort_by = request.args.get('sort', 'year')
    
    data = lookup_itunes(artist_id, 'album', 200)
    if not data:
        return "Artist not found", 404

    artist = data[0]
    raw_albums = [x for x in data if x.get('collectionType') == 'Album']
    discography = sort_albums(raw_albums)

    if category not in discography:
        return "Category not found", 404

    results = discography[category]
    
    # Apply sorting
    if sort_by == 'name':
        results.sort(key=lambda x: x.get('collectionName', '').lower())
    elif sort_by == 'year':
        results.sort(key=lambda x: x.get('releaseDate', '')[:4], reverse=True)
    # Default 'year' for discography
    
    # Apply pagination
    total_results = len(results)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_results = results[start:end]
    
    has_next = end < total_results
    has_prev = page > 1
    
    return render_template('index.html', view='artist_discography', results=paginated_results, type=category, query=artist.get('artistName', ''), artist=artist,
                          page=page, per_page=per_page, has_next=has_next, has_prev=has_prev, total=total_results, sort_by=sort_by)

@artist_bp.route('/redirect-artist')
def redirect_artist():
    name = request.args.get('name')
    if not name:
        return "Artist name required", 400

    # Search for the artist by name
    results = search_itunes(name, 'musicArtist', 1)
    if not results:
        return f"Artist '{name}' not found", 404

    artist_id = results[0].get('artistId')
    if not artist_id:
        return f"Artist '{name}' not found", 404

    return redirect(url_for('artist.artist_page', artist_id=artist_id))

@artist_bp.route('/artist/<artist_id>/similar')
def similar_artists(artist_id):
    """Show all similar artists for a given artist."""
    from flask import current_app
    
    # Get artist name first
    data = lookup_itunes(artist_id)
    if not data:
        return "Artist not found", 404
    
    artist_name = data[0].get('artistName', '')
    
    # Get similar artists
    similar = get_similar_artists(artist_name)
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Apply pagination
    total_results = len(similar) if similar else 0
    start = (page - 1) * per_page
    end = start + per_page
    paginated_results = similar[start:end] if similar else []
    
    has_next = end < total_results
    has_prev = page > 1
    
    return render_template('index.html', view='similar_artists', results=paginated_results, query=artist_name, artist_id=artist_id,
                          page=page, per_page=per_page, has_next=has_next, has_prev=has_prev, total=total_results)

@artist_bp.route('/artist/<artist_id>/top-songs')
def artist_top_songs(artist_id):
    """Show all top songs for a given artist."""
    from flask import current_app
    
    # Get artist name
    data = lookup_itunes(artist_id)
    if not data:
        return "Artist not found", 404
    
    artist_name = data[0].get('artistName', '')
    
    # Get all songs
    top_songs = []
    seen_titles = set()
    target_id = int(artist_id)
    target_name_lower = artist_name.lower()
    
    songs_data = lookup_itunes(artist_id, 'song', 200)
    if songs_data:
        for song in songs_data:
            if song.get('artistId') == target_id or song.get('artistName', '').lower() == target_name_lower:
                title = song.get('trackName', '')
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    song['spotify_link'] = f"https://open.spotify.com/search/{artist_name} {title}".replace(' ', '%20')
                    song['youtube_link'] = f"https://www.youtube.com/results?search_query={artist_name} {title}".replace(' ', '+')
                    top_songs.append(song)
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    sort_by = request.args.get('sort', 'popularity')
    
    # Apply sorting
    if sort_by == 'name':
        top_songs.sort(key=lambda x: x.get('trackName', '').lower())
    elif sort_by == 'popularity':
        # Keep original order (iTunes returns by popularity)
        pass
    # Default is popularity
    
    # Apply pagination
    total_results = len(top_songs)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_results = top_songs[start:end]
    
    has_next = end < total_results
    has_prev = page > 1
    
    return render_template('index.html', view='top_songs', results=paginated_results, query=artist_name, artist_id=artist_id,
                          page=page, per_page=per_page, has_next=has_next, has_prev=has_prev, total=total_results, sort_by=sort_by)