import os
import json
import random
import string

from misli.entities import Page, Note
from .repository import Repository

from misli import get_logger
log = get_logger(__name__)

RANDOMIZE_TEXT = False
V4_FILE_EXT = '.misl.json'


class FSStorageRepository(Repository):
    def __init__(self, path):
        Repository.__init__(self)

        self.path = path
        self._page_ids = []

        self._process_legacy_pages()

    def _process_legacy_pages(self):
        for file in os.scandir(self.path):

            if self.is_v4_page(file.path):
                pass

            elif file.path.endswith('.json'):
                page_state = self.convert_v3_to_v4(file.path)

                if not page_state:
                    log.warning('Empty page state for legacy page %s' %
                                file.name)
                    continue

                self.create_page(**page_state)

                backup_path = file.path + '.backup'
                os.rename(file.path, backup_path)
                log.info('Loaded v3 page %s and backed it up as %s' %
                         (file.name, backup_path))

            else:
                log.warning('Untracked file in the repo: %s' % file.name)

    def _path_for_page(self, page_id):
        name = page_id + V4_FILE_EXT
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
                log.error('Cannot create repository in non-empty folder %s' %
                          path)
                return None

        os.makedirs(path, exist_ok=True)
        return cls(path)

    def create_page(self, **page_state):
        page = Page(**page_state)

        path = self._path_for_page(page.id)
        try:
            if os.path.exists(path):
                log.error('Cannot create page. File already exists %s' % path)
                return

            with open(path, 'w') as pf:
                json.dump(page_state, pf)

        except Exception as e:
            log.error('Exception while creating page at %s: %s' % (path, e))

    def page_ids(self):
        page_ids = []

        for file in os.scandir(self.path):
            if self.is_v4_page(file.path):
                page_id = file.name[:-len(V4_FILE_EXT)]  # Strip extension

                if not page_id:
                    log.warning('Page with no id at %s' % file.path)
                    continue

                page_ids.append(page_id)

        return page_ids

    def page_state(self, page_id):
        path = self._path_for_page(page_id)

        try:
            with open(path) as pf:
                page_state = json.load(pf)

        except Exception as e:
            log.error('Exception %s while loading page' % e, path)
            return None

        return page_state

    def update_page(self, **page_state):
        page = Page(**page_state)

        path = self._path_for_page(page.id)
        try:
            if not os.path.exists(path):
                log.warning('Page at %s was missing. Will create it.' % path)

            with open(path, 'w') as pf:
                page_state = page.state()
                json.dump(page_state, pf)

        except Exception as e:
            log.error('Exception while updating page at %s: %s' % (path, e))

    def delete_page(self, page_id):
        path = self._path_for_page(page_id)

        if os.path.exists(path):
            os.remove(path)

        else:
            log.error('Cannot delete missing page: %s' % path)

    def is_v4_page(self, file_path):
        if file_path.endswith(V4_FILE_EXT):
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
                    for ch in word:
                        new_word.append(random.choice(string.ascii_letters))

                    words[i] = ''.join(new_word)
                text = ' '.join(words)
                # print(text)
                nt['text'] = text

        for i, nt in enumerate(notes):
            nt['color'] = nt.pop('txt_col')
            nt['background_color'] = nt.pop('bg_col')
            nt['id'] = str(nt['id'])

            # Redirect notes
            if nt['text'].startswith('this_note_points_to:'):
                nt['href'] = nt['text'].split(':', 1)[1]
                nt['text'] = nt['href']
                nt['obj_class'] = 'Redirect'

            else:
                nt['obj_class'] = 'Text'

            # Remove unimplemented attributes to avoid errors
            note = Note()
            new_state = {}
            for key in nt:
                if hasattr(note, key):
                    new_state[key] = nt[key]

            notes[i] = new_state

            # Testing
            # nt['class'] = 'Test'
            # if nt['id'] % 2 == 0:
            #     nt['font_size'] = 2

        note_states = {n['id']: n for n in json_object.pop('notes')}
        json_object['note_states'] = note_states
        json_object['obj_class'] = 'MapPage'

        return json_object
