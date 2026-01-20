"""
Search engine providers.

This package contains concrete implementations of the library's core interfaces
for specific search engines (e.g., Bing, Google).
"""

from .bing import BingSearcherManager, BingSearchSessionsManager
from .google import GoogleSearcherManager, GoogleSearchSessionsManager

__all__ = ["GoogleSearcherManager", "GoogleSearchSessionsManager",
           "BingSearcherManager", "BingSearchSessionsManager"]