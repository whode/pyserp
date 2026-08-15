"""
Session management logic for search engine interactions.

This module defines the abstractions for:
1. `SearchSessionBase`: Represents a single logical session with a specific engine
   (handling cookies, base headers, and request execution).
2. `SearchSessionsManagerBase`: Manages a pool of `aiohttp.ClientSession` objects,
   handles proxy rotation, and dispenses search sessions according to a rotation strategy.
"""

import warnings
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from urllib.parse import urlencode

import aiohttp
from yarl import URL

from .exceptions.session import ClientError, StatusCodeError
from .models.session import GS_ResponseModel
from .primitives import PositiveInt
from .utils import configured_validate_call, log_class


@log_class
class SearchSessionBase(ABC):
    """
    Abstract base class for a single search engine session.

    Encapsulates an `aiohttp.ClientSession` along with specific headers, cookies,
    and proxy settings required to interact with a search engine.
    """

    @property
    @staticmethod
    @abstractmethod
    def _init_url() -> str:
        """The URL used to initialize cookies (e.g., the main page of the search engine)."""
        pass

    @property
    @staticmethod
    @abstractmethod
    def _search_url() -> str:
        """The URL endpoint for search queries."""
        pass

    @configured_validate_call
    def __init__(self, session: aiohttp.ClientSession, params: dict | None = None,
                 headers: dict | None = None, cookies: dict | None = None, proxy: str | None = None,
                 ssl: bool | None = None):
        """
        Initializes the search session.

        Args:
            session (aiohttp.ClientSession): The underlying HTTP session.
            params (dict | None): Default query parameters to include in every request.
            headers (dict | None): Default headers to include in every request.
            cookies (dict | None): Default cookies to include in every request.
            proxy (str | None): Proxy URL to be used for requests in this session.
            ssl (bool | None): Whether to verify SSL certificates.
        """
        self._session = session

        self._params = (params or {}).copy()
        self._headers = (headers or {}).copy()
        self._cookies = (cookies or {}).copy()
        self._proxy = proxy

        self._ssl = ssl is None or ssl
        self._initialized = False

    @property
    def initialized(self) -> bool:
        """Returns True if the session has successfully initialized cookies."""
        return self._initialized

    async def initialize_cookies(self, headers: dict | None = None, cookies: dict | None = None,
                                 proxy: str | None = None):
        """
        Performs a request to the initialization URL to gather necessary cookies.

        This is often required to bypass consent forms or establish a valid session
        before making actual search queries.

        Args:
            headers (dict | None): Additional headers for the initialization request.
            cookies (dict | None): Additional cookies for the initialization request.
            proxy (str | None): Override the default proxy for this request.
        """
        headers = self._gen_headers(headers) | self._create_cookies_header(cookies)
        proxy = proxy or self._proxy

        try:
            async with self._session.get(self._init_url, headers=headers, proxy=proxy,
                                        ssl=self._ssl) as resp:
                cookies = {k: v.value for k, v in resp.cookies.items()}
        except aiohttp.ClientError as e:
            raise ClientError(str(e))
        self._cookies |= cookies
        self._initialized = True

    def _gen_params(self, params: dict) -> dict:
        return self._params | (params or {})

    def _gen_headers(self, headers: dict) -> dict:
        return self._headers | (headers or {})

    def _create_cookies_header(self, cookies: dict) -> dict:
        cookies = self._cookies | (cookies or {})
        return {"Cookie": "; ".join([f"{key}={value}" for key, value in cookies.items()])}

    async def get_serp(self, params: dict | None = None, headers: dict | None = None,
                      cookies: dict | None = None, proxy: str | None = None) -> GS_ResponseModel:
        """
        Performs a search request and returns the raw response content.

        Args:
            params (dict | None): Query parameters (merged with default session params).
            headers (dict | None): HTTP headers (merged with default session headers).
            cookies (dict | None): Cookies (merged with default session cookies).
            proxy (str | None): Proxy URL (overrides default session proxy).

        Returns:
            GS_ResponseModel: A model containing the raw byte content of the response.

        Raises:
            StatusCodeError: If the response status code is not 200.
            ClientError: If a network or protocol error occurs during the request.
        """
        params = self._gen_params(params)
        headers = self._gen_headers(headers) | self._create_cookies_header(cookies)
        proxy = proxy or self._proxy

        serp = GS_ResponseModel()
        try:
            query_string = urlencode(params)
            url = URL(f"{self._search_url}?{query_string}", encoded=True)
            async with self._session.get(url, headers=headers,
                                         proxy=proxy, ssl=self._ssl) as resp:
                if resp.status != 200:
                    debug_info = [prev_resp.request_info
                                  for prev_resp in resp.history] + [resp.request_info]
                    raise StatusCodeError(resp.status, resp.reason, debug_info)
                else:
                    serp.content = await resp.read()
        except aiohttp.ClientError as e:
            raise ClientError(str(e))

        return serp
    
