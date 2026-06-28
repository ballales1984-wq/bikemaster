"""Analytics repositories - data access layer for analytics."""

from .athlete_repository import AthleteRepository
from .fitness_state_repository import FitnessStateRepository
from .ride_repository import RideRepository
from .training_stress_repository import TrainingStressRepository
from .user_repository import UserRepository

__all__ = [
    "AthleteRepository",
    "FitnessStateRepository",
    "RideRepository",
    "TrainingStressRepository",
    "UserRepository",
]
