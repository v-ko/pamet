import os
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

from misli import entity_library
from misli.basic_classes import Point2D

from pamet.note_components.text.entity import TextNote
from pamet.services.hacky_backups import backup_page_hackily
from .repository import Repository

from misli import get_logger
log = get_logger(__name__)

RANDOMIZE_TEXT = False
V4_FILE_EXT = '.misl.json'


class FSStorageRepository(Repository):
    def __init__(self, path):
        Repository.__init__(self)

        self.path = Path(path)
        self._page_ids = []

        self._process_legacy_pages()

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

    def create_page(self, page, notes):
        page_state = page.asdict()
        page_state['note_states'] = [n.asdict() for n in notes]

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

    def get_page_and_notes(self, page_id):
        path = self._path_for_page(page_id)

        try:
            with open(path) as pf:
                page_state = json.load(pf)

        except Exception as e:
            log.error('Exception %s while loading page' % e, path)
            return None

        note_states = page_state.pop('note_states', [])

        notes = []

        for ns in note_states:
            notes.append(entity_library.from_dict(ns))

        return entity_library.from_dict(page_state), notes

    def update_page(self, page, notes):
        page_state = page.asdict()
        page_state['note_states'] = [n.asdict() for n in notes]

        path = self._path_for_page(page.id)
        if os.path.exists(path):
            backup_page_hackily(path)
        else:
            log.warning('[update_page] Page at %s was missing. Will create'
                        ' it.' % path)

        with open(path, 'w') as pf:
            json.dump(page_state, pf)

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

    def _convert_v3_to_v4(self, json_path):
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

            nt['page_id'] = name

        for i, nt in enumerate(notes):
            nt['id'] = str(nt['id'])
            nt['color'] = nt.pop('txt_col')
            nt['background_color'] = nt.pop('bg_col')
            nt['x'] = nt.pop('x')
            nt['y'] = nt.pop('y')
            nt['width'] = nt.pop('width')
            nt['height'] = nt.pop('height')
            nt['time_created'] = datetime.strptime(
                nt.pop('t_made'), '%m.%d.%Y %H:%M:%S')
            nt['time_modified'] = datetime.strptime(
                nt.pop('t_mod'), '%m.%d.%Y %H:%M:%S')

            # Redirect notes
            if nt['text'].startswith('this_note_points_to:'):
                nt['href'] = nt['text'].split(':', 1)[1]
                nt['text'] = nt['href']
                nt['obj_type'] = 'Text'
                # nt['obj_type'] = 'Redirect'

            else:
                nt['obj_type'] = 'Text'

            # Remove unimplemented attributes to avoid errors
            note = TextNote(*nt)
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

        json_object['obj_type'] = 'MapPage'
        json_object['note_states'] = note_states

        return json_object

    def _convert_v2_to_v4(self, file_path):
        # Example:
        # [79367]
        # txt=this_note_points_to:Програмиране
        # x=-7
        # y=-4.5
        # z=0
        # a=9
        # b=2.5
        # font_size=1
        # t_made=6.10.2019 14:1:12
        # t_mod=6.10.2019 14:1:12
        # txt_col=0;0;1;1
        # bg_col=0;0;1;0.100008
        # l_id=
        # l_txt=
        # l_CP_x=
        # l_CP_y=
        # tags=

        # Ignored fields: font_size, z (unused)

        with open(file_path) as misl_file:
            misl_file_string = misl_file.read()

        is_displayed_first_on_startup = False
        is_a_timeline_notefile = False

        # Clear the windows standart junk
        misl_file_string = misl_file_string.replace('\r', '')
        lines = [ln for ln in misl_file_string.split('\n') if ln]  # Skip empty

        lines_left = []
        for line in lines:
            if line.startswith('#'):  # Skip comments
                continue

            if line.startswith('is_displayed_first_on_startup'):
                is_displayed_first_on_startup = True
                continue

            elif line.startswith('is_a_timeline_note_file'):
                is_a_timeline_notefile = True

            lines_left.append(line)

        @dataclass
        class Arrow:
            source_id: str
            target_id: str
            control_point: Point2D

        # Extract groups
        notes = {}
        current_note_id = None
        arrows = []  # source, target, control_point

        for line in lines_left:
            if line.startswith('[') and line.endswith(']'):
                current_note_id = line[1:-1]
                continue

            [key, value] = line.split('=', 1)

            if key == 'txt':
                value = value.replace('\\n', '\n')
            elif key in ['txt_col', 'bg_col']:
                value = [float(channel) for channel in value.split(';')]
            elif key in ['l_id', 'l_CP_x', 'l_CP_y']:
                value = value.split(';')

            notes[current_note_id][key] = value

        for note_id, nt in notes.items():
            # Pop unused values
            nt.pop('font_size', '')
            nt.pop('z', '')

            nt['id'] = int(note_id)
            nt['color'] = nt.pop('txt_col')
            nt['background_color'] = nt.pop('bg_col')
            nt['x'] = float(nt.pop('x'))
            nt['y'] = float(nt.pop('y'))
            nt['width'] = float(nt.pop('a'))
            nt['height'] = float(nt.pop('b'))
            nt['text'] = nt.pop('txt')
            nt['time_created'] = datetime.strptime(
                nt.pop('t_made'), '%m.%d.%Y %H:%M:%S')
            nt['time_modified'] = datetime.strptime(
                nt.pop('t_mod'), '%m.%d.%Y %H:%M:%S')
            # nt['tags'] unchanged

            # Process arrows (formerly named links)
            control_points = []
            if 'l_CP_x' in nt and 'l_CP_y' in nt:
                for cp_x, cp_y in zip(nt['l_CP_x'], nt['l_CP_y']):
                    control_points.append(Point2D(cp_x, cp_y))
            else:
                control_points = None

            for arrow_idx, target_id in enumerate(nt['l_id']):
                if control_points:
                    control_point = control_points[arrow_idx]
                else:
                    control_point = None

                arrows.append(Arrow(nt['id'], target_id, control_point))

    def _process_legacy_pages(self):
        legacy_pages = []
        backup_path = self.path / '__legacy_pages_backup__'

        for file in os.scandir(self.path):
            if self.is_v4_page(file.path):
                continue

            try:
                if file.path.endswith('.misl'):
                    page_state = self.convert_v2_to_v4(file.path)

                elif file.path.endswith('.json'):
                    page_state = self._convert_v3_to_v4(file.path)

                else:
                    log.warning('Untracked file in the repo: %s' % file.name)
                    continue
            except Exception as e:
                log.error(f'Exception raised when processing legacy page '
                          f'{file.path}: {e}')
                continue

            if not page_state:
                log.warning('Empty page state for legacy page %s' %
                            file.name)
                continue

            note_states = page_state.pop('note_states', [])
            notes = [entity_library.from_dict(ns)
                     for nid, ns in note_states.items()]

            self.create_page(entity_library.from_dict(page_state), notes)
            legacy_pages.append(Path(file.path))

        if legacy_pages:
            backup_path.mkdir(parents=True, exist_ok=True)

        for page_path in legacy_pages:
            page_backup_path = backup_path / (page_path.name + '.backup')
            page_path.rename(page_backup_path)
            log.info('Loaded legacy page %s and backed it up as %s' %
                     (page_path, page_backup_path))
