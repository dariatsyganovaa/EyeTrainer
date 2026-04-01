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
    def __init__(self, title, description, color, btn_text, command, tag="", parent=None):
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
        row.setContentsMargins(28, 22, 24, 22)
        row.setSpacing(22)

        dot = QFrame()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background:{color}; border-radius:5px;")
        row.addWidget(dot, alignment=Qt.AlignmentFlag.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
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
        d.setFont(QFont("Segoe UI", 11))
        d.setStyleSheet("color:#606060;")
        d.setWordWrap(True)
        col.addWidget(d)

        row.addLayout(col, stretch=1)

        btn = QPushButton(btn_text)
        btn.setMinimumHeight(42)
        btn.setMinimumWidth(140)
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {color};
                color: #fff;
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{ background: #fff; color: {color}; }}
            QPushButton:disabled {{ background: #2a2a2a; color: #444; }}
        """)
        btn.clicked.connect(lambda _=False, fn=command: fn())
        row.addWidget(btn, alignment=Qt.AlignmentFlag.AlignVCenter)


class TrainingTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.cap = None
        self.simulation_process = None
        self._exercise_plan = {}

        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

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

        self._plan_label = QLabel("")
        self._plan_label.setFont(QFont("Segoe UI", 10))
        self._plan_label.setStyleSheet("""
            color: #5B8DEF;
            background: #1a2a3a;
            border-radius: 8px;
            padding: 8px 14px;
        """)
        self._plan_label.setWordWrap(True)
        self._plan_label.setVisible(False)
        lay.addWidget(self._plan_label)

        lay.addSpacing(8)

        lay.addWidget(ExerciseCard(
            title="Гимнастика глаз",
            description=(
                "Комплекс упражнений для снятия усталости "
                "и укрепления глазодвигательных мышц."
            ),
            color="#7C5CBF",
            btn_text="ЗАПУСТИТЬ",
            command=self._launch_gymnastics,
        ))

        lay.addStretch()
        scroll.setWidget(w)
        root.addWidget(scroll, stretch=1)

    def apply_plan(self, plan: dict):
        self._exercise_plan = plan
        notes = plan.get("notes", [])
        if notes:
            self._plan_label.setText("Рекомендации:  " + "  •  ".join(notes))
            self._plan_label.setVisible(True)
        speed = "медленно" if plan.get("speed") == "slow" else "стандартно"
        print(f"[TrainingTab] план: скорость={speed}, фон={plan.get('background')}")

    def _get_plan(self) -> dict:
        return self._exercise_plan or {
            "background": "plain_white.png",
            "color_scheme": "dark",
            "speed": "medium",
        }

    def _launch_gymnastics(self):
        import subprocess
        exe_path = os.path.join(
            "eye_gymnastics", "build", "Release", "eye_gymnasticsApp.exe"
        )
        if not os.path.exists(exe_path):
            print("[TrainingTab] exe не найден")
            return
        subprocess.Popen([exe_path])

    def _cleanup(self):
        if self.cap:
            self.cap.release()
        if self.simulation_process and self.simulation_process.is_alive():
            self.simulation_process.terminate()

    def closeEvent(self, event):
        self._cleanup()
        super().closeEvent(event)
