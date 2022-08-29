from browser import window, document
import fusion


class Logger:
    def critical(self):
        print('testssss')


def get_logger(name: str):
    return Logger()


def test_func(*args):
    for a in args:
        print(a)


def test_func_kwa(**custom_kwargs):
    for a, v in custom_kwargs.items():
        print(v)


def main():
    window.test_func = test_func
    window.test_func_kwa = test_func_kwa
    window.fusion = fusion

    label = document['label']
    label.text = 'LOADED, YO'
    label.style.color = 'red'


if __name__ == '__main__':
    main()
