from copy import copy
from datetime import datetime
import time
from typing import Dict, Generator, List, Tuple
import os
import json
from pathlib import Path

import misli
from misli import entity_library, Entity, Change
from misli.basic_classes.point2d import Point2D
from misli.basic_classes.rectangle import Rectangle
from misli.helpers import current_time, get_new_id
from misli.pubsub import Channel
from misli.storage.in_memory_repository import InMemoryRepository
from misli.storage.repository import Repository
import pamet

from pamet.model import Page, Note
from pamet.model.arrow import Arrow, ArrowAnchorType
from pamet.model.image_note import ImageNote
from pamet.model.script_note import ScriptNote
from pamet.model.text_note import TextNote
from slugify import slugify

from .legacy import EXTERNAL_ANCHOR_PREFIX, IMAGE_NOTE_PREFIX
from .legacy import INTERNAL_ANCHOR_PREFIX, ONE_V3_COORD_UNIT_TO_V4
from .legacy import SYSTEM_CALL_NOTE_PREFIX, TIME_FORMAT

from misli import get_logger

log = get_logger(__name__)

RANDOMIZE_TEXT = False
V4_FILE_EXT = '.pam4.json'


def backup_file(file_path: Path, backup_folder: Path):
    backup_folder.mkdir(parents=True, exist_ok=True)
    backup_path = backup_folder / (file_path.name + '.backup')
    if backup_path.exists():
        backup_path = (backup_path.name + f'.backup-{get_new_id()}')
    file_path.rename(backup_path)
    return backup_path


