import re
import urllib.parse

def clean_name_for_search(text):
    if not text: return ""
    text = re.sub(r'\s*\(.*?\)', '', text)
    text = re.sub(r'\s*\[.*?\]', '', text)
    text = re.sub(r'(?i)\s(deluxe|remastered|expanded|anniversary)\s+edition', '', text)
    return text.strip()

def generate_spotify_link(query):
    return f"https://open.spotify.com/search/{urllib.parse.quote(query)}"

def sort_albums(albums_list):
    categorized = {'albums': [], 'singles': [], 'live': [], 'compilations': []}
    seen = set()
    for alb in albums_list:
        if alb['collectionName'] in seen: continue
        seen.add(alb['collectionName'])
        alb['artworkUrl100'] = alb.get('artworkUrl100', '').replace('100x100bb', '400x400bb')
        name = alb['collectionName'].lower()
        cnt = alb.get('trackCount', 0)
        
        if 'live' in name or 'concert' in name: categorized['live'].append(alb)
        elif 'greatest' in name or 'best of' in name or 'anthology' in name: categorized['compilations'].append(alb)
        elif cnt < 5 or 'single' in name or 'ep' in name: categorized['singles'].append(alb)
        else: categorized['albums'].append(alb)
    
    for k in categorized: categorized[k].sort(key=lambda x: x.get('releaseDate', ''), reverse=True)
    return categorized
