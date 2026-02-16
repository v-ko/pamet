"""Centralized color role utilities for migration.

Provides legacy_normalized_rgba_to_role for converting legacy (0..1 float)
RGBA values (used in v4 and earlier schemas) to named color roles.

The mapping and algorithm match the TypeScript old_color_to_role in
fusion/js-src/src/primitives/Color.ts.
"""
from __future__ import annotations
from typing import List
from fusion.logging import get_logger

log = get_logger(__name__)

# Legacy (normalized 0..1) role mapping — must match the TS roleToRgbaMap
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
    """Return closest legacy role name for a normalized (0..1) RGBA list.

    Uses Euclidean distance in RGBA space, matching the TS implementation.
    """
    min_distance = float('inf')
    closest_role = ''
    for role, role_rgba in LEGACY_ROLE_TO_RGBA_MAP.items():
        distance = sum((rgba_color[i] - role_rgba[i]) ** 2 for i in range(4)) ** 0.5
        if distance < min_distance:
            min_distance = distance
            closest_role = role
    return closest_role

