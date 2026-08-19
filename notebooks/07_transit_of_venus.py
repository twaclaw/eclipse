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


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    /// tip | Try this
    Set **timing** to 120 s — the best an eighteenth-century observer with a
    pendulum clock and a shaking telescope might manage on a bad day. The
    answer is worthless. Now bring it to 10 s and the astronomical unit lands
    within a few percent, which is roughly what the 1761 and 1769 expeditions
    actually achieved. Captain Cook sailed to Tahiti for those seconds.

    Then drag **chord** towards 0, a transit straight across the sun's middle.
    The two durations converge and the error explodes. A chord through the
    centre barely changes length when you shift it sideways, so its timing
    tells you almost nothing about *where* it is. Halley knew this: the method
    needs chords well off centre, and observers as far apart as possible.
    ///

    ### Why it works

    Let $b$ be the distance between the observers, $d$ the gap from Earth to
    Venus, and $a$ the gap from Venus to the sun.

    The two sight lines cross at Venus, so the angle $p$ they make there is the
    same on both sides. On the near side $p = b/d$; on the far side
    $p = s/a$, where $s$ is how far apart the lines land on the sun. Therefore

    $$s = b\,\frac{a}{d}$$

    Kepler gives $a/d$ without any distances at all: Venus sits at 0.723 of
    Earth's distance, so $a/d = 0.723/0.277 = 2.61$. The separation on the sun
    is 2.61 times the baseline — bigger than the baseline, which is the piece
    of luck that makes the method work.

    Seen from Earth, $s$ subtends an angle $\Delta\theta = s / \text{AU}$. Turn
    that around:

    $$\text{AU} = \frac{b}{\Delta\theta}\cdot\frac{a}{d}$$

    A length you can pace out, an angle you can measure, and a ratio Kepler
    gives you free.

    ### Notes on the model

    * **Nobody measures $\Delta\theta$ directly.** At 29″ against a disc 1919″
      across, it is far too fine for an eighteenth-century micrometer. Halley's
      insight was to measure *time* instead: a shorter chord takes less time to
      cross, so the parallax turns into a difference of several minutes between
      two clocks. That is what the second panel shows, and it is why the
      **timing** control is the one that decides the answer.
    * The gap between the chords is drawn wider than it is — 3% of the sun's
      radius is nearly invisible. The **gap ×** control sets that exaggeration,
      and 1 is the truth.
    * The baseline here is the separation *projected across the line of sight*.
      Two real observers get less than Earth's full diameter, and how much less
      depends on where they stand and when.
    * Left out: the black-drop effect that blurred contact timings and wrecked
      the 1761 results, limb darkening, refraction in Venus's atmosphere,
      Earth's rotation during the six hours, and the small eccentricities of
      both orbits.
    * Radar to Venus settled the astronomical unit in the 1960s, and it is now
      a defined constant: 149,597,870.7 km exactly.
    """)
    return


if __name__ == "__main__":
    app.run()
