"""Where the sun is, relative to a rotating and tilted Earth.

One reference frame is used by every animation in this project:

* the world *xz* plane is the ecliptic, and world *+y* is ecliptic north;
* Earth's spin axis is **fixed** in that frame, tilted by the obliquity towards
  *+x*, because the axis keeps pointing at Polaris all year;
* ``lam`` is the sun's ecliptic longitude measured from the June solstice, so
  ``lam = 0`` puts the sun on the side the axis leans towards.

That single choice is what makes one tilted axis produce a different solar
declination as the year advances, which is the mechanism behind the seasons.

Angles are radians unless a name says ``_deg``. Times are apparent solar hours:
the equation of time is deliberately ignored, so 12:00 always means the sun is
on the Greenwich meridian.
"""

from __future__ import annotations

import numpy as np

OBLIQUITY = np.radians(23.4392811)
TROPIC_DEG = 23.4392811
POLAR_DEG = 90.0 - TROPIC_DEG

YEAR = 365.2422
ECCENTRICITY = 0.016708
PERIHELION_DOY = 3.5  # Earth is closest to the sun in early January
PERIHELION_LON = np.radians(282.946)  # sun's longitude then, from the March equinox

#: Unit vector along Earth's spin axis, fixed in the world frame.
SPIN_AXIS = np.array([np.sin(OBLIQUITY), np.cos(OBLIQUITY), 0.0])


# --------------------------------------------------------------------- orbit


def mean_anomaly(day_of_year):
    return 2.0 * np.pi * (np.asarray(day_of_year, float) - PERIHELION_DOY) / YEAR


def eccentric_anomaly(mean_anom):
    """Solve Kepler's equation ``M = E - e sin E`` by Newton iteration."""
    ecc_anom = np.array(mean_anom, dtype=float, copy=True)
    for _ in range(6):
        ecc_anom -= (ecc_anom - ECCENTRICITY * np.sin(ecc_anom) - mean_anom) / (
            1.0 - ECCENTRICITY * np.cos(ecc_anom)
        )
    return ecc_anom


def true_anomaly(day_of_year):
    ecc_anom = eccentric_anomaly(mean_anomaly(day_of_year))
    return 2.0 * np.arctan2(
        np.sqrt(1.0 + ECCENTRICITY) * np.sin(ecc_anom / 2.0),
        np.sqrt(1.0 - ECCENTRICITY) * np.cos(ecc_anom / 2.0),
    )


def sun_distance_au(day_of_year):
    """Earth-sun distance in AU. The orbit is an ellipse, not a circle."""
    return 1.0 - ECCENTRICITY * np.cos(
        eccentric_anomaly(mean_anomaly(day_of_year))
    )


def sun_ecliptic_longitude(day_of_year):
    """Sun's ecliptic longitude, measured from the June solstice.

    Because the orbit is elliptical the sun does not advance at a constant
    rate, and that is what puts the equinoxes on their real calendar dates.
    """
    return true_anomaly(day_of_year) + PERIHELION_LON - np.pi / 2.0


# ----------------------------------------------------------------- sun angles


def sun_direction(lam):
    """Unit vector from Earth towards the sun, in world coordinates."""
    lam = np.asarray(lam, float)
    return np.stack([np.cos(lam), np.zeros_like(lam), -np.sin(lam)], axis=-1)


def solar_declination(lam):
    """Latitude directly under the sun. Swings between the two tropics."""
    return np.arcsin(np.sin(OBLIQUITY) * np.cos(lam))


def sun_right_ascension(lam):
    """Angle the spin has to make up so the subsolar meridian lands on time."""
    return np.arctan2(np.sin(lam), np.cos(lam) * np.cos(OBLIQUITY))


def spin_angle(lam, hours):
    """Rotation of the globe that puts the subsolar meridian at ``hours``.

    Follows from ``subsolar_longitude = right_ascension - spin``; see
    ``tests/test_astronomy.py``, which re-derives it by undoing the rotations
    the renderer actually applies.
    """
    return sun_right_ascension(lam) - (np.pi - np.radians(15.0 * np.asarray(hours, float)))


def subsolar_longitude_raw(hours):
    """Longitude under the sun, degrees east, left unwrapped.

    Unwrapped so it can be linearly interpolated without jumping the dateline.
    """
    return 180.0 - 15.0 * np.asarray(hours, float)


def subsolar_longitude(hours):
    """Longitude under the sun, degrees east, wrapped to [-180, 180)."""
    return wrap_longitude(subsolar_longitude_raw(hours))


def wrap_longitude(lon_deg):
    return (np.asarray(lon_deg, float) + 180.0) % 360.0 - 180.0


# ------------------------------------------------------------ on the surface


