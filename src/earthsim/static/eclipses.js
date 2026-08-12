/* Animation 4 - eclipses.
 *
 * View    : what you would actually see. A photographic Moon with Earth's
 *           shadow crossing it, or the sun's disc going behind the Moon.
 * Shadow  : the same event drawn flat, looking down the shadow's axis, so the
 *           track through (or past) the umbra is unmistakable.
 * Side    : the whole system edge-on and, unusually for a diagram like this,
 *           entirely to scale. Sixty Earth radii of gap, a shadow that runs
 *           out after two hundred, and a Moon that misses it by a whisker.
 *
 * The node control is the point of the thing: alignments happen monthly, but
 * they only become eclipses near the two places the Moon's orbit crosses the
 * plane of Earth's.
 */

export default {
  async render({ model, el }) {
    el.classList.add("es-root");
    el.innerHTML = `
      <div class="es-grid es-grid-even">
        <div class="es-panel es-eclipseview">
          <canvas class="es-csolar"></canvas>
          <canvas class="es-c3d"></canvas>
          <div class="es-clock"></div>
          <div class="es-phase"></div>
        </div>
        <div class="es-panel es-shadowplane">
          <canvas class="es-c2d"></canvas>
          <div class="es-hint">down the shadow's axis</div>
        </div>
      </div>
      <div class="es-panel es-sidepanel">
        <canvas class="es-cside"></canvas>
        <div class="es-hint">to scale &middot; drag to turn &middot; scroll or use zoom</div>
        <div class="es-scale"></div>
      </div>
      ${controlBar(
        playHTML(),
        sliderHTML("speed", "time"),
        sliderHTML("node", "node"),
        sliderHTML("zoom", "zoom"),
        sliderHTML("when", "when"),
      )}
      <div class="es-status">loading textures&hellip;</div>`;

    const c3d = el.querySelector(".es-c3d");
    const c2d = el.querySelector(".es-c2d");
    const csolar = el.querySelector(".es-csolar");
    const cside = el.querySelector(".es-cside");
    const clockEl = el.querySelector(".es-clock");
    const scaleEl = el.querySelector(".es-scale");
    const kindEl = el.querySelector(".es-phase");
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

    /* ------------------------------------------------- the Moon, eclipsed */

    const renderer = new THREE.WebGLRenderer({ canvas: c3d, antialias: true });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
    renderer.setClearColor(0x05060c, 1);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(30, 1, 0.05, 200);
    scene.add(buildStars(THREE, 1200, 60));

    // A full moon, so the sun is behind us and the disc is evenly lit. The low
    // limb-darkening exponent is what makes it read flat, the way the real
    // full moon does, instead of like a shaded ball.
    const moon = buildBody(THREE, {
      dayImg: moonImg,
      nightImg: null,
      nightGain: 0,
      ambient: 0.02,
      twilight: 0.015,
      atmosphere: 0,
      limbDarkening: 0.22,
      exposure: 1.15,
      segments: 128,
      maxAniso: renderer.capabilities.getMaxAnisotropy(),
    });
    moon.uniforms.uSunDir.value.set(0, 0, 1);
    scene.add(moon.group);

    // Fixed viewpoint: you are on Earth, and the shadow is placed in the view
    // plane, so orbiting the camera would quietly misplace it.
    camera.position.set(0, 0, 3.4);
    camera.lookAt(0, 0, 0);
    const ro3d = autoSize(c3d, (w, h, dpr) => {
      renderer.setPixelRatio(dpr);
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    });

    /* --------------------------------------------------- the sun, eclipsed */

    const solar = csolar.getContext("2d");
    let solarW = 1;
    let solarH = 1;
    const roSolar = autoSize(csolar, (w, h, dpr) => {
      solarW = w;
      solarH = h;
      solar.setTransform(dpr, 0, 0, dpr, 0, 0);
    });

    function drawSolar(track, at) {
      const s = track.scalars;
      const perDeg = Math.min(solarW, solarH) / 2 / (s.sun_radius_deg * 3.6);
      const cx = solarW / 2;
      const cy = solarH / 2;
      const mx = cx + at.dlon_deg * perDeg;
      const my = cy - at.latitude_deg * perDeg;
      const gap = Math.hypot(mx - cx, my - cy) / perDeg;
      const hidden = Math.max(
        0,
        Math.min(1, (s.moon_radius_deg + s.sun_radius_deg - gap) / (2 * s.sun_radius_deg)),
      );

      // The sky itself darkens as the sun goes, which is most of what makes a
      // deep partial eclipse feel strange.
      const dusk = Math.pow(Math.max(0, hidden), 4);
      const sky = solar.createLinearGradient(0, 0, 0, solarH);
      sky.addColorStop(0, "rgb(" + Math.round(10 + 20 * (1 - dusk)) + ","
        + Math.round(16 + 34 * (1 - dusk)) + "," + Math.round(34 + 60 * (1 - dusk)) + ")");
      sky.addColorStop(1, "rgb(" + Math.round(6 + 26 * (1 - dusk)) + ","
        + Math.round(9 + 26 * (1 - dusk)) + "," + Math.round(20 + 40 * (1 - dusk)) + ")");
      solar.fillStyle = sky;
      solar.fillRect(0, 0, solarW, solarH);

      const moonPx = s.moon_radius_deg * perDeg;
      const sunPx = s.sun_radius_deg * perDeg;
      const totality = gap < s.moon_radius_deg - s.sun_radius_deg;

      if (totality) {
        // Corona: a soft halo with a few streamers, which is the whole reason
        // people travel for these.
        const halo = solar.createRadialGradient(cx, cy, moonPx * 0.98, cx, cy, moonPx * 4);
        halo.addColorStop(0, "rgba(255,250,235,0.75)");
        halo.addColorStop(0.18, "rgba(255,243,215,0.30)");
        halo.addColorStop(1, "rgba(255,238,205,0)");
        solar.fillStyle = halo;
        solar.beginPath();
        solar.arc(cx, cy, moonPx * 4, 0, Math.PI * 2);
        solar.fill();

        solar.save();
        solar.translate(cx, cy);
        for (let i = 0; i < 16; i++) {
          const a = (i / 16) * Math.PI * 2 + 0.3;
          const reach = moonPx * (2.1 + 1.9 * Math.abs(Math.cos(a * 1.5)));
          const streak = solar.createLinearGradient(
            Math.cos(a) * moonPx, Math.sin(a) * moonPx,
            Math.cos(a) * reach, Math.sin(a) * reach,
          );
          streak.addColorStop(0, "rgba(255,250,238,0.34)");
          streak.addColorStop(1, "rgba(255,246,225,0)");
          solar.strokeStyle = streak;
          solar.lineWidth = moonPx * 0.30;
          solar.beginPath();
          solar.moveTo(Math.cos(a) * moonPx, Math.sin(a) * moonPx);
          solar.lineTo(Math.cos(a) * reach, Math.sin(a) * reach);
          solar.stroke();
        }
        solar.restore();
      }

      const disc = solar.createRadialGradient(cx, cy, 0, cx, cy, sunPx);
      disc.addColorStop(0, "#fffef7");
      disc.addColorStop(0.86, "#ffeeb4");
      disc.addColorStop(1, "#ffca6a");
      solar.save();
      solar.shadowColor = "rgba(255,214,120,0.85)";
      solar.shadowBlur = totality ? 0 : sunPx * 0.5;
      solar.fillStyle = disc;
      solar.beginPath();
      solar.arc(cx, cy, sunPx, 0, Math.PI * 2);
      solar.fill();
      solar.restore();

      // The Moon itself: a hole, lit only by earthshine.
      solar.fillStyle = "#0a0c14";
      solar.beginPath();
      solar.arc(mx, my, moonPx, 0, Math.PI * 2);
      solar.fill();

      label(solar, (hidden * 100).toFixed(0) + "% of the sun covered",
            solarW / 2, solarH - 10, "rgba(255,255,255,0.72)", "center");
    }

    /* --------------------------------------------- looking down the shadow */

    const plane = c2d.getContext("2d");
    let planeW = 1;
    let planeH = 1;
    const roPlane = autoSize(c2d, (w, h, dpr) => {
      planeW = w;
      planeH = h;
      plane.setTransform(dpr, 0, 0, dpr, 0, 0);
    });

    // Earth as a photograph rather than a blue circle, projected once and
    // reused every frame.
    let earthDisc = null;
    let earthDiscSize = 0;

    function drawPlane(track, at) {
      const s = track.scalars;
      const lunar = s.kind === "lunar";
      const cx = planeW / 2;
      const cy = planeH / 2;

      plane.clearRect(0, 0, planeW, planeH);
      plane.fillStyle = "#05070f";
      plane.fillRect(0, 0, planeW, planeH);

      // Everything is measured from the shadow's axis: degrees for the lunar
      // case, Earth radii for the solar one.
      const outer = lunar ? s.penumbra_radius_deg * 1.55 : 2.1;
      const per = Math.min(planeW, planeH) / 2 / outer;
      const toX = lunar ? at.dlon_deg : at.dlon_deg * s.earth_radii_per_deg;
      const toY = lunar ? at.latitude_deg : at.latitude_deg * s.earth_radii_per_deg;

      const ring = (r, fill, stroke) => {
        plane.beginPath();
        plane.arc(cx, cy, r * per, 0, Math.PI * 2);
        if (fill) {
          plane.fillStyle = fill;
          plane.fill();
        }
        if (stroke) {
          plane.strokeStyle = stroke;
          plane.lineWidth = 1.2;
          plane.stroke();
        }
      };

      if (lunar) {
        ring(s.penumbra_radius_deg, "rgba(90,115,170,0.20)", "rgba(150,180,230,0.45)");
        ring(s.umbra_radius_deg, "rgba(12,8,16,0.92)", "rgba(190,120,90,0.55)");
        label(plane, "penumbra", cx + s.penumbra_radius_deg * per + 4, cy - 4,
              "rgba(150,180,230,0.8)");
        label(plane, "umbra", cx + s.umbra_radius_deg * per + 4, cy + 12,
              "rgba(210,140,110,0.9)");
      } else {
        if (earthDiscSize !== Math.round(per * 2)) {
          earthDiscSize = Math.max(24, Math.round(per * 2));
          earthDisc = globeDisc(earthImg, earthDiscSize, 0, true);
        }
        plane.drawImage(earthDisc, cx - per, cy - per, per * 2, per * 2);
        ring(1, null, "rgba(150,180,230,0.35)");
      }

      // The path the Moon takes across the shadow during the window shown.
      const first = gridValueAt(track.grids.latitude_deg, model.get("node_offset_deg"), track.t[0]);
      const last = gridValueAt(
        track.grids.latitude_deg,
        model.get("node_offset_deg"),
        track.t[track.t.length - 1],
      );
      const scaleY = lunar ? 1 : s.earth_radii_per_deg;
      const scaleX = lunar ? 1 : s.earth_radii_per_deg;
      polyline(
        plane,
        [
          [cx + track.channels.dlon_deg[0] * scaleX * per, cy - first * scaleY * per],
          [
            cx + track.channels.dlon_deg[track.t.length - 1] * scaleX * per,
            cy - last * scaleY * per,
          ],
        ],
        "rgba(255,255,255,0.30)",
        1,
        [5, 4],
      );

      if (!lunar) {
        // The Moon's penumbra on Earth is a patch a few thousand km across;
        // the umbra inside it is the sliver where the eclipse is total.
        const spot = plane.createRadialGradient(
          cx + toX * per, cy - toY * per, 0,
          cx + toX * per, cy - toY * per, s.moon_penumbra_earth_radii * per,
        );
        spot.addColorStop(0, "rgba(4,6,14,0.82)");
        spot.addColorStop(1, "rgba(4,6,14,0)");
        plane.fillStyle = spot;
        plane.beginPath();
        plane.arc(cx + toX * per, cy - toY * per, s.moon_penumbra_earth_radii * per, 0, Math.PI * 2);
        plane.fill();
        if (s.moon_umbra_earth_radii > 0) {
          dot(plane, cx + toX * per, cy - toY * per, "#12060a",
              Math.max(2, s.moon_umbra_earth_radii * per), false);
        }
      } else {
        plane.save();
        plane.globalAlpha = 0.95;
        plane.drawImage(
          moonDisc(s),
          cx + toX * per - s.moon_radius_deg * per,
          cy - toY * per - s.moon_radius_deg * per,
          s.moon_radius_deg * per * 2,
          s.moon_radius_deg * per * 2,
        );
        plane.restore();
      }

      label(plane, lunar ? "Earth's shadow" : "the Moon's shadow on Earth",
            8, 16, "rgba(255,255,255,0.62)");
    }

    let moonDiscCache = null;
    let moonDiscKey = 0;
    function moonDisc(s) {
      const size = 96;
      if (!moonDiscCache || moonDiscKey !== size) {
        moonDiscCache = globeDisc(moonImg, size, 0, true);
        moonDiscKey = size;
      }
      return moonDiscCache;
    }

    /* ------------------------------------------------- the system, to scale */

    const sideRenderer = new THREE.WebGLRenderer({ canvas: cside, antialias: true });
    sideRenderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    sideRenderer.outputColorSpace = THREE.LinearSRGBColorSpace;
    sideRenderer.setClearColor(0x04060e, 1);

    const sideScene = new THREE.Scene();
    sideScene.add(buildStars(THREE, 900, 400));
    const sideCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, -2000, 2000);
    let sideBuiltFor = "";
    let casterGroup = null;
    let targetGroup = null;

    function cone(rNear, rFar, length, x0, color, opacity) {
      const geo = new THREE.CylinderGeometry(rFar, rNear, length, 64, 1, true);
      geo.rotateZ(-Math.PI / 2);
      geo.translate(x0 + length / 2, 0, 0);
      return new THREE.Mesh(
        geo,
        new THREE.MeshBasicMaterial({
          color,
          transparent: true,
          opacity,
          side: THREE.DoubleSide,
          depthWrite: false,
        }),
      );
    }

    function buildSide(track) {
      const s = track.scalars;
      const key = s.kind + ":" + s.moon_distance_km;
      if (sideBuiltFor === key) return;
      sideBuiltFor = key;

      for (const group of [casterGroup, targetGroup]) {
        if (group) sideScene.remove(group);
      }
      casterGroup = new THREE.Group();
      targetGroup = new THREE.Group();
      const lunar = s.kind === "lunar";
      const distance = s.moon_distance_earth_radii;

      const earth = buildBody(THREE, {
        dayImg: earthImg,
        nightImg: null,
        nightGain: 0,
        ambient: 0.03,
        atmosphere: 0.6,
        segments: 96,
        radius: 1,
        maxAniso: sideRenderer.capabilities.getMaxAnisotropy(),
      });
      earth.uniforms.uSunDir.value.set(-1, 0, 0);
      const luna = buildBody(THREE, {
        dayImg: moonImg,
        nightImg: null,
        nightGain: 0,
        ambient: 0.02,
        atmosphere: 0,
        segments: 64,
        radius: s.moon_earth_radii,
        maxAniso: sideRenderer.capabilities.getMaxAnisotropy(),
      });
      luna.uniforms.uSunDir.value.set(-1, 0, 0);

      if (lunar) {
        casterGroup.add(earth.group);
        casterGroup.add(cone(1, s.penumbra_earth_radii, distance * 1.12, 0, 0x8fb4ff, 0.10));
        casterGroup.add(cone(1, s.umbra_earth_radii, distance * 1.12, 0, 0x0a0d1c, 0.85));
        targetGroup.add(luna.group);
      } else {
        casterGroup.add(luna.group);
        const apex = s.moon_umbra_apex_earth_radii;
        casterGroup.add(
          cone(s.moon_earth_radii, s.moon_penumbra_earth_radii, distance * 1.05, 0, 0x8fb4ff, 0.10),
        );
        // Converges to a point, then opens out again. Whether Earth sits
        // before or after that point is total against annular.
        casterGroup.add(cone(s.moon_earth_radii, 0.0005, apex, 0, 0x0a0d1c, 0.9));
        casterGroup.add(
          cone(0.0005, s.moon_earth_radii * 0.5, Math.max(0.001, distance * 1.05 - apex), apex, 0x0a0d1c, 0.45),
        );
        targetGroup.add(earth.group);
      }

      casterGroup.add(
        makeLine(
          THREE,
          [new THREE.Vector3(0, 0, 0), new THREE.Vector3(distance * 1.25, 0, 0)],
          0x9fb6e8,
          0.35,
        ),
      );

      // Sunlight, coming in parallel from the left.
      for (let i = -3; i <= 3; i++) {
        casterGroup.add(
          makeLine(
            THREE,
            [
              new THREE.Vector3(-distance * 0.16, i * 1.4, 0),
              new THREE.Vector3(-1.8, i * 1.4, 0),
            ],
            0xffd27f,
            0.35,
          ),
        );
      }

      sideScene.add(casterGroup);
      sideScene.add(targetGroup);
      view.state.span = distance * 1.3;
      view.apply();
    }

    // Zoomed out it is the whole system; zoomed in it closes on whichever body
    // the shadow is falling across, which is where anything actually moves.
    const view = attachOrthoView(cside, sideCamera, {
      span: 74,
      zoom: 5,
      // Turned away from dead edge-on on purpose: the Moon's crossing runs
      // almost entirely across the shadow axis, which an edge-on view hides.
      yaw: -0.62,
      pitch: 0.30,
      minZoom: 1,
      maxZoom: 24,
      onZoom: (z) => {
        zoom.set(z);
        zoom.commit();
      },
    });

    const roSide = autoSize(cside, (w, h, dpr) => {
      sideRenderer.setPixelRatio(dpr);
      sideRenderer.setSize(w, h, false);
      view.state.aspect = w / h;
      view.apply();
    });

    // The stretch of orbit the Moon covers in the window on screen. Without it
    // the Moon is a dot with no visible reason to be going anywhere.
    let arcLine = null;
    let arcBuiltFor = null;

    function buildArc(track, nodeOffset) {
      const s = track.scalars;
      const key = s.kind + ":" + s.moon_distance_km + ":" + nodeOffset.toFixed(2);
      if (arcBuiltFor === key) return;
      arcBuiltFor = key;
      if (arcLine) {
        sideScene.remove(arcLine);
        arcLine.geometry.dispose();
      }
      const lunar = s.kind === "lunar";
      const latitude = gridRowAt(track.grids.latitude_deg, nodeOffset);
      const points = [];
      for (let i = 0; i < track.t.length; i += 2) {
        points.push(
          new THREE.Vector3(...moonPlace(s, track, latitude[i], i, lunar)),
        );
      }
      arcLine = makeLine(THREE, points, 0xff9ec2, 0.65);
      sideScene.add(arcLine);
    }

    /* Where the Moon sits in the side view, in Earth radii. */
    function moonPlace(s, track, latitudeDeg, index, lunar) {
      const along = track.channels.moon_axis_re[index];
      const across = track.channels.moon_cross_re[index];
      const up = latitudeDeg * s.earth_radii_per_deg;
      return lunar
        ? [along, up, across]
        : [s.moon_distance_earth_radii - along, up, across];
    }

    /* ------------------------------------------------------------ controls */

    const play = attachPlay(el, model);
    const speed = attachSlider(el, model, {
      name: "speed",
      trait: "speed",
      min: 0,
      max: 1.5,
      step: 0.05,
      unit: "h/s",
      decimals: 2,
    });
    const node = attachSlider(el, model, {
      name: "node",
      trait: "node_offset_deg",
      min: -12,
      max: 12,
      step: 0.1,
      unit: "°",
      decimals: 1,
    });
    const zoom = attachSlider(el, model, {
      name: "zoom",
      trait: "side_zoom",
      min: 1,
      max: 24,
      step: 0.5,
      unit: "×",
      decimals: 1,
    });

    const span = (model.get("track").scalars || {}).span_hours || 6;
    const when = attachScrubber(el, model, {
      name: "when",
      trait: "hours",
      min: -span,
      max: span,
      step: 0.05,
      format: (v) => (v >= 0 ? "+" : "\u2212") + fmtHM(Math.abs(v)),
    });

    let hours = model.get("hours");
    let last = performance.now();
    let raf = 0;
    const gate = visibilityGate(el);

    function frame(now) {
      raf = requestAnimationFrame(frame);
      const dt = Math.min(0.08, (now - last) / 1000);
      last = now;
      if (!gate.visible || document.hidden) return;

      const track = model.get("track");
      if (!track || !track.t) return;
      const s = track.scalars;
      const lunar = s.kind === "lunar";
      buildSide(track);

      if (when.scrubbing) {
        hours = when.value;
      } else if (play.playing) {
        hours += dt * speed.value;
        if (hours > s.span_hours) hours = -s.span_hours;
      }
      when.follow(hours);

      const at = trackSample(track, hours);
      at.latitude_deg = gridValueAt(track.grids.latitude_deg, node.value, hours);
      const height = at.latitude_deg * s.earth_radii_per_deg;

      c3d.style.display = lunar ? "block" : "none";
      csolar.style.display = lunar ? "none" : "block";

      if (lunar) {
        const perMoon = 1 / s.moon_radius_deg;
        moon.uniforms.uShadowCentre.value.set(
          -at.dlon_deg * perMoon,
          -at.latitude_deg * perMoon,
        );
        moon.uniforms.uUmbraR.value = s.umbra_radius_deg * perMoon;
        moon.uniforms.uPenumbraR.value = s.penumbra_radius_deg * perMoon;
        renderer.render(scene, camera);
      } else {
        drawSolar(track, at);
      }

      buildArc(track, node.value);
      const along = sampleChannel(hours, track.t, track.channels.moon_axis_re);
      const across = sampleChannel(hours, track.t, track.channels.moon_cross_re);
      if (lunar) {
        targetGroup.position.set(along, height, across);
      } else {
        casterGroup.position.set(
          s.moon_distance_earth_radii - along,
          height,
          across,
        );
        targetGroup.position.set(s.moon_distance_earth_radii, 0, 0);
      }

      drawPlane(track, at);

      // Pull the camera towards the shadow's business end as it zooms in: the
      // Moon for a lunar eclipse, Earth for a solar one. Zoomed out it frames
      // the whole system instead.
      view.state.zoom = zoom.value;
      const closeness = Math.max(0, Math.min(1, (zoom.value - 1) / 2.5));
      const wide = s.moon_distance_earth_radii * 0.42;
      const onto = s.moon_distance_earth_radii;
      view.state.target = [
        wide + (onto - wide) * closeness,
        (lunar ? height : 0) * closeness,
        (lunar ? across : 0) * closeness,
      ];
      view.apply();
      sideRenderer.render(sideScene, sideCamera);

      const acrossRe = view.state.span / view.state.zoom;
      scaleEl.textContent =
        Math.round(acrossRe) + " Earth radii across · " +
        Math.round(acrossRe * 6371).toLocaleString() + " km";

      clockEl.textContent =
        (hours >= 0 ? "+" : "−") + fmtHM(Math.abs(hours)) + " from alignment";
      kindEl.textContent = lunar ? "Lunar eclipse" : "Solar eclipse";
    }
    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      play.dispose();
      speed.dispose();
      node.dispose();
      zoom.dispose();
      when.dispose();
      gate.dispose();
      ro3d.disconnect();
      roPlane.disconnect();
      roSolar.disconnect();
      roSide.disconnect();
      renderer.dispose();
      sideRenderer.dispose();
    };
  },
};
