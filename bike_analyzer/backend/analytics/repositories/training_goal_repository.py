"""Training goal repository - data access abstraction for training goals."""

from __future__ import annotations


class TrainingGoalRepository:
    @staticmethod
    def is_sqlalchemy_available() -> bool:
        from ...db.postgres_db import SQLALCHEMY_AVAILABLE

        return SQLALCHEMY_AVAILABLE

    @staticmethod
    def save_training_goal(athlete_id: int, goal: dict) -> int:
        from ...db.postgres_db import save_training_goal

        return save_training_goal(athlete_id, goal)

    @staticmethod
    def get_training_goals(athlete_id: int, status: str | None = None):
        from ...db.postgres_db import get_training_goals

        return get_training_goals(athlete_id, status)

    @staticmethod
    def get_training_goal_model():
        from ...db.postgres_db import TrainingGoalModel

        return TrainingGoalModel

    @staticmethod
    def get_session():
        from ...db.postgres_db import get_session

        return get_session()