def terminator_lat_deg(hour_angle_deg, declination):
    """Latitude of the day/night boundary at a given hour angle.

    The hour angle is longitude measured from the subsolar meridian, so this
    curve is the same shape all day and simply slides west. Its extremes reach
    ``90 - |declination|``: a broad wave at a solstice, and two straight
    meridians through the poles at an equinox.
    """
    tan_dec = np.tan(declination)
    # tan(lat) = -cos(H) / tan(dec), but taken through arctan2 so that a zero
    # declination lands on the poles instead of dividing by zero. The
    # denominator is forced positive to keep the result inside (-90, 90): with a
    # negative declination arctan2 would otherwise hand back a "latitude" beyond
    # the pole and flip the whole curve.
    sign = np.where(tan_dec < 0.0, -1.0, 1.0)
    return np.degrees(
        np.arctan2(-np.cos(np.radians(hour_angle_deg)) * sign, np.abs(tan_dec))
    )


def sun_elevation_deg(lat_deg, lon_deg, subsolar_lon_deg, declination):
    """Angle of the sun above the horizon, degrees. Negative means night."""
    lat = np.radians(lat_deg)
    hour_angle = np.radians(np.asarray(lon_deg, float) - subsolar_lon_deg)
    sin_elev = np.sin(lat) * np.sin(declination) + np.cos(lat) * np.cos(
        declination
    ) * np.cos(hour_angle)
    return np.degrees(np.arcsin(np.clip(sin_elev, -1.0, 1.0)))


def _half_day_angle_deg(lat_deg, declination):
    """Hour angle of sunset, degrees, or nan under midnight sun/polar night."""
    cos_h = -np.tan(np.radians(lat_deg)) * np.tan(declination)
    return np.where(np.abs(cos_h) > 1.0, np.nan, np.degrees(np.arccos(np.clip(cos_h, -1.0, 1.0))))


def day_length_hours(lat_deg, declination):
    """Hours of daylight, geometric: sun's centre, no atmospheric refraction."""
    cos_h = -np.tan(np.radians(lat_deg)) * np.tan(declination)
    hours = 2.0 * np.degrees(np.arccos(np.clip(cos_h, -1.0, 1.0))) / 15.0
    return np.where(cos_h <= -1.0, 24.0, np.where(cos_h >= 1.0, 0.0, hours))


def sunrise_sunset_hours(lat_deg, lon_deg, declination):
    """Sunrise and sunset in solar time UTC, or ``None`` if the sun never sets.

    Returns ``(rise, set)``; both are ``None`` during midnight sun or polar
    night, which is exactly when the day length saturates at 24 or 0.
    """
    half = _half_day_angle_deg(lat_deg, declination)
    if np.isnan(half):
        return None, None
    noon_utc = (12.0 - np.asarray(lon_deg, float) / 15.0) % 24.0
    return (
        float((noon_utc - half / 15.0) % 24.0),
        float((noon_utc + half / 15.0) % 24.0),
    )


def local_solar_time_hours(lon_deg, subsolar_lon_deg):
    """Clock reading of a sundial at this longitude, hours."""
    return float((12.0 + wrap_longitude(lon_deg - subsolar_lon_deg) / 15.0) % 24.0)


# ------------------------------------------------------------- the local sky


def sun_azimuth_deg(lat_deg, lon_deg, subsolar_lon_deg, declination):
    """Compass bearing of the sun: degrees clockwise from north.

    0 is north, 90 east, 180 south, 270 west. Paired with
    :func:`sun_elevation_deg` this is where the sun actually is in somebody's
    sky, which is what turns a terminator into a sunrise.
    """
    lat = np.radians(lat_deg)
    hour_angle = np.radians(np.asarray(lon_deg, float) - subsolar_lon_deg)
    east = -np.cos(declination) * np.sin(hour_angle)
    north = np.sin(declination) * np.cos(lat) - np.cos(declination) * np.sin(
        lat
    ) * np.cos(hour_angle)
    return np.degrees(np.arctan2(east, north)) % 360.0


def noon_elevation_deg(lat_deg, declination):
    """How high the sun climbs at its best moment of the day."""
    return 90.0 - np.abs(np.asarray(lat_deg, float) - np.degrees(declination))


SOLAR_CONSTANT = 1361.0  # W/m^2 at 1 AU


