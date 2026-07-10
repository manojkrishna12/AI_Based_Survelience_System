import os

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'surveillance_secret_key_123_btech_project')
    
    # Base directory of the application
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # SQLite Database configuration
    DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'surveillance.db')
    SCHEMA_PATH = os.path.join(BASE_DIR, 'database', 'schema.sql')
    
    # Detection configuration
    CAPTURE_DIR = os.path.join(BASE_DIR, 'static', 'captures')
    
    # Make sure captures directory exists
    os.makedirs(CAPTURE_DIR, exist_ok=True)
    
    # Confidence thresholds
    YOLO_CONFIDENCE_THRESHOLD = 0.5
    FACE_CONFIDENCE_THRESHOLD = 0.5
    MOTION_THRESHOLD = 15  # Minimum contour area for motion detection
    
    # Alert Throttle (minimum seconds between alerts of the same type for a camera to prevent spamming)
    ALERT_THROTTLE_SECONDS = 10
    
    # Camera fallbacks
    ALLOW_VIRTUAL_FEED_FALLBACK = True
