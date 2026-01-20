"""
Searcher implementation for Google.

This module maps the generic search logic to Google's specific query parameters,
such as `num` for results count and `start` for pagination offset.
"""

from ...core.searcher import SearcherBase, SearcherManagerBase
from ...core.utils import log_class
from .models.parser import GSERP_Model
from .parser import GSERP_Parser
from .session import GoogleSearchSession, GoogleSearchSessionsManager


@log_class
class GoogleSearcher(SearcherBase[GoogleSearchSession, GSERP_Model]):
    """
    Google searcher implementation.
    """

    @staticmethod
    def _serp_organic_results_limit():
        return 400  # Approximate upper limit known to the community

    def _get_results_per_page(self, params: dict) -> int | None:
        return (params or {}).get("num", None)

    def _create_params_addition(self, query: str, start: int) -> dict:
        """
        Creates Google-specific parameters.
        """
        return {"q": query, "start": start}
    
@log_class
class GoogleSearcherManager(SearcherManagerBase[GoogleSearchSession, GSERP_Model]):
    """
    Manager for GoogleSearcher.
    """
    _SearchSessionsManager = GoogleSearchSessionsManager
    _SERP_Parser = GSERP_Parser
    _Searcher = GoogleSearcher


__all__ = ["GoogleSearcher", "GoogleSearcherManager"]
