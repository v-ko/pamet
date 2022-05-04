from copy import copy
from typing import List, Union, Callable

import misli
from misli import Entity, Change
from misli.storage.repository import Repository

log = misli.get_logger(__name__)

_repo: Repository = None


def publish_entity_change(change: Change):
    misli.channels.entity_changes.push(change)
    misli.channels.entity_changes_by_id.push(change)
    misli.channels.entity_changes_by_parent_gid.push(change)


def on_entity_changes(handler: Callable):
    misli.channels.entity_changes.subscribe(handler)


@log.traced
def repo():
    return _repo


@log.traced
def set_repo(repo):
    global _repo

    log.info('Setting repo to %s' % repo.path)
    _repo = repo


def insert(entity_or_batch: Union[Entity, List[Entity]]):
    batch = entity_or_batch
    if not isinstance(entity_or_batch, list):
        batch = [entity_or_batch]

    _repo.insert(batch)
    for entity in batch:
        change = Change.CREATE(entity)
        publish_entity_change(change)


def remove(entity_or_batch: Union[Entity, List[Entity]]):
    batch = entity_or_batch
    if not isinstance(entity_or_batch, list):
        batch = [entity_or_batch]

    _repo.remove(batch)
    for entity in batch:
        change = Change.DELETE(entity)
        publish_entity_change(change)


def update(entity_or_batch: Union[Entity, List[Entity]]):
    batch = entity_or_batch
    if not isinstance(entity_or_batch, list):
        batch = [entity_or_batch]

    _repo.update(batch)
    for entity in batch:
        old_state = find_one(gid=entity.gid())
        if not old_state:
            raise Exception(f'Cannot update missing entity {entity}')

        change = Change.UPDATE(old_state, entity)
        publish_entity_change(change)


def find(**filter):
    results = []
    for item in _repo.find(**filter):
        results.append(copy(item))
    return results


def find_one(**filter):
    found = _repo.find(**filter)

    for f in found:
        return copy(f)

    return None
