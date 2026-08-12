"""The Python/JavaScript seam.

Python computes the astronomy and ships a track; the JavaScript interpolates
that track and draws. Nothing in the browser re-derives a number, so the only
way the two can disagree is if the JS reads the track wrongly - an off-by-one
in a lookup, a step label picked up a frame late, or a channel interpolated
across a wrap. These tests run the real JS through node against the real
Python, for all three animations.

Skipped when node is not installed; the astronomy suite still covers the maths.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from earthsim import astronomy as ast
from earthsim.labels import hm, phase_name, season_name, short_date
from earthsim.track import day_track, eclipse_track, moon_track, year_track

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "src" / "earthsim" / "static"
DRIVER = Path(__file__).parent / "js" / "contract_driver.mjs"

node = shutil.which("node")
requires_node = pytest.mark.skipif(node is None, reason="node is not installed")

# A southern declination, where the terminator's signs matter most.
DAY_OF_YEAR = 305.0
SEASONS_LATITUDE = 45.0
# On a grid node, between two, and at both solstice extremes.
GRID_DECLINATIONS = [-23.4392811, -12.0, -0.25, 0.0, 7.37, 23.4392811]
DAY_HOURS = [0.0, 0.001, 1.0, 3.7, 6.0, 11.5, 12.0, 15.9833, 17.25, 23.0, 23.9999, 24.0]
MOON_AGES = [0.0, 3.2, 7.38, 11.0, 14.765, 18.5, 22.15, 26.0, 29.53]
YEAR_DAYS = [0.0, 3.5, 79.8, 100.0, 172.0, 186.0, 265.7, 300.0, 355.0, 365.0]
ECLIPSE_HOURS = [-6.0, -3.25, -1.0, 0.0, 0.5, 2.75, 6.0]
HOUR_ANGLES = [-180.0, -179.5, -117.3, -90.0, -0.4, 0.0, 45.6, 90.0, 179.9, 180.0]


@pytest.fixture(scope="module")
def readings(tmp_path_factory):
    """Run the browser's own code over known tracks and collect the results."""
    tracks = {
        "day": day_track(DAY_OF_YEAR, (51.5, -0.1)),
        "eclipse": eclipse_track("lunar"),
        "moon": moon_track(),
        "year": year_track(SEASONS_LATITUDE, 0.0),
    }
    spec = {
        "tracks": tracks,
        "times": {
            "day": DAY_HOURS,
            "moon": MOON_AGES,
            "year": YEAR_DAYS,
            "eclipse": ECLIPSE_HOURS,
        },
        "tableQueries": {
            "terminator": {"track": "day", "table": "terminator_lat", "at": HOUR_ANGLES},
            "daylight": {
                "track": "year",
                "table": "daylight_hours",
                "at": GRID_DECLINATIONS,
            },
        },
        "gridQueries": {
            "sun": {"track": "year", "grid": "sun_elevation", "at": GRID_DECLINATIONS}
        },
        "clock": DAY_HOURS,
    }
    payload = tmp_path_factory.mktemp("js") / "queries.json"
    payload.write_text(json.dumps(spec))
    result = subprocess.run(
        [node, str(DRIVER), str(STATIC / "earthkit.js"), str(payload)],
        capture_output=True,
        text=True,
        check=True,
    )
    return tracks, json.loads(result.stdout)


@requires_node
@pytest.mark.parametrize(
    "name",
    ["earthkit.js", "daynight.js", "moonphases.js", "seasons.js", "eclipses.js"],
)
def test_javascript_parses(name):
    subprocess.run([node, "--check", str(STATIC / name)], check=True)


# ------------------------------------------------------- 3. day and night


@requires_node
def test_js_reproduces_the_spin_python_computed(readings):
    _, out = readings
    lam = ast.sun_ecliptic_longitude(DAY_OF_YEAR)
    for hour, sample in zip(DAY_HOURS, out["samples"]["day"], strict=True):
        assert sample["spin"] == pytest.approx(float(ast.spin_angle(lam, hour)), abs=1e-9)


@requires_node
def test_js_reproduces_the_subsolar_longitude(readings):
    _, out = readings
    for hour, sample in zip(DAY_HOURS, out["samples"]["day"], strict=True):
        expected = float(ast.subsolar_longitude(hour))
        wrapped = float(ast.wrap_longitude(sample["subsolar_lon"]))
        assert wrapped == pytest.approx(expected, abs=1e-9)


