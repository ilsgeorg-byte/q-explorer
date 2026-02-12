from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        print(f"Connecting to: {app.config['SQLALCHEMY_DATABASE_URI']}")
        try:
            # Check if column exists first (different for SQLite vs Postgres but ALTER works for both)
            db.session.execute(text('ALTER TABLE playlist_item ADD COLUMN position INTEGER DEFAULT 0'))
            db.session.commit()
            print("Successfully added 'position' column to 'playlist_item' table.")
        except Exception as e:
            db.session.rollback()
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("Column 'position' already exists.")
            else:
                print(f"Migration error: {e}")

if __name__ == "__main__":
    migrate()
