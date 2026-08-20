import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo

    from earthsim.labels import lat_label, lon_label
    from earthsim.widgets import LatitudeWidget

    return LatitudeWidget, lat_label, lon_label, mo


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 6. Latitude, and the height of the pole star

        Latitude is an angle at the centre of Earth: swing from the equator up to
        where you are standing, and that is your latitude. It is not something you
        can see, because you cannot get to the centre of Earth to measure it.

        But you can measure it, with a protractor and a clear night, because **the
        pole star sits that same angle above your horizon**. Sailors navigated on
        this for centuries.

        Pick a place on the globe or on the map — they are the same choice, shown
        twice — and the figure underneath works out why.

    One figure, two scales. In front: what you would actually do — stand
        still, face north, and measure how high the pole sits above your horizon.
        Behind it: the same corner drawn on a section of the Earth, which is why
        that measurement is your latitude. The dashed lines join the two, because
        the near view is simply the far one magnified.

        The **dotted blue line** is the true celestial pole, exactly parallel to
        Earth's axis. Polaris is the star just off it, riding the small
        dotted circle it traces once a day. That circle is the entire error in the
        method, and it is drawn far larger than life so you can see it at all.
    """)
    return


@app.cell(hide_code=True)
def _(LatitudeWidget, mo):
    # Built in a cell of its own: marimo closes a widget's comm when its
    # defining cell re-runs, so nothing here may depend on the controls.
    latitude = LatitudeWidget()
    latitude_ui = mo.ui.anywidget(latitude)
    latitude_ui
    return (latitude_ui,)


@app.cell(hide_code=True)
def _(lat_label, latitude_ui, lon_label, mo):
    _r = latitude_ui.readout
    _low, _high = _r["polaris_low_deg"], _r["polaris_high_deg"]
    _seen = (
        f"{_low:.1f}° to {_high:.1f}° as it circles the pole"
        if _r["visible"]
        else "below the horizon — you would need the southern sky instead"
    )
    mo.md(
        f"""
    | | |
    |---|---|
    | Place | {lat_label(_r['latitude_deg'])}  {lon_label(_r['longitude_deg'])} |
    | Angle at Earth's centre | {_r['latitude_deg']:+.1f}° from the equator |
    | Height of the celestial pole | **{_r['pole_altitude_deg']:+.1f}° above the horizon** |
    | Polaris over a night | {_seen} |

    {_r['headline']}
    """
    )
    return


if __name__ == "__main__":
    app.run()
