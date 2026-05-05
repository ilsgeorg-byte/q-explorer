from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Favorite, Playlist, PlaylistItem
from api_clients import search_itunes
import requests
from urllib.parse import quote

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('search.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('auth.register'))
            
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        return redirect(url_for('search.index'))
        
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('search.index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            return redirect(url_for('search.index'))
        else:
            flash('Invalid email or password')
            
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('search.index'))

@auth_bp.route('/profile')
@login_required
def profile():
    # Load favorites and playlists
    fav_artists = Favorite.query.filter_by(user_id=current_user.id, type='artist').all()
    fav_albums = Favorite.query.filter_by(user_id=current_user.id, type='album').all()
    fav_tracks = Favorite.query.filter_by(user_id=current_user.id, type='song').all()
    playlists = Playlist.query.filter_by(user_id=current_user.id).all()
    
    return render_template('index.html', view='profile', user=current_user, 
                           fav_artists=fav_artists, 
                           fav_albums=fav_albums, 
                           fav_tracks=fav_tracks,
                           playlists=playlists)

@auth_bp.route('/favorites')
@login_required
def favorites():
    # Load favorites and playlists
    fav_artists = Favorite.query.filter_by(user_id=current_user.id, type='artist').all()
    fav_albums = Favorite.query.filter_by(user_id=current_user.id, type='album').all()
    fav_tracks = Favorite.query.filter_by(user_id=current_user.id, type='song').all()
    playlists = Playlist.query.filter_by(user_id=current_user.id).all()
    
    return render_template('index.html', view='favorites',
                           fav_artists=fav_artists, 
                           fav_albums=fav_albums, 
                           fav_tracks=fav_tracks,
                           playlists=playlists)

@auth_bp.route('/playlists')
@login_required
def playlists():
    user_playlists = Playlist.query.filter_by(user_id=current_user.id).order_by(Playlist.created_at.desc()).all()
    return render_template('index.html', view='playlists', playlists=user_playlists)

@auth_bp.route('/playlist/<int:playlist_id>')
@login_required
def playlist_detail(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)
    if playlist.user_id != current_user.id:
        return "Access denied", 403
    
    if request.args.get('json'):
        return jsonify({
            'id': playlist.id,
            'name': playlist.name,
            'tracks': [{
                'id': item.id,
                'track_id': item.track_id,
                'title': item.title,
                'artist_name': item.artist_name,
                'image_url': item.image_url
            } for item in playlist.items]
        })
    
    return render_template('index.html', view='playlist_detail', playlist=playlist)

@auth_bp.route('/api/favorite', methods=['POST'])
@login_required
def toggle_favorite():
    data = request.json
    item_type = data.get('type')
    item_id = data.get('id')
    
    if not item_type or not item_id:
        return jsonify({'error': 'Missing data'}), 400
        
    # Check if already in favorites
    existing = Favorite.query.filter_by(user_id=current_user.id, type=item_type, item_id=item_id).first()
    
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'status': 'removed'})
    else:
        new_fav = Favorite(user_id=current_user.id, type=item_type, item_id=item_id)
        db.session.add(new_fav)
        db.session.commit()
        return jsonify({'status': 'added'})

@auth_bp.route('/api/check_favorites')
@login_required
def check_favorites():
    favs = Favorite.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'type': f.type,
        'item_id': f.item_id
    } for f in favs])

@auth_bp.route('/api/playlists/create', methods=['POST'])
@login_required
def create_playlist():
    data = request.json
    name = data.get('name')
    description = data.get('description', '')
    
    if not name:
        return jsonify({'error': 'Name is required'}), 400
        
    new_playlist = Playlist(user_id=current_user.id, name=name, description=description)
    db.session.add(new_playlist)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'playlist': {
            'id': new_playlist.id,
            'name': new_playlist.name
        }
    })

