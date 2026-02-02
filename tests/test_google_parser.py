"""
Tests for Google SERP parsing utilities and layout detection.
"""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import TestCase

from bs4 import BeautifulSoup as bs

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pyserp.core.exceptions.parser import EmptyPageError
from pyserp.providers.google._internal.exceptions.parser import JsCaptchaError, UnknownLayoutError
from pyserp.providers.google.parser import GSERP_Parser


class GoogleParserTests(TestCase):
    """Parser unit tests for Google-specific logic."""
    def test_parse_url_unquotes_target(self):
        soup = bs(
            '<a href="/url?url=https%3A%2F%2Fexample.com%2Ftest&sa=U">link</a>',
            "lxml",
        )
        url = GSERP_Parser.parse_url(soup.find("a"), "url=")
        self.assertEqual(url, "https://example.com/test")

    def test_parse_serp_empty_raises(self):
        executor = ThreadPoolExecutor(max_workers=1)
        self.addCleanup(executor.shutdown, wait=True)
        parser = GSERP_Parser(executor)

        with self.assertRaises(EmptyPageError):
            parser.parse_serp(b"")

    def test_parse_serp_js_captcha_raises(self):
        executor = ThreadPoolExecutor(max_workers=1)
        self.addCleanup(executor.shutdown, wait=True)
        parser = GSERP_Parser(executor)
        html = b"<html><head><title>Google Search</title></head><body></body></html>"

        with self.assertRaises(JsCaptchaError):
            parser.parse_serp(html)

    def test_parse_serp_unknown_layout_raises(self):
        executor = ThreadPoolExecutor(max_workers=1)
        self.addCleanup(executor.shutdown, wait=True)
        parser = GSERP_Parser(executor)
        html = b"<html><head><title>Other</title></head><body>\n<div></div></body></html>"

        with self.assertRaises(UnknownLayoutError):
            parser.parse_serp(html)
