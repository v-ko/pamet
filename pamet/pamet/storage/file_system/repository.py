from copy import copy
from typing import List
import os
import json
from pathlib import Path
from collections import defaultdict

import misli
from misli import entity_library, Entity, Change
# from misli.gui.view_library import TYPE_NAME
from misli.helpers import find_many_by_props, test
from misli.storage.repository import Repository
import pamet

from pamet.model import Page, Note

from .hacky_backups import backup_page_hackily
from .legacy import _convert_v2_to_v4, _convert_v3_to_v4

from misli import get_logger

log = get_logger(__name__)

RANDOMIZE_TEXT = False
V4_FILE_EXT = '.misl.json'


class FSStorageRepository(Repository):
    """File system storage. This class has all entities cached at all times"""

    def __init__(self, path):
        Repository.__init__(self)

        self.path = Path(path)
        self._page_ids = []

        self._entity_cache = {}
        self._entity_cache_by_parent = defaultdict(set)

        self.upserted_pages = set()
        self.removed_pages = set()
        self.pages_for_write_removal = {}

        self._process_legacy_pages()

        # Load all pages in cache

        for page_name in self.page_names():
            page, notes = self.get_page_and_notes(page_name)
            self.upsert_to_cache(page)
            for note in notes:
                self.upsert_to_cache(note)

    def _path_for_page(self, page_name):
        name = page_name + V4_FILE_EXT
        return os.path.join(self.path, name)

    @classmethod
    def open(cls, path):
        if not os.path.exists(path) or not os.path.isdir(path):
            raise Exception('Bad path. Cannot create repository for', path)

        return cls(path)

    @classmethod
    def new(cls, path):
        if os.path.exists(path):
            if os.listdir(path):
                raise Exception(
                    f'Cannot create repository in non-empty folder {path}')

        os.makedirs(path, exist_ok=True)
        return cls(path)

    def upsert_to_cache(self, entity: Entity):
        self._entity_cache[entity.gid()] = entity
        if entity.parent_gid():
            self._entity_cache_by_parent[entity.parent_gid()].add(entity.gid())

    def remove_from_cache(self, entity: Entity):
        self._entity_cache.pop(entity.gid(), None)
        if entity.parent_gid():
            self._entity_cache_by_parent[entity.parent_gid()].remove(
                entity.gid())

    def insert_one(self, entity):
        if entity.gid() in self._entity_cache:
            raise Exception('Cannot insert {entity}, since it already exists')

        self.upsert_to_cache(entity)
        if isinstance(entity, Page):
            self.upserted_pages.add(entity.gid())
        elif isinstance(entity, Note):
            self.upserted_pages.add(entity.parent_gid())

    def insert(self, entities: List[Entity]):
        for entity in entities:
            self.insert_one(entity)

        # Async to allow for grouping of all calls within an e.g. action
        misli.call_delayed(self.write_to_disk, 0)

    def remove_one(self, entity):
        if entity.gid() not in self._entity_cache:
            raise Exception(f'Cannot remove missing {entity}')

        self.remove_from_cache(entity)
        if isinstance(entity, Page):
            self.removed_pages.add(entity.gid())
            self.pages_for_write_removal[entity.gid()] = entity
        elif isinstance(entity, Note):
            self.upserted_pages.add(entity.parent_gid())

    def remove(self, entities: List[Entity]):
        for entity in entities:
            self.remove_one(entity)

        # Async to allow for grouping of all calls within an e.g. action
        misli.call_delayed(self.write_to_disk, 0)

    def update_one(self, entity):
        if entity.gid() not in self._entity_cache:
            raise Exception('Cannot update missing {entity}')

        self.upsert_to_cache(entity)
        if isinstance(entity, Page):
            self.upserted_pages.add(entity.gid())
        elif isinstance(entity, Note):
            self.upserted_pages.add(entity.parent_gid())

    def update(self, entities: List[Entity]):
        for entity in entities:
            self.update_one(entity)

        # Async to allow for grouping of all calls within an e.g. action
        misli.call_delayed(self.write_to_disk, 0)

    def find(self, **filter):
        # If searching by gid - there will be only one unique result (if any)
        if 'gid' in filter:
            gid = filter.get('gid')
            result = self._entity_cache.get(gid, None)
            yield from [result] if result else []

        # If searching by parent_gid - use the index to do it efficiently
        elif 'parent_gid' in filter:
            parent_gid = filter.pop('parent_gid')
            found = self._entity_cache_by_parent.get(parent_gid, [])
            found_entities = [self._entity_cache[gid] for gid in found]
            if not filter:
                yield from found_entities
            else:
                yield from find_many_by_props(found_entities, **filter)
        else:
            search_set = self._entity_cache.values()
            if 'type_name' in filter:
                type_name = filter.pop('type_name')
                search_set = [
                    ent for gid, ent in self._entity_cache.items()
                    if type(ent).__name__ == type_name
                ]
            found = list(find_many_by_props(search_set, **filter))
            yield from found

    def write_to_disk(self):
        if self.upserted_pages.intersection(self.removed_pages):
            raise Exception('A page is both marked for upsert and removal.')

        for page_gid in self.upserted_pages:
            page = misli.find_one(gid=page_gid)
            if os.path.exists(self._path_for_page(page.name)):
                self.update_page(page, page.notes())
            else:
                self.create_page(page, page.notes())

        for page_gid in self.removed_pages:
            page = self.pages_for_write_removal.pop(page_gid)
            self.delete_page(page)

        self.upserted_pages.clear()
        self.removed_pages.clear()

    def create_page(self, page, notes):
        page_state = page.asdict()
        page_state['note_states'] = [n.asdict() for n in notes]

        path = self._path_for_page(page.name)
        try:
            if os.path.exists(path):
                log.error('Cannot create page. File already exists %s' % path)
                return

            with open(path, 'w') as pf:
                json.dump(page_state, pf, ensure_ascii=False)

        except Exception as e:
            log.error('Exception while creating page at %s: %s' % (path, e))

    def page_names(self):
        page_names = []

        for file in os.scandir(self.path):
            if self.is_v4_page(file.path):
                page_name = file.name[:-len(V4_FILE_EXT)]  # Strip extension

                if not page_name:
                    log.warning('Page with no id at %s' % file.path)
                    continue

                page_names.append(page_name)

        return page_names

    def get_page_and_notes(self, page_name):
        path = self._path_for_page(page_name)

        try:
            with open(path) as pf:
                page_state = json.load(pf)

        except Exception as e:
            log.error('Exception %s while loading page' % e, path)
            return None

        # # TODO REMOVE
        # page_state['name'] = page_state.get('id')
        page_state.pop('type_name', '')  # Refactoring fixes

        note_states = page_state.pop('note_states', [])
        notes = []
        for ns in note_states:

            ns.pop('type_name', '')  # Refactoring fixes
            if 'x' in ns: # Refactoring fixes
                x = ns.pop('x')
                y = ns.pop('y')
                width = ns.pop('width')
                height = ns.pop('height')
                ns['geometry'] = [x, y, width, height]

            if 'time_created' in ns:
                ns['created'] = ns.pop('time_created')
                ns['modified'] = ns.pop('time_modified')

            type_name = pamet.note_type_from_props(ns).__name__
            notes.append(entity_library.from_dict(type_name, ns))

        return entity_library.from_dict(Page.__name__, page_state), notes

    def update_page(self, page, notes):
        page_state = page.asdict()
        page_state['note_states'] = [n.asdict() for n in notes]

        path = self._path_for_page(page.id)
        if os.path.exists(path):
            backup_page_hackily(path)
        else:
            log.error(f'[update_page] Page at {path} was missing.')

        with open(path, 'w') as pf:
            json.dump(page_state, pf, ensure_ascii=False)

    def delete_page(self, page):
        path = self._path_for_page(page.id)

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
                print('dsa')
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
        for change in changes:
            if change.is_create():
                self.insert_one(change.last_state())
            elif change.is_delete():
                self.remove_one(change.last_state())
            elif change.is_update():
                self.update_one(change.last_state())
        misli.call_delayed(self.write_to_disk, 0)
