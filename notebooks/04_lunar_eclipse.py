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


if __name__ == "__main__":
    app.run()
