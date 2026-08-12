"""Checks on the equations in :mod:`earthsim.astronomy`.

Expected values are geometric - the sun's centre, no atmospheric refraction -
because that is what the code computes. Almanac figures are quoted to the
precision the model can reasonably reach with a two-body orbit and no
perturbations.
"""

from __future__ import annotations

import numpy as np
import pytest

from earthsim import astronomy as ast
from earthsim.labels import (
    PHASE_NAMES_ES,
    SEASON_DAYS,
    date_label,
    phase_name,
    phase_name_es,
)
from earthsim.track import Track, day_track, eclipse_track, moon_track, year_track


def declination_on(day_of_year):
    """Solar declination in degrees, the quantity every animation turns on."""
    return np.degrees(ast.solar_declination(ast.sun_ecliptic_longitude(day_of_year)))


JUNE = ast.solar_declination(ast.sun_ecliptic_longitude(172))


# ------------------------------------------------------------------- the orbit


def test_orbit_is_an_ellipse_not_a_circle():
    assert ast.sun_distance_au(ast.PERIHELION_DOY) == pytest.approx(0.98329, abs=1e-4)
    assert ast.sun_distance_au(186) == pytest.approx(1.01671, abs=1e-3)


@pytest.mark.parametrize(
    ("day_of_year", "expected"),
    [(3, -22.85), (105, 9.9), (172, 23.44), (305, -14.2), (355, -23.44)],
)
def test_declination_tracks_the_almanac(day_of_year, expected):
    assert declination_on(day_of_year) == pytest.approx(expected, abs=0.3)


def test_declination_never_leaves_the_tropics():
    dec = declination_on(np.arange(0, 366, 0.25))
    assert np.max(np.abs(dec)) == pytest.approx(ast.TROPIC_DEG, abs=0.01)


@pytest.mark.parametrize(
    ("name", "expected_doy"),
    [
        ("March equinox", 79.8),
        ("June solstice", 172.0),
        ("September equinox", 265.7),
        ("December solstice", 355.6),
    ],
)
def test_season_boundaries_fall_on_their_real_dates(name, expected_doy):
    """The dates are read back off the orbit model, not hard-coded."""
    found = [doy for doy, label in SEASON_DAYS.items() if label == name]
    assert found, f"{name} was not located"
    assert found[0] == pytest.approx(expected_doy, abs=1.0)


# ------------------------------------------------------- sun over the surface


@pytest.mark.parametrize(
    ("hours", "expected_lon"), [(12, 0.0), (0, 180.0), (18, -90.0), (6, 90.0)]
)
def test_subsolar_longitude_follows_solar_time(hours, expected_lon):
    assert abs(ast.subsolar_longitude(hours)) == pytest.approx(abs(expected_lon))


def _rot_z(vec, angle):
    c, s = np.cos(angle), np.sin(angle)
    return np.array([vec[0] * c - vec[1] * s, vec[0] * s + vec[1] * c, vec[2]])


def _rot_y(vec, angle):
    c, s = np.cos(angle), np.sin(angle)
    return np.array([vec[0] * c + vec[2] * s, vec[1], -vec[0] * s + vec[2] * c])


@pytest.mark.parametrize(
    ("day_of_year", "hours"),
    [(172, 12), (172, 0), (80, 6), (355, 17.25), (1, 3.7), (266, 21)],
)
def test_globe_and_flat_map_agree_on_the_subsolar_point(day_of_year, hours):
    """The load-bearing check.

    The flat map is drawn from ``(declination, subsolar_longitude)`` while the
    globe is drawn by rotating a mesh with ``spin_angle``. Undo the two
    rotations the renderer applies and the sun must land on the same spot, or
    the two panels would quietly disagree.
    """
    lam = ast.sun_ecliptic_longitude(day_of_year)
    world = ast.sun_direction(lam)
    tilted = _rot_z(world, ast.OBLIQUITY)  # undo axisGroup.rotation.z
    local = _rot_y(tilted, -ast.spin_angle(lam, hours))  # undo mesh.rotation.y

    lat = np.degrees(np.arcsin(local[1]))
    lon = np.degrees(np.arctan2(-local[2], local[0]))

    assert lat == pytest.approx(declination_on(day_of_year), abs=1e-9)
    assert ast.wrap_longitude(lon - ast.subsolar_longitude(hours)) == pytest.approx(
        0.0, abs=1e-9
    )


