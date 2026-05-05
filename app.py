from flask import Flask
from flask_login import LoginManager
from flask_caching import Cache
from config import Config
from models import db, User
from blueprints.search import search_bp
from blueprints.artist import artist_bp
from blueprints.album import album_bp
from blueprints.api import api_bp
from blueprints.auth import auth_bp
import os

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
cache = Cache(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprints
app.register_blueprint(search_bp)
app.register_blueprint(artist_bp)
app.register_blueprint(album_bp)
app.register_blueprint(api_bp)
app.register_blueprint(auth_bp)

# Error Handlers
@app.errorhandler(500)
def internal_error(error):
    import traceback
    print("\n--- INTERNAL SERVER ERROR ---")
    traceback.print_exc()
    return "Internal Server Error (Check logs or terminal for details)", 500

try:
    with app.app_context():
        db.create_all()
        # Migration: Add 'position' column if it doesn't exist
        from sqlalchemy import text
        try:
            db.session.execute(text('ALTER TABLE playlist_item ADD COLUMN position INTEGER DEFAULT 0'))
            db.session.commit()
            print("Migration: Added 'position' column to playlist_item")
        except Exception:
            db.session.rollback()
except Exception as e:
    print(f"Database initialization error: {e}")

if __name__ == '__main__':
    print("\n" + "="*50)
    print("RUNNING ON PORT 5001 TO AVOID WINDOWS PORT COLLISION")
    print("OPEN THIS LINK: http://127.0.0.1:5001")
    print("="*50 + "\n")
    app.run(debug=True, port=5001)