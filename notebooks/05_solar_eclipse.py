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

    The other control is the same one as in the lunar notebook: an alignment
    only becomes an eclipse near a **node** of the Moon's tilted orbit.
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


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    /// tip | Try this
    Set the distance to **405500 km**, the Moon's furthest. Its disc is now too
    small to cover the sun and you get a ring — an **annular** eclipse. Bring it
    back to **363300 km** and totality returns, corona and all.

    The edge-on panel shows exactly why. The Moon's shadow narrows to a point
    about 374,000 km behind it. Earth is roughly 384,000 km away, so at average
    distance the cone runs out **before it gets here** — by about 45 km. Only
    when the Moon is closer than that does the tip actually land, and the patch
    it lands in is the path of totality: a hundred kilometres or so across,
    which is why you have to travel for one.
    ///

    ### Notes on the model

    * The view is **geocentric** — what you would see from the centre of Earth,
      or near enough from the best-placed spot on the surface. Where you stand
      matters enormously for a real solar eclipse: the Moon shifts by up to a
      degree against the sun between one side of Earth and the other. That
      parallax is why totality is a narrow track rather than a hemisphere, and
      it is not modelled here.
    * That also makes the node limits here narrower than the real ones. This
      model stops producing eclipses past about 6°; allowing for observers
      anywhere on Earth, the real limit is nearer 15°.
    * Annular eclipses are slightly the commoner kind, for the reason above.
    * The corona is drawn, not computed. Its shape follows the sun's magnetic
      field and changes from eclipse to eclipse.
    * Node offset is measured in degrees of the Moon's travel round its orbit
      from the node, at the moment of alignment.
    """)
    return


if __name__ == "__main__":
    app.run()
