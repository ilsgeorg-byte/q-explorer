
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

if __name__ == "__main__":
    with app.app_context():
        # 1. Check DB
        print("Checking tables...")
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        print("Tables found:", inspector.get_table_names())
        
        # 2. Test routes
        test_page('/', 'Home Page')
        test_page('/login', 'Login Page')
        test_page('/register', 'Register Page')
        
    print("\n--- Diagnostic Finished ---")
