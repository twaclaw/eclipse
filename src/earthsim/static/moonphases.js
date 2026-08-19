/* Animation 1 - the phases of the Moon.
 *
 * Left  : the system from above, not to scale. Sunlight arrives from one side,
 *         so Earth and Moon are each half lit at all times. Nothing about that
 *         changes during the month.
 * Right : the Moon as it looks from Earth. The Moon keeps one face turned
 *         towards us, so the view never changes - only the lighting swings
 *         around it, and that swing is the entire phase cycle.
 *
 * Putting the two side by side is the point: the phase on the right is just
 * how much of the lit half on the left happens to face us.
 */

export default {
  async render({ model, el }) {
    el.classList.add("es-root");
    el.innerHTML = `
      <div class="es-grid es-grid-even">
        <div class="es-panel es-orbit">
          <canvas class="es-c2d"></canvas>
          <div class="es-hint">from above the north pole &middot; not to scale</div>
        </div>
        <div class="es-panel es-moon">
          <canvas class="es-c3d"></canvas>
          <div class="es-clock"></div>
          <div class="es-hint">drag to look around</div>
          <div class="es-phase"></div>
        </div>
      </div>
      <div class="es-bigname"></div>
      ${controlBar(
        playHTML(),
        sliderHTML("speed", "cycle"),
        sliderHTML("light", "moon"),
        sliderHTML("when", "when"),
        fullscreenHTML(),
      )}
      <div class="es-status">loading textures&hellip;</div>`;

    const c2d = el.querySelector(".es-c2d");
    const c3d = el.querySelector(".es-c3d");
    const clockEl = el.querySelector(".es-clock");
    const phaseEl = el.querySelector(".es-phase");
    const bigNameEl = el.querySelector(".es-bigname");
    const status = el.querySelector(".es-status");

    let THREE, moonImg, earthImg;
    try {
      [THREE, moonImg, earthImg] = await Promise.all([
        getThree(),
        loadImage(TEX.moon),
        loadImage(TEX.day),
      ]);
    } catch (err) {
      status.textContent = "could not load three.js or the textures: " + err.message;
      status.classList.add("es-error");
      return;
    }
    status.remove();

    /* --------------------------------------------------- the Moon from Earth */

    const renderer = new THREE.WebGLRenderer({
      canvas: c3d,
      antialias: true,
      alpha: false,
    });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
    renderer.setClearColor(0x05060c, 1);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(30, 1, 0.05, 200);
    scene.add(buildStars(THREE, 1400, 60));

    // No atmosphere, so the terminator is nearly a knife edge and the dark
    // side shows only earthshine.
    const moon = buildBody(THREE, {
      dayImg: moonImg,
      nightImg: null,
      nightGain: 0,
      ambient: 0.02,
      twilight: 0.015,
      atmosphere: 0,
      segments: 96,
      maxAniso: renderer.capabilities.getMaxAnisotropy(),
    });
    scene.add(moon.group);

    const orbit = attachOrbit(c3d, camera, { radius: 4.0, phi: Math.PI / 2, minR: 2.4, maxR: 9 });
    const ro3d = autoSize(c3d, (w, h, dpr) => {
      renderer.setPixelRatio(dpr);
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    });

    /* ------------------------------------------------------- the view above */

    const ctx = c2d.getContext("2d");
    let w = 1;
    let h = 1;
    const ro2d = autoSize(c2d, (cw, ch, dpr) => {
      w = cw;
      h = ch;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    });

    /* Draws a body as a disc with its sunward half lit. The sun is always to
     * the left here, so every half-lit disc faces the same way - which is the
     * thing the animation is trying to make obvious. */
    function halfLitDisc(x, y, r, litColour, darkColour) {
      ctx.save();
      ctx.beginPath();
      ctx.arc(x, y, r, Math.PI / 2, (3 * Math.PI) / 2);
      ctx.fillStyle = litColour;
      ctx.fill();
      ctx.beginPath();
      ctx.arc(x, y, r, (3 * Math.PI) / 2, Math.PI / 2);
      ctx.fillStyle = darkColour;
      ctx.fill();
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(255,255,255,0.35)";
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.restore();
    }

    function drawAbove(track, at) {
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "#05070f";
      ctx.fillRect(0, 0, w, h);

      const cx = w * 0.58;
      const cy = h * 0.5;
      const orbitR = Math.min(w * 0.34, h * 0.38);
      const earthR = Math.max(9, orbitR * 0.13);
      const moonR = Math.max(5, orbitR * 0.07);

      // Sunlight: parallel rays from the left, because the sun is far away.
      for (let i = 0; i <= 6; i++) {
        const y = h * (0.12 + (0.76 * i) / 6);
        polyline(ctx, [[6, y], [cx - orbitR - 26, y]], "rgba(255,214,120,0.30)", 1.5);
        polyline(
          ctx,
          [
            [cx - orbitR - 34, y],
            [cx - orbitR - 26, y - 4],
            [cx - orbitR - 26, y + 4],
          ],
          "rgba(255,214,120,0.30)",
          1.5,
        );
      }
      label(ctx, "sunlight", 8, 16, "rgba(255,214,120,0.75)");

      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, orbitR, 0, Math.PI * 2);
      ctx.setLineDash([4, 4]);
      ctx.strokeStyle = "rgba(255,255,255,0.22)";
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.restore();

      // Elongation grows eastward from the sun, so new moon sits between us
      // and the sun. Screen y points down, so drawing it clockwise here is
      // anticlockwise seen from over the north pole, which is the real sense.
      const angle = at.elongation_deg * DEG;
      const mx = cx - orbitR * Math.cos(angle);
      const my = cy - orbitR * Math.sin(angle);

      // Ghost discs at the four cardinal phases, for orientation.
      for (const a of [0, 90, 180, 270]) {
        const gx = cx - orbitR * Math.cos(a * DEG);
        const gy = cy - orbitR * Math.sin(a * DEG);
        ctx.save();
        ctx.globalAlpha = 0.28;
        halfLitDisc(gx, gy, moonR * 0.75, "#cfd4e0", "#20242f");
        ctx.restore();
      }

      polyline(ctx, [[cx, cy], [mx, my]], "rgba(255,255,255,0.35)", 1, [3, 3]);

      halfLitDisc(cx, cy, earthR, "#7fb2e8", "#16243a");
      label(ctx, "Earth", cx, cy + earthR + 14, "rgba(255,255,255,0.6)", "center");

      halfLitDisc(mx, my, moonR, "#e8e4da", "#23252c");

      // The slice of that lit half we can see from Earth is the phase.
      label(
        ctx,
        Math.round(at.illuminated * 100) + "% lit from here",
        mx,
        my - moonR - 8,
        "rgba(255,255,255,0.72)",
        "center",
      );

      label(ctx, at.phase, cx, 18, "rgba(255,255,255,0.85)", "center");
    }

    /* ------------------------------------------------------------------ loop */

    const play = attachPlay(el, model);
    const speed = attachSlider(el, model, {
      name: "speed",
      trait: "speed",
      min: 0,
      max: 8,
      step: 0.25,
      unit: "d/s",
      decimals: 2,
    });
    const light = attachSlider(el, model, {
      name: "light",
      trait: "brightness",
      min: 0.15,
      max: 2.5,
      step: 0.05,
      unit: "\u00d7",
      decimals: 2,
    });

    const month = (model.get("track").scalars || {}).synodic_month || 29.53;
    const when = attachScrubber(el, model, {
      name: "when",
      trait: "age_days",
      min: 0,
      max: month,
      step: 0.05,
      format: (v) => "day " + Number(v).toFixed(1),
    });

    const fullscreen = attachFullscreen(el);

    let age = model.get("age_days");
    let last = performance.now();
    let raf = 0;
    const gate = visibilityGate(el);
    const sunVec = new THREE.Vector3();

    function frame(now) {
      raf = requestAnimationFrame(frame);
      const dt = Math.min(0.08, (now - last) / 1000);
      last = now;
      if (!gate.visible || document.hidden) return;

      const track = model.get("track");
      if (!track || !track.t) return;

      if (when.scrubbing) {
        age = when.value;
      } else if (play.playing) {
        age = (age + dt * speed.value) % month;
        if (age < 0) age += month;
      }
      when.follow(age);
      const at = trackSample(track, age);

      sunVec.set(at.moon_view_sun[0], at.moon_view_sun[1], at.moon_view_sun[2]);
      moon.uniforms.uSunDir.value.copy(sunVec);
      moon.uniforms.uExposure.value = light.value;
      moon.uniforms.uAmbient.value =
        0.012 + 0.075 * at.earthshine * (model.get("show_earthshine") ? 1 : 0);
      // Southern-hemisphere observers see the same Moon turned upside down.
      camera.up.set(0, model.get("southern_view") ? -1 : 1, 0);
      orbit.apply();

      renderer.render(scene, camera);
      drawAbove(track, at);

      clockEl.textContent = "day " + age.toFixed(1) + " of " + month.toFixed(1);
      phaseEl.textContent =
        at.phase + " · " + Math.round(at.illuminated * 100) + "%";
      // Python decides the wording; the stylesheet puts it in capitals.
      bigNameEl.textContent = at.phase_es;
    }
    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      play.dispose();
      speed.dispose();
      light.dispose();
      when.dispose();
      orbit.dispose();
      fullscreen.dispose();
      gate.dispose();
      ro3d.disconnect();
      ro2d.disconnect();
      renderer.dispose();
    };
  },
};
