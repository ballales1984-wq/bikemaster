"""Compatibility package for ``bike_analyzer.backend.core``.

Some backend modules (e.g. ``api.routes``) import validation helpers via the
relative path ``..core.validation`` which resolves to
``bike_analyzer.backend.core.validation``. The real implementation lives in
``bike_analyzer.core``. This package re-exports the needed symbols so those
imports keep working without duplicating logic.
"""
