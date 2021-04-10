from typing import Callable
from collections import defaultdict
from enum import Enum
from copy import deepcopy

from misli.main_loop import NoMainLoop
from misli.change import Change
from misli import get_logger


log = get_logger(__name__)

_main_loop = NoMainLoop()


class SubscriptionTypes(Enum):
    CHANNEL = 1
    ENTITY = 2
    INVALID = 0


# An implementation of per entity subscribtions is commented out, since it's
# turned out to be redundant for the time being and no testing was done
class Subscription:
    def __init__(self, handler, sub_type, channel, entity_id):
        self.id = id(self)
        self.handler = handler
        self.type = sub_type
        self.channel = channel
        self.entity_id = entity_id

    @classmethod
    def channel_type(cls, channel, handler):
        return cls(handler, SubscriptionTypes.CHANNEL, channel, None)

    @classmethod
    def entity_type(cls, channel, entity_id, handler):
        return cls(handler, SubscriptionTypes.ENTITY, channel, entity_id)


_subscriptions = {}  # by id
_channel_subscriptions = defaultdict(list)  # [channel] = list
# _per_entity_subscriptions = defaultdict(list)  # [(channel, entity_id)] = list
_message_stacks = {}
_subscription_keys_by_id = dict


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
        delay: float = 0,
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
def dispatch(message: object, channel: str):
    log.info('DISPATCH on "%s": %s' % (channel, message))

    _message_stacks[channel].append(message)
    call_delayed(_invoke_handlers, 0)


@log.traced
def subscribe(channel: str, handler: Callable):
    if channel not in channels():
        raise Exception('No such channel')

    if handler in _channel_subscriptions[channel]:
        raise Exception('Handler %s already added to channel %s' %
                        (handler, channel))

    sub = Subscription.channel_type(channel, handler)

    _channel_subscriptions[channel].append(handler)
    _subscriptions[sub.id] = sub

    return sub.id


# def subscribe_to_entity(channel, entity_id, handler):
#     sub = Subscription.entity_type(channel, entity_id, handler)
#
#     _per_entity_subscriptions[(channel, entity_id)].append(handler)
#     _subscriptions[sub.id] = sub
#
#     return sub.id


def subscription(subscription_id):
    if subscription_id not in _subscriptions:
        return None

    return _subscriptions[subscription_id]


@log.traced
def unsubscribe(subscription_id):
    sub = subscription(subscription_id)
    if not sub:
        raise Exception('Cannot unsubscribe missing subscription with id %s' %
                        subscription_id)

    if sub.type == SubscriptionTypes.CHANNEL:
        _channel_subscriptions[sub.channel].remove(sub.handler)

    # elif sub.type == SubscriptionTypes.ENTITY:
    #     _per_entity_subscriptions[(sub.channel, sub.entity_id)].remove(
    #         sub.handler)

    _subscriptions[sub.id].remove(sub)


@log.traced
def _invoke_handlers():
    for channel, messages in _message_stacks.items():
        if not _message_stacks[channel]:
            continue

        # Send the messages to the per-channel subscribers
        for handler in _channel_subscriptions[channel]:
            handler([deepcopy(m) for m in messages])

        # # Send the messages to the per-entity subscribers
        # for message in messages:
        #     change = Change(**message)
        #     entity_id = change.last_state()['id']
        #
        #     per_entity_key = (channel, entity_id)
        #     if per_entity_key in _per_entity_subscriptions:
        #         for handler in _per_entity_subscriptions[per_entity_key]:
        #             handler(message.copy())

        _message_stacks[channel].clear()
