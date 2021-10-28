import pamet
from pamet.constants import ALIGNMENT_GRID_UNIT


def snap_to_grid(x):
    return round(x / ALIGNMENT_GRID_UNIT) * ALIGNMENT_GRID_UNIT


def generate_default_page_id():
    base_id = 'New page'  # Could be replaced with config, translations, etc.

    page_id = base_id
    default_names_found = 0
    while True:
        if not pamet.page(page_id):
            return page_id
        default_names_found += 1
        page_id = f'{base_id} {default_names_found}'
