"""
Data models for the session component.
"""

from pydantic import BaseModel


class GS_ResponseModel(BaseModel):
    """
    Represents the raw response from a search engine.

    Attributes:
        content (bytes): The raw binary content of the HTTP response body.
    """
    content: bytes = b""

__all__ = ["GS_ResponseModel"]