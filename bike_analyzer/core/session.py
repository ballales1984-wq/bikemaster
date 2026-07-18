"""Nuovo dominio della Super App: spine che unisce tracking, salute e AI.

Entita' pure (nessuna dipendenza da DB/provider). Estendono il modello esistente
in modo retro-compatibile: `Ride` resta valido, `SessionData` ne e' il superset.

Componenti principali:
- ``ActivityType`` - enum dei tipi di attivita' tracciabili.
- ``SessionMode`` - enum delle modalita' di tracciamento (live, background, off).
- ``SensorSample`` - lettura istantanea di sensori (HR, cadenza, potenza).
- ``SessionData`` - stream grezzo di una sessione di tracciamento.
- ``HealthSample`` - campione dati salute (sonno, HRV, passi, peso).
- ``FusionRecord`` - snapshot fuso per l'AI Coach (salute + meteo + traffico + stato).
- ``Recommendation`` - output strutturato dell'AI Coach.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .models import GPSPoint, Ride


class ActivityType(str, Enum):
    """Tipo di attivita' tracciata (superset di `ride`).

    I valori supportati includono: corsa, camminata, hiking, ciclismo,
    attivita' indoor e altro.
    """

    RIDE = "ride"
    WALK = "walk"
    HIKE = "hike"
    RUN = "run"
    INDOOR = "indoor"
    OTHER = "other"

    @classmethod
    def values(cls) -> list[str]:
        """Lista dei valori enum delle attivita' sportive supportate."""
        return [m.value for m in cls]


class SessionMode(str, Enum):
    """Modalita' di tracciamento.

    - LIVE: uscita ufficiale tracciata e salvata.
    - BACKGROUND: tracciamento informale in background.
    - OFF: tracciamento disattivo.
    """

    LIVE = "live"
    BACKGROUND = "background"
    OFF = "off"


class HealthMetricType(str, Enum):
    """Tipi di campione salute supportati.

    Include metriche native del dispositivo e quelle importate da
    Google Fit / Apple Health.
    """

    SLEEP_HOURS = "sleep_hours"
    HRV_MS = "hrv_ms"
    STEPS = "steps"
    RESTING_HR = "resting_hr"
    WEIGHT_KG = "weight_kg"
    BLOOD_OXYGEN = "blood_oxygen"


@dataclass
class SensorSample:
    """Lettura sensore istantanea associata a un punto GPS.

    Attributes:
        timestamp: Timestamp UTC del campione.
        heart_rate: Frequenza cardiaca in bpm (opzionale).
        cadence: Cadenza di pedalata in rpm (opzionale).
        power: Potenza istantanea in watt (opzionale).
    """

    timestamp: datetime
    heart_rate: float | None = None
    cadence: float | None = None
    power: float | None = None


@dataclass
class SessionData:
    """Stream grezzo di una sessione di tracciamento (live o background).

    È l'ingresso del `UnifiedMetricsEngine`: contiene GPS + sensori + metadati,
    ma NON ancora metriche calcolate.
    """

    athlete_id: int | None
    tenant_id: int = 0
    mode: SessionMode = SessionMode.LIVE
    activity_type: ActivityType = ActivityType.RIDE
    started_at: datetime = field(default_factory=datetime.now)
    points: list[GPSPoint] = field(default_factory=list)
    sensor_samples: list[SensorSample] = field(default_factory=list)
    title: str | None = None
    is_official: bool = True
    source: str = "gps_tracking"

    def to_ride(self) -> Ride:
        """Promuove la sessione a `Ride` (entità di storage esistente)."""
        gps = self.points
        total_distance = sum(
            gps[i].distance_to(gps[i - 1]) for i in range(1, len(gps))
        ) if len(gps) > 1 else 0.0
        duration = 0.0
        if gps:
            span = (gps[-1].timestamp - gps[0].timestamp).total_seconds()
            duration = span / 60.0
        hr_values = [s.heart_rate for s in self.sensor_samples if s.heart_rate]
        return Ride(
            athlete_id=self.athlete_id,
            tenant_id=self.tenant_id,
            date=self.started_at.date().isoformat(),
            distance_km=total_distance / 1000.0,
            duration_minutes=duration,
            avg_speed_kmh=(total_distance / 1000.0) / (duration / 60.0) if duration else 0.0,
            heart_rate_avg=sum(hr_values) / len(hr_values) if hr_values else None,
            title=self.title,
            gps_points=gps,
            external_source=None,
            external_id=None,
            activity_type=self.activity_type.value,
            is_official=self.is_official,
            source=self.source,
        )


@dataclass
class HealthSample:
    """Campione dati salute (sonno, HRV, passi, peso, ecc.)."""

    athlete_id: int
    date: str
    metric_type: HealthMetricType
    value: float
    tenant_id: int = 0
    source: str = "manual"

    def to_dict(self) -> dict[str, Any]:
        """Serializza il campione salute in dizionario JSON-compatibile."""
        return {
            "athlete_id": self.athlete_id,
            "tenant_id": self.tenant_id,
            "date": self.date,
            "metric_type": self.metric_type.value,
            "value": self.value,
            "source": self.source,
        }


@dataclass
class FusionRecord:
    """Snapshot fuso pronto per l'AI Coach: salute + meteo + traffico + stato.

    È l'unico input che l'AI Coach deve consumare (mai sorgenti grezze).
    """

    athlete_id: int
    tenant_id: int = 0
    date: str = ""
    activity: dict[str, Any] | None = None
    health: list[dict[str, Any]] = field(default_factory=list)
    weather: dict[str, Any] | None = None
    traffic_risk: float | None = None
    fitness_state: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serializza il record fusion in dizionario JSON-compatibile."""
        return {
            "athlete_id": self.athlete_id,
            "tenant_id": self.tenant_id,
            "date": self.date,
            "activity": self.activity,
            "health": self.health,
            "weather": self.weather,
            "traffic_risk": self.traffic_risk,
            "fitness_state": self.fitness_state,
        }


@dataclass
class Recommendation:
    """Output strutturato dell'AI Coach."""

    athlete_id: int
    kind: str  # recovery | nutrition | training
    text: str
    tenant_id: int = 0
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serializza la raccomandazione in dizionario JSON-compatibile."""
        return {
            "athlete_id": self.athlete_id,
            "tenant_id": self.tenant_id,
            "kind": self.kind,
            "text": self.text,
            "created_at": self.created_at or datetime.now().isoformat(),
        }
