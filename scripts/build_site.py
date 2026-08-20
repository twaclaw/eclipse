#!/usr/bin/env python3
"""Build the static site: one WebAssembly page per notebook, plus a contents page.

    uv run --group dev python scripts/build_site.py
    python -m http.server --directory site

Every notebook imports ``earthsim``, and ``marimo export html-wasm`` bundles the
notebook file and nothing else. So the package is built as a wheel and named as
a PEP 723 dependency in a throwaway copy of each notebook; marimo spots the
local wheel, copies it into the export, and rewrites the reference. The
notebooks in the repository stay clean and know nothing about any of this.

Two wrinkles worth knowing.

marimo copies its whole front end - some 28 MB - into every export. Seven
copies of the same 728 files is most of a gigabyte for nothing, so the pages
are laid out flat at the site root and share one ``assets`` directory. Nothing
has to be rewritten for that: the exports already reference ``./assets/...``,
which resolves to the same place once the page is at the root.

The wheel does need one fix. marimo points at ``../public/wheels/...``, which
assumes the export sits at the root of the domain; under a project page that
climbs out of the site entirely. It is rewritten to stay inside.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOKS = ROOT / "notebooks"

#: Pyodide runs Python 3.12, so the wheel must not ask for anything newer.
PYODIDE_PYTHON = ">=3.12"

#: Both steps are seconds of work locally. The point of a bound is that a
#: child which stops making progress - waiting on a lock, a mirror or an
#: answer nobody is there to give - fails the build instead of sitting there
#: until the CI runner's own six-hour limit puts it out of its misery.
WHEEL_TIMEOUT_S = 300
EXPORT_TIMEOUT_S = 600


def slug(path: Path) -> str:
    return path.stem.replace("_", "-")


def notebook_title(path: Path) -> str:
    """The single ``# heading`` each notebook opens with."""
    found = re.search(r"^\s*#\s+(\d+\..+?)\s*$", path.read_text(), re.MULTILINE)
    return found.group(1) if found else path.stem


def descriptions() -> dict[str, str]:
    """One line per notebook, lifted from the table in the README.

    Keeping the blurbs in one place stops the contents page drifting away from
    the documentation.
    """
    out: dict[str, str] = {}
    for line in (ROOT / "README.md").read_text().splitlines():
        row = re.match(r"^\|\s*`([^`]+\.py)`\s*\|\s*(.+?)\s*\|\s*$", line)
        if row:
            out[row.group(1)] = row.group(2)
    return out


