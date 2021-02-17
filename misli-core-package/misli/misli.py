from typing import Callable
from collections import defaultdict
from enum import Enum

from misli.main_loop import NoMainLoop
from misli.change import Change
from misli import get_logger


log = get_logger(__name__)

_main_loop = NoMainLoop()


class SubscribtionTypes(Enum):
    CHANNEL = 1
    ENTITY = 2
    INVALID = 0


class Subscribtion:
    def __init__(self, handler, sub_type, channel, entity_id):
        self.id = id(self)
        self.handler = handler
        self.type = sub_type
        self.channel = None
        self.entity_id = None

    @classmethod
    def channel_type(cls, channel, handler):
        return cls(handler, SubscribtionTypes.CHANNEL, channel, None)

    @classmethod
    def entity_type(cls, channel, entity_id, handler):
        return cls(handler, SubscribtionTypes.ENTITY, channel, entity_id)


_subscribtions = {}  # by id
_channel_subscribtions = defaultdict(list)  # [channel] = list
_per_entity_subscribtions = defaultdict(list)  # [(channel, entity_id)] = list
_message_stacks = {}
_subscribtion_keys_by_id = dict


@log.traced
def set_main_loop(main_loop):
    global _main_loop
    _main_loop = main_loop


def channels():
    return list(_message_stacks.keys())


@log.traced
def add_channel(channel_name):
    _message_stacks[channel_name] = []


@log.traced
def remove_channel(channel_name):
    if channel_name not in _message_stacks:
        raise Exception('Trying to delete non-existent channel')

    del _message_stacks[channel_name]


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


# Channel interface
# @log.traced
def dispatch(message: dict, channel: str):
    log.info('DISPATCH on "%s": %s' % (channel, message))

    _message_stacks[channel].append(message)
    call_delayed(_invoke_handlers, 0)


@log.traced
def subscribe(channel: str, handler: Callable):
    if channel not in channels():
        raise Exception('No such channel')

    if handler in _channel_subscribtions[channel]:
        raise Exception('Handler %s already added to channel %s' %
                        (handler, channel))

    sub = Subscribtion.channel_type(channel, handler)

    _channel_subscribtions[channel].append(handler)
    _subscribtions[sub.id] = sub

    return sub.id


def subscribe_to_entity(channel, entity_id, handler):
    sub = Subscribtion.entity_type(channel, entity_id, handler)

    _per_entity_subscribtions[(channel, entity_id)].append(handler)
    _subscribtions[sub.id] = sub

    return sub.id


def subscribtion(subscribtion_id):
    if subscribtion_id not in _subscribtions:
        return None

    return subscribtion_id


@log.traced
def unsubscribe(subscribtion_id):
    sub = subscribtion(subscribtion_id)
    if not sub:
        raise Exception('Cannot unsubscribe missing subscribtion with id %s' %
                        subscribtion_id)

    if sub.type == SubscribtionTypes.CHANNEL:
        _channel_subscribtions[sub.channel].remove(sub.handler)

    elif sub.type == SubscribtionTypes.ENTITY:
        _per_entity_subscribtions[(sub.channel, sub.entity_id)].remove(
            sub.handler)

    _subscribtions.remove(sub)


@log.traced
def _invoke_handlers():
    for channel, messages in _message_stacks.items():
        if not _message_stacks[channel]:
            continue

        # Send the messages to the per-channel subscribers
        for handler in _channel_subscribtions[channel]:
            handler([m.copy() for m in messages])

        # Send the messages to the per-entity subscribers
        for message in messages:
            change = Change(**message)
            entity_id = change.last_state()['id']

            per_entity_key = (channel, entity_id)
            if per_entity_key in _per_entity_subscribtions:
                for handler in _per_entity_subscribtions[per_entity_key]:
                    handler(message.copy())

        _message_stacks[channel].clear()