def test_spin_axis_is_the_tilted_pole():
    assert np.degrees(np.arccos(ast.SPIN_AXIS[1])) == pytest.approx(ast.TROPIC_DEG)
    assert np.linalg.norm(ast.SPIN_AXIS) == pytest.approx(1.0)


# ------------------------------------------------------------- the terminator


def test_terminator_touches_the_polar_circles_at_a_solstice():
    assert ast.terminator_lat_deg(0, JUNE) == pytest.approx(-ast.POLAR_DEG, abs=0.01)
    assert ast.terminator_lat_deg(180, JUNE) == pytest.approx(ast.POLAR_DEG, abs=0.01)
    assert ast.terminator_lat_deg(90, JUNE) == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize("hour_angle", [-170, -95, -20, 15, 60, 140])
@pytest.mark.parametrize("day_of_year", [172, 355, 80, 250, 30])
def test_sun_sits_exactly_on_the_horizon_along_the_terminator(
    hour_angle, day_of_year
):
    """Swept across the year: a southern declination used to flip the curve."""
    dec = ast.solar_declination(ast.sun_ecliptic_longitude(day_of_year))
    lat = ast.terminator_lat_deg(hour_angle, dec)
    assert -90.0 <= lat <= 90.0
    assert ast.sun_elevation_deg(lat, hour_angle, 0.0, dec) == pytest.approx(
        0.0, abs=1e-9
    )


def test_terminator_stays_inside_the_pole_to_pole_range_all_year():
    hour_angle = np.arange(-180.0, 180.0, 1.0)[:, None]
    dec = ast.solar_declination(ast.sun_ecliptic_longitude(np.arange(0, 366, 1.0)))
    lat = ast.terminator_lat_deg(hour_angle, dec)
    assert np.all(np.abs(lat) <= 90.0 + 1e-9)


def test_night_falls_on_the_pole_the_sun_turns_away_from():
    """December: the Arctic is dark, so night is north of the terminator."""
    december = ast.solar_declination(ast.sun_ecliptic_longitude(355))
    assert ast.terminator_lat_deg(0, december) == pytest.approx(
        ast.POLAR_DEG, abs=0.01
    )
    assert ast.sun_elevation_deg(89.0, 0.0, 0.0, december) < 0
    assert ast.sun_elevation_deg(-89.0, 0.0, 0.0, december) > 0


@pytest.mark.parametrize("day_of_year", [172, 130, 80, 300, 355])
def test_curve_amplitude_is_ninety_minus_declination(day_of_year):
    """What the eye reads off the flat map.

    A broad wave grazing the polar circles at a solstice, steepening until at
    an equinox it stands up into two meridians through both poles.
    """
    dec = ast.solar_declination(ast.sun_ecliptic_longitude(day_of_year))
    hour_angle = np.arange(-180.0, 180.0, 0.05)
    amplitude = np.max(np.abs(ast.terminator_lat_deg(hour_angle, dec)))
    assert amplitude == pytest.approx(90.0 - abs(np.degrees(dec)), abs=0.01)


def test_equinox_stands_the_terminator_up_through_the_poles():
    hour_angle = np.arange(-180.0, 180.0, 0.05)
    lat = ast.terminator_lat_deg(hour_angle, 0.0)
    assert np.max(np.abs(lat)) == pytest.approx(90.0, abs=1e-9)
    # Every column is at one pole or the other: no wave in between. The two
    # meridians a quarter turn from the sun are the exception, since there the
    # terminator runs through every latitude at once.
    on_the_boundary = np.abs(np.cos(np.radians(hour_angle))) < 1e-12
    assert np.all(np.abs(np.abs(lat[~on_the_boundary]) - 90.0) < 1e-6)


# --------------------------------------------------------------- day length


