from app import app, db
from models import User, Playlist, PlaylistItem
import os

def test_playlist_render():
    with app.app_context():
        # Get any playlist
        playlist = Playlist.query.first()
        if not playlist:
            print("No playlist found to test.")
            return
            
        print(f"Testing render for playlist: {playlist.name} (ID: {playlist.id})")
        try:
            from flask import render_template
            # Mocking loop/request context if needed
            with app.test_request_context():
                html = render_template('index.html', view='playlist_detail', playlist=playlist)
                print("Render successful!")
        except Exception as e:
            import traceback
            print("Render failed!")
            traceback.print_exc()

if __name__ == "__main__":
    test_playlist_render()
