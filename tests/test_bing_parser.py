"""
Tests for Bing SERP parsing.
"""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pyserp.core.exceptions.parser import EmptyPageError
from pyserp.providers.bing.parser import BSERP_Parser


class BingParserTests(TestCase):
    """Parser unit tests for Bing-specific logic."""
    def test_parse_serp_empty_raises(self):
        executor = ThreadPoolExecutor(max_workers=1)
        self.addCleanup(executor.shutdown, wait=True)
        parser = BSERP_Parser(executor)

        with self.assertRaises(EmptyPageError):
            parser.parse_serp(b"")

    def test_parse_serp_minimal_page(self):
        executor = ThreadPoolExecutor(max_workers=1)
        self.addCleanup(executor.shutdown, wait=True)
        parser = BSERP_Parser(executor)
        html = b"""
        <html>
            <body>
                <ol id="b_results">
                    <li class="b_algo">
                        <div class="tptt">Example Site</div>
                        <h2><a href="https://example.com">Example Title</a></h2>
                        <p class="b_lineclamp2">Snippet text<span class="news_dt">1 day ago</span></p>
                    </li>
                    <li class="b_pag"></li>
                </ol>
            </body>
        </html>
        """

        parsed = parser.parse_serp(html)
        self.assertTrue(parsed.has_more)
        self.assertEqual(len(parsed.results.organic), 1)
        result = parsed.results.organic[0]
        self.assertEqual(result.url, "https://example.com")
        self.assertEqual(result.title, "Example Title")
        self.assertEqual(result.site_name, "Example Site")
        self.assertEqual(result.time, "1 day ago")
        self.assertEqual(result.snippet.strip(), "Snippet text")
