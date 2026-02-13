"""
Core search logic and orchestration module.

This module provides the base classes for performing search operations. It includes
`SearcherBase`, which encapsulates the logic for single and multi-page searches,
handling retries, pagination, and error management. It also includes
`SearcherManagerBase`, which acts as a factory and manager for the searcher,
dependencies, and resources like executors and semaphores.
"""

import asyncio
import math
import os
import traceback
from abc import ABC, abstractmethod
from asyncio import Semaphore
from collections.abc import AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
from typing import Generic

from .exceptions.base import BaseError
from .models.general import ErrorModel
from .models.parser import SERP_Specific_Type
from .parser import SERP_Parser_Base
from .primitives import PositiveInt
from .searcher_model import SearchManyResultModel, SearchTopResultModel
from .session import SearchSessionsManagerBase, SearchSessionType
from .utils import configured_validate_call, log_class


@log_class
class SearcherBase(ABC, Generic[SearchSessionType, SERP_Specific_Type]):
    """
    Abstract base class for search engine interactions.

    This class implements the core algorithms for fetching and orchestrating
    the parsing of search results. It supports fetching a single page, specific
    pages by offset, or collecting a "top N" results by automatically handling
    pagination logic.
    """

    @abstractmethod
    def _get_results_per_page(self, params: dict) -> int | None:
        """
        Extracts the requested number of results per page from the search parameters.

        Args:
            params (dict): The search parameters.

        Returns:
            int | None: The count if found, otherwise None.
        """
        pass

    @abstractmethod
    def _create_params_addition(self, query: str, start: int) -> dict:
        """
        Creates engine-specific parameters for pagination and query injection.

        Args:
            query (str): The search query.
            start (int): The offset for the search results (pagination).

        Returns:
            dict: A dictionary of parameters to merge with the base request.
        """
        pass

    @staticmethod
    @abstractmethod
    def _serp_organic_results_limit() -> PositiveInt:
        """
        Returns the theoretical maximum number of organic results the engine provides.
        """
        pass

    @configured_validate_call
    def __init__(self, search_sessions_manager: SearchSessionsManagerBase[SearchSessionType],
                 parser: SERP_Parser_Base[SERP_Specific_Type], semaphore: asyncio.Semaphore,
                 results_per_page: PositiveInt | None = None,
                 pages_per_time_default: PositiveInt | None = None):
        """
        Initializes the SearcherBase.

        Args:
            search_sessions_manager (SearchSessionsManagerBase): Manager to handle session rotation.
            parser (SERP_Parser_Base): Parser to process the HTML responses.
            semaphore (asyncio.Semaphore): Semaphore to limit concurrent requests.
            results_per_page (PositiveInt | None): Default number of results per page (defaults to 10).
            pages_per_time_default (PositiveInt | None): Default number of pages to fetch concurrently (defaults to 1).
        """
        self._search_sessions_manager = search_sessions_manager
        self._parser = parser

        self._semaphore = semaphore

        self._results_per_page = results_per_page or 10
        self._pages_per_time_default = pages_per_time_default or 1

    @configured_validate_call
    async def search_one(self, query: str, start: int = 0, params: dict | None = None,
                         headers: dict | None = None, cookies: dict | None = None,
                         proxy: str | None = None, tries: PositiveInt | None = None
                         ) -> SERP_Specific_Type | ErrorModel:
        """
        Performs a search for a single page of results.

        This method attempts to fetch and parse a specific SERP. It includes built-in
        retry logic for handling transient errors.

        Args:
            query (str): The search query string.
            start (int): The offset for results (default is 0).
            params (dict | None): Additional query parameters.
            headers (dict | None): Custom HTTP headers.
            cookies (dict | None): Custom cookies.
            proxy (str | None): Proxy URL to use for this specific request.
            tries (PositiveInt | None): Number of retry attempts (default is 3).

        Returns:
            SERP_Specific_Type | ErrorModel: The parsed result model if successful,
            or an ErrorModel if all retries fail.
        """
        final_params = (params or {}) | self._create_params_addition(query, start)
        retries = tries or 3
        
        async with self._semaphore:
            for _ in range(retries):
                try:
                    search_session = (await self._search_sessions_manager.get_search_session())
                    serp = await search_session.get_serp(final_params, headers, cookies, proxy)
                    parsed_serp = await self._parser.parse(serp.content)
                except BaseError as e:
                    formatted_traceback = traceback.format_exc()
                    full_debug_info = {
                        "original_debug_info": e.debug_info,
                        "traceback": formatted_traceback,
                    }
                    error = ErrorModel(error_type=type(e).__name__, message=e.message,
                                       debug_info=full_debug_info)
                else:
                    return parsed_serp
            return error

    @configured_validate_call
    async def search_many_gen(self, query: str, starts: list[int] | None = None,
                              params: dict | None = None, headers: dict | None = None,
                              cookies: dict | None = None, proxy: str | None = None,
                              tries: PositiveInt | None = None, in_order: bool | None = None
                              ) -> AsyncGenerator[SERP_Specific_Type | ErrorModel]:
        """
        Asynchronously yields search results for multiple pages (offsets).

        Args:
            query (str): The search query.
            starts (list[int] | None): A list of offsets to fetch. If None,
                defaults to the first 100 results (range 0 to 100).
            params (dict | None): Additional query parameters.
            headers (dict | None): Custom HTTP headers.
            cookies (dict | None): Custom cookies.
            proxy (str | None): Proxy URL.
            tries (PositiveInt | None): Number of retry attempts.
            in_order (bool | None): If True (default), yields results in the order
                of `starts`. If False, yields results as soon as they are available.

        Yields:
            SERP_Specific_Type | ErrorModel: Parsed pages or errors.
        """
        if starts is None:
            results_per_page = (self._get_results_per_page(params) or self._results_per_page)
            starts = list(range(0, 100, results_per_page))

        if in_order is None:
            in_order = True

        tasks = [
            self.search_one(query, start, params, headers, cookies, proxy, tries)
            for start in starts
        ]
        if in_order:
            results = await asyncio.gather(*tasks)
            for result in results:
                yield result
        else:
            for result in asyncio.as_completed(tasks):
                page = await result
                yield page

    async def search_many(self, query: str, starts: list[int] | None = None,
                          params: dict | None = None, headers: dict | None = None,
                          cookies: dict | None = None, proxy: str | None = None,
                          tries: PositiveInt | None = None,
                          in_order: bool | None = None) -> SearchManyResultModel[SERP_Specific_Type]:
        """
        Fetches multiple pages and returns them as a single list model.

        This is a wrapper around `search_many_gen` that aggregates all results.

        Args:
            query (str): The search query.
            starts (list[int] | None): List of offsets.
            params, headers, cookies, proxy, tries, in_order: See `search_many_gen`.

        Returns:
            SearchManyResultModel: A model containing a list of all pages/errors.
        """
        pages = []
        async for page in self.search_many_gen(query, starts, params, headers, cookies, proxy,
                                               tries, in_order):
            pages.append(page)

        return SearchManyResultModel[SERP_Specific_Type](pages=pages)

    async def _search_top_gen(self, query: str, params: dict | None = None,
                              headers: dict | None = None, cookies: dict | None = None,
                              proxy: str | None = None, tries: PositiveInt | None = None,
                              in_order: bool | None = None,
                              pages_per_time_default: PositiveInt | None = None
                              ) -> AsyncGenerator[SERP_Specific_Type | ErrorModel]:
        """
        Internal generator for fetching top results using batch processing.

        Calculates the necessary steps and offsets to cover the theoretical
        limit of organic results, yielding pages in batches.
        """
        results_per_page = self._get_results_per_page(params) or self._results_per_page
        max_pages_required = math.ceil(self._serp_organic_results_limit() / results_per_page)

        if pages_per_time_default is None:
            pages_per_time_default = self._pages_per_time_default

        if pages_per_time_default and pages_per_time_default <= max_pages_required:
            pages_per_time = pages_per_time_default
        else:
            pages_per_time = max_pages_required

        step = results_per_page * pages_per_time
        for skip in range(0, self._serp_organic_results_limit(), step):
            starts = list(range(skip, skip + step, results_per_page))
            search_gen = self.search_many_gen(query, starts, params, headers, cookies, proxy, tries, in_order)
            async for page in search_gen:
                yield page

    @configured_validate_call
    async def search_top_gen(self, query: str, limit: PositiveInt, params: dict | None = None,
                             headers: dict | None = None, cookies: dict | None = None,
                             proxy: str | None = None, tries: PositiveInt | None = None,
                             in_order: bool | None = None,
                             pages_per_time_default: PositiveInt | None = None,
                             ignore_page_errors: bool | None = None,
                             include_page_errors: bool | None = None
                             ) -> AsyncGenerator[SERP_Specific_Type | ErrorModel]:
        """
        Generator that searches for the top N results.

        It continuously fetches pages until the requested `limit` of organic results
        is reached or the search engine stops returning results.

        Args:
            query (str): The search query.
            limit (PositiveInt): The maximum number of organic results to collect.
            params, headers, cookies, proxy, tries, in_order: See `search_one`.
            pages_per_time_default (PositiveInt | None): Override the default batch size.
            ignore_page_errors (bool | None): If True, continues searching even if a page fails.
                If False (default), stops iteration on the first error.
            include_page_errors (bool | None): If True (default), yields ErrorModel objects
                when they occur. If False, silently skips errors.

        Yields:
            SERP_Specific_Type | ErrorModel: Parsed pages or errors until the limit is reached.
        """
        if ignore_page_errors is None:
            ignore_page_errors = False
        if include_page_errors is None:
            include_page_errors = True

        search_gen = self._search_top_gen(query, params, headers, cookies, proxy, tries,
                                          in_order, pages_per_time_default)
        results_count = 0
        async for page in search_gen:
            if isinstance(page, ErrorModel):
                if include_page_errors:
                    yield page
                if not ignore_page_errors:
                    break
            else:
                if len(page.results.organic):
                    yield page
                    results_count += len(page.results.organic)
                if not len(page.results.organic) or not page.has_more:
                    break
            if results_count >= limit:
                break

    async def search_top(self, query: str, limit: PositiveInt, params: dict | None = None,
                         headers: dict | None = None, cookies: dict | None = None,
                         proxy: str | None = None, tries: PositiveInt | None = None,
                         in_order: bool | None = None,
                         pages_per_time_default: PositiveInt | None = None,
                         ignore_page_errors: bool | None = None,
                         include_page_errors: bool | None = None) -> SearchTopResultModel[SERP_Specific_Type]:
        """
        Fetches the top N results and returns them as a single model.

        Wrapper around `search_top_gen`.

        Args:
            query (str): The search query.
            limit (PositiveInt): The maximum number of organic results to collect.
            params, headers, cookies, proxy, tries, in_order: See `search_top_gen`.
            pages_per_time_default, ignore_page_errors, include_page_errors: See `search_top_gen`.

        Returns:
            SearchTopResultModel: A model containing a list of all parsed pages
            and any errors occurred.
        """
        search_gen = self.search_top_gen(query, limit, params, headers, cookies, proxy, tries,
                                         in_order, pages_per_time_default, ignore_page_errors,
                                         include_page_errors)
        pages = []
        async for page in search_gen:
            pages.append(page)

        return SearchTopResultModel[SERP_Specific_Type](pages=pages)

