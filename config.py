import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    TESTING = False
    
    # Camera settings
    CAMERA_INDEX = int(os.environ.get('CAMERA_INDEX', '0'))
    MAX_FACES = int(os.environ.get('MAX_FACES', '100'))
    FACE_RECOGNITION_TOLERANCE = float(os.environ.get('FACE_RECOGNITION_TOLERANCE', '0.5'))
    
    # File paths
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    STATIC_DIR = os.path.join(BASE_DIR, 'static')
    TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
    
    # Security settings
    SESSION_COOKIE_SECURE = not DEBUG
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # CORS settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # Performance settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    @staticmethod
    def init_app(app):
        """Initialize app with configuration"""
        app.config['SECRET_KEY'] = Config.SECRET_KEY
        app.config['DEBUG'] = Config.DEBUG
        app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH
        app.config['PERMANENT_SESSION_LIFETIME'] = Config.PERMANENT_SESSION_LIFETIME
        
        # Create directories if they don't exist
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        os.makedirs(Config.STATIC_DIR, exist_ok=True)
        os.makedirs(os.path.join(Config.DATA_DIR, 'temp'), exist_ok=True)

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    
    # Production-specific settings
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///face_recognition.db')
    REDIS_URL = os.environ.get('REDIS_URL', None)
    
    # Security headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block'
    }

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = True
    
    # Development settings
    DEVELOPMENT_DATABASE = 'sqlite:///face_recognition_dev.db'
