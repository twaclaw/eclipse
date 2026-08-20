import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo

    from earthsim.track import eclipse_summary
    from earthsim.widgets import SolarEclipseWidget

    return SolarEclipseWidget, eclipse_summary, mo


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 5. Solar eclipses

    The Moon is four hundred times smaller than the sun and four hundred times
    closer, so the two discs come out very nearly the same size in our sky.
    Nothing arranged that; it is a coincidence of this era, and it is the only
    reason totality looks the way it does.

    "Very nearly" is doing some work. The Moon's orbit is not a circle, and at
    its mean distance the Moon's disc is **slightly the smaller of the two**. So
    a dead-central eclipse gives a ring of sunlight rather than a black disc,
    and totality only happens when the Moon is close enough. Drag the
    **distance** control and watch the eclipse flip between total and annular.

    """)
    return


@app.cell(hide_code=True)
def _(mo):
    # The distance is the interesting control here: it decides total or annular.
    # Time, node and zoom live inside the widget so they survive maximising.
    solar_distance = mo.ui.slider(
        363300,
        405500,
        1000,
        value=365000,
        label="Moon's distance (km)  ·  perigee 363300, apogee 405500",
        show_value=True,
    )
    solar_distance
    return (solar_distance,)


@app.cell(hide_code=True)
def _(SolarEclipseWidget, mo):
    # Built in a cell of its own: marimo closes a widget's comm when its
    # defining cell re-runs, so nothing here may depend on the controls.
    solar = SolarEclipseWidget()
    solar_ui = mo.ui.anywidget(solar)
    solar_ui
    return (solar_ui,)


@app.cell(hide_code=True)
def _(solar_distance, solar_ui):
    solar_ui.moon_distance_km = float(solar_distance.value)
    return


@app.cell(hide_code=True)
def _(eclipse_summary, mo, solar_ui):
    _s = eclipse_summary(solar_ui.track, solar_ui.node_offset_deg)
    _scalars = solar_ui.track["scalars"]
    _umbra_km = _scalars["moon_umbra_earth_radii"] * 6371
    _reach = (
        f"reaches Earth, {2 * _umbra_km:,.0f} km wide"
        if _umbra_km > 0
        else f"closes {abs(_umbra_km):,.0f} km short — no totality anywhere"
    )
    mo.md(
        f"""
    | | |
    |---|---|
    | Alignment sits | {_s['node_offset_deg']:+.1f}° from the node |
    | Moon's latitude then | {_s['latitude_deg']:+.3f}° |
    | Result | **{_s['verdict'].upper()}** |
    | Magnitude | {_s['magnitude']:.2f} of the sun's width |
    | Time {_s['during']} | {_s['duration_hours']:.1f} h |
    | Moon's disc | {_scalars['moon_radius_deg'] * 2:.4f}° across |
    | Sun's disc | {_scalars['sun_radius_deg'] * 2:.4f}° across |
    | The Moon's umbra | {_reach} |
    """
    )
    return


if __name__ == "__main__":
    app.run()