@log_class
class SearcherManagerBase(ABC, Generic[SearchSessionType, SERP_Specific_Type]):
    """
    Abstract manager class for initializing and controlling the searcher lifecycle.

    This class handles the creation of dependencies such as the SessionManager,
    Executor, and Semaphore, ensuring they are properly closed when the manager
    is disposed. It acts as a context manager (`async with`).
    """

    @property
    @staticmethod
    @abstractmethod
    def _SearchSessionsManager() -> type[SearchSessionsManagerBase[SearchSessionType]]:
        """The class of the session manager to use."""
        pass

    @property
    @staticmethod
    @abstractmethod
    def _SERP_Parser() -> type[SERP_Parser_Base[SERP_Specific_Type]]:
        """The class of the parser to use."""
        pass

    @property
    @staticmethod
    @abstractmethod
    def _Searcher() -> type[SearcherBase[SearchSessionType, SERP_Specific_Type]]:
        """The class of the searcher to use."""
        pass

    @configured_validate_call
    def __init__(self, search_sessions_manager: SearchSessionsManagerBase[SearchSessionType] | None = None,
                 executor: ThreadPoolExecutor | None = None, semaphore: Semaphore = None,
                 results_per_page: PositiveInt | None = None,
                 pages_per_time_default: PositiveInt | None = None):
        """
        Initializes the SearcherManager.

        Args:
            search_sessions_manager (SearchSessionsManagerBase | None): Existing session manager.
                If None, a new one is created.
            executor (ThreadPoolExecutor | None): ThreadPoolExecutor for parsing.
                If None, creates one based on CPU count.
            semaphore (Semaphore | None): Concurrency limit. Defaults to 100.
            results_per_page (PositiveInt | None): Default results per page for the searcher.
            pages_per_time_default (PositiveInt | None): Default batch size for the searcher.
        """
        self._should_close_manager = not search_sessions_manager
        self._search_sessions_manager = (search_sessions_manager or self._SearchSessionsManager())

        self._should_close_executor = not bool(executor)
        self._executor = executor or ThreadPoolExecutor(max_workers=os.cpu_count())
        self._serp_parser = self._SERP_Parser(self._executor)

        self._semaphore = semaphore or Semaphore(100)
        self._searcher = self._Searcher(self._search_sessions_manager, self._serp_parser,
                                        self._semaphore, results_per_page, pages_per_time_default)

    @property
    def searcher(self) -> SearcherBase[SearchSessionType, SERP_Specific_Type]:
        """Returns the initialized searcher instance."""
        return self._searcher

    async def close(self, wait: bool | None = True):
        """
        Releases all resources (sessions, executor).

        Args:
            wait (bool | None): If True, waits for the executor to shutdown gracefully.
        """
        if wait is None:
            wait = True

        if self._should_close_manager:
            await self._search_sessions_manager.close()
        if self._should_close_executor:
            self._executor.shutdown(wait=wait)

    async def __aenter__(self) -> SearcherBase[SearchSessionType, SERP_Specific_Type]:
        return self.searcher

    async def __aexit__(self, exc_type, exc_value, tb):
        await self.close()

__all__ = ["SearcherBase", "SearcherManagerBase"]
