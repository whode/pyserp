"""
Tests for core search orchestration logic.
"""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pyserp.core.exceptions.base import BaseError
from pyserp.core.models.general import ErrorModel
from pyserp.core.models.session import GS_ResponseModel
from pyserp.core.parser import SERP_Parser_Base
from pyserp.core.searcher import SearcherBase
from pyserp.core.session import SearchSessionsManagerBase


class DummySearchSession:
    """Minimal session stub with a preloaded response queue."""
    def __init__(self, responses):
        self._responses = list(responses)

    async def get_serp(self, *args, **kwargs):
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        if isinstance(item, GS_ResponseModel):
            return item
        return GS_ResponseModel(content=item)


class DummySessionsManager(SearchSessionsManagerBase[DummySearchSession]):
    """Sessions manager stub that returns a single session instance."""
    _SearchSession = DummySearchSession
    _headers_default = {}
    _cookies_default = {}

    def __init__(self, session):
        self._session = session

    async def get_search_session(self, initialize: bool | None = None):
        return self._session

    async def close(self):
        return None


class DummyParser(SERP_Parser_Base):
    """Parser stub that returns a fixed result."""
    def __init__(self, result):
        self._result = result

    def parse_serp(self, serp_html: bytes):
        return self._result

    async def parse(self, serp_html: bytes):
        return self._result


class DummySearcher(SearcherBase[DummySearchSession, object]):
    """Searcher stub that mirrors Google-style pagination params."""
    @staticmethod
    def _serp_organic_results_limit():
        return 100

    def _get_results_per_page(self, params: dict) -> int | None:
        return (params or {}).get("num")

    def _create_params_addition(self, query: str, start: int) -> dict:
        return {"q": query, "start": start}


class SearcherBaseTests(IsolatedAsyncioTestCase):
    """Behavioral tests for SearcherBase."""
    async def test_search_one_retries_then_success(self):
        session = DummySearchSession(
            [
                BaseError("boom", debug_info={"attempt": 1}),
                GS_ResponseModel(content=b"<html/>"),
            ]
        )
        parser = DummyParser(result="parsed")
        manager = DummySessionsManager(session)
        searcher = DummySearcher(manager, parser, asyncio.Semaphore(1))

        result = await searcher.search_one("query", tries=2)
        self.assertEqual(result, "parsed")

    async def test_search_one_returns_error_model_after_retries(self):
        session = DummySearchSession(
            [
                BaseError("fail-1", debug_info="first"),
                BaseError("fail-2", debug_info="second"),
            ]
        )
        parser = DummyParser(result="parsed")
        manager = DummySessionsManager(session)
        searcher = DummySearcher(manager, parser, asyncio.Semaphore(1))

        result = await searcher.search_one("query", tries=2)
        self.assertIsInstance(result, ErrorModel)
        self.assertEqual(result.error_type, "BaseError")
        self.assertEqual(result.message, "fail-2")
        self.assertEqual(result.debug_info["original_debug_info"], "second")

    async def test_search_many_gen_respects_ordering(self):
        class OrderingSearcher(DummySearcher):
            async def search_one(self, query: str, start: int = 0, *args, **kwargs):
                delay = 0.02 if start == 0 else 0.001
                await asyncio.sleep(delay)
                return start

        manager = DummySessionsManager(DummySearchSession([]))
        parser = DummyParser(result=None)
        searcher = OrderingSearcher(manager, parser, asyncio.Semaphore(1))

        in_order = [
            page
            async for page in searcher.search_many_gen("query", starts=[0, 10], in_order=True)
        ]
        out_of_order = [
            page
            async for page in searcher.search_many_gen("query", starts=[0, 10], in_order=False)
        ]

        self.assertEqual(in_order, [0, 10])
        self.assertEqual(out_of_order, [10, 0])

    async def test_search_top_gen_limit_and_error_handling(self):
        def make_page(count, has_more=True):
            return SimpleNamespace(
                results=SimpleNamespace(organic=[object()] * count),
                has_more=has_more,
            )

        class TopGenSearcher(DummySearcher):
            def __init__(self, *args, pages):
                super().__init__(*args)
                self._pages = pages

            async def _search_top_gen(self, *args, **kwargs):
                for page in self._pages:
                    yield page

        parser = DummyParser(result=None)
        manager = DummySessionsManager(DummySearchSession([]))

        pages = [make_page(3, True), make_page(3, True)]
        searcher = TopGenSearcher(manager, parser, asyncio.Semaphore(1), pages=pages)
        results = [page async for page in searcher.search_top_gen("query", limit=5)]
        self.assertEqual(len(results), 2)

        error_pages = [ErrorModel(error_type="X", message="fail", debug_info=None), make_page(2)]
        searcher = TopGenSearcher(manager, parser, asyncio.Semaphore(1), pages=error_pages)
        results = [page async for page in searcher.search_top_gen("query", limit=5)]
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], ErrorModel)
