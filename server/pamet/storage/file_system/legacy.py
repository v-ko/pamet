from __future__ import annotations

from collections import defaultdict
from copy import copy
# from hashlib import md5
import json

from datetime import datetime, timedelta
from pathlib import Path
import shutil
from typing import TYPE_CHECKING
from fusion.libs.entity import load_from_dict
from slugify import slugify

from fusion.util import Point2D
from fusion.util.rectangle import Rectangle
from fusion.util import current_time, get_new_id, timestamp
from fusion.logging import get_logger
from fusion.storage.in_memory_repository import InMemoryRepository
from pamet.constants import MAX_NOTE_HEIGHT, MAX_NOTE_WIDTH, MIN_NOTE_HEIGHT
from pamet.constants import MIN_NOTE_WIDTH
from pamet.util import snap_to_grid
from pamet.model.page import Page
from pamet.model.arrow import Arrow, ArrowAnchorType
from pamet.model.image_note import ImageNote
from pamet.model.note import Note
from pamet.model.script_note import ScriptNote
from pamet.model.text_note import TextNote

if TYPE_CHECKING:
    pass


log = get_logger(__name__)

V4_FILE_EXT = '.pam4.json'

_cache = {}
_paths_cache = {}
MAX_CACHE = 1000
new_to_old_path = {}
md5_by_old_name = {}

# # Caching - to be removed. it's only for the bin import
# def get_from_cache(page_path: Path):
#     if page_md5 in _cache:
#         return _cache[page_md5]
#     return page_md5

TIME_FORMAT = '%d.%m.%Y %H:%M:%S'
ONE_V3_COORD_UNIT_TO_V4 = 20

INTERNAL_ANCHOR_PREFIX = 'this_note_points_to:'
EXTERNAL_ANCHOR_PREFIX = 'define_web_page_note:'
IMAGE_NOTE_PREFIX = 'define_picture_note:'
SYSTEM_CALL_NOTE_PREFIX = 'define_system_call_note:'


def backup_file(file_path: Path, backup_folder: Path):
    backup_folder.mkdir(parents=True, exist_ok=True)
    backup_path = backup_folder / (file_path.name + '.backup')
    if backup_path.exists():
        backup_name = (backup_path.stem + f'.backup-{get_new_id()}')
        backup_path = backup_folder / backup_name

    shutil.copy(file_path, backup_path)
    log.info(f'Backed up file {file_path} to {backup_path}')

    return backup_path


def new_legacy_id_for_legacy_note(note_id: int, timestamp: str, text: str,
                                  all_ids: list):
    # Make a deterministic new id based on the timestamp and old id
    new_id = hash(timestamp)
    if new_id in all_ids:
        # If that's not enough - add a suffix based on the note text
        new_id = hash(timestamp + text)
        if new_id in all_ids:  # Mostly for timeline notes
            new_id = hash(get_new_id())
            if new_id in all_ids:
                raise Exception('WTF')

    return new_id


def new_id_for_legacy_note(note_id, timestamp, content: str, all_ids: list):
    # Make a deterministic new id based on the timestamp and old id
    note_id = str(note_id)
    timestamp = str(timestamp)
    new_id = get_new_id(note_id + timestamp)
    if new_id in all_ids:
        # If that's not enough - add a suffix based on the note text
        new_id = get_new_id(note_id + timestamp + str(content))
        if new_id in all_ids:  # Mostly for timeline notes
            raise Exception('WTF')

    return new_id


def path_for_page(page, repo_path: Path) -> Path:
    """Standalone function to calculate the file path for a page"""
    slug = slugify(page.name, separator='_', max_length=100)
    filename = f'{slug}-{page.id}{V4_FILE_EXT}'
    return repo_path / filename


