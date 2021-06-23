from pamet.constants import ALIGNMENT_GRID_UNIT


def snap_to_grid(x):
    return round(x / ALIGNMENT_GRID_UNIT) * ALIGNMENT_GRID_UNIT
