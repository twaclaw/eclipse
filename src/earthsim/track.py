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
    AU_KM,
    EARTH_RADIUS_KM,
    ECCENTRICITY,
    ECLIPSE_LIMIT_DEG,
    MOON_RADIUS_KM,
    PERIHELION_DOY,
    SUN_RADIUS_KM,
    SYNODIC_MONTH,
    TROPIC_DEG,
    AU_KM,
    VENUS_SEMI_MAJOR_AU,
    angular_radius_deg,
    au_from_chord_separation,
    chord_separation_arcsec,
    eclipse_magnitude,
    impact_uncertainty_arcsec,
    daily_insolation,
    day_length_hours,
    earth_position_au,
    earthshine,
    illuminated_fraction,
    moon_direction,
    moon_ecliptic_latitude,
    lunar_eclipse_kind,
    moon_ecliptic_latitude_at_node_offset,
    moon_elongation,
    separation_deg,
    shadow_radius_km,
    solar_eclipse_kind,
    solar_declination,
    spin_angle,
    subsolar_longitude,
    subsolar_longitude_raw,
    sun_azimuth_deg,
    sun_direction,
    sun_direction_in_moon_view,
    sun_distance_au,
    sun_ecliptic_longitude,
    sun_elevation_deg,
    sun_elevation_local_deg,
    sun_angular_radius_arcsec,
    sunrise_sunset_hours,
    syzygy_longitude_offset_deg,
    transit_duration_hours,
    transit_rate_arcsec_per_hour,
    terminator_lat_deg,
    venus_angular_radius_arcsec,
)
from .labels import (
    PHASE_NAMES_ES,
    date_label,
    phase_name,
    season_name,
    short_date,
)


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
        steps={
            "phase": compact_steps(naming_age, named),
            # Same instants, other language: built from the same list so the
            # two can never fall out of step.
            "phase_es": compact_steps(
                naming_age, [PHASE_NAMES_ES[name] for name in named]
            ),
        },
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


# ------------------------------------------------------------- 4. eclipses


def eclipse_track(
    kind: str = "lunar",
    moon_distance_km: float = 365_000.0,
    span_hours: float = 6.0,
    samples: int = 241,
    node_span_deg: float = 12.0,
    node_step_deg: float = 0.5,
) -> dict:
    """A few hours either side of an alignment, for every node offset at once.

    Latitude arrives as a grid indexed by how far the alignment sits from the
    Moon's orbital node, so that control can be dragged live without Python
    rebuilding anything. That matters here: sliding off the node until the
    eclipse fails is the whole lesson.
    """
    hours = np.linspace(-span_hours, span_hours, samples)
    delta_lon = syzygy_longitude_offset_deg(hours)
    offsets = np.arange(-node_span_deg, node_span_deg + 1e-9, node_step_deg)
    latitude = moon_ecliptic_latitude_at_node_offset(offsets[:, None], hours[None, :])

    moon_radius = float(angular_radius_deg(MOON_RADIUS_KM, moon_distance_km))
    sun_radius = float(angular_radius_deg(SUN_RADIUS_KM, AU_KM))
    umbra_km, penumbra_km = shadow_radius_km(EARTH_RADIUS_KM, moon_distance_km)
    moon_umbra_km, moon_penumbra_km = shadow_radius_km(
        MOON_RADIUS_KM, moon_distance_km
    )
    # Where the Moon's own shadow closes to a point. Short of Earth and the
    # eclipse can only be annular.
    apex_km = MOON_RADIUS_KM * AU_KM / (SUN_RADIUS_KM - MOON_RADIUS_KM)

    return Track(
        t=_floats(hours),
        channels={
            "dlon_deg": _floats(delta_lon),
            # Where the Moon actually is, in Earth radii: along the shadow's
            # axis, and across it in the plane of Earth's orbit. The crossing
            # motion is almost all in "cross" - which is why an edge-on view
            # shows so little of it, and the view has to be turned.
            "moon_axis_re": _floats(
                moon_distance_km / EARTH_RADIUS_KM * np.cos(np.radians(delta_lon))
            ),
            "moon_cross_re": _floats(
                -moon_distance_km / EARTH_RADIUS_KM * np.sin(np.radians(delta_lon))
            ),
        },
        grids={
            "latitude_deg": grid(
                latitude,
                row_start=-node_span_deg,
                row_step=node_step_deg,
                col_start=-span_hours,
                col_step=2.0 * span_hours / (samples - 1),
                decimals=4,
            )
        },
        scalars={
            "kind": kind,
            "span_hours": float(span_hours),
            "moon_distance_km": float(moon_distance_km),
            "moon_radius_deg": moon_radius,
            "sun_radius_deg": sun_radius,
            "umbra_radius_deg": float(
                angular_radius_deg(umbra_km, moon_distance_km)
            ),
            "penumbra_radius_deg": float(
                angular_radius_deg(penumbra_km, moon_distance_km)
            ),
            # The side view is drawn to scale vertically, in Earth radii.
            "earth_radii_per_deg": float(
                moon_distance_km * np.radians(1.0) / EARTH_RADIUS_KM
            ),
            "umbra_earth_radii": float(umbra_km / EARTH_RADIUS_KM),
            "penumbra_earth_radii": float(penumbra_km / EARTH_RADIUS_KM),
            "moon_earth_radii": float(MOON_RADIUS_KM / EARTH_RADIUS_KM),
            "moon_umbra_earth_radii": float(moon_umbra_km / EARTH_RADIUS_KM),
            "moon_penumbra_earth_radii": float(moon_penumbra_km / EARTH_RADIUS_KM),
            "moon_umbra_apex_fraction": float(apex_km / moon_distance_km),
            "moon_distance_earth_radii": float(moon_distance_km / EARTH_RADIUS_KM),
            "moon_umbra_apex_earth_radii": float(apex_km / EARTH_RADIUS_KM),
            "earth_umbra_apex_earth_radii": float(
                EARTH_RADIUS_KM * AU_KM / (SUN_RADIUS_KM - EARTH_RADIUS_KM)
                / EARTH_RADIUS_KM
            ),
        },
    ).payload()


def eclipse_summary(track: dict, node_offset_deg: float) -> dict:
    """What the eclipse comes to at its deepest, for a given node offset.

    Both eclipse notebooks print the same verdict, so it is worked out once
    here rather than twice in markdown. The window is scanned rather than
    solved: greatest eclipse is not quite at the moment of alignment once the
    Moon is climbing away from the node.
    """
    scalars = track["scalars"]
    span = scalars["span_hours"]
    hours = np.linspace(-span, span, 2001)
    gap = separation_deg(
        syzygy_longitude_offset_deg(hours),
        moon_ecliptic_latitude_at_node_offset(node_offset_deg, hours),
    )
    closest = float(np.min(gap))
    moon_radius = scalars["moon_radius_deg"]

    if scalars["kind"] == "lunar":
        verdict = lunar_eclipse_kind(
            closest,
            moon_radius,
            scalars["umbra_radius_deg"],
            scalars["penumbra_radius_deg"],
        )
        covered, covering = moon_radius, scalars["umbra_radius_deg"]
        inside = gap < scalars["umbra_radius_deg"] + moon_radius
        during = "in Earth's umbra"
    else:
        verdict = solar_eclipse_kind(
            closest, moon_radius, scalars["sun_radius_deg"]
        )
        covered, covering = scalars["sun_radius_deg"], moon_radius
        inside = gap < scalars["sun_radius_deg"] + moon_radius
        during = "with the sun partly hidden"

    return {
        "kind": scalars["kind"],
        "node_offset_deg": float(node_offset_deg),
        "latitude_deg": float(
            moon_ecliptic_latitude_at_node_offset(node_offset_deg)
        ),
        "closest_deg": closest,
        "verdict": verdict,
        "magnitude": eclipse_magnitude(closest, covered, covering),
        "duration_hours": float(np.count_nonzero(inside)) * (hours[1] - hours[0]),
        "during": during,
    }


# ------------------------------------------------------ 7. transit of Venus


def transit_view(
    baseline_km: float = 8_000.0,
    impact_arcsec: float = 400.0,
    timing_seconds: float = 10.0,
) -> dict:
    """One transit as two observers a baseline apart would time it.

    Everything the two panels draw and everything the notebook prints, worked
    out here. The last three entries are the payoff: an absolute distance in
    kilometres, recovered from an angle and a baseline, and how well you would
    know it given how sharply you can time a contact.
    """
    radius = sun_angular_radius_arcsec()
    separation = chord_separation_arcsec(baseline_km)
    near = float(impact_arcsec)
    far = near + separation

    durations = [transit_duration_hours(near), transit_duration_hours(far)]
    blur = np.hypot(
        impact_uncertainty_arcsec(near, timing_seconds),
        impact_uncertainty_arcsec(far, timing_seconds),
    )
    recovered = au_from_chord_separation(baseline_km, separation)
    # Infinity is not JSON, and a trait has to cross to the browser as JSON.
    # An unmeasurable case travels as null and is described in words instead.
    usable = separation > 0 and bool(np.isfinite(blur))
    error = float(blur / separation) if usable else None
    longest = max(durations) or 1.0

    if not durations[0] or not durations[1]:
        headline = (
            "One of the two chords misses the sun altogether, so there is "
            "nothing to compare."
        )
    elif error is None:
        headline = (
            "A chord straight across the middle barely changes length when it "
            "shifts sideways, so its timing says almost nothing about where "
            "it is. The method needs chords well off centre."
        )
    else:
        headline = (
            f"Timing each contact to {timing_seconds:.0f} s puts the "
            f"astronomical unit within {error * 100:.1f}% - "
            f"{recovered * error / 1e6:,.1f} million km either way."
        )

    return {
        "baseline_km": float(baseline_km),
        "sun_radius_arcsec": radius,
        "venus_radius_arcsec": venus_angular_radius_arcsec(),
        "rate_arcsec_per_hour": transit_rate_arcsec_per_hour(),
        "impact_arcsec": [near, far],
        "duration_hours": durations,
        "duration_gap_minutes": abs(durations[0] - durations[1]) * 60.0,
        "separation_arcsec": separation,
        "separation_fraction": separation / radius,
        "orbit_ratio": VENUS_SEMI_MAJOR_AU,
        "timing_seconds": float(timing_seconds),
        "span_hours": longest * 0.62,
        "au_km": recovered,
        "au_true_km": AU_KM,
        "au_error_fraction": error,
        "measurable": usable and all(durations),
        "headline": headline,
    }
