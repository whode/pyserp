"""
Data models representing the aggregated output of search operations.
"""

from typing import Generic

from pydantic import BaseModel

from .models.general import ErrorModel
from .models.parser import SERP_Specific_Type


class SearchResultBaseModel(BaseModel, Generic[SERP_Specific_Type]):
    """
    Generic container for a collection of search result pages.

    Attributes:
        pages (list[SERP_Specific_Type | ErrorModel]): A list containing either
            successfully parsed pages or error objects.
    """
    pages: list[SERP_Specific_Type | ErrorModel]

class SearchManyResultModel(SearchResultBaseModel):
    """
    Result model for the `search_many` operation.
    """
    pass

class SearchTopResultModel(SearchResultBaseModel):
    """
    Result model for the `search_top` operation.
    """
    pass


__all__ = ["SearchResultBaseModel", "SearchManyResultModel", "SearchTopResultModel"]
