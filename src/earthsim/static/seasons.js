/* Animation 2 - axial tilt and the seasons.
 *
 * Orbit : the sun at a focus, Earth walking the ellipse, and the spin axis
 *         pointing the same way in space the whole way round. That fixed axis
 *         leaning towards the sun in June and away in December is the entire
 *         mechanism. The globe does not spin: a year passes in seconds here,
 *         and 365 turns in that span would read as a blur.
 * Map   : pick a place.
 * Sun   : that place's day, drawn as the sun's height against the clock. The
 *         lit area is the daylight, so as Earth moves round the orbit the
 *         bright arch swells through summer and shrinks to nothing through a
 *         polar winter.
 *
 * The orbit really is very nearly circular, so the eccentricity control starts
 * at its true value and has to be exaggerated on purpose. Earth is closest to
 * the sun in early January, in the middle of northern winter, which is the
 * quickest way to see that distance is not what makes the seasons.
 */

export default {
  async render({ model, el }) {
    el.classList.add("es-root");
    el.innerHTML = `
      <div class="es-grid">
        <div class="es-panel es-orbit">
          <canvas class="es-c3d"></canvas>
          <div class="es-clock"></div>
          <div class="es-hint">drag to orbit &middot; scroll to zoom</div>
          <div class="es-phase"></div>
        </div>
        <div class="es-panel es-map">
          <canvas class="es-c2d"></canvas>
          <div class="es-hint">click to pick a location</div>
        </div>
      </div>
      ${controlBar(
        playHTML(),
        sliderHTML("speed", "orbit"),
        sliderHTML("light", "earth"),
        sliderHTML("sunlight", "sun"),
        sliderHTML("when", "when"),
      )}
      <div class="es-panel es-sunpanel">
        <canvas class="es-csun"></canvas>
      </div>
      <div class="es-status">loading textures&hellip;</div>`;

    const c3d = el.querySelector(".es-c3d");
    const c2d = el.querySelector(".es-c2d");
    const csun = el.querySelector(".es-csun");
    const clockEl = el.querySelector(".es-clock");
    const seasonEl = el.querySelector(".es-phase");
    const status = el.querySelector(".es-status");

    let THREE, dayImg, nightImg;
    try {
      [THREE, dayImg, nightImg] = await Promise.all([
        getThree(),
        loadImage(TEX.day),
        loadImage(TEX.night),
      ]);
    } catch (err) {
      status.textContent = "could not load three.js or the textures: " + err.message;
      status.classList.add("es-error");
      return;
    }
    status.remove();

    /* ------------------------------------------------------------ the orbit */

    const renderer = new THREE.WebGLRenderer({ canvas: c3d, antialias: true });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
    renderer.setClearColor(0x04060e, 1);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(34, 1, 0.01, 500);
    scene.add(buildStars(THREE, 1800, 90));

    // Same globe as animation 3: one Earth, reused.
    const EARTH_SCALE = 0.12;
    const earth = buildBody(THREE, {
      dayImg,
      nightImg,
      tiltDeg: model.get("obliquity_deg"),
      radius: EARTH_SCALE,
      axis: true,
      graticule: true,
      segments: 96,
      maxAniso: renderer.capabilities.getMaxAnisotropy(),
    });
    scene.add(earth.group);

    // Marks the chosen place on the globe, so you can watch it swing into
    // permanent daylight or permanent night as the year turns.
    const pin = new THREE.Mesh(
      new THREE.SphereGeometry(EARTH_SCALE * 0.09, 12, 10),
      new THREE.MeshBasicMaterial({ color: 0xff5f7e }),
    );
    earth.mesh.add(pin);

    // Nothing here is to scale - the real sun would be a hundred times Earth's
    // width and four hundred times further off - so it is drawn small enough
    // to read as a light source rather than dominate the orbit.
    const SUN_TINT = [1.0, 0.847, 0.541];
    const sun = new THREE.Mesh(
      new THREE.SphereGeometry(0.075, 48, 32),
      new THREE.MeshBasicMaterial({ color: 0xffd88a }),
    );
    scene.add(sun);
    const glow = new THREE.Mesh(
      new THREE.SphereGeometry(0.17, 32, 24),
      new THREE.MeshBasicMaterial({
        color: 0xffbb55,
        transparent: true,
        opacity: 0.14,
      }),
    );
    scene.add(glow);

    /* Exaggerates how far each point strays from the mean radius, leaving the
     * sun at the focus. A stretch of 1 is the real orbit, which looks like a
     * circle because it very nearly is one. */
    function stretched(pos, stretch) {
      const r = Math.hypot(pos[0], pos[1], pos[2]);
      if (r < 1e-9) return [0, 0, 0];
      const scale = (1 + (r - 1) * stretch) / r;
      return [pos[0] * scale, pos[1] * scale, pos[2] * scale];
    }

    let orbitLine = null;
    let builtFor = null;

    function buildOrbit(track, stretch) {
      if (orbitLine) {
        scene.remove(orbitLine);
        orbitLine.geometry.dispose();
      }
      orbitLine = makeLine(
        THREE,
        track.vectors.earth_pos.map(
          (p) => new THREE.Vector3(...stretched(p, stretch)),
        ),
        0x6f8fd0,
        0.55,
      );
      scene.add(orbitLine);
      builtFor = stretch;
    }

    const orbitCam = attachOrbit(c3d, camera, {
      radius: 3.4,
      phi: 0.75,
      minR: 0.4,
      maxR: 9,
    });
    const ro3d = autoSize(c3d, (w, h, dpr) => {
      renderer.setPixelRatio(dpr);
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    });

    /* -------------------------------------------------------------- the map */

    const map = c2d.getContext("2d");
    let mapW = 1;
    let mapH = 1;
    const ro2d = autoSize(c2d, (w, h, dpr) => {
      mapW = w;
      mapH = h;
      map.setTransform(dpr, 0, 0, dpr, 0, 0);
    });

    function drawMap(at) {
      const proj = mapProjection(mapW, mapH);
      map.clearRect(0, 0, mapW, mapH);
      map.drawImage(dayImg, 0, 0, mapW, mapH);
      drawMapFrame(map, proj, mapW, mapH, {
        graticule: model.get("show_graticule"),
      });

      // The latitude the sun stands over, sliding between the tropics as the
      // year passes. This is the tilt, drawn on the ground.
      const y = proj.y(at.declination_deg);
      polyline(map, [[0, y], [mapW, y]], "rgba(255,214,120,0.95)", 2);
      label(
        map,
        "sun overhead here",
        8,
        y - 5,
        "rgba(255,225,160,0.95)",
      );

      dot(map, proj.x(at.longitude_deg), proj.y(at.latitude_deg), "#ff5f7e", 5.5, true);
    }

    c2d.addEventListener("click", (event) => {
      model.set("marker", pickLatLon(c2d, event));
      model.save_changes();
    });

    /* --------------------------------------------------------- the sun path */

    const sky = csun.getContext("2d");
    let sunW = 1;
    let sunH = 1;
    const roSun = autoSize(csun, (w, h, dpr) => {
      sunW = w;
      sunH = h;
      sky.setTransform(dpr, 0, 0, dpr, 0, 0);
    });

    // Fixed scales on both axes: the whole point is that today's arch can be
    // compared with midsummer's and midwinter's.
    const EL_TOP = 90;
    const EL_BOTTOM = -50;

    function drawSunPath(track, at) {
      const g = track.grids.sun_elevation;
      const elevation = gridRowAt(g, at.declination_deg);
      const daylight = tableLookup(track.tables.daylight_hours, at.declination_deg);

      const box = { x: 46, y: 14, w: sunW - 62, h: sunH - 40 };
      const x = (hour) => box.x + (hour / 24) * box.w;
      const y = (elev) =>
        box.y + ((EL_TOP - elev) / (EL_TOP - EL_BOTTOM)) * box.h;
      const horizon = y(0);

      sky.clearRect(0, 0, sunW, sunH);
      sky.fillStyle = "#05070f";
      sky.fillRect(0, 0, sunW, sunH);

      // Night, then the twilight the sun passes through on its way under.
      sky.fillStyle = "#080d1c";
      sky.fillRect(box.x, box.y, box.w, box.h);
      sky.fillStyle = "#101a33";
      sky.fillRect(box.x, horizon, box.w, Math.max(0, y(-18) - horizon));

      const curve = [];
      for (let c = 0; c < g.cols; c++) {
        curve.push([x(gridColValue(g, c)), y(elevation[c])]);
      }

      // Daylight: everything between the arc and the horizon. Brightest where
      // the sun is highest, which is what makes the shape read as a day.
      if (daylight > 0) {
        const gradient = sky.createLinearGradient(0, y(EL_TOP), 0, horizon);
        gradient.addColorStop(0, "rgba(255,240,190,0.95)");
        gradient.addColorStop(0.45, "rgba(255,196,90,0.72)");
        gradient.addColorStop(1, "rgba(255,140,60,0.30)");
        sky.save();
        sky.beginPath();
        sky.moveTo(box.x, horizon);
        for (let c = 0; c < g.cols; c++) {
          sky.lineTo(x(gridColValue(g, c)), y(Math.max(elevation[c], 0)));
        }
        sky.lineTo(box.x + box.w, horizon);
        sky.closePath();
        sky.fillStyle = gradient;
        sky.fill();
        sky.restore();
      }

      // Midsummer and midwinter, as the bounds today's arc lives between.
      for (const [name, style] of [
        ["sun_june", "rgba(255,214,120,0.40)"],
        ["sun_december", "rgba(140,200,255,0.40)"],
      ]) {
        const path = track.paths[name];
        if (path) {
          polyline(sky, path.map(([h, e]) => [x(h), y(e)]), style, 1.3, [4, 3]);
        }
      }

      for (const elev of [-30, 30, 60]) {
        polyline(
          sky,
          [[box.x, y(elev)], [box.x + box.w, y(elev)]],
          "rgba(255,255,255,0.09)",
          1,
        );
        label(sky, elev + "°", box.x - 6, y(elev) + 3, "rgba(255,255,255,0.35)", "right");
      }
      for (let hour = 0; hour <= 24; hour += 3) {
        polyline(
          sky,
          [[x(hour), box.y], [x(hour), box.y + box.h]],
          "rgba(255,255,255,0.07)",
          1,
        );
        label(
          sky,
          String(hour).padStart(2, "0"),
          x(hour),
          box.y + box.h + 15,
          "rgba(255,255,255,0.45)",
          "center",
        );
      }

      polyline(
        sky,
        [[box.x, horizon], [box.x + box.w, horizon]],
        "rgba(255,255,255,0.65)",
        1.5,
      );
      label(sky, "horizon", box.x + 4, horizon - 5, "rgba(255,255,255,0.6)");
      polyline(sky, curve, "rgba(255,226,150,0.95)", 2.2);

      // Sunrise and sunset are symmetric about local noon by construction.
      if (daylight > 0 && daylight < 24) {
        for (const [hour, txt] of [
          [12 - daylight / 2, "sunrise " + fmtHM(12 - daylight / 2)],
          [12 + daylight / 2, "sunset " + fmtHM(12 + daylight / 2)],
        ]) {
          polyline(
            sky,
            [[x(hour), horizon], [x(hour), box.y]],
            "rgba(255,196,90,0.55)",
            1,
            [4, 3],
          );
          label(sky, txt, x(hour) + 4, box.y + 12, "rgba(255,214,140,0.9)");
        }
      }

      const noon = elevation[Math.floor(g.cols / 2)];
      const verdict =
        daylight >= 24
          ? "midnight sun"
          : daylight <= 0
            ? "polar night"
            : fmtHM(daylight).replace(":", " h ") + " m of daylight";
      label(
        sky,
        verdict + "   ·   sun peaks at " + noon.toFixed(1) + "°",
        box.x + box.w,
        box.y - 1,
        "rgba(255,255,255,0.88)",
        "right",
      );
      label(
        sky,
        "local solar time at " +
          Math.abs(at.latitude_deg).toFixed(1) +
          "°" +
          (at.latitude_deg >= 0 ? "N" : "S"),
        box.x,
        box.y - 1,
        "rgba(255,255,255,0.6)",
      );
    }

    /* ------------------------------------------------------------------ loop */

    const play = attachPlay(el, model);
    const speed = attachSlider(el, model, {
      name: "speed",
      trait: "speed",
      min: 0,
      max: 120,
      step: 1,
      unit: "d/s",
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
    const sunlight = attachSlider(el, model, {
      name: "sunlight",
      trait: "sun_brightness",
      min: 0,
      max: 2,
      step: 0.05,
      unit: "\u00d7",
      decimals: 2,
    });

    const when = attachScrubber(el, model, {
      name: "when",
      trait: "day_of_year",
      min: 0,
      max: 365,
      step: 0.5,
      format: (v) => "day " + Math.round(v),
    });

    let day = model.get("day_of_year");
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

      const stretch = model.get("eccentricity_stretch");
      if (builtFor !== stretch) buildOrbit(track, stretch);

      if (when.scrubbing) {
        day = when.value;
      } else if (play.playing) {
        day = (day + dt * speed.value) % 365;
        if (day < 0) day += 365;
      }
      when.follow(day);

      const at = trackSample(track, day);
      const pos = stretched(at.earth_pos, stretch);
      earth.group.position.set(pos[0], pos[1], pos[2]);
      earth.grid.visible = model.get("show_graticule");
      earth.uniforms.uExposure.value = light.value;
      // Keeps the chosen place at local noon, so the hemisphere you are
      // looking at is always the one the sun is shining on.
      earth.mesh.rotation.y = at.spin_marker_noon;

      const glare = Math.min(1, sunlight.value);
      sun.material.color.setRGB(
        SUN_TINT[0] * glare,
        SUN_TINT[1] * glare,
        SUN_TINT[2] * glare,
      );
      glow.material.opacity = 0.14 * sunlight.value;
      pin.position.set(
        ...latLonToVec3(at.latitude_deg, at.longitude_deg, EARTH_SCALE * 1.02),
      );

      // Lighting comes from wherever the sun actually is relative to Earth.
      sunVec.set(-pos[0], -pos[1], -pos[2]).normalize();
      earth.uniforms.uSunDir.value.copy(sunVec);

      orbitCam.state.target = model.get("follow_earth") ? pos : [0, 0, 0];
      orbitCam.apply();

      renderer.render(scene, camera);
      drawMap(at);
      drawSunPath(track, at);

      clockEl.textContent = at.date;
      seasonEl.textContent =
        at.season + " · " + at.distance_au.toFixed(4) + " AU";
    }
    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      play.dispose();
      speed.dispose();
      light.dispose();
      sunlight.dispose();
      when.dispose();
      orbitCam.dispose();
      gate.dispose();
      ro3d.disconnect();
      ro2d.disconnect();
      roSun.disconnect();
      renderer.dispose();
    };
  },
};
