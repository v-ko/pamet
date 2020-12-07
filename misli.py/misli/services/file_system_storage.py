import os
import json
import random
import string

import misli
from misli.objects import Repository, Page
from misli.objects.change import ChangeTypes

from misli import logging
log = logging.getLogger(__name__)

RANDOMIZE_TEXT = False


class FSStorageRepository(Repository):
    def __init__(self, path):
        Repository.__init__(self)

        self.path = path
        self._pages = {}

        # Parse repo folder
        for file in os.scandir(path):
            if self.is_misli_page(file.path):
                try:
                    with open(file.path) as pf:
                        page_state = json.load(pf)

                except Exception as e:
                    log.error('Exception %s while loading page' % e, file.path)
                    continue

                page = Page(**page_state)
                self.load_page(page)

            elif file.path.endswith('.json'):
                page_state = self.convert_v3_to_v4(file.path)

                if page_state:
                    page = Page(**page_state)
                    self.load_page(page)
                    self.save_page(page)
                    os.rename(file.path, file.path + '.backup')
                    log.info('Loaded and backed up v3 page %s' % file.name)

            else:
                log.warning('Untracked file in the repo: %s' % file.name)

    def path_for_page(self, page):
        name = page.id + '.misl.json'
        return os.path.join(self.path, name)

    @classmethod
    def open(cls, path):
        if not os.path.exists(path) or not os.path.isdir(path):
            log.error('Bad path. Cannot create repository for', path)
            return None

        return cls(path)

    @classmethod
    def create(cls, path):
        if os.path.exists(path):
            if os.listdir(path):
                log.error('Cannot create repository in non-empty folder', path)
                return None

        os.makedirs(path, exist_ok=True)
        return cls(path)

    def load_page(self, page):
        self._pages[page.id] = page

    def save_page(self, page):
        try:
            path = self.path_for_page(page)
            with open(path, 'w') as pf:
                page_state = page.state(include_notes=True)
                json.dump(page_state, pf)
        except Exception as e:
            log.error('Exception while saving page at', path, e)

    def pages(self):
        return [page for pid, page in self._pages.items()]

    def page(self, page_id):
        if page_id not in self._pages:
            return None

        return self._pages[page_id]

    def is_misli_page(self, file_path):
        if file_path.endswith('.misl.json') and os.path.exists(file_path):
            return True

        return False

    def catch_legacy_version(self, file_path):
        fname = os.path.basename(file_path)
        name, ext = os.path.splitext(fname)
        version = 0

        if ext == 'json':
            version = 3
        elif ext == 'misl':
            version = 1

        return version

    def convert_v3_to_v4(self, json_path):
        # V3 example: {"notes": [
        # {"bg_col": [0,0,1,0.1],
        #     "font_size": 1,
        #     "height": 3,
        #     "id": 1,
        #     "links": [],
        #     "t_made": "10.4.2019 14:2:2",
        #     "t_mod": "10.4.2019 14:2:2",
        #     "tags": [],
        #     "text": "this_note_points_to:notes",
        #     "txt_col": [0,0,1,1],
        #     "width": 11,
        #     "x": 1,
        #     "y": -2.5}]}

        json_object = json.load(open(json_path))

        fname = os.path.basename(json_path)
        name, ext = os.path.splitext(fname)
        json_object['id'] = name

        ONE_V3_COORD_UNIT_TO_V4 = 20

        notes = json_object['notes']

        # Scale old coords by 10 so that default widget fonts
        # look adequate without correction
        for nt in notes:
            for coord in ['x', 'y', 'width', 'height']:
                nt[coord] = nt[coord] * ONE_V3_COORD_UNIT_TO_V4

            nt['obj_type'] = 'Note'
            nt['page_id'] = name

        for nt in notes:
            if RANDOMIZE_TEXT:
                text = nt['text']
                words = text.split()

                for i, word in enumerate(words):
                    new_word = []
                    for c in word:
                        new_word.append(random.choice(string.ascii_letters))

                    words[i] = ''.join(new_word)
                text = ' '.join(words)
                # print(text)
                nt['text'] = text

        for nt in notes:
            nt['color'] = nt.pop('txt_col')
            nt['background_color'] = nt.pop('bg_col')

            # Redirect notes
            if nt['text'].startswith('this_note_points_to:'):
                nt['href'] = nt['text'].split(':', 1)[1]
                nt['text'] = nt['href']
                nt['obj_class'] = 'Redirect'

            else:
                nt['obj_class'] = 'Text'

            # Testing
            # nt['class'] = 'Test'
            # if nt['id'] % 2 == 0:
            #     nt['font_size'] = 2

        json_object['note_states'] = json_object.pop('notes')
        json_object['obj_class'] = 'MapPage'

        return json_object


def save_changes(changes):
    pages_to_save = set()

    savable_changes = [ChangeTypes.CREATE,
                       ChangeTypes.DELETE,
                       ChangeTypes.UPDATE]

    for change in changes:
        if change.type in savable_changes:
            last_state = change.last_state()
            if last_state['obj_type'] == 'Note':
                pages_to_save.add(last_state['page_id'])

            elif last_state['obj_type'] == 'Page':
                pages_to_save.add(last_state['id'])

    for page_id in pages_to_save:
        page = misli.page(page_id)
        misli.repo().save_page(page)