def daily_insolation(lat_deg, day_of_year):
    """Daily mean sunlight at the top of the atmosphere, W/m^2.

    Combines the two things the tilt controls - how high the sun gets and how
    long it stays up - into the single number the seasons actually run on. The
    distance term is in here too, which is what makes it possible to show that
    distance is *not* what drives them.
    """
    lam = sun_ecliptic_longitude(day_of_year)
    declination = solar_declination(lam)
    distance = np.asarray(sun_distance_au(day_of_year), float)
    lat = np.radians(np.asarray(lat_deg, float))
    half_day = np.arccos(np.clip(-np.tan(lat) * np.tan(declination), -1.0, 1.0))
    flux = (SOLAR_CONSTANT / np.pi) * distance**-2.0 * (
        half_day * np.sin(lat) * np.sin(declination)
        + np.cos(lat) * np.cos(declination) * np.sin(half_day)
    )
    return np.maximum(flux, 0.0)


def earth_position_au(day_of_year):
    """Earth's position relative to the sun, in AU, in world coordinates."""
    lam = sun_ecliptic_longitude(day_of_year)
    distance = np.asarray(sun_distance_au(day_of_year), float)
    return -sun_direction(lam) * distance[..., None]


# ------------------------------------------------------------------ the Moon

SYNODIC_MONTH = 29.530588853  # new moon to new moon
SIDEREAL_MONTH = 27.321661  # one orbit measured against the stars
MOON_INCLINATION = np.radians(5.145)
MOON_DISTANCE_KM = 384_400.0
MOON_RADIUS_KM = 1_737.4
EARTH_RADIUS_KM = 6_371.0

#: Angular radius of Earth's umbra at the Moon's distance, plus the Moon's own
#: radius: roughly how close to the ecliptic a full moon must be to be eclipsed.
ECLIPSE_LIMIT_DEG = 0.70 + 0.259


def moon_elongation(age_days):
    """Angle Sun-Earth-Moon, growing eastward. 0 is new moon, pi is full."""
    return 2.0 * np.pi * np.asarray(age_days, float) / SYNODIC_MONTH


def illuminated_fraction(elongation):
    """Fraction of the Moon's disc that is lit, as seen from Earth.

    Note what this does *not* depend on: Earth's shadow. The Moon is always
    half lit by the sun, and the phase is only how much of that lit half
    happens to face us.
    """
    return (1.0 - np.cos(np.asarray(elongation, float))) / 2.0


def moon_ecliptic_latitude(lam, elongation, node_longitude=0.0):
    """How far the Moon sits above or below the plane of Earth's orbit.

    The orbit is tilted 5.1 degrees and crosses the plane at two nodes, which
    is why most full moons sail clear of Earth's shadow instead of being
    eclipsed by it.
    """
    argument = np.asarray(lam, float) + np.asarray(elongation, float) - node_longitude
    return np.arcsin(np.sin(MOON_INCLINATION) * np.sin(argument))


def moon_direction(lam, elongation, ecliptic_latitude=0.0):
    """Unit vector from Earth towards the Moon, in world coordinates."""
    angle = np.asarray(lam, float) + np.asarray(elongation, float)
    beta = np.asarray(ecliptic_latitude, float)
    flat = np.cos(beta)
    return np.stack(
        [flat * np.cos(angle), np.sin(beta) * np.ones_like(angle), -flat * np.sin(angle)],
        axis=-1,
    )


def sun_direction_in_moon_view(elongation):
    """Sun's direction in the frame where the Moon's near side faces +z.

    The Moon keeps one face turned towards us, so the view never changes; only
    the lighting swings around it, and that swing *is* the phase cycle. At
    ``elongation = 0`` the sun is behind the Moon and the disc is dark; at
    ``pi`` it is behind us and the disc is full.
    """
    e = np.asarray(elongation, float)
    return np.stack([np.sin(e), np.zeros_like(e), -np.cos(e)], axis=-1)


def earthshine(elongation):
    """Brightness of the ashen glow on the Moon's dark side, 0 to 1.

    Earth and Moon show each other complementary phases, so the dark side is
    lit best when the Moon itself is a thin crescent.
    """
    return 1.0 - illuminated_fraction(elongation)


def lunar_eclipse_possible(ecliptic_latitude, elongation):
    """Whether this full moon is close enough to a node to be eclipsed."""
    near_full = np.abs(np.degrees(np.asarray(elongation, float)) % 360.0 - 180.0) < 15.0
    near_plane = np.abs(np.degrees(ecliptic_latitude)) < ECLIPSE_LIMIT_DEG
    return bool(np.all(near_full & near_plane))


def sun_elevation_local_deg(lat_deg, local_solar_hours, declination):
    """Sun's height above the horizon, against the local sundial clock.

    Local solar time puts noon under the sun by definition, so the shape of
    this curve depends only on latitude and declination - longitude merely
    shifts the whole thing along the clock. That is what lets one table serve
    a location for the entire year.
    """
    hour_angle_deg = (np.asarray(local_solar_hours, float) - 12.0) * 15.0
    return sun_elevation_deg(lat_deg, hour_angle_deg, 0.0, declination)
