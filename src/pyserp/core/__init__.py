"""
Core components of the library.

This package exports the fundamental building blocks: base classes for searchers,
session managers, exceptions, and data models.
"""

from .exceptions import BaseError
from .models import ErrorModel
from .searcher import SearcherManagerBase
from .session import SearchSessionsManagerBase

__all__ = ["ErrorModel", "BaseError",
           "SearcherManagerBase",
           "SearchSessionsManagerBase"]