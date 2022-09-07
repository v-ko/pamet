from dataclasses import dataclass
from typing import List, Tuple

from fusion.libs.entity.change import Change
from fusion.libs.channel import Channel
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


def concat_content_for_note(note: Note) -> str:
    return ' '.join([str(val) for val in note.content.values()])


@dataclass
class SearchResult:
    note_gid: Tuple
    content_string: str
    score: float

    def get_note(self):
        return pamet.find_one(gid=self.note_gid)


class IndexEntry:
    def __init__(self, note: Note):
        self.content_string = content_str_for_note(note)
        self.content_lowered = concat_content_for_note(note).lower()


class BaseSearchService:

    def __init__(self, change_set_channel: Channel):
        self.index = {}  # By note gid
        change_set_channel.subscribe(self.handle_change_set)

    def load_all_content(self):
        for page in pamet.pages():
            for note in pamet.notes(page):
                index_entry = IndexEntry(note)
                self.index[note.gid()] = index_entry

    def handle_change_set(self, change_set: List[Change]):
        """Keeps the cached texts up to date using the received changes."""
        for change in change_set:
            state = change.last_state()
            if not isinstance(state, Note):
                continue

            if change.is_delete():
                if state.gid() in self.index:
                    self.index.pop(state.gid())
            else:  # change is_create or is_update
                index_entry = IndexEntry(state)
                self.index[state.gid()] = index_entry

    def text_search(self, text: str) -> SearchResult:
        """Searches the cached texts and returns search results"""
        raise NotImplementedError
