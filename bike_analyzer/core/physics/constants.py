"""Physical constants and default rider/bike parameters for the physics engine.

Reuses the same coefficients already validated in
``bike_analyzer.core.calculators.calories.calories_physics`` so the point-wise
model stays consistent with the existing ride-level estimates.
"""

from __future__ import annotations

from dataclasses import dataclass

GRAVITY = 9.81  # m/s^2
AIR_DENSITY = 1.225  # kg/m^3 (sea level, 15C)
CDA_DEFAULT = 0.4  # m^2 effective frontal area * drag coefficient
CRR_DEFAULT = 0.005  # rolling resistance coefficient (asphalt)
DRIVETRAIN_EFFICIENCY = 0.97  # fractional losses in chain/derailleur (matches calories.py)
RIDER_MASS_DEFAULT = 70.0  # kg
BIKE_MASS_DEFAULT = 8.0  # kg


@dataclass(frozen=True)
class RiderBikeParams:
    """Physical parameters describing rider + bicycle for the forward model."""

    rider_mass_kg: float = RIDER_MASS_DEFAULT
    bike_mass_kg: float = BIKE_MASS_DEFAULT
    cda: float = CDA_DEFAULT
    crr: float = CRR_DEFAULT
    rho: float = AIR_DENSITY
    drivetrain_efficiency: float = DRIVETRAIN_EFFICIENCY

    @property
    def total_mass_kg(self) -> float:
        return self.rider_mass_kg + self.bike_mass_kg
