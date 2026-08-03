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

from .agents import (
    AthleteAgent,
    EnvironmentAgent,
    GarminAgent,
    GPSAgent,
    MetabolismAgent,
    SensorAgent,
    StravaAgent,
)
from .algorithms import (
    ALL_ALGORITHMS,
    Algorithm,
    EnergyModel,
    FatigueModel,
    MetabolismModel,
    ModelResult,
    MovementModel,
    NutritionModel,
    PerformanceModel,
    PowerModel,
    RecoveryModel,
    RouteDifficultyModel,
    TrainingLoadModel,
)
from .knowledge import Insight, KnowledgeEngine
from .models import Activity, AnalysisContext, Athlete, Bike, MetabolicDailySummary, MetabolicProfile, WorldObject
from .orchestrator import AIOrchestrator
from .simulation import ScenarioOverride, SimulationComparison, SimulationEngine
from .transformer import TransformerEngine
from .units import Quantity, UnitRegistry, convert, q

__all__ = [
    # core
    "Quantity", "q", "UnitRegistry", "convert",
    "TransformerEngine",
    "Athlete", "Bike", "Activity", "WorldObject", "AnalysisContext",
    "MetabolicProfile", "MetabolicDailySummary",
    # algorithms
    "Algorithm", "ModelResult", "ALL_ALGORITHMS",
    "MovementModel", "EnergyModel", "PerformanceModel", "FatigueModel",
    "RouteDifficultyModel", "RecoveryModel", "NutritionModel",
    "PowerModel", "TrainingLoadModel", "MetabolismModel",
    # simulation / knowledge / agents / orchestrator
    "SimulationEngine", "ScenarioOverride", "SimulationComparison",
    "KnowledgeEngine", "Insight",
    "GPSAgent", "AthleteAgent", "EnvironmentAgent", "SensorAgent",
    "MetabolismAgent", "StravaAgent", "GarminAgent",
    "AIOrchestrator",
]
