import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import numpy as np

    from earthsim import astronomy as ast
    from earthsim.labels import date_label, duration, hm, lat_label, lon_label
    from earthsim.widgets import DayNightWidget

    return (
        DayNightWidget,
        ast,
        date_label,
        duration,
        hm,
        lat_label,
        lon_label,
        mo,
        np,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 3. Rotation, day and night

    The globe carries a real equirectangular NASA texture, so the continents
    turn with it. A fragment shader decides, for every point on the surface,
    whether the sun is above or below the local horizon, and blends the
    daylight map into the city-lights map across a twilight band.

    The flat map is the *same instant*, unrolled. The boundary between light
    and dark is the **terminator**, and on an equirectangular projection it
    traces the sine-like curve

    $$\varphi_{\text{term}}(H) \;=\; \arctan\!\left(\frac{-\cos H}{\tan \delta}\right)$$

    where $\delta$ is the sun's declination and $H$ is longitude measured from
    the meridian under the sun. Its crests reach $90° - |\delta|$, so drag the
    date and watch the curve swing: at a solstice it is a broad wave just
    grazing the polar circles, and as an equinox approaches it steepens until
    it stands up into two straight meridians through both poles — the moment
    every latitude on Earth gets twelve hours of daylight.

    Click anywhere on the map to pick a location, and the third panel opens the
    same moment out into that spot's own sky: a dome showing where the sun is
    overhead, and a timeline showing when it climbs over the horizon and drops
    back under it.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    play = mo.ui.switch(True, label="play")
    speed = mo.ui.slider(
        0, 12, 0.25, value=2.0, label="speed (sim hours / second)", show_value=True
    )
    doy = mo.ui.slider(1, 365, 1, value=172, label="day of year", show_value=True)
    utc = mo.ui.slider(
        0, 24, 0.05, value=12.0, label="set solar time (h)", show_value=True
    )
    twilight = mo.ui.slider(
        0.5, 18, 0.5, value=6.0, label="twilight width (deg)", show_value=True
    )
    lights = mo.ui.switch(True, label="city lights")
    graticule = mo.ui.switch(True, label="graticule")
    sky = mo.ui.switch(True, label="sun path panel")

    mo.vstack(
        [
            mo.hstack([play, speed, doy], justify="start", gap=1.5, wrap=True),
            mo.hstack(
                [utc, twilight, lights, graticule, sky],
                justify="start",
                gap=1.5,
                wrap=True,
            ),
        ],
        gap=0.4,
    )
    return doy, graticule, lights, play, sky, speed, twilight, utc


@app.cell(hide_code=True)
def _(DayNightWidget, mo):
    # Built in a cell of its own on purpose: marimo closes a widget's comm when
    # its defining cell re-runs, so nothing here may depend on the controls.
    daynight = DayNightWidget()
    daynight_ui = mo.ui.anywidget(daynight)
    daynight_ui
    return (daynight_ui,)


@app.cell(hide_code=True)
def _(daynight_ui, doy, graticule, lights, play, sky, speed, twilight, utc):
    # Pushes the control values onto the live widget. Changing the date rebuilds
    # the track table; traitlets only notifies on a real change, so nudging one
    # slider never disturbs the running clock.
    daynight_ui.day_of_year = float(doy.value)
    daynight_ui.twilight_deg = float(twilight.value)
    daynight_ui.speed = float(speed.value)
    daynight_ui.playing = bool(play.value)
    daynight_ui.show_lights = bool(lights.value)
    daynight_ui.show_graticule = bool(graticule.value)
    daynight_ui.show_sky = bool(sky.value)
    daynight_ui.utc_hour = float(utc.value)
    return


@app.cell(hide_code=True)
def _(
    ast,
    date_label,
    daynight_ui,
    doy,
    duration,
    hm,
    lat_label,
    lon_label,
    mo,
    np,
):
    # Recomputed in Python whenever the date or the marker changes. Nothing
    # here is animated, so it never needs to cross into the browser.
    _dec = ast.solar_declination(ast.sun_ecliptic_longitude(doy.value))
    _rows = [
        ("Date", date_label(doy.value)),
        ("Sun overhead at", lat_label(np.degrees(_dec))),
    ]

    _marker = list(daynight_ui.marker)
    if _marker:
        _lat, _lon = _marker
        _rise, _set = ast.sunrise_sunset_hours(_lat, _lon, _dec)
        _length = float(ast.day_length_hours(_lat, _dec))
        _rows += [("Marker", f"{lat_label(_lat)}  {lon_label(_lon)}")]
        if _rise is None:
            _rows += [
                ("Sunrise / sunset", "the sun never crosses the horizon"),
                ("Daylight", "24 h 00 m (midnight sun)" if _length else "0 h 00 m (polar night)"),
            ]
        else:
            _rows += [
                ("Sunrise / sunset", f"{hm(_rise)} / {hm(_set)} solar UTC"),
                ("Daylight", duration(_length)),
            ]
    else:
        _rows += [("Marker", "click the flat map to place one")]

    mo.md(
        "\n".join(
            ["| | |", "|---|---|"]
            + [f"| {name} | {value} |" for name, value in _rows]
        )
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    /// tip | Try this
    Drag the date to **355** and click deep inside Antarctica: the sun never
    sets there. Keep the marker where it is and drag the date to **172** for
    the opposite extreme, polar night. Anywhere on the equator the readout
    stays at twelve hours all year, which is the one latitude the tilt cannot
    reach.
    ///

    ### Notes on the model

    * The frame is the one every animation here shares: the ecliptic is the
      world *xz* plane and the spin axis is **fixed** in it, tilted 23.44°
      toward *+x*. That is why one unchanging axis yields a different solar
      declination as the year advances, which is the mechanism animation 2
      will show directly.
    * The orbit is a real ellipse solved through Kepler's equation, so the
      equinoxes and solstices land on their actual calendar dates rather than
      being spaced evenly. Those dates are read back off the model, not
      hard-coded — see `earthsim.labels.SEASON_DAYS`.
    * Times are apparent solar time: the equation of time and the four-minute
      gap between the solar and sidereal day are ignored. Over one simulated
      day the difference is invisible.
    * Day lengths are geometric — the sun's centre, no atmospheric refraction —
      so they run a few minutes shorter than an almanac's sunrise tables.
    * Textures come from the three.js example set (NASA Blue Marble and the
      DMSP night-lights composite), loaded from a CDN.
    """)
    return


if __name__ == "__main__":
    app.run()
