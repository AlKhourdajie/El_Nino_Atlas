"""Smoke tests: the app imports and the layout builds."""

import plotly.io as pio


def test_app_imports_and_layout_builds():
    import app as app_module

    assert app_module.server is not None
    layout = app_module.app.layout
    assert layout is not None
    assert "No layers are active yet" in str(layout)


def test_plotly_templates_registered():
    from src import theme

    theme.register_templates()
    assert theme.TEMPLATE_DARK in pio.templates
    assert theme.TEMPLATE_LIGHT in pio.templates


def test_not_assessed_never_shares_no_alert_colour():
    from src import theme
    from src.layout import legend

    assert theme.STATE_COLOURS["not_assessed"] != theme.STATE_COLOURS["no_alert"]
    assert theme.STATE_COLOURS["not_assessed"] != theme.STATE_COLOURS["alert"]
    rendered = str(legend())
    for state in ("alert", "no_alert", "not_assessed"):
        assert f"legend-{state}" in rendered


def test_update_command_reports_no_fetchers(capsys):
    import run

    assert run.main(["update"]) == 0
    assert capsys.readouterr().out.strip() == "no fetchers registered"
