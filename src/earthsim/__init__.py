"""Animations of the Earth-Moon-Sun system for marimo notebooks.

The split is deliberate: :mod:`earthsim.astronomy` holds every equation and is
covered by the test suite, :mod:`earthsim.track` samples those equations into
plain tables, and the JavaScript under ``static/`` only interpolates and draws.
"""

from .labels import date_label, phase_name, season_name
from .track import (
    day_track,
    eclipse_summary,
    eclipse_track,
    moon_track,
    year_track,
)
from .widgets import (
    DayNightWidget,
    EclipsesWidget,
    LatitudeWidget,
    LunarEclipseWidget,
    MoonPhasesWidget,
    SeasonsWidget,
    SolarEclipseWidget,
)

__all__ = [
    "DayNightWidget",
    "EclipsesWidget",
    "LatitudeWidget",
    "LunarEclipseWidget",
    "MoonPhasesWidget",
    "SeasonsWidget",
    "SolarEclipseWidget",
    "date_label",
    "day_track",
    "eclipse_summary",
    "eclipse_track",
    "moon_track",
    "phase_name",
    "season_name",
    "year_track",
]
