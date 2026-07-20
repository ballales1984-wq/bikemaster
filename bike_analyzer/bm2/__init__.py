"""BikeMaster 2.0 - Knowledge/model-driven architecture.

Levels:
    RAW DATA  -> agents (GPS/Athlete/Environment/Sensor)
    TRANSFORM -> TransformerEngine (units/geo/time/quality)
    CORE MODEL-> Athlete/Bike/Activity/WorldObject
    MODEL     -> Algorithm Engine (Movement/Energy/Performance/Fatigue/...)
    SIMULATION-> Simulation Engine ("what if")
    KNOWLEDGE -> Knowledge Engine (numbers -> concepts)
    ORCHESTRATOR -> AI Orchestrator (conversational router)

Every result is a :class:`ModelResult` always containing:
result + formula + data used + precision + source.
"""

from __future__ import annotations

from .algorithms import (
    ALL_ALGORITHMS, Algorithm, EnergyModel, FatigueModel, ModelResult,
    MovementModel, NutritionModel, PerformanceModel, PowerModel,
    RecoveryModel, RouteDifficultyModel, TrainingLoadModel,
)
from .agents import (
    AthleteAgent,
    EnvironmentAgent,
    GarminAgent,
    GPSAgent,
    SensorAgent,
    StravaAgent,
)
from .knowledge import Insight, KnowledgeEngine
from .models import AnalysisContext, Athlete, Activity, Bike, WorldObject
from .orchestrator import AIOrchestrator
from .simulation import ScenarioOverride, SimulationEngine, SimulationComparison
from .transformer import TransformerEngine
from .units import Quantity, UnitRegistry, convert, q

__all__ = [
    # core
    "Quantity", "q", "UnitRegistry", "convert",
    "TransformerEngine",
    "Athlete", "Bike", "Activity", "WorldObject", "AnalysisContext",
    # algorithms
    "Algorithm", "ModelResult", "ALL_ALGORITHMS",
    "MovementModel", "EnergyModel", "PerformanceModel", "FatigueModel",
    "RouteDifficultyModel", "RecoveryModel", "NutritionModel",
    "PowerModel", "TrainingLoadModel",
    # simulation / knowledge / agents / orchestrator
    "SimulationEngine", "ScenarioOverride", "SimulationComparison",
    "KnowledgeEngine", "Insight",
    "GPSAgent", "AthleteAgent", "EnvironmentAgent", "SensorAgent",
    "StravaAgent", "GarminAgent",
    "AIOrchestrator",
]
