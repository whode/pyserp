"""
Data models for Bing SERP parsing.

This module defines the schemas for Bing search results using a static
structure with optional fields to handle variability in data presence.
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
    Represents a prominent sitelink.
    """
    pass


class OrganicResultModel(BaseModel):
    """
    Model for Bing organic search results.

    Attributes:
        url (str): The main result URL.
        title (str): The result headline.
        site_name (str): The name of the website.
        time (str | None): Publication time/date.
        snippet (str | None): Result description.
        sitelinks (list | None): List of nested links.
    """
    url: str
    title: str
    site_name: str
    time: str | None = None
    snippet: str | None = None
    sitelinks: list[OrganicResultSitelinkModel] | list[MainOrganicResultSitelinkModel] | None = None


class SearchResultsModel(BaseModel):
    """
    Container for the list of organic results.
    """
    organic: list[OrganicResultModel | ErrorModel]


class BSERP_Model(SERP_BaseModel):
    """
    Top-level model for a Bing Search Results Page.

    Attributes:
        has_more (bool): Indicates if there is a 'Next' page available.
        results (SearchResultsModel): Container for the parsed results.
    """
    has_more: bool
    results: SearchResultsModel


__all__ = [
    "OrganicResultSitelinkModel",
    "MainOrganicResultSitelinkModel",
    "OrganicResultModel",
    "SearchResultsModel",
    "BSERP_Model",
]
