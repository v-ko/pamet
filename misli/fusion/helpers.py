from __future__ import annotations

from contextlib import contextmanager
from hashlib import md5
from typing import Generator, Any, List, Union

from collections.abc import Iterable
import random
import uuid
from datetime import datetime


_fake_time = None


@contextmanager
def fake_time(time: datetime):
    global _fake_time

    if time.tzinfo is None:
        raise Exception

    _fake_time = time
    yield
    _fake_time = None


def current_time() -> datetime:
    if _fake_time:  # For testing purposes
        return _fake_time

    return datetime.now().astimezone()


def timestamp(dt: datetime, microseconds: bool = False):
    if dt.tzinfo is None:  # If no timezone is set - assume local
        dt = dt.astimezone()
    if microseconds:
        return dt.isoformat()
    else:
        return dt.isoformat(timespec='seconds')


def get_new_id(seed=None) -> str:
    """Get a random id"""
    if seed:
        return md5(str(seed).encode('utf-8')).hexdigest()[-8:]
    guid = str(uuid.UUID(int=random.getrandbits(128)))[-8:]
    return guid


def test(item_list: Union[list, dict], **props):
    print('bla')
    yield from ['bla', 2]


def find_many_by_props(
        item_list: Union[list, dict], **props) -> Generator[Any, None, None]:
    """Filter a list or dict and return only objets which have attributes
    matching the provided keyword arguments (key==attr_name and val==attr_val)
    """
    if isinstance(item_list, dict):
        item_list = item_list.values()
    elif isinstance(item_list, Iterable):
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


def find_one_by_props(item_list: list | dict, **props) -> Any:
    """Convenience method to filter for one object in a list or dict with
     attributes matching the given keyword arguments.
    """
    items_found = list(find_many_by_props(item_list, **props))

    if not items_found:
        return None

    return items_found[0]
