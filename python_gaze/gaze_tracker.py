from pathlib import Path
import cv2
import time
import threading
import numpy as np
import torch
import torch.nn as nn
from ultralytics import YOLO

class Reshaper(nn.Module):
    def __init__(self, target_shape):
        super(Reshaper, self).__init__()
        self.target_shape = target_shape
    def forward(self, input):
        return torch.reshape(input, (-1, *self.target_shape))

class EyesNet(nn.Module):
    def __init__(self):
        super(EyesNet, self).__init__()
        self.features_left = nn.Sequential(
            nn.Conv2d(1, 32, 5, 2, 2), nn.LeakyReLU(),
            nn.Conv2d(32, 64, 3, 2, 1), nn.LeakyReLU(),
            nn.Conv2d(64, 64, 3, 2, 1), nn.LeakyReLU(),
            nn.Conv2d(64, 64, 3, 2, 1), nn.LeakyReLU(),
            nn.Conv2d(64, 64, 3, 2, 1), nn.LeakyReLU(),
            Reshaper([64])
        )
        self.features_right = nn.Sequential(
            nn.Conv2d(1, 32, 5, 2, 2), nn.LeakyReLU(),
            nn.Conv2d(32, 64, 3, 2, 1), nn.LeakyReLU(),
            nn.Conv2d(64, 64, 3, 2, 1), nn.LeakyReLU(),
            nn.Conv2d(64, 64, 3, 2, 1), nn.LeakyReLU(),
            nn.Conv2d(64, 64, 3, 2, 1), nn.LeakyReLU(),
            Reshaper([64])
        )
        self.fc = nn.Sequential(
            nn.Linear(128, 64), nn.LeakyReLU(),
            nn.Linear(64, 16), nn.LeakyReLU(),
            nn.Linear(16, 2), nn.Sigmoid()
        )
    def forward(self, x_left, x_right):
        x_left = self.features_left(x_left)
        x_right = self.features_right(x_right)
        return self.fc(torch.cat((x_left, x_right), 1))

class GazePredictor(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(12, 64), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, 32), nn.ReLU(),
            nn.Linear(32, 2), nn.Sigmoid()
        )
    def forward(self, x):
        return self.net(x)

class GazeTrackerRunner:
    def __init__(self, device = 'cpu', width=1280, height=720):
        self.device = device
        self.width = width
        self.height = height
        self.running = False
        self.history = []
        self.start_time = 0

        print("[GazeTracker] Initialization of neural networks...")
        base_path = Path(__file__).resolve().parent / "models"
        try:
            self.eye_model = YOLO(str(base_path / "best.pt"))
            self.eye_model.to(self.device)

            self.pupil_model = EyesNet().to(self.device)
            self.pupil_model.load_state_dict(torch.load(str(base_path / "epoch_299.pth"), map_location=self.device))
            self.pupil_model.eval()

            self.gaze_model = GazePredictor().to(self.device)
            self.gaze_model.load_state_dict(torch.load(str(base_path / "gaze_predictor_own_dataset.pth"), map_location=self.device))
            self.gaze_model.eval()
            print("[GazeTracker] All models loaded successfully.")
        except Exception as e:
            print(f"[GazeTracker] Critical error while loading: {e}")

    def calculate_iou(self, box1, box2):
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        xi1 = max(x1_1, x1_2)
        yi1 = max(y1_1, y1_2)
        xi2 = min(x2_1, x2_2)
        yi2 = min(y2_1, y2_2)
        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = box1_area + box2_area - inter_area
        return inter_area / union_area if union_area > 0 else 0

    def filter_duplicate_boxes(self, boxes, iou_threshold=0.5):
        if boxes is None or len(boxes) == 0:
            return []
        boxes_np = []
        for box in boxes:
            coords = box.xyxy[0].cpu().numpy()
            boxes_np.append((coords, box.conf[0].cpu().numpy(), box))
        boxes_np.sort(key=lambda x: x[1], reverse=True)
        filtered_boxes = []
        used_indices = set()
        for i, (coords_i, conf_i, box_i) in enumerate(boxes_np):
            if i in used_indices:
                continue
            filtered_boxes.append(box_i)
            used_indices.add(i)
            for j, (coords_j, conf_j, box_j) in enumerate(boxes_np):
                if j in used_indices or i == j:
                    continue
                if self.calculate_iou(coords_i, coords_j) > iou_threshold:
                    used_indices.add(j)
        return filtered_boxes

    def preprocess_eye_for_pupil(self, eye_roi):
        try:
            if len(eye_roi.shape) == 3:
                gray = cv2.cvtColor(eye_roi, cv2.COLOR_RGB2GRAY)
            else:
                gray = eye_roi
            resized = cv2.resize(gray, (32, 16))
            tensor = torch.FloatTensor(resized / 255.0).unsqueeze(0).unsqueeze(0)
            return tensor.to(self.device), resized
        except:
            return None, None

    def detect_pupil_simple(self, eye_roi):
        try:
            if len(eye_roi.shape) == 3:
                gray = cv2.cvtColor(eye_roi, cv2.COLOR_RGB2GRAY)
            else:
                gray = eye_roi
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            blurred = cv2.GaussianBlur(enhanced, (7, 7), 0)
            _, thresh = cv2.threshold(blurred, 40, 255, cv2.THRESH_BINARY_INV)
            kernel = np.ones((3,3), np.uint8)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                largest = max(contours, key=cv2.contourArea)
                if cv2.contourArea(largest) > 10:
                    M = cv2.moments(largest)
                    if M["m00"] != 0:
                        return int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
            return eye_roi.shape[1] // 2, eye_roi.shape[0] // 2
        except:
            return eye_roi.shape[1] // 2, eye_roi.shape[0] // 2

    def detect_pupil_neural(self, left_eye_roi, right_eye_roi):
        try:
            left_tensor, _ = self.preprocess_eye_for_pupil(left_eye_roi)
            right_tensor, _ = self.preprocess_eye_for_pupil(right_eye_roi)
            if left_tensor is None or right_tensor is None:
                return self.detect_pupil_simple(left_eye_roi), self.detect_pupil_simple(right_eye_roi)
            with torch.no_grad():
                pupils_pred = self.pupil_model(left_tensor, right_tensor)
            pupil_y, pupil_x = pupils_pred[0].cpu().numpy()
            left = (pupil_x * left_eye_roi.shape[1], pupil_y * left_eye_roi.shape[0])
            right = (pupil_x * right_eye_roi.shape[1], pupil_y * right_eye_roi.shape[0])
            return left, right
        except:
            return self.detect_pupil_simple(left_eye_roi), self.detect_pupil_simple(right_eye_roi)

    def extract_features_from_frame(self, frame):
        if frame is None:
            return None
        h, w = frame.shape[:2]

        results = self.eye_model.predict(frame, conf=0.01, iou=0.4, verbose=False)
        if results[0].boxes is None:
            return None

        filtered_boxes = self.filter_duplicate_boxes(results[0].boxes)
        if len(filtered_boxes) < 2:
            return None

        objects = []
        for box in filtered_boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            objects.append({'coords': [x1, y1, x2, y2], 'center_x': (x1 + x2) / 2})
        objects.sort(key=lambda x: x['center_x'])

        left = objects[0]
        right = objects[-1]
        left_coords = [int(c) for c in left['coords']]
        right_coords = [int(c) for c in right['coords']]

        left_roi = frame[left_coords[1]:left_coords[3], left_coords[0]:left_coords[2]]
        right_roi = frame[right_coords[1]:right_coords[3], right_coords[0]:right_coords[2]]

        if left_roi.size == 0 or right_roi.size == 0:
            return None

        left_pupil, right_pupil = self.detect_pupil_neural(left_roi, right_roi)

        left_pupil_abs = (left_coords[0] + left_pupil[0], left_coords[1] + left_pupil[1])
        right_pupil_abs = (right_coords[0] + right_pupil[0], right_coords[1] + right_pupil[1])

        left_center = ((left_coords[0] + left_coords[2]) / 2, (left_coords[1] + left_coords[3]) / 2)
        right_center = ((right_coords[0] + right_coords[2]) / 2, (right_coords[1] + right_coords[3]) / 2)

        left_w = left_coords[2] - left_coords[0]
        left_h = left_coords[3] - left_coords[1]
        right_w = right_coords[2] - right_coords[0]
        right_h = right_coords[3] - right_coords[1]

        features = [
            left_center[0] / w, left_center[1] / h,
            right_center[0] / w, right_center[1] / h,
            (left_pupil_abs[0] - left_coords[0]) / left_w,
            (left_pupil_abs[1] - left_coords[1]) / left_h,
            (right_pupil_abs[0] - right_coords[0]) / right_w,
            (right_pupil_abs[1] - right_coords[1]) / right_h,
            left_w / w, left_h / h, right_w / w, right_h / h
        ]
        return np.array(features, dtype=np.float32)

    def predict_gaze_point(self, features, screen_width=1920, screen_height=1080):
        if features is None:
            return None

        input_tensor = torch.FloatTensor(features).reshape(1, -1)

        with torch.no_grad():
            normalized_point = self.gaze_model(input_tensor)[0].numpy()

        screen_x = int(normalized_point[0] * screen_width)
        screen_y = int(normalized_point[1] * screen_height)

        return (screen_x, screen_y)

    def start(self):
        if self.running: return
        self.running = True
        self.history = []
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print("[GazeTracker] Thread started.")

    def stop(self):
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=3.0)
        return self.history

    def _run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            return

        print(f"[GazeTracker] Camera open: {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")

        no_eye_count = 0
        while self.running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("[GazeTracker] Failed to receive frame")
                bre
            if not self.running:
                break

            features = self.extract_features_from_frame(frame)
            if features is not None:
                input_tensor = torch.FloatTensor(features).reshape(1, -1).to(self.device)
                with torch.no_grad():
                    res = self.gaze_model(input_tensor)[0].cpu().numpy()
                self.history.append({
                    'duration': time.time() - self.start_time,
                    'x_coord': int(res[0] * 1920 * (self.width / 1920)),
                    'y_coord': int(res[1] * 1080 * (self.height / 1080))
                })
                no_eye_count = 0
            else:
                no_eye_count += 1
                if no_eye_count % 50 == 1:
                    print(f"[GazeTracker] Eyes not found ({no_eye_count} frames in a row)")

            time.sleep(0.01)

        cap.release()
        print(f"[GazeTracker] Flow completed, collected {len(self.history)} points")
