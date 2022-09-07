from thefuzz import fuzz

from pamet.services.search.base import BaseSearchService, SearchResult


class FuzzySearchService(BaseSearchService):

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
            else:
                score = fuzz.partial_ratio(text, index_entry.content_lowered)
                score = (score / 100) * 0.98

            if score <= 0.5:
                continue

            search_result = SearchResult(
                note_gid,
                content_string=index_entry.content_string,
                score=score)
            search_results.append(search_result)

        return sorted(search_results, key=lambda r: r.score, reverse=True)
