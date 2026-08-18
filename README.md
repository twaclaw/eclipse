# Earth simulations

Animations of the Earth-Moon-Sun system, served from a marimo notebook.

| notebook | shows |
|---|---|
| `01_moon_phases.py` | the Moon is always half lit; the phase is how much of that half faces us |
| `02_seasons.py` | one axis, fixed in space, and how it stretches and shrinks a chosen place's day |
| `03_day_and_night.py` | rotation, the terminator on a flat map, and the sun's path over one place |
| `04_lunar_eclipse.py` | Earth's shadow crossing the Moon, and why it usually misses |
| `05_solar_eclipse.py` | the Moon's shadow crossing us, and why it is often a ring |

```sh
uv run marimo edit notebooks/
uv run pytest
```

## How it is put together

The one rule worth knowing: **Python owns every equation, JavaScript owns
pixels.**

```
earthsim/astronomy.py   Kepler, declination, terminator, day length, insolation,
                        horizontal coordinates, the Moon
earthsim/labels.py      names for phases, seasons and dates
earthsim/track.py       samples all of it into a few kB of plain numbers
earthsim/widgets.py     carries a track across to the browser
earthsim/static/
  earthkit.js           track interpolation, the day/night shader, orbit
                        controls - shared by all three animations
  daynight.js           \
  moonphases.js          \  one drawing module
  seasons.js             /  per animation
  eclipses.js           /   (both eclipse notebooks share this one)
```

The browser never re-derives a number. It receives a track table - sample
times plus a channel per quantity - interpolates it, and renders. That keeps
the astronomy under `pytest`, and it means the JavaScript has no notion of
dates, axial tilt or orbits, so there is only one place a physics bug can hide.

A track is one shape for all three animations: `channels` and `vectors` are
series sampled at `t` and interpolated, `steps` are labels that switch rather
than blend, and `tables`, `grids` and `paths` are precomputed shapes to draw.

Three things follow from that split and are worth preserving:

* **Track channels are unwrapped.** `subsolar_lon` runs 180 down to -180
  without jumping the dateline and an azimuth keeps climbing past 360, so the
  JavaScript can lerp anything blindly.
* **The terminator ships as a lookup table** indexed by hour angle. The curve
  keeps its shape all day and only slides west, so one table covers the whole
  animation and the JS needs no trigonometry.
* **Labels are computed in Python too.** Phase names, season names and dates
  arrive as `steps`, so the browser never has to decide what a gibbous moon is.
* **Grids are indexed by the quantity, not the date.** The seasons sun-path
  grid is indexed by solar declination, because the same declination always
  produces the same daily arc - so half the year is free, and the browser
  animates it by interpolating rows.

Play, speed, brightness and the time scrubber live inside the animations, not
in the notebook, so they stay reachable when a panel is maximised. The
scrubber runs with the clock and can be dragged against it: the render loop
pushes the time in, and that push is ignored while the handle is held. That is also the only
arrangement that works: a notebook cell pushing those values down would re-run
on every change the widget made and overwrite it. Everything a widget does
*not* write back - dates, toggles, the moon's node longitude - stays a marimo
control.

Two suites cover the browser half without a browser, both skipped if node is
missing:

* `tests/test_js_contract.py` runs the real JavaScript through node and checks
  what it reads out of a track against the real Python - including the sun
  curve, point for point.
* `tests/test_js_smoke.py` runs each animation's actual `render()` against a
  three.js stub and a fake DOM and pumps frames, so a reference error or a
  temporal dead zone fails here rather than blanking a panel.

## Rendering

three.js draws the globe: a real equirectangular NASA texture on a sphere, with
a fragment shader blending the daylight map into the city-lights map across a
twilight band. Textures load from a CDN.

Plotly was considered and dropped. `go.Surface` only takes a one-dimensional
colorscale, which makes the continents mono-tinted, and `go.Mesh3d` needs six
figures of vertices before coastlines stop looking blocky.

## What the animations argue

Each one is built against a common misconception, because that is usually what
the picture is for:

* Phases are **not** Earth's shadow. That is a lunar eclipse, it is rare, and
  the notebook lets you move the orbit's nodes to see why.
* Seasons are **not** distance. Earth is closest to the sun in early January.
  The eccentricity control starts at the true value - a circle, near enough -
  and has to be exaggerated on purpose.
* At an equinox the terminator does **not** flatten onto the equator; it stands
  up into two meridians through the poles. It is roundest at the solstices.
* Eclipses are **not** rare because alignments are rare - those happen monthly.
  They are rare because the Moon's orbit is tilted, so most alignments miss by
  a degree or so, which is a whole Earth radius at that distance.

## Accuracy

The orbit is a real ellipse solved through Kepler's equation, so the equinoxes
and solstices land within about half a day of their true dates and declination
tracks the almanac to roughly 0.2°. Those dates are found by reading the model
back, not hard-coded - see `earthsim.labels.SEASON_DAYS`.

Insolation is the daily mean at the top of the atmosphere and reproduces the
textbook values: 416 W/m² annual mean at the equator, and 524 W/m² at the north
pole on the June solstice, which is more than the equator gets that day.

Eclipse geometry falls out of the same two-body picture: Earth's umbra works
out at 4600 km across at the Moon's distance and its penumbra at 8175 km, both
matching the almanac, and the Moon's own umbra closes about 45 km short of
Earth at mean distance - which is why annular eclipses are slightly the more
common kind. The solar view is geocentric, so the parallax that makes totality
a narrow track rather than a hemisphere is not modelled.

Deliberately left out: the equation of time, the gap between the solar and
sidereal day, atmospheric refraction, and the sun's angular radius. Day lengths
are therefore geometric and run a few minutes shorter than an almanac's
sunrise tables. The Moon's orbit is a circle at a fixed 5.145° inclination with
the node longitude exposed as a control rather than tied to a real date, so
animation 1 is a faithful cycle rather than an ephemeris.

## Hosting

Not set up yet. `marimo export html-wasm` bundles the notebook file and nothing
else, so serving this from GitHub Pages will mean getting `earthsim` into
Pyodide - most likely by building a wheel and installing it with `micropip`
from the same site.
