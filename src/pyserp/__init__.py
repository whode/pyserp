"""
pyserp: A comprehensive asynchronous library for scraping and parsing Search Engine Results Pages (SERPs).

This library provides a modular architecture for querying search engines (like Google and Bing),
managing sessions, and parsing the resulting HTML into structured data models.
"""

from .core import BaseError, ErrorModel

__all__ = ["BaseError", "ErrorModel"]

__version__ = "1.0.2.post2"