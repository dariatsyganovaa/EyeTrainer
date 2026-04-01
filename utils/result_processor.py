from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from repositories.user_repository import UserRepository
from utils.db_manager import DatabaseManager

@dataclass
class UserProfile:
    user_id: Optional[int] = None
    has_vision_problems: bool = False
    wears_glasses: bool = False
    eye_diseases: str = ""
    interests: list = field(default_factory=list)
    training_format: str = ""
    color_scheme: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SurveyAnswer:
    question_id:   str
    question_text: str
    answer:        list


@dataclass
class SurveyResult:
    survey_id: str = ""
    answers: list = field(default_factory=list)
    completed_at: datetime = field(default_factory=datetime.utcnow)


BOOL_YES = {"да", "yes"}

DISEASES_MAP = {
    "Миопия слабой степени": "miopia1",
    "Миопия средней степени": "miopia2",
    "Миопия высокой степени": "miopia3",
    "Гиперметропия слабой степени": "hyperopia1",
    "Гиперметропия средней степени": "hyperopia2",
    "Гиперметропия высокой степени": "hyperopia3"
}

REVERSE_DISEASES_MAP = {v: k for k, v in DISEASES_MAP.items()}

DISEASE_RECOMMENDATIONS = {
    "miopia1": "Лёгкие упражнения на расслабление глаз",
    "miopia2": "Упражнения на фокусировку вдаль",
    "miopia3": "Ограничить нагрузку, добавить частые перерывы",
    "hyperopia1": "Лёгкие упражнения на фокусировку вблизи",
    "hyperopia2": "Регулярные упражнения на аккомодацию",
    "hyperopia3": "Щадящий режим + упражнения на ближний фокус",
}

INTERESTS_MAP = {
    "Природа": "nature",
    "Технологии": "tech",
    "Спорт": "sport",
    "Искусство": "art",
    "Архитектура": "architecture",
}

FORMAT_MAP = {
    "Классический": "classic",
    "Игровой": "game",
    "Интерактивный":"interactive",
}

SCHEME_MAP = {
    "Светлая": "light",
    "Темная": "dark",
}

BACKGROUND_MAP = {
    "nature": "forest_light.png",
    "tech": "plain_dark.png",
    "sport": "meadow_sunny.png",
    "art": "plain_white.png",
    "architecture": "sky_blue_clear.png",
}

class ResultProcessor:
    def process(self, result: SurveyResult) -> dict:
        profile = self._build_profile(result)
        user_id = self._save_to_db(profile, result)
        profile.user_id = user_id
        plan = self._make_plan(profile)
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

            if qid == "q_med_001":
                profile.has_vision_problems = self._to_bool(values)
            elif qid == "q_med_002":
                profile.wears_glasses = self._to_bool(values)
            elif qid == "q_med_003":
                raw = values[0] if values else ""
                profile.eye_diseases = DISEASES_MAP.get(raw, raw)
            elif qid == "q_int_001":
                profile.interests = [
                    INTERESTS_MAP.get(v, v.lower()) for v in values
                ]
            elif qid == "q_pref_001":
                v = values[0] if values else ""
                profile.training_format = FORMAT_MAP.get(v, v.lower())
            elif qid == "q_pref_002":
                v = values[0] if values else ""
                profile.color_scheme = SCHEME_MAP.get(v, v.lower())

            if profile.eye_diseases:
                profile.has_vision_problems = True
        return profile

    @staticmethod
    def _to_bool(values: list) -> bool:
        return bool(values) and values[0].strip().lower() in BOOL_YES

    def _make_plan(self, profile: UserProfile) -> dict:
        background = "plain_white.png"
        for interest in profile.interests:
            if interest in BACKGROUND_MAP:
                background = BACKGROUND_MAP[interest]
                break

        speed = "slow" if (profile.has_vision_problems or profile.eye_diseases) else "medium"

        repeat = profile.has_vision_problems

        notes = []
        if profile.has_vision_problems:
            notes.append("Рекомендованы медленные упражнения")
        if profile.wears_glasses:
            notes.append("Пользователь носит очки/линзы")
        if profile.eye_diseases:
            rec = DISEASE_RECOMMENDATIONS.get(profile.eye_diseases)
            if rec:
                notes.append(rec)
        if not notes:
            notes.append("Стандартная программа тренировок")

        return {
            "background": background,
            "color_scheme": profile.color_scheme or "dark",
            "speed": speed,
            "repeat_exercise": repeat,
            "notes": notes,
        }

    @staticmethod
    def _make_summary(profile: UserProfile, plan: dict) -> str:
        lines = []
        lines.append(f"Проблемы со зрением: {'Да' if profile.has_vision_problems else 'Нет'}")
        lines.append(f"Очки/линзы: {'Да' if profile.wears_glasses else 'Нет'}")
        if profile.eye_diseases:
            readable = REVERSE_DISEASES_MAP.get(profile.eye_diseases, profile.eye_diseases)
            lines.append(f"Диагноз: {readable}")
        if profile.interests:
            lines.append(f"Интересы: {', '.join(profile.interests)}")
        lines.append(f"Скорость упражнений: {plan['speed']}")
        lines.append(f"Фон: {plan['background']}")
        for note in plan["notes"]:
            lines.append(f"• {note}")
        return "\n".join(lines)

    def _save_to_db(self, profile: UserProfile, result: SurveyResult) -> Optional[int]:
        try:
            db = DatabaseManager()
            user_repo = UserRepository(db)

            user_id = user_repo.create_user(name="User", age=0)

            if profile.eye_diseases:
                severity = self._extract_severity(profile.eye_diseases)

                user_repo.save_medical(
                    user_id=user_id,
                    disease=profile.eye_diseases,
                    severity=severity
                )

            user_repo.save_preferences(
                user_id=user_id,
                theme=profile.color_scheme,
                interests=profile.interests
            )

            db.close()
            return user_id

        except Exception as e:
            print(f"[DB] Ошибка: {e}")
            return None

    def _extract_severity(self, disease_code: str) -> int:
        if disease_code.endswith("1"):
            return 1
        elif disease_code.endswith("2"):
            return 2
        elif disease_code.endswith("3"):
            return 3
        return 0
