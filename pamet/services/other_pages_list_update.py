from fusion.libs.action import action
from fusion.libs.entity.change import Change
from fusion.util.point2d import Point2D
from pamet import channels
import pamet
from pamet.constants import ALIGNMENT_GRID_UNIT
from pamet.model.note import Note
from pamet.model.op_list_note import OtherPageListNote
from pamet.model.page import Page
from pamet.model.text_note import TextNote
from pamet.util import snap_to_grid
from pamet.views.note.qt_helpers import minimal_nonelided_size

DUPLICATE_LIST_NOTE_WARNING = 'Only one OtherPageList note allowed per page.'

# Test cases:
# Add/remove/update link note in a page with an OPList
# Add page


class OtherPagesListUpdateService:

    def __init__(self) -> None:
        self.OPL_notes_by_page_id = {}

    def start(self):
        channels.entity_change_sets_per_TLA.subscribe(
            self.handle_entity_changes)

        # Create the oplist cache
        for note in pamet.find(type=OtherPageListNote):
            if note.page_id in self.OPL_notes_by_page_id:
                self.swap_duplicate_OPLNote_for_warning(note)
                continue
            self.OPL_notes_by_page_id[note.page_id] = note

        self.update_all_oplists()

    @action('swap_duplicate_oplist_note_for_warning')
    def swap_duplicate_OPLNote_for_warning(self, note: OtherPageListNote):
        note = TextNote().with_id(note.id)
        note.text = DUPLICATE_LIST_NOTE_WARNING
        pamet.update_note(note)

    @action('update_all_oplists')
    def update_all_oplists(self):
        for page_id in self.OPL_notes_by_page_id:
            self.update_oplist(page_id)

    @action('update_oplist')
    def update_oplist(self, page_id: str):
        if page_id not in self.OPL_notes_by_page_id:
            return

        oplist_note = self.OPL_notes_by_page_id[page_id]

        # Get all the other notes in the page. Make a set with the ones linking
        # to internal pages and fill in the OPList to hold links to all pages
        link_notes_by_page_id = {}
        all_page_ids = [page.id for page in pamet.pages()]
        notes = pamet.notes(page_id)
        notes_probably_in_list = []
        list_left_border = oplist_note.rect().x() + ALIGNMENT_GRID_UNIT
        for note in notes:
            if note.rect().x() == list_left_border:
                notes_probably_in_list.append(note)

            if not note.url.is_internal():
                continue
            link_notes_by_page_id[note.url.get_page_id()] = note

        missing_links = set(all_page_ids) - set(link_notes_by_page_id)
        spawn_pos = oplist_note.rect().bottom_left() + Point2D(
            ALIGNMENT_GRID_UNIT, ALIGNMENT_GRID_UNIT)

        # Find the bottom of the list in order to add the note there
        probe_spawn_pos = spawn_pos
        while probe_spawn_pos and notes_probably_in_list:
            found_next = False
            for note in notes_probably_in_list:
                rect = note.rect()
                if rect.contains(probe_spawn_pos):
                    probe_spawn_pos = (rect.bottom_left() +
                                       Point2D(0, ALIGNMENT_GRID_UNIT))
                    found_next = True
                    break

            if not found_next:
                spawn_pos = probe_spawn_pos
                probe_spawn_pos = None
                break

        for missing_page_id in missing_links:
            new_note = TextNote.in_page(page_id=page_id)
            new_note.url = pamet.page(missing_page_id).url()

            # Move to the initial spawn position
            rect = new_note.rect()
            rect.set_top_left(spawn_pos)

            # Autosize
            new_size = minimal_nonelided_size(new_note)
            rect.set_size(snap_to_grid(new_size))

            # Move to the spawn pos
            rect.set_top_left(spawn_pos)

            new_note.set_rect(rect)
            pamet.insert_note(new_note)

            # Move the spawn pos
            spawn_pos.set_y(rect.bottom() + ALIGNMENT_GRID_UNIT)

    def handle_entity_changes(self, change_set: list[Change]):
        pages_for_update = set()

        for change in change_set:
            entity = change.last_state()

            if isinstance(entity, Note):
                # If its an OPList note - keep the cache up to date
                if isinstance(entity, OtherPageListNote):
                    if change.is_create():
                        # If there's already an OPList note in that page -
                        # disable it
                        if entity.page_id in self.OPL_notes_by_page_id:
                            self.swap_duplicate_OPLNote_for_warning(entity)
                            continue

                        self.OPL_notes_by_page_id[entity.page_id] = entity
                        pages_for_update.add(entity.page_id)
                    elif change.is_delete():
                        self.OPL_notes_by_page_id.pop(entity.page_id)

                # If the note change is in one of the pages with an OPList
                # if it's a change in the internal link - update the OPList
                elif entity.page_id in self.OPL_notes_by_page_id:
                    if ((entity.url.is_internal()) and
                        (change.is_create() or change.is_delete())
                            or (change.is_update() and change.updated.url)):
                        pages_for_update.add(entity.page_id)

                for page_id in pages_for_update:
                    self.update_oplist(page_id)

            elif isinstance(entity, Page) and change.is_create():
                self.update_all_oplists()
