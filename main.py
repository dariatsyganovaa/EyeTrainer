import sys
import multiprocessing

from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from tabs.testing_tab import TestingTab
from tabs.diagnosis_tab import DiagnosisTab
from tabs.training_tab import TrainingTab

STYLE = """
* { font-family: 'Segoe UI'; }

QMainWindow, QWidget {
    background-color: #141414;
    color: #ffffff;
}

QTabWidget::pane {
    border: none;
    background-color: #141414;
}

QTabBar {
    background: #1a1a1a;
}

QTabBar::tab {
    background-color: #1a1a1a;
    color: #555555;
    font-size: 13px;
    font-weight: 600;
    padding: 14px 32px;
    border: none;
    border-bottom: 3px solid transparent;
    min-width: 150px;
    letter-spacing: 0.5px;
}

QTabBar::tab:selected {
    color: #ffffff;
    background-color: #141414;
    border-bottom: 3px solid #5B8DEF;
}

QTabBar::tab:hover:!selected {
    color: #aaaaaa;
    background-color: #1f1f1f;
}

QScrollBar:vertical {
    background: #1a1a1a;
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #383838;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0; }
"""


class EyeTrainerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EyeTrainer")
        self.showMaximized()
        self.setStyleSheet(STYLE)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.tab_testing   = TestingTab()
        self.tab_diagnosis = DiagnosisTab()
        self.tab_training  = TrainingTab()

        self.tabs.addTab(self.tab_testing,   "  Тестирование  ")
        self.tabs.addTab(self.tab_diagnosis, "  Диагностика   ")
        self.tabs.addTab(self.tab_training,  "  Тренировка    ")

        self.setCentralWidget(self.tabs)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

    def closeEvent(self, event):
        self.tab_training._cleanup()
        super().closeEvent(event)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    window = EyeTrainerApp()
    sys.exit(app.exec())