@requires_node
def test_js_reproduces_the_local_sun_position(readings):
    """The sun-path panel is only as good as the two channels behind it."""
    _, out = readings
    dec = ast.solar_declination(ast.sun_ecliptic_longitude(DAY_OF_YEAR))
    for hour, sample in zip(DAY_HOURS, out["samples"]["day"], strict=True):
        subsolar = ast.subsolar_longitude(hour)
        assert sample["sun_elevation"] == pytest.approx(
            float(ast.sun_elevation_deg(51.5, -0.1, subsolar, dec)), abs=0.02
        )
        expected = float(ast.sun_azimuth_deg(51.5, -0.1, subsolar, dec))
        assert sample["sun_azimuth"] % 360.0 == pytest.approx(expected, abs=0.05)


@requires_node
def test_js_terminator_lookup_is_exact_on_the_table_nodes(readings):
    """An off-by-one in the table index would slide the whole curve east."""
    _, out = readings
    dec = ast.solar_declination(ast.sun_ecliptic_longitude(DAY_OF_YEAR))
    on_node = [
        (h, got)
        for h, got in zip(HOUR_ANGLES, out["tables"]["terminator"], strict=True)
        if float(h).is_integer()
    ]
    assert on_node, "no whole-degree hour angles in the query set"
    for hour_angle, got in on_node:
        expected = float(ast.terminator_lat_deg(hour_angle, dec))
        assert got == pytest.approx(expected, abs=1e-9)


@requires_node
def test_js_terminator_interpolation_stays_far_below_a_pixel(readings):
    """Between nodes the JS lerps a curve, so a little error is expected.

    One degree of latitude is about 2.5 px on the map, so 0.01 degrees is a
    fortieth of a pixel - invisible, but tight enough that a real indexing
    mistake (off by a whole degree) would still fail here.
    """
    _, out = readings
    dec = ast.solar_declination(ast.sun_ecliptic_longitude(DAY_OF_YEAR))
    for hour_angle, got in zip(HOUR_ANGLES, out["tables"]["terminator"], strict=True):
        expected = float(ast.terminator_lat_deg(hour_angle, dec))
        assert got == pytest.approx(expected, abs=0.01)
        assert -90.0 <= got <= 90.0


@requires_node
def test_js_and_python_agree_on_the_clock(readings):
    _, out = readings
    for hour, shown in zip(DAY_HOURS, out["clock"], strict=True):
        assert shown == hm(hour)


# ---------------------------------------------------------- 1. moon phases


@requires_node
def test_js_reproduces_the_illuminated_fraction(readings):
    _, out = readings
    for age, sample in zip(MOON_AGES, out["samples"]["moon"], strict=True):
        expected = float(ast.illuminated_fraction(ast.moon_elongation(age)))
        assert sample["illuminated"] == pytest.approx(expected, abs=2e-4)


@requires_node
def test_js_lights_the_moon_from_the_right_side(readings):
    """The lighting vector is the whole phase animation; a sign flip here
    would show a waxing moon lit on the wrong limb."""
    _, out = readings
    for age, sample in zip(MOON_AGES, out["samples"]["moon"], strict=True):
        expected = ast.sun_direction_in_moon_view(ast.moon_elongation(age))
        assert sample["moon_view_sun"] == pytest.approx(expected, abs=2e-3)
        assert np.linalg.norm(sample["moon_view_sun"]) == pytest.approx(1.0, abs=2e-3)


@requires_node
def test_js_picks_up_the_phase_name_at_the_right_moment(readings):
    """Steps switch rather than blend, so the boundary has to land exactly."""
    _, out = readings
    for age, sample in zip(MOON_AGES, out["samples"]["moon"], strict=True):
        assert sample["phase"] == phase_name(ast.moon_elongation(age))


@requires_node
def test_new_and_full_moon_are_named_and_lit_correctly(readings):
    tracks, _ = readings
    month = tracks["moon"]["scalars"]["synodic_month"]
    assert phase_name(ast.moon_elongation(0.0)) == "New moon"
    assert phase_name(ast.moon_elongation(month / 2)) == "Full moon"
    assert ast.illuminated_fraction(ast.moon_elongation(0.0)) == pytest.approx(0.0)
    assert ast.illuminated_fraction(ast.moon_elongation(month / 2)) == pytest.approx(1.0)


