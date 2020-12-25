import random
import uuid
from .constants import ALIGNMENT_GRID_UNIT


def get_new_id():
    guid = str(uuid.UUID(int=random.getrandbits(128)))[:8]
    return guid


def find_many_by_props(item_list, **props):
    if type(item_list) == dict:
        item_list = [val for key, val in item_list.items()]

    elif type(item_list) == list:
        pass

    else:
        raise ValueError

    for item in item_list:
        item_state = item.state()

        skip = False
        for key, value in props.items():
            if key not in item_state:
                skip = True
                continue

            if item_state[key] != value:
                skip = True

        if not skip:
            yield item


def find_one_by_props(item_list, **props):
    items_found = list(find_many_by_props(item_list, **props))

    if not items_found:
        return None

    return items_found[0]


def snap_to_grid(x):
    return round(x / ALIGNMENT_GRID_UNIT) * ALIGNMENT_GRID_UNIT