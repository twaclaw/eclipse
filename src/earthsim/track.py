"""The handoff from Python to the browser.

The widgets contain no astronomy. Python samples the motion for the period
being animated and ships a :class:`Track` - a bundle of plain numbers - and the
JavaScript only interpolates it and draws. A track is a few kilobytes of JSON,
so a slider change simply rebuilds one.

The one rule that keeps the JavaScript honest: **channels are unwrapped**. A
longitude runs 180 down to -180 rather than jumping the dateline, an azimuth
keeps climbing past 360. Linear interpolation is then always safe, and the
browser never has to know which quantities are angles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .astronomy import (
    ECCENTRICITY,
    ECLIPSE_LIMIT_DEG,
    PERIHELION_DOY,
    SYNODIC_MONTH,
    daily_insolation,
    day_length_hours,
    earth_position_au,
    earthshine,
    illuminated_fraction,
    moon_direction,
    moon_ecliptic_latitude,
    moon_elongation,
    solar_declination,
    spin_angle,
    TROPIC_DEG,
    subsolar_longitude,
    subsolar_longitude_raw,
    sun_azimuth_deg,
    sun_direction,
    sun_direction_in_moon_view,
    sun_distance_au,
    sun_ecliptic_longitude,
    sun_elevation_deg,
    sun_elevation_local_deg,
    sunrise_sunset_hours,
    terminator_lat_deg,
)
from .labels import date_label, phase_name, season_name, short_date


def _floats(values) -> list[float]:
    return [float(v) for v in np.asarray(values, float).ravel()]


def _vectors(values) -> list[list[float]]:
    array = np.asarray(values, float).reshape(-1, 3)
    return [[float(x), float(y), float(z)] for x, y, z in array]


def unwrapped_degrees(values) -> list[float]:
    """Strip the 360-degree jumps so the browser can lerp straight through."""
    return _floats(np.degrees(np.unwrap(np.radians(np.asarray(values, float)))))


def table(values, start: float, step: float, wrap: float | None = None) -> dict:
    """A regularly spaced lookup the JavaScript reads instead of computing."""
    return {
        "start": float(start),
        "step": float(step),
        "wrap": None if wrap is None else float(wrap),
        "values": _floats(values),
    }


def compact_steps(times, names) -> list[tuple[float, str]]:
    """Keep only the moments a label actually changes."""
    steps: list[tuple[float, str]] = []
    for when, name in zip(times, names, strict=True):
        if not steps or name != steps[-1][1]:
            steps.append((float(when), name))
    return steps


def grid(values, row_start, row_step, col_start, col_step, decimals=2) -> dict:
    """A 2-D field, drawn in the browser as an image."""
    array = np.round(np.asarray(values, float), decimals)
    rows, cols = array.shape
    return {
        "rows": rows,
        "cols": cols,
        "row_start": float(row_start),
        "row_step": float(row_step),
        "col_start": float(col_start),
        "col_step": float(col_step),
        "vmin": float(np.nanmin(array)),
        "vmax": float(np.nanmax(array)),
        "values": _floats(array),
    }


@dataclass
class Track:
    """Everything one animation needs, as numbers the browser can only read.

    ``channels`` and ``vectors`` are series sampled at ``t`` and interpolated.
    ``steps`` are labels that switch at a time rather than blending. ``tables``,
    ``grids`` and ``paths`` are precomputed shapes to draw.
    """

    t: list[float]
    channels: dict[str, list[float]] = field(default_factory=dict)
    vectors: dict[str, list[list[float]]] = field(default_factory=dict)
    steps: dict[str, list[tuple[float, str]]] = field(default_factory=dict)
    tables: dict[str, dict] = field(default_factory=dict)
    grids: dict[str, dict] = field(default_factory=dict)
    paths: dict[str, list[list[float]]] = field(default_factory=dict)
    scalars: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        count = len(self.t)
        for name, series in self.channels.items():
            if len(series) != count:
                raise ValueError(
                    f"channel {name!r} has {len(series)} samples, expected {count}"
                )
        for name, series in self.vectors.items():
            if len(series) != count:
                raise ValueError(
                    f"vector {name!r} has {len(series)} samples, expected {count}"
                )

    def payload(self) -> dict:
        return {
            "t": self.t,
            "channels": self.channels,
            "vectors": self.vectors,
            "steps": {k: [[float(a), b] for a, b in v] for k, v in self.steps.items()},
            "tables": self.tables,
            "grids": self.grids,
            "paths": self.paths,
            "scalars": self.scalars,
        }


# ------------------------------------------------------- 3. day and night


def _sky_path(lat_deg: float, lon_deg: float, day_of_year: float, samples=289):
    """The sun's track across one location's sky over a whole day.

    A polyline of ``[azimuth, elevation, hours]`` so the browser can draw it
    without knowing what any of the three numbers mean: the first two place the
    sun on a sky dome, the third puts it on a timeline. Points below the
    horizon are kept, and the panels clip them as each sees fit.
    """
    declination = solar_declination(sun_ecliptic_longitude(day_of_year))
    hours = np.linspace(0.0, 24.0, samples)
    subsolar = subsolar_longitude(hours)
    elevation = sun_elevation_deg(lat_deg, lon_deg, subsolar, declination)
    azimuth = sun_azimuth_deg(lat_deg, lon_deg, subsolar, declination)
    return [
        [float(a), float(e), float(h)]
        for a, e, h in zip(azimuth, elevation, hours, strict=True)
    ]


def day_track(
    day_of_year: float,
    marker: tuple[float, float] | None = None,
    samples: int = 145,
) -> dict:
    """One simulated day: how the globe turns and where the sun sits.

    The sun's direction and declination barely move in a day - about 0.4
    degrees of declination - so they are held fixed and only the rotation is
    sampled. When a location has been picked, the sun's path across that
    location's sky is sampled too.
    """
    lam = sun_ecliptic_longitude(day_of_year)
    declination = solar_declination(lam)
    hours = np.linspace(0.0, 24.0, samples)
    hour_angle = np.arange(-180.0, 180.0 + 1e-9, 1.0)
    sun = np.broadcast_to(sun_direction(lam), (samples, 3))

    track = Track(
        t=_floats(hours),
        channels={
            "spin": _floats(spin_angle(lam, hours)),
            "subsolar_lon": _floats(subsolar_longitude_raw(hours)),
        },
        vectors={"sun": _vectors(sun)},
        tables={
            "terminator_lat": table(
                terminator_lat_deg(hour_angle, declination),
                start=-180.0,
                step=1.0,
                wrap=360.0,
            )
        },
        scalars={
            "declination_deg": float(np.degrees(declination)),
            "date_label": date_label(day_of_year),
            "has_marker": marker is not None,
        },
    )

    if marker is not None:
        lat, lon = float(marker[0]), float(marker[1])
        subsolar = subsolar_longitude(hours)
        track.channels["sun_elevation"] = _floats(
            sun_elevation_deg(lat, lon, subsolar, declination)
        )
        track.channels["sun_azimuth"] = unwrapped_degrees(
            sun_azimuth_deg(lat, lon, subsolar, declination)
        )
        # Solstice arcs give the day's path something to be compared against.
        for name, doy in (("today", day_of_year), ("june", 172), ("december", 355)):
            track.paths[f"sky_{name}"] = _sky_path(lat, lon, doy)
        rise, sets = sunrise_sunset_hours(lat, lon, declination)
        track.scalars.update(
            marker_lat=lat,
            marker_lon=lon,
            sunrise_hours=rise,
            sunset_hours=sets,
            sunrise_azimuth=None
            if rise is None
            else float(
                sun_azimuth_deg(lat, lon, subsolar_longitude(rise), declination)
            ),
            sunset_azimuth=None
            if sets is None
            else float(
                sun_azimuth_deg(lat, lon, subsolar_longitude(sets), declination)
            ),
        )

    return track.payload()


# --------------------------------------------------------- 1. moon phases


def moon_track(
    day_of_year: float = 172.0,
    node_longitude_deg: float = 0.0,
    samples: int = 121,
) -> dict:
    """One synodic month, from new moon back to new moon.

    Time runs in days of the Moon's age. The sun's direction is sampled too,
    because it swings about 29 degrees while the Moon goes round once, and that
    lag is exactly why the synodic month is longer than the sidereal one.
    """
    age = np.linspace(0.0, SYNODIC_MONTH, samples)
    elongation = moon_elongation(age)
    lam = sun_ecliptic_longitude(day_of_year + age)
    node = np.radians(node_longitude_deg)
    beta = moon_ecliptic_latitude(lam, elongation, node)

    # Named on a finer grid than the animation samples, so the four cardinal
    # phases are not stepped over between frames.
    naming_age = np.linspace(0.0, SYNODIC_MONTH, 8 * samples)
    named = [phase_name(e) for e in moon_elongation(naming_age)]

    return Track(
        t=_floats(age),
        channels={
            "elongation_deg": unwrapped_degrees(np.degrees(elongation)),
            "illuminated": _floats(illuminated_fraction(elongation)),
            "earthshine": _floats(earthshine(elongation)),
            "ecliptic_lat_deg": _floats(np.degrees(beta)),
        },
        vectors={
            "moon_dir": _vectors(moon_direction(lam, elongation, beta)),
            "sun_dir": _vectors(sun_direction(lam)),
            "moon_view_sun": _vectors(sun_direction_in_moon_view(elongation)),
        },
        steps={"phase": compact_steps(naming_age, named)},
        scalars={
            "synodic_month": SYNODIC_MONTH,
            "eclipse_limit_deg": ECLIPSE_LIMIT_DEG,
            "node_longitude_deg": float(node_longitude_deg),
        },
    ).payload()


# ------------------------------------------------------------ 2. seasons


def year_track(
    latitude_deg: float = 45.0,
    longitude_deg: float = 0.0,
    samples: int = 366,
    declination_step: float = 0.5,
    hour_samples: int = 145,
) -> dict:
    """One orbit, and what it does to the sun's daily arc at one place.

    The orbit channels drive the 3-D panel. The rest is for the sun-path panel:
    a grid of the sun's height against local solar time, indexed by
    declination. Declination is what the date actually controls, and the same
    declination always produces the same arc, so one grid covers the whole year
    and the browser needs no trigonometry to animate it.
    """
    days = np.linspace(0.0, 365.0, samples)
    lam = sun_ecliptic_longitude(days)
    declination = solar_declination(lam)

    naming_days = np.arange(0.0, 365.0, 0.25)
    seasons = compact_steps(naming_days, [season_name(d) for d in naming_days])
    calendar = compact_steps(days, [short_date(d) for d in days])

    # Indexed by declination rather than date: the arc repeats when the sun
    # comes back to the same latitude, so half the year is free.
    dec_deg = np.arange(-24.0, 24.0 + 1e-9, declination_step)
    hours = np.linspace(0.0, 24.0, hour_samples)
    elevation = sun_elevation_local_deg(
        latitude_deg, hours[None, :], np.radians(dec_deg)[:, None]
    )
    daylight = day_length_hours(latitude_deg, np.radians(dec_deg))

    solstice = np.radians(TROPIC_DEG)
    envelope = {
        "sun_june": sun_elevation_local_deg(latitude_deg, hours, solstice),
        "sun_december": sun_elevation_local_deg(latitude_deg, hours, -solstice),
    }

    return Track(
        t=_floats(days),
        channels={
            "declination_deg": _floats(np.degrees(declination)),
            "distance_au": _floats(sun_distance_au(days)),
            # Turns the globe so the chosen place sits at local noon, which is
            # what keeps its hemisphere the one facing the sun all year.
            # Unwrapped: right ascension goes round once over the year.
            "spin_marker_noon": _floats(
                np.unwrap(spin_angle(lam, (180.0 - longitude_deg) / 15.0))
            ),
        },
        vectors={
            "earth_pos": _vectors(earth_position_au(days)),
            "sun_dir": _vectors(sun_direction(lam)),
        },
        steps={"season": seasons, "date": calendar},
        tables={
            "daylight_hours": table(daylight, start=-24.0, step=declination_step),
        },
        grids={
            "sun_elevation": grid(
                elevation,
                row_start=-24.0,
                row_step=declination_step,
                col_start=0.0,
                col_step=24.0 / (hour_samples - 1),
                decimals=2,
            ),
        },
        paths={
            name: [[float(h), float(e)] for h, e in zip(hours, values, strict=True)]
            for name, values in envelope.items()
        },
        scalars={
            "latitude_deg": float(latitude_deg),
            "longitude_deg": float(longitude_deg),
            "eccentricity": float(ECCENTRICITY),
            "obliquity_deg": float(TROPIC_DEG),
            "perihelion_doy": float(PERIHELION_DOY),
            "aphelion_doy": 186.0,
        },
    ).payload()
