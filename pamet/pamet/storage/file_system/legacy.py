from ast import Tuple
from collections import defaultdict
from copy import copy
import json

from datetime import datetime
from pathlib import Path
from random import randint
import shutil
from typing import List
from misli import entity_library

from misli.basic_classes import Point2D
from misli.basic_classes.rectangle import Rectangle
from misli.entity_library.change import Change
from misli.helpers import current_time, get_new_id
from misli.logging import get_logger
from pamet.model import Page
from pamet.model.arrow import Arrow, ArrowAnchorType
from pamet.model.image_note import ImageNote
from pamet.model.note import Note
from pamet.model.script_note import ScriptNote
from pamet.model.text_note import TextNote

log = get_logger(__name__)

TIME_FORMAT = '%d.%m.%Y %H:%M:%S'
ONE_V3_COORD_UNIT_TO_V4 = 20

INTERNAL_ANCHOR_PREFIX = 'this_note_points_to:'
EXTERNAL_ANCHOR_PREFIX = 'define_web_page_note:'
IMAGE_NOTE_PREFIX = 'define_picture_note:'
SYSTEM_CALL_NOTE_PREFIX = 'define_system_call_note:'

v2_note_checksum_by_page_name = defaultdict(int)
v3_note_checksum_by_page_name = defaultdict(int)
v2_notes_by_page_name = defaultdict(set)


def backup_file(file_path: Path, backup_folder: Path):
    backup_folder.mkdir(parents=True, exist_ok=True)
    backup_path = backup_folder / (file_path.name + '.backup')
    if backup_path.exists():
        backup_name = (backup_path.stem + f'.backup-{get_new_id()}')
        backup_path = backup_folder / backup_name

    shutil.copy(file_path, backup_path)
    log.info(f'Backed up file {file_path} to {backup_path}')

    return backup_path


