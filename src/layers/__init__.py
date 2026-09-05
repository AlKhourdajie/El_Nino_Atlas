"""Map and chart layers (stubs only).

Each layer will expose a ``build(data) -> dash component`` function and
classify every unit into one of the three states defined in
``src.theme.STATE_COLOURS``. No layer is implemented yet.
"""

REGISTERED_LAYERS: dict[str, object] = {}
