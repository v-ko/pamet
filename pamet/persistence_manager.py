from typing import List
from fusion.libs.entity.change import Change
from fusion.libs.entity import Entity
from fusion.libs.channel import Channel
from fusion.storage.in_memory_repository import InMemoryRepository
from fusion.storage.repository import Repository
from pamet.storage.base_repository import PametRepository


class PersistenceManager(Repository):
    """TODO: finish the implementation.
    Receives changesets on the input_channel and sends them to the async repo.
    Then receives the successfull and unsuccessfull saves on the respective
    channels and applies some policy to handle the unsuccessful ones (initially
    just throw an error or something)

    Also the state of the class can be connected to the gui to reflect the
    save status. donno how yet"""

    def __init__(self,
                 in_channel: Channel,
                 sync_repo: PametRepository,
                 async_repo: Repository = None):
        self.in_channel = in_channel
        self.sync_repo = sync_repo
        self.async_repo = async_repo
        self._change_sets = []

        # Create out/save channels
        # self._out_channel = Channel('CHANGES_FOR_SAVING')
        # self._saved_changes_channel = Channel('SAVED_CHANGES')
        self.changes_for_async_save_channel = Channel(
            '__CHANGES_FOR_ASYNC_SAVE__')
        self.unsuccessfully_saved_changes_channel = Channel(
            '__UNSUCCESSFUL_SAVES__')
        self.successfully_saved_changes_channel = Channel(
            '__SUCCESSFUL_SAVES__')

        # Connect the channels
        self.in_channel.subscribe(self.queue_save_for_changeset)
        self.repository.set_save_channel(self._saved_changes_channel)
        self.successfully_saved_changes_channel.subscribe(
            self.handle_saved_changes)

        # crud methods with buffering and calling the repo when the object is
        # not buffered

    def handle_saved_changes(self, changes: List[Change]):
        pass

    def queue_save_for_changeset(self, changes: List[Change]):
        self._change_sets.append(changes)
