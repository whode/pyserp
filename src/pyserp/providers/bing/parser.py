"""
Parsing logic for Bing SERPs.

This module implements the `SERP_Parser_Base` for Bing, extracting organic results
from the specific HTML structure returned by Bing's search engine.
"""

import traceback

from bs4 import BeautifulSoup as bs
from pydantic import ValidationError

from ...core.exceptions.parser import EmptyPageError, PageParsingError
from ...core.models.general import ErrorModel
from ...core.parser import SERP_Parser_Base
from ...core.utils import log_class
from .models.parser import BSERP_Model


@log_class
class BSERP_Parser(SERP_Parser_Base[BSERP_Model]):
    """
    Parser for Bing Search Engine Results Pages.
    """

    def parse_default_serp(self, bpage: bs):
        """
        Parses the standard layout of a Bing SERP.

        Args:
            bpage (BeautifulSoup): The parsed HTML object.

        Returns:
            BSERP_Model: The structured data extracted from the page.

        Raises:
            AttributeError: If critical structural elements (like the results container) are missing.
            ValidationError: If the constructed data does not match the Pydantic model.
        """
        organic_results = []
        b_results = bpage.find("ol", id="b_results")
        for li in b_results.find_all("li", class_="b_algo"):
            try:
                result = {}
                try:
                    site_name_item = li.find("div", class_="tptt")
                    result["site_name"] = site_name_item.text
                except AttributeError as e:
                    raise type(e)(f"Error while parsing the site name <- {e}")
                try:
                    h2 = li.find("h2")
                    link_item = h2.find("a")
                    result["url"] = link_item.attrs["href"]
                    result["title"] = link_item.text
                except (AttributeError, KeyError) as e:
                    raise type(e)(f"Error while parsing url and title <- {e}")
                try:
                    info_item = li.find("p", class_="b_lineclamp2")
                    snippet_items = info_item.find_all(text=True, recursive=False)
                    result["snippet"] = " ".join([snippet_item.text for snippet_item in snippet_items])
                    time_item = info_item.find("span", class_="news_dt")
                    if time_item:
                        result["time"] = time_item.text
                except AttributeError as e:
                    raise type(e)(f"Error while parsing the snippet <- {e}")

                organic_results.append(result)
            except (AttributeError, KeyError) as e:
                organic_results.append(
                    ErrorModel(error_type=f"(result_parsing_error, {type(e)})", message=str(e),
                               debug_info=(li, traceback.format_exc())))

        has_more_item = b_results.find("li", class_="b_pag")
        results = {"organic": organic_results}
        serp = {"results": results, "has_more": bool(has_more_item)}

        parsed_serp = BSERP_Model.model_validate(serp)

        return parsed_serp

    def parse_serp(self, serp_html: bytes) -> BSERP_Model:
        """
        Parses the raw HTML bytes of a Bing SERP.

        Args:
            serp_html (bytes): The raw HTML content.

        Returns:
            BSERP_Model: The parsed data model.

        Raises:
            EmptyPageError: If the input HTML is empty.
            PageParsingError: If the parsing fails due to layout changes or validation errors.
        """
        if not serp_html:
            raise EmptyPageError

        bpage = bs(serp_html.decode(errors="replace"), "lxml")
        try:
            parsed_serp = self.parse_default_serp(bpage)
        except (AttributeError, ValidationError) as e:
            raise PageParsingError(str(e), (serp_html, traceback.format_exc()))

        return parsed_serp


__all__ = ["BSERP_Parser"]
