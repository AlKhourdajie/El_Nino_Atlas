"""Runtime configuration for the El Niño Atlas dashboard.

Values are read from the environment with safe defaults so that the same
module serves local development (``python run.py dashboard``) and the
gunicorn entry point (``gunicorn app:server``).
"""

import os

HOST: str = os.environ.get("ATLAS_HOST", "127.0.0.1")
PORT: int = int(os.environ.get("ATLAS_PORT", os.environ.get("PORT", "8050")))
DEBUG: bool = os.environ.get("ATLAS_DEBUG", "false").lower() in {"1", "true", "yes"}
