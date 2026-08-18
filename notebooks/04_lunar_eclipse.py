import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo

    from earthsim.track import eclipse_summary
    from earthsim.widgets import LunarEclipseWidget

    return LunarEclipseWidget, eclipse_summary, mo


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 4. Lunar eclipses

    Earth's shadow reaches a million and a half kilometres into space, and once
    in a while the Moon walks through it.

    Every month the Moon passes opposite the sun, so if the three bodies shared
    a plane there would be a lunar eclipse every four weeks. There are usually
    two a year. The reason is the 5.1° tilt of the Moon's orbit: it crosses the
    plane of Earth's orbit at just two points — the **nodes** — and a full moon
    only lands in the shadow if it happens near one. Anywhere else it sails a
    degree or so over or under, and a degree puts it a whole Earth radius clear.

    Drag the **node** control and watch that happen.

    Three views of the same moment: the Moon as you would see it, the shadow
    seen down its own axis, and the whole system edge-on — that last one drawn
    entirely to scale, which diagrams of this almost never are. The pink line
    is the stretch of orbit the Moon covers while you watch. Pull **zoom** back
    to 1 for the true extent of it, and drag to turn the view, because the
    crossing runs almost entirely *across* the shadow's axis and straight-on
    would hide it.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    # Only the distance rebuilds the geometry. Time, the node and the zoom all
    # live inside the widget, where they stay reachable when it is maximised.
    lunar_distance = mo.ui.slider(
        363300,
        405500,
        1000,
        value=365000,
        label="Moon's distance (km)",
        show_value=True,
    )
    lunar_distance
    return (lunar_distance,)


@app.cell(hide_code=True)
def _(LunarEclipseWidget, mo):
    # Built in a cell of its own: marimo closes a widget's comm when its
    # defining cell re-runs, so nothing here may depend on the controls.
    lunar = LunarEclipseWidget()
    lunar_ui = mo.ui.anywidget(lunar)
    lunar_ui
    return (lunar_ui,)


@app.cell(hide_code=True)
def _(lunar_distance, lunar_ui):
    lunar_ui.moon_distance_km = float(lunar_distance.value)
    return


@app.cell(hide_code=True)
def _(eclipse_summary, lunar_ui, mo):
    _s = eclipse_summary(lunar_ui.track, lunar_ui.node_offset_deg)
    _scalars = lunar_ui.track["scalars"]
    mo.md(
        f"""
    | | |
    |---|---|
    | Alignment sits | {_s['node_offset_deg']:+.1f}° from the node |
    | Moon's latitude then | {_s['latitude_deg']:+.3f}° |
    | Closest approach to the axis | {_s['closest_deg']:.3f}° |
    | Result | **{_s['verdict'].upper()}** |
    | Magnitude | {_s['magnitude']:.2f} of the Moon's width |
    | Time {_s['during']} | {_s['duration_hours']:.1f} h |
    | Earth's umbra out there | {_scalars['umbra_radius_deg'] * 2:.2f}° across, {_scalars['umbra_earth_radii'] * 2 * 6371:,.0f} km |
    """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    /// tip | Try this
    Leave the node at 0 and let it run. The Moon slides into the penumbra and
    dims, then enters the umbra and turns **copper rather than black**. That
    colour is sunlight refracted through the whole ring of Earth's sunrises and
    sunsets and bent inward — during totality the Moon is lit by every dawn on
    the planet at once.

    Now walk the node control out to **±6°**. The umbral crossing shortens, the
    eclipse goes partial, then penumbral, then stops. Past about 10.6° it
    cannot happen at all.
    ///

    ### Notes on the model

    * A lunar eclipse is visible from **the whole night side of Earth** at once,
      and lasts hours. That is the opposite of a solar eclipse, which is why
      most people have seen several of these and no totalities.
    * Shadow sizes come out of the geometry rather than being quoted: Earth's
      umbra works out at 4600 km across at the Moon's distance and its penumbra
      8175 km, both matching the almanac.
    * The edge-on strip is **fully to scale**, both directions: sixty Earth
      radii of gap and a shadow that tapers away to nothing after two hundred.
      Textbook versions are almost always drawn with the Moon far too close and
      far too big, which is part of why eclipses seem like they ought to be
      monthly.
    * Almost none of the crossing is up-and-down. Over six hours either side of
      the alignment the Moon moves about six Earth radii across the shadow's
      axis and only half of one vertically.
    * Node offset is measured in degrees of the Moon's travel round its orbit
      from the node, at the moment of alignment.
    """)
    return


if __name__ == "__main__":
    app.run()
