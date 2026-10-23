"""Shared CLI helpers for SpectrumSentry AI scripts.

Scripts print Unicode box-drawing/symbol characters that Windows' default cp1252
console cannot encode, crashing them with UnicodeEncodeError. Importing
``force_utf8_stdio()`` at script start reconfigures stdout/stderr to UTF-8 with
replacement so output always succeeds.
"""

import sys


def force_utf8_stdio() -> None:
    """Reconfigure stdout/stderr to UTF-8 (no-op on streams that don't support it)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
