"""The misli facade offers a pub/sub mechanism to dispatch messages.

It supports adding named channels on which to subscribe handlers and then
dispatch messages (which are arbitrary python objects).

Example usage with the NoMainLoop implementation (default):
    import misli

    misli.add_channel('main')
    misli.subscribe('main', lambda x: print(x))
    misli.dispatch(message='Test', channel_name='main')
    misli.main_loop().process_events()  # Would not be needed when using a proper main loop
    # Prints ['Test']

Example usage with Qt:
    from PySide2.QtWidgets import QApplication

    import misli
    from misli.gui.desktop import QtMainLoop

    app = QApplication()
    misli.set_main_loop(QtMainLoop())

    misli.add_channel('main')
    misli.subscribe('main', lambda x: print(x))
    misli.dispatch(message='Test', channel_name='main')

    app.exec_()
    # Prints ['Test']

The main loop can be swapped with different implementations in order to
accomodate different GUI frameworks. The implementations that are actually
used can be found in misli_gui (Qt) and misli_brython (JS).

Dispatching and invoking the handlers are both done on the same thread, so
it's expected that the subscribed callables are light, since the main purpose
of misli is GUI rendering and blocking the main loop would cause freezing.
"""

from typing import Callable, Union
from collections import defaultdict
from enum import Enum
from copy import deepcopy

from misli.main_loop import NoMainLoop
from misli import get_logger


log = get_logger(__name__)

# --------------Main loop related-------------------
_main_loop = NoMainLoop()


@log.traced
def set_main_loop(main_loop):
    """Swap the main loop that the module uses. That's needed in order to make
    the GUI swappable (and most frameworks have their own mechanisms).
    """
    global _main_loop
    _main_loop = main_loop


def main_loop():
    """Get the main loop object"""
    return _main_loop


def call_delayed(
        callback: Callable,
        delay: float = 0,
        args: list = None,
        kwargs: dict = None):
    """Call a function with a delay on the main loop.

    Args:
        callback (Callable): The callable to be invoked
        delay (float, optional): The delay in seconds. Defaults to 0.
        args (list, optional): A list with the arguments. Defaults to None.
        kwargs (dict, optional): A dictionary with the keyword arguments.
            Defaults to None.
    """
    args = args or []
    kwargs = kwargs or {}

    log.debug('Will call %s delayed with %s secs' % (callback.__name__, delay))
    _main_loop.call_delayed(callback, delay, args, kwargs)


# --------------Dispatcher related-------------------
_subscriptions = {}  # by id
_channel_subscriptions = defaultdict(list)  # Per channel lists

# The implementation of per entity subscribtions is commented out, since it
# turned out to be redundant for the time being and no testing was done.
# Otherwise the idea was to reduce lookup overhead for channels with a lot of
# subscriptions.
# _per_entity_subscriptions = defaultdict(list)  # [(channel, entity_id)] = list

_message_stacks = {}
_subscription_keys_by_id = dict


class SubscriptionTypes(Enum):
    CHANNEL = 1
    ENTITY = 2
    INVALID = 0


class Subscription:
    def __init__(self, handler, sub_type, channel, entity_id):
        self.id = id(self)
        self.handler = handler
        self.type = sub_type
        self.channel = channel
        self.entity_id = entity_id

    # @classmethod
    # def channel_type(cls, channel, handler):
    #     return cls(handler, SubscriptionTypes.CHANNEL, channel, None)

    # @classmethod
    # def entity_type(cls, channel, entity_id, handler):
    #     return cls(handler, SubscriptionTypes.ENTITY, channel, entity_id)


def channels():
    """Get the registered channels list"""
    return list(_message_stacks.keys())


@log.traced
def add_channel(channel_name: str):
    """Register a new channel

    Args:
        channel_name (str): The name of the channel

    Raises:
        Exception: If a channel with this name already exists
    """

    if channel_name in _message_stacks:
        raise Exception('Channel already exists')
    _message_stacks[channel_name] = []


@log.traced
def remove_channel(channel_name: str):
    """Deregister a channel.

    Args:
        channel_name (str): The name of the channel

    Raises:
        Exception: When trying to remove a non-existent channel
    """
    if channel_name not in _message_stacks:
        raise Exception('Trying to delete non-existent channel')

    del _message_stacks[channel_name]


# Channel interface
@log.traced
def subscribe(channel_name: str, handler: Callable):
    """Subscribe a function to be invoked for every message on the channel.

    Args:
        channel (str): The channel name
        handler (Callable):

    Raises:
        Exception: [description]
        Exception: [description]

    Returns:
        [type]: [description]
    """
    if channel_name not in channels():
        raise Exception('No such channel')

    if handler in _channel_subscriptions[channel_name]:
        raise Exception('Handler %s already added to channel %s' %
                        (handler, channel_name))

    sub = Subscription(handler, SubscriptionTypes.CHANNEL, channel_name, None)

    _channel_subscriptions[channel_name].append(handler)
    _subscriptions[sub.id] = sub

    return sub.id


# def subscribe_to_entity(channel, entity_id, handler):
#     sub = Subscription.entity_type(channel, entity_id, handler)
#
#     _per_entity_subscriptions[(channel, entity_id)].append(handler)
#     _subscriptions[sub.id] = sub
#
#     return sub.id


def subscription(subscription_id: str) -> Union[Subscription, None]:
    """Get a subscription by id. If not present - returns None"""
    if subscription_id not in _subscriptions:
        return None

    return _subscriptions[subscription_id]


@log.traced
def unsubscribe(subscription_id):
    """Deactivate the subscription with the specified id"""
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


# @log.traced
def dispatch(message: object, channel_name: str):
    """Dispatch a message on the specified channel.

    Args:
        message (object): The message to be dispatched
        channel (str): The name of the channel to be used
    """
    log.info('DISPATCH on "%s": %s' % (channel_name, message))

    _message_stacks[channel_name].append(message)
    call_delayed(_invoke_handlers, 0)


@log.traced
def _invoke_handlers():
    """Handle the dispatched messages, by invoking all relevant handlers.
    Gets queued on the main loop with each dispatch.
    """
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
