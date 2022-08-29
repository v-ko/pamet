from dataclasses import dataclass
from typing import List, Tuple

from fusion.entity_library.change import Change
from fusion.pubsub import Channel
import pamet
from pamet.model.note import Note


def content_str_for_note(note):
    content = note.content
    # Disregard empty keys
    content = {key: value for key, value in content.items() if value}
    if len(content) == 1 and 'text' in content:
        # If there's only text: add just the text
        content_str = content['text']
    else:
        # If there's other keys (e.g. 'url', etc) - format them
        content_rows = []
        for key, item in content.items():
            content_rows.append(f'{key}: {item}')
        content_str = '\n'.join(content_rows)
    return content_str


@dataclass
class SearchResult:
    note_gid: Tuple
    content_string: str
    score: float

    def get_note(self):
        return pamet.find_one(gid=self.note_gid)


class BaseSearchService:

    def __init__(self, change_set_channel: Channel):
        self.content_strings = {}  # By note gid
        change_set_channel.subscribe(self.handle_change_set)

    def load_all_content(self):
        for page in pamet.pages():
            for note in pamet.notes(page):
                self.content_strings[note.gid()] = content_str_for_note(note)

    def handle_change_set(self, change_set: List[Change]):
        """Keeps the cached texts up to date using the received changes."""
        for change in change_set:
            state = change.last_state()
            if not isinstance(state, Note):
                continue

            if change.is_delete():
                if state.gid() in self.content_strings:
                    self.content_strings.pop(state.gid())
            else:  # change is_create or is_update
                self.content_strings[state.gid()] = content_str_for_note(state)


    def text_search(self, text: str) -> SearchResult:
        """Searches the cached texts and returns search results"""
        raise NotImplementedError
