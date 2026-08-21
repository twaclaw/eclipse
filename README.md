# Ήλιος, Σελήνη και Γαία

*Earth simulations*

This series of animations depicts the Earth-Moon-Sun system and is intended for young children. 
They are not meant to be accurate, just indicative.  These animations were coded almost entirely using Claude code across multiple iterations and sessions.

Loosely speaking, the instructions were along these lines:

- Implement all the physics in Python.
- Keep the JavaScript layer as thin as possible.
- Use Marimo and its ability to export WebAssembly (WASM) to serve this site on GitHub Pages.
- Use photo-realistic images of the Earth and Moon.

The following notebooks were implemented:


| notebook | shows |
|---|---|
| [01_moon_phases.py](./notebooks/01_moon_phases.py) | the Moon is always half lit; the phase is how much of that half faces us |
| [02_seasons.py](./notebooks/02_seasons.py) | one axis, fixed in space, and how it stretches and shrinks a chosen place's day |
| [03_day_and_night.py](./notebooks/03_day_and_night.py) | rotation, the terminator on a flat map, and the sun's path over one place |
| [04_lunar_eclipse.py](./notebooks/04_lunar_eclipse.py) | Earth's shadow crossing the Moon, and why it usually misses |
| [05_solar_eclipse.py](./notebooks/05_solar_eclipse.py) | the Moon's shadow crossing us, and why it is often a ring |
| [06_latitude_and_polaris.py](./notebooks/06_latitude_and_polaris.py) | latitude as an angle you cannot see, and the pole star that shows it |
| [07_transit_of_venus.py](./notebooks/07_transit_of_venus.py) | parallax across a baseline, and the first honest measure of the solar system |

```sh
make install   # virtualenv, plus a browser for checking the site
make edit      # open the notebooks in marimo
make test
make serve     # build the site and serve it at localhost:8080
make check     # load every built page in a real browser
```

