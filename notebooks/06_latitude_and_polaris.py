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


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    /// tip | Try this
        Drag the latitude slider from the equator to the pole. At **0°** the pole
        star sits on the horizon; at **90°** it is straight overhead and the stars
        wheel round the zenith. Everywhere between, the angle at the centre of the
        figure and the angle at your feet stay locked together.

        Then go south. Below the equator the sight line dips under the horizon and
        Polaris is simply gone — the angle is still your latitude, it is just
        measured downwards.
        ///

        ### Why it works

        Two facts and one piece of school geometry:

        1. Your **zenith** — straight up — points along the radius from Earth's
           centre through your feet. So the angle between the equator and your
           radius is also the angle between the equatorial plane and your zenith.
        2. Polaris is about 433 light years away. Every line drawn to it from
           anywhere on Earth is, to any accuracy that matters, **parallel to
           Earth's axis**.

    Your radius is then a transversal cutting two parallel lines: the axis at
        the centre, and your sight line to the pole. In the figure those are the
        two **blue** angles, θ at the centre and θ′ at your feet, and they are equal
        because alternate angles across a transversal always are.

        Your horizon is square to your zenith, so what is left over is
        φ′ = 90° − θ′ = 90° − θ = φ. Those are the two **orange** angles: one is
        your latitude, the other is the height of the pole above your horizon, and
        the figure shows they are the same angle.

        ### Notes on the model

        * **"Approximately" is doing one job only.** The *celestial pole* stands
          exactly your latitude above the horizon; that part is not an
          approximation. Polaris merely sits about 0.65° away from that pole, so
          it circles it once a day and its altitude wanders by that much either
          side. Precession is closing that gap until roughly 2100, after which it
          opens again.
        * Also left out: atmospheric refraction, which lifts objects near the
          horizon by around half a degree and so matters most at low latitudes,
          and the fact that Earth is slightly flattened, which separates
          *geodetic* latitude from the geocentric angle drawn here by up to 0.19°.
        * There is no bright southern equivalent. σ Octantis does the same job
          below the equator, but at magnitude 5.4 it is barely visible.
    """)
    return


if __name__ == "__main__":
    app.run()
