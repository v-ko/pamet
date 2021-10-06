from typing import Generator, Any

import random
import uuid
from datetime import datetime


def get_new_id() -> str:
    """Get a random id"""
    guid = str(uuid.UUID(int=random.getrandbits(128)))[-8:]
    return guid


def find_many_by_props(
        item_list: [list, dict], **props) -> Generator[Any, None, None]:
    """Filter a list or dict and return only objets which have attributes
    matching the provided keyword arguments (key==attr_name and val==attr_val)
    """
    if isinstance(item_list, dict):
        item_list = item_list.values()

    elif isinstance(item_list, list):
        pass

    else:
        raise ValueError

    for item in item_list:
        skip = False
        for key, value in props.items():
            if not hasattr(item, key):
                skip = True
                continue

            if getattr(item, key) != value:
                skip = True

        if not skip:
            yield item


def find_one_by_props(item_list: [list, dict], **props) -> Any:
    """Convenience method to filter for one object in a list or dict with
     attributes matching the given keyword arguments.
    """
    items_found = list(find_many_by_props(item_list, **props))

    if not items_found:
        return None

    return items_found[0]


def datetime_from_string(datetime_string: str) -> datetime:
    return datetime.fromisoformat(datetime_string)


def datetime_to_string(date_time: datetime) -> str:
    return date_time.astimezone().isoformat()
