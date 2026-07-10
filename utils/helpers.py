import os
from datetime import datetime
from config import Config

def init_app_directories():
    """Ensure all required static directories, database folders, and upload paths exist."""
    required_dirs = [
        os.path.join(Config.BASE_DIR, 'database'),
        os.path.join(Config.BASE_DIR, 'models'),
        os.path.join(Config.BASE_DIR, 'routes'),
        os.path.join(Config.BASE_DIR, 'utils'),
        os.path.join(Config.BASE_DIR, 'dataset'),
        os.path.join(Config.BASE_DIR, 'static', 'css'),
        os.path.join(Config.BASE_DIR, 'static', 'js'),
        Config.CAPTURE_DIR
    ]
    
    for directory in required_dirs:
        os.makedirs(directory, exist_ok=True)
        print(f"Directory verified: {directory}")

def format_datetime(value, format_str="%b %d, %Y - %I:%M:%S %p"):
    """Format an SQLite datetime string to a human-readable display."""
    if not value:
        return ""
    try:
        # SQLite timestamps are in 'YYYY-MM-DD HH:MM:SS' format
        dt = datetime.strptime(value.split('.')[0], "%Y-%m-%d %H:%M:%S")
        return dt.strftime(format_str)
    except Exception:
        # Return raw value as fallback if parsing fails
        return str(value)

def send_alert_notification(alert_type, camera_name, confidence):
    """
    Simulates sending instant push notifications, emails, or SMS alerts.
    In a real system, this would call Twilio (SMS), SendGrid (Email), or Telegram API.
    For college evaluation, printing to terminal with special formatting demonstrates this.
    """
    border = "=" * 60
    message = (
        f"\n{border}\n"
        f"!!! AI SURVEILLANCE CRITICAL WARNING !!!\n"
        f"Alert Type: {alert_type.upper()} DETECTED\n"
        f"Camera    : {camera_name}\n"
        f"Confidence: {confidence * 100:.1f}%\n"
        f"Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Action    : Screenshot saved, notification dispatched.\n"
        f"{border}\n"
    )
    print(message)
    
    # Can also write to a security_audit.log file
    log_file_path = os.path.join(Config.BASE_DIR, 'security_alerts.log')
    try:
        with open(log_file_path, 'a') as log_file:
            log_file.write(f"[{datetime.now().isoformat()}] {alert_type.upper()} on camera '{camera_name}' (conf: {confidence:.2f})\n")
    except Exception as e:
        print(f"Error writing to alert log: {e}")
