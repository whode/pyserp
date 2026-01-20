"""
Data models for Google SERP parsing.

This module defines the schemas for Google search results using a static model
approach. It handles different layout versions (v1/v2 vs v3) via Pydantic Unions,
distinguishing them by required fields (e.g., 'site_name' for v3, 'breadcrumbs' for legacy).
"""

from pydantic import BaseModel

from ....core.models.general import ErrorModel
from ....core.models.parser import SERP_BaseModel


class OrganicResultSitelinkModel(BaseModel):
    """
    Represents a standard sitelink (sub-link) within a result.
    """
    url: str
    title: str


class MainOrganicResultSitelinkModel(OrganicResultSitelinkModel):
    """
    Represents a prominent sitelink that includes a description/snippet.
    """
    snippet: str


class OrganicResultBaseModel(BaseModel):
    """
    The fundamental fields present in every organic result across all versions.
    """
    url: str
    title: str
    time: str | None = None
    snippet: str | None = None
    sitelinks: list[OrganicResultSitelinkModel] | list[MainOrganicResultSitelinkModel] | None = None


class OrganicResult_v3_Model(OrganicResultBaseModel):
    """
    Base model for Version 3 organic results (Modern).
    """
    v: int = 3
    site_name: str


class OrganicResult_small_Model(OrganicResultBaseModel):
    """
    Base model for Version 1 and 2 organic results (Legacy).
    """
    breadcrumbs: str
    

class SearchResultsModel(BaseModel):
    """
    Container for the list of organic results.

    The organic list can be strictly typed as either a list of Modern (v3) results
    or a list of Legacy (v1/v2) results, depending on the parsed page version.
    """
    organic: list[OrganicResult_v3_Model | ErrorModel] | list[OrganicResult_small_Model | ErrorModel]


class GSERP_Model(SERP_BaseModel):
    """
    Top-level model for Google Search Results Page.

    Attributes:
        results (SearchResultsModel): The parsed results container.
        has_more (bool): Indicates if pagination is possible.
    """
    results: SearchResultsModel
    has_more: bool


__all__ = [
    "OrganicResultSitelinkModel",
    "MainOrganicResultSitelinkModel",
    "OrganicResultBaseModel",
    "OrganicResult_v3_Model",
    "OrganicResult_small_Model",
    "SearchResultsModel",
    "GSERP_Model",
]
