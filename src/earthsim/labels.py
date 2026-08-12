"""Turning numbers into the strings the notebook and the widgets display."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from .astronomy import solar_declination, sun_ecliptic_longitude, wrap_longitude

YEAR_DAYS = 365


def _season_days() -> dict[int, str]:
    """Locate the equinoxes and solstices from the orbit model itself.

    They are not hard-coded: the elliptical orbit is what decides where they
    land, so reading them back off the model keeps the labels honest.
    """
    days = np.arange(0.0, YEAR_DAYS, 0.005)
    dec = solar_declination(sun_ecliptic_longitude(days))
    rising = (dec[:-1] < 0) & (dec[1:] >= 0)
    falling = (dec[:-1] > 0) & (dec[1:] <= 0)
    return {
        int(round(days[:-1][rising][0])): "March equinox",
        int(round(days[:-1][falling][0])): "September equinox",
        int(round(days[int(np.argmax(dec))])): "June solstice",
        int(round(days[int(np.argmin(dec))])): "December solstice",
    }


SEASON_DAYS = _season_days()


def date_label(day_of_year: float) -> str:
    """``"Jun 21"``, tagged when it falls on a season boundary."""
    doy = int(round(day_of_year))
    stamp = date(2001, 1, 1) + timedelta(days=doy - 1)  # 2001 is not a leap year
    label = f"{stamp:%b} {stamp.day}"
    for event_doy, name in SEASON_DAYS.items():
        if abs(doy - event_doy) <= 1:
            return f"{label} — {name}"
    return label


def short_date(day_of_year: float) -> str:
    """``"Jun 21"``, with no season tag attached."""
    stamp = date(2001, 1, 1) + timedelta(days=int(round(day_of_year)) - 1)
    return f"{stamp:%b} {stamp.day}"


def hm(hours: float) -> str:
    """``13.5`` becomes ``"13:30"``."""
    total = round(float(hours) % 24.0 * 60.0)
    return f"{total // 60 % 24:02d}:{total % 60:02d}"


def duration(hours: float) -> str:
    """``16.63`` becomes ``"16 h 38 m"``."""
    total = round(float(hours) * 60.0)
    return f"{total // 60} h {total % 60:02d} m"


def lat_label(lat_deg: float) -> str:
    return f"{abs(float(lat_deg)):.1f}°{'N' if lat_deg >= 0 else 'S'}"


def lon_label(lon_deg: float) -> str:
    wrapped = float(wrap_longitude(lon_deg))
    return f"{abs(wrapped):.1f}°{'E' if wrapped >= 0 else 'W'}"


PHASE_NAMES = (
    "New moon",
    "Waxing crescent",
    "First quarter",
    "Waxing gibbous",
    "Full moon",
    "Waning gibbous",
    "Last quarter",
    "Waning crescent",
)

_CARDINAL_PHASES = ((0.0, "New moon"), (90.0, "First quarter"), (180.0, "Full moon"), (270.0, "Last quarter"))


def phase_name(elongation, cardinal_tolerance_deg: float = 6.0) -> str:
    """Name the phase from the Sun-Earth-Moon angle alone.

    The four cardinal phases are instants, so anything within a tolerance of
    one gets its name; everything else is a crescent or a gibbous.
    """
    angle = float(np.degrees(elongation)) % 360.0
    for centre, name in _CARDINAL_PHASES:
        gap = abs(angle - centre)
        if min(gap, 360.0 - gap) <= cardinal_tolerance_deg:
            return name
    if angle < 90.0:
        return "Waxing crescent"
    if angle < 180.0:
        return "Waxing gibbous"
    if angle < 270.0:
        return "Waning gibbous"
    return "Waning crescent"


#: Spanish names, in the order of PHASE_NAMES. Stored in ordinary case; the
#: widget puts them in capitals for display.
PHASE_NAMES_ES = {
    "New moon": "Luna nueva",
    "Waxing crescent": "Luna creciente",
    "First quarter": "Cuarto creciente",
    "Waxing gibbous": "Luna gibosa creciente",
    "Full moon": "Luna llena",
    "Waning gibbous": "Luna gibosa menguante",
    "Last quarter": "Cuarto menguante",
    "Waning crescent": "Luna menguante",
}


def phase_name_es(elongation, cardinal_tolerance_deg: float = 6.0) -> str:
    """The phase's Spanish name.

    Routed through :func:`phase_name` so the two languages can never disagree
    about which phase it is or when it changes.
    """
    return PHASE_NAMES_ES[phase_name(elongation, cardinal_tolerance_deg)]


_SEASON_AFTER = {
    "March equinox": "N spring / S autumn",
    "June solstice": "N summer / S winter",
    "September equinox": "N autumn / S spring",
    "December solstice": "N winter / S summer",
}


def season_name(day_of_year: float) -> str:
    """Which season the date falls in, named for both hemispheres at once."""
    marks = sorted(SEASON_DAYS.items())
    current = marks[-1][1]  # before the March equinox we are still in the last one
    for boundary, name in marks:
        if day_of_year >= boundary:
            current = name
    return _SEASON_AFTER[current]
