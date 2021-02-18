from .entities import Page
from .pamet import *

misli.subscribe(PAGES_CHANNEL, update_views_for_page_changes)
misli.subscribe(ALL_NOTES_CHANNEL, update_views_for_note_changes)
