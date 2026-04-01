from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Signal
from .ui_testing_tab import Ui_Form as Ui_TestingTab
from .ui_control_panel import Ui_Form as Ui_ControlPanel
from utils.data_loader import SurveyLoader
from utils.result_processor import SurveyResult, SurveyAnswer


class TestingTab(QWidget):
    survey_finished = Signal(object)

    SURVEY_PATH = "tests/test_data/example_test.json"

    def __init__(self):
        super().__init__()

        self.ui = Ui_TestingTab()
        self.ui.setupUi(self)

        self.control_widget = QWidget()
        self.cp = Ui_ControlPanel()
        self.cp.setupUi(self.control_widget)

        self.cp.horizontalLayoutWidget.setParent(None)
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.addWidget(self.cp.btnPrev)
        nav_layout.addWidget(self.cp.btnNext)
        nav_layout.addWidget(self.cp.btnFinish)
        self.control_widget.setLayout(nav_layout)
        self.control_widget.setFixedHeight(48)

        self.ui.mainLayout.addWidget(self.control_widget)
        self.control_widget.setVisible(False)

        self.questions = []
        self.current_idx = 0
        self.answers = {}
        self.button_group = None
        self._survey_id = ""

        self.ui.groupBox.setVisible(False)
        self.ui.labelProgress.setVisible(False)
        self.ui.progressBar.setVisible(False)

        self.ui.btnStart.clicked.connect(self._on_start)
        self.cp.btnPrev.clicked.connect(self._on_prev)
        self.cp.btnNext.clicked.connect(self._on_next)
        self.cp.btnFinish.clicked.connect(self._on_finish)

    def _on_start(self):
        loader = SurveyLoader()
        survey = loader.load(self.SURVEY_PATH)

        self._survey_id = survey.get("survey_info", {}).get("survey_id", "unknown")
        self.questions = loader.get_all_questions(survey)
        self.current_idx = 0
        self.answers = {}

        if not self.questions:
            self.ui.labelQuestion.setText("Нет вопросов в тесте.")
            return

        self.ui.btnStart.setVisible(False)
        self.ui.groupBox.setVisible(True)
        self.ui.labelProgress.setVisible(True)
        self.ui.progressBar.setVisible(True)
        self.control_widget.setVisible(True)
        self._show_question()

    def _on_prev(self):
        self._save_answer()
        if self.current_idx > 0:
            self.current_idx -= 1
            self._show_question()

    def _on_next(self):
        self._save_answer()
        if self.current_idx < len(self.questions) - 1:
            self.current_idx += 1
            self._show_question()

    def _on_finish(self):
        self._save_answer()
        self._finish()

    def _show_question(self):
        q = self.questions[self.current_idx]
        total = len(self.questions)

        self.ui.progressBar.setValue(int((self.current_idx / total) * 100))
        self.ui.labelProgress.setText(f"Вопрос {self.current_idx + 1} из {total}")
        self.ui.labelTitle.setText(q.get("_section_title", ""))
        self.ui.labelQuestion.setText(q.get("text", ""))

        self.cp.btnPrev.setEnabled(self.current_idx > 0)
        self.cp.btnNext.setVisible(self.current_idx < total - 1)
        self.cp.btnFinish.setVisible(self.current_idx == total - 1)

        self._clear_answers()

        q_type = q.get("type", "single_choice")
        raw_opts = q.get("options", [])
        options = [o["text"] if isinstance(o, dict) else o for o in raw_opts]
        saved = self.answers.get(self.current_idx, [])

        if q_type == "multiple_choice":
            self._build_checkboxes(options, saved)
        elif q_type == "boolean":
            self._build_radio(["Да", "Нет"], saved)
        elif q_type == "text":
            pass
        else:
            self._build_radio(options, saved)

    def _build_radio(self, options, saved):
        self.button_group = QButtonGroup(self)
        for i, opt in enumerate(options):
            rb = QRadioButton(opt)
            if opt in saved:
                rb.setChecked(True)

            rb.setStyleSheet("""
                        QRadioButton {
                            font-size: 18px;
                            padding: 10px;
                        }
                        QRadioButton::indicator {
                            width: 18px;
                            height: 18px;
                        }
                        QRadioButton:hover {
                            background-color: #2a2a2a;
                            border-radius: 8px;
                        }
                    """)

            self.button_group.addButton(rb, i)
            self.ui.answersLayout.addWidget(rb)
        self.ui.answersLayout.addStretch()

    def _build_checkboxes(self, options, saved):
        self.button_group = None
        for opt in options:
            cb = QCheckBox(opt)
            if opt in saved:
                cb.setChecked(True)

            cb.setStyleSheet("""
                        QCheckBox {
                            font-size: 18px;
                            padding: 10px;
                        }
                        QCheckBox::indicator {
                            width: 18px;
                            height: 18px;
                        }
                        QCheckBox:hover {
                            background-color: #2a2a2a;
                            border-radius: 8px;
                        }
                    """)
            self.ui.answersLayout.addWidget(cb)
        self.ui.answersLayout.addStretch()

    def _clear_answers(self):
        layout = self.ui.answersLayout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.button_group = None

    def _save_answer(self):
        q = self.questions[self.current_idx]
        layout = self.ui.answersLayout
        selected = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if not item:
                continue
            w = item.widget()
            if isinstance(w, (QRadioButton, QCheckBox)) and w.isChecked():
                selected.append(w.text())
        self.answers[self.current_idx] = SurveyAnswer(
            question_id = q.get("question_id", f"q_{self.current_idx}"),
            question_text = q.get("text", ""),
            answer = selected,
        )

    def _finish(self):
        result = SurveyResult(
            survey_id = self._survey_id,
            answers = list(self.answers.values()),
        )
        self.survey_finished.emit(result)

        self.ui.progressBar.setValue(100)
        self.ui.labelProgress.setText("Тест завершён!")
        self.ui.labelTitle.setText("Спасибо за прохождение теста.")
        self.ui.labelQuestion.setText("")
        self._clear_answers()
        self.ui.groupBox.setVisible(False)
        self.control_widget.setVisible(False)
        self.ui.btnStart.setText("Пройти ещё раз")
        self.ui.btnStart.setVisible(True)
