from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QDialog,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor


def _shadow(blur=20, dy=4, alpha=100):
    s = QGraphicsDropShadowEffect()
    s.setBlurRadius(blur)
    s.setOffset(0, dy)
    s.setColor(QColor(0, 0, 0, alpha))
    return s


class TestCard(QFrame):
    def __init__(self, title: str, description: str, color: str, command, parent=None):
        super().__init__(parent)
        self.setObjectName("tc")
        self.setMinimumHeight(90)
        self.setStyleSheet(f"""
            QFrame#tc {{
                background-color: #1e1e1e;
                border-radius: 14px;
                border-left: 4px solid {color};
            }}
        """)
        self.setGraphicsEffect(_shadow())

        row = QHBoxLayout(self)
        row.setContentsMargins(24, 16, 20, 16)
        row.setSpacing(18)

        dot = QFrame()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background:{color}; border-radius:5px;")
        row.addWidget(dot, alignment=Qt.AlignmentFlag.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(4)

        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        t.setStyleSheet("color:#f2f2f2;")
        col.addWidget(t)

        d = QLabel(description)
        d.setFont(QFont("Segoe UI", 10))
        d.setStyleSheet("color:#606060;")
        d.setWordWrap(True)
        col.addWidget(d)

        row.addLayout(col, stretch=1)

        btn = QPushButton("НАЧАТЬ")
        btn.setFixedSize(110, 36)
        btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {color};
                color: #fff;
                border-radius: 8px;
                border: none;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: #fff;
                color: {color};
            }}
            QPushButton:pressed {{ background: #ddd; }}
        """)
        btn.clicked.connect(lambda _=False, fn=command: fn())
        row.addWidget(btn, alignment=Qt.AlignmentFlag.AlignVCenter)


class StubDialog(QDialog):
    def __init__(self, test_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(test_name)
        self.setFixedSize(440, 280)
        self.setStyleSheet("background:#1a1a1a;")
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
        )

        v = QVBoxLayout(self)
        v.setContentsMargins(36, 36, 36, 36)
        v.setSpacing(14)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl = QLabel(test_name)
        lbl.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        lbl.setStyleSheet("color:#fff;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(lbl)

        sub = QLabel("Этот модуль находится в стадии разработки")
        sub.setFont(QFont("Segoe UI", 10))
        sub.setStyleSheet("color:#555;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(sub)

        btn = QPushButton("Закрыть")
        btn.setFixedWidth(120)
        btn.setStyleSheet("""
            QPushButton {
                background:#2a2a2a; color:#888;
                border-radius:8px; padding:9px; border:none;
            }
            QPushButton:hover { background:#333; color:#fff; }
        """)
        btn.clicked.connect(self.close)
        v.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)


class TestingTab(QWidget):
    TESTS = [
        (
            "Полихроматические таблицы Рабкина",
            "Классический метод диагностики дальтонизма. Определение цифр и фигур на цветном фоне.",
            "#4A90D9",
        ),
        (
            "Тест Ишихары",
            "Международный стандарт проверки цветового зрения. Серия пластин с точками.",
            "#E05C5C",
        ),
        (
            "Тест Фарнсворта-Манселла",
            "Глубокий анализ цветовосприятия. Расположите цветовые фишки в порядке плавного перехода оттенка.",
            "#D4A017",
        ),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")

        w = QWidget()
        w.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(36, 30, 36, 30)
        lay.setSpacing(14)

        h1 = QLabel("Тестирование зрения")
        h1.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        h1.setStyleSheet("color:#fff;")
        lay.addWidget(h1)

        h2 = QLabel("Выберите тест для начала диагностики")
        h2.setFont(QFont("Segoe UI", 11))
        h2.setStyleSheet("color:#444;")
        lay.addWidget(h2)

        lay.addSpacing(8)

        for title, desc, color in self.TESTS:
            lay.addWidget(TestCard(title, desc, color, lambda t=title: self._open(t)))

        lay.addStretch()
        scroll.setWidget(w)
        root.addWidget(scroll)

    def _open(self, name: str):
        StubDialog(name, self).exec()
