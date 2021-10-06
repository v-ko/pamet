from typing import List, Union

import misli
from misli import Entity, Change
from pamet.services.repository import Repository
from misli.gui import ENTITY_CHANGE_CHANNEL

log = misli.get_logger(__name__)

_repo: Repository = None


@log.traced
def repo():
    return _repo


@log.traced
def set_repo(repo, updates_channel: str):
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
        misli.dispatch(change, ENTITY_CHANGE_CHANNEL)


def remove(entity_or_batch: Union[Entity, List[Entity]]):
    batch = entity_or_batch
    if not isinstance(entity_or_batch, list):
        batch = [entity_or_batch]

    _repo.remove(batch)
    for entity in batch:
        change = Change.DELETE(entity)
        misli.dispatch(change, ENTITY_CHANGE_CHANNEL)


def update(entity_or_batch: Union[Entity, List[Entity]]):
    batch = entity_or_batch
    if not isinstance(entity_or_batch, list):
        batch = [entity_or_batch]

    changes = []
    for entity in batch:
        old_state = find_one(gid=entity.gid())
        if not old_state:
            raise Exception(f'Cannot update missing entity {entity}')

        changes.append(Change.UPDATE(old_state, entity))

    _repo.update(batch)

    for change in changes:
        misli.dispatch(change, ENTITY_CHANGE_CHANNEL)


def find(**filter):
    return _repo.find(**filter)


def find_one(**filter):
    found = _repo.find(**filter)
    if found:
        return found[0]
    else:
        return None
