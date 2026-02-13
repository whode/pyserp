"""
Base exception definition.
"""

from typing import Any


class BaseError(Exception):
    """
    Base exception class for all library-specific errors.

    Attributes:
        message (str): A human-readable error message.
        debug_info (Any): Arbitrary data useful for debugging (e.g., HTML content, stack traces).
    """
    
    def __init__(self, message: str = "", debug_info: Any = None):
        super().__init__(message)
        self.message = message
        self.debug_info = debug_info


__all__ = ["BaseError"]
