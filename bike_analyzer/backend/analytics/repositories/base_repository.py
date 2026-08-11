"""Base repository class for analytics repositories."""

from __future__ import annotations

from typing import Any


class BaseRepository:
    """Base class for analytics repositories.

    Provides common utility methods for lazy database imports.
    Subclasses can override as needed.
    """

    @staticmethod
    def _get_db_function(module_path: str, function_name: str) -> Any:
        """Lazy import a function from a database module.

        Args:
            module_path: Dotted path to the database module.
            function_name: Name of the function to import.

        Returns:
            The imported function.
        """
        import importlib

        module = importlib.import_module(module_path)
        return getattr(module, function_name)
