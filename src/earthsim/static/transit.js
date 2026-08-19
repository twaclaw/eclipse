/* Animation 7 - the transit of Venus, and the size of the solar system.
 *
 * Figure : two observers, two sight lines, and the fact they carry. The lines
 *          cross at Venus, so the angle they make there is the same on both
 *          sides - vertically opposite - which turns a baseline you can pace
 *          out into a distance you cannot.
 * Sun    : what the two of them actually see. Venus crossing along two chords
 *          a hair apart, entering and leaving at different moments.
 *
 * Kepler's laws give the shape of the solar system from orbital periods alone,
 * but no size at all. This is the measurement that supplied the size.
 */

export default {
  async render({ model, el }) {
    el.classList.add("es-root");
    el.innerHTML = `
      <div class="es-panel es-diagram es-transitfig">
        <canvas class="es-cfig"></canvas>
      </div>
      <div class="es-panel es-sundisc">
        <canvas class="es-csun"></canvas>
        <div class="es-hint">what the two observers see</div>
      </div>
      ${controlBar(
        sliderHTML("base", "baseline"),
        sliderHTML("impact", "chord"),
        sliderHTML("timing", "timing"),
        sliderHTML("boost", "gap ×"),
        sliderHTML("when", "when"),
        fullscreenHTML(),
      )}`;

    const cfig = el.querySelector(".es-cfig");
    const csun = el.querySelector(".es-csun");
    const fig = cfig.getContext("2d");
    const sun = csun.getContext("2d");

    let figW = 1;
    let figH = 1;
    const roFig = autoSize(cfig, (w, h, dpr) => {
      figW = w;
      figH = h;
      fig.setTransform(dpr, 0, 0, dpr, 0, 0);
    });
    let sunW = 1;
    let sunH = 1;
    const roSun = autoSize(csun, (w, h, dpr) => {
      sunW = w;
      sunH = h;
      sun.setTransform(dpr, 0, 0, dpr, 0, 0);
    });

    const INK = "#1d2433";
    const FAINT = "#9aa4b8";
    const ANGLE = "#c2410c";
    const SITE_A = "#1d4ed8";
    const SITE_B = "#be123c";

    /* -------------------------------------------------------- the argument */

    function bracket(ctx, x, y1, y2, colour, text, side) {
      const tip = side === "left" ? -7 : 7;
      polyline(ctx, [[x + tip, y1], [x, y1], [x, y2], [x + tip, y2]], colour, 1.4);
      label(
        ctx,
        text,
        x + tip * 2.2,
        (y1 + y2) / 2 + 4,
        colour,
        side === "left" ? "right" : "left",
      );
    }

    function drawFigure(view) {
      fig.clearRect(0, 0, figW, figH);
      fig.fillStyle = "#fbfaf6";
      fig.fillRect(0, 0, figW, figH);

      const midY = figH * 0.52;
      const sunX = figW * 0.13;
      const venusX = figW * 0.52;
      const earthX = figW * 0.84;
      const sunR = Math.min(figH * 0.30, figW * 0.09);
      const earthR = Math.max(16, figH * 0.075);

      // Distances are hopeless to scale: Venus is 0.28 AU off and the sun
      // 0.72 further. Only the angles are honest here.
      polyline(fig, [[sunX, midY], [earthX, midY]], FAINT, 1.2, [5, 5]);

      fig.save();
      const glow = fig.createRadialGradient(sunX, midY, 0, sunX, midY, sunR);
      glow.addColorStop(0, "#fff3c4");
      glow.addColorStop(1, "#f0a92f");
      fig.fillStyle = glow;
      fig.beginPath();
      fig.arc(sunX, midY, sunR, 0, Math.PI * 2);
      fig.fill();
      fig.restore();
      label(fig, "sun", sunX, midY + sunR + 18, INK, "center");

      // The two observers, and the two lines through Venus.
      const half = earthR * 0.82;
      const ay = midY - half;
      const by = midY + half;
      fig.save();
      fig.strokeStyle = INK;
      fig.lineWidth = 1.6;
      fig.beginPath();
      fig.arc(earthX, midY, earthR, 0, Math.PI * 2);
      fig.stroke();
      fig.restore();
      label(fig, "Earth", earthX, midY + earthR + 18, INK, "center");

      // Lines cross at Venus, so the far separation grows in the ratio of the
      // two distances - which is the whole trick.
      const grow = view.orbit_ratio / (1 - view.orbit_ratio);
      const sunGap = half * grow;
      const hitA = midY + sunGap;
      const hitB = midY - sunGap;
      polyline(fig, [[earthX, ay], [sunX, hitA]], SITE_A, 1.8);
      polyline(fig, [[earthX, by], [sunX, hitB]], SITE_B, 1.8);

      dot(fig, earthX, ay, SITE_A, 4.5, false);
      dot(fig, earthX, by, SITE_B, 4.5, false);
      label(fig, "A", earthX + earthR * 0.55, ay - 6, SITE_A);
      label(fig, "B", earthX + earthR * 0.55, by + 14, SITE_B);

      dot(fig, venusX, midY, "#2b2b2b", 6, false);
      label(fig, "Venus", venusX, midY - 16, INK, "center");

      dot(fig, sunX, hitA, SITE_A, 4, false);
      dot(fig, sunX, hitB, SITE_B, 4, false);

      // The angle at Venus, the same on both sides.
      const toA = Math.atan2(ay - midY, earthX - venusX);
      const toB = Math.atan2(by - midY, earthX - venusX);
      const toHitA = Math.atan2(hitA - midY, sunX - venusX);
      const toHitB = Math.atan2(hitB - midY, sunX - venusX);
      const arcR = Math.min(figW * 0.055, 46);
      for (const [from, to] of [[toA, toB], [toHitB, toHitA]]) {
        fig.save();
        fig.strokeStyle = ANGLE;
        fig.lineWidth = 2.2;
        fig.beginPath();
        fig.arc(venusX, midY, arcR, from, to);
        fig.stroke();
        fig.restore();
      }
      label(fig, "p", venusX + arcR + 8, midY + 4, ANGLE);
      label(fig, "p", venusX - arcR - 14, midY + 4, ANGLE);

      bracket(fig, earthX + earthR + 16, ay, by, INK, "b", "right");
      bracket(fig, sunX - sunR - 22, hitB, hitA, INK, "s", "left");
      label(fig, "d", (venusX + earthX) / 2, midY - 8, FAINT, "center");
      label(fig, "a", (sunX + venusX) / 2, midY - 8, FAINT, "center");

      const lines = [
        "The two sight lines cross at Venus, so the angle p is the same on",
        "both sides of it. Vertically opposite angles — that is the whole of it.",
        "",
        "p = b / d   and   p = s / a,   so   s = b · a / d.",
        "",
        "Kepler's third law gives a / d from the orbital periods alone: Venus",
        "rides at 0.723 of Earth's distance, so s comes out 2.61 times b.",
        "But Kepler gives only the shape of the solar system, never its size.",
        "",
        "Measure the angle s subtends from here and the scale falls out:",
        "1 AU = b · 2.61 / Δθ.   Pace out b, measure Δθ, and you have the",
        "distance to the sun in kilometres.",
        "",
        "Δθ here is " + view.separation_arcsec.toFixed(1) + "″ — "
          + (view.separation_fraction * 100).toFixed(1)
          + "% of the sun's radius, from a baseline of "
          + Math.round(view.baseline_km).toLocaleString() + " km.",
      ];
      const textX = Math.max(earthX + earthR + 70, figW * 0.60);
      lines.forEach((line, i) =>
        label(fig, line, textX, 30 + i * 19, i === lines.length - 1 ? ANGLE : INK),
      );
      label(fig, "distances not to scale — only the angles are", sunX - sunR,
            figH - 12, FAINT);
    }

    /* ------------------------------------------------------------- the sun */

    function drawSun(view, hours, boost) {
      sun.clearRect(0, 0, sunW, sunH);
      sun.fillStyle = "#0a0c14";
      sun.fillRect(0, 0, sunW, sunH);

      const radius = view.sun_radius_arcsec;
      const scale = (Math.min(sunH * 0.86, sunW * 0.55) / 2) / radius;
      const cx = sunW * 0.36;
      const cy = sunH / 2;

      const face = sun.createRadialGradient(cx, cy, 0, cx, cy, radius * scale);
      face.addColorStop(0, "#fffdf2");
      face.addColorStop(0.82, "#ffe9a8");
      face.addColorStop(1, "#f5b642");
      sun.fillStyle = face;
      sun.beginPath();
      sun.arc(cx, cy, radius * scale, 0, Math.PI * 2);
      sun.fill();

      // Two chords, drawn further apart than they are so the gap is visible.
      const mid = (view.impact_arcsec[0] + view.impact_arcsec[1]) / 2;
      const colours = [SITE_A, SITE_B];
      view.impact_arcsec.forEach((impact, i) => {
        const shown = mid + (impact - mid) * boost;
        if (Math.abs(shown) >= radius) return;
        const halfChord = Math.sqrt(radius * radius - shown * shown);
        const y = cy - shown * scale;
        polyline(
          sun,
          [[cx - halfChord * scale, y], [cx + halfChord * scale, y]],
          colours[i],
          1.6,
          [5, 4],
        );

        const x = cx + view.rate_arcsec_per_hour * hours * scale;
        if (Math.abs(x - cx) <= halfChord * scale) {
          sun.save();
          sun.fillStyle = "#101018";
          sun.beginPath();
          sun.arc(x, y, Math.max(2.5, view.venus_radius_arcsec * scale), 0, Math.PI * 2);
          sun.fill();
          sun.strokeStyle = colours[i];
          sun.lineWidth = 1.4;
          sun.stroke();
          sun.restore();
        }
      });

      const rows = [
        ["observer A", view.duration_hours[0], SITE_A],
        ["observer B", view.duration_hours[1], SITE_B],
      ];
      const textX = Math.min(sunW - 190, cx + radius * scale + 26);
      rows.forEach(([name, hoursTaken, colour], i) => {
        label(sun, name, textX, 30 + i * 20, colour);
        label(
          sun,
          hoursTaken ? fmtHM(hoursTaken).replace(":", " h ") + " m" : "no transit",
          textX + 92,
          30 + i * 20,
          "rgba(255,255,255,0.9)",
        );
      });
      label(
        sun,
        "difference  " + view.duration_gap_minutes.toFixed(1) + " min",
        textX,
        84,
        "rgba(255,255,255,0.95)",
      );
      label(
        sun,
        "gap drawn " + boost.toFixed(0) + "× wider than it is",
        textX,
        112,
        "rgba(255,255,255,0.5)",
      );
      label(
        sun,
        "the timing is the measurement:",
        textX,
        146,
        "rgba(255,255,255,0.6)",
      );
      label(
        sun,
        "a few minutes apart, from a few",
        textX,
        164,
        "rgba(255,255,255,0.6)",
      );
      label(sun, "thousand km apart.", textX, 182, "rgba(255,255,255,0.6)");
    }

    /* -------------------------------------------------------------- wiring */

    const baseline = attachSlider(el, model, {
      name: "base",
      trait: "baseline_km",
      min: 500,
      max: 12742,
      step: 100,
      unit: "km",
      decimals: 0,
    });
    const impact = attachSlider(el, model, {
      name: "impact",
      trait: "impact_arcsec",
      min: -900,
      max: 900,
      step: 10,
      unit: "″",
      decimals: 0,
    });
    const timing = attachSlider(el, model, {
      name: "timing",
      trait: "timing_seconds",
      min: 1,
      max: 120,
      step: 1,
      unit: "s",
      decimals: 0,
    });
    const boost = attachSlider(el, model, {
      name: "boost",
      trait: "gap_boost",
      min: 1,
      max: 20,
      step: 1,
      unit: "×",
      decimals: 0,
    });
    const when = attachScrubber(el, model, {
      name: "when",
      trait: "hours",
      min: -5,
      max: 5,
      step: 0.02,
      format: (v) => (v >= 0 ? "+" : "−") + fmtHM(Math.abs(v)),
    });

    const fullscreen = attachFullscreen(el);

    let raf = 0;
    const gate = visibilityGate(el);

    function frame() {
      raf = requestAnimationFrame(frame);
      if (!gate.visible || document.hidden) return;
      const view = model.get("view");
      if (!view || !view.impact_arcsec) return;
      drawFigure(view);
      drawSun(view, when.value, boost.value);
    }
    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      baseline.dispose();
      impact.dispose();
      timing.dispose();
      boost.dispose();
      when.dispose();
      fullscreen.dispose();
      gate.dispose();
      roFig.disconnect();
      roSun.disconnect();
    };
  },
};
