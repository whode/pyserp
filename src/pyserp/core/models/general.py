"""
General purpose data models.
"""

from typing import Any

from pydantic import BaseModel


class ErrorModel(BaseModel):
    """
    Represents a captured error during the search process.

    This model is returned instead of raising an exception when
    methods like `search_many` or `search_top` encounter errors
    but are configured to continue execution.

    Attributes:
        error_type (str): The classification or name of the error (e.g., the exception class name).
        message (str): The string representation of the error message.
        debug_info (Any): Arbitrary context for debugging (e.g., stack trace, raw HTML).
    """
    error_type: str
    message: str
    debug_info: Any


__all__ = ["ErrorModel"]
