"""FIR (Flight Information Region) data for Aviation Weather."""

from __future__ import annotations

from .models import Fir
from .registry import FIRS, get_fir

__all__ = [
    "Fir",
    "FIRS",
    "get_fir",
]
