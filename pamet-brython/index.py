from typing import Callable
from browser import window, document, timer

import misli
import pamet


class JSMainLoop:
    def call_delayed(
            self, callback: Callable, delay: float, args: list, kwargs: dict):
        timer.set_timeout(lambda: callback(*args, **kwargs), delay * 1000)


def main():
    label = document['label']
    label.text = 'LOADED, YO'
    label.style.color = 'red'

    window.pamet = pamet

    misli.set_main_loop(JSMainLoop())
    print('test')
    misli.insert(id='test_page')
    misli.insert(
        page_id='test_page', text='Test that shit out')
    print(pamet.page(gid='test_page').notes()[0].asdict())


if __name__ == '__main__':
    main()