def test_equator_always_gets_twelve_hours():
    assert ast.day_length_hours(0.0, JUNE) == pytest.approx(12.0)


def test_polar_day_and_polar_night():
    assert ast.day_length_hours(80.0, JUNE) == 24.0
    assert ast.day_length_hours(-80.0, JUNE) == 0.0
    assert ast.sunrise_sunset_hours(80.0, 0.0, JUNE) == (None, None)


def test_twelve_hours_everywhere_at_an_equinox():
    lat = np.arange(-80.0, 80.1, 5.0)
    assert ast.day_length_hours(lat, 0.0) == pytest.approx(12.0)


@pytest.mark.parametrize("lat", [-70.0, -35.0, 5.0, 45.0, 63.0])
def test_day_length_matches_counting_the_daylit_hours(lat):
    """Independent of the closed form: count how long the sun is actually up."""
    hours = np.linspace(0.0, 24.0, 200_001)[:-1] + 24.0 / 400_000
    elevation = ast.sun_elevation_deg(lat, 0.0, ast.subsolar_longitude(hours), JUNE)
    counted = np.count_nonzero(elevation > 0) * 24.0 / hours.size
    assert ast.day_length_hours(lat, JUNE) == pytest.approx(counted, abs=0.002)


def test_sunrise_and_sunset_bracket_the_day():
    rise, sets = ast.sunrise_sunset_hours(51.5, 0.0, JUNE)
    assert ast.sun_elevation_deg(51.5, 0.0, ast.subsolar_longitude(rise), JUNE) == (
        pytest.approx(0.0, abs=1e-9)
    )
    assert ast.sun_elevation_deg(51.5, 0.0, ast.subsolar_longitude(sets), JUNE) == (
        pytest.approx(0.0, abs=1e-9)
    )
    assert (sets - rise) % 24.0 == pytest.approx(
        float(ast.day_length_hours(51.5, JUNE)), abs=1e-9
    )


@pytest.mark.parametrize(
    ("lon", "subsolar_lon", "expected"), [(45, 45, 12.0), (90, 0, 18.0), (-90, 0, 6.0)]
)
def test_local_solar_time(lon, subsolar_lon, expected):
    assert ast.local_solar_time_hours(lon, subsolar_lon) == pytest.approx(expected)


# ------------------------------------------------- the tracks handed to the JS


def test_track_channels_are_unwrapped_so_the_js_can_lerp_them():
    """Interpolating across a wrap would swing the animation backwards."""
    day = day_track(172.0, (51.5, -0.1))
    assert np.all(np.diff(day["channels"]["spin"]) > 0)
    assert np.all(np.diff(day["channels"]["subsolar_lon"]) < 0)
    # Azimuth may pass 360 at high latitudes; it must never jump back.
    assert np.all(np.abs(np.diff(day["channels"]["sun_azimuth"])) < 180.0)
    assert np.all(np.diff(moon_track()["channels"]["elongation_deg"]) > 0)


def test_track_rejects_a_channel_of_the_wrong_length():
    """The contract the browser relies on, enforced where it is built."""
    with pytest.raises(ValueError, match="expected 3"):
        Track(t=[0.0, 1.0, 2.0], channels={"bad": [0.0, 1.0]})


def test_day_track_agrees_with_the_astronomy_it_was_built_from():
    track = day_track(80.0)
    lam = ast.sun_ecliptic_longitude(80.0)
    assert track["scalars"]["declination_deg"] == pytest.approx(declination_on(80.0))
    assert track["vectors"]["sun"][0] == pytest.approx(ast.sun_direction(lam))
    assert len(track["tables"]["terminator_lat"]["values"]) == 361
    for hours, spin in zip(track["t"], track["channels"]["spin"], strict=True):
        assert spin == pytest.approx(float(ast.spin_angle(lam, hours)))


def test_terminator_table_is_indexed_by_hour_angle_from_minus_180():
    tbl = day_track(172.0)["tables"]["terminator_lat"]
    for index in (0, 90, 180, 270, 360):
        expected = ast.terminator_lat_deg(tbl["start"] + index * tbl["step"], JUNE)
        assert tbl["values"][index] == pytest.approx(expected)


