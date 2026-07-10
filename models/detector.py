import os
import cv2
import numpy as np
import time
from datetime import datetime
from ultralytics import YOLO
from config import Config
from database.database import log_alert, get_camera_by_id
from utils.helpers import send_alert_notification

class SurveillanceDetector:
    def __init__(self, camera_id, camera_source):
        self.camera_id = camera_id
        self.camera_source = camera_source
        self.is_simulated = (camera_source == 'simulated')
        
        # Load YOLOv8 model (downloads yolov8n.pt if not present, ~6MB)
        try:
            self.model = YOLO('yolov8n.pt')
        except Exception as e:
            print(f"Error loading YOLOv8 model: {e}. Fallback to dummy classifications.")
            self.model = None

        # Load OpenCV Face Detector Haar Cascade
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        if self.face_cascade.empty():
            print("Warning: Haar cascade face XML not loaded correctly.")

        # Initialize video capture
        self.cap = None
        if not self.is_simulated:
            # Parse camera source (either integer index or stream path)
            try:
                src = int(camera_source)
            except ValueError:
                src = camera_source
                
            self.cap = cv2.VideoCapture(src)
            # Set resolution to 640x480 for better performance
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # Check if camera opens, otherwise fall back to simulation
            if not self.cap.isOpened():
                print(f"Warning: Camera source {camera_source} could not be opened. Falling back to simulation.")
                self.is_simulated = True

        # State for Motion Detection (background accumulation)
        self.prev_frame = None

        # Active detection models toggles
        self.enable_human = True
        self.enable_face = True
        self.enable_motion = False
        self.enable_intrusion = False
        self.enable_fire = False
        
        # Simulated states for moving targets
        self.sim_tick = 0
        
        # Intrusion zone configuration (Normalized coordinates)
        # Bounding box in middle of frame: X: 30% to 70%, Y: 30% to 80%
        self.intrusion_zone = {
            'x_min': 0.3, 'y_min': 0.3,
            'x_max': 0.7, 'y_max': 0.8
        }
        
        # Timestamp trackers for throttling alerts (to prevent database spam)
        self.last_alert_times = {
            'Human': 0,
            'Face': 0,
            'Motion': 0,
            'Intrusion': 0,
            'Fire/Smoke': 0
        }

    def trigger_alert(self, alert_type, confidence, frame):
        """Saves screenshot and writes alert record to SQLite if cooling period has passed."""
        now = time.time()
        time_elapsed = now - self.last_alert_times.get(alert_type, 0)
        
        if time_elapsed >= Config.ALERT_THROTTLE_SECONDS:
            self.last_alert_times[alert_type] = now
            
            # Format timestamp for files and records
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cam{self.camera_id}_{alert_type.replace('/', '_')}_{timestamp_str}.jpg"
            save_path = os.path.join(Config.CAPTURE_DIR, filename)
            
            # Write image to disk
            cv2.imwrite(save_path, frame)
            
            # DB relative path to render in templates
            relative_db_path = f"/static/captures/{filename}"
            
            # Insert alert entry in SQLite
            log_alert(
                camera_id=self.camera_id,
                alert_type=alert_type,
                confidence=float(confidence),
                image_path=relative_db_path
            )
            
            # Fetch camera name for the notification dispatch
            camera_name = "Camera Feed"
            try:
                cam = get_camera_by_id(self.camera_id)
                if cam:
                    camera_name = cam['name']
            except:
                pass
                
            send_alert_notification(alert_type, camera_name, float(confidence))

    def generate_simulated_frame(self):
        """Generates mock frames dynamically with drawing and overlays."""
        # Create a black frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.sim_tick += 1
        
        # Draw background elements
        cv2.rectangle(frame, (10, 10), (630, 470), (40, 30, 20), 2)
        cv2.putText(frame, "SIMULATED FEED: REAR DRIVEWAY", (30, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (240, 240, 240), 2)
        
        # Draw grid lines for a professional security feed style
        for y in range(80, 480, 80):
            cv2.line(frame, (10, y), (630, y), (30, 30, 30), 1)
        for x in range(80, 640, 80):
            cv2.line(frame, (x, 10), (x, 470), (30, 30, 30), 1)

        # Base pattern simulation
        t = self.sim_tick * 0.05
        
        # 1. Simulate Human walking
        # Person path is an ellipse
        h_x = int(320 + 200 * np.cos(t))
        h_y = int(240 + 100 * np.sin(t))
        
        # Only simulate person sometimes to make it dynamic
        if int(self.sim_tick / 200) % 2 == 0:
            # Draw a stick figure representing a person
            cv2.circle(frame, (h_x, h_y - 40), 12, (200, 200, 200), -1)  # Head
            cv2.line(frame, (h_x, h_y - 28), (h_x, h_y + 10), (200, 200, 200), 3)  # Torso
            cv2.line(frame, (h_x, h_y - 15), (h_x - 20, h_y - 5), (200, 200, 200), 2)  # Left Arm
            cv2.line(frame, (h_x, h_y - 15), (h_x + 20, h_y - 5), (200, 200, 200), 2)  # Right Arm
            cv2.line(frame, (h_x, h_y + 10), (h_x - 15, h_y + 40), (200, 200, 200), 2)  # Left Leg
            cv2.line(frame, (h_x, h_y + 10), (h_x + 15, h_y + 40), (200, 200, 200), 2)  # Right Leg
            
            # Store mock detection coordinates
            self.mock_person_box = (h_x - 30, h_y - 60, h_x + 30, h_y + 50)
        else:
            self.mock_person_box = None

        # 2. Simulate Face appearing in corner
        # Every 400 ticks, simulate close-up face detection
        if int(self.sim_tick / 150) % 3 == 1:
            f_x, f_y = 500, 120
            cv2.circle(frame, (f_x, f_y), 30, (230, 200, 180), -1)  # Face circle
            cv2.circle(frame, (f_x - 10, f_y - 8), 4, (40, 40, 255), -1)  # Eye L
            cv2.circle(frame, (f_x + 10, f_y - 8), 4, (40, 40, 255), -1)  # Eye R
            cv2.ellipse(frame, (f_x, f_y + 10), (12, 6), 0, 0, 180, (40, 40, 40), 2)  # Smile
            self.mock_face_box = (f_x - 35, f_y - 35, 70, 70)
        else:
            self.mock_face_box = None

        # 3. Simulate Fire/Smoke
        # Every 300 ticks, create a flickering orange fire polygon
        if int(self.sim_tick / 300) % 3 == 2:
            fire_pts = np.array([
                [100, 420], [120, 370], [135, 390], 
                [150, 350], [165, 380], [180, 360], 
                [200, 420]
            ], np.int32)
            cv2.fillPoly(frame, [fire_pts], (0, 69, 255)) # Orange Fire
            # Add some smoke layers
            cv2.circle(frame, (150, 320), 25, (120, 120, 120), -1)
            cv2.circle(frame, (140, 290), 35, (160, 160, 160), -1)
            self.mock_fire = True
        else:
            self.mock_fire = False

        # Add timestamp overlay
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, time_str, (430, 460), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return frame

    def process_frame(self):
        """Reads frame, runs selected algorithms, draws visuals, logs alerts."""
        if self.is_simulated:
            frame = self.generate_simulated_frame()
        else:
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to capture frame. Switching to simulated feed.")
                self.is_simulated = True
                frame = self.generate_simulated_frame()

        # Create copies for processing
        display_frame = frame.copy()
        height, width, _ = display_frame.shape

        # -------------------------------------------------------------
        # 1. MOTION DETECTION (Frame Differencing)
        # -------------------------------------------------------------
        if self.enable_motion:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if self.prev_frame is None:
                self.prev_frame = gray
            else:
                frame_diff = cv2.absdiff(self.prev_frame, gray)
                thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)[1]
                thresh = cv2.dilate(thresh, None, iterations=2)
                
                # Find contours of moving areas
                contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                motion_detected = False
                for contour in contours:
                    if cv2.contourArea(contour) < Config.MOTION_THRESHOLD * 50:
                        continue
                    # Drawing motion boxes
                    (x, y, w, h) = cv2.boundingRect(contour)
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 255), 1)
                    motion_detected = True
                
                if motion_detected:
                    cv2.putText(display_frame, "[MOTION]", (10, 460), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                    self.trigger_alert("Motion", 0.70, frame)
                
                # Update previous frame
                self.prev_frame = gray

        # -------------------------------------------------------------
        # 2. FACE DETECTION (Haar Cascade or Simulated)
        # -------------------------------------------------------------
        if self.enable_face:
            if self.is_simulated:
                if self.mock_face_box:
                    x, y, w, h = self.mock_face_box
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                    cv2.putText(display_frame, "Face 92%", (x, y - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                    self.trigger_alert("Face", 0.92, frame)
            else:
                gray_face = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(
                    gray_face, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
                )
                for (x, y, w, h) in faces:
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                    cv2.putText(display_frame, "Face", (x, y - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                    self.trigger_alert("Face", 0.85, frame)

        # -------------------------------------------------------------
        # 3. HUMAN & INTRUSION DETECTION (YOLOv8 or Simulated)
        # -------------------------------------------------------------
        # Draw Intrusion Zone overlay if enabled
        if self.enable_intrusion:
            zx_min = int(self.intrusion_zone['x_min'] * width)
            zy_min = int(self.intrusion_zone['y_min'] * height)
            zx_max = int(self.intrusion_zone['x_max'] * width)
            zy_max = int(self.intrusion_zone['y_max'] * height)
            
            # Semitransparent red polygon overlay for intrusion zone
            overlay = display_frame.copy()
            cv2.rectangle(overlay, (zx_min, zy_min), (zx_max, zy_max), (0, 0, 255), -1)
            cv2.addWeighted(overlay, 0.2, display_frame, 0.8, 0, display_frame)
            cv2.rectangle(display_frame, (zx_min, zy_min), (zx_max, zy_max), (0, 0, 255), 2)
            cv2.putText(display_frame, "RESTRICTED INTRUSION ZONE", (zx_min, zy_min - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        if self.enable_human:
            if self.is_simulated:
                if self.mock_person_box:
                    x1, y1, x2, y2 = self.mock_person_box
                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(display_frame, "Human 88%", (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    self.trigger_alert("Human", 0.88, frame)
                    
                    # Intrusion calculation: check center of person
                    if self.enable_intrusion:
                        px_mid = (x1 + x2) / 2
                        py_mid = (y1 + y2) / 2
                        # Check inside zone
                        if (zx_min <= px_mid <= zx_max) and (zy_min <= py_mid <= zy_max):
                            cv2.putText(display_frame, "[INTRUSION ALERT]", (zx_min, zy_max + 25), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                            self.trigger_alert("Intrusion", 0.95, frame)
            else:
                # Run YOLOv8 on real video frame
                if self.model:
                    results = self.model(frame, verbose=False)[0]
                    # Loop over detected objects
                    for box in results.boxes:
                        class_id = int(box.cls[0])
                        confidence = float(box.conf[0])
                        
                        # Class 0 in COCO is "person"
                        if class_id == 0 and confidence >= Config.YOLO_CONFIDENCE_THRESHOLD:
                            xyxy = box.xyxy[0].cpu().numpy().astype(int)
                            x1, y1, x2, y2 = xyxy
                            
                            # Draw green bounding box
                            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            cv2.putText(display_frame, f"Human {confidence:.2f}", (x1, y1 - 10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                            self.trigger_alert("Human", confidence, frame)
                            
                            # Check intrusion boundary intersection
                            if self.enable_intrusion:
                                px_mid = (x1 + x2) / 2
                                py_mid = (y1 + y2) / 2
                                if (zx_min <= px_mid <= zx_max) and (zy_min <= py_mid <= zy_max):
                                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 0, 255), 3) # Alert highlight
                                    cv2.putText(display_frame, "[INTRUSION DETECTED]", (x1, y1 - 25), 
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                                    self.trigger_alert("Intrusion", confidence, frame)

        # -------------------------------------------------------------
        # 4. FIRE & SMOKE DETECTION (HSV range thresholding or Simulation)
        # -------------------------------------------------------------
        if self.enable_fire:
            if self.is_simulated:
                if self.mock_fire:
                    cv2.putText(display_frame, "FIRE/SMOKE 90%", (100, 330), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 69, 255), 2)
                    self.trigger_alert("Fire/Smoke", 0.90, frame)
            else:
                # HSV thresholding for flame color (typically Red/Orange/Yellow ranges)
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                
                # Flame lower and upper ranges
                lower_fire = np.array([15, 100, 100], dtype="uint8")
                upper_fire = np.array([35, 255, 255], dtype="uint8")
                
                mask = cv2.inRange(hsv, lower_fire, upper_fire)
                # Filter noise
                kernel = np.ones((5, 5), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                
                # Check pixel density
                fire_pixels = cv2.countNonZero(mask)
                if fire_pixels > 800:
                    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    for contour in contours:
                        if cv2.contourArea(contour) > 400:
                            x, y, w, h = cv2.boundingRect(contour)
                            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 69, 255), 2)
                            cv2.putText(display_frame, "Fire Candidate", (x, y - 10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 69, 255), 2)
                            self.trigger_alert("Fire/Smoke", 0.82, frame)

        return display_frame

    def get_frame_bytes(self):
        """Processes the frame and encodes it to JPG bytes for Flask streaming."""
        processed = self.process_frame()
        ret, jpeg = cv2.imencode('.jpg', processed)
        if not ret:
            return None
        return jpeg.tobytes()

    def release(self):
        """Release resources on deletion."""
        if self.cap and self.cap.isOpened():
            self.cap.release()