class LegacyFSRepoReader:

    def convert_v3_to_v4(self, json_path: str | Path, backup_folder: Path,
                         page_id_to_name_mapping_info: dict):
        # V3 example: {
        # "is_displayed_first_on_startup": true
        # "notes": [
        # {"bg_col": [0,0,1,0.1],
        #     "font_size": 1,
        #     "height": 3,
        #     "id": 1,
        #     "links": [
        #         {
        #             "cp": [
        #                 12.25,
        #                 -7.25
        #             ],
        #             "text": "",
        #             "to_id": 1
        #         }
        #     ],
        #     "t_made": "10.4.2019 14:2:2",
        #     "t_mod": "10.4.2019 14:2:2",
        #     "tags": [],
        #     "text": "this_note_points_to:notes",
        #     "txt_col": [0,0,1,1],
        #     "width": 11,
        #     "x": 1,
        #     "y": -2.5}]}

        json_path = Path(json_path)
        page_data = json.loads(json_path.read_text())
        notes_data = page_data.pop('notes')

        # Load the page
        page = Page(name=json_path.stem)

        # Load the notes and arrows
        earliest_creation_time = current_time()
        notes = []
        arrows = []
        notes_by_id = {}
        ids_with_duplicates = []
        for nt in notes_data:
            v3_note_checksum_by_page_name[page.name] += 1
            # Scale old coords so that default widget fonts
            # look adequate without correction
            for coord in ['x', 'y', 'width', 'height']:
                nt[coord] = nt[coord] * ONE_V3_COORD_UNIT_TO_V4

                # There was that very specific case with an overflow, wtf
                if not (-2147483647 < nt[coord] < 2147483647):
                    nt[coord] = 1

            nt['page_id'] = page.id

            nt['id'] = str(nt['id'])
            nt['color'] = nt.pop('txt_col')
            nt['background_color'] = nt.pop('bg_col')
            nt['geometry'] = (nt.pop('x'), nt.pop('y'), nt.pop('width'),
                              nt.pop('height'))
            t_made = nt.pop('t_made')
            t_mod = nt.pop('t_mod')

            if not t_made:
                log.warning('In page {page.name}: Note {nt} is missing t_made')
                t_made = datetime.strftime(current_time(), TIME_FORMAT)
            if not t_mod:
                log.warning('In page {page.name}: Note {nt} is missing t_mod')
                t_mod = datetime.strftime(current_time(), TIME_FORMAT)

            created = datetime.strptime(t_made, TIME_FORMAT)
            modified = datetime.strptime(t_mod, TIME_FORMAT)
            created = created.astimezone()  # Fuckit, use the local timezone
            modified = modified.astimezone()
            nt['created'] = created
            nt['modified'] = modified

            nt.pop('font_size', None)

            if created < earliest_creation_time:
                earliest_creation_time = created

            # Arrows
            legacy_arrows = nt.pop('links')
            for legacy_arrow in legacy_arrows:
                arrow = Arrow()
                if not page.id:
                    raise Exception
                arrow.page_id = page.id
                arrow.set_tail(anchor_note_id=nt['id'])
                arrow.set_head(anchor_note_id=str(legacy_arrow['to_id']))
                control_point = legacy_arrow.pop('cp', None)
                if control_point:
                    midpoint = Point2D(*control_point)
                    midpoint *= ONE_V3_COORD_UNIT_TO_V4
                    arrow.replace_midpoints([midpoint])

                arrows.append(arrow)

            # Import according to the note type
            note_text = nt.pop('text')

            # Internal anchors
            if note_text.startswith(INTERNAL_ANCHOR_PREFIX):
                page_name = note_text[len(INTERNAL_ANCHOR_PREFIX):]
                note = entity_library.from_dict(TextNote.__name__, nt)
                note.url = page_name  # Will be converted to a url afterwards

            # External anchors (web links)
            elif note_text.startswith(EXTERNAL_ANCHOR_PREFIX):
                lines = note_text.split('\n')
                url = ''
                text = ''
                for line in lines:
                    if line.startswith('url='):
                        url = line[4:]
                    elif line.startswith('name='):
                        text = line[5:]

                note = entity_library.from_dict(TextNote.__name__, nt)
                note.url = url
                note.text = text

            # Image notes
            elif note_text.startswith(IMAGE_NOTE_PREFIX):
                image_url = note_text[len(IMAGE_NOTE_PREFIX):]
                note = entity_library.from_dict(ImageNote.__name__, nt)
                note.image_url = image_url
                note.local_image_url = image_url

            # System call notes
            elif note_text.startswith(SYSTEM_CALL_NOTE_PREFIX):
                script = note_text[len(SYSTEM_CALL_NOTE_PREFIX):]
                script_parts = script.split()
                command_args = ''.join(script_parts[1:])

                note = entity_library.from_dict(ScriptNote.__name__, nt)
                note.script_path = script_parts[0]
                note.command_args = command_args
                note.text = script

            else:  # It's just a text note
                note = entity_library.from_dict(TextNote.__name__, nt)
                note.text = note_text

            # Detect duplicate ids
            if note.id in notes_by_id:
                ids_with_duplicates.append(note.id)
                print(f'Updating the id of {note}. '
                      f'Url: {note.url}, text: {note.text}. |'
                      f'Duplicate {note}'
                      f'Url: {notes_by_id[note.id].url}, '
                      f'text: {notes_by_id[note.id].text}.')
                note = note.with_id(get_new_id())
            notes.append(note)
            notes_by_id[note.id] = note

        # Remove arrows which start or end at notes with duplicate ids, because
        # we don't want to deal with that at all
        arrows = [
            a for a in arrows if arrow.tail_note_id not in ids_with_duplicates
            and arrow.head_note_id not in ids_with_duplicates
        ]

        for arrow in arrows:

            tail_note = notes_by_id[arrow.tail_note_id]
            head_note = notes_by_id[arrow.head_note_id]

            tail_rect = tail_note.rect()
            head_rect: Rectangle = head_note.rect()

            # To check if the notes are above one another - move to the same
            # height and check for an intersection
            intersect_check_rect = copy(head_rect)
            intersect_check_rect.set_y(tail_rect.y())

            if tail_rect.intersects(intersect_check_rect):
                if head_rect.center().y() < tail_rect.center().y():
                    arrow.tail_anchor_type = ArrowAnchorType.TOP_MID
                    arrow.head_anchor_type = ArrowAnchorType.BOTTOM_MID
                else:
                    arrow.tail_anchor_type = ArrowAnchorType.BOTTOM_MID
                    arrow.head_anchor_type = ArrowAnchorType.TOP_MID
            elif head_rect.right() <= tail_rect.left():
                arrow.tail_anchor_type = ArrowAnchorType.MID_LEFT
                arrow.head_anchor_type = ArrowAnchorType.MID_RIGHT
            elif head_rect.left() >= tail_rect.right():
                arrow.tail_anchor_type = ArrowAnchorType.MID_RIGHT
                arrow.head_anchor_type = ArrowAnchorType.MID_LEFT
            else:
                raise Exception

        # Assume page created time from the notes. Modified makes sense only
        # for renames as of now and there's no basis to infer it
        page.created = earliest_creation_time
        page.modified = earliest_creation_time

        new_path = self.path_for_page(page)
        page_json_str = self.serialize_page(page, notes, arrows)

        # Disabled on DEBUG for now
        # if new_path.exists():
        #     raise Exception or move or something

        new_path.write_text(page_json_str)

        backup_file(json_path, backup_folder)
        log.info(f'Converted V3 page {json_path} to V4 at {new_path} ')
        json_path.unlink()

        return new_path

    def convert_v2_to_v3(self, file_path: str | Path, backup_folder: Path):
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

        file_path = Path(file_path)
        misl_file_string = file_path.read_text()

        is_displayed_first_on_startup = False
        is_a_timeline_notefile = False

        # Clear the windows standart junk
        # The \r chars should be handled by python
        # misl_file_string = misl_file_string.replace('\r', '')

        lines = [ln for ln in misl_file_string.split('\n') if ln]  # Skip empty

        lines_left = []
        for line in lines:
            if line.startswith('#'):  # Skip comments
                continue

            elif line.startswith('is_displayed_first_on_startup'):
                is_displayed_first_on_startup = True
                continue

            elif line.startswith('is_a_timeline_note_file'):
                is_a_timeline_notefile = True
                continue

            lines_left.append(line)

        if is_a_timeline_notefile:
            return

        def random_id():
            rid = randint(10000, 2000000)
            if rid in v2_notes_by_page_name[file_path.stem]:
                return random_id()
            else:
                return rid

        # Extract groups
        notes = defaultdict(dict)
        current_note_id = None
        changed_note_ids = []
        for line in lines_left:

            if line.startswith('[') and line.endswith(']'):
                current_note_id = int(line[1:-1])
                if current_note_id in v2_notes_by_page_name[file_path.stem]:
                    changed_note_ids.append(current_note_id)
                    current_note_id = random_id()
                v2_note_checksum_by_page_name[file_path.stem] += 1
                v2_notes_by_page_name[file_path.stem].add(current_note_id)
                continue

            # if skip_till_next_note:
            #     continue

            if '=' not in line:
                raise Exception

            [key, value] = line.split('=', 1)

            # Drop some unused fields
            if key in ['z', 'l_txt']:
                continue

            # Convert values where needed
            elif key == 'txt':
                value = value.replace('\\n', '\n')
            elif key in ['txt_col', 'bg_col']:
                value = [float(channel) for channel in value.split(';')]
            elif key in ['l_id', 'l_CP_x', 'l_CP_y']:
                value = value.split(';')
                value = [v for v in value if v]
                if key == 'l_id':
                    value = [int(v) for v in value]
                else:
                    value = [float(v) for v in value]
            elif key == 'id':
                value = int(value)
            elif key in ['x', 'y', 'a', 'b']:
                value = float(value)
            elif key in ['tags', 'font_size', 't_mod', 't_made']:
                pass
            else:
                raise Exception

            notes[current_note_id][key] = value

        for note_id, nt in notes.items():
            # Rename fields to the V3 schema
            nt['id'] = note_id
            nt['width'] = nt.pop('a')
            nt['height'] = nt.pop('b')
            nt['text'] = nt.pop('txt')

            # Process arrows (formerly named links)
            control_points = []
            if 'l_CP_x' in nt and 'l_CP_y' in nt:
                for cp_x, cp_y in zip(nt['l_CP_x'], nt['l_CP_y']):
                    control_points.append(Point2D(cp_x, cp_y))
            else:
                control_points = None

            to_ids = nt.pop('l_id')
            cp_xs = nt.pop('l_CP_x', None)
            cp_ys = nt.pop('l_CP_y', None)

            if cp_xs and cp_ys:
                CPs = list(zip(cp_xs, cp_ys))
                # # Clear empty ones
                # CPs = [cp for cp in CPs if cp[0] and cp[1]]
                if len(to_ids) != len(CPs):
                    raise Exception
            else:
                CPs = None

            nt['links'] = []
            for i, to_id in enumerate(to_ids):
                if to_id in changed_note_ids:  # Skip links of buggy notes
                    continue
                link_dict = {'text': '', 'to_id': to_id}
                if CPs:
                    link_dict['cp'] = CPs[i]

                nt['links'].append(link_dict)

        assert len(notes) == len(v2_notes_by_page_name[file_path.stem])
        assert len(notes) == v2_note_checksum_by_page_name[file_path.stem]

        page_dict = {'notes': list(notes.values())}
        if is_displayed_first_on_startup:
            page_dict['is_displayed_first_on_startup'] = True

        new_path = file_path.with_suffix('.json')
        json_str = json.dumps(page_dict, indent=4, ensure_ascii=False)
        new_path.write_text(json_str)
        log.info(f'Converted v2 file at {file_path} to v3 file at {new_path}')

        backup_folder.mkdir(parents=True, exist_ok=True)
        backup_file(file_path, backup_folder)
        file_path.unlink()

        return new_path

    def fix_legacy_page_internal_links(self, page: Page):

        if not isinstance(page, Page):
            raise Exception

        entities = self.find(parent_gid=page.gid())
        notes = [entity for entity in entities if isinstance(entity, Note)]
        arrows = [entity for entity in entities if isinstance(entity, Arrow)]

        notes_updated = 0
        for note in notes:
            if note.url.is_empty():
                continue
            linked_page = self.find_one(type_name=Page.__name__,
                                        name=str(note.url))

            if str(note.url) == 'Imagga':
                pass
            if linked_page:
                notes_updated += 1
                note.url = linked_page.url()
                self.in_memory_repo.update_one(note)

        if len(set(notes)) != len(notes):
            raise Exception

        if notes_updated:
            self.update_page(page, notes, arrows)
            log.info(f'Updated {notes_updated} internal links for '
                     f'imported legacy page "{page.name}"')

    def _process_legacy_pages(self, page_id_to_name_mapping_info: dict = None):
        # Collect the legacy page paths
        v2_pages = []
        v3_pages = []
        for file in list(self.path.iterdir()):
            if self.is_v4_page(file) or not file.is_file():
                continue
            if file.suffix == '.misl':
                v2_pages.append(file)
            elif file.suffix == '.json':
                v3_pages.append(file)
            else:
                log.warning('Untracked file in the repo: %s' % file.name)
                continue

        # If there's none - return
        if not v2_pages and not v3_pages:
            return []

        legacy_pages: List[Tuple] = []  # Tuples (page, notes, arrows)

        # Process the legacy pages
        for page_path in v2_pages:
            try:
                new_path = self.convert_v2_to_v3(page_path,
                                                 backup_folder=self.path /
                                                 '__v2_legacy_pages_backup__')
                v3_pages.append(new_path)
            except Exception as e:
                log.error(f'Exception raised when processing legacy page '
                          f'{file.path}: {e}')
                continue

        for page_path in v3_pages:
            try:
                new_path = self.convert_v3_to_v4(
                    page_path,
                    backup_folder=self.path / '__v3_legacy_pages_backup__',
                    page_id_to_name_mapping_info=page_id_to_name_mapping_info)
                legacy_pages.append(new_path)
            except Exception as e:
                log.error(f'Exception raised when processing legacy page '
                          f'{file.path}: {e}')
                continue
        return legacy_pages

    def checksum_imported_page_notes(self, page: Page):
        note_count_in_repo = len([
            nt for nt in self.find(parent_gid=page.gid())
            if isinstance(nt, Note)
        ])

        v2_note_count = v2_note_checksum_by_page_name[page.name]
        v3_note_count = v3_note_checksum_by_page_name[page.name]

        assert note_count_in_repo == v2_note_count == v3_note_count
