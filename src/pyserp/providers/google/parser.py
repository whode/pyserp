"""
Parsing logic for Google SERPs.

This module implements the `SERP_Parser_Base` for Google. It contains logic to
identify and parse three different versions of Google's SERP layout (v1, v2, v3),
which are served based on the User-Agent and other factors. It also detects
JavaScript-based challenges (captchas).
"""

import traceback
from urllib.parse import unquote

from bs4 import BeautifulSoup as bs
from bs4 import Tag
from pydantic import ValidationError

from ...core.exceptions.parser import EmptyPageError, PageParsingError
from ...core.models.general import ErrorModel
from ...core.parser import SERP_Parser_Base
from ...core.utils import log_class
from ._internal.exceptions.parser import JsCaptchaError, UnknownLayoutError
from .models.parser import GSERP_Model


@log_class
class GSERP_Parser(SERP_Parser_Base[GSERP_Model]):
    """
    Parser for Google Search Engine Results Pages.

    Supports multiple layout versions and automatic URL decoding.
    """

    def parse_serp_v3(self, bpage: bs) -> GSERP_Model:
        """
        Parses Google SERP layout version 3 (Modern Desktop/Mobile).

        This layout typically uses `div` structures with classes like `MjjYud` and `vt6azd`.

        Args:
            bpage (BeautifulSoup): The parsed HTML object.

        Returns:
            GSERP_Model: The parsed data model for version 3.

        Raises:
            AttributeError, KeyError, IndexError: If the structure doesn't match expectations.
        """
        organic_results = []
        search_div = bpage.find("div", {"id": "search"})
        main_div = search_div.find("div", class_="dURPMd")
        if main_div:
            main_div2 = main_div.contents[-1]
            if main_div2.name == "div" and not main_div2.attrs:
                items = [(div, True)
                         for div in main_div.find_all("div", class_="MjjYud", recursive=False)]
                for div in main_div2.find_all("div", class_="MjjYud", recursive=False):
                    items.append((div, False))
            else:
                items = [(div, False)
                         for div in main_div.find_all("div", class_="MjjYud", recursive=False)]

            for div, is_main in items:
                try:
                    div2 = div.find("div", class_="vt6azd")
                    if div2:
                        result = {}
                        try:
                            a = div2.find("a", class_="zReHs")
                            result["url"] = a.attrs["href"]
                            h3 = a.find("h3")
                            result["title"] = h3.text
                            site_name_item = a.find("span", class_="VuuXrf")
                            result["site_name"] = site_name_item.text
                        except (KeyError, AttributeError) as e:
                            raise type(e)(f"Error while parsing the link <- {e}")
                        second_part_item = div2.find("div", class_="p4wth")
                        try:
                            time_item = second_part_item.find("span", class_="YrbPuc")
                            if time_item:
                                result["time"] = time_item.find("span").text
                        except AttributeError as e:
                            raise type(e)(f"Error while parsing the time <- {e}")
                        try:
                            snippet_item = second_part_item.contents[-1]
                            result["snippet"] = snippet_item.text.strip()
                        except IndexError as e:
                            raise type(e)(f"Error while parsing the snippet <- {e}")
                        try:
                            result["sitelinks"] = []
                            if is_main:
                                sitelinks_item = div2.find("table", class_="jmjoTe")
                                for sitelink_item in sitelinks_item.find_all("div", class_="VttTV"):
                                    a = sitelink_item.find("a")
                                    snippet_item = sitelink_item.find("div", class_="zz3gNc")
                                    snippet = snippet_item.text
                                    sitelink = {
                                        "url": a.attrs["href"],
                                        "title": a.text,
                                        "snippet": snippet,
                                    }
                                    result["sitelinks"].append(sitelink)
                            else:
                                for a in div2.find_all("a", class_="dM1Yyd"):
                                    sitelink = {"url": a.attrs["href"], "title": a.text}
                                    result["sitelinks"].append(sitelink)
                        except (AttributeError, KeyError) as e:
                            raise type(e)(f"Error while parsing sitelinks <- {e}")
                        organic_results.append(result)
                except (KeyError, AttributeError, IndexError) as e:
                    organic_results.append(
                        ErrorModel(error_type=f"(result_parsing_error, {type(e)})", message=str(e),
                                   debug_info=(div, traceback.format_exc())))

        has_more = bool(bpage.find("a", class_="LLNLxf"))
        results = {"organic": organic_results}
        serp = {"results": results, "has_more": has_more}

        parsed_serp = GSERP_Model.model_validate(serp)
        return parsed_serp

    def parse_serp_v2(self, bpage: bs) -> GSERP_Model:
        """
        Parses Google SERP layout version 2 (Legacy Mobile/Desktop).

        This layout is characterized by the `lQigmf` class structure and requires
        manual URL decoding (cleaning Google's redirect wrapper).

        Args:
            bpage (BeautifulSoup): The parsed HTML object.

        Returns:
            GSERP_Model: The parsed data model for version 2.

        Raises:
            AttributeError, KeyError, IndexError: If the structure doesn't match expectations.
        """
        organic_results = []
        main_div = bpage.find("div", id="main")
        for div in main_div.find_all("div", recursive=False)[1:]:
            try:
                result = {}
                part_items = div.find_all("div", class_="lQigmf")
                if part_items:
                    first_part_item = part_items[0]
                    try:
                        a = first_part_item.find("a")
                        result["url"] = self.parse_url(a, "url=")
                        h3 = a.find("h3")
                        result["title"] = h3.text
                        breadcrumbs_item = a.find("div", class_="AKfAgb")
                        result["breadcrumbs"] = breadcrumbs_item.text
                    except (AttributeError, KeyError, IndexError) as e:
                        raise type(e)(f"Error while parsing the link <- {e}")
                    second_part_item = part_items[1].find("div", class_="ilUpNd")
                    info_items = second_part_item.find_all("div", class_="ilUpNd")
                    try:
                        time_item = info_items[0].find("span", class_="UK5aid")
                        if time_item:
                            result["time"] = time_item.text
                    except (IndexError, AttributeError) as e:
                        raise type(e)(f"Error while parsing the time <- {e}")
                    try:
                        snippet_item = info_items[0].find(text=True, recursive=False)
                        result["snippet"] = snippet_item.text.strip()
                    except (IndexError, AttributeError) as e:
                        raise type(e)(f"Error while parsing the snippet <- {e}")
                    try:
                        if len(info_items) > 1:
                            result["sitelinks"] = []
                            for a in info_items[1].find_all("a"):
                                sitelink = {
                                    "url": self.parse_url(a, "url="),
                                    "title": a.text,
                                }
                                result["sitelinks"].append(sitelink)
                    except (AttributeError, KeyError, IndexError) as e:
                        raise type(e)(f"Error while parsing the sitelinks <- {e}")
                    organic_results.append(result)
            except (AttributeError, KeyError, IndexError) as e:
                organic_results.append(
                    ErrorModel(error_type=f"(result_parsing_error, {type(e)})", message=str(e),
                               debug_info=(div, traceback.format_exc())))

        has_more = bool(bpage.find("a", {"class": "nBDE1b", "aria-label": "Next page"}))
        results = {"organic": organic_results}
        serp = {"results": results, "has_more": has_more}

        parsed_serp = GSERP_Model.model_validate(serp)
        return parsed_serp

    def parse_serp_v1(self, bpage: bs) -> GSERP_Model:
        """
        Parses Google SERP layout version 1 (Oldest supported).

        Note:
            Google discontinued support for this layout version on 2025-09-10.
            The code is kept for legacy purposes or handling cached pages.

        Args:
            bpage (BeautifulSoup): The parsed HTML object.

        Returns:
            GSERP_Model: The parsed data model for version 1.

        Raises:
            AttributeError, KeyError, IndexError: If the structure doesn't match expectations.
        """
        organic_results = []
        for div in bpage.find_all("div", class_="ezO2md"):
            try:
                a = div.find("a", class_="fuLhoc")
                if a:
                    result = {}
                    try:
                        result["url"] = self.parse_url(a, "q=")
                        title_item = a.find("span")
                        result["title"] = title_item.text
                        breadcrumbs_item = a.find("span", class_="fYyStc")
                        result["breadcrumbs"] = breadcrumbs_item.text
                    except (AttributeError, KeyError, IndexError) as e:
                        raise type(e)(f"Error while parsing the link <- {e}")
                    second_part_item = div.find("div", class_="Dks9wf")
                    if second_part_item:
                        info_items = second_part_item.find_all("span", class_="qXLe6d")
                        if info_items:
                            try:
                                info_item = info_items[0]
                                time_item = info_item.find("span", class_="YVIcad")
                                if time_item:
                                    result["time"] = time_item.text
                            except (IndexError, AttributeError) as e:
                                raise type(e)(f"Error while parsing the time <- {e}")
                            try:
                                snippet_item = info_item.find("span", class_="fYyStc")
                                result["snippet"] = snippet_item.text.strip()
                            except AttributeError as e:
                                raise type(e)(f"Error while parsing the snippet <- {e}")
                        try:
                            if len(info_items) > 1:
                                result["sitelinks"] = []
                                info_item = info_items[1]
                                sitelinks_items = info_item.find_all("a", class_="M3vVJe")
                                for a in sitelinks_items:
                                    sitelink = {
                                        "url": self.parse_url(a, "q="),
                                        "title": a.text,
                                    }
                                    result["sitelinks"].append(sitelink)
                        except (AttributeError, KeyError, IndexError) as e:
                            raise type(e)(f"Error while parsing the sitelinks <- {e}")
                    organic_results.append(result)
            except (AttributeError, KeyError, IndexError) as e:
                organic_results.append(
                    ErrorModel(error_type=f"(result_parsing_error, {type(e)})", message=str(e),
                               debug_info=(div, traceback.format_exc())))

        has_more_list = bpage.find_all("a", class_="frGj1b")
        has_more = bool(has_more_list) and has_more_list[-1].text.endswith(">")
        results = {"organic": organic_results}
        serp = {"results": results, "has_more": has_more}

        parsed_serp = GSERP_Model.model_validate(serp)
        return parsed_serp

    @staticmethod
    def parse_url(a: Tag, sep: str) -> str:
        """
        Extracts and decodes the real URL from Google's intermediate redirect link.

        Args:
            a (Tag): The anchor tag containing the href.
            sep (str): The query parameter used as a separator (e.g., "url=" or "q=").

        Returns:
            str: The decoded target URL.
        """
        try:
            parsed_url = unquote(a.attrs["href"].split(sep)[1].split("&")[0])
        except (AttributeError, KeyError, IndexError) as e:
            raise type(e)(f"Error while parsing the href <- {e}")

        return parsed_url

    def parse_serp(self, serp_html: bytes) -> GSERP_Model:
        """
        Main entry point for parsing Google SERPs.

        It automatically detects the layout version or raises an error if the layout
        is unknown or if a captcha is detected.

        Logic:
            1. Checks for empty content.
            2. Checks page title for JS Captcha ("Google Search" title usually indicates this).
            3. Inspects body classes and specific headers to dispatch to `parse_serp_v3`, `v2`, or `v1`.

        Args:
            serp_html (bytes): The raw HTML content.

        Returns:
            GSERP_Model: The parsed data model.

        Raises:
            EmptyPageError: If html is empty.
            JsCaptchaError: If a JS challenge is detected.
            UnknownLayoutError: If the layout version cannot be determined.
            PageParsingError: For general parsing failures.
        """
        if not serp_html:
            raise EmptyPageError

        bpage = bs(serp_html.decode(errors="replace"), "lxml")
        title = bpage.title.get_text(strip=True) if bpage.title else ""
        if title == "Google Search":
            raise JsCaptchaError(serp_html)

        body = bpage.body
        if body and body.has_attr("class") and "srp" in body.attrs["class"]:
            parser = self.parse_serp_v3
        elif body and len(body.contents) > 1 and getattr(body.contents[1], "name", None) == "header":
            parser = self.parse_serp_v2
        elif bpage.find("div", class_="n692Zd"):
            parser = self.parse_serp_v1
        else:
            raise UnknownLayoutError(serp_html)

        try:
            parsed_serp = parser(bpage)
        except (AttributeError, IndexError, ValidationError) as e:
            raise PageParsingError(str(e), (serp_html, traceback.format_exc()))

        return parsed_serp


__all__ = ["GSERP_Parser"]
