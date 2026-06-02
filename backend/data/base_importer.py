"""Base fetch and DTOs for data importers"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class RawPoint:
    """Unified raw point before normalization"""
    latitude: float
    longitude: float
    timestamp: datetime
    elevation: Optional[float] = None
    speed: Optional[float] = None
    heart_rate: Optional[int] = None
    cadence: Optional[int] = None
    power: Optional[int] = None
    temperature: Optional[float] = None


@dataclass
class RawRide:
    """Unified raw ride data"""
    name: str
    sport_type: str
    source: str
    external_id: Optional[str]
    points: list[RawPoint]


class BaseImporter(ABC):
    """Interface that all data importers must implement"""

    @abstractmethod
    def can_handle(self, file_path: str) -> bool:
        """Return True if this importer can process the given file"""
        raise NotImplementedError

    @abstractmethod
    def import_file(self, file_path: str, sport_type: str = "cycling") -> RawRide:
        """Parse file and return normalized RawRide"""
        raise NotImplementedError
