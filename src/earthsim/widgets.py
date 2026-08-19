"""anywidget wrappers.

These hold no astronomy either. A widget's job is to carry a track across to
the browser and relay a handful of display switches; everything numeric is
computed in :mod:`earthsim.astronomy` and packed by :mod:`earthsim.track`.

Each widget bundles ``earthkit.js`` with its own drawing module, so the shared
toolkit - track interpolation, the day/night shader, orbit controls - exists
once and is reused by all three animations.
"""

from __future__ import annotations

import pathlib

import anywidget
import numpy as np
import traitlets

from .astronomy import (
    OBLIQUITY,
    POLARIS_POLE_SEPARATION_DEG,
    celestial_pole_altitude_deg,
    polaris_altitude_range_deg,
    pole_star_is_up,
)
from .track import transit_view, day_track, eclipse_track, moon_track, year_track

_STATIC = pathlib.Path(__file__).parent / "static"
_CSS = (_STATIC / "widget.css").read_text()

OBLIQUITY_DEG = float(np.degrees(OBLIQUITY))


def _bundle(*names: str) -> str:
    """Concatenate JS files into the single ES module anywidget expects."""
    return "\n".join((_STATIC / name).read_text() for name in names)


class _Base(anywidget.AnyWidget):
    _css = _CSS

    #: The sampled motion; see :mod:`earthsim.track`.
    track = traitlets.Dict().tag(sync=True)
    obliquity_deg = traitlets.Float(OBLIQUITY_DEG).tag(sync=True)
    playing = traitlets.Bool(True).tag(sync=True)
    speed = traitlets.Float(2.0).tag(sync=True)


