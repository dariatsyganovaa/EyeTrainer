import random
from dataclasses import dataclass, field
from typing import Optional
from .config_loader import ConfigLoader, DiseaseConfig

DISEASE_KEYWORDS = {
    "myopia":["миопия", "близорукость", "myopia"],
    "hyperopia":["гиперметропия", "дальнозоркость", "hyperopia"],
}

MYOPIA_LEVELS    = {"-1", "-2", "-3", "-4", "-5", "-6"}
HYPEROPIA_LEVELS = {"+1", "+2", "+3", "+4", "+5", "+6"}


@dataclass
class ExercisePlan:
    user_id: Optional[int]
    disease: str
    level: str
    config: Optional[DiseaseConfig]
    background_file: str = "star"
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

    SCENE_MAP = {
            "nature":    ["butterfly", "bug"], # Фон: grass.png
            "transport": ["plane", "boat"],    # Фон: sky.png / water.png
            "space":     ["star", "plane"],    # Фон: night-sky.png
            "animals":   ["mouse"],            # Фон: floor.png
            "sea":       ["bubble", "boat"]    # Фон: underwater.png / water.png
    }

    def __init__(self):
        self._loader = ConfigLoader()

    def build(self, user_id: Optional[int], survey_answers: dict) -> ExercisePlan:
        disease, level = self._detect_disease(survey_answers)
        config = self._loader.load(disease, level)

        plan = ExercisePlan(user_id=user_id, disease=disease, level=level, config=config)

        interests = survey_answers.get("q_int_001", [])
        possible_scenes = []
        for key in interests:
            possible_scenes.extend(self.SCENE_MAP.get(key, []))

        possible_scenes = list(set(possible_scenes))
        chosen_scene = random.choice(possible_scenes) if possible_scenes else "star"

        if config:
            chosen_color = random.choice(config.colors) if config.colors else None

            plan.background_file = chosen_scene
            plan.object_hex = chosen_color.object_hex if chosen_color else "#FFFFFF"
            plan.object_scale = config.object_scale
            plan.speed_ms = config.speed_ms
            plan.mechanic = config.object.exercise_mechanic
            plan.exercises = [{"name": e.name, "speed": e.speed} for e in config.exercises]
            plan.notes = self._build_notes(config)
        else:
            plan = self._default_plan(user_id, disease, level)
            plan.background_file = chosen_scene

        return plan

    def _detect_disease(self, answers: dict) -> tuple:
        disease_type = answers.get("q_disease_type", ["myopia"])[0]
        if disease_type not in ("myopia", "hyperopia"):
            return "myopia", "-1"
        level = answers.get("q_disease_level", ["-1"])[0]
        return disease_type, level

    def _detect_level(self, disease: str, answers: dict) -> str:
        raw = self._get_answer(answers, "q_disease_level", "")

        if disease == "myopia" and raw in MYOPIA_LEVELS:
            return raw
        if disease == "hyperopia" and raw in HYPEROPIA_LEVELS:
            return raw

        if disease == "myopia":
            return "-1"
        return "+1"

    @staticmethod
    def _build_notes(config: DiseaseConfig) -> list:
        speed = config.exercises[0].speed if config.exercises else "medium"
        speed_ru = {"very_slow": "очень медленно", "slow": "медленно", "medium": "стандартно"}.get(speed, speed)
        return[
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
            notes=["Стандартная программа"],
        )

    @staticmethod
    def _get_answer(answers: dict, key: str, default: str = "") -> str:
        val = answers.get(key,[])
        return val[0] if val else default
