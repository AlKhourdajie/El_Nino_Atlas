"""Panel modules for the El Niño Atlas page.

Each module here is one panel. A data panel exposes ``build_figure(...)``
and ``explainer() -> Explainer`` (``src/layout/explainer.py``); a panel
that shows a static asset exposes a builder for its page section
instead. Every panel names its source, its registry id in
``src/sources.yaml`` and its licence in its module docstring, and none
of them fetches: frames arrive through ``src.data_access``, curated
entries through ``src.activations``. ``app.build_page`` assembles the
panels along the forecast, action, impact spine.

``enso_index``        the RONI and ONI series with event seasons shaded
``activations_map``   the anticipatory-action activation map and table
``commodities``       World Bank Pink Sheet prices with El Niño seasons
``teleconnections``   the draft teleconnection schematic
"""