def test_sky_paths_appear_only_once_a_location_is_picked():
    assert day_track(172.0)["paths"] == {}
    assert day_track(172.0)["scalars"]["has_marker"] is False
    picked = day_track(172.0, (51.5, -0.1))
    assert set(picked["paths"]) == {"sky_today", "sky_june", "sky_december"}
    assert picked["scalars"]["has_marker"] is True


def test_sky_path_carries_azimuth_elevation_and_time():
    path = day_track(172.0, (51.5, -0.1))["paths"]["sky_today"]
    dec = ast.solar_declination(ast.sun_ecliptic_longitude(172.0))
    for azimuth, elevation, hours in path:
        assert 0.0 <= azimuth <= 360.0
        subsolar = ast.subsolar_longitude(hours)
        assert elevation == pytest.approx(
            float(ast.sun_elevation_deg(51.5, -0.1, subsolar, dec)), abs=1e-9
        )


def test_sky_path_crosses_the_horizon_at_sunrise_and_sunset():
    """What the timeline panel draws has to line up with the printed times."""
    dec = ast.solar_declination(ast.sun_ecliptic_longitude(172.0))
    rise, sets = ast.sunrise_sunset_hours(51.5, -0.1, dec)
    path = day_track(172.0, (51.5, -0.1))["paths"]["sky_today"]
    up = [h for _, elevation, h in path if elevation > 0]
    assert min(up) == pytest.approx(rise, abs=0.1)
    assert max(up) == pytest.approx(sets, abs=0.1)


def test_polar_day_leaves_the_sun_up_for_the_whole_path():
    path = day_track(172.0, (80.0, 0.0))["paths"]["sky_today"]
    assert all(elevation > 0 for _, elevation, _ in path)


def test_moon_track_covers_exactly_one_synodic_month():
    track = moon_track()
    assert track["t"][0] == 0.0
    assert track["t"][-1] == pytest.approx(ast.SYNODIC_MONTH)
    lit = track["channels"]["illuminated"]
    assert lit[0] == pytest.approx(0.0, abs=1e-9)
    assert max(lit) == pytest.approx(1.0, abs=1e-3)
    assert lit[-1] == pytest.approx(0.0, abs=1e-9)


def test_spanish_phase_names_switch_at_the_same_instants():
    """The banner and the readout must never disagree about the phase."""
    track = moon_track()
    english = track["steps"]["phase"]
    spanish = track["steps"]["phase_es"]
    assert len(english) == len(spanish)
    for (when_en, name_en), (when_es, name_es) in zip(english, spanish, strict=True):
        assert when_en == when_es
        assert name_es == PHASE_NAMES_ES[name_en]


def test_every_phase_has_a_spanish_name():
    from earthsim.labels import PHASE_NAMES

    assert set(PHASE_NAMES_ES) == set(PHASE_NAMES)
    for elongation in np.linspace(0, 2 * np.pi, 400):
        assert phase_name_es(elongation) == PHASE_NAMES_ES[phase_name(elongation)]


def test_moon_phase_steps_run_through_the_cycle_in_order():
    names = [name for _, name in moon_track()["steps"]["phase"]]
    assert names[0] == "New moon"
    assert names[:5] == [
        "New moon",
        "Waxing crescent",
        "First quarter",
        "Waxing gibbous",
        "Full moon",
    ]


def test_moon_orbit_tilt_keeps_most_full_moons_out_of_the_shadow():
    """The reason phases are not eclipses."""
    eclipsed = 0
    for node in range(0, 360, 5):
        lam = ast.sun_ecliptic_longitude(172.0)
        elongation = np.pi  # full moon
        beta = ast.moon_ecliptic_latitude(lam, elongation, np.radians(node))
        eclipsed += ast.lunar_eclipse_possible(beta, elongation)
    assert 0 < eclipsed < 72 * 0.3


