"""
Google search session components.

This module configures the HTTP sessions for Google, including critical
default cookies to bypass consent screens and headers to influence the
returned layout version.
"""

import warnings

import aiohttp

from ...core.primitives import PositiveInt
from ...core.session import SearchSessionBase, SearchSessionsManagerBase
from ...core.utils import log_class


@log_class
class GoogleSearchSession(SearchSessionBase):
    """
    Google-specific search session.

    Handles connection details for Google Search, including the correct endpoints
    and parameter filtering.
    """

    _init_url = "https://www.google.com"
    _search_url = "https://www.google.com/search"

    def __init__(self, session: aiohttp.ClientSession, params: dict | None = None,
                 headers: dict | None = None, cookies: dict | None = None, proxy: str | None = None,
                 ssl: bool | None = None):
        """
        Initializes the Google session.

        Warns if 'num' is passed in params, as it should be controlled by the Searcher.
        """

        super().__init__(session, params, headers, cookies, proxy, ssl)

        if "num" in self._params:
            warnings.warn(
                'The "num" parameter should not be passed in separate sessions, it will be ignored. Instead, pass it in the searcher constructor.'
            )
            del self._params["num"]

@log_class
class GoogleSearchSessionsManager(SearchSessionsManagerBase[GoogleSearchSession]):
    """
    Manager for Google search sessions.

    Applies specific defaults:
    - User-Agent: Targeted to trigger GSERPv2 layout (often more stable/less captcha-prone).
    - Cookies: Pre-set 'CONSENT' and 'SOCS' cookies to bypass the GDPR consent page.
    """
    _headers_default = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.2; WOW64; Trident/7.0; rv:11.0) like Gecko"
    }

    _cookies_default = {
        "CONSENT": "PENDING+987",
        "SOCS": "CAESHAgBEhJnd3NfMjAyMzA4MTAtMF9SQzIaAmRlIAEaBgiAo_CmBg",
    }

    _SearchSession = GoogleSearchSession

    def __init__(self, sessions: list[aiohttp.ClientSession] | None = None,
                 connector: aiohttp.TCPConnector | None = None,
                 headers: dict[str, str] | None = None, cookies: dict[str, str] | None = None,
                 params: dict[str, str] | None = None, proxies: list[str] | None = None,
                 ssl: bool | None = None, apply_default_headers: bool | None = None,
                 apply_default_cookies: bool | None = None,
                 switch_period: PositiveInt | None = None):
        """
        Initializes the manager, stripping 'num' from global params if present.
        """
        
        if params and "num" in params:
            params = params.copy()
            warnings.warn(
                'The "num" parameter should not be passed in separate search sessions, it will be ignored. Instead, pass it in the searcher constructor.'
            )
            del params["num"]

        super().__init__(sessions, connector, headers, cookies, params, proxies, ssl,
                         apply_default_headers, apply_default_cookies, switch_period)

    async def get_search_session(self, initialize: bool = True) -> GoogleSearchSession:
        return await super().get_search_session(initialize)


__all__ = ["GoogleSearchSession", "GoogleSearchSessionsManager"]
