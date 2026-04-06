import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "survey_results")

BOOL_YES = {"да", "yes", "true", "1"}


@dataclass
class SurveyAnswer:
    question_id: str
    question_text: str
    answer: list


@dataclass
class SurveyResult:
    survey_id: str  = ""
    answers: list = field(default_factory=list)
    completed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UserProfile:
    user_id: Optional[int] = None
    name: str = ""
    age: Optional[int] = None
    has_vision_problems: bool = True
    wears_glasses: bool = False
    disease_type: str = "myopia"
    disease_level: str = "-1"
    interests: list = field(default_factory=list)
    training_format: str = "classic"
    color_scheme: str = "dark"
    created_at: datetime = field(default_factory=datetime.utcnow)


class ResultProcessor:
    def process(self, result: SurveyResult) -> dict:
        profile = self._build_profile(result)

        self._save_to_json(profile, result)

        user_id = self._save_to_db(profile, result)
        profile.user_id = user_id

        plan = self._build_plan(profile, result)

        if user_id:
            self._save_plan_to_db(user_id, plan)

        summary = self._make_summary(profile, plan)

        return {
            "user_id": user_id,
            "profile": profile,
            "exercise_plan": plan,
            "summary": summary,
        }

    def _build_profile(self, result: SurveyResult) -> UserProfile:
        profile = UserProfile()
        for ans in result.answers:
            qid = ans.question_id
            values = ans.answer

            if qid == "q_name":
                profile.name = values[0].strip() if values else ""
            elif qid == "q_age":
                try:
                    profile.age = int(values[0]) if values else None
                except ValueError:
                    profile.age = None
            elif qid == "q_med_002":
                profile.wears_glasses = self._to_bool(values)
            elif qid == "q_disease_type":
                profile.disease_type = values[0] if values else "myopia"
            elif qid == "q_disease_level":
                profile.disease_level = values[0] if values else "-1"
            elif qid == "q_int_001":
                profile.interests = values
            elif qid == "q_pref_001":
                profile.training_format = values[0] if values else "classic"
            elif qid == "q_pref_002":
                profile.color_scheme = values[0] if values else "dark"
        return profile

    @staticmethod
    def _to_bool(values: list) -> bool:
        if not values:
            return False
        val = str(values[0]).strip().lower()
        return val in BOOL_YES

    def _build_plan(self, profile: UserProfile, result: SurveyResult) -> dict:
        try:
            from utils.plan_builder import PlanBuilder
            answers_dict = {
                ans.question_id: ans.answer
                for ans in result.answers
            }
            answers_dict["q_disease_type"] =[profile.disease_type]
            answers_dict["q_disease_level"] = [profile.disease_level]
            builder = PlanBuilder()
            plan = builder.build(profile.user_id, answers_dict)
            return plan.to_dict()
        except Exception as e:
            print(f"[PlanBuilder] ошибка: {e}")
            return self._fallback_plan(profile)

    @staticmethod
    def _fallback_plan(profile: UserProfile) -> dict:
        return {
            "disease": profile.disease_type,
            "level": profile.disease_level,
            "background": "plain_white.png",
            "object_hex": "#FFFFFF",
            "object_scale": 1.0,
            "speed_ms": 30,
            "exercises":[
                {"name": "circle_right", "speed": "medium"},
                {"name": "horizontal",   "speed": "medium"},
            ],
            "notes": ["Стандартная программа"],
        }

    def _save_to_json(self, profile: UserProfile, result: SurveyResult):
        try:
            os.makedirs(RESULTS_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name_slug = profile.name.replace(" ", "_") or "user"
            filename = f"{name_slug}_{timestamp}.json"
            path = os.path.join(RESULTS_DIR, filename)

            data = {
                "survey_id": result.survey_id,
                "completed_at": result.completed_at.isoformat(),
                "profile": {
                    "name": profile.name,
                    "age": profile.age,
                    "has_vision_problems": profile.has_vision_problems,
                    "wears_glasses": profile.wears_glasses,
                    "disease_type": profile.disease_type,
                    "disease_level": profile.disease_level,
                    "interests": profile.interests,
                    "training_format": profile.training_format,
                    "color_scheme": profile.color_scheme,
                },
                "answers":[
                    {
                        "question_id": a.question_id,
                        "question_text": a.question_text,
                        "answer": a.answer,
                    }
                    for a in result.answers
                ],
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[ResultProcessor] сохранено: {path}")
        except Exception as e:
            print(f"[ResultProcessor] ошибка JSON: {e}")

    @staticmethod
    def _save_to_db(profile: UserProfile, result: SurveyResult) -> Optional[int]:
        try:
            from utils.db_manager import DatabaseManager
            from repositories.user_repository import UserRepository

            db = DatabaseManager()
            repo = UserRepository(db)

            user_id = repo.create_user(name = profile.name or "Аноним", age  = profile.age or 0,  )
            if profile.disease_type or profile.has_vision_problems:
                repo.save_medical(user_id = user_id, disease = profile.disease_type, severity = 0, )
            if profile.interests or profile.color_scheme:
                repo.save_preferences(user_id = user_id, theme = profile.color_scheme or "dark", interests = profile.interests, )
            db.close()
            return user_id
        except Exception as e:
            print(f"[DB] недоступна: {e}")
            return None

    @staticmethod
    def _save_plan_to_db(user_id: int, plan: dict):
        try:
            from utils.db_manager import DatabaseManager
            from repositories.exercise_repository import ExerciseRepository
            db = DatabaseManager()
            repo = ExerciseRepository(db)
            repo.save_plan(user_id, plan)
            db.close()
        except Exception as e:
            print(f"[DB] план не сохранён: {e}")

    @staticmethod
    def _make_summary(profile: UserProfile, plan: dict) -> str:
        DISEASE_RU = {"myopia": "Миопия", "hyperopia": "Гиперметропия"}
        INTERESTS_RU = {
            "nature": "Природа", "transport": "Транспорт",
            "space": "Космос", "animals": "Животные", "sea": "Море"
        }
        SCENE_DISPLAY_RU = {
            "boat": "Катер в море", "bubble": "Пузыри под водой",
            "bug": "Жук в траве", "butterfly": "Бабочка в траве",
            "mouse": "Мышонок на полу", "plane": "Самолет в небе",
            "star": "Звезды в космосе"
        }

        lines = []
        if profile.name:
            lines.append(f"Пользователь: {profile.name}")

        lines.append(f"Диагноз: {DISEASE_RU.get(profile.disease_type)} {profile.disease_level}")

        if profile.interests:
            ints = ", ".join(INTERESTS_RU.get(i, i) for i in profile.interests)
            lines.append(f"Интересы: {ints}")

        lines.append("─" * 28)

        scene_id = plan.get("background", "star")
        lines.append(f"Сцена: {SCENE_DISPLAY_RU.get(scene_id, scene_id)}")

        for note in plan.get("notes", []):
            lines.append(f"• {note}")

        return "\n".join(lines)
