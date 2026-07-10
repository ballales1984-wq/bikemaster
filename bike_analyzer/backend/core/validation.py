"""Re-export validation models from the canonical ``bike_analyzer.core`` package.

``api.routes`` imports ``from ..core.validation import ValidatedGPSPoint,
ValidatedRide`` which resolves to ``bike_analyzer.backend.core.validation``.
The actual definitions live in :mod:`bike_analyzer.core.validation`; this module
bridges the two paths so GPX/FIT import validation works.
"""

from bike_analyzer.core.validation import (  # noqa: F401
    ValidatedGPSPoint,
    ValidatedRide,
)

__all__ = ["ValidatedGPSPoint", "ValidatedRide"]
