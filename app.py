import os
import atexit
import signal
from flask import Flask, redirect, url_for
from config import Config
from database.database import init_db
from utils.helpers import init_app_directories, format_datetime
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.camera import camera_bp, release_all_detectors

def create_app():
    """Application factory for initialization."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # 1. Initialize Directories on bootup
    init_app_directories()

    # 2. Initialize Database on bootup
    init_db()

    # 3. Register custom Jinja2 template filters
    app.template_filter('format_datetime')(format_datetime)

    # 4. Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(camera_bp)

    # Root route redirect to dashboard
    @app.route('/')
    def root():
        return redirect(url_for('dashboard.index'))

    return app

app = create_app()

# Register teardown function to release webcam captures on shutdown
@atexit.register
def shutdown():
    print("Shutting down surveillance server...")
    release_all_detectors()


def handle_shutdown(signum, frame):
    print("Received shutdown signal, cleaning up camera resources...")
    release_all_detectors()
    raise SystemExit(0)


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

if __name__ == '__main__':
    # We turn use_reloader=False off because Flask's default reloader runs the script 
    # twice in two processes, which can lock the webcam resources.
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
