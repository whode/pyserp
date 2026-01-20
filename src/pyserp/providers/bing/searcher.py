"""
Searcher implementation for Bing.

This module binds the generic search logic to Bing's specific parameters
(e.g., mapping `start` offset to the `first` parameter).
"""

from ...core.searcher import SearcherBase, SearcherManagerBase
from ...core.utils import log_class
from .models import BSERP_Model
from .parser import BSERP_Parser
from .session import BingSearchSession, BingSearchSessionsManager


@log_class
class BingSearcher(SearcherBase[BingSearchSession, BSERP_Model]):
    """
    Bing searcher implementation.
    """
    
    @staticmethod
    def _serp_organic_results_limit():
        return 700  # Approximate upper limit known to the community

    def _get_results_per_page(self, params: dict) -> int | None:
        return (params or {}).get("count", None)

    def _create_params_addition(self, query: str, start: int) -> dict:
        """
        Creates Bing-specific parameters.

        Maps the generic `start` offset to Bing's `first` parameter.
        """
        return {"q": query, "first": start}

@log_class
class BingSearcherManager(SearcherManagerBase[BingSearchSession, BSERP_Model]):
    """
    Manager for BingSearcher.
    """
    _SearchSessionsManager = BingSearchSessionsManager
    _SERP_Parser = BSERP_Parser
    _Searcher = BingSearcher

__all__ = ["BingSearcher", "BingSearcherManager"]
