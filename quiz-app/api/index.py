"""Vercel entrypoint.

Vercel's Python runtime looks for an ASGI ``app`` in this module and routes
requests to it (see vercel.json). Locally you run ``uvicorn app.main:app``
instead and this file is unused.
"""

import sys
from pathlib import Path

# The function executes with the project root bundled alongside this file;
# make sure `app` is importable regardless of the working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app as app  # noqa: E402  (import after sys.path setup)
