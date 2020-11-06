import time

from org.transcrypt.stubs.browser import __pragma__

__pragma__('skip')
S = console = window = Math = 0
__pragma__('noskip')

__pragma__('alias', 'S', '$')


class TestCase(object):
    def __init__(self, prop):
        self.stuff = 'much_stuff'
        self.prop = prop

    def tryy(self):
        console.log(self.stuff)


def test():
    start = time.time()
    console.log(start)
    d = {}
    for i in range(1000000):
        d[i] = TestCase(i)

    console.log(time.time() - start)
    return len(d)


def changeColors():
    S__divs = S('div')

    for div in S__divs:
        rgb = [int(256 * Math.random()) for i in range(3)]
        S(div).css({
            'color': 'rgb({},{},{})'.format(*rgb),
        })


def start():
    window.setInterval(changeColors, 500)
