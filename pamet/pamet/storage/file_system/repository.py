import time
from typing import Dict, Generator, List
import os
import json
from pathlib import Path

import misli
from misli import entity_library, Entity, Change
from misli.pubsub import Channel
from misli.storage.in_memory_repository import InMemoryRepository
from misli.storage.repository import Repository
import pamet

from pamet.model import Page, Note
from pamet.model.arrow import BEZIER_CUBIC, DEFAULT_ARROW_THICKNESS, Arrow
from slugify import slugify

from .hacky_backups import backup_page_hackily
from .legacy import _convert_v2_to_v4, _convert_v3_to_v4

from misli import get_logger

log = get_logger(__name__)

RANDOMIZE_TEXT = False
V4_FILE_EXT = '.misl.json'


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

        self._process_legacy_pages()

        # Load all pages in cache
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
            self.upsert_to_cache(page)
            for note in notes:
                self.upsert_to_cache(note)
            for arrow in arrows:
                self.upsert_to_cache(arrow)

            # Save the path corresponding to the id in order to handle renames
            self.page_paths_by_id[page.id] = self.path_for_page(page)

    def path_for_page(self, page) -> Path:
        slug = slugify(page.name, separator='_', max_length=100)
        name = f'{slug}-{page.id}{V4_FILE_EXT}'
        return self.path / name

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
        self.in_memory_repo.upsert_to_cache(entity)

    def insert_one(self, entity: Entity):
        self.upsert_to_cache(entity)
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
        self.upsert_to_cache(entity)
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
        page_state.pop('type_name', None)
        note_states = page_state.pop('note_states', [])
        arrow_states = page_state.pop('arrow_states', [])

        notes = []
        for ns in note_states:
            # Refactoring fixes .. REMOVE LATER
            if 'x' in ns:
                x = ns.pop('x')
                y = ns.pop('y')
                width = ns.pop('width')
                height = ns.pop('height')
                ns['geometry'] = [x, y, width, height]

            if 'time_created' in ns:
                ns['created'] = ns.pop('time_created')
                ns['modified'] = ns.pop('time_modified')

            if ns['type_name'] == 'AnchorNote':
                ns['type_name'] = 'TextNote'
            # /ad-hoc fixes

            note_type = pamet.note_type_from_props(ns)
            if not note_type:
                log.error(f'Could not get note type (in {json_file_path}) '
                          f'for the following note: {ns}')
                continue
            notes.append(entity_library.from_dict(note_type.__name__, ns))

        arrows = []
        for arrow_state in arrow_states:
            # REMOVE vvv
            arrow_state.pop('background_color', None)
            if 'mid_point_coords' not in arrow_state:
                arrow_state['mid_point_coords'] = arrow_state.pop('mid_points')
            if 'head_coords' not in arrow_state:
                arrow_state['head_coords'] = arrow_state.pop('head_point')
            if 'tail_coords' not in arrow_state:
                arrow_state['tail_coords'] = arrow_state.pop('tail_point')

            try:
                arrow: Arrow = entity_library.from_dict(
                    Arrow.__name__, arrow_state)
            except Exception as e:
                log.error(f'Exception {e} raised while parsing arrow '
                          f'{arrow_state} from file {json_file_path}')
                continue

            arrows.append(arrow)

        page = entity_library.from_dict(Page.__name__, page_state)
        return page, notes, arrows

    def entities_to_json_str(self, page, notes, arrows):
        page_state = page.asdict()
        page_state['note_states'] = [n.asdict() for n in notes]
        page_state['arrow_states'] = [a.asdict() for a in arrows]

        try:
            json_str = json.dumps(page_state, ensure_ascii=False)
        except Exception as e:
            raise e  # Or log error
            return None

        return json_str

    def create_page(self, page: Page, notes: List[Note], arrows: List[Arrow]):
        path = self.path_for_page(page)
        try:
            if os.path.exists(path):
                log.error('Cannot create page. File already exists %s' % path)
                return

            page_json_str = self.entities_to_json_str(page, notes, arrows)
            if not page_json_str:
                return

            with open(path, 'w') as pf:
                pf.write(page_json_str)

            self.page_paths_by_id[page.id] = path

        except Exception as e:
            log.error('Exception while writing page at %s: %s' % (path, e))

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

        if path.exists():
            backup_page_hackily(path)
        else:
            log.error(f'[update_page] Page at {path} was missing.')

        page_json_str = self.entities_to_json_str(page, notes, arrows)
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

    def _process_legacy_pages(self):
        legacy_pages = []
        backup_path = self.path / '__legacy_pages_backup__'

        for file in os.scandir(self.path):
            if self.is_v4_page(file.path):
                continue

            if os.path.isdir(file.path):
                continue

            try:
                if file.path.endswith('.misl'):
                    page_state = _convert_v2_to_v4(file.path)

                elif file.path.endswith('.json'):
                    page_state = _convert_v3_to_v4(file.path)

                else:
                    log.warning('Untracked file in the repo: %s' % file.name)
                    continue
            except Exception as e:
                log.error(f'Exception raised when processing legacy page '
                          f'{file.path}: {e}')
                continue

            if not page_state:
                log.warning('Empty page state for legacy page %s' % file.name)
                continue

            note_states = page_state.pop('note_states', [])
            notes = []
            for nid, ns in note_states.items():
                # ns['type_name'] = 'TextNote'
                type_name = pamet.note_type_from_props(ns).__name__
                notes.append(entity_library.from_dict(type_name, ns))

            self.create_page(
                entity_library.from_dict(Page.__name__, page_state), notes)
            legacy_pages.append(Path(file.path))

        if legacy_pages:
            backup_path.mkdir(parents=True, exist_ok=True)

        for page_path in legacy_pages:
            page_backup_path = backup_path / (page_path.name + '.backup')
            page_path.rename(page_backup_path)
            log.info('Loaded legacy page %s and backed it up as %s' %
                     (page_path, page_backup_path))

    def save_changes(self, changes: List[Change]):
        # TODO: At some point this should become async to avoid freezes
        t0 = time.time()
        self._try_to_save(changes)

        # If there's a big save lag log a warining
        if time.time() - t0 > 0.03:
            log.warning('The save time was above 30ms. Maybe it\'s time to '
                        'implement the async IO')
