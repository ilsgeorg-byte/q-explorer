from flask import Flask, render_template, request, redirect, url_for
from api_clients import search_itunes, search_deezer_artists, lookup_itunes, get_true_artist_image, get_lastfm_artist_stats, get_lastfm_album_stats, get_similar_artists
from utils import generate_spotify_link, sort_albums

app = Flask(__name__)

@app.route('/')
def index():
    query = request.args.get('q')
    if not query:
        return render_template('index.html', view='home')
    
    results = {'artists': [], 'albums': [], 'songs': []}
    
    # 1. Artists (iTunes + Last.fm stats + iTunes image hack)
    for art in search_itunes(query, 'musicArtist', 4):
        if query.lower() in art.get('artistName', '').lower():
            art['image'] = get_true_artist_image(art.get('artistId'))
            art['stats'] = get_lastfm_artist_stats(art.get('artistName', ''))
            results['artists'].append(art)
    
    # 2. Albums
    for alb in search_itunes(query, 'album', 15):
        if query.lower() in alb.get('collectionName', '').lower():
            alb['artworkUrl100'] = alb.get('artworkUrl100', '').replace('100x100bb', '300x300bb')
            date = alb.get('releaseDate', '')
            alb['year'] = date[:4] if date else ''
            results['albums'].append(alb)
    results['albums'] = results['albums'][:8]
    
    # 3. Songs
    for song in search_itunes(query, 'song', 15):
        if query.lower() in song.get('trackName', '').lower():
            q = f"{song.get('artistName', '')} {song.get('trackName', '')}"
            song['spotify_link'] = generate_spotify_link(q)
            results['songs'].append(song)
    results['songs'] = results['songs'][:10]
        
    return render_template('index.html', view='results', data=results, query=query)

@app.route('/see-all/<type>') 
def see_all(type):
    query = request.args.get('q')
    if not query: return "No query provided", 400
        
    results = []
    
    if type == 'artists':
        # ИСПОЛЬЗУЕМ DEEZER ДЛЯ КАРТИНОК!
        deezer_data = search_deezer_artists(query, 30)
        results = deezer_data
    else:
        # iTunes для остального
        entity_map = {'albums': 'album', 'songs': 'song'}
        entity = entity_map.get(type, 'album')
        data = search_itunes(query, entity, 30)
        
        for item in data:
            if type == 'albums':
                if item.get('collectionName') and query.lower() in item.get('collectionName', '').lower():
                    item['artworkUrl100'] = item.get('artworkUrl100', '').replace('100x100bb', '300x300bb')
                    date = item.get('releaseDate', '')
                    item['year'] = date[:4] if date else ''
                    results.append(item)
            elif type == 'songs':
                if item.get('trackName') and query.lower() in item.get('trackName', '').lower():
                    item['spotify_link'] = generate_spotify_link(f"{item.get('artistName')} {item.get('trackName')}")
                    results.append(item)

    return render_template('index.html', view='see_all', results=results, type=type, query=query)

@app.route('/artist/<artist_id>')
def artist_page(artist_id):
    # ХАК: Если ID пришел от Deezer (он обычно короче или просто другой), iTunes его не найдет.
    # Пробуем найти сначала в iTunes напрямую
    data = lookup_itunes(artist_id)
    
    # Если не нашли по ID, возможно это ID от Deezer, но у нас нет имени...
    # В URL мы передаем только ID. 
    # В See All мы генерируем ссылку /artist/<deezer_id>.
    # Тут есть проблема: мы не знаем имя артиста, чтобы найти его iTunes ID.
    
    # РЕШЕНИЕ: В See All мы будем генерировать ссылку вида /artist/search:<name>
    # Если ID начинается с "search:", мы ищем по имени в iTunes.
    
    if str(artist_id).startswith('search:'):
        artist_name = artist_id.split(':', 1)[1]
        # Ищем в iTunes этого артиста
        search_res = search_itunes(artist_name, 'musicArtist', 1)
        if search_res:
            # Нашли! Перенаправляем на настоящий iTunes ID
            real_id = search_res[0]['artistId']
            return redirect(url_for('artist_page', artist_id=real_id))
        else:
            return "Artist not found in iTunes library", 404

    if not data: return "Artist not found"
    
    artist = data[0]
    artist['stats'] = get_lastfm_artist_stats(artist.get('artistName', ''))
    similar = get_similar_artists(artist.get('artistName', ''))
    
    raw_albums = [x for x in lookup_itunes(artist_id, 'album', 200) if x.get('collectionType') == 'Album' and x.get('artistId') == int(artist_id)]
    discography = sort_albums(raw_albums)
    
    artist_image = discography['albums'][0]['artworkUrl100'] if discography['albums'] else None
    
    return render_template('index.html', view='artist_detail', artist=artist, discography=discography, artist_image=artist_image, similar=similar)

@app.route('/album/<collection_id>')
def album_page(collection_id):
    data = lookup_itunes(collection_id, 'song')
    if not data: return "Album not found"
    
    album_info = data[0]
    album_info['artworkUrl100'] = album_info.get('artworkUrl100', '').replace('100x100bb', '600x600bb')
    
    # Год
    date = album_info.get('releaseDate', '')
    album_info['year'] = date[:4] if date else ''
    
    artist_name = album_info.get('artistName', '')
    collection_name = album_info.get('collectionName', '')
    
    album_stats = get_lastfm_album_stats(artist_name, collection_name)
    spotify_link = generate_spotify_link(f"{artist_name} {collection_name}")
    
    songs = []
    for item in data[1:]:
        if item.get('kind') == 'song':
            item['spotify_link'] = generate_spotify_link(f"{item.get('artistName')} {item.get('trackName')}")
            songs.append(item)
            
    return render_template('index.html', view='album_detail', album=album_info, songs=songs, spotify_link=spotify_link, album_stats=album_stats)

if __name__ == '__main__':
    app.run(debug=True)
