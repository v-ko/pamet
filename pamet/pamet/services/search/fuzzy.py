from thefuzz import fuzz

from pamet.services.search.base import BaseSearchService, SearchResult


class FuzzySearchService(BaseSearchService):

    def text_search(self, text: str) -> SearchResult:
        """Searches the cached texts and returns search results"""
        search_results = []
        for note_gid, content_string in self.content_strings.items():
            score = 0
            if content_string.startswith(text):
                score = 1
            else:
                score = fuzz.token_set_ratio(text, content_string)
                score = score * 0.99

            if score <= 0:
                continue

            search_result = SearchResult(note_gid,
                                         content_string=content_string,
                                         score=score)
            search_results.append(search_result)

        return sorted(search_results, key=lambda r: r.score, reverse=True)
