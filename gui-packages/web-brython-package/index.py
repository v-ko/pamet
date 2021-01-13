from typing import Callable
from browser import window, document, timer

import misli


class JSMainLoop:
    def call_delayed(
            self, callback: Callable, delay: float, args: list, kwargs: dict):
        timer.set_timeout(lambda: callback(*args, **kwargs), delay * 1000)


def main():
    label = document['label']
    label.text = 'LOADED, YO'
    label.style.color = 'red'

    window.misli = misli

    misli.set_main_loop(JSMainLoop())
    print('test')
    misli.create_page(id='test_page')
    misli.create_note(
        page_id='test_page', text='Test that shit out')
    print(misli.page('test_page').notes()[0].state())


if __name__ == '__main__':
    main()
