import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import numpy as np

    from earthsim import astronomy as ast
    from earthsim.labels import phase_name
    from earthsim.widgets import MoonPhasesWidget

    return MoonPhasesWidget, ast, mo, np, phase_name


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 1. The phases of the Moon

    Half the Moon is lit. It always has been, and it always will be, in exactly
    the same way half of Earth is always in daylight. What changes over a month
    is **how much of that lit half happens to be pointed at us**.

    Watch the two panels together. On the left, from above the north pole, the
    Moon's bright side stubbornly faces the sun no matter where it is on its
    orbit. On the right is the same Moon seen from Earth, and the phase is
    simply the slice of the bright side that our line of sight catches.

    /// warning | Not Earth's shadow
    It is tempting to explain phases by saying Earth gets between the sun and
    the Moon. That does happen — it is called a **lunar eclipse**, it lasts a
    couple of hours, and it is rare. Phases happen every month, take four weeks,
    and would carry on exactly the same if Earth cast no shadow at all. The
    `node longitude` control below shows why eclipses are the exception:
    the Moon's orbit is tilted about 5°, so at most full moons it sails above
    or below the shadow entirely.
    ///
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    # Play, speed and brightness live inside the widget, so they stay reachable
    # when the panel is maximised. Setting them here too would fight it.
    moon_age = mo.ui.slider(
        0, 29.5, 0.1, value=0.0, label="set age (days)", show_value=True
    )
    moon_node = mo.ui.slider(
        0, 360, 5, value=0, label="node longitude (deg)", show_value=True
    )
    moon_south = mo.ui.switch(False, label="southern view")
    moon_shine = mo.ui.switch(True, label="earthshine")

    mo.vstack(
        [
            mo.hstack(
                [moon_age, moon_node, moon_shine, moon_south],
                justify="start",
                gap=1.5,
                wrap=True,
            ),
        ],
        gap=0.4,
    )
    return moon_age, moon_node, moon_shine, moon_south


@app.cell(hide_code=True)
def _(MoonPhasesWidget, mo):
    # Built in a cell of its own: marimo closes a widget's comm when its
    # defining cell re-runs, so nothing here may depend on the controls.
    moon = MoonPhasesWidget()
    moon_ui = mo.ui.anywidget(moon)
    moon_ui
    return (moon_ui,)


@app.cell(hide_code=True)
def _(moon_age, moon_node, moon_shine, moon_south, moon_ui):
    moon_ui.age_days = float(moon_age.value)
    moon_ui.node_longitude_deg = float(moon_node.value)
    moon_ui.show_earthshine = bool(moon_shine.value)
    moon_ui.southern_view = bool(moon_south.value)
    return


@app.cell(hide_code=True)
def _(ast, mo, moon_age, moon_node, np, phase_name):
    # Static analysis of the age on the slider, computed in Python.
    _elongation = ast.moon_elongation(moon_age.value)
    _lam = ast.sun_ecliptic_longitude(172.0 + moon_age.value)
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
    | Age | {moon_age.value:.1f} days of {ast.SYNODIC_MONTH:.2f} |
    | Phase | {phase_name(_elongation)} |
    | Lit as seen from Earth | {_lit * 100:.0f}% |
    | Elongation from the sun | {np.degrees(_elongation) % 360:.0f}° |
    | Height above the ecliptic | {_beta_deg:+.2f}° |
    | Eclipse | {_verdict} |
    """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    /// tip | Try this
    Pause with the control strip and drag **age** slowly from 0 to 29.5. The Moon on
    the right never stops being half lit; only our viewing angle changes.

    Then leave the age at **14.8 days** (full moon) and sweep **node
    longitude**. The phase on the right does not budge, because the tilt is
    irrelevant to it — but the height above the ecliptic swings through five
    degrees, and only for a narrow band of node angles does an eclipse become
    possible at all.
    ///

    ### Notes on the model

    * The left panel is **not to scale**. The Moon is about thirty Earth
      diameters away, and the sun is four hundred times further than that. Drawn
      honestly, the orbit would be a speck and the sun would be off in the next
      room. What *is* honest is the geometry: sunlight arrives as parallel rays,
      and both bodies keep their lit halves turned towards it.
    * The Moon on the right keeps one face towards Earth, so the camera never
      moves — the lighting swings around it instead. That is why you always see
      the same craters.
    * The cycle runs on the **synodic month** of 29.53 days, which is longer
      than the 27.32-day orbit because the sun keeps moving too. In one lunar
      orbit the Earth has travelled far enough that the Moon needs another two
      days to catch the sun up.
    * The **moon** slider is exposure, not physics: it brightens the sunlit
      face so a thin crescent stays visible without washing out a full moon.
    * Earthshine is the faint glow on the dark side: sunlight reflected off
      Earth. It is brightest at a thin crescent, because that is when Earth as
      seen from the Moon is nearly full.
    """)
    return


if __name__ == "__main__":
    app.run()