class MigrationsManager:

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = Path(repo_path)
        self.v2_note_checksum_by_page_name = {}
        self.v3_note_checksum_by_page_name = {}
        self.v2_notes_by_page_name = defaultdict(set)

    def convert_v3_to_v4(self, json_path: str | Path, backup_folder: Path,
                         previous_v_repo_entities: dict | None):
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

        # Import the FSStorageRepository here to avoid circular imports
        from pamet.storage.file_system.repository import FSStorageRepository

        json_path = Path(json_path)
        page_data = json.loads(json_path.read_text())
        notes_data = page_data.pop('notes')

        # Load the page
        page = Page()
        page.id = get_new_id(json_path.stem)
        page.name = json_path.stem
        self.v3_note_checksum_by_page_name[page.name] = 0

        # Load the notes and arrows
        earliest_creation_time = current_time()
        notes = []
        arrows = []
        notes_by_id = {}
        ids_with_duplicates = []
        new_ids_by_old = {}
        for nt in notes_data:
            self.v3_note_checksum_by_page_name[page.name] += 1
            # Scale old coords so that default widget fonts
            # look adequate without correction
            for coord in ['x', 'y', 'width', 'height']:
                nt[coord] = snap_to_grid(nt[coord] * ONE_V3_COORD_UNIT_TO_V4)

                # There was that very specific case with an overflow, wtf
                if not (-2147483647 < nt[coord] < 2147483647):
                    nt[coord] = 1

            # nt['page_id'] = page.id

            nt['id'] = (page.id, str(nt['id']))
            nt['color'] = nt.pop('txt_col')
            nt['background_color'] = nt.pop('bg_col')
            nt['geometry'] = [
                nt.pop('x'),
                nt.pop('y'),
                nt.pop('width'),
                nt.pop('height')
            ]
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
            # Fuckit, use the local timezone
            created = created.astimezone()
            modified = modified.astimezone()

            nt['created'] = timestamp(created)
            nt['modified'] = timestamp(modified)

            nt.pop('font_size', None)

            if created < earliest_creation_time:
                earliest_creation_time = created

            if not page.id:
                raise Exception

            # Arrows
            legacy_arrows = nt.pop('links')
            for legacy_arrow in legacy_arrows:
                arrow = Arrow.in_page(page)
                arrow.set_tail(anchor_note_id=nt['id'][1])
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
                nt['type_name'] = TextNote.__name__
                note = load_from_dict(nt)
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

                nt['type_name'] = TextNote.__name__
                note = load_from_dict(nt)
                note.url = url
                note.text = text

            # Image notes
            elif note_text.startswith(IMAGE_NOTE_PREFIX):
                image_url = note_text[len(IMAGE_NOTE_PREFIX):]
                nt['type_name'] = ImageNote.__name__
                note = load_from_dict(nt)
                note.image_url = image_url
                note.local_image_url = image_url

            # System call notes
            elif note_text.startswith(SYSTEM_CALL_NOTE_PREFIX):
                script = note_text[len(SYSTEM_CALL_NOTE_PREFIX):]
                script_parts = script.split()
                command_args = ''.join(script_parts[1:])

                nt['type_name'] = ScriptNote.__name__
                note = load_from_dict(nt)
                note.script_path = script_parts[0]
                note.command_args = command_args
                note.text = script

            else:  # It's just a text note
                nt['type_name'] = TextNote.__name__
                note = load_from_dict(nt)
                note.text = note_text

            # Detect duplicate ids
            if note.own_id in notes_by_id:
                ids_with_duplicates.append(note.own_id)
                log.warning(f'Detected duplicate for {note}. '
                            f'Links to/from it will be deleted.')

            old_id = note.own_id
            note = note.with_id(own_id=new_id_for_legacy_note(
                note.own_id,
                note.created,
                note.content,
                list(notes_by_id.keys()),
            ))
            new_ids_by_old[old_id] = note.own_id

            # Check note sizes
            size = note.rect().size()
            size_x = max(min(size.x(), MAX_NOTE_WIDTH), MIN_NOTE_WIDTH)
            size_y = max(min(size.y(), MAX_NOTE_HEIGHT), MIN_NOTE_HEIGHT)
            if size_x != size.x() or size_y != size.y():
                log.info(f'Note with invalid size imported. '
                         f'Old: {size.x(), size.y()}; New: {size_x, size_y}')
                rect = note.rect()
                rect.set_size(Point2D(size_x, size_y))
                note.set_rect(rect)

            notes.append(note)
            notes_by_id[note.own_id] = note

        # Remove arrows which start or end at notes with duplicate ids, because
        # we don't want to deal with that at all
        arrows = [
            a for a in arrows if a.tail_note_id not in ids_with_duplicates
            and a.head_note_id not in ids_with_duplicates
        ]

        for arrow in arrows:
            # Fix arrow ids (since we changed the note ids)
            arrow.tail_note_id = new_ids_by_old[arrow.tail_note_id]
            arrow.head_note_id = new_ids_by_old[arrow.head_note_id]

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

        # Update the arrow ids to be deterministic
        arrows_with_new_ids = []
        arrows_by_id = {}
        for arrow in arrows:
            new_id = get_new_id([arrow.tail_note_id, arrow.head_note_id])
            if new_id in arrows_by_id:
                # This means there's a second arrow with the same start and
                # end. We just remove it.
                continue
            arrows_by_id[new_id] = arrow
            arrows_with_new_ids.append(arrow.with_id(arrow.page_id, new_id))
        arrows = arrows_with_new_ids

        # Assume page created time from the notes. Modified makes sense only
        # for renames as of now and there's no basis to infer it
        page.datetime_created = earliest_creation_time - timedelta(seconds=10)
        page.datetime_modified = earliest_creation_time - timedelta(seconds=10)

        # Create a temporary repo instance to calculate the path and serialize
        new_path = path_for_page(page, self.repo_path)

        page_json_str = FSStorageRepository.serialize_page(page, notes, arrows)

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

        file_path = Path(file_path)
        self.v2_note_checksum_by_page_name[file_path.stem] = 0

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

        # Extract groups
        notes = defaultdict(dict)
        current_note_id = None
        changed_note_ids = []
        meta_for_id_replace = {}  # Gets assigned the target id
        for line in lines_left:

            if line.startswith('[') and line.endswith(']'):
                current_note_id = int(line[1:-1])

                if current_note_id in self.v2_notes_by_page_name[
                        file_path.stem]:
                    changed_note_ids.append(current_note_id)
                    old_id = current_note_id
                    current_note_id = get_new_id()
                    if current_note_id in meta_for_id_replace:
                        Exception('Not enough randomness, wtf')
                    meta_for_id_replace[current_note_id] = old_id

                self.v2_note_checksum_by_page_name[file_path.stem] += 1
                self.v2_notes_by_page_name[file_path.stem].add(current_note_id)
                continue

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

        # Notes with duplicate ids first get a random id and then we
        # replace it with a deterministic id based on
        # id, timestamp, text
        for nt_random_id, old_id in meta_for_id_replace.items():
            nt = notes.pop(nt_random_id)
            note_id = new_legacy_id_for_legacy_note(old_id, nt['t_made'],
                                                    nt['txt'],
                                                    list(notes.keys()))
            notes[note_id] = nt

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

        assert len(notes) == len(self.v2_notes_by_page_name[file_path.stem])
        assert len(notes) == self.v2_note_checksum_by_page_name[file_path.stem]

        page_dict: dict = {'notes': list(notes.values())}
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

    # Methods for post-migration processing (to be called by FSStorageRepository)
    # These methods are kept for backward compatibility but should be migrated
    # to work with a repo instance passed as parameter

    def fix_legacy_page_internal_links(self, fs_repo, page: Page):
        """
        This method should be called by FSStorageRepository after migrations are complete.
        It requires an active repo instance to work.
        """
        if not isinstance(page, Page):
            raise Exception

        notes = set(fs_repo.notes(page))
        arrows = set(fs_repo.arrows(page))

        notes_updated = 0
        for note in notes:
            if note.url.is_empty():
                continue
            linked_page = fs_repo.find_one(type=Page, name=str(note.url))

            if str(note.url) == 'Imagga':
                pass
            if linked_page:
                notes_updated += 1
                note.url = linked_page.url()
                InMemoryRepository.update_one(fs_repo, note)

        if len(set(notes)) != len(notes):
            raise Exception

        if notes_updated:
            fs_repo.update_page_on_disk(page, notes, arrows)
            log.info(f'Updated {notes_updated} internal links for '
                     f'imported legacy page "{page.name}"')


    def process_legacy_pages(self, previous_v_repo_entities: dict | None = None):
        """
        Process legacy pages in stages: v2→v3, then v3→v4.
        This method incorporates the migration logic that was previously in main.py
        and works independently without requiring an fs_repo instance.

        Creates its own repository instance for post-migration processing.

        Returns a list of migrated page paths and their metadata for post-migration processing.
        """
        # Stage 1: Collect the legacy page paths
        v2_pages = []
        v3_pages = []

        v2_backup_folder = self.repo_path / '__v2_legacy_pages_backup__'
        v3_backup_folder = self.repo_path / '__v3_legacy_pages_backup__'

        for file in list(self.repo_path.iterdir()):
            if not file.is_file():
                continue

            # Check if it's a v4 page (skip those)
            if file.suffix == V4_FILE_EXT:
                continue

            if file.name == '.misli_timeline_database.json':
                backup_file(file, v3_backup_folder)
                file.unlink()
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

        legacy_page_info = []  # List of (page_path, page_id) tuples

        # Stage 2: Process v2 → v3 migrations first
        log.info(f'Starting v2→v3 migration for {len(v2_pages)} pages')
        for page_path in v2_pages:
            try:
                new_path = self.convert_v2_to_v3(page_path,
                                                 backup_folder=v2_backup_folder)
                v3_pages.append(new_path)
                log.info(f'Converted v2 page: {page_path} → {new_path}')
            except Exception as e:
                log.error(f'Exception raised when processing legacy page '
                          f'{page_path}: {e}')
                continue

        # Stage 3: Process v3 → v4 migrations
        log.info(f'Starting v3→v4 migration for {len(v3_pages)} pages')
        for page_path in v3_pages:
            try:
                new_path = self.convert_v3_to_v4(
                    page_path,
                    backup_folder=v3_backup_folder,
                    previous_v_repo_entities=previous_v_repo_entities)

                # Extract page ID from the path for post-migration processing
                # Format is: slug-page_id.pam4.json
                filename = new_path.stem  # removes .pam4.json
                parts = filename.rsplit('-', 1)  # Split from right, once
                if len(parts) == 2:
                    page_id = parts[1]
                    legacy_page_info.append((new_path, page_id))
                    log.info(f'Converted v3 page: {page_path} → {new_path}')
                else:
                    log.warning(f'Could not extract page ID from {new_path}')
                    legacy_page_info.append((new_path, None))

            except Exception as e:
                log.error(f'Exception raised when processing legacy page '
                          f'{page_path}: {e}')
                continue

        log.info(f'Migration completed. Processed {len(legacy_page_info)} pages')

        # Perform post-migration processing with a new repository instance
        if legacy_page_info:  # Only if there were migrations to process
            # Import here to avoid circular imports
            from pamet.storage.file_system.repository import FSStorageRepository

            log.info('Performing post-migration checksumming and link fixing')
            fs_repo = FSStorageRepository.open(self.repo_path, queue_save_on_change=False)
            fs_repo.load_all_pages()

            # Checksum legacy pages and fix internal links in them
            for page_path, page_id in legacy_page_info:
                if page_id:
                    pages = list(fs_repo.find(type=Page, id=page_id))
                    if pages:
                        page = pages[0]  # Get the first (and should be only) page
                        self.checksum_imported_page_notes(fs_repo, page)
                        self.fix_legacy_page_internal_links(fs_repo, page)

        return legacy_page_info

    def checksum_imported_page_notes(self, fs_repo, page: Page):
        """
        This method should be called by FSStorageRepository after migrations are complete.
        It requires an active repo instance to work.
        """
        note_count_in_repo = len([
            nt for nt in fs_repo.find(parent_gid=page.gid())
            if isinstance(nt, Note)
        ])

        if page.name in self.v2_note_checksum_by_page_name:
            v2_note_count = self.v2_note_checksum_by_page_name[page.name]
            assert note_count_in_repo == v2_note_count

        if page.name in self.v3_note_checksum_by_page_name:
            v3_note_count = self.v3_note_checksum_by_page_name[page.name]
            assert note_count_in_repo == v3_note_count
