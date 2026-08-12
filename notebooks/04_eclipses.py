import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import numpy as np

    from earthsim import astronomy as ast
    from earthsim.widgets import EclipsesWidget

    return EclipsesWidget, ast, mo, np


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 4. Eclipses

    Every month the Moon passes between us and the sun, and every month it
    passes opposite the sun. If the three bodies shared a plane, that would mean
    a solar eclipse and a lunar eclipse every four weeks. We get a couple of
    each a year instead.

    The reason is the 5.1° tilt of the Moon's orbit. It crosses the plane of
    Earth's orbit at just two points — the **nodes** — and an alignment only
    becomes an eclipse if it happens near one of them. Anywhere else the Moon
    sails a degree or so above or below, and the shadow misses.

    Drag the **node** control and watch that happen. A degree of latitude puts
    the Moon a full Earth radius off the shadow's axis.

    Three views of the same moment: what you would see, the shadow seen down
    its own axis, and the whole system edge-on. That last one is drawn entirely
    to scale, which diagrams of this almost never are. The pink line is the
    stretch of orbit the Moon covers while you watch, and it slides along it
    and through the cone. Pull **zoom** back to 1 to see the true extent of the
    system, and drag to turn the view — the crossing runs almost entirely
    *across* the shadow's axis, so straight-on it would be hidden.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    eclipse_kind = mo.ui.dropdown(
        {"lunar — Earth's shadow on the Moon": "lunar",
         "solar — the Moon's shadow on us": "solar"},
        value="lunar — Earth's shadow on the Moon",
        label="eclipse",
    )
    moon_distance = mo.ui.slider(
        363300,
        405500,
        1000,
        value=365000,
        label="Moon's distance (km)",
        show_value=True,
    )

    mo.hstack([eclipse_kind, moon_distance], justify="start", gap=1.5, wrap=True)
    return eclipse_kind, moon_distance


@app.cell(hide_code=True)
def _(EclipsesWidget, mo):
    # Built in a cell of its own: marimo closes a widget's comm when its
    # defining cell re-runs, so nothing here may depend on the controls.
    eclipses = EclipsesWidget()
    eclipses_ui = mo.ui.anywidget(eclipses)
    eclipses_ui
    return (eclipses_ui,)


@app.cell(hide_code=True)
def _(eclipse_kind, eclipses_ui, moon_distance):
    # Play, time and the node offset belong to the widget. These two change the
    # geometry itself, so they rebuild the track.
    eclipses_ui.kind = str(eclipse_kind.value)
    eclipses_ui.moon_distance_km = float(moon_distance.value)
    return


@app.cell(hide_code=True)
def _(ast, eclipses_ui, mo, np):
    # The verdict at greatest eclipse, computed in Python from the node offset
    # the widget last reported.
    _scalars = eclipses_ui.track["scalars"]
    _offset = float(eclipses_ui.node_offset_deg)
    _hours = np.linspace(-_scalars["span_hours"], _scalars["span_hours"], 2001)
    _gap = ast.separation_deg(
        ast.syzygy_longitude_offset_deg(_hours),
        ast.moon_ecliptic_latitude_at_node_offset(_offset, _hours),
    )
    _closest = float(np.min(_gap))
    _moon_r = _scalars["moon_radius_deg"]

    if _scalars["kind"] == "lunar":
        _verdict = ast.lunar_eclipse_kind(
            _closest,
            _moon_r,
            _scalars["umbra_radius_deg"],
            _scalars["penumbra_radius_deg"],
        )
        _covered, _covering = _moon_r, _scalars["umbra_radius_deg"]
        _inside = _gap < _scalars["umbra_radius_deg"] + _moon_r
        _what = "in Earth's umbra"
    else:
        _verdict = ast.solar_eclipse_kind(_closest, _moon_r, _scalars["sun_radius_deg"])
        _covered, _covering = _scalars["sun_radius_deg"], _moon_r
        _inside = _gap < _scalars["sun_radius_deg"] + _moon_r
        _what = "with the sun partly hidden"

    _magnitude = ast.eclipse_magnitude(_closest, _covered, _covering)
    _duration = float(np.count_nonzero(_inside)) * (_hours[1] - _hours[0])

    mo.md(
        f"""
    | | |
    |---|---|
    | Alignment sits | {_offset:+.1f}° from the node |
    | Moon's latitude then | {ast.moon_ecliptic_latitude_at_node_offset(_offset):+.3f}° |
    | Closest approach | {_closest:.3f}° |
    | Result | **{_verdict.upper()}** |
    | Magnitude | {_magnitude:.2f} of the disc's width |
    | Time {_what} | {_duration:.1f} h |
    """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    /// tip | Try this
    Start on **lunar** with the node at 0 and let it run: the Moon slides into
    the penumbra, dims, then enters the umbra and turns copper rather than
    black. That colour is sunlight refracted through the whole ring of Earth's
    sunrises and sunsets, bent inward onto the Moon.

    Now walk the node control out to **±6°**. The umbra crossing shortens, the
    eclipse goes partial, then penumbral, then stops. Past about 10.6° it
    cannot happen at all.

    Switch to **solar** and set the Moon's distance to **405500 km**, its
    furthest. The Moon is now too small to cover the sun and you get a ring —
    an annular eclipse. Bring it back to **363300 km** and totality returns,
    corona and all. The edge-on panel shows why: at distance the Moon's shadow
    closes to a point before it reaches us.
    ///

    ### Notes on the model

    * The edge-on strip is **fully to scale**, both directions: sixty Earth
      radii of gap, a shadow that tapers away to nothing after two hundred, and
      a Moon a quarter of Earth's width. Only the sun is missing, and it would
      be four hundred times further off again. Textbook versions of this
      picture are almost always drawn with the Moon far too close and far too
      big, which is part of why eclipses seem like they ought to be monthly.
    * The solar view is geocentric: what you would see from the centre of Earth.
      Real solar eclipses also depend on *where* you stand, since the Moon
      shifts by up to a degree against the sun between one side of Earth and
      the other. That parallax is why totality is a narrow track rather than a
      hemisphere, and it is not modelled here.
    * Shadow sizes come out of the geometry rather than being quoted: Earth's
      umbra works out at 4600 km across at the Moon's distance, its penumbra
      8175 km, both matching the almanac.
    * The Moon's own umbra is a near thing. At its mean distance the cone closes
      about 45 km *short* of Earth, which is why annular eclipses are slightly
      more common than total ones.
    * Almost none of the crossing is up-and-down. Over six hours either side of
      the alignment the Moon moves about six Earth radii across the shadow's
      axis and only half of one vertically, which is why the side view is
      turned rather than drawn dead edge-on.
    * Node offset is measured in degrees of the Moon's travel round its orbit
      from the node, at the moment of alignment.
    """)
    return


if __name__ == "__main__":
    app.run()
