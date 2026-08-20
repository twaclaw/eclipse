import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import numpy as np

    from earthsim import astronomy as ast
    from earthsim.labels import phase_name, phase_name_es
    from earthsim.widgets import MoonPhasesWidget

    return MoonPhasesWidget, ast, mo, np, phase_name, phase_name_es


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 1. The phases of the Moon

    Half the Moon is lit. It always has been, and it always will be, in exactly
    the same way half of Earth is always in daylight. What changes over a month
    is **how much of that lit half happens to be pointed at us**.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    # Play, speed and brightness live inside the widget, so they stay reachable
    # when the panel is maximised. Setting them here too would fight it.
    moon_node = mo.ui.slider(
        0, 360, 5, value=0, label="node longitude (deg)", show_value=True
    )
    moon_south = mo.ui.switch(False, label="southern view")
    moon_shine = mo.ui.switch(True, label="earthshine")

    mo.vstack(
        [
            mo.hstack(
                [moon_node, moon_shine, moon_south],
                justify="start",
                gap=1.5,
                wrap=True,
            ),
        ],
        gap=0.4,
    )
    return moon_node, moon_shine, moon_south


@app.cell(hide_code=True)
def _(MoonPhasesWidget, mo):
    # Built in a cell of its own: marimo closes a widget's comm when its
    # defining cell re-runs, so nothing here may depend on the controls.
    moon = MoonPhasesWidget()
    moon_ui = mo.ui.anywidget(moon)
    moon_ui
    return (moon_ui,)


@app.cell(hide_code=True)
def _(moon_node, moon_shine, moon_south, moon_ui):
    moon_ui.node_longitude_deg = float(moon_node.value)
    moon_ui.show_earthshine = bool(moon_shine.value)
    moon_ui.southern_view = bool(moon_south.value)
    return


@app.cell(hide_code=True)
def _(ast, mo, moon_node, moon_ui, np, phase_name, phase_name_es):
    # Static analysis of the age on the slider, computed in Python.
    _age = float(moon_ui.age_days)
    _elongation = ast.moon_elongation(_age)
    _lam = ast.sun_ecliptic_longitude(172.0 + _age)
    _beta = ast.moon_ecliptic_latitude(_lam, _elongation, np.radians(moon_node.value))
    _beta_deg = float(np.degrees(_beta))
    _lit = float(ast.illuminated_fraction(_elongation))

    _eclipse = ast.lunar_eclipse_possible(_beta, _elongation)
    if abs(np.degrees(_elongation) % 360.0 - 180.0) > 15.0:
        _verdict = "not near full, so no eclipse is possible"
    elif _eclipse:
        _verdict = "**close enough to a node — this full moon can be eclipsed**"
    else:
        _verdict = (
            f"full, but {abs(_beta_deg):.1f}° "
            f"{'above' if _beta_deg > 0 else 'below'} the ecliptic, so the Moon "
            f"misses Earth's shadow"
        )

    mo.md(
        f"""
    | | |
    |---|---|
    | Age | {_age:.1f} days of {ast.SYNODIC_MONTH:.2f} |
    | Phase | {phase_name(_elongation)} · **{phase_name_es(_elongation).upper()}** |
    | Lit as seen from Earth | {_lit * 100:.0f}% |
    | Elongation from the sun | {np.degrees(_elongation) % 360:.0f}° |
    | Height above the ecliptic | {_beta_deg:+.2f}° |
    | Eclipse | {_verdict} |
    """
    )
    return


if __name__ == "__main__":
    app.run()
