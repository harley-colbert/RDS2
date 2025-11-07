"""Flask blueprints for auxiliary API routes."""

from __future__ import annotations

__all__ = [
    "settings_bp",
]

from .settings import settings_bp  # noqa: E402  # import after defining __all__