def build_wheel(into: Path) -> Path:
    into.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["uv", "build", "--wheel", "-o", str(into)],
        cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL, timeout=WHEEL_TIMEOUT_S,
    )
    wheels = sorted(into.glob("*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"expected exactly one wheel, found {[w.name for w in wheels]}")
    return wheels[0]


def wheel_reference_ok(html: str, wheel: Path) -> bool:
    """Check the page still asks for the wheel where the build puts it.

    Resolved from the worker in ``assets/``, ``../public/wheels/`` is the site
    root. If a future marimo writes something else, the site would load and
    then fail deep inside Pyodide with a bare ModuleNotFoundError, so it is
    worth failing here instead.
    """
    return f"../public/wheels/{wheel.name}" in html


def prepared(path: Path, wheel: Path, tmp: Path) -> Path:
    """A copy of the notebook that can stand on its own in a browser.

    Two changes, both only for the hosted build: the dependency block telling
    Pyodide what to install, and a full-width layout so the animation fills the
    page instead of sitting in a column.
    """
    header = (
        "# /// script\n"
        f'# requires-python = "{PYODIDE_PYTHON}"\n'
        "# dependencies = [\n"
        '#     "numpy",\n'
        '#     "anywidget==0.11.0",\n'
        f'#     "earth-simulations @ {wheel}",\n'
        "# ]\n"
        "# ///\n\n"
    )
    source = path.read_text().replace(
        'marimo.App(width="medium")', 'marimo.App(width="full")'
    )
    target = tmp / path.name
    target.write_text(header + source)
    return target


INDEX = Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Earth, Moon and Sun</title>
<link rel="icon" href="favicon.ico">
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }

  body {
    margin: 0;
    padding: 6vh 5vw 9vh;
    background: #070b1c;
    background-image:
      radial-gradient(1100px 700px at 82% -12%, #1e2f66 0%, transparent 62%),
      radial-gradient(900px 600px at 6% 6%, #2a1d51 0%, transparent 58%);
    color: #f2f5ff;
    font-family: ui-rounded, "SF Pro Rounded", "Hiragino Maru Gothic ProN",
      Nunito, Quicksand, "Varela Round", "Trebuchet MS", system-ui, sans-serif;
    font-size: 17px;
    line-height: 1.55;
  }

  /* A sky to put the cards in. Dots rather than an image, so the page is still
     one file and still loads instantly. */
  .stars {
    position: fixed; inset: 0; z-index: 0; pointer-events: none; opacity: .7;
    background-image:
      radial-gradient(2px 2px at 12% 18%, #fff, transparent),
      radial-gradient(2px 2px at 27% 62%, #ffe9b8, transparent),
      radial-gradient(1.5px 1.5px at 41% 12%, #fff, transparent),
      radial-gradient(2px 2px at 58% 78%, #d6e6ff, transparent),
      radial-gradient(1.5px 1.5px at 66% 33%, #fff, transparent),
      radial-gradient(2px 2px at 79% 8%, #ffe9b8, transparent),
      radial-gradient(1.5px 1.5px at 88% 54%, #fff, transparent),
      radial-gradient(2px 2px at 94% 88%, #d6e6ff, transparent),
      radial-gradient(1.5px 1.5px at 34% 91%, #fff, transparent),
      radial-gradient(2px 2px at 5% 47%, #fff, transparent);
    animation: twinkle 4.5s ease-in-out infinite alternate;
  }
  @keyframes twinkle { from { opacity: .35 } to { opacity: .85 } }

  main { position: relative; z-index: 1; max-width: 68rem; margin: 0 auto; }

  h1 {
    margin: 0 0 .35rem;
    font-size: clamp(2.2rem, 6.2vw, 3.7rem);
    font-weight: 800;
    letter-spacing: .01em;
    color: #ffe7a3;
    text-shadow: 0 0 28px rgba(255, 197, 92, .38);
  }

  p.lede {
    margin: 0 0 2.4rem;
    max-width: 40rem;
    font-size: 1.16rem;
    color: #c9d1ec;
  }

  ol.cards {
    list-style: none; margin: 0; padding: 0;
    display: grid; gap: 16px;
    grid-template-columns: repeat(auto-fit, minmax(25rem, 1fr));
  }

  a.card {
    display: grid;
    grid-template-columns: 108px 1fr;
    gap: 1.1rem;
    align-items: center;
    height: 100%;
    padding: 1.15rem 1.3rem;
    border-radius: 22px;
    border: 2px solid var(--tint);
    background:
      linear-gradient(158deg, rgba(255, 255, 255, .09), rgba(255, 255, 255, .02));
    color: inherit;
    text-decoration: none;
    transition: transform .18s ease, box-shadow .18s ease, background .18s ease;
  }

  a.card:hover, a.card:focus-visible {
    outline: none;
    transform: translateY(-4px);
    background:
      linear-gradient(158deg, rgba(255, 255, 255, .16), rgba(255, 255, 255, .04));
    box-shadow: 0 14px 34px rgba(0, 0, 0, .5);
  }

  .art { display: block; width: 108px; height: 108px; }
  .art svg { display: block; width: 100%; height: 100%; }
  a.card:hover .art { animation: wiggle .65s ease-in-out; }
  @keyframes wiggle {
    25% { transform: rotate(-7deg) }
    60% { transform: rotate(6deg) }
  }

  .num {
    display: inline-flex; align-items: center; justify-content: center;
    width: 1.75rem; height: 1.75rem; margin-bottom: .25rem;
    border-radius: 50%;
    background: var(--tint); color: #0a0f22;
    font-size: .95rem; font-weight: 800;
  }

  .name {
    display: block;
    font-size: 1.3rem; font-weight: 800; line-height: 1.25;
    color: var(--tint);
  }

  .blurb { display: block; margin-top: .3rem; color: #c9d1ec; }

  p.hint {
    margin: 2.4rem 0 0;
    font-size: 1.05rem;
    color: #ffe7a3;
  }

  footer {
    margin-top: 2rem; padding-top: 1.3rem;
    border-top: 1px solid rgba(140, 170, 220, .18);
    max-width: 44rem;
    color: #8b95b5; font-size: .92rem; line-height: 1.6;
  }

  @media (prefers-reduced-motion: reduce) {
    .stars { animation: none }
    a.card { transition: none }
    a.card:hover .art { animation: none }
  }
</style>
</head>
<body>
<div class="stars"></div>
<main>
  <h1>Earth, Moon and Sun</h1>
  <p class="lede">$lede</p>
  <ol class="cards">
$cards
  </ol>
  <p class="hint">$hint</p>
  <footer>$footer</footer>
</main>
</body>
</html>
""")

CARD = Template("""    <li><a class="card" href="$slug.html" style="--tint: $tint">
      <span class="art">$art</span>
      <span>
        <span class="num">$num</span>
        <span class="name">$name</span>
        <span class="blurb">$blurb</span>
      </span>
    </a></li>""")

# A picture per notebook, drawn rather than fetched: an emoji would be at the
# mercy of the reader's font, and a child picks the page by its picture.
ART = {
    "moon": """<svg viewBox="0 0 100 100" aria-hidden="true">
      <circle cx="50" cy="50" r="31" fill="#2b3566"/>
      <path d="M50 19a31 31 0 0 1 0 62 21 31 0 0 0 0-62z" fill="#ffeec2"/>
      <circle cx="15" cy="20" r="2.4" fill="#fff"/>
      <circle cx="86" cy="76" r="2" fill="#fff"/>
    </svg>""",
    "seasons": """<svg viewBox="0 0 100 100" aria-hidden="true">
      <g stroke="#ffd166" stroke-width="3.4" stroke-linecap="round">
        <path d="M24 32V23M24 68v9M8 50H1M14 40L9 35M14 60L9 65M34 40L39 35"/>
      </g>
      <circle cx="24" cy="50" r="14" fill="#ffd166"/>
      <circle cx="72" cy="52" r="19" fill="#4a8fd6"/>
      <path d="M60 48c8 5 18 5 25 0" stroke="#9ad4a0" stroke-width="3.4"
        fill="none" stroke-linecap="round"/>
      <path d="M63 73L81 31" stroke="#fff8e6" stroke-width="3"
        stroke-linecap="round" stroke-dasharray="6 5"/>
    </svg>""",
    "daynight": """<svg viewBox="0 0 100 100" aria-hidden="true">
      <circle cx="52" cy="52" r="30" fill="#141d3d"/>
      <path d="M52 22a30 30 0 0 0 0 60z" fill="#7ee0c0"/>
      <path d="M52 22v60" stroke="#0b1226" stroke-width="2.5"/>
      <circle cx="14" cy="18" r="9" fill="#ffd166"/>
      <circle cx="88" cy="84" r="6" fill="#e8ecff"/>
      <circle cx="78" cy="26" r="2.2" fill="#fff"/>
      <circle cx="92" cy="46" r="1.8" fill="#fff"/>
    </svg>""",
    "lunar": """<svg viewBox="0 0 100 100" aria-hidden="true">
      <path d="M28 34l68 10v12l-68 10z" fill="#232a52"/>
      <circle cx="26" cy="50" r="17" fill="#4a8fd6"/>
      <path d="M14 44c8 4 18 4 26 0" stroke="#9ad4a0" stroke-width="3.2"
        fill="none" stroke-linecap="round"/>
      <circle cx="79" cy="50" r="10" fill="#e2603f"/>
    </svg>""",
    "solar": """<svg viewBox="0 0 100 100" aria-hidden="true">
      <g stroke="#ffd166" stroke-width="3.6" stroke-linecap="round">
        <path d="M50 6v9M50 85v9M6 50h9M85 50h9M19 19l6 6M75 75l6 6M81 19l-6 6M25 75l-6 6"/>
      </g>
      <circle cx="50" cy="50" r="27" fill="#ffd166"/>
      <circle cx="46" cy="47" r="24" fill="#0b1020"/>
    </svg>""",
    "polaris": """<svg viewBox="0 0 100 100" aria-hidden="true">
      <path d="M74 6l4.4 12.6L91 23l-12.6 4.4L74 40l-4.4-12.6L57 23l12.6-4.4z"
        fill="#ffe08a"/>
      <path d="M44 72L72 26" stroke="#ffe08a" stroke-width="2.6"
        stroke-dasharray="5 5" stroke-linecap="round"/>
      <circle cx="44" cy="72" r="21" fill="#4a8fd6"/>
      <path d="M31 66c9 4 17 4 26 0" stroke="#9ad4a0" stroke-width="3.2"
        fill="none" stroke-linecap="round"/>
    </svg>""",
    "transit": """<svg viewBox="0 0 100 100" aria-hidden="true">
      <circle cx="50" cy="50" r="31" fill="#ffd166"/>
      <path d="M22 60h56" stroke="#d79a24" stroke-width="2.6"
        stroke-dasharray="4 6" stroke-linecap="round"/>
      <circle cx="61" cy="60" r="6" fill="#221a3a"/>
      <circle cx="61" cy="60" r="6" fill="none" stroke="#fff4d2" stroke-width="1.4"/>
    </svg>""",
}

#: What each page is called on the contents, in the words of the person most
#: likely to be clicking. The README table stays the grown-up description and
#: still fills in for anything not listed here.
INVITATIONS = {
    "01_moon_phases.py": (
        "moon", "#9fd8ff",
        "Why does the Moon change shape?",
        "Half of it is always sunny. We just see that sunny half from the side.",
    ),
    "02_seasons.py": (
        "seasons", "#ffd166",
        "Why do we get summer and winter?",
        "The Earth leans over, and it keeps leaning the same way all year long.",
    ),
    "03_day_and_night.py": (
        "daynight", "#7ee0c0",
        "Where in the world is it night now?",
        "Spin the Earth and follow the line where the Sun is just coming up.",
    ),
    "04_lunar_eclipse.py": (
        "lunar", "#ff9d7a",
        "Can the Earth hide the Moon?",
        "Now and then our shadow falls on the Moon and paints it red.",
    ),
    "05_solar_eclipse.py": (
        "solar", "#c9a6ff",
        "Can the Moon hide the Sun?",
        "Now and then the Moon's shadow lands on us, and the day goes dim.",
    ),
    "06_latitude_and_polaris.py": (
        "polaris", "#ffe08a",
        "Which star never moves?",
        "Point at it, and you have just measured how far north you live.",
    ),
    "07_transit_of_venus.py": (
        "transit", "#ff9fc4",
        "How far away is the Sun?",
        "Two people far apart watched a tiny dot cross it, and worked it out.",
    ),
}

# Dropped into every exported page: the notebooks are separate documents, so
# without this there is no way back to the contents.
BACK_LINK = """
<style>
  .es-home {
    position: fixed; left: 14px; bottom: 14px; z-index: 9999;
    padding: 7px 13px; border-radius: 999px; text-decoration: none;
    background: rgba(11, 16, 32, .9); color: #ffd88a;
    border: 1px solid rgba(255, 216, 138, .45);
    font: 500 13px/1 ui-sans-serif, system-ui, sans-serif;
  }
  .es-home:hover { background: #101733; }
</style>
<a class="es-home" href="./">&#8592; all notebooks</a>
"""

LEDE = (
    "Seven things the sky does, and seven pictures you can play with until you "
    "can see why. Drag them, slide time back and forth, and pick the spot you "
    "live in."
)
HINT = (
    "Pick a picture to begin. Give it a few seconds to wake up — it is "
    "building a whole little world."
)
FOOTER = (
    "For grown-ups: each page runs a marimo notebook in your browser through "
    "WebAssembly, so there is no server and nothing to install. The first load "
    "fetches a Python runtime; after that everything is local. Every number "
    "comes from Python you can read, and the browser only draws. Planet "
    "imagery from the three.js example set, originally NASA."
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="site", type=Path)
    args = parser.parse_args()

    out = (ROOT / args.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    notebooks = sorted(NOTEBOOKS.glob("[0-9]*.py"))
    if not notebooks:
        raise SystemExit("no notebooks found")
    blurbs = descriptions()
    cards = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        wheel = build_wheel(tmp / "wheel")
        print(f"wheel  {wheel.name}  ({wheel.stat().st_size // 1024} kB)\n")
        shared_taken = False

        for path in notebooks:
            name = slug(path)
            export = tmp / f"export-{name}"
            started = time.monotonic()
            subprocess.run(
                [
                    "uv", "run", "marimo", "export", "html-wasm",
                    str(prepared(path, wheel, tmp)),
                    "-o", str(export), "--mode", "run", "--force",
                    # The prepared copy carries inline dependencies, and marimo
                    # offers to resolve them in a throwaway venv. It skips the
                    # question when stdin is not a terminal, but saying so
                    # outright keeps the build the same everywhere.
                    "--no-sandbox",
                ],
                cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL, timeout=EXPORT_TIMEOUT_S,
            )

            # The front end is byte-identical between exports, so the first one
            # donates it and the rest are thrown away.
            if not shared_taken:
                shutil.copytree(export / "assets", out / "assets")
                for extra in sorted(export.iterdir()):
                    if extra.is_file() and extra.name not in {"index.html", "CLAUDE.md"}:
                        shutil.copy2(extra, out / extra.name)
                shared_taken = True

            html = (export / "index.html").read_text()
            if not wheel_reference_ok(html, wheel):
                raise SystemExit(
                    f"{name}: the page does not reference "
                    f"../public/wheels/{wheel.name} - marimo may have changed "
                    "how it writes local wheel dependencies, and the site would "
                    "fail at import time"
                )
            html = html.replace("</body>", BACK_LINK + "</body>")
            (out / f"{name}.html").write_text(html)

            title = notebook_title(path)
            number, _, rest = title.partition(". ")
            art, tint, headline, invite = INVITATIONS.get(
                path.name, ("moon", "#9fd8ff", rest or title, blurbs.get(path.name, ""))
            )
            cards.append(
                CARD.substitute(
                    slug=name,
                    tint=tint,
                    art=ART[art],
                    num=number,
                    name=headline,
                    blurb=invite,
                )
            )
            print(f"page   {name}.html  ({time.monotonic() - started:.0f}s)",
                  flush=True)

        wheels = out / "public" / "wheels"
        wheels.mkdir(parents=True, exist_ok=True)
        shutil.copy2(wheel, wheels / wheel.name)

    (out / "index.html").write_text(
        INDEX.substitute(
            lede=LEDE,
            hint=HINT,
            footer=FOOTER,
            cards="\n".join(cards),
        )
    )
    (out / ".nojekyll").touch()

    total = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"\n{len(notebooks)} pages, {total / 1e6:.1f} MB in {out.relative_to(ROOT)}/")
    print(f"  python -m http.server --directory {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
