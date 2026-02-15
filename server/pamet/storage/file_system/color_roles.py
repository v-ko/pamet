"""Centralized color role utilities for migration.

Provides two mappings:
- legacy_normalized_rgba_to_role: for legacy (0..1 float) RGBA values used in early schemas.
- approximate_rgba_to_role: for 0..255 RGBA tuples used in v4→v5 migration with richer role set.

Keeps original algorithms to avoid behavioral drift, just consolidates duplication.
"""
from __future__ import annotations
import math
from typing import Tuple, List
from fusion.logging import get_logger

log = get_logger(__name__)

# ---------------- Legacy (normalized 0..1) role mapping ---------------- #
LEGACY_ROLE_TO_RGBA_MAP = {
    'primary': [0.0, 0.0, 1.0, 0.1],
    'onPrimary': [0.0, 0.0, 1.0, 1.0],
    'error': [1.0, 0.0, 0.0, 0.1],
    'onError': [1.0, 0.0, 0.0, 1.0],
    'success': [0.0, 1.0, 0.0, 0.1],
    'onSuccess': [0.0, 0.64, 0.235, 1.0],
    'surfaceDim': [0.0, 0.0, 0.0, 0.1],
    'onSurface': [0.0, 0.0, 0.0, 1.0],
    'transparent': [0.0, 0.0, 0.0, 0.0],
}


def legacy_normalized_rgba_to_role(rgba_color: List[float]) -> str:
    """Return closest legacy role name for a normalized RGBA list."""
    min_distance = float('inf')
    closest_role = ''
    for role, role_rgba in LEGACY_ROLE_TO_RGBA_MAP.items():
        distance = sum((rgba_color[i] - role_rgba[i]) ** 2 for i in range(4)) ** 0.5
        if distance < min_distance:
            min_distance = distance
            closest_role = role
    return closest_role

# ---------------- New (0..255) role mapping for v5 schema ---------------- #
# Keep this aligned with the web app note colors (see TS constants)
COLOR_MAPPINGS = {
    (0, 0, 255, 26): 'primary',            # '#0000ff1a'
    (0, 0, 255, 255): 'onPrimary',         # '#0000ff'
    (255, 0, 0, 26): 'error',              # '#ff00001a'
    (255, 0, 0, 255): 'onError',           # '#ff0000'
    (0, 255, 0, 26): 'success',            # '#00ff001a'
    (0, 163, 60, 255): 'onSuccess',        # '#00a33c'
    (255, 255, 255, 255): 'surface',       # '#ffffff'
    (0, 0, 0, 255): 'onSurface',           # '#000000'
    (0, 0, 0, 26): 'surfaceDim',           # '#0000001a'
}

DEFAULT_ROLE_COLORS = {
    'primary': (0, 0, 255, 26),
    'onPrimary': (0, 0, 255, 255),
    'error': (255, 0, 0, 26),
    'onError': (255, 0, 0, 255),
    'success': (0, 255, 0, 26),
    'onSuccess': (0, 163, 60, 255),
    'surface': (255, 255, 255, 255),
    'onSurface': (0, 0, 0, 255),
    'surfaceDim': (0, 0, 0, 26),
}


def approximate_rgba_to_role(rgba: Tuple[int, int, int, int]) -> str:
    """Map 0..255 RGBA to the closest v5 role name."""
    if rgba in COLOR_MAPPINGS:
        return COLOR_MAPPINGS[rgba]
    min_distance = float('inf')
    closest_role = 'onSurface'
    for role, default_color in DEFAULT_ROLE_COLORS.items():
        distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(rgba, default_color)))
        if distance < min_distance:
            min_distance = distance
            closest_role = role
    return closest_role

