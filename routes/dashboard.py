from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from routes.auth import login_required
from database.database import (
    get_dashboard_stats, get_recent_alerts, delete_alert, 
    get_all_cameras, add_camera, delete_camera, update_camera, get_camera_by_id
)

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Render the dashboard UI containing high-level stats."""
    stats = get_dashboard_stats()
    recent = get_recent_alerts(limit=5)
    cameras = get_all_cameras()
    return render_template('dashboard.html', stats=stats, recent_alerts=recent, cameras=cameras)

@dashboard_bp.route('/api/stats')
@login_required
def api_stats():
    """Return dashboard analytics in JSON format for dynamic JS graphs."""
    stats = get_dashboard_stats()
    return jsonify(stats)

@dashboard_bp.route('/api/recent_alerts')
@login_required
def api_recent_alerts():
    """Fetch 10 most recent alerts for dynamic scrolling widgets."""
    limit = request.args.get('limit', 10, type=int)
    recent = get_recent_alerts(limit=limit)
    return jsonify(recent)

@dashboard_bp.route('/alerts')
@login_required
def alerts_history():
    """Render the historical alert records page with filtering option."""
    alert_type = request.args.get('type')
    camera_id = request.args.get('camera_id', type=int)
    
    cameras = get_all_cameras()
    alerts = get_recent_alerts(limit=100, alert_type=alert_type, camera_id=camera_id)
    
    return render_template(
        'alerts.html', 
        alerts=alerts, 
        cameras=cameras, 
        selected_type=alert_type, 
        selected_camera=camera_id
    )

@dashboard_bp.route('/alerts/delete/<int:alert_id>', methods=['POST'])
@login_required
def remove_alert(alert_id):
    """Delete an alert record and its captured picture."""
    delete_alert(alert_id)
    flash("Alert record deleted successfully.", "success")
    return redirect(url_for('dashboard.alerts_history'))

@dashboard_bp.route('/cameras')
@login_required
def cameras_manage():
    """Render camera management list."""
    cameras = get_all_cameras()
    return render_template('cameras_manage.html', cameras=cameras)

@dashboard_bp.route('/cameras/add', methods=['POST'])
@login_required
def camera_add():
    """Register a new camera device or stream."""
    name = request.form.get('name', '').strip()
    source = request.form.get('source', '').strip()
    status = request.form.get('status', 'active')
    
    if not name or not source:
        flash("Name and Source are required.", "danger")
        return redirect(url_for('dashboard.cameras_manage'))
        
    add_camera(name, source, status)
    flash("New camera added successfully.", "success")
    return redirect(url_for('dashboard.cameras_manage'))

@dashboard_bp.route('/cameras/edit/<int:camera_id>', methods=['POST'])
@login_required
def camera_edit(camera_id):
    """Update configurations of a registered camera."""
    name = request.form.get('name', '').strip()
    source = request.form.get('source', '').strip()
    status = request.form.get('status', 'active')
    
    if not name or not source:
        flash("All fields are required.", "danger")
        return redirect(url_for('dashboard.cameras_manage'))
        
    update_camera(camera_id, name, source, status)
    flash("Camera updated successfully.", "success")
    return redirect(url_for('dashboard.cameras_manage'))

@dashboard_bp.route('/cameras/delete/<int:camera_id>', methods=['POST'])
@login_required
def camera_delete(camera_id):
    """Remove a camera registration and cleanup active connections."""
    # Note: Detector dictionary cleanup happens on route call or stream termination.
    delete_camera(camera_id)
    flash("Camera deleted successfully.", "success")
    return redirect(url_for('dashboard.cameras_manage'))
