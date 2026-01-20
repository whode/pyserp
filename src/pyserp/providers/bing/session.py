"""
Bing search session components.

This module defines the specialized session classes required to interact with Bing,
handling engine-specific connection details like base URLs, default headers,
and parameter sanitization.
"""

import warnings

import aiohttp

from ...core.primitives import PositiveInt
from ...core.session import SearchSessionBase, SearchSessionsManagerBase
from ...core.utils import log_class


@log_class
class BingSearchSession(SearchSessionBase):
    """
    Bing-specific search session.

    Handles the initialization of cookies via the main page and executes
    search requests against the Bing endpoint.
    """

    _init_url = "https://www.bing.com"
    _search_url = "https://www.bing.com/search"

    def __init__(self, session: aiohttp.ClientSession, params: dict | None = None,
                 headers: dict | None = None, cookies: dict | None = None, proxy: str | None = None,
                 ssl: bool | None = None):
        """
        Initializes the Bing session.

        Warns if 'count' is passed in params, as it should be controlled by the Searcher.
        """

        super().__init__(session, params, headers, cookies, proxy, ssl)

        if "count" in self._params:
            warnings.warn(
                'The "count" parameter should not be passed in separate sessions, it will be ignored. Instead, pass it in the searcher constructor.'
            )
            del self._params["count"]

@log_class
class BingSearchSessionsManager(SearchSessionsManagerBase[BingSearchSession]):
    """
    Manager for Bing search sessions.

    Provides default headers (User-Agent) that are known to work well with Bing.
    """

    _headers_default = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0"
    }
    _cookies_default = {}

    _SearchSession = BingSearchSession

    def __init__(self, sessions: list[aiohttp.ClientSession] | None = None,
                 connector: aiohttp.TCPConnector | None = None,
                 headers: dict[str, str] | None = None, cookies: dict[str, str] | None = None,
                 params: dict[str, str] | None = None, proxies: list[str] | None = None,
                 ssl: bool | None = None, apply_default_headers: bool | None = None,
                 apply_default_cookies: bool | None = None,
                 switch_period: PositiveInt | None = None):
        """
        Initializes the manager, stripping 'count' from global params if present.
        """

        if params and "count" in params:
            params = params.copy()
            warnings.warn(
                'The "count" parameter should not be passed in separate search sessions, it will be ignored. Instead, pass it in the searcher constructor.'
            )
            del params["count"]

        super().__init__(sessions, connector, headers, cookies, params, proxies, ssl,
                         apply_default_headers, apply_default_cookies, switch_period)

    async def get_search_session(self, initialize: bool | None = None) -> BingSearchSession:
        return await super().get_search_session(initialize)

__all__ = ["BingSearchSession", "BingSearchSessionsManager"]
