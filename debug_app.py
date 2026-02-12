
from app import app, db
from flask import url_for
import traceback

def test_page(path, name):
    print(f"\n--- Testing {name} ({path}) ---")
    with app.test_client() as client:
        try:
            response = client.get(path)
            if response.status_code == 200:
                print(f"SUCCESS: {name} is OK")
            else:
                print(f"FAILED: {name} returned status {response.status_code}")
                # If it's 500, we might not get the traceback here, 
                # but let's see the data
                if response.status_code == 500:
                    print("Error content snippet:")
                    print(response.data.decode('utf-8')[:500])
        except Exception:
            print(f"EXCEPTION during {name}:")
            traceback.print_exc()

def login_test_user(client):
    from models import User
    user = User.query.first()
    if not user:
        return False
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True
    return user

def create_sample_playlist(user):
    from models import Playlist, PlaylistItem, db
    # Check if exists
    p = Playlist.query.filter_by(user_id=user.id, name="Test Playlist").first()
    if not p:
        p = Playlist(user_id=user.id, name="Test Playlist")
        db.session.add(p)
        db.session.commit()
        item = PlaylistItem(playlist_id=p.id, track_id="test|123", title="Test Track", artist_name="Test Artist")
        db.session.add(item)
        db.session.commit()
    return p

if __name__ == "__main__":
    with app.app_context():
        # 1. Check DB
        print("Checking tables...")
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        print("Tables found:", inspector.get_table_names())
        
        with app.test_client() as client:
            print("Logging in...")
            user = login_test_user(client)
            if user:
                # 2. Test routes
                print("\n--- Testing Home Page (/) ---")
                res = client.get('/')
                print(f"Status: {res.status_code}")
                
                print("\n--- Testing Playlists Page (/playlists) ---")
                res = client.get('/playlists')
                print(f"Status: {res.status_code}")
                
                print("\n--- Testing Registration POST ---")
                res = client.post('/register', data={
                    'username': 'newuser',
                    'email': 'new@example.com',
                    'password': 'password123'
                })
                print(f"Status: {res.status_code}")
                if res.status_code == 500:
                    print(res.data.decode('utf-8')[:1000])

                print("\n--- Creating Sample Playlist ---")
                p = create_sample_playlist(user)
                
                print(f"\n--- Testing Playlist Detail (/playlist/{p.id}) ---")
                res = client.get(f'/playlist/{p.id}')
                print(f"Status: {res.status_code}")
                if res.status_code == 500:
                    print(res.data.decode('utf-8')[:1000])
            else:
                print("No user found to login.")
                
    print("\n--- Diagnostic Finished ---")
