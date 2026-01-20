"""
Exceptions for the parser component.

This module defines errors that occur during the processing and extraction
of data from HTML content.
"""

from typing import Any

from .base import BaseError


class EmptyPageError(BaseError):
    """
    Raised when the retrieved SERP HTML content is empty or None.
    """

    def __init__(self, debug_info: Any = None):
        super().__init__("The SERP html is empty.", debug_info)


class PageParsingError(BaseError):
    """
    Raised when the parser fails to extract data from the HTML structure.

    This usually indicates that the search engine's layout has changed
    or the response contains an unexpected format (e.g., a captcha).
    """
    pass

__all__ = ["EmptyPageError", "PageParsingError"]