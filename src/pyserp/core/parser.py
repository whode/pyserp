"""
Core parsing logic for processing Search Engine Results Pages (SERPs).

This module defines the abstract base class `SERP_Parser_Base`, which serves as the
foundation for all specific search engine parsers (e.g., for Google or Bing).
It handles the orchestration of parsing tasks, specifically offloading CPU-intensive
HTML processing to a separate thread pool to ensure non-blocking asynchronous execution.
"""

import asyncio
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Generic

from .models.parser import SERP_Specific_Type
from .utils import configured_validate_call, log_class


@log_class
class SERP_Parser_Base(ABC, Generic[SERP_Specific_Type]):
    """
    Abstract base class for Search Engine Results Page (SERP) parsers.

    This class defines the interface for parsing HTML content from search engines
    into structured models. It handles the execution of parsing logic within
    a thread pool to prevent blocking the asynchronous event loop during CPU-bound
    parsing operations (e.g., BeautifulSoup processing).
    """

    @abstractmethod
    def parse_serp(self, serp_html: bytes) -> SERP_Specific_Type:
        """
        Parses the raw HTML bytes of a SERP into a specific data model.

        This abstract method must be implemented by concrete parser subclasses
        to handle the specific HTML structure of a search engine.

        Args:
            serp_html (bytes): The raw HTML content of the search results page.

        Returns:
            SERP_Specific_Type: An instance of a pydantic model representing
            the parsed data.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
            pydantic.ValidationError: If the parsed data does not match the model schema.
        """
        pass

    @configured_validate_call
    def __init__(self, executor: ThreadPoolExecutor):
        """
        Initializes the parser with a thread pool executor.

        Args:
            executor (ThreadPoolExecutor): The executor to be used for offloading
                CPU-bound parsing tasks.
        """
        self._executor = executor

    async def parse(self, serp_html: bytes) -> SERP_Specific_Type:
        """
        Asynchronously parses the SERP HTML using the configured executor.

        This method wraps the synchronous `parse_serp` method, scheduling it
        to run in the default asyncio loop's executor to avoid blocking.

        Args:
            serp_html (bytes): The raw HTML content of the search results page.

        Returns:
            SERP_Specific_Type: The parsed structured data model.

        Example:
            ```python
            class MyParser(SERP_Parser_Base[MyModel]):
                def parse_serp(self, html):
                    return MyModel(...)

            executor = ThreadPoolExecutor()
            parser = MyParser(executor)
            result = await parser.parse(b"<html>...</html>")
            ```
        """
        loop = asyncio.get_running_loop()
        parsed_serp = await loop.run_in_executor(self._executor, self.parse_serp, serp_html)
        return parsed_serp


__all__ = ["SERP_Parser_Base"]
