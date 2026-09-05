"""Dash application factory for the El Niño Atlas.

The app is built at import time so that ``gunicorn app:server`` works
unchanged. ``run.py`` imports the same object for local serving.
"""

import dash
import dash_bootstrap_components as dbc

from src import theme
from src.layout import build_layout

theme.register_templates()

app = dash.Dash(
    __name__,
    title="El Niño Atlas",
    external_stylesheets=[dbc.themes.FLATLY],
)
app.layout = build_layout()

server = app.server