# ------------------------------------------------------------- 2. seasons


@requires_node
def test_js_reproduces_earths_orbital_position(readings):
    _, out = readings
    for day, sample in zip(YEAR_DAYS, out["samples"]["year"], strict=True):
        assert sample["earth_pos"] == pytest.approx(
            ast.earth_position_au(day), abs=2e-4
        )
        assert sample["distance_au"] == pytest.approx(
            float(ast.sun_distance_au(day)), abs=2e-5
        )


@requires_node
def test_js_picks_up_the_season_and_date_labels(readings):
    _, out = readings
    for day, sample in zip(YEAR_DAYS, out["samples"]["year"], strict=True):
        assert sample["season"] == season_name(day)
        # A step label holds from its own start time, so mid-day still reads as
        # the day that began, not the one it is rounding towards.
        assert sample["date"] == short_date(math.floor(day))


@requires_node
@pytest.mark.parametrize("index", range(len(GRID_DECLINATIONS)))
def test_js_draws_the_sun_curve_python_computed(readings, index):
    """The curve the seasons panel fills under, checked point for point.

    The JavaScript interpolates between declination rows; Python evaluates the
    formula directly. They have to agree along the whole day or the daylight
    area would be the wrong shape.
    """
    _, out = readings
    declination = GRID_DECLINATIONS[index]
    hours = np.array(out["gridCols"]["sun"])
    drawn = np.array(out["gridRows"]["sun"][index])
    expected = ast.sun_elevation_local_deg(
        SEASONS_LATITUDE, hours, np.radians(declination)
    )
    assert drawn == pytest.approx(expected, abs=0.05)


@requires_node
def test_the_curve_gets_taller_and_wider_as_summer_comes(readings):
    """The whole point of the panel: a swelling arch, not a static picture."""
    _, out = readings
    rows = {d: np.array(r) for d, r in zip(GRID_DECLINATIONS, out["gridRows"]["sun"])}
    winter = rows[-23.4392811]
    summer = rows[23.4392811]
    assert summer.max() > winter.max() + 40  # sun climbs far higher
    assert (summer > 0).sum() > (winter > 0).sum()  # and stays up far longer


@requires_node
def test_daylight_table_agrees_with_the_curve_it_sits_beside(readings):
    """The printed hours and the lit area have to be the same day length."""
    _, out = readings
    hours = np.array(out["gridCols"]["sun"])
    step = hours[1] - hours[0]
    for declination, row in zip(GRID_DECLINATIONS, out["gridRows"]["sun"], strict=True):
        above = np.count_nonzero(np.array(row) > 0) * step
        stated = float(ast.day_length_hours(SEASONS_LATITUDE, np.radians(declination)))
        assert above == pytest.approx(stated, abs=step * 1.5)


@requires_node
def test_js_reads_the_daylight_table_the_same_way_python_wrote_it(readings):
    """Read back through the browser's own lookup, not a copy of it here."""
    _, out = readings
    for declination, got in zip(
        GRID_DECLINATIONS, out["tables"]["daylight"], strict=True
    ):
        expected = float(
            ast.day_length_hours(SEASONS_LATITUDE, np.radians(declination))
        )
        assert got == pytest.approx(expected, abs=0.02)


# ------------------------------------------------------------- 4. eclipses


@requires_node
def test_js_places_the_moon_where_python_put_it(readings):
    """The side view reads these two channels to move the Moon. Getting either
    wrong is how the panel ends up looking static."""
    _, out = readings
    distance = None
    for hours, sample in zip(ECLIPSE_HOURS, out["samples"]["eclipse"], strict=True):
        distance = sample["moon_distance_earth_radii"]
        expected_across = -distance * np.sin(
            np.radians(ast.syzygy_longitude_offset_deg(hours))
        )
        expected_along = distance * np.cos(
            np.radians(ast.syzygy_longitude_offset_deg(hours))
        )
        assert sample["moon_cross_re"] == pytest.approx(expected_across, abs=1e-6)
        assert sample["moon_axis_re"] == pytest.approx(expected_along, abs=1e-6)


@requires_node
def test_js_sees_the_moon_move_over_the_window(readings):
    _, out = readings
    across = [s["moon_cross_re"] for s in out["samples"]["eclipse"]]
    assert max(across) - min(across) > 5.0  # Earth radii
