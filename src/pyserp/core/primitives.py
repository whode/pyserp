"""
Primitive data types and type annotations used throughout the library.
"""

from typing import Annotated

from pydantic import Field

PositiveInt = Annotated[int, Field(gt=0)]
"""An integer strictly greater than zero."""

__all__ = ["PositiveInt"]