@auth_bp.route('/api/playlists/recommendations/<int:playlist_id>')
@login_required
def get_playlist_recommendations(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)
    if playlist.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
        
    if not playlist.items:
        return jsonify([])
        
    # Get unique artists from playlist
    artists = list(set([item.artist_name for item in playlist.items]))
    if not artists: return jsonify([])
    base_artist = artists[0]
    
    # Search similar tracks via iTunes
    url = f"https://itunes.apple.com/search?term={quote(base_artist)}&entity=song&limit=10"
    try:
        res = requests.get(url, timeout=5).json()
        tracks = []
        existing_ids = set([i.track_id.split('|')[-1] for i in playlist.items])
        
        for r in res.get('results', []):
            tid = str(r.get('trackId'))
            if tid not in existing_ids:
                tracks.append({
                    'id': tid,
                    'title': r.get('trackName'),
                    'artist': r.get('artistName'),
                    'album': r.get('collectionName'),
                    'img': r.get('artworkUrl100'),
                    'albumId': r.get('collectionId')
                })
        return jsonify(tracks[:5])
    except Exception as e:
        print(f"Rec error: {e}")
        return jsonify([])

@auth_bp.route('/api/playlists/add-track', methods=['POST'])
@login_required
def add_to_playlist():
    data = request.json
    playlist_id = data.get('playlist_id')
    track_data = data.get('track') # {id, title, artist, img}
    
    if not playlist_id or not track_data:
        return jsonify({'error': 'Missing data'}), 400
        
    playlist = Playlist.query.get_or_404(playlist_id)
    if playlist.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
        
    # Combined ID to store album reference: "albumId|trackId"
    stored_id = f"{track_data.get('albumId', '')}|{track_data['id']}" if track_data.get('albumId') else str(track_data['id'])

    # Check for existing item
    existing = PlaylistItem.query.filter_by(playlist_id=playlist_id, track_id=stored_id).first()
    if existing:
        return jsonify({'status': 'already_exists'})
        
    new_item = PlaylistItem(
        playlist_id=playlist_id,
        track_id=stored_id,
        title=track_data['title'],
        artist_name=track_data.get('artist'),
        image_url=track_data.get('img')
    )
    db.session.add(new_item)
    db.session.commit()
    
    return jsonify({'status': 'added'})

@auth_bp.route('/api/playlists/remove-track', methods=['POST'])
@login_required
def remove_from_playlist():
    data = request.json
    playlist_id = data.get('playlist_id')
    track_id = str(data.get('track_id'))
    
    item = PlaylistItem.query.filter_by(playlist_id=playlist_id, track_id=track_id).first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404
        
    if item.playlist.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
        
    db.session.delete(item)
    db.session.commit()
    
    return jsonify({'status': 'removed'})

@auth_bp.route('/api/playlists/delete/<int:playlist_id>', methods=['POST'])
@login_required
def delete_playlist(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)
    if playlist.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
        
    db.session.delete(playlist)
    db.session.commit()
    
    return jsonify({'status': 'deleted'})

@auth_bp.route('/api/playlists/reorder', methods=['POST'])
@login_required
def reorder_playlist():
    data = request.json
    playlist_id = data.get('playlist_id')
    new_order = data.get('order') # List of PlaylistItem.id
    
    if not playlist_id or not new_order:
        return jsonify({'error': 'Missing data'}), 400
        
    playlist = Playlist.query.get_or_404(playlist_id)
    if playlist.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
        
    # Update positions based on the order list
    # new_order is a list of PlaylistItem IDs in the new order
    for index, item_id in enumerate(new_order):
        item = PlaylistItem.query.get(item_id)
        if item and item.playlist_id == playlist.id:
            item.position = index
            
    db.session.commit()
    return jsonify({'status': 'success'})

@auth_bp.route('/api/playlists/list')
@login_required
def list_playlists_api():
    user_playlists = Playlist.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'count': len(p.items)
    } for p in user_playlists])