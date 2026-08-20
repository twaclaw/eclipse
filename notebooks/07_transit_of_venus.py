import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo

    from earthsim.widgets import TransitWidget

    return TransitWidget, mo


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 7. The transit of Venus, and the size of the solar system

    Kepler's third law is generous and stingy at once. From nothing but the
    orbital periods it hands you the entire *shape* of the solar system —
    Venus rides at 0.723 of Earth's distance, Jupiter at 5.20, and so on, all
    of it exact. What it never gives you is a single distance in kilometres.
    The whole map is drawn to an unknown scale.

    One measurement fixes that scale, and for two centuries it was this one.
    When Venus crosses the face of the sun, two observers far apart on Earth
    see it cross along slightly different lines, because they are looking from
    slightly different places. The gap between those two lines is a parallax,
    and a parallax is a distance in disguise.

    The figure below is the argument. The two sight lines **cross at Venus**,
    so the angle they make there is the same on both sides — vertically
    opposite, the same schoolroom fact that carried the last notebook.
    """)
    return


@app.cell(hide_code=True)
def _(TransitWidget, mo):
    # Built in a cell of its own: marimo closes a widget's comm when its
    # defining cell re-runs, so nothing here may depend on the controls.
    transit = TransitWidget()
    transit_ui = mo.ui.anywidget(transit)
    transit_ui
    return (transit_ui,)


@app.cell(hide_code=True)
def _(mo, transit_ui):
    _v = transit_ui.view
    _a, _b = _v["duration_hours"]
    _err = _v["au_error_fraction"]
    _measured = _err is not None and _err < 1
    _range = (
        f"{_v['au_km'] * (1 - _err) / 1e6:,.0f} – {_v['au_km'] * (1 + _err) / 1e6:,.0f} million km"
        if _measured
        else "nothing usable from this pair of chords"
    )
    _within = f"to within {_err * 100:.1f}%" if _measured else "— not measurable here"
    mo.md(
        f"""
    | | |
    |---|---|
    | Baseline between observers | {_v['baseline_km']:,.0f} km |
    | Gap between their chords | {_v['separation_arcsec']:.1f}″ — {_v['separation_fraction'] * 100:.1f}% of the sun's radius |
    | Transit seen by A | {_a:.3f} h |
    | Transit seen by B | {_b:.3f} h |
    | Difference in duration | **{_v['duration_gap_minutes']:.1f} minutes** |
    | Contacts timed to | ±{_v['timing_seconds']:.0f} s |
    | Astronomical unit | **{_v['au_km'] / 1e6:,.1f} million km**, {_within} |
    | So, somewhere in | {_range} |

    {_v['headline']}
    """
    )
    return


if __name__ == "__main__":
    app.run()
