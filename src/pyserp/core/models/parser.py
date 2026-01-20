"""
Base models for the parser component.
"""

from typing import TypeVar

from pydantic import BaseModel


class SERP_BaseModel(BaseModel):
    """
    Base Pydantic model for all specific SERPs.

    Concrete implementations (like Google or Bing models) must inherit from this.
    """
    pass

SERP_Specific_Type = TypeVar('SERP_Specific_Type', bound=SERP_BaseModel)

__all__ = ["SERP_BaseModel"]