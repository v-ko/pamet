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
    from PySide6.QtWidgets import QApplication

    import misli
    from misli.gui.desktop_app import QtMainLoop

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

from operator import index
from typing import Callable, Dict, Union, List, Any
from collections import defaultdict
from enum import Enum
from copy import copy
from dataclasses import MISSING

from misli.pubsub.main_loop import MainLoop, NoMainLoop
from misli import get_logger

log = get_logger(__name__)

# --------------Main loop related-------------------
_main_loop = NoMainLoop()


@log.traced
def set_main_loop(main_loop: MainLoop):
    """Swap the main loop that the module uses. That's needed in order to make
    the GUI swappable (and most frameworks have their own mechanisms).
    """
    global _main_loop
    _main_loop = main_loop


def main_loop() -> MainLoop:
    """Get the main loop object"""
    return _main_loop


def call_delayed(callback: Callable,
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

    if not callback:
        raise Exception('Callback cannot be None')

    _main_loop.call_delayed(callback, delay, args, kwargs)


# --------------Dispatcher related-------------------
_subscriptions = {}  # by id
_channels = {}


class SubscriptionTypes(Enum):
    CHANNEL = 1
    ENTITY = 2
    INVALID = 0


class Subscription:

    def __init__(self, handler, channel_name, index_val: Any = MISSING):
        self.id = id(self)
        self.handler = handler
        self.channel_name = channel_name
        self.index_val = index_val


class Channel:

    def __init__(self,
                 name: str,
                 index_key: Callable = None,
                 filter_key: Callable = None):
        self.name = name
        self.index_key = index_key
        self.filter_key = filter_key
        self.message_stack = []
        self.subscribtions: Dict[Callable, Subscription] = {}

        # if index_key:
        self.index = defaultdict(list)

        if name in _channels:
            raise Exception('A channel with this name already exists')
        _channels[name] = self

    def __repr__(self):
        return f'<Channel name={self.name}>'

    # @log.traced
    def push(self, message):
        if self.filter_key:
            # Remove this exception to test
            raise Exception(
                'This mechanism is not tested. It might just work though')
            if not self.filter_key(message):
                return

        log.info('^^PUSH^^ on "%s": %s' % (self.name, message))

        # if self.index_key:
        #     self.index[self.index_key(message)].append(message)

        # self.message_stack.append(message)
        # call_delayed(_invoke_handlers, 0)

        for handler, sub in self.subscribtions.items():
            if self.index_key and sub.index_val is not MISSING:
                if self.index_key(message) != sub.index_val:
                    continue

            log.info(f'Queueing {handler=} for {message=} on'
                     f' channel_name={sub.channel_name}')
            call_delayed(handler, 0, args=[message])

    @log.traced
    def subscribe(self, handler, index_val: Any = MISSING):
        return subscribe(self.name, handler=handler, index_val=index_val)

    def add_subscribtion(self, subscribtion):
        if subscribtion.handler in self.subscribtions:
            raise Exception(
                f'Handler {subscribtion.handler} already added to channel '
                f'{self.name}')

        self.subscribtions[subscribtion.handler] = subscribtion

    def remove_subscribtion(self, subscribtion):
        if subscribtion.handler not in self.subscribtions:
            raise Exception(
                f'Cannot unsubscribe missing handler {subscribtion.handler}'
                f' in channel {self.name}')

        self.subscribtions.pop(subscribtion.handler)

    def notify_subscribers(self):
        if not self.message_stack:
            return

        # Iterate over a copy of the subscriptions, since an additional handler
        # can get added while executing the present handlers
        for handler, sub in copy(self.subscribtions).items():
            # If the channel is not indexed or the subscriber does not filter
            # messages using the index - notify for all messages
            if not self.index_key or sub.filter_val is MISSING:
                messages = self.message_stack
            else:
                messages = self.index.get(sub.filter_val, [])

            for message in messages:
                log.info(f'Calling {handler=} for {message=} on'
                         f' channel_name={sub.channel_name}')
                handler(message)

        self.message_stack.clear()
        self.index.clear()


def channel_names() -> List[str]:
    """Get the registered channels list"""
    return list(_channels)


@log.traced
def add_channel(channel_name: str, index_key: Callable = None):
    """Register a new channel

    Args:
        channel_name (str): The name of the channel

    Raises:
        Exception: If a channel with this name already exists
    """
    return Channel(channel_name, index_key)


@log.traced
def remove_channel(channel_name: str):
    """Deregister a channel.

    Args:
        channel_name (str): The name of the channel

    Raises:
        Exception: When trying to remove a non-existent channel
    """
    if channel_name not in _channels:
        raise Exception('Trying to delete non-existent channel')

    del _channels[channel_name]


# Channel interface
def subscribe(channel_name: str, handler: Callable, index_val: Any = MISSING):
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
    if channel_name not in channel_names():
        raise Exception('No such channel')

    sub = Subscription(handler, channel_name, index_val)

    _channels[channel_name].add_subscribtion(sub)
    _subscriptions[sub.id] = sub

    return sub.id


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

    _channels[sub.channel_name].remove_subscribtion(sub)
    _subscriptions.pop(sub.id)


def dispatch(message: object, channel_name: str):
    """Dispatch a message on the specified channel.

    Args:
        message (object): The message to be dispatched
        channel (str): The name of the channel to be used
    """
    _channels[channel_name].push(message)


# @log.traced
def _invoke_handlers():
    """Handle the dispatched messages, by invoking all relevant handlers.
    Gets queued on the main loop with each dispatch.
    """
    for channel_name, channel in _channels.items():
        channel.notify_subscribers()
