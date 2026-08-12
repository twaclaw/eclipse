import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import numpy as np

    from earthsim import astronomy as ast
    from earthsim.labels import date_label, duration, lat_label
    from earthsim.widgets import SeasonsWidget

    return SeasonsWidget, ast, date_label, duration, lat_label, mo, np


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 2. Axial tilt and the seasons

    Earth's axis leans 23.44° out of the plane of its orbit, and — this is the
    part that matters — **it keeps pointing the same way in space all year**. It
    does not tip back and forth. It does not follow the sun. It just leans, and
    the planet carries that lean around the orbit with it.

    Six months apart, that unchanging lean is pointed towards the sun and then
    away from it. Watch the axis in the left panel as Earth walks its orbit: the
    blue line never changes direction, yet in June its northern end tips
    sunward and in December it tips away.

    Pick a place on the map, and the panel underneath draws that place's day:
    the sun's height against the clock, with the daylight lit up. Watch it as
    the orbit runs. The bright arch swells through summer and shrinks through
    winter, and above the polar circle it either swallows the whole day or
    vanishes below the horizon altogether. Same axis, same lean, all year.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    # Play and speed live inside the widget, so they stay reachable when the
    # panel is maximised. Setting them from here too would fight the widget.
    season_stretch = mo.ui.slider(
        1, 12, 0.5, value=1.0, label="exaggerate the ellipse (×)", show_value=True
    )
    season_follow = mo.ui.switch(False, label="follow Earth")
    season_grat = mo.ui.switch(False, label="graticule")

    mo.vstack(
        [
            mo.hstack(
                [season_stretch, season_follow, season_grat],
                justify="start",
                gap=1.5,
                wrap=True,
            ),
        ],
        gap=0.4,
    )
    return season_follow, season_grat, season_stretch


@app.cell(hide_code=True)
def _(SeasonsWidget, mo):
    # Built in a cell of its own: marimo closes a widget's comm when its
    # defining cell re-runs, so nothing here may depend on the controls.
    seasons = SeasonsWidget()
    seasons_ui = mo.ui.anywidget(seasons)
    seasons_ui
    return (seasons_ui,)


@app.cell(hide_code=True)
def _(season_follow, season_grat, season_stretch, seasons_ui):
    seasons_ui.eccentricity_stretch = float(season_stretch.value)
    seasons_ui.follow_earth = bool(season_follow.value)
    seasons_ui.show_graticule = bool(season_grat.value)
    return


@app.cell(hide_code=True)
def _(ast, date_label, duration, lat_label, mo, np, seasons_ui):
    _doy = float(seasons_ui.day_of_year)
    _lat = float(seasons_ui.marker[0])
    _dec = ast.solar_declination(ast.sun_ecliptic_longitude(_doy))
    _distance = float(ast.sun_distance_au(_doy))
    _daylight = float(ast.day_length_hours(_lat, _dec))
    _energy = float(ast.daily_insolation(_lat, _doy))

    # The same latitude, half a year away: the comparison that makes the point.
    _opposite = (_doy + 182.6) % 365.0
    _energy_opposite = float(ast.daily_insolation(_lat, _opposite))
    _distance_opposite = float(ast.sun_distance_au(_opposite))

    mo.md(
        f"""
    | | today | in six months |
    |---|---|---|
    | Date | {date_label(_doy)} | {date_label(_opposite)} |
    | Distance to the sun | {_distance:.4f} AU | {_distance_opposite:.4f} AU |
    | Sunlight at {lat_label(_lat)} | **{_energy:.0f} W/m²** | **{_energy_opposite:.0f} W/m²** |
    | Daylight there | {duration(_daylight)} | {duration(float(ast.day_length_hours(_lat, ast.solar_declination(ast.sun_ecliptic_longitude(_opposite))))) } |
    | Sun overhead at | {np.degrees(_dec):+.1f}° | {np.degrees(ast.solar_declination(ast.sun_ecliptic_longitude(_opposite))):+.1f}° |

    Click the map to move the location. Distance changes by under two percent
    across the whole year; the sunlight at a given latitude can change by a
    factor of ten.
    """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    /// tip | Try this
    Hit pause in the control strip and drag **when** to day **3** —
    Earth's closest approach to the sun, at
    0.983 AU. It is the depth of northern winter. Now set it to **186**, the
    furthest point at 1.017 AU, in the middle of northern summer. Distance is
    doing the opposite of what the seasons do.

    Then press play, ease the orbit speed down until it crawls, and click
    somewhere above the Arctic circle — northern Greenland, or
    Svalbard at about 78°N — and let it run. The arch lifts clear of the
    horizon for weeks on end in summer, then sinks entirely beneath it in
    winter. Compare the tenfold swing in the sunlight row above with the 3.4%
    swing in the distance row.

    Finally, drag **exaggerate the ellipse** up to 12 and watch the orbit turn
    into a visible oval. That is what textbook diagrams draw, and it is why so
    many people come away thinking the seasons are about distance.
    ///

    ### Notes on the model

    * The orbit is genuinely this circular. At its true eccentricity of 0.0167
      the ellipse is indistinguishable from a circle on screen, which is why the
      exaggeration slider exists — and why it starts at 1.0, showing the truth.
    * **The globe does not spin.** A year passes in seconds here, so 365 turns
      would be a blur that hid the thing worth seeing. The lit half still moves,
      because that depends on where Earth is, not on the time of day.
    * The globe is turned so the place you picked sits at local noon, which is
      why its hemisphere is always the one facing the sun. Pick somewhere else
      and the planet swings round to suit.
    * The **earth** and **sun** sliders are exposure, not physics. The sun is
      drawn far smaller than any honest scale would allow — at true proportions
      it would be a hundred times Earth's width and four hundred times further
      away — so its size and glare are chosen to read well, not to measure.
    * The yellow line on the map is the latitude the sun stands directly over.
      It slides between the two tropics and back once a year: that is the tilt,
      drawn on the ground.
    * The sun-path panel runs on **local solar time**, so noon is always at 12
      and longitude does not change the shape of the arch — only latitude and
      the date do. The dashed curves are the June and December solstices, the
      bounds every other day of the year falls between.
    * Insolation in the table is the daily mean at the top of the atmosphere,
      so it accounts for how high the sun climbs, how long it stays up, *and*
      the distance. Clouds, air and ground cover are not in it.
    * Season names are given for both hemispheres, since the tilt does opposite
      things at opposite ends of the planet at the same moment.
    """)
    return


if __name__ == "__main__":
    app.run()
