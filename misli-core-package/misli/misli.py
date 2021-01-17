from typing import Callable

from misli.helpers import get_new_id, find_many_by_props
from misli.helpers import find_one_by_props
from misli.main_loop import NoMainLoop
from misli.change import Change, ChangeTypes

from misli import get_logger


log = get_logger(__name__)

_repo = None
_main_loop = NoMainLoop()

_entity_indices = {}

_subscribtions = {}
_change_stacks = {}


def create_entity_index(index_id):
    _entity_indices[index_id] = {}


def delete_entity_index(index_id):
    del _entity_indices[index_id]


@log.traced
def set_main_loop(main_loop):
    global _main_loop
    _main_loop = main_loop


def channels():
    return list(_change_stacks.keys())


@log.traced
def add_channel(channel_name):
    _subscribtions[channel_name] = []
    _change_stacks[channel_name] = []


@log.traced
def remove_channel(channel_name):
    if channel_name not in _change_stacks:
        raise Exception('Trying to delete non-existent channel')

    del _subscribtions[channel_name]
    del _change_stacks[channel_name]


def call_delayed(
        callback: Callable,
        delay: float,
        args: list = None,
        kwargs: dict = None):

    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    log.debug('Will call %s delayed with %s secs' % (callback.__name__, delay))
    _main_loop.call_delayed(callback, delay, args, kwargs)


# Change channel interface
@log.traced
def dispatch(change: Change, channel: str):
    log.info(str(change))

    _change_stacks[channel].append(change)
    call_delayed(_handle_changes, 0)


@log.traced
def subscribe(handler: Callable, channel: str):
    if channel not in channels():
        raise Exception('No such channel')

    if handler in _subscribtions[channel]:
        raise Exception('Handler %s already added to channel %s' %
                        (handler, channel))

    _subscribtions[channel].append(handler)


@log.traced
def unsubscribe(handler: Callable, channel: str):
    if channel not in _subscribtions:
        raise Exception('No such channel')

    if handler not in _subscribtions[channel]:
        raise Exception('Trying to remove missing handler %s form channel %s' %
                        (handler, channel))

    _subscribtions[channel].remove(handler)


@log.traced
def repo():
    return _repo


@log.traced
def set_repo(repo, updates_channel: str):
    global _repo
    log.info('Setting repo to %s' % repo.path)

    _repo = repo
    subscribe(repo.save_changes, updates_channel)


@log.traced
def _handle_changes():
    for channel in channels():
        if not _change_stacks[channel]:
            return

        for handler in _subscribtions[channel]:
            handler(_change_stacks[channel])

        _change_stacks[channel].clear()


# -------------Entity CRUD-------------
@log.traced
def add_entity(_entity, index_id):
    if not _entity.id:
        _entity.id = get_new_id()

    load_entity(_entity, index_id)
    change = Change(
        ChangeTypes.CREATE, old_state={}, new_state=_entity.asdict())
    dispatch(change, 'all')


@log.traced
def load_entity(_entity, index_id):
    if entity(_entity.id, index_id):
        raise Exception('Entity already exists')

    _entity_indices[index_id][_entity.id] = _entity


@log.traced
def unload_entity(_entity, index_id):
    if not entity(_entity.id, index_id):
        raise Exception('Cannot unload missing entity %s' % _entity)

    del _entity_indices[index_id][_entity.id]


@log.traced
def entities(index_id):
    return [entity.copy()
            for eid, entity in _entity_indices[index_id].items()]


# @log.traced
def entity(entity_id, index_id):
    if entity_id not in _entity_indices[index_id]:
        return None

    return _entity_indices[index_id][entity_id].copy()


@log.traced
def find_entities(index_id, **props):
    if index_id not in _entity_indices:
        return []

    return find_many_by_props(_entity_indices[index_id], **props)


@log.traced
def find_entity(index_id, **props):
    if index_id not in _entity_indices:
        return None

    return find_one_by_props(_entity_indices[index_id], **props)


@log.traced
def update_entity(new_entity, index_id):
    ent = entity(new_entity.id, index_id)

    if not ent:
        log.error('Cannot update missing entity %s' % new_entity)
        return

    old_state = ent.asdict()
    _entity_indices[index_id][ent.id] = new_entity

    change = Change(ChangeTypes.UPDATE, old_state, new_entity.asdict())
    dispatch(change, 'all')


@log.traced
def remove_entity(entity_id, index_id):
    ent = entity(entity_id, index_id)

    if not ent:
        log.error('Could not delete missing entity %s' % entity_id)
        return

    unload_entity(ent, index_id)
    change = Change(ChangeTypes.DELETE, old_state=ent.state(), new_state={})
    dispatch(change, 'all')
