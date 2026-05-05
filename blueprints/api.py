from flask import Blueprint, jsonify, request
from api_clients import search_itunes, lookup_itunes, search_deezer_artists, get_true_artist_image
from utils import generate_spotify_link
import hashlib
import os
import requests

api_bp = Blueprint('api', __name__)

# Image caching function
def get_cached_image(url, cache_dir='static/cache'):
    if not url:
        return url
    
    # Create cache filename from URL hash
    url_hash = hashlib.md5(url.encode()).hexdigest()
    ext = url.split('.')[-1].split('?')[0]  # Get extension
    if ext not in ['jpg', 'jpeg', 'png', 'gif']:
        ext = 'jpg'
    cache_path = f"{cache_dir}/{url_hash}.{ext}"
    
    # Check if cached
    if os.path.exists(cache_path):
        return f"/{cache_path}"
    
    # Download and cache
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            with open(cache_path, 'wb') as f:
                f.write(response.content)
            return f"/{cache_path}"
    except:
        pass
    
    return url  # Fallback to original URL

@api_bp.route('/api/search-suggestions')
def api_search_suggestions():
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify([])
    
    # Get suggestions from iTunes API
    suggestions = []
    try:
        # Search for artists
        artists = search_itunes(query, 'musicArtist', 5)
        for artist in artists:
            name = artist.get('artistName', '')
            if name and query.lower() in name.lower():
                suggestions.append({'text': name, 'type': 'artist', 'id': artist.get('artistId')})
        
        # Search for albums
        albums = search_itunes(query, 'album', 5)
        for album in albums:
            name = album.get('collectionName', '')
            if name and query.lower() in name.lower():
                suggestions.append({'text': f"{name} - {album.get('artistName', '')}", 'type': 'album', 'id': album.get('collectionId')})
        
        # Limit to 8 suggestions
        suggestions = suggestions[:8]
        
    except Exception as e:
        print(f"Suggestions error: {e}")
    
    return jsonify(suggestions)

@api_bp.route('/api/get-artist-image/<artist_id>')
def api_get_artist_image(artist_id):
    # 1. First try Deezer (artist name required)
    try:
        data = lookup_itunes(artist_id)
        if data:
            name = data[0].get('artistName')
            if name:
                dz = search_deezer_artists(name, 1)
                if dz: 
                    cached_image = get_cached_image(dz[0]['image'])
                    return jsonify({'image': cached_image})
    except: pass

    # 2. If it fails — take from iTunes artwork
    image_url = get_true_artist_image(artist_id)
    if image_url:
        cached_image = get_cached_image(image_url)
        return jsonify({'image': cached_image})
    return jsonify({'image': None})

@api_bp.route('/api/get-artist-image-by-name')
def api_get_artist_image_by_name():
    name = request.args.get('name')
    if not name: return jsonify({'image': None})
    
    # 1. First try Deezer (faster and prettier)
    try:
        dz = search_deezer_artists(name, 1)
        if dz: 
            cached_image = get_cached_image(dz[0]['image'])
            return jsonify({'image': cached_image})
    except: pass
    
    # 2. If not, search in iTunes (via Artist ID -> Album)
    try:
        results = search_itunes(name, 'musicArtist', 1)
        if results:
            artist_id = results[0].get('artistId')
            img = get_true_artist_image(artist_id)
            if img: 
                cached_image = get_cached_image(img)
                return jsonify({'image': cached_image})
    except:
        pass

    # 3. Fallback: If no artist photo, take the cover of the first available album
    try:
        albums = search_itunes(name, 'album', 60)
        for alb in albums:
            if alb.get('artworkUrl100'):
                # Skip Donda and Vultures (often dark/empty covers)
                cname = alb.get('collectionName', '').lower()
                if 'donda' in cname or 'vultures' in cname: continue
                img_url = alb.get('artworkUrl100').replace('100x100bb', '300x300bb')
                cached_image = get_cached_image(img_url)
                return jsonify({'image': cached_image})
    except:
        pass
    
    return jsonify({'image': None})