from dataclasses import dataclass, field
from typing import Optional
from .config_loader import ConfigLoader, DiseaseConfig


DISEASE_KEYWORDS = {
    "myopia": ["миопия", "близорукость", "myopia"],
    "hyperopia": ["гиперметропия", "дальнозоркость", "hyperopia"],
}

MYOPIA_LEVELS    = {"-1", "-2", "-3", "-4", "-5", "-6"}
HYPEROPIA_LEVELS = {"+1", "+2", "+3", "+4", "+5", "+6"}

MYOPIA_LEVEL_MAP = {
    "слабая (-1)": "-1", "слабая (-2)": "-2",
    "средняя (-3)": "-3", "средняя (-4)": "-4",
    "высокая (-5)": "-5", "высокая (-6)": "-6",
}
HYPEROPIA_LEVEL_MAP = {
    "слабая (+1)": "+1", "слабая (+2)": "+2",
    "средняя (+3)": "+3", "средняя (+4)": "+4",
    "высокая (+5)": "+5", "высокая (+6)": "+6",
}

@dataclass
class ExercisePlan:
    user_id: Optional[int]
    disease: str
    level: str
    config: Optional[DiseaseConfig]
    background_file: str = "plain_white.png"
    object_hex: str = "#FFFFFF"
    object_scale: float = 1.0
    speed_ms: int = 30
    mechanic: str = ""
    exercises: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "disease": self.disease,
            "level": self.level,
            "background": self.background_file,
            "object_hex": self.object_hex,
            "object_scale": self.object_scale,
            "speed_ms": self.speed_ms,
            "mechanic": self.mechanic,
            "exercises": self.exercises,
            "notes": self.notes,
        }


class PlanBuilder:
    def __init__(self):
        self._loader = ConfigLoader()

    def build(self, user_id: Optional[int], survey_answers: dict) -> ExercisePlan:
        disease, level = self._detect_disease(survey_answers)
        config = self._loader.load(disease, level)

        plan = ExercisePlan(user_id=user_id, disease=disease, level=level, config=config)

        if config:
            plan.background_file = config.primary_color.background_file
            plan.object_hex = config.primary_color.object_hex
            plan.object_scale = config.object_scale
            plan.speed_ms = config.speed_ms
            plan.mechanic = config.object.exercise_mechanic
            plan.exercises = [
                {"name": e.name, "speed": e.speed}
                for e in config.exercises
            ]
            plan.notes = self._build_notes(config)
        else:
            plan = self._default_plan(user_id, disease, level)

        return plan

    def _detect_disease(self, answers: dict) -> tuple:
        disease_type = self._get_answer(answers, "q_disease_type")
        if disease_type in ("myopia", "hyperopia"):
            level = self._detect_level(disease_type, answers)
            return disease_type, level

        diagnosis_text = self._get_answer(answers, "q_med_003", "").lower()
        for disease, keywords in DISEASE_KEYWORDS.items():
            if any(kw in diagnosis_text for kw in keywords):
                level = self._detect_level(disease, answers)
                return disease, level

        return "healthy", "0"

    def _detect_level(self, disease: str, answers: dict) -> str:
        raw = self._get_answer(answers, "q_disease_level", "")

        if disease == "myopia" and raw in MYOPIA_LEVELS:
            return raw
        if disease == "hyperopia" and raw in HYPEROPIA_LEVELS:
            return raw

        raw_lower = raw.lower()
        if disease == "myopia":
            return MYOPIA_LEVEL_MAP.get(raw_lower, "-1")
        elif disease == "hyperopia":
            return HYPEROPIA_LEVEL_MAP.get(raw_lower, "+1")
        return "0"

    @staticmethod
    def _build_notes(config: DiseaseConfig) -> list:
        speed = config.exercises[0].speed if config.exercises else "medium"
        speed_ru = {"very_slow": "очень медленно", "slow": "медленно", "medium": "стандартно"}.get(speed, speed)
        return [
            f"Скорость: {speed_ru}",
            f"Механика: {config.object.exercise_mechanic}",
            f"Размер объекта: {config.object.size}",
        ]

    @staticmethod
    def _default_plan(user_id, disease: str, level: str) -> ExercisePlan:
        return ExercisePlan(
            user_id=user_id, disease=disease, level=level, config=None,
            exercises=[
                {"name": "circle_right", "speed": "medium"},
                {"name": "horizontal", "speed": "medium"},
                {"name": "vertical", "speed": "medium"},
            ],
            notes=["Стандартная профилактическая программа"],
        )

    @staticmethod
    def _get_answer(answers: dict, key: str, default: str = "") -> str:
        val = answers.get(key, [])
        return val[0] if val else default
