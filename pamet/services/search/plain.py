from pamet.services.search.base import BaseSearchService, SearchResult


class PlainSearchService(BaseSearchService):
    def text_search(self, text: str) -> SearchResult:
        """Searches the cached texts and returns search results"""
        search_results = []
        for note_gid, content_string in self.content_strings.items():
            score = 0
            if content_string.startswith(text):
                score = 1
            elif content_string.find(text):
                score = 0.9

            if score <= 0:
                continue

            search_result = SearchResult(note_gid)
            search_results.append(search_result)

        return sorted(search_results, key=lambda r: r.score, reverse=True)
