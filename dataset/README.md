# Smart AI Surveillance System - Dataset Specifications & Training Guides

This folder is designed to satisfy academic requirements for B.Tech Computer Science mini-projects. It explains the datasets used by the detection models and guides students on how they can train custom models for advanced evaluations.

---

## 1. Human Detection Dataset (YOLOv8)
* **Model**: Ultralytics YOLOv8 Nano (`yolov8n.pt`)
* **Dataset**: **COCO (Common Objects in Context)**
  * **Images**: ~330K labeled images.
  * **Categories**: 80 object classes.
  * **Class Utilized**: Class `0` (`person`).
* **Why YOLOv8 Nano?**
  * Extremely lightweight (~6.2 MB parameter size).
  * Highly optimized for real-time edge processing (running on standard CPU laptops without requiring Nvidia CUDA GPUs).

---

## 2. Face Detection Dataset (Haar Cascade)
* **Model**: OpenCV Frontal Face Cascade (`haarcascade_frontalface_default.xml`)
* **Dataset**: Trained on early Viola-Jones datasets (composed of facial images and non-facial background regions).
* **How to extend for Face Recognition?**
  To perform actual face recognition (identifying WHO the person is), students can train a **Local Binary Patterns Histograms (LBPH)** recognizer:
  1. Capture 50 snapshot images of a student/user's face.
  2. Save them in a directory `dataset/user_name/`.
  3. Run an LBPH train script:
     ```python
     import cv2
     import numpy as np
     # Code snippet to train face recognizer on face images
     recognizer = cv2.face.LBPHFaceRecognizer_create()
     # Loop and train ...
     recognizer.write('models/face_trainer.yml')
     ```
  4. Load the trainer in `detector.py` to classify names in real-time.

---

## 3. Fire and Smoke Detection Dataset (Academic Datasets)
For evaluations, we have implemented an **HSV Color Range Chromaticity Filter** that isolates red, orange, and yellow hues (for flames) and light-gray values (for smoke).
For a high-scoring final year project, students can train a custom YOLOv8 model for Fire & Smoke detection using the following open datasets:
* **Recommended Datasets**:
  * [Kaggle Fire and Smoke Dataset](https://www.kaggle.com/datasets/kutaykutlu/fire-and-smoke-dataset)
  * [Roboflow Universe Fire Detection Datasets](https://universe.roboflow.com/search?q=fire%20detection) (provides ready-to-use YOLO text format annotations).
* **Training YOLOv8 on Custom Fire Dataset**:
  ```python
  from ultralytics import YOLO

  # Load pre-trained nano model
  model = YOLO('yolov8n.pt')

  # Train the model on custom fire dataset configuration file
  results = model.train(data='dataset/fire_config.yaml', epochs=50, imgsz=640)
  ```

---

## 4. Intrusion Detection (Polygon Coordinates)
* **Logic**: Bounding box geometry.
* **Details**: Our system checks if the center point `(x_mid, y_mid)` of a YOLO person bounding box falls within the normalized restricted area:
  $$\text{zx\_min} \le x_{\text{mid}} \le \text{zx\_max}$$
  $$\text{zy\_min} \le y_{\text{mid}} \le \text{zy\_max}$$
* This mathematical logic represents a real spatial search query without requiring heavier GIS computational packages.
