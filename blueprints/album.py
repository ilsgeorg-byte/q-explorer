from flask import Blueprint, render_template
from api_clients import lookup_itunes, get_lastfm_album_stats
from utils import generate_spotify_link, generate_youtube_link

album_bp = Blueprint('album', __name__)

@album_bp.route('/album/<collection_id>')
def album_page(collection_id):
    # Increase limit to 200 as box sets can have many tracks
    data = lookup_itunes(collection_id, 'song', 200)
    if not data: return "Album not found"
    
    album_info = data[0]
    album_info['artworkUrl100'] = album_info.get('artworkUrl100', '').replace('100x100bb', '600x600bb')
    
    date = album_info.get('releaseDate', '')
    album_info['year'] = date[:4] if date else ''
    
    album_stats = get_lastfm_album_stats(album_info.get('artistName'), album_info.get('collectionName'))
    spotify_link = generate_spotify_link(f"{album_info.get('artistName')} {album_info.get('collectionName')}")
    youtube_link = generate_youtube_link(f"{album_info.get('artistName')} {album_info.get('collectionName')}")
    
    # Sort by disc and track number (important for box sets)
    songs = data
    songs.sort(key=lambda x: (x.get('discNumber', 1), x.get('trackNumber', 1)))
            
    return render_template('index.html', view='album_detail', album=album_info, songs=songs, spotify_link=spotify_link, youtube_link=youtube_link, album_stats=album_stats)