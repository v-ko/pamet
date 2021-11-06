import pamet
from pamet.constants import ALIGNMENT_GRID_UNIT


def snap_to_grid(x):
    return round(x / ALIGNMENT_GRID_UNIT) * ALIGNMENT_GRID_UNIT


def generate_default_page_id() -> str:
    base_name = 'New page'  # Could be replaced with config, translations, etc.

    page_name = base_name
    default_names_found = 0
    while True:
        if not pamet.page(name=page_name):
            return page_name
        default_names_found += 1
        page_name = f'{base_name} {default_names_found}'
