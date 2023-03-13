from pathlib import Path
from typing import Tuple
import numpy as np
from fusion.libs.channel import Channel

from pamet.services.search.base import BaseSearchService, IndexEntry, SearchResult

try:
    from sqlitedict import SqliteDict
    from sentence_transformers import SentenceTransformer, util
except Exception:
    raise Exception('The semantic search service depends on the python '
                    'packages sentence_transformers and sqlitedict. ')


class SemanticSearchService(BaseSearchService):

    def __init__(self, data_folder: str, change_set_channel: Channel):
        super().__init__(change_set_channel)
        self.data_folder = Path(data_folder)
        self.data_folder.mkdir(parents=True, exist_ok=True)
        self.fv_index = {}  # Feature vectors by text
        self.sqlite_db = SqliteDict(self.data_folder / 'semantic_index.sqlite',
                                    autocommit=True)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.report_item_count = False

    def upsert_to_index(self, entry: IndexEntry):
        if entry.content_string not in self.fv_index:
            self._get_fv(entry.content_string)
        super().upsert_to_index(entry)
        if self.report_item_count:
            print(f'Items in index: {len(self.fv_index)}', end='\r')

    def remove_from_index(self, note_gid: Tuple):
        self.fv_index.pop(note_gid)
        super().remove_from_index(note_gid)
        if self.report_item_count:
            print(f'Items in index: {len(self.fv_index)}', end='\r')

    def _get_fv(self, text: str) -> dict:
        """Returns a feature vector for the given text either from the cache
        or by calculating it"""
        fv = self.fv_index.get(text)

        if fv is None:
            fv = self.embedding_model.encode([text],
                                             show_progress_bar=False)[0]
            self.sqlite_db[text] = fv
            self.fv_index[text] = fv
        return fv

    def text_search(self, text: str) -> SearchResult:
        search_results = []
        text = text.lower()
        query_fv = self.embedding_model.encode([text],
                                               show_progress_bar=False)[0]
        for note_gid, index_entry in self.index.items():
            score = np.linalg.norm(self.fv_index[index_entry.content_string] -
                                   query_fv)

            if score < 10:
                search_results.append(
                    SearchResult(
                        note_gid=note_gid,
                        content_string=(f'{score:.2f}'
                                        f' {index_entry.content_string}'),
                        score=score))

        search_results = sorted(search_results, key=lambda r: r.score)
        return search_results

    def load_all_content(self):
        # Load the feature vectors from the database
        print('Loading feature vectors from database...', end='')
        for text, fv in self.sqlite_db.items():
            self.fv_index[text] = fv
        print('Done')

        self.report_item_count = True
        super().load_all_content()
        self.report_item_count = False