SearchSessionType = TypeVar('SearchSessionType', bound=SearchSessionBase)

@log_class
class SearchSessionsManagerBase(ABC, Generic[SearchSessionType]):
    """
    Abstract base class for managing a pool of search sessions.

    This manager handles the lifecycle of `aiohttp.ClientSession` instances,
    assigns proxies to them, and implements a rotation strategy to distribute
    load across available sessions/proxies.
    """

    @property
    @staticmethod
    @abstractmethod
    def _SearchSession() -> type[SearchSessionType]:
        """The specific SearchSession class to instantiate."""
        pass

    @property
    @staticmethod
    @abstractmethod
    def _headers_default() -> dict:
        """Default headers to apply to all sessions."""
        pass

    @property
    @staticmethod
    @abstractmethod
    def _cookies_default() -> dict:
        """Default cookies to apply to all sessions."""
        pass

    @configured_validate_call
    def __init__(self, sessions: list[aiohttp.ClientSession] | None = None,
                 connector: aiohttp.TCPConnector | None = None, headers: dict | None = None,
                 cookies: dict | None = None, params: dict | None = None,
                 proxies: list[str] | None = None, ssl: bool | None = None,
                 apply_default_headers: bool | None = None,
                 apply_default_cookies: bool | None = None,
                 switch_period: PositiveInt | None = None):
        """
        Initializes the sessions manager.

        Args:
            sessions (list[aiohttp.ClientSession] | None): A list of existing aiohttp sessions.
                If None, new sessions will be created based on the `proxies` list.
            connector (aiohttp.TCPConnector | None): Connector for creating new sessions.
            headers (dict | None): Global headers for all sessions.
            cookies (dict | None): Global cookies for all sessions.
            params (dict | None): Global query parameters.
            proxies (list[str] | None): List of proxy URLs. If `sessions` is None, one session
                is created per proxy. If `sessions` are provided, proxies are distributed
                among them in a round-robin fashion.
            ssl (bool | None): Whether to verify SSL certificates.
            apply_default_headers (bool | None): Whether to apply engine-specific default headers.
            apply_default_cookies (bool | None): Whether to apply engine-specific default cookies.
            switch_period (PositiveInt | None): Number of requests to make with a single session
                before rotating to the next one. Defaults to 3.
        """
        self._sessions = sessions or []
        proxies_provided = proxies is not None
        proxies = proxies or [None]
        if not self._sessions:
            for _ in range(len(proxies)):
                session = aiohttp.ClientSession(connector=connector,
                                                cookie_jar=aiohttp.DummyCookieJar())
                # The proxy is added not at the session level, but at the level of individual requests,
                # in order to unify this process for cases where the user provides their own sessions
                # and when they do not.
                self._sessions.append(session)
            self._should_close_sessions = True
        else:
            self._should_close_sessions = False

        if apply_default_headers is None:
            apply_default_headers = True

        if apply_default_cookies is None:
            apply_default_cookies = False

        headers = (self._headers_default if apply_default_headers else {}) | (headers or {})
        cookies = (self._cookies_default if apply_default_cookies else {}) | (cookies or {})

        self._search_sessions: list[SearchSessionType] = []
        has_session_proxy = False
        for i in range(len(self._sessions)):
            search_session = self._SearchSession(self._sessions[i], headers=headers,
                                                 cookies=cookies, params=params,
                                                 proxy=proxies[i % len(proxies)], ssl=ssl)
            
            self._search_sessions.append(search_session)
            if self._sessions[i]._default_proxy and not has_session_proxy:
                has_session_proxy = True

        if has_session_proxy and proxies_provided:
            warnings.warn("If you pass proxies to the search session manager constructor, you should not add proxies at the aiohttp session level -- the latter will be ignored.")

        self._switch_period = switch_period or 3
        self._calls_count = 0

    async def get_search_session(self, initialize: bool | None = None) -> SearchSessionType:
        """
        Retrieves the next search session according to the rotation strategy.

        Args:
            initialize (bool | None): If True (default), ensures the session has
                initialized cookies before returning it.

        Returns:
            SearchSessionType: An active search session.
        """
        if initialize is None:
            initialize = True

        index = self._calls_count // self._switch_period % len(self._search_sessions)
        self._calls_count += 1
        search_session = self._search_sessions[index]
        if initialize and not search_session.initialized:
            await search_session.initialize_cookies()

        return search_session

    async def close(self):
        """
        Closes all managed `aiohttp.ClientSession` instances if they were created by this manager.
        """
        if self._should_close_sessions:
            for session in self._sessions:
                await session.close()

__all__ = ["SearchSessionBase", "SearchSessionType", "SearchSessionsManagerBase"]
