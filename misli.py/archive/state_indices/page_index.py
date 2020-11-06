from collections import defaultdict
from .state_index import StateIndex


class PageIndex(StateIndex):
    def __init__(self):
        super(PageIndex, self).__init__('name')
