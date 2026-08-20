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

    Earth's axis leans 23.44° out of the plane of its orbit, and - this is the
    part that matters — **it keeps pointing the same way in space all year**. It
    does not tip back and forth. It does not follow the sun. It just leans, and
    the planet carries that lean around the orbit with it.

    Six months apart, that unchanging lean is pointed towards the sun and then
    away from it. Watch the axis in the left panel as Earth walks its orbit: the
    blue line never changes direction, yet in June its northern end tips
    sunward and in December it tips away.

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


if __name__ == "__main__":
    app.run()
