#!/usr/bin/env python3
"""Load every built page in a real browser and check it actually works.

    uv run --group site python scripts/check_site.py

The unit tests cover the astronomy and run the drawing code against a stub, but
neither can tell you whether the site *deploys*. A site can build cleanly, pass
every test, serve every file with a 200, and still be dead the moment Pyodide
tries to import the package - which is exactly what happened once, from a wheel
URL that was correct relative to the page and wrong relative to the worker that
fetches it.

So this serves the build and waits for each notebook to actually draw.
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent

#: Generous: the first page has to fetch a Python runtime before it can start.
READY_TIMEOUT_MS = 120_000

#: One page at a time. Each holds WebGL contexts and its own Pyodide worker,
#: and running them together starved some pages badly enough to time out on a
#: site that was perfectly healthy. Sequential is slower and tells the truth.


async def check(context, url: str, name: str) -> tuple[bool, str]:
    page = await context.new_page()
    problems: list[str] = []
    page.on(
        "console",
        lambda m: problems.append(m.text[:160])
        if "ModuleNotFoundError" in m.text or "Failed to load packages" in m.text
        else None,
    )
    try:
        await page.goto(url, wait_until="load")
        # A canvas inside the widget means Python ran, the package imported,
        # the widget mounted and its first frame drew. Attached, not visible:
        # some widgets stack two canvases and hide one - the eclipse pages show
        # either the Moon or the sun - and waiting for visibility on whichever
        # happens to come first in the markup is a coin toss.
        await page.wait_for_selector(
            ".es-root canvas", state="attached", timeout=READY_TIMEOUT_MS
        )
        await page.wait_for_timeout(1200)
        body = await page.inner_text("body")
        canvases = await page.query_selector_all(".es-root canvas")
        for word in ("ModuleNotFoundError", "Traceback (most recent call last)"):
            if word in body:
                problems.append(f"{word} on the page")
        if not canvases:
            problems.append("no canvas drawn")
        return not problems, f"{name:34s} canvases={len(canvases):2d} {'; '.join(problems[:2])}"
    except Exception as exc:  # noqa: BLE001 - the message is the report
        return False, f"{name:34s} {type(exc).__name__}: {str(exc)[:90]}"
    finally:
        await page.close()


async def run(site: Path, port: int) -> int:
    from playwright.async_api import async_playwright

    pages = sorted(site.glob("[0-9]*.html"))
    if not pages:
        raise SystemExit(f"no pages in {site} - build the site first")

    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--directory", str(site)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        base = f"http://127.0.0.1:{port}"
        for _ in range(50):
            try:
                urlopen(base, timeout=0.5).read(1)
                break
            except Exception:  # noqa: BLE001 - just waiting for the port
                time.sleep(0.1)

        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            # One context for all of them, so the Python runtime is fetched
            # once and every page after the first starts warm.
            context = await browser.new_context()
            results = []
            for path in pages:
                results.append(await check(context, f"{base}/{path.name}", path.name))
                print(f"{'ok  ' if results[-1][0] else 'FAIL'} {results[-1][1]}")
            await browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)

    failed = sum(not ok for ok, _ in results)
    print(f"\n{len(results) - failed}/{len(results)} pages live")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default="site", type=Path)
    parser.add_argument("--port", default=8899, type=int)
    args = parser.parse_args()
    return asyncio.run(run((ROOT / args.site).resolve(), args.port))


if __name__ == "__main__":
    sys.exit(main())
