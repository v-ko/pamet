from pamet.services.search.base import BaseSearchService, SearchResult


class PlainSearchService(BaseSearchService):
    def text_search(self, text: str) -> SearchResult:
        """Searches the cached texts and returns search results"""
        search_results = []
        text = text.lower()
        for note_gid, index_entry in self.index.items():
            score = 0
            if index_entry.content_lowered.startswith(text):
                score = 1
            elif index_entry.content_lowered.find(text):
                score = 0.99

            if score <= 0:
                continue

            search_result = SearchResult(note_gid)
            search_results.append(search_result)

        return sorted(search_results, key=lambda r: r.score, reverse=True)
