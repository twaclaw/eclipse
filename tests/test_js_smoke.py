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
import shutil
import subprocess
from pathlib import Path

import pytest

from earthsim.widgets import DayNightWidget, MoonPhasesWidget, SeasonsWidget

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
    assert smoke["moonphases_paused"]["transport"] == "▶"


@requires_node
def test_every_slider_gets_wired_up(smoke):
    """An unbound slider leaves its readout blank, a missing one reads None."""
    seasons = smoke["seasons"]["readouts"]
    assert seasons["speed"] == "30 d/s"
    assert seasons["light"] == "1.00 ×"
    assert seasons["sunlight"] == "0.70 ×"

    moon = smoke["moonphases"]["readouts"]
    assert moon["speed"] == "1.50 d/s"
    assert moon["light"] == "1.00 ×"
    assert moon["sunlight"] is None, "the moon has no sun-brightness control"


@requires_node
def test_day_and_night_has_no_control_strip(smoke):
    """Guards the fake DOM as much as the code: it has to be able to say that
    something is absent, or a control that was never rendered would pass here
    and throw in a browser."""
    assert smoke["daynight"]["transport"] is None
    assert smoke["daynight"]["readouts"]["speed"] is None


@requires_node
def test_the_transport_actually_drives_the_orbit(smoke):
    """Reading the speed wrongly would advance the date by NaN, silently."""
    running = smoke["seasons"]["clocks"]
    assert len(set(running)) > 1, "the date never advanced"
    assert all("NaN" not in c and c.strip() for c in running)

    paused = smoke["seasons_paused"]["clocks"]
    assert len(set(paused)) == 1, "paused, yet the date moved"

    moon = smoke["moonphases"]["clocks"]
    assert len(set(moon)) > 1, "the moon's age never advanced"
    assert all("NaN" not in c for c in moon)
    assert len(set(smoke["moonphases_paused"]["clocks"])) == 1
