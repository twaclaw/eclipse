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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOKS = ROOT / "notebooks"

#: Pyodide runs Python 3.12, so the wheel must not ask for anything newer.
PYODIDE_PYTHON = ">=3.12"


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


INDEX = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Earth, Moon and Sun</title>
<link rel="icon" href="favicon.ico">
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 7vh 5vw 12vh;
    background: #04060e; color: #e9edf6;
    font: 16px/1.65 ui-sans-serif, system-ui, -apple-system, sans-serif;
  }}
  main {{ max-width: 60rem; margin: 0 auto; }}
  h1 {{ margin: 0 0 .5rem; font-size: clamp(2rem, 5vw, 3.1rem); letter-spacing: -0.02em; }}
  p.lede {{ margin: 0 0 3rem; max-width: 42rem; color: #a8b3c9; font-size: 1.06rem; }}
  ol {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 13px; }}
  a.card {{
    display: grid; grid-template-columns: 2.6rem 1fr; gap: 1rem; align-items: baseline;
    padding: 1.1rem 1.3rem; border-radius: 14px;
    background: #0b1020; border: 1px solid rgba(140, 170, 220, 0.18);
    color: inherit; text-decoration: none;
    transition: border-color .15s, background .15s, transform .15s;
  }}
  a.card:hover {{
    border-color: rgba(255, 216, 138, 0.55); background: #101733;
    transform: translateY(-1px);
  }}
  .num {{ font: 600 1.4rem/1 ui-monospace, SFMono-Regular, Menlo, monospace; color: #ffd88a; }}
  .name {{ display: block; font-weight: 600; font-size: 1.1rem; }}
  .blurb {{ display: block; color: #a8b3c9; margin-top: .18rem; }}
  footer {{
    margin-top: 3.5rem; padding-top: 1.4rem;
    border-top: 1px solid rgba(140, 170, 220, 0.16);
    color: #7f8ba3; font-size: .92rem; max-width: 42rem;
  }}
</style>
</head>
<body>
<main>
  <h1>Earth, Moon and Sun</h1>
  <p class="lede">{lede}</p>
  <ol>
{cards}
  </ol>
  <footer>{footer}</footer>
</main>
</body>
</html>
"""

CARD = """    <li><a class="card" href="{slug}.html">
      <span class="num">{num}</span>
      <span><span class="name">{name}</span><span class="blurb">{blurb}</span></span>
    </a></li>"""

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
    "Seven notebooks on how the sky works, each built so the geometry can be "
    "poked at rather than taken on trust. Every number comes from Python you "
    "can read; the browser only draws."
)
FOOTER = (
    "Each page runs its notebook in your browser through WebAssembly — there "
    "is no server. The first load fetches a Python runtime, so give it a few "
    "seconds; after that everything is local. Planet imagery from the three.js "
    "example set, originally NASA."
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
            subprocess.run(
                [
                    "uv", "run", "marimo", "export", "html-wasm",
                    str(prepared(path, wheel, tmp)),
                    "-o", str(export), "--mode", "run", "--force",
                ],
                cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
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
            cards.append(
                CARD.format(
                    slug=name,
                    num=number,
                    name=rest or title,
                    blurb=blurbs.get(path.name, ""),
                )
            )
            print(f"page   {name}.html")

        wheels = out / "public" / "wheels"
        wheels.mkdir(parents=True, exist_ok=True)
        shutil.copy2(wheel, wheels / wheel.name)

    (out / "index.html").write_text(
        INDEX.format(
            lede=LEDE,
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
