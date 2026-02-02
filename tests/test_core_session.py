"""
Tests for core session behavior and provider-specific session quirks.
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock, patch
import warnings

import aiohttp

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pyserp.core.exceptions.session import StatusCodeError
from pyserp.core.session import SearchSessionBase, SearchSessionsManagerBase
from pyserp.providers.bing.session import BingSearchSession
from pyserp.providers.google.session import GoogleSearchSession


class DummyResponse:
    def __init__(self, status=200, reason="OK", body=b"", cookies=None, history=None):
        self.status = status
        self.reason = reason
        self._body = body
        self.cookies = cookies or {}
        self.history = history or []
        self.request_info = "request-info"

    async def read(self):
        return self._body


class DummyContext:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummySearchSession(SearchSessionBase):
    """Lightweight session stub for exercising base logic."""
    _init_url = "https://example.com"
    _search_url = "https://example.com/search"


class SearchSessionBaseTests(IsolatedAsyncioTestCase):
    """Behavioral tests for SearchSessionBase and session managers."""
    async def test_initialize_cookies_sets_initialized(self):
        session = aiohttp.ClientSession()
        try:
            cookies = {"NID": SimpleNamespace(value="cookie-value")}
            response = DummyResponse(cookies=cookies)
            ctx = DummyContext(response)
            with patch.object(session, "get", new=Mock(return_value=ctx)):
                search_session = DummySearchSession(session)
                await search_session.initialize_cookies()
                self.assertTrue(search_session.initialized)
                self.assertIn("NID", search_session._cookies)
        finally:
            await session.close()

    async def test_get_serp_success_returns_content(self):
        session = aiohttp.ClientSession()
        try:
            response = DummyResponse(body=b"ok")
            ctx = DummyContext(response)
            with patch.object(session, "get", new=Mock(return_value=ctx)):
                search_session = DummySearchSession(session)
                serp = await search_session.get_serp()
                self.assertEqual(serp.content, b"ok")
        finally:
            await session.close()

    async def test_get_serp_raises_status_code_error(self):
        session = aiohttp.ClientSession()
        try:
            history = [SimpleNamespace(request_info="prev-request")]
            response = DummyResponse(status=429, reason="Too Many Requests", history=history)
            ctx = DummyContext(response)
            with patch.object(session, "get", new=Mock(return_value=ctx)):
                search_session = DummySearchSession(session)
                with self.assertRaises(StatusCodeError) as ctx_err:
                    await search_session.get_serp()
                self.assertEqual(
                    ctx_err.exception.debug_info,
                    ["prev-request", "request-info"],
                )
        finally:
            await session.close()

    async def test_google_search_session_strips_num_param(self):
        session = aiohttp.ClientSession()
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                search_session = GoogleSearchSession(session, params={"num": "10"})
                self.assertNotIn("num", search_session._params)
                self.assertTrue(any("num" in str(w.message) for w in caught))
        finally:
            await session.close()

    async def test_bing_search_session_strips_count_param(self):
        session = aiohttp.ClientSession()
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                search_session = BingSearchSession(session, params={"count": "10"})
                self.assertNotIn("count", search_session._params)
                self.assertTrue(any("count" in str(w.message) for w in caught))
        finally:
            await session.close()

    async def test_sessions_manager_rotates_and_initializes(self):
        class DummyManagedSession:
            def __init__(self, session, params=None, headers=None, cookies=None, proxy=None, ssl=None):
                self.session = session
                self.proxy = proxy
                self._initialized = False

            @property
            def initialized(self):
                return self._initialized

            async def initialize_cookies(self, *args, **kwargs):
                self._initialized = True

        class DummySessionsManager(SearchSessionsManagerBase[DummyManagedSession]):
            _SearchSession = DummyManagedSession
            _headers_default = {}
            _cookies_default = {}

        session_one = aiohttp.ClientSession()
        session_two = aiohttp.ClientSession()
        try:
            manager = DummySessionsManager(
                sessions=[session_one, session_two],
                proxies=["proxy-1", "proxy-2"],
                switch_period=1,
            )
            first = await manager.get_search_session()
            second = await manager.get_search_session()
            third = await manager.get_search_session()

            self.assertTrue(first.initialized)
            self.assertTrue(second.initialized)
            self.assertIs(first, manager._search_sessions[0])
            self.assertIs(second, manager._search_sessions[1])
            self.assertIs(third, manager._search_sessions[0])
            self.assertEqual(first.proxy, "proxy-1")
            self.assertEqual(second.proxy, "proxy-2")
        finally:
            await session_one.close()
            await session_two.close()
