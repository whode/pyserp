"""
Internal exceptions for the Google parser.

These exceptions are specific to the layout detection and anti-bot mechanisms
encountered on Google SERPs.
"""

from typing import Any

from .....core.exceptions.base import BaseError


class JsCaptchaError(BaseError):
    """
    Raised when Google returns a page requiring JavaScript execution to proceed.

    This typically happens when Google suspects bot activity and serves a
    JS-based challenge (to generate the SG_SS cookie) instead of the actual SERP.
    """

    def __init__(self, debug_info: Any = None):
        message = "Google is testing browser integrity (JS is needed to generate SG_SS cookie)."
        super().__init__(message, debug_info)


class UnknownLayoutError(BaseError):
    """
    Raised when the parser cannot determine the version of the SERP layout.

    This error indicates that the HTML structure does not match any of the
    supported versions (v1, v2, v3).
    """

    def __init__(self, debug_info: Any = None):
        super().__init__("The layout of the SERP doesn't seem to be of any known version.", debug_info)
