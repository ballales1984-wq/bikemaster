"""BikeMaster 2.0 - Model Engine: catalogo degli algoritmi."""

from __future__ import annotations

from .base import Algorithm, ModelResult
from .energy import EnergyModel
from .fatigue import FatigueModel
from .movement import MovementModel
from .nutrition import NutritionModel
from .performance import PerformanceModel
from .power_model import PowerModel
from .recovery import RecoveryModel
from .route_difficulty import RouteDifficultyModel
from .training_load import TrainingLoadModel

__all__ = [
    "Algorithm", "ModelResult",
    "MovementModel", "EnergyModel", "PerformanceModel", "FatigueModel",
    "RouteDifficultyModel", "RecoveryModel", "NutritionModel",
    "PowerModel", "TrainingLoadModel",
    "ALL_ALGORITHMS", "MODEL_REGISTRY",
]


ALL_ALGORITHMS: list[type[Algorithm]] = [
    MovementModel, EnergyModel, PerformanceModel, FatigueModel,
    RouteDifficultyModel, RecoveryModel, NutritionModel,
    PowerModel, TrainingLoadModel,
]

MODEL_REGISTRY: dict[str, type[Algorithm]] = {a.name: a for a in ALL_ALGORITHMS}
