import time
from typing import Dict, Generator, List
import os
import json
from pathlib import Path
from pamet import desktop_app
from pamet.desktop_app import get_repo_settings, get_user_settings
from pamet.model.arrow import Arrow
from pamet.model.page_child import PageChild
from pamet.storage.pamet_in_memory_repo import PametInMemoryRepository
from slugify import slugify

import fusion
from fusion.libs.entity import Entity, dump_to_dict, load_from_dict
from fusion.libs.entity.change import Change
from fusion.libs.channel import Channel
from fusion.storage.in_memory_repository import InMemoryRepository
from fusion import get_logger

import pamet
from pamet.model.page import Page
from pamet.model.note import Note

from .legacy import LegacyFSRepoReader

log = get_logger(__name__)

V4_FILE_EXT = '.pam4.json'


class FSStorageRepository(PametInMemoryRepository, LegacyFSRepoReader):
    """File system storage. This class has all entities cached at all times"""

    def __init__(self, path, queue_save_on_change=False):
        PametInMemoryRepository.__init__(self)
        LegacyFSRepoReader.__init__(self)

        self.path = Path(path)
        self.queue_save_on_change = queue_save_on_change
        self._page_ids = []

        self._save_channel: Channel = None

        self.page_paths_by_id: Dict[str, Path] = {}

        self.upserted_pages = set()
        self.removed_pages = set()

    def load_all_pages(self):
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
                self.create_page_on_disk(page, notes, arrows)
                log.error(f'Bad page name. Deleted {page_path} and saved the '
                          f'page {page.name} anew.')

            # Check for dupicates
            page_duplicates = list(self.find(gid=page.gid()))
            for page_duplicate in page_duplicates:
                dup_path = self.path_for_page(page_duplicate)

                if dup_path.stat().st_mtime <= page_path.stat().st_mtime:
                    # If the page that's older is loaded
                    InMemoryRepository.remove_one(self, page_duplicate)
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
                InMemoryRepository.insert_one(self, page)
                for note in notes:
                    try:
                        InMemoryRepository.insert_one(self, note)
                    except Exception:
                        log.error(f'Duplicate note. Skipping {note}')
                        continue
                for arrow in arrows:
                    try:
                        InMemoryRepository.insert_one(self, arrow)
                    except Exception:
                        log.error(f'Duplicate arrow. Skipping {arrow}')
                        continue
            except Exception:
                log.error(f'Duplicate page. Skipping {page}')
                continue

            # Save the path corresponding to the id in order to handle renames
            self.page_paths_by_id[page.id] = self.path_for_page(page)

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

    def insert_one(self, entity: Entity):
        if isinstance(entity, Page):
            self.upserted_pages.add(entity)
        elif isinstance(entity, PageChild):
            page = self.page(entity.page_id)
            if not page:
                raise Exception(f'Invalid parent for {entity}')
            self.upserted_pages.add(page)

        InMemoryRepository.insert_one(self, entity)

        return Change.CREATE(entity)

    def insert(self, entities: List[Entity]):
        for entity in entities:
            self.insert_one(entity)

    def remove_one(self, entity):
        InMemoryRepository.remove_one(self, entity)
        if isinstance(entity, Page):
            self.removed_pages.add(entity)
        elif isinstance(entity, PageChild):
            page = self.page(entity.page_id)
            if not page:
                return None
            self.upserted_pages.add(page)

        return Change.DELETE(entity)

    def remove(self, entities: List[Entity]):
        for entity in entities:
            self.remove_one(entity)

    def update_one(self, entity):
        change = InMemoryRepository.update_one(self, entity)
        if isinstance(entity, Page):
            self.upserted_pages.add(entity)
        elif isinstance(entity, PageChild):
            page = self.page(entity.page_id)
            if not page:
                raise Exception(f'Invalid parent for {entity}')
            self.upserted_pages.add(page)
        return change

    def update(self, entities: List[Entity]):
        for entity in entities:
            self.update_one(entity)

    def find(self, **filter):
        yield from InMemoryRepository.find(self, **filter)

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

        for page in self.upserted_pages:
            page = pamet.page(page.id)

            if page.id in self.page_paths_by_id:
                self.update_page_on_disk(page, pamet.notes(page),
                                         pamet.arrows(page))
            else:
                self.create_page_on_disk(page, pamet.notes(page),
                                         pamet.arrows(page))

        for page in self.removed_pages:
            self.delete_page_on_disk(page)

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
        if 'type_name' not in page_state:
            page_state['type_name'] = Page.__name__

        # Detach the children
        note_states = page_state.pop('notes', [])
        arrow_states = page_state.pop('arrows', [])

        # Create the page
        page = load_from_dict(page_state)

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

            id = ns['id']
            if isinstance(id, str):
                assert 'page_id' in ns
                ns['id'] = (ns.pop('page_id'), id)

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

            if 'color' in ns:
                for prop in ['color', 'background_color']:
                    prop_val = ns.pop(prop)
                    if 'style' not in ns:
                        ns['style'] = {}
                    ns['style'][prop] = prop_val

            # /ad-hoc fixes

            notes.append(load_from_dict(ns))

        # Load the arrows
        arrows = []
        for arrow_state in arrow_states:
            # REMOVE vvv
            id = arrow_state['id']
            if isinstance(id, str):
                assert 'page_id' in arrow_state
                arrow_state['id'] = (arrow_state.pop('page_id'), id)

            if 'type_name' not in arrow_state:
                arrow_state['type_name'] = Arrow.__name__
            # arrow_state.pop('background_color', None)
            # if 'mid_point_coords' not in arrow_state:
            #     arrow_state['mid_point_coords'] = arrow_state.pop('
            # mid_points')
            # if 'head_coords' not in arrow_state:
            #     arrow_state['head_coords'] = arrow_state.pop('head_point')
            # if 'tail_coords' not in arrow_state:
            #     arrow_state['tail_coords'] = arrow_state.pop('tail_point')

            # if 'page_id' not in arrow_state or not arrow_state['page_id']:
            #     raise Exception

            try:
                arrow: Arrow = load_from_dict(arrow_state)
            except Exception as e:
                log.error(f'Exception {e} raised while parsing arrow '
                          f'{arrow_state} from file {json_file_path}')
                continue

            arrows.append(arrow)

        return page, notes, arrows

    @staticmethod
    def serialize_page(page: Page, notes: List[Note], arrows: List[Arrow]):
        page_state = dump_to_dict(page)
        page_state['notes'] = [dump_to_dict(n) for n in notes]
        page_state['arrows'] = [dump_to_dict(a) for a in arrows]

        try:
            json_str = json.dumps(page_state, ensure_ascii=False, indent=4)
        except Exception as e:
            raise e  # Or log error
            return None

        return json_str

    def create_page_on_disk(self, page: Page, notes: List[Note],
                            arrows: List[Arrow]):
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

    def update_page_on_disk(self, page: Page, notes: List[Note],
                            arrows: List[Arrow]):
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

    def delete_page_on_disk(self, page):
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

    def save_changes(self, changes: List[Change]):
        t0 = time.time()
        self._try_to_save(changes)

        # If there's a big save lag log a warining
        if time.time() - t0 > 0.03:
            log.warning('The save time was above 30ms. Maybe it\'s time to '
                        'implement the async IO')

    def default_page(self):
        repo_settings = get_repo_settings(self.path)
        default_page = self.page(repo_settings.home_page)
        return default_page

    def set_default_page(self, new_page: Page):
        repo_settings = get_repo_settings(self.path)
        repo_settings.home_page = new_page.id
        desktop_app.save_repo_settings(repo_settings)
