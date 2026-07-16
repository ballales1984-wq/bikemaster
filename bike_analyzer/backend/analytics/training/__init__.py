"""Training plan engine package.

Components:
- GoalAnalyzer: interprets athlete goals
- ConstraintSolver: validates real-world constraints
- WorkoutGenerator: generates concrete workouts
- PlanDistributor: distributes weekly load with periodization
- AdaptationRules: pure functions for adaptation logic
- AdaptationEngine: orchestrates plan adaptation
- ScenarioGenerator: creates alternative plan scenarios
"""

from .adaptation_engine import AdaptationEngine
from .adaptation_rules import AdaptationRules
from .constraint_solver import ConstraintSolver
from .goal_analyzer import GoalAnalyzer
from .models import (
    AdaptationEvent,
    AdaptationEventType,
    GoalType,
    PlanConstraints,
    Scenario,
    ScenarioType,
    TrainingGoal,
    WeeklyPlan,
    Workout,
    WorkoutBlock,
    WorkoutType,
)
from .plan_distributor import PlanDistributor
from .scenario_generator import ScenarioGenerator
from .workout_generator import WorkoutGenerator

__all__ = [
    "AdaptationEngine",
    "AdaptationEvent",
    "AdaptationEventType",
    "AdaptationRules",
    "ConstraintSolver",
    "GoalAnalyzer",
    "GoalType",
    "PlanConstraints",
    "Scenario",
    "ScenarioGenerator",
    "ScenarioType",
    "TrainingGoal",
    "WeeklyPlan",
    "Workout",
    "WorkoutBlock",
    "WorkoutGenerator",
    "WorkoutType",
]