def test_insolation_matches_the_textbook_figures():
    """Still used by the notebook's distance-versus-sunlight table."""
    equator_annual = ast.daily_insolation(0.0, np.arange(0, 365, 0.5)).mean()
    assert equator_annual == pytest.approx(416.0, abs=3.0)
    # The midsummer pole out-earns the equator, which surprises people.
    assert ast.daily_insolation(90.0, 172.0) == pytest.approx(524.0, abs=6.0)
    assert ast.daily_insolation(90.0, 172.0) > ast.daily_insolation(0.0, 172.0)
    assert ast.daily_insolation(90.0, 355.0) == 0.0


def test_year_track_grid_is_indexed_by_declination_and_local_hour():
    """The seasons panel reads rows as declination and columns as the clock."""
    track = year_track(45.0, 0.0)
    field = track["grids"]["sun_elevation"]
    values = np.array(field["values"]).reshape(field["rows"], field["cols"])
    declinations = field["row_start"] + np.arange(field["rows"]) * field["row_step"]
    hours = field["col_start"] + np.arange(field["cols"]) * field["col_step"]

    assert hours[0] == 0.0
    assert hours[-1] == pytest.approx(24.0)
    for row in (0, field["rows"] // 2, field["rows"] - 1):
        expected = ast.sun_elevation_local_deg(
            45.0, hours, np.radians(declinations[row])
        )
        assert values[row] == pytest.approx(expected, abs=0.01)


@pytest.mark.parametrize("longitude", [0.0, -75.0, 151.2, 180.0])
def test_the_globe_turns_the_chosen_place_towards_the_sun(longitude):
    """Undo the renderer's two rotations: the sun must land on the marker's
    meridian on every day of the year, so the face you look at is the lit one.
    """
    track = year_track(45.0, longitude)
    spin = np.array(track["channels"]["spin_marker_noon"])
    for index in range(0, len(track["t"]), 37):
        day = track["t"][index]
        lam = ast.sun_ecliptic_longitude(day)
        tilted = _rot_z(ast.sun_direction(lam), ast.OBLIQUITY)
        local = _rot_y(tilted, -spin[index])
        subsolar_lon = np.degrees(np.arctan2(-local[2], local[0]))
        assert ast.wrap_longitude(subsolar_lon - longitude) == pytest.approx(
            0.0, abs=1e-9
        )
        # The latitude is left free: that swing is the season.
        assert np.degrees(np.arcsin(local[1])) == pytest.approx(
            declination_on(day), abs=1e-9
        )


def test_marker_noon_spin_is_unwrapped_for_the_browser_to_lerp():
    """Right ascension goes round once a year; a wrap would jerk the globe."""
    spin = np.array(year_track(45.0, -75.0)["channels"]["spin_marker_noon"])
    assert np.all(np.diff(spin) > 0)
    assert float(np.max(spin) - np.min(spin)) == pytest.approx(2 * np.pi, abs=0.02)


def test_the_arch_swells_in_summer_and_shrinks_in_winter():
    """What the animation is for, stated as an assertion."""
    track = year_track(45.0, 0.0)
    field = track["grids"]["sun_elevation"]
    values = np.array(field["values"]).reshape(field["rows"], field["cols"])
    declinations = field["row_start"] + np.arange(field["rows"]) * field["row_step"]
    summer = values[int(np.argmin(np.abs(declinations - ast.TROPIC_DEG)))]
    winter = values[int(np.argmin(np.abs(declinations + ast.TROPIC_DEG)))]

    assert summer.max() == pytest.approx(90.0 - 45.0 + ast.TROPIC_DEG, abs=0.2)
    assert winter.max() == pytest.approx(90.0 - 45.0 - ast.TROPIC_DEG, abs=0.2)
    assert np.count_nonzero(summer > 0) > np.count_nonzero(winter > 0)


def test_a_polar_location_gets_a_day_with_no_sunset_and_one_with_no_sunrise():
    track = year_track(78.2, 15.6)
    field = track["grids"]["sun_elevation"]
    values = np.array(field["values"]).reshape(field["rows"], field["cols"])
    declinations = field["row_start"] + np.arange(field["rows"]) * field["row_step"]
    summer = values[int(np.argmin(np.abs(declinations - ast.TROPIC_DEG)))]
    winter = values[int(np.argmin(np.abs(declinations + ast.TROPIC_DEG)))]

    assert summer.min() > 0  # the sun never sets
    assert winter.max() < 0  # and never rises


def test_daylight_table_and_solstice_paths_line_up_with_the_grid():
    track = year_track(45.0, 0.0)
    tbl = track["tables"]["daylight_hours"]
    for index, value in enumerate(tbl["values"]):
        declination = np.radians(tbl["start"] + index * tbl["step"])
        assert value == pytest.approx(
            float(ast.day_length_hours(45.0, declination)), abs=0.01
        )
    for name, declination in (
        ("sun_june", ast.TROPIC_DEG),
        ("sun_december", -ast.TROPIC_DEG),
    ):
        for hour, elevation in track["paths"][name]:
            assert elevation == pytest.approx(
                float(ast.sun_elevation_local_deg(45.0, hour, np.radians(declination))),
                abs=1e-9,
            )


def test_date_label_names_the_season_boundaries():
    assert "June solstice" in date_label(172)
    assert "December solstice" in date_label(356)
    assert date_label(1).startswith("Jan 1")
    assert "solstice" not in date_label(200)


# ------------------------------------------------------------- 4. eclipses


def test_shadow_sizes_match_the_almanac():
    umbra, penumbra = ast.shadow_radius_km(ast.EARTH_RADIUS_KM, ast.MOON_DISTANCE_KM)
    assert umbra == pytest.approx(4600.0, abs=20.0)
    assert penumbra == pytest.approx(8175.0, abs=20.0)
    assert umbra / ast.MOON_RADIUS_KM == pytest.approx(2.65, abs=0.02)


def test_angular_radii_match_the_almanac():
    assert ast.angular_radius_deg(
        ast.MOON_RADIUS_KM, ast.MOON_DISTANCE_KM
    ) == pytest.approx(0.259, abs=0.002)
    assert ast.angular_radius_deg(ast.SUN_RADIUS_KM, ast.AU_KM) == pytest.approx(
        0.2666, abs=0.002
    )


def test_the_moons_shadow_only_just_reaches_us():
    """Why annular eclipses happen at all: at its mean distance the Moon's
    umbra closes to a point some 45 km short of Earth."""
    at_mean, _ = ast.shadow_radius_km(ast.MOON_RADIUS_KM, ast.MOON_DISTANCE_KM)
    at_perigee, _ = ast.shadow_radius_km(ast.MOON_RADIUS_KM, ast.MOON_PERIGEE_KM)
    at_apogee, _ = ast.shadow_radius_km(ast.MOON_RADIUS_KM, ast.MOON_APOGEE_KM)
    assert at_mean < 0
    assert at_perigee > 0  # totality, on a track about a hundred km wide
    assert at_apogee < at_mean


@pytest.mark.parametrize(
    ("distance", "expected"),
    [
        (ast.MOON_PERIGEE_KM, "total"),
        (ast.MOON_DISTANCE_KM, "annular"),
        (ast.MOON_APOGEE_KM, "annular"),
    ],
)
def test_a_dead_central_solar_eclipse_turns_on_distance(distance, expected):
    moon = ast.angular_radius_deg(ast.MOON_RADIUS_KM, distance)
    sun = ast.angular_radius_deg(ast.SUN_RADIUS_KM, ast.AU_KM)
    assert ast.solar_eclipse_kind(0.0, moon, sun) == expected


def test_one_degree_of_latitude_is_a_whole_earth_radius_off_the_axis():
    """The claim the edge-on panel is drawn to make."""
    offset_km = ast.MOON_DISTANCE_KM * np.radians(1.0)
    assert offset_km / ast.EARTH_RADIUS_KM == pytest.approx(1.05, abs=0.02)


def _closest_approach(node_offset_deg, span_hours=6.0):
    hours = np.linspace(-span_hours, span_hours, 4001)
    return float(
        np.min(
            ast.separation_deg(
                ast.syzygy_longitude_offset_deg(hours),
                ast.moon_ecliptic_latitude_at_node_offset(node_offset_deg, hours),
            )
        )
    )


def test_an_alignment_on_the_node_is_a_dead_central_eclipse():
    assert _closest_approach(0.0) == pytest.approx(0.0, abs=1e-6)


@pytest.mark.parametrize(
    ("node_offset", "expected"),
    [(0.0, "total"), (5.0, "partial"), (11.0, "penumbral"), (17.0, "none")],
)
def test_lunar_eclipses_fade_out_as_the_alignment_leaves_the_node(
    node_offset, expected
):
    """Drag away from the node and the eclipse degrades, then stops.

    The boundaries are read off the model, not asserted from memory: total out
    to about 4.7 degrees, umbral partial to 10.7, penumbral to 16.6.
    """
    umbra, penumbra = ast.shadow_radius_km(ast.EARTH_RADIUS_KM, ast.MOON_DISTANCE_KM)
    assert (
        ast.lunar_eclipse_kind(
            _closest_approach(node_offset),
            ast.angular_radius_deg(ast.MOON_RADIUS_KM, ast.MOON_DISTANCE_KM),
            ast.angular_radius_deg(umbra, ast.MOON_DISTANCE_KM),
            ast.angular_radius_deg(penumbra, ast.MOON_DISTANCE_KM),
        )
        == expected
    )


def test_the_latitude_grid_is_indexed_by_node_offset_then_time():
    track = eclipse_track("lunar")
    field = track["grids"]["latitude_deg"]
    values = np.array(field["values"]).reshape(field["rows"], field["cols"])
    offsets = field["row_start"] + np.arange(field["rows"]) * field["row_step"]
    hours = field["col_start"] + np.arange(field["cols"]) * field["col_step"]
    for row in (0, field["rows"] // 2, field["rows"] - 1):
        expected = ast.moon_ecliptic_latitude_at_node_offset(offsets[row], hours)
        assert values[row] == pytest.approx(expected, abs=1e-4)
    # Dead on the node, the Moon crosses zero latitude at the alignment.
    middle = int(np.argmin(np.abs(offsets)))
    assert values[middle][int(np.argmin(np.abs(hours)))] == pytest.approx(0.0, abs=1e-4)


def test_the_moon_actually_travels_across_the_shadow():
    """The side view once drew the Moon at a fixed z and only bobbed it up and
    down, so nothing appeared to happen. Almost all the crossing motion is
    *across* the shadow axis; the vertical part is a tenth of it."""
    track = eclipse_track("lunar")
    across = np.array(track["channels"]["moon_cross_re"])
    along = np.array(track["channels"]["moon_axis_re"])
    latitude = np.array(track["grids"]["latitude_deg"]["values"]).reshape(
        track["grids"]["latitude_deg"]["rows"], -1
    )
    on_node = int(track["grids"]["latitude_deg"]["rows"] // 2)
    vertical = latitude[on_node] * track["scalars"]["earth_radii_per_deg"]

    assert np.ptp(across) == pytest.approx(6.1, abs=0.3)
    assert np.ptp(across) > 8 * np.ptp(vertical)
    assert np.ptp(along) < 0.2  # the distance barely changes


def test_the_moon_track_position_is_consistent_with_its_distance():
    track = eclipse_track("lunar")
    scalars = track["scalars"]
    along = np.array(track["channels"]["moon_axis_re"])
    across = np.array(track["channels"]["moon_cross_re"])
    assert np.hypot(along, across) == pytest.approx(
        scalars["moon_distance_earth_radii"], abs=1e-9
    )
    # Dead on the alignment the Moon sits square on the axis.
    middle = len(along) // 2
    assert across[middle] == pytest.approx(0.0, abs=1e-9)


def test_eclipse_magnitude_reads_as_a_fraction_of_the_disc():
    moon = ast.angular_radius_deg(ast.MOON_RADIUS_KM, ast.MOON_DISTANCE_KM)
    sun = ast.angular_radius_deg(ast.SUN_RADIUS_KM, ast.AU_KM)
    assert ast.eclipse_magnitude(moon + sun, sun, moon) == pytest.approx(0.0)
    assert ast.eclipse_magnitude(0.0, sun, moon) > 0.9
    assert ast.eclipse_magnitude(99.0, sun, moon) == 0.0
