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

from .astronomy import OBLIQUITY
from .track import day_track, eclipse_track, moon_track, year_track

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
