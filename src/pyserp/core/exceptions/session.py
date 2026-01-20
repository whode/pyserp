"""
Exceptions for the session component.

This module defines errors arising from the session management layer and
HTTP request execution logic (e.g., status code errors, transport failures).
"""

from typing import Any

from .base import BaseError


class StatusCodeError(BaseError):
    """
    Raised when the search engine returns a non-200 HTTP status code.
    """

    def __init__(self, status_code: int, reason: str, debug_info: Any = None):
        super().__init__(f"Status code is {status_code}: {reason}.", debug_info)


class ClientError(BaseError):
    """
    Raised for general network or protocol errors (wraps aiohttp client errors).
    """
    pass

__all__ = ["StatusCodeError", "ClientError"]