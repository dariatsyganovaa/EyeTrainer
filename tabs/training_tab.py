import os
from datetime import datetime

import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QGridLayout,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QFont, QColor, QLinearGradient, QPainter, QPen


def _shadow(blur=24, dy=6, alpha=80):
    s = QGraphicsDropShadowEffect()
    s.setBlurRadius(blur)
    s.setOffset(0, dy)
    s.setColor(QColor(0, 0, 0, alpha))
    return s

class ParamCard(QFrame):
    def __init__(self, label: str, value: str, accent: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.setStyleSheet("""
            QFrame {
                background: #1e1e1e;
                border-radius: 10px;
                border: none;
            }
        """)
        self.setGraphicsEffect(_shadow(16, 4, 60))

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 16, 0)
        row.setSpacing(14)

        strip = QFrame()
        strip.setFixedWidth(3)
        strip.setMinimumHeight(80)
        strip.setStyleSheet(f"background: {accent}; border-radius: 2px; border: none;")
        row.addWidget(strip)

        col = QVBoxLayout()
        col.setSpacing(4)
        col.setContentsMargins(0, 12, 0, 12)

        lbl = QLabel(label.upper())
        lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {accent}; letter-spacing: 1.5px; background: transparent;")
        col.addWidget(lbl)

        val = QLabel(value)
        val.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        val.setStyleSheet("color: #ffffff; background: transparent;")
        col.addWidget(val)

        row.addLayout(col)

class ExerciseCard(QFrame):
    SPEED_LABELS = {
        "very_slow":("Очень медленно", "#7C5CBF"),
        "slow":("Медленно", "#5B8DEF"),
        "medium":("Стандартно", "#3DB87A"),
    }
    EXERCISE_LABELS = {
        "circle_right": "Круг по часовой",
        "circle_left": "Круг против часовой",
        "horizontal": "Горизонталь",
        "vertical": "Вертикаль",
        "zigzag": "Зигзаг",
        "clock": "Циферблат",
        "two_diagonals": "Диагонали",
        "diagonal_up": "Диагональ вверх",
        "diagonal_down": "Диагональ вниз",
        "rectangle": "Прямоугольник",
    }

    def __init__(self, exercise: dict, index: int, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)

        speed = exercise.get("speed", "medium")
        name = exercise.get("name", "")
        label, color = self.SPEED_LABELS.get(speed, ("Стандартно", "#3DB87A"))
        ex_label = self.EXERCISE_LABELS.get(name, name)

        self.setStyleSheet("""
            QFrame {
                background: #181818;
                border-radius: 10px;
            }
        """)

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(12)

        num = QLabel(f"{index:02d}")
        num.setFixedWidth(28)
        num.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        num.setStyleSheet(f"color: {color}; background: transparent;")
        row.addWidget(num)

        name_lbl = QLabel(ex_label)
        name_lbl.setFont(QFont("Segoe UI", 11))
        name_lbl.setStyleSheet("color: #cccccc; background: transparent;")
        row.addWidget(name_lbl, stretch=1)

        speed_lbl = QLabel(label)
        speed_lbl.setFont(QFont("Segoe UI", 9))
        speed_lbl.setStyleSheet(f"""
            color: {color};
            background: {color}22;
            border-radius: 6px;
            padding: 3px 10px;
        """)
        row.addWidget(speed_lbl)

class LaunchButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(52)
        self.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5B8DEF, stop:1 #7C5CBF
                );
                color: #ffffff;
                border: none;
                border-radius: 12px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a7de0, stop:1 #6a4aaf
                );
            }
            QPushButton:pressed {
                background: #3a6dd0;
            }
            QPushButton:disabled {
                background: #222;
                color: #444;
            }
        """)
        self.setGraphicsEffect(_shadow(20, 6, 100))

class TrainingTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._exercise_plan   = {}
        self._current_user_id = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(48, 36, 48, 48)
        lay.setSpacing(0)

        header = QHBoxLayout()
        header.setSpacing(0)

        title_col = QVBoxLayout()
        title_col.setSpacing(6)

        self._title = QLabel("Программа тренировок")
        self._title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        self._title.setStyleSheet("color: #ffffff; background: transparent;")
        title_col.addWidget(self._title)

        self._subtitle = QLabel("Пройдите тестирование для загрузки персонального плана")
        self._subtitle.setFont(QFont("Segoe UI", 11))
        self._subtitle.setStyleSheet("color: #444; background: transparent;")
        title_col.addWidget(self._subtitle)

        header.addLayout(title_col, stretch=1)

        self._launch_btn = LaunchButton("Запустить гимнастику")
        self._launch_btn.setFixedWidth(240)
        self._launch_btn.clicked.connect(self._launch_gymnastics)
        header.addWidget(self._launch_btn, alignment=Qt.AlignmentFlag.AlignBottom)

        lay.addLayout(header)
        lay.addSpacing(32)

        self._params_frame = QFrame()
        self._params_frame.setVisible(False)
        params_lay = QVBoxLayout(self._params_frame)
        params_lay.setContentsMargins(0, 0, 0, 0)
        params_lay.setSpacing(16)

        section_lbl = QLabel("ПАРАМЕТРЫ ПЛАНА")
        section_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        section_lbl.setStyleSheet("color: #888; letter-spacing: 2px; background: transparent;")
        params_lay.addWidget(section_lbl)

        self._params_grid = QGridLayout()
        self._params_grid.setSpacing(12)
        params_lay.addLayout(self._params_grid)

        lay.addWidget(self._params_frame)
        lay.addSpacing(32)

        self._exercises_frame = QFrame()
        self._exercises_frame.setVisible(False)
        ex_lay = QVBoxLayout(self._exercises_frame)
        ex_lay.setContentsMargins(0, 0, 0, 0)
        ex_lay.setSpacing(16)

        ex_header = QHBoxLayout()
        ex_section = QLabel("СПИСОК УПРАЖНЕНИЙ")
        ex_section.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        ex_section.setStyleSheet("color: #888; letter-spacing: 2px; background: transparent;")
        ex_header.addWidget(ex_section)
        ex_header.addStretch()

        self._ex_count = QLabel("")
        self._ex_count.setFont(QFont("Segoe UI", 9))
        self._ex_count.setStyleSheet("color: #444; background: transparent;")
        ex_header.addWidget(self._ex_count)
        ex_lay.addLayout(ex_header)

        self._exercises_lay = QVBoxLayout()
        self._exercises_lay.setSpacing(8)
        ex_lay.addLayout(self._exercises_lay)

        lay.addWidget(self._exercises_frame)
        lay.addSpacing(32)

        self._notes_frame = QFrame()
        self._notes_frame.setVisible(False)
        self._notes_frame.setStyleSheet("""
            QFrame {
                background: #0d1f35;
                border-radius: 14px;
            }
        """)
        notes_lay = QVBoxLayout(self._notes_frame)
        notes_lay.setContentsMargins(20, 16, 20, 16)
        notes_lay.setSpacing(8)

        notes_title = QLabel("РЕКОМЕНДАЦИИ")
        notes_title.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        notes_title.setStyleSheet("color: #5B8DEF; letter-spacing: 1.5px; background: transparent;")
        notes_lay.addWidget(notes_title)

        self._notes_label = QLabel("")
        self._notes_label.setFont(QFont("Segoe UI", 10))
        self._notes_label.setStyleSheet("color: #8aabde; background: transparent;")
        self._notes_label.setWordWrap(True)
        notes_lay.addWidget(self._notes_label)

        lay.addWidget(self._notes_frame)
        lay.addStretch()

        scroll.setWidget(container)
        root.addWidget(scroll)

    def apply_plan(self, plan: dict, user_id: int = None):
        self._exercise_plan = plan
        self._current_user_id = user_id

        disease = plan.get("disease", "")
        level = plan.get("level", "")

        if disease and disease != "healthy":
            self._subtitle.setText(
                f"Персональный план  ·  {disease.capitalize()}  {level}"
            )

        self._clear_grid()
        params = [
            ("Диагноз", f"{disease} {level}", "#5B8DEF"),
            ("Фон", plan.get("background", "—"), "#7C5CBF"),
            ("Объект", plan.get("object_hex", "—"), "#3DB87A"),
            ("Масштаб", str(plan.get("object_scale", 1.0)), "#F4A261"),
            ("Скорость", f"{plan.get('speed_ms', 30)} мс", "#E63946"),
            ("Механика", plan.get("mechanic", "—"), "#48CAE4"),
        ]
        for i, (label, value, accent) in enumerate(params):
            card = ParamCard(label, value, accent)
            self._params_grid.addWidget(card, i // 3, i % 3)

        self._params_frame.setVisible(True)

        self._clear_exercises()
        exercises = plan.get("exercises", [])
        self._ex_count.setText(f"{len(exercises)} упражнений")
        for i, ex in enumerate(exercises, 1):
            card = ExerciseCard(ex, i)
            self._exercises_lay.addWidget(card)
        self._exercises_frame.setVisible(bool(exercises))

        notes = plan.get("notes", [])
        if notes:
            self._notes_label.setText("\n".join(f"• {n}" for n in notes))
            self._notes_frame.setVisible(True)

        print(f"[TrainingTab] план: {disease} {level}, "
              f"фон={plan.get('background')}, "
              f"скорость={plan.get('speed_ms')}мс")

    def _clear_grid(self):
        while self._params_grid.count():
            item = self._params_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _clear_exercises(self):
        while self._exercises_lay.count():
            item = self._exercises_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def load_plan_from_db(self, user_id: int):
        try:
            from utils.db_manager import DatabaseManager
            from repositories.exercise_repository import ExerciseRepository
            db = DatabaseManager()
            repo = ExerciseRepository(db)
            plan = repo.get_plan(user_id)
            db.close()
            if plan:
                self.apply_plan(plan, user_id)
        except Exception as e:
            print(f"[TrainingTab] план из БД недоступен: {e}")

    def _get_plan(self) -> dict:
        return self._exercise_plan or {
            "background": "plain_white.png",
            "object_hex": "#FFFFFF",
            "object_scale": 1.0,
            "speed_ms": 30,
        }

    def _launch_gymnastics(self):
        current_dir = Path(__file__).resolve().parent
        project_root = current_dir.parent
        exe_path = project_root / "eye_gymnastics" / "build" / "Release" / "eye_gymnasticsApp.exe"

        if not exe_path.exists():
            print(f"[TrainingTab] exe не найден по пути: {exe_path}")
            return

        subprocess.Popen([str(exe_path)])

    def _cleanup(self):
        pass

    def closeEvent(self, event):
        self._cleanup()
        super().closeEvent(event)
