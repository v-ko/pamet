from typing import Callable
from browser import window, document, timer

import fusion
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

    fusion.set_main_loop(JSMainLoop())
    print('test')
    pamet.insert(id='test_page')
    pamet.insert(
        page_id='test_page', text='Test that shit out')
    print(pamet.page('test_page').notes()[0].asdict())


if __name__ == '__main__':
    main()
