import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-very-safe'
    
    # Database
    database_url = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')
    if not database_url:
        if os.name == 'nt':  # Windows local
            database_url = 'sqlite:///instance/users.db'
        else:
            database_url = 'sqlite:///tmp/users.db'
    else:
        database_url = database_url.replace('postgres://', 'postgresql://')
    
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session
    SESSION_COOKIE_SECURE = False if os.name == 'nt' else True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Cache
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 3600