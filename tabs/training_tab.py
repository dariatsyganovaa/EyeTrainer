import os
import multiprocessing
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QImage, QPixmap, QColor

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


def _shadow(blur=20, dy=4, alpha=100):
    s = QGraphicsDropShadowEffect()
    s.setBlurRadius(blur)
    s.setOffset(0, dy)
    s.setColor(QColor(0, 0, 0, alpha))
    return s

class ExerciseCard(QFrame):
    def __init__(self, title: str, description: str,
                 color: str, btn_text: str, command,
                 tag: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("ec")
        self.setMinimumHeight(100)
        self.setStyleSheet(f"""
            QFrame#ec {{
                background: #1e1e1e;
                border-radius: 14px;
                border-left: 4px solid {color};
            }}
        """)
        self.setGraphicsEffect(_shadow())

        row = QHBoxLayout(self)
        row.setContentsMargins(24, 18, 20, 18)
        row.setSpacing(18)

        dot = QFrame()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background:{color}; border-radius:5px;")
        row.addWidget(dot, alignment=Qt.AlignmentFlag.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(5)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        t.setStyleSheet("color:#f2f2f2;")
        header_row.addWidget(t)

        if tag:
            badge = QLabel(tag)
            badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            badge.setStyleSheet(f"""
                background: {color}33;
                color: {color};
                border-radius: 6px;
                padding: 2px 8px;
            """)
            header_row.addWidget(badge)
        header_row.addStretch()
        col.addLayout(header_row)

        d = QLabel(description)
        d.setFont(QFont("Segoe UI", 10))
        d.setStyleSheet("color:#606060;")
        d.setWordWrap(True)
        col.addWidget(d)

        row.addLayout(col, stretch=1)

        btn = QPushButton(btn_text)
        btn.setFixedSize(130, 38)
        btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {color};
                color: #fff;
                border-radius: 8px;
                border: none;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{ background: #fff; color: {color}; }}
            QPushButton:pressed {{ background: #ddd; }}
            QPushButton:disabled {{
                background: #2a2a2a;
                color: #444;
            }}
        """)
        btn.clicked.connect(lambda _=False, fn=command: fn())
        row.addWidget(btn, alignment=Qt.AlignmentFlag.AlignVCenter)


class TrainingTab(QWidget):
    SAVE_FOLDER = "recordings"
    CAM_W, CAM_H = 280, 210

    def __init__(self, parent=None):
        super().__init__(parent)
        os.makedirs(self.SAVE_FOLDER, exist_ok=True)

        self.cap = None
        self.is_running_camera = False
        self.is_recording = False
        self.video_writer = None
        self.simulation_process = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_frame)

        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame()
        sidebar.setFixedWidth(300)
        sidebar.setStyleSheet("background:#191919; border-right: 1px solid #222;")

        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(18, 28, 18, 22)
        sb.setSpacing(14)
        sb.setAlignment(Qt.AlignmentFlag.AlignTop)

        cam_title = QLabel("Контроль положения")
        cam_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        cam_title.setStyleSheet("color:#aaa;")
        cam_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sb.addWidget(cam_title)

        self.cam_label = QLabel("Камера\nвыключена")
        self.cam_label.setFixedSize(self.CAM_W, self.CAM_H)
        self.cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cam_label.setFont(QFont("Segoe UI", 11))
        self.cam_label.setStyleSheet(
            "background:#111; border-radius:10px; color:#333;"
        )
        sb.addWidget(self.cam_label, alignment=Qt.AlignmentFlag.AlignCenter)


        self.btn_cam = QPushButton("Включить камеру")
        self.btn_cam.setCheckable(True)
        self.btn_cam.setFont(QFont("Segoe UI", 11))
        self.btn_cam.setStyleSheet(self._cam_style(False))
        self.btn_cam.toggled.connect(self._on_cam_toggle)
        sb.addWidget(self.btn_cam)

        self.btn_rec = QPushButton("Начать запись")
        self.btn_rec.setFont(QFont("Segoe UI", 11))
        self.btn_rec.setEnabled(False)
        self.btn_rec.setStyleSheet(self._rec_style(False))
        self.btn_rec.clicked.connect(self._toggle_recording)
        sb.addWidget(self.btn_rec)

        sb.addStretch()
        root.addWidget(sidebar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")

        w = QWidget()
        w.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(36, 30, 36, 30)
        lay.setSpacing(14)

        h1 = QLabel("Программа тренировок")
        h1.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        h1.setStyleSheet("color:#fff;")
        lay.addWidget(h1)

        h2 = QLabel("Упражнения для здоровья глаз")
        h2.setFont(QFont("Segoe UI", 11))
        h2.setStyleSheet("color:#444;")
        lay.addWidget(h2)

        lay.addSpacing(8)


        lay.addWidget(ExerciseCard(
            title="Гимнастика глаз",
            description=(
                "Комплекс упражнений для снятия усталости и укрепления "
                "глазодвигательных мышц. Модуль разработан совместно."
            ),
            color="#7C5CBF",
            btn_text="ЗАПУСТИТЬ",
            command=self._launch_gymnastics,
        ))

        lay.addStretch()
        scroll.setWidget(w)
        root.addWidget(scroll, stretch=1)

    def _on_cam_toggle(self, checked: bool):
        if checked:
            self.btn_cam.setText("Выключить камеру")
            self.btn_cam.setStyleSheet(self._cam_style(True))
            self._start_camera()
        else:
            self.btn_cam.setText("Включить камеру")
            self.btn_cam.setStyleSheet(self._cam_style(False))
            self._stop_camera()

    def _start_camera(self):
        if not CV2_AVAILABLE:
            self.cam_label.setText("OpenCV\nне установлен")
            self.btn_cam.setChecked(False)
            return
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.cam_label.setText("Камера\nне найдена")
            self.btn_cam.setChecked(False)
            return
        self.is_running_camera = True
        self.btn_rec.setEnabled(True)
        self.cam_label.setText("")
        self._timer.start(30)

    def _stop_camera(self):
        if self.is_recording:
            self._toggle_recording()
        self._timer.stop()
        self.is_running_camera = False
        self.btn_rec.setEnabled(False)
        if self.cap:
            self.cap.release()
            self.cap = None
        self.cam_label.setPixmap(QPixmap())
        self.cam_label.setText("Камера\nвыключена")

    def _update_frame(self):
        if not self.is_running_camera or not self.cap:
            return
        ret, frame = self.cap.read()
        if not ret:
            return
        frame = cv2.flip(frame, 1)
        if self.is_recording and self.video_writer:
            self.video_writer.write(frame)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(img).scaled(
            self.CAM_W, self.CAM_H,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.cam_label.setPixmap(pix)

    def _toggle_recording(self):
        if not self.is_recording:
            if not self.cap or not self.cap.isOpened():
                return
            W = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            H = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            path = os.path.join(self.SAVE_FOLDER, f"video_{ts}.avi")
            self.video_writer = cv2.VideoWriter(
                path, cv2.VideoWriter_fourcc(*"XVID"), 20.0, (W, H)
            )
            self.is_recording = True
            self.btn_rec.setText("Остановить")
            self.btn_rec.setStyleSheet(self._rec_style(True))
        else:
            self.is_recording = False
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            self.btn_rec.setText("Начать запись")
            self.btn_rec.setStyleSheet(self._rec_style(False))


    def _launch_gymnastics(self):
        import subprocess
        import os

        exe_path = os.path.join("eye_gymnastics", "build", "Release", "eye_gymnasticsApp.exe")

        if not os.path.exists(exe_path):
            print("[TrainingTab] exe не найден")
            return

        subprocess.Popen([exe_path])

    def _cleanup(self):
        if self.is_recording and self.video_writer:
            self.video_writer.release()
        self._timer.stop()
        if self.cap:
            self.cap.release()
        if self.simulation_process and self.simulation_process.is_alive():
            self.simulation_process.terminate()

    def closeEvent(self, event):
        self._cleanup()
        super().closeEvent(event)


    @staticmethod
    def _cam_style(on: bool) -> str:
        bg, hv = ("#1a5c38", "#144d2e") if on else ("#252525", "#2e2e2e")
        return f"""
            QPushButton {{
                background:{bg}; color:#ddd;
                border-radius:8px; padding:10px; border:none;
            }}
            QPushButton:hover {{ background:{hv}; color:#fff; }}
        """

    @staticmethod
    def _rec_style(on: bool) -> str:
        bg, hv = ("#7b1d1d", "#5c1515") if on else ("#2a1a0a", "#3a2510")
        return f"""
            QPushButton {{
                background:{bg}; color:#ddd;
                border-radius:8px; padding:10px; border:none;
            }}
            QPushButton:hover {{ background:{hv}; color:#fff; }}
            QPushButton:disabled {{
                background:#1c1c1c; color:#333;
            }}
        """
