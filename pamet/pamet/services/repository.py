from typing import List

from misli import Entity
from misli.entity_library.change import Change
from misli import get_logger

import pamet

log = get_logger(__name__)


class Repository:
    def __init__(self):
        self.path = ''

    def page_names(self):
        raise NotImplementedError

    def create_page(self, page, notes):
        raise NotImplementedError

    def get_page_and_notes(self, page_id):
        raise NotImplementedError

    def update_page(self, page, notes):
        raise NotImplementedError

    def delete_page(self, page_id):
        raise NotImplementedError
