import sqlite3
import os
from werkzeug.security import generate_password_hash
from config import Config

def get_db_connection():
    """Establish a connection to the SQLite database."""
    # Ensure database directory exists
    db_dir = os.path.dirname(Config.DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Returns rows that behave like dicts
    return conn

def init_db():
    """Initialize database tables and seed default admin user and camera if empty."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Read schema file and execute
    if os.path.exists(Config.SCHEMA_PATH):
        with open(Config.SCHEMA_PATH, 'r') as f:
            cursor.executescript(f.read())
        conn.commit()
        print("Database schema loaded successfully.")
    else:
        print(f"Error: Schema file not found at {Config.SCHEMA_PATH}")
        conn.close()
        return

    # Seed Default User if not present
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        hashed_password = generate_password_hash("admin123")
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", hashed_password, "admin")
        )
        print("Default administrator seeded (admin / admin123).")
    
    # Seed Default Cameras if none exist
    cursor.execute("SELECT COUNT(*) FROM cameras")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO cameras (name, source, status) VALUES (?, ?, ?)",
            ("Primary Camera (Webcam 0)", "0", "active")
        )
        cursor.execute(
            "INSERT INTO cameras (name, source, status) VALUES (?, ?, ?)",
            ("Secondary Feed (Simulated)", "simulated", "active")
        )
        print("Default cameras seeded (Webcam 0 and Simulated Feed).")
        
    conn.commit()
    conn.close()

# --- User Database Helper Functions ---

def get_user_by_username(username):
    """Retrieve a user by username."""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return user

def create_user(username, password, role="operator"):
    """Create a new user with a hashed password."""
    conn = get_db_connection()
    hashed_pwd = generate_password_hash(password)
    try:
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, hashed_pwd, role)
        )
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success


# --- Camera Database Helper Functions ---

def get_all_cameras():
    """Retrieve all cameras."""
    conn = get_db_connection()
    cameras = conn.execute("SELECT * FROM cameras ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(cam) for cam in cameras]

def get_camera_by_id(camera_id):
    """Retrieve camera by ID."""
    conn = get_db_connection()
    camera = conn.execute("SELECT * FROM cameras WHERE id = ?", (camera_id,)).fetchone()
    conn.close()
    return dict(camera) if camera else None

def add_camera(name, source, status="active"):
    """Add a new camera feed."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO cameras (name, source, status) VALUES (?, ?, ?)",
        (name, source, status)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def update_camera(camera_id, name, source, status):
    """Update camera details."""
    conn = get_db_connection()
    conn.execute(
        "UPDATE cameras SET name = ?, source = ?, status = ? WHERE id = ?",
        (name, source, status, camera_id)
    )
    conn.commit()
    conn.close()

def delete_camera(camera_id):
    """Delete camera and its associated alerts."""
    conn = get_db_connection()
    conn.execute("DELETE FROM cameras WHERE id = ?", (camera_id,))
    conn.commit()
    conn.close()


# --- Alert Database Helper Functions ---

def log_alert(camera_id, alert_type, confidence, image_path):
    """Log a new security alert."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO alerts (camera_id, alert_type, confidence, image_path) VALUES (?, ?, ?, ?)",
        (camera_id, alert_type, confidence, image_path)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def get_recent_alerts(limit=10, alert_type=None, camera_id=None):
    """Retrieve recent alerts with filter options."""
    conn = get_db_connection()
    query = """
        SELECT alerts.*, cameras.name as camera_name 
        FROM alerts 
        LEFT JOIN cameras ON alerts.camera_id = cameras.id
    """
    conditions = []
    params = []
    
    if alert_type:
        conditions.append("alerts.alert_type = ?")
        params.append(alert_type)
    if camera_id:
        conditions.append("alerts.camera_id = ?")
        params.append(camera_id)
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += " ORDER BY alerts.created_at DESC LIMIT ?"
    params.append(limit)
    
    alerts = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(alert) for alert in alerts]

def delete_alert(alert_id):
    """Delete an alert from database."""
    conn = get_db_connection()
    # Get image path first to delete the file if needed
    alert = conn.execute("SELECT image_path FROM alerts WHERE id = ?", (alert_id,)).fetchone()
    if alert and alert['image_path']:
        full_path = os.path.join(Config.BASE_DIR, alert['image_path'].lstrip('/'))
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except Exception as e:
                print(f"Error removing alert image: {e}")
                
    conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()

def get_dashboard_stats():
    """Compile metrics for dashboard charts and widgets."""
    conn = get_db_connection()
    stats = {}
    
    # 1. Total Alert Counts
    stats['total_alerts'] = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    
    # 2. Alert Count by Type
    type_counts = conn.execute(
        "SELECT alert_type, COUNT(*) as count FROM alerts GROUP BY alert_type"
    ).fetchall()
    stats['alerts_by_type'] = {row['alert_type']: row['count'] for row in type_counts}
    
    # 3. Total Camera count (active/inactive)
    stats['total_cameras'] = conn.execute("SELECT COUNT(*) FROM cameras").fetchone()[0]
    stats['active_cameras'] = conn.execute("SELECT COUNT(*) FROM cameras WHERE status = 'active'").fetchone()[0]
    
    # 4. Hourly alert distributions for today (last 24 hours)
    # Using strftime to group by hour
    hourly_alerts = conn.execute(
        """SELECT strftime('%H', created_at) as hour, COUNT(*) as count 
           FROM alerts 
           WHERE created_at >= datetime('now', '-24 hours')
           GROUP BY hour 
           ORDER BY hour ASC"""
    ).fetchall()
    stats['hourly_distribution'] = {row['hour']: row['count'] for row in hourly_alerts}
    
    conn.close()
    return stats
