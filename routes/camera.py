from flask import Blueprint, render_template, Response, request, jsonify
from routes.auth import login_required
from models.detector import SurveillanceDetector
from database.database import get_camera_by_id, get_all_cameras
import os
import cv2
import time
from datetime import datetime
from config import Config

camera_bp = Blueprint('camera', __name__)

# Cache active detector instances: camera_id -> SurveillanceDetector
active_detectors = {}

def get_or_create_detector(camera_id):
    """Retrieve existing detector or create a new instance for a camera."""
    global active_detectors
    
    # Check if detector already exists
    if camera_id in active_detectors:
        # Check if the camera device status is still open (for real physical cameras)
        detector = active_detectors[camera_id]
        if not detector.is_simulated and (detector.cap is None or not detector.cap.isOpened()):
            # Recreate if it got disconnected
            try:
                detector.release()
            except:
                pass
            cam_data = get_camera_by_id(camera_id)
            if cam_data:
                active_detectors[camera_id] = SurveillanceDetector(camera_id, cam_data['source'])
        return active_detectors[camera_id]
        
    # Instantiate new detector
    cam_data = get_camera_by_id(camera_id)
    if not cam_data:
        return None
        
    print(f"Initializing AI Surveillance Detector for Camera: {cam_data['name']} (Source: {cam_data['source']})")
    detector = SurveillanceDetector(camera_id, cam_data['source'])
    active_detectors[camera_id] = detector
    return detector

def generate_feed(detector, camera_id):
    """Generator to yield MJPEG video frames with boundaries."""
    try:
        while True:
            try:
                frame_bytes = detector.get_frame_bytes()
                if frame_bytes is None:
                    time.sleep(0.1)
                    continue
                    
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                # Control frame rate slightly (~20 FPS) to reduce CPU overhead
                time.sleep(0.04)
            except Exception as e:
                print(f"Error in stream generator: {e}")
                break
    except GeneratorExit:
        print(f"Client disconnected from camera {camera_id}; releasing detector resources.")
    finally:
        if camera_id in active_detectors and active_detectors[camera_id] is detector:
            try:
                detector.release()
            except Exception as e:
                print(f"Error releasing detector for camera {camera_id}: {e}")
            active_detectors.pop(camera_id, None)

@camera_bp.route('/camera/<int:camera_id>')
@login_required
def view_camera(camera_id):
    """Render the individual camera live stream screen."""
    camera = get_camera_by_id(camera_id)
    if not camera:
        return "Camera not found", 404
        
    detector = get_or_create_detector(camera_id)
    all_cameras = get_all_cameras()
    
    # Pass current detection toggles to the UI to set initial button states
    states = {
        'human': detector.enable_human if detector else True,
        'face': detector.enable_face if detector else True,
        'motion': detector.enable_motion if detector else False,
        'intrusion': detector.enable_intrusion if detector else False,
        'fire': detector.enable_fire if detector else False
    }
    
    return render_template('camera.html', camera=camera, cameras=all_cameras, states=states)

@camera_bp.route('/camera/video_feed/<int:camera_id>')
@login_required
def video_feed(camera_id):
    """Retrieve JPEG frame bytes as an MJPEG stream."""
    detector = get_or_create_detector(camera_id)
    if not detector:
        return "Detector initialization failed", 500
        
    return Response(
        generate_feed(detector, camera_id),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@camera_bp.route('/camera/toggle_detector/<int:camera_id>', methods=['POST'])
@login_required
def toggle_detector(camera_id):
    """Toggle detection algorithms dynamically from the UI checkbox toggles."""
    detector = get_or_create_detector(camera_id)
    if not detector:
        return jsonify({'success': False, 'message': 'Detector not found'}), 404
        
    data = request.json
    feature = data.get('feature')
    enabled = data.get('enabled', False)
    
    if feature == 'human':
        detector.enable_human = enabled
    elif feature == 'face':
        detector.enable_face = enabled
    elif feature == 'motion':
        detector.enable_motion = enabled
        # Clear previous frame reference when enabling motion to reset background model
        if enabled:
            detector.prev_frame = None
    elif feature == 'intrusion':
        detector.enable_intrusion = enabled
    elif feature == 'fire':
        detector.enable_fire = enabled
    else:
        return jsonify({'success': False, 'message': 'Invalid feature'}), 400
        
    return jsonify({
        'success': True, 
        'feature': feature, 
        'enabled': enabled, 
        'message': f"Feature '{feature}' toggled successfully."
    })

@camera_bp.route('/camera/capture_screenshot/<int:camera_id>', methods=['POST'])
@login_required
def capture_screenshot(camera_id):
    """Capture a manual high-resolution screenshot and log it in SQLite."""
    detector = get_or_create_detector(camera_id)
    if not detector:
        return jsonify({'success': False, 'message': 'Detector not found'}), 404
        
    # Grab a fresh frame from the feed
    if detector.is_simulated:
        frame = detector.generate_simulated_frame()
    else:
        # Read from active capture device
        ret, frame = detector.cap.read()
        if not ret:
            frame = detector.generate_simulated_frame()
            
    # Save the screenshot immediately
    # We call trigger_alert directly with type 'Manual' and 1.0 confidence
    # To bypass cooling periods and log immediately, we update last alert time manually
    detector.last_alert_times['Manual'] = 0 # Force save
    detector.trigger_alert('Manual', 1.0, frame)
    
    return jsonify({
        'success': True,
        'message': 'Screenshot captured and logged in detection history.'
    })

def release_all_detectors():
    """Cleanup and release camera resources on server shutdown."""
    global active_detectors
    for cam_id, detector in list(active_detectors.items()):
        try:
            detector.release()
            print(f"Released camera detector resources for camera ID {cam_id}")
        except Exception as e:
            print(f"Error releasing camera ID {cam_id}: {e}")
    active_detectors.clear()
