"""Does the browser code actually run?

The contract tests check that the JavaScript reads a track correctly. These
check something cruder and, it turns out, just as necessary: that ``render()``
completes and can draw frames at all. A three.js stub and a fake DOM stand in
for the browser, so a temporal dead zone, a misspelled property or a reference
to something that no longer exists fails here instead of blanking a panel.

Nothing about appearance is verified. Only that no line throws.

Skipped when node is not installed.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from earthsim.widgets import (
    DayNightWidget,
    LatitudeWidget,
    LunarEclipseWidget,
    MoonPhasesWidget,
    SeasonsWidget,
    SolarEclipseWidget,
    TransitWidget,
)

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "src" / "earthsim" / "static"
DRIVER = Path(__file__).parent / "js" / "smoke_driver.mjs"

node = shutil.which("node")
requires_node = pytest.mark.skipif(node is None, reason="node is not installed")


def widget_state(widget) -> dict:
    """The synced traits the browser reads.

    Skips ipywidgets' own plumbing (``layout``, ``tooltip``) and the ``_esm`` /
    ``_css`` payloads, which are either unserializable or enormous and which
    the animation code never asks the model for.
    """
    state = {}
    for name in widget.trait_names():
        if name.startswith("_") or not widget.trait_metadata(name, "sync"):
            continue
        value = getattr(widget, name)
        try:
            json.dumps(value)
        except TypeError:
            continue
        state[name] = value
    return state


def build_runs() -> list[dict]:
    picked = DayNightWidget()
    picked.marker = [51.5, -0.1]
    polar = DayNightWidget(day_of_year=172.0)
    polar.marker = [78.2, 15.6]  # Svalbard: the sun never sets in June
    return [
        {
            "name": "daynight",
            "modules": ["earthkit.js", "daynight.js"],
            "state": widget_state(DayNightWidget()),
        },
        {
            "name": "daynight_with_location",
            "modules": ["earthkit.js", "daynight.js"],
            "state": widget_state(picked),
        },
        {
            "name": "daynight_polar_day",
            "modules": ["earthkit.js", "daynight.js"],
            "state": widget_state(polar),
        },
        {
            "name": "moonphases",
            "modules": ["earthkit.js", "moonphases.js"],
            "state": widget_state(MoonPhasesWidget()),
            "frames": 30,
        },
        {
            "name": "moonphases_paused",
            "modules": ["earthkit.js", "moonphases.js"],
            "state": widget_state(MoonPhasesWidget(playing=False)),
            "frames": 30,
        },
        {
            "name": "moonphases_southern",
            "modules": ["earthkit.js", "moonphases.js"],
            "state": widget_state(MoonPhasesWidget(southern_view=True)),
        },
        {
            "name": "seasons",
            "modules": ["earthkit.js", "seasons.js"],
            "state": widget_state(SeasonsWidget()),
            "frames": 30,
        },
        {
            "name": "seasons_paused",
            "modules": ["earthkit.js", "seasons.js"],
            "state": widget_state(SeasonsWidget(playing=False)),
            "frames": 30,
        },
        {
            "name": "seasons_polar_location",
            "modules": ["earthkit.js", "seasons.js"],
            "state": widget_state(
                SeasonsWidget(marker=[78.2, 15.6], eccentricity_stretch=8.0)
            ),
        },
        {
            "name": "seasons_southern_location",
            "modules": ["earthkit.js", "seasons.js"],
            "state": widget_state(SeasonsWidget(marker=[-33.9, 151.2])),
        },
        {
            "name": "latitude_north",
            "modules": ["earthkit.js", "latitude.js"],
            "state": widget_state(LatitudeWidget()),
        },
        {
            "name": "latitude_globe_click",
            "modules": ["earthkit.js", "latitude.js"],
            "state": widget_state(LatitudeWidget()),
            "click": {"selector": ".es-c3d", "x": 400, "y": 200},
        },
        {
            "name": "latitude_map_click",
            "modules": ["earthkit.js", "latitude.js"],
            "state": widget_state(LatitudeWidget()),
            "click": {"selector": ".es-c2d", "x": 675, "y": 105},
        },
        {
            "name": "latitude_equator",
            "modules": ["earthkit.js", "latitude.js"],
            "state": widget_state(LatitudeWidget(latitude=0.0)),
        },
        {
            "name": "latitude_south",
            "modules": ["earthkit.js", "latitude.js"],
            "state": widget_state(LatitudeWidget(latitude=-33.9, longitude=151.2)),
        },
        {
            "name": "latitude_pole",
            "modules": ["earthkit.js", "latitude.js"],
            "state": widget_state(LatitudeWidget(latitude=90.0)),
        },
        {
            "name": "transit_default",
            "modules": ["earthkit.js", "transit.js"],
            "state": widget_state(TransitWidget()),
        },
        {
            # A phone: no Element.requestFullscreen anywhere in sight.
            "name": "daynight_no_fullscreen_api",
            "modules": ["earthkit.js", "daynight.js"],
            "state": widget_state(DayNightWidget()),
            "fullscreen_api": False,
            "press_fullscreen": True,
        },
        {
            "name": "transit_central",
            "modules": ["earthkit.js", "transit.js"],
            "state": widget_state(TransitWidget(impact_arcsec=0.0)),
        },
        {
            "name": "transit_grazing",
            "modules": ["earthkit.js", "transit.js"],
            "state": widget_state(TransitWidget(impact_arcsec=950.0)),
        },
        {
            "name": "eclipse_lunar",
            "modules": ["earthkit.js", "eclipses.js"],
            "state": widget_state(LunarEclipseWidget()),
            "frames": 30,
        },
        {
            "name": "eclipse_lunar_missed",
            "modules": ["earthkit.js", "eclipses.js"],
            "state": widget_state(LunarEclipseWidget(node_offset_deg=11.0)),
        },
        {
            "name": "eclipse_solar_total",
            "modules": ["earthkit.js", "eclipses.js"],
            "state": widget_state(SolarEclipseWidget(moon_distance_km=363300.0)),
            "frames": 30,
        },
        {
            "name": "eclipse_zoomed_out",
            "modules": ["earthkit.js", "eclipses.js"],
            "state": widget_state(LunarEclipseWidget(side_zoom=1.0)),
        },
        {
            "name": "eclipse_zoomed_in",
            "modules": ["earthkit.js", "eclipses.js"],
            "state": widget_state(LunarEclipseWidget(side_zoom=24.0)),
        },
        {
            "name": "eclipse_solar_annular",
            "modules": ["earthkit.js", "eclipses.js"],
            "state": widget_state(SolarEclipseWidget(moon_distance_km=405500.0)),
        },
        {
            "name": "seasons_following_earth",
            "modules": ["earthkit.js", "seasons.js"],
            "state": widget_state(SeasonsWidget(follow_earth=True)),
        },
    ]


@pytest.fixture(scope="module")
def smoke(tmp_path_factory):
    if node is None:
        pytest.skip("node is not installed")
    spec = {"runs": build_runs()}
    payload = tmp_path_factory.mktemp("smoke") / "spec.json"
    payload.write_text(json.dumps(spec))
    result = subprocess.run(
        [node, str(DRIVER), str(STATIC), str(payload)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


@requires_node
@pytest.mark.parametrize("name", [run["name"] for run in build_runs()])
def test_animation_renders_frames_without_throwing(smoke, name):
    record = smoke[name]
    assert record["ok"], f"{name} failed:\n{record.get('error', 'no frames drawn')}"
    assert record["frames"] >= 4


@requires_node
def test_the_clock_gets_written_every_frame(smoke):
    """A frame that throws part-way leaves the readout empty."""
    assert smoke["daynight"]["clock"].endswith("solar")
    assert smoke["moonphases"]["clock"].startswith("day ")
    assert smoke["seasons"]["clock"]


@requires_node
def test_the_transport_control_gets_wired_up(smoke):
    """An unwired button leaves its label blank."""
    assert smoke["seasons"]["transport"] == "❙❙"
    assert smoke["seasons_paused"]["transport"] == "▶"
    assert smoke["moonphases"]["transport"] == "❙❙"
    assert smoke["eclipse_lunar"]["transport"] == "❙❙"
    assert smoke["daynight"]["transport"] == "❙❙"
    assert smoke["moonphases_paused"]["transport"] == "▶"


@requires_node
def test_every_slider_gets_wired_up(smoke):
    """An unbound slider leaves its readout blank, a missing one reads None."""
    seasons = smoke["seasons"]["readouts"]
    assert seasons["speed"] == "30 d/s"
    assert seasons["light"] == "1.00 ×"
    assert seasons["sunlight"] == "0.70 ×"

    eclipse = smoke["eclipse_lunar"]["readouts"]
    assert eclipse["speed"] == "0.25 h/s"
    assert eclipse["node"] == "0.0 °"
    assert eclipse["zoom"] == "5.0 ×"

    moon = smoke["moonphases"]["readouts"]
    assert moon["speed"] == "1.50 d/s"
    assert moon["light"] == "1.00 ×"
    assert moon["sunlight"] is None, "the moon has no sun-brightness control"


@requires_node
def test_the_spanish_phase_name_is_shown(smoke):
    """Blank here means the banner never got its text."""
    from earthsim.labels import PHASE_NAMES_ES

    assert smoke["moonphases"]["bigname"] in PHASE_NAMES_ES.values()
    assert smoke["daynight"]["bigname"] is None


@requires_node
def test_the_side_view_reports_how_much_is_in_frame(smoke):
    """The to-scale strip is only honest if it says what scale it is at."""
    wide = smoke["eclipse_zoomed_out"]["scale"]
    close = smoke["eclipse_zoomed_in"]["scale"]
    assert "Earth radii across" in wide
    assert "Earth radii across" in close
    assert int(wide.split()[0]) > int(close.split()[0])
    assert smoke["daynight"]["scale"] is None


@requires_node
def test_the_fake_dom_can_still_report_something_absent(smoke):
    """Guards the harness as much as the code: it has to be able to say that
    something is absent, or a control that was never rendered would pass here
    and throw in a browser."""
    assert smoke["daynight"]["readouts"]["node"] is None
    assert smoke["daynight"]["scale"] is None
    assert smoke["moonphases"]["readouts"]["sunlight"] is None


@requires_node
@pytest.mark.parametrize(
    ("name", "pattern"),
    [
        ("daynight", r"^\d{2}:\d{2} solar$"),
        ("seasons", r"^day \d+$"),
        ("moonphases", r"^day \d+\.\d$"),
        ("eclipse_lunar", r"^[+\u2212]\d{2}:\d{2}$"),
    ],
)
def test_every_animation_has_a_time_scrubber(name, pattern, smoke):
    assert re.match(pattern, smoke[name]["readouts"]["when"] or ""), (
        f"{name} scrubber reads {smoke[name]['readouts']['when']!r}"
    )


@requires_node
def test_the_scrubber_follows_playback_and_stops_when_paused(smoke):
    """The handle has to track the clock, or it is just a second control that
    disagrees with the animation."""
    assert smoke["seasons"]["readouts"]["when"] != "day 0"
    assert smoke["moonphases"]["readouts"]["when"] != "day 0.0"
    assert smoke["seasons_paused"]["readouts"]["when"] == "day 0"
    assert smoke["moonphases_paused"]["readouts"]["when"] == "day 0.0"


@requires_node
def test_the_transport_actually_drives_the_orbit(smoke):
    """Reading the speed wrongly would advance the date by NaN, silently."""
    running = smoke["seasons"]["clocks"]
    assert len(set(running)) > 1, "the date never advanced"
    assert all("NaN" not in c and c.strip() for c in running)

    paused = smoke["seasons_paused"]["clocks"]
    assert len(set(paused)) == 1, "paused, yet the date moved"

    for name in ("eclipse_lunar", "eclipse_solar_total"):
        ticks = smoke[name]["clocks"]
        assert len(set(ticks)) > 1, f"{name} never advanced"
        assert all("NaN" not in c for c in ticks)

    moon = smoke["moonphases"]["clocks"]
    assert len(set(moon)) > 1, "the moon's age never advanced"
    assert all("NaN" not in c for c in moon)
    assert len(set(smoke["moonphases_paused"]["clocks"])) == 1


@requires_node
def test_the_latitude_panel_shows_where_you_picked(smoke):
    """The clock corner is the only confirmation that a click landed."""
    assert smoke["latitude_north"]["clock"] == "51.5°N"
    assert smoke["latitude_south"]["clock"] == "33.9°S"
    assert smoke["latitude_pole"]["clock"] == "90.0°N"
    assert smoke["latitude_north"]["readouts"]["lat"] == "51.5 °"


@requires_node
def test_clicking_the_globe_lands_where_it_was_aimed(smoke):
    """The stub puts the ray's hit at 30N 45E, so that is where the marker has
    to end up. Anything else means the world-to-local conversion is wrong."""
    click = smoke["latitude_globe_click"]["click"]
    assert click["latitude"] == pytest.approx(30.0, abs=0.02)
    assert click["longitude"] == pytest.approx(45.0, abs=0.02)


@requires_node
def test_globe_picking_ignores_the_lines_drawn_on_it(smoke):
    """The graticule, the parallel and the pin are all children of the globe,
    and three's line intersections use a world-space threshold of 1 - vast
    against a sphere of radius 1. Recursive picking snapped every click to the
    nearest 30-degree line."""
    assert smoke["latitude_globe_click"]["click"]["recursive"] is False


@requires_node
def test_clicking_the_flat_map_lands_where_it_was_aimed(smoke):
    """The fake canvas reports 900x420 at the origin, so three quarters across
    and a quarter down is 90E, 45N."""
    click = smoke["latitude_map_click"]["click"]
    assert click["longitude"] == pytest.approx(90.0, abs=1.0)
    assert click["latitude"] == pytest.approx(45.0, abs=1.0)


@requires_node
@pytest.mark.parametrize(
    "name",
    ["daynight", "moonphases", "seasons", "eclipse_lunar", "latitude_north",
     "transit_default"],
)
def test_every_animation_offers_full_screen(name, smoke):
    """marimo's app mode strips the cell chrome, so the expand control has to
    come from the widget or the published pages have none at all."""
    label = smoke[name]["fullscreen"]
    assert label.startswith("\u2922")
    # In words as well as in glyph: the icon on its own was too easy to miss.
    assert "Full screen" in label
    assert smoke[name]["fullscreenHidden"] is False


@requires_node
def test_full_screen_works_without_the_fullscreen_api(smoke):
    """iOS Safari has no Element.requestFullscreen - only a video can go full
    screen there - so the button hid itself on exactly the device with the
    least screen to spare. It pins the widget over the page instead."""
    run = smoke["daynight_no_fullscreen_api"]
    assert run["fullscreenHidden"] is False
    assert "es-blown" in run["blown"]
    assert run["fullscreenPressed"].startswith("\u2715")