class FSStorageRepository(Repository):
    """File system storage. This class has all entities cached at all times"""

    def __init__(self, path, queue_save_on_change=False):
        Repository.__init__(self)

        self.path = Path(path)
        self.queue_save_on_change = queue_save_on_change
        self._page_ids = []

        self._save_channel: Channel = None

        self.in_memory_repo = InMemoryRepository()
        self.page_paths_by_id: Dict[str, Path] = {}

        self.upserted_pages = set()
        self.removed_pages = set()
        self.pages_for_write_removal = {}

        legacy_pages = self._process_legacy_pages()

        # Load all pages in the cache
        for page_path in self.page_paths():
            try:
                entities = self.get_entities_from_json(
                    page_path)  #@IgnoreException
                if not entities:
                    continue
                page, notes, arrows = entities
            except Exception as e:
                log.error(
                    f'Exception raised while loading page {page_path}: {e}')
                continue

            # Check if the page is saved under the right name
            inferred_path = self.path_for_page(page)
            if page_path != inferred_path:  # If not - fix it by re-saving
                page_path.unlink()
                self.create_page(page, notes, arrows)
                log.error(f'Bad page name. Deleted {page_path} and saved the '
                          f'page {page.name} anew.')

            # Check for dupicates
            page_duplicates = self.find(gid=page.gid())
            for page_duplicate in page_duplicates:
                dup_path = self.path_for_page(page_duplicate)

                if dup_path.stat().st_mtime <= page_path.stat().st_mtime:
                    # If the page that's older is loaded
                    self.in_memory_repo.remove_one(page_duplicate)
                    backup_path = dup_path.with_suffix('.backup')
                    dup_path.rename(backup_path)
                    log.error(f'Found duplicate page "{page_duplicate.name} '
                              f'in the repo. Backed it up as {backup_path}')
                else:
                    # If the page, currently processed in the upper loop
                    # is older
                    backup_path = page_path.with_suffix('.backup')
                    dup_path.rename(backup_path)
                    log.error(f'Found duplicate page "{page_duplicate.name} '
                              f'in the repo. Backed it up as {backup_path}')
                    break

            # Add the entities to the in-memory cache
            try:
                self.in_memory_repo.insert_one(page)
                for note in notes:
                    try:
                        self.in_memory_repo.insert_one(note)
                    except Exception:
                        log.error(f'Duplicate note. Skipping {note}')
                        continue
                for arrow in arrows:
                    try:
                        self.in_memory_repo.insert_one(arrow)
                    except Exception:
                        log.error(f'Duplicate arrow. Skipping {arrow}')
                        continue
            except Exception:
                log.error(f'Duplicate page. Skipping {page}')
                continue

            # Save the path corresponding to the id in order to handle renames
            self.page_paths_by_id[page.id] = self.path_for_page(page)

        # Fix the internal links of legacy pages
        for page_path in legacy_pages:
            self.fix_legacy_page_internal_links(page_path)

    def path_for_page(self, page) -> Path:
        slug = slugify(page.name, separator='_', max_length=100)
        name = f'{slug}-{page.id}{V4_FILE_EXT}'
        return self.path / name

    def id_from_page_path(self, path: Path) -> str:
        # Remove the file ext .pam4.json and get the file name
        page_id = path.with_suffix('').stem

        slug, page_id = page_id.split('-')
        return page_id

    @classmethod
    def open(cls, path, **kwargs):
        if not os.path.exists(path) or not os.path.isdir(path):
            raise Exception('Bad path. Cannot create repository for', path)

        return cls(path, **kwargs)

    @classmethod
    def new(cls, path, **kwargs):
        if os.path.exists(path):
            if os.listdir(path):
                raise Exception(
                    f'Cannot create repository in non-empty folder {path}')

        os.makedirs(path, exist_ok=True)
        return cls(path, **kwargs)

    def set_save_channel(self, save_channel):
        self._save_channel = save_channel

    def upsert_to_cache(self, entity: Entity):
        return self.in_memory_repo.upsert_to_cache(entity)

    def insert_one(self, entity: Entity):
        self.in_memory_repo.insert_one(entity)
        if isinstance(entity, Page):
            self.upserted_pages.add(entity.gid())
        elif isinstance(entity, (Note, Arrow)):
            self.upserted_pages.add(entity.parent_gid())

        if self.queue_save_on_change:
            misli.call_delayed(self.write_to_disk, 0)

        return Change.CREATE(entity)

    def insert(self, entities: List[Entity]):
        for entity in entities:
            self.insert_one(entity)

        # Async to allow for grouping of all calls within an e.g. action
        misli.call_delayed(self.write_to_disk, 0)

    def remove_one(self, entity):
        self.in_memory_repo.remove_one(entity)
        if isinstance(entity, Page):
            self.removed_pages.add(entity.gid())
            self.pages_for_write_removal[entity.gid()] = entity
        elif isinstance(entity, (Note, Arrow)):
            self.upserted_pages.add(entity.parent_gid())

        if self.queue_save_on_change:
            misli.call_delayed(self.write_to_disk, 0)

        return Change.DELETE(entity)

    def remove(self, entities: List[Entity]):
        for entity in entities:
            self.remove_one(entity)

        # Async to allow for grouping of all calls within an e.g. action
        misli.call_delayed(self.write_to_disk, 0)

    def update_one(self, entity):
        change = self.in_memory_repo.update_one(entity)
        if isinstance(entity, Page):
            self.upserted_pages.add(entity.gid())
        elif isinstance(entity, (Note, Arrow)):
            self.upserted_pages.add(entity.parent_gid())

        if self.queue_save_on_change:
            misli.call_delayed(self.write_to_disk, 0)

        return change

    def update(self, entities: List[Entity]):
        for entity in entities:
            self.update_one(entity)

        # Async to allow for grouping of all calls within an e.g. action
        misli.call_delayed(self.write_to_disk, 0)

    def find(self, **filter):
        yield from self.in_memory_repo.find(**filter)

    def _try_to_save(self, changes: List[Change]):
        try:
            for change in changes:
                if change.is_create():
                    self.insert_one(change.last_state())
                elif change.is_delete():
                    self.remove_one(change.last_state())
                elif change.is_update():
                    self.update_one(change.last_state())

            self.write_to_disk(changes)
        except Exception as e:
            # Here I could handle exceptions silently, retry, show in GUI, etc
            raise e
        # else:
        #     if self._save_channel:
        #         self._save_channel.push(changes)

    def write_to_disk(self):
        if self.upserted_pages.intersection(self.removed_pages):
            raise Exception('A page is both marked for upsert and removal.')

        for page_gid in self.upserted_pages:
            page = pamet.find_one(gid=page_gid)

            if page.id in self.page_paths_by_id:
                self.update_page(page, page.notes(), page.arrows())
            else:
                self.create_page(page, page.notes(), page.arrows())

        for page_gid in self.removed_pages:
            page = self.pages_for_write_removal.pop(page_gid)
            self.delete_page(page)

        self.upserted_pages.clear()
        self.removed_pages.clear()

    def page_paths(self) -> Generator[Path, None, None]:
        for file in os.scandir(self.path):
            if self.is_v4_page(file.path):
                yield Path(file.path)

    def get_entities_from_json(self, json_file_path):
        try:
            with open(json_file_path) as pf:
                page_state = json.load(pf)  #@IgnoreException
        except Exception as e:
            log.error('Exception %s while loading page' % e, json_file_path)
            return None

        # # TODO REMOVE
        # page_state.pop('type_name', None)
        # if 'note_states' in page_state:
        #     page_state['notes'] = page_state.pop('note_states', [])
        # if 'arrow_states' in page_state:
        #     page_state['arrows'] = page_state.pop('arrow_states', [])

        # Detach the children
        note_states = page_state.pop('notes', [])
        arrow_states = page_state.pop('arrows', [])

        # Create the page
        page = entity_library.from_dict(Page.__name__, page_state)

        # Load the notes
        notes = []
        for ns in note_states:
            # Refactoring fixes .. REMOVE LATER
            # if 'x' in ns:
            #     x = ns.pop('x')
            #     y = ns.pop('y')
            #     width = ns.pop('width')
            #     height = ns.pop('height')
            #     ns['geometry'] = [x, y, width, height]

            # if 'time_created' in ns:
            #     ns['created'] = ns.pop('time_created')
            #     ns['modified'] = ns.pop('time_modified')

            # if ns['type_name'] == 'AnchorNote':
            #     ns['type_name'] = 'TextNote'

            if 'script_args_str' in ns:
                command_args = ns.pop('script_args_str')
                if 'content' not in ns:
                    ns['content'] = {}
                ns['content']['command_args'] = command_args

            content = ns.get('content', None)
            if content:

                if 'script' in content:
                    script_path = content.pop('script')
                    content['script_path'] = script_path

            # /ad-hoc fixes

            try:
                note_type = entity_library.get_entity_class_by_name(
                    ns['type_name'])
            except Exception:
                log.error(f'Could not get note type (in {json_file_path}) '
                          f'for the following note: {ns}')
                continue

            notes.append(entity_library.from_dict(note_type.__name__, ns))

        # Load the arrows
        arrows = []
        for arrow_state in arrow_states:
            # REMOVE vvv
            # arrow_state.pop('background_color', None)
            # if 'mid_point_coords' not in arrow_state:
            #     arrow_state['mid_point_coords'] = arrow_state.pop('mid_points')
            # if 'head_coords' not in arrow_state:
            #     arrow_state['head_coords'] = arrow_state.pop('head_point')
            # if 'tail_coords' not in arrow_state:
            #     arrow_state['tail_coords'] = arrow_state.pop('tail_point')

            if 'page_id' not in arrow_state or not arrow_state['page_id']:
                raise Exception

            try:
                arrow: Arrow = entity_library.from_dict(
                    Arrow.__name__, arrow_state)
            except Exception as e:
                log.error(f'Exception {e} raised while parsing arrow '
                          f'{arrow_state} from file {json_file_path}')
                continue

            arrows.append(arrow)

        return page, notes, arrows

    @staticmethod
    def serialize_page(page: Page, notes: List[Note], arrows: List[Arrow]):
        page_state = page.asdict()
        page_state['notes'] = [n.asdict() for n in notes]
        page_state['arrows'] = [a.asdict() for a in arrows]

        try:
            json_str = json.dumps(page_state, ensure_ascii=False, indent=4)
        except Exception as e:
            raise e  # Or log error
            return None

        return json_str

    def create_page(self, page: Page, notes: List[Note], arrows: List[Arrow]):
        path = self.path_for_page(page)
        try:
            if path.exists():
                log.error('Cannot create page. File already exists %s' % path)
                return

            page_json_str = self.serialize_page(page, notes, arrows)
            if not page_json_str:
                return

            with open(path, 'w') as pf:
                pf.write(page_json_str)

            self.page_paths_by_id[page.id] = path
        except Exception as e:
            log.error('Exception while writing page at %s: %s' % (path, e))

        return path

    def update_page(self, page: Page, notes: List[Note], arrows: List[Arrow]):
        saved_path = self.page_paths_by_id[page.id]
        path = self.path_for_page(page)

        # If the paths differ - the page has been renamed and the file should
        # be moved
        if saved_path != path and saved_path.exists():
            log.debug(f'Page renamed, moving file {saved_path} to {path}.')
            if path.exists():
                raise Exception('This should have been handlet at init time')
            saved_path.rename(path)
            self.page_paths_by_id[page.id] = path

        page_json_str = self.serialize_page(page, notes, arrows)
        if not page_json_str:
            return

        with open(path, 'w') as pf:
            pf.write(page_json_str)

    def delete_page(self, page):
        path = self.page_paths_by_id.pop(page.id)

        if os.path.exists(path):
            os.remove(path)

        else:
            log.error('Cannot delete missing page: %s' % path)

    def is_v4_page(self, file_path: str | Path):
        file_path = Path(file_path)
        if file_path.name.endswith(V4_FILE_EXT):
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
        backup_path = self.path / '__legacy_pages_backup__'

        # Process the legacy pages
        for page_path in v2_pages:
            try:
                new_path = self.convert_v2_to_v3(
                    page_path,
                    backup_folder=backup_path,
                    page_id_to_name_mapping_info=page_id_to_name_mapping_info)
                v3_pages.append(new_path)
            except Exception as e:
                log.error(f'Exception raised when processing legacy page '
                          f'{file.path}: {e}')
                continue

        for page_path in v3_pages:
            try:
                new_path = self.convert_v3_to_v4(
                    page_path,
                    backup_folder=backup_path,
                    page_id_to_name_mapping_info=page_id_to_name_mapping_info)
                legacy_pages.append(new_path)
            except Exception as e:
                log.error(f'Exception raised when processing legacy page '
                          f'{file.path}: {e}')
                continue
        return legacy_pages

    def save_changes(self, changes: List[Change]):
        t0 = time.time()
        self._try_to_save(changes)

        # If there's a big save lag log a warining
        if time.time() - t0 > 0.03:
            log.warning('The save time was above 30ms. Maybe it\'s time to '
                        'implement the async IO')

    def convert_v3_to_v4(self, json_path: str | Path, backup_folder: Path,
                         page_id_to_name_mapping_info: dict):
        # V3 example: {"notes": [
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
        # timezone = datetime.now().astimezone().tzinfo
        # created = datetime.fromtimestamp(json_path.stat().st_ctime, timezone)
        # modified = datetime.fromtimestamp(json_path.stat().st_mtime, timezone)
        page = Page(name=json_path.stem)

        # Load the notes and arrows
        earliest_creation_time = current_time()
        notes = []
        arrows = []
        notes_by_id = {}
        ids_with_duplicates = []
        for nt in notes_data:
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
                control_point = legacy_arrow['cp']
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
                print(
                    f'Updating the id of {note}. '
                    f'Url: {note.url}, text: {note.text}. |'
                    f'Duplicate {note}'
                    f'Url: {notes_by_id[note.id].url}, '
                    f'text: {notes_by_id[note.id].text}.'
                )
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

        backup_path = backup_file(json_path, backup_folder)
        log.info(f'Converted V3 page {json_path} to V4 at {new_path} '
                 f'and backed it up as {backup_path}')

        return new_path

    def convert_v2_to_v3(self, file_path):
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
            nt['time_created'] = datetime.strptime(nt.pop('t_made'),
                                                   '%m.%d.%Y %H:%M:%S')
            nt['time_modified'] = datetime.strptime(nt.pop('t_mod'),
                                                    '%m.%d.%Y %H:%M:%S')
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

    def fix_legacy_page_internal_links(self, page_path: Path):
        page_id = self.id_from_page_path(page_path)
        page = self.find_one(id=page_id)

        entities = self.find(parent_gid=page_id)
        notes = [entity for entity in entities if isinstance(entity, Note)]
        arrows = [entity for entity in entities if isinstance(entity, Arrow)]

        notes_updated = 0
        for note in notes:
            if note.url.is_empty():
                continue
            linked_page = self.find_one(type_name=Page.__name__,
                                        name=str(note.url))
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
