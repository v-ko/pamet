from typing import List, Union, Callable

import misli
from misli import Entity, Change
from misli.storage.repository import Repository

log = misli.get_logger(__name__)

_repo: Repository = None
_repo_subscription_id = None

ENTITY_CHANGE_CHANNEL = '__ENTITY_CHANGES__'
ENTITY_CHANGE_BY_ID_CHANNEL = '__ENTITY_CHANGES_BY_ID__'
misli.add_channel(ENTITY_CHANGE_CHANNEL)
misli.add_channel(ENTITY_CHANGE_BY_ID_CHANNEL,
                  index_key=lambda x: x.last_state().id)


def publish_entity_change(change: Change):
    misli.dispatch(change, ENTITY_CHANGE_CHANNEL)
    misli.dispatch(change, ENTITY_CHANGE_BY_ID_CHANNEL)


def on_entity_changes(handler: Callable):
    misli.subscribe(ENTITY_CHANGE_CHANNEL, handler)


@log.traced
def repo():
    return _repo


@log.traced
def set_repo(repo):
    global _repo
    global _repo_subscription_id

    log.info('Setting repo to %s' % repo.path)

    if _repo_subscription_id:
        misli.unsubscribe(_repo_subscription_id)

    _repo = repo
    _repo_subscription_id = misli.subscribe(ENTITY_CHANGE_CHANNEL,
                                            repo.save_changes)


def insert(entity_or_batch: Union[Entity, List[Entity]]):
    batch = entity_or_batch
    if not isinstance(entity_or_batch, list):
        batch = [entity_or_batch]

    for entity in batch:
        change = Change.CREATE(entity)
        publish_entity_change(change)


def remove(entity_or_batch: Union[Entity, List[Entity]]):
    batch = entity_or_batch
    if not isinstance(entity_or_batch, list):
        batch = [entity_or_batch]

    for entity in batch:
        change = Change.DELETE(entity)
        publish_entity_change(change)


def update(entity_or_batch: Union[Entity, List[Entity]]):
    batch = entity_or_batch
    if not isinstance(entity_or_batch, list):
        batch = [entity_or_batch]

    # changes = []
    for entity in batch:
        old_state = find_one(gid=entity.gid())
        if not old_state:
            raise Exception(f'Cannot update missing entity {entity}')

        # changes.append(Change.UPDATE(old_state, entity))
        change = Change.UPDATE(old_state, entity)

        # for change in changes:
        publish_entity_change(change)


def find(**filter):
    return _repo.find(**filter)


def find_one(**filter):
    found = list(_repo.find(**filter))
    if found:
        return found[0]
    else:
        return None
