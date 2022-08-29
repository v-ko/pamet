"""The fusion facade offers a pub/sub mechanism to dispatch messages.

It supports adding named channels on which to subscribe handlers and then
dispatch messages (which are arbitrary python objects).

Example usage with the NoMainLoop implementation (default):
    import fusion

    fusion.add_channel('main')
    fusion.subscribe('main', lambda x: print(x))
    fusion.dispatch(message='Test', channel_name='main')
    fusion.main_loop().process_events()  # Would not be needed when using a proper main loop
    # Prints ['Test']

Example usage with Qt:
    from PySide6.QtWidgets import QApplication

    import fusion
    from fusion.gui.desktop_app import QtMainLoop

    app = QApplication()
    fusion.set_main_loop(QtMainLoop())

    fusion.add_channel('main')
    fusion.subscribe('main', lambda x: print(x))
    fusion.dispatch(message='Test', channel_name='main')

    app.exec_()
    # Prints ['Test']

The main loop can be swapped with different implementations in order to
accomodate different GUI frameworks. The implementations that are actually
used can be found in misli_gui (Qt) and misli_brython (JS).

Dispatching and invoking the handlers are both done on the same thread, so
it's expected that the subscribed callables are light, since the main purpose
of fusion is GUI rendering and blocking the main loop would cause freezing.
"""

from typing import Callable, Dict, Any
from collections import defaultdict
from enum import Enum
from dataclasses import MISSING

from fusion.pubsub.main_loop import MainLoop, NoMainLoop
from fusion import get_logger

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
_channels = {}


class SubscriptionTypes(Enum):
    CHANNEL = 1
    ENTITY = 2
    INVALID = 0


class Subscription:

    def __init__(self, handler, channel, index_val: Any = MISSING):
        self.id = id(self)
        self.handler = handler
        self.channel = channel
        self.index_val = index_val

    def props(self):
        return self.handler, self.channel, self.index_val

    def unsubscribe(self):
        self.channel.remove_subscribtion(self)


class Channel:

    def __init__(self,
                 name: str,
                 index_key: Callable = None,
                 filter_key: Callable = None):
        self.name = name
        self.index_key = index_key
        self.filter_key = filter_key
        # self.message_stack = []
        self.subscriptions: Dict[tuple, Subscription] = {}  # by id

        # if index_key:
        self.index = defaultdict(list)

        if name in _channels:
            raise Exception('A channel with this name already exists')
        _channels[name] = self

    def __repr__(self):
        return f'<Channel name={self.name}>'

    @log.traced
    def push(self, message):
        if self.filter_key:
            if not self.filter_key(message):
                return

        # self.message_stack.append(message)
        # call_delayed(self.notify_subscribers)
        # !!! NO, this way messages get batched by channel and
        # the order is lost

        # # log.info('^^PUSH^^ on "%s": %s' % (self.name, message))

        for sub_props, sub in self.subscriptions.items():
            if self.index_key and sub.index_val is not MISSING:
                if self.index_key(message) != sub.index_val:
                    continue

            log.info(f'Queueing {sub.handler=} for {message=} on'
                     f' channel_name={self.name}')
            call_delayed(sub.handler, 0, args=[message])

    # @log.traced
    def subscribe(self, handler: Callable, index_val: Any = MISSING):
        sub = Subscription(handler, _channels[self.name], index_val)
        self.add_subscribtion(sub)
        return sub

    def add_subscribtion(self, subscribtion):
        if subscribtion.props() in self.subscriptions:
            raise Exception(f'Subscription with props {subscribtion.props()} '
                            f'already added to channel '
                            f'{self.name}')

        self.subscriptions[subscribtion.props()] = subscribtion

    def remove_subscribtion(self, subscribtion):
        if subscribtion.props() not in self.subscriptions:
            raise Exception(
                f'Cannot unsubscribe missing subscription with props'
                f' {subscribtion.props()}'
                f' in channel {self.name}')

        self.subscriptions.pop(subscribtion.props())

    # def notify_subscribers(self):
    # !!! NO, this way messages get batched by channel and the order is lost
    #     if not self.message_stack:
    #         return

    #     # # Iterate over a copy of the subscriptions, since an additional handler
    #     # # can get added while executing the present handlers
    #     # for sub_props, sub in copy(self.subscriptions).items():
    #     #     # If the channel is not indexed or the subscriber does not filter
    #     #     # messages using the index - notify for all messages
    #     #     if not self.index_key or sub.filter_val is MISSING:
    #     #         messages = self.message_stack
    #     #     else:
    #     #         messages = self.index.get(sub.filter_val, [])

    #     #     for message in messages:
    #     #         log.info(f'Calling {sub.handler=} for {message=} on'
    #     #                  f' channel_name={sub.channel_name}')
    #     #         sub.handler(message)

    #     for message in copy(self.message_stack):
    #         # Copy the subscriptions we iterate over, because the list can
    #         # change while executing the actions and we don't want that
    #         for sub_props, sub in copy(self.subscriptions).items():
    #             if self.index_key and sub.index_val is not MISSING:
    #                 if self.index_key(message) != sub.index_val:
    #                     continue

    #             log.info(f'Calling {sub.handler=} for {message=} on'
    #                      f' channel_name={self.name}')
    #             call_delayed(sub.handler, 0, args=[message])
    #             # !!!! sub.handler(message)
    #     self.message_stack.clear()
    #     # self.index.clear()