class DayNightWidget(_Base):
    """Animation 3: spinning globe, flat-map terminator, and a local sky."""

    _esm = _bundle("earthkit.js", "daynight.js")

    day_of_year = traitlets.Float(172.0)
    #: Half-width of the twilight band, in degrees of sun elevation.
    twilight_deg = traitlets.Float(6.0)

    utc_hour = traitlets.Float(12.0).tag(sync=True)
    show_lights = traitlets.Bool(True).tag(sync=True)
    show_graticule = traitlets.Bool(True).tag(sync=True)
    show_sky = traitlets.Bool(True).tag(sync=True)
    #: ``twilight_deg`` as a cosine, ready to hand straight to the shader.
    twilight_cos = traitlets.Float(0.1).tag(sync=True)
    #: ``[lat, lon]`` of the location the user picked, or empty.
    marker = traitlets.List(traitlets.Float(), default_value=[]).tag(sync=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rebuild()
        self.twilight_cos = float(np.sin(np.radians(self.twilight_deg)))

    @property
    def location(self) -> tuple[float, float] | None:
        """The picked location as ``(lat, lon)``, or ``None``."""
        return (self.marker[0], self.marker[1]) if len(self.marker) == 2 else None

    def _rebuild(self) -> None:
        self.track = day_track(self.day_of_year, self.location)

    @traitlets.observe("day_of_year", "marker")
    def _on_geometry(self, _change) -> None:
        # The sky panel needs the sun's path for the chosen spot, so the track
        # depends on the marker as well as the date.
        self._rebuild()

    @traitlets.observe("twilight_deg")
    def _on_twilight(self, change) -> None:
        self.twilight_cos = float(np.sin(np.radians(change["new"])))


class MoonPhasesWidget(_Base):
    """Animation 1: the system from above, and the Moon as it looks from here."""

    _esm = _bundle("earthkit.js", "moonphases.js")

    day_of_year = traitlets.Float(172.0)
    #: Where the Moon's tilted orbit crosses the ecliptic, in degrees.
    node_longitude_deg = traitlets.Float(0.0)

    age_days = traitlets.Float(0.0).tag(sync=True)
    #: Brightness of the Moon's sunlit face. Driven from inside the widget.
    brightness = traitlets.Float(1.0).tag(sync=True)
    show_earthshine = traitlets.Bool(True).tag(sync=True)
    #: The Moon looks upside down from the far side of the equator.
    southern_view = traitlets.Bool(False).tag(sync=True)

    def __init__(self, **kwargs):
        kwargs.setdefault("speed", 1.5)
        super().__init__(**kwargs)
        self._rebuild()

    def _rebuild(self) -> None:
        self.track = moon_track(self.day_of_year, self.node_longitude_deg)

    @traitlets.observe("day_of_year", "node_longitude_deg")
    def _on_geometry(self, _change) -> None:
        self._rebuild()


class SeasonsWidget(_Base):
    """Animation 2: the orbit, the fixed axis, and one place's daily sunlight."""

    _esm = _bundle("earthkit.js", "seasons.js")

    day_of_year = traitlets.Float(0.0).tag(sync=True)
    #: 1.0 is the true orbit. Anything more is a deliberate exaggeration.
    eccentricity_stretch = traitlets.Float(1.0).tag(sync=True)
    follow_earth = traitlets.Bool(False).tag(sync=True)
    show_graticule = traitlets.Bool(False).tag(sync=True)
    #: Brightness of Earth's sunlit face. Driven from inside the widget.
    brightness = traitlets.Float(1.0).tag(sync=True)
    #: Brightness of the sun itself. Also driven from inside the widget.
    sun_brightness = traitlets.Float(0.7).tag(sync=True)
    #: ``[lat, lon]`` of the place the sun-path panel is drawn for.
    marker = traitlets.List(traitlets.Float(), default_value=[45.0, 0.0]).tag(
        sync=True
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("speed", 30.0)
        super().__init__(**kwargs)
        self._rebuild()

    @property
    def location(self) -> tuple[float, float]:
        """The chosen place as ``(lat, lon)``."""
        return (self.marker[0], self.marker[1])

    def _rebuild(self) -> None:
        # The sun-path grid is computed for one latitude, so picking a new
        # place rebuilds it. Only happens on a click.
        self.track = year_track(*self.location)

    @traitlets.observe("marker")
    def _on_marker(self, _change) -> None:
        self._rebuild()


class EclipsesWidget(_Base):
    """Animation 4: why an alignment only sometimes becomes an eclipse."""

    _esm = _bundle("earthkit.js", "eclipses.js")

    #: "lunar" or "solar". Changing it rebuilds the track.
    kind = traitlets.Unicode("lunar")
    #: The Moon's distance decides whether a central solar eclipse is total or
    #: annular, so it is worth being able to move.
    moon_distance_km = traitlets.Float(365_000.0)

    #: How far the alignment sits from the Moon's orbital node. Driven from
    #: inside the widget: latitude ships as a grid over this, so dragging it
    #: needs no round trip.
    node_offset_deg = traitlets.Float(0.0).tag(sync=True)
    #: How far the to-scale side view is zoomed in, 1 being the whole system.
    side_zoom = traitlets.Float(5.0).tag(sync=True)
    #: Where the time scrubber sits, in hours either side of the alignment.
    hours = traitlets.Float(0.0).tag(sync=True)

    def __init__(self, **kwargs):
        # Slow by default: an eclipse takes hours, and the interesting part is
        # the shadow creeping rather than the clock running.
        kwargs.setdefault("speed", 0.25)
        super().__init__(**kwargs)
        self._rebuild()

    def _rebuild(self) -> None:
        self.track = eclipse_track(self.kind, self.moon_distance_km)

    @traitlets.observe("kind", "moon_distance_km")
    def _on_geometry(self, _change) -> None:
        self._rebuild()


class LunarEclipseWidget(EclipsesWidget):
    """Earth's shadow crossing the Moon.

    Shares its engine with the solar one - the same geometry seen from the
    other end - with the kind fixed so a notebook need not ask.
    """

    kind = traitlets.Unicode("lunar")


class SolarEclipseWidget(EclipsesWidget):
    """The Moon's shadow crossing us."""

    kind = traitlets.Unicode("solar")


class LatitudeWidget(_Base):
    """Animation 6: your latitude, and the height of the pole star.

    Globe and map are two views of one choice - clicking either moves both -
    and the diagram argues why the angle overhead is the angle underfoot.
    """

    _esm = _bundle("earthkit.js", "latitude.js")

    latitude = traitlets.Float(51.5).tag(sync=True)
    longitude = traitlets.Float(-0.1).tag(sync=True)
    #: Everything the diagram prints, worked out in Python.
    readout = traitlets.Dict().tag(sync=True)

    def __init__(self, **kwargs):
        kwargs.setdefault("playing", False)
        super().__init__(**kwargs)
        self._rebuild()

    @traitlets.observe("latitude")
    def _on_latitude(self, _change) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        self.readout = self.summary()

    def summary(self) -> dict:
        """What is true at the chosen latitude, in words and numbers."""
        lat = float(self.latitude)
        altitude = float(celestial_pole_altitude_deg(lat))
        low, high = polaris_altitude_range_deg(lat)
        up = pole_star_is_up(lat)
        if up:
            headline = f"Polaris stands about {altitude:.1f}° above your horizon."
        elif lat == 0:
            headline = "On the equator the pole sits exactly on the horizon."
        else:
            headline = (
                f"Polaris is {abs(altitude):.1f}° below your horizon — "
                "never visible from here."
            )
        return {
            "latitude_deg": lat,
            "longitude_deg": float(self.longitude),
            "pole_altitude_deg": altitude,
            "polaris_low_deg": low,
            "polaris_high_deg": high,
            "polaris_separation_deg": POLARIS_POLE_SEPARATION_DEG,
            "visible": up,
            "headline": headline,
        }


class TransitWidget(_Base):
    """Animation 7: the transit of Venus, and the scale of the solar system."""

    _esm = _bundle("earthkit.js", "transit.js")

    #: Separation of the two observers, projected across the line of sight.
    baseline_km = traitlets.Float(8_000.0).tag(sync=True)
    #: How far the nearer chord runs from the sun's centre, in arcseconds.
    impact_arcsec = traitlets.Float(400.0).tag(sync=True)
    #: How sharply each contact can be timed.
    timing_seconds = traitlets.Float(10.0).tag(sync=True)
    #: The real gap between the chords is 3% of the sun's radius. This widens
    #: it for the drawing only; 1 is the truth.
    gap_boost = traitlets.Float(6.0).tag(sync=True)
    hours = traitlets.Float(0.0).tag(sync=True)

    #: Everything both panels draw; see :func:`earthsim.track.transit_view`.
    view = traitlets.Dict().tag(sync=True)

    def __init__(self, **kwargs):
        kwargs.setdefault("playing", False)
        super().__init__(**kwargs)
        self._rebuild()

    @traitlets.observe("baseline_km", "impact_arcsec", "timing_seconds")
    def _on_setup(self, _change) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        self.view = transit_view(
            self.baseline_km, self.impact_arcsec, self.timing_seconds
        )
