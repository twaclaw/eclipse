/* Animation 6 - latitude, and the height of the pole star.
 *
 * Globe and map : the same point, picked on either and shown on both.
 * Diagram       : why the angle you measure up to Polaris is the angle you
 *                 stand at. Earth in section, the radius to your feet, the
 *                 horizon square to it, and the line to Polaris parallel to
 *                 the axis - because Polaris is far enough away that every
 *                 line drawn to it is the same line.
 *
 * The equality is alternate angles and nothing more, which is why a diagram
 * argues it better than a formula.
 */

export default {
  async render({ model, el }) {
    el.classList.add("es-root");
    el.innerHTML = `
      <div class="es-grid">
        <div class="es-panel es-globe">
          <canvas class="es-c3d"></canvas>
          <div class="es-hint">click the globe &middot; drag to turn</div>
          <div class="es-clock"></div>
        </div>
        <div class="es-panel es-map">
          <canvas class="es-c2d"></canvas>
          <div class="es-hint">or click the map</div>
        </div>
      </div>
      ${controlBar(sliderHTML("lat", "latitude"))}
      <div class="es-panel es-diagram">
        <canvas class="es-cdiag"></canvas>
      </div>
      <div class="es-status">loading textures&hellip;</div>`;

    const c3d = el.querySelector(".es-c3d");
    const c2d = el.querySelector(".es-c2d");
    const cdiag = el.querySelector(".es-cdiag");
    const clockEl = el.querySelector(".es-clock");
    const status = el.querySelector(".es-status");

    let THREE, dayImg;
    try {
      [THREE, dayImg] = await Promise.all([getThree(), loadImage(TEX.day)]);
    } catch (err) {
      status.textContent = "could not load three.js or the textures: " + err.message;
      status.classList.add("es-error");
      return;
    }
    status.remove();

    /* ---------------------------------------------------------- the globe */

    const renderer = new THREE.WebGLRenderer({ canvas: c3d, antialias: true });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
    renderer.setClearColor(0x04060e, 1);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(36, 1, 0.05, 200);
    scene.add(buildStars(THREE, 1200, 60));

    // Lit from the camera rather than the sun: this notebook is about where a
    // place is, so the whole visible face should be readable.
    const earth = buildBody(THREE, {
      dayImg,
      nightImg: null,
      nightGain: 0,
      ambient: 0.10,
      tiltDeg: 0,
      axis: true,
      graticule: true,
      atmosphere: 0.5,
      limbDarkening: 0.5,
      maxAniso: renderer.capabilities.getMaxAnisotropy(),
    });
    scene.add(earth.group);

    const pin = new THREE.Mesh(
      new THREE.SphereGeometry(0.022, 14, 12),
      new THREE.MeshBasicMaterial({ color: 0xff5f7e }),
    );
    earth.mesh.add(pin);

    // The parallel through the chosen place, rebuilt when it moves.
    let ring = null;
    function drawParallel(latDeg) {
      if (ring) {
        earth.mesh.remove(ring);
        ring.geometry.dispose();
      }
      ring = makeLine(
        THREE,
        parallelPoints(THREE, latDeg, 1.004, 180),
        0xff8fa8,
        0.9,
      );
      earth.mesh.add(ring);
    }

    const orbit = attachOrbit(c3d, camera, { radius: 3.1, phi: 1.25 });
    const ro3d = autoSize(c3d, (w, h, dpr) => {
      renderer.setPixelRatio(dpr);
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    });

    // Picking has to share the canvas with the turntable, so a press that
    // travelled more than a few pixels is a drag and not a click.
    const raycaster = new THREE.Raycaster();
    const ndc = new THREE.Vector2();
    let pressed = null;
    c3d.addEventListener("pointerdown", (e) => {
      pressed = { x: e.clientX, y: e.clientY };
    });
    c3d.addEventListener("pointerup", (e) => {
      if (!pressed) return;
      const travelled = Math.hypot(e.clientX - pressed.x, e.clientY - pressed.y);
      pressed = null;
      if (travelled > 4) return;
      const rect = c3d.getBoundingClientRect();
      ndc.set(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1,
      );
      raycaster.setFromCamera(ndc, camera);
      const hit = raycaster.intersectObject(earth.mesh)[0];
      if (!hit) return;
      const local = earth.mesh.worldToLocal(hit.point.clone());
      const [lat, lon] = vec3ToLatLon(local.x, local.y, local.z);
      place(lat, lon);
    });

    /* ------------------------------------------------------------ the map */

    const map = c2d.getContext("2d");
    let mapW = 1;
    let mapH = 1;
    const ro2d = autoSize(c2d, (w, h, dpr) => {
      mapW = w;
      mapH = h;
      map.setTransform(dpr, 0, 0, dpr, 0, 0);
    });

    function drawMap(lat, lon) {
      const proj = mapProjection(mapW, mapH);
      map.clearRect(0, 0, mapW, mapH);
      map.drawImage(dayImg, 0, 0, mapW, mapH);
      drawMapFrame(map, proj, mapW, mapH, { graticule: true });
      const y = proj.y(lat);
      polyline(map, [[0, y], [mapW, y]], "rgba(255,143,168,0.95)", 2);
      dot(map, proj.x(lon), y, "#ff5f7e", 5.5, true);
    }

    c2d.addEventListener("click", (event) => {
      const [lat, lon] = pickLatLon(c2d, event);
      place(lat, lon);
    });

    /* -------------------------------------------------------- the diagram */

    const dia = cdiag.getContext("2d");
    let diaW = 1;
    let diaH = 1;
    const roDia = autoSize(cdiag, (w, h, dpr) => {
      diaW = w;
      diaH = h;
      dia.setTransform(dpr, 0, 0, dpr, 0, 0);
    });

    const INK = "#1d2433";
    const FAINT = "#9aa4b8";
    const LAT_COLOUR = "#c2410c";
    const CO_COLOUR = "#1d4ed8";

    function arc(cx, cy, r, from, to, colour, width) {
      dia.save();
      dia.strokeStyle = colour;
      dia.lineWidth = width || 2;
      dia.beginPath();
      dia.arc(cx, cy, r, from, to, to < from);
      dia.stroke();
      dia.restore();
    }

    function tick(x, y, dx, dy, colour) {
      // A chevron, the schoolbook mark for "these two lines are parallel".
      const nx = -dy;
      const ny = dx;
      polyline(
        dia,
        [
          [x - dx * 6 + nx * 5, y - dy * 6 + ny * 5],
          [x + dx * 4, y + dy * 4],
          [x - dx * 6 - nx * 5, y - dy * 6 - ny * 5],
        ],
        colour,
        1.6,
      );
    }

    /* Polaris is 0.65 degrees off the pole, which at any scale that fits on a
     * screen is under a pixel. It is drawn far larger than that and said so;
     * the alternative is a figure that cannot show the thing it is about. */
    const ERROR_DRAW = 0.15;

    /* Halfway round the short way between two angles, for putting a label
     * inside the wedge it belongs to. */
    function midAngle(from, to) {
      let delta = (to - from) % (Math.PI * 2);
      if (delta > Math.PI) delta -= Math.PI * 2;
      if (delta < -Math.PI) delta += Math.PI * 2;
      return from + delta / 2;
    }

    function angleLabel(x, y, from, to, r, text, colour) {
      const at = midAngle(from, to);
      label(dia, text, x + r * Math.cos(at), y + r * Math.sin(at) + 4, colour, "center");
    }

    function star(x, y, r, colour) {
      dia.save();
      dia.fillStyle = colour;
      dia.beginPath();
      for (let i = 0; i < 10; i++) {
        const a = -Math.PI / 2 + (i * Math.PI) / 5;
        const rad = i % 2 ? r * 0.42 : r;
        const sx = x + Math.cos(a) * rad;
        const sy = y + Math.sin(a) * rad;
        if (i) dia.lineTo(sx, sy);
        else dia.moveTo(sx, sy);
      }
      dia.closePath();
      dia.fill();
      dia.restore();
    }

    function dottedCircle(x, y, r, colour, dash) {
      dia.save();
      dia.setLineDash(dash || []);
      dia.strokeStyle = colour;
      dia.lineWidth = 1.4;
      dia.beginPath();
      dia.arc(x, y, r, 0, Math.PI * 2);
      dia.stroke();
      dia.restore();
    }

    function drawDiagram(readout) {
      const lat = readout.latitude_deg;
      const phi = lat * DEG;
      const R = Math.min(diaW * 0.30, diaH * 0.35);
      const cx = R + 34;
      const cy = diaH - R - 34;
      const textX = Math.max(cx + R + 56, diaW * 0.6);

      dia.clearRect(0, 0, diaW, diaH);
      dia.fillStyle = "#fbfaf6";
      dia.fillRect(0, 0, diaW, diaH);

      // Earth in section, the equator across it and the axis running up.
      dia.save();
      dia.strokeStyle = INK;
      dia.lineWidth = 2;
      dia.beginPath();
      dia.arc(cx, cy, R, 0, Math.PI * 2);
      dia.stroke();
      dia.restore();

      polyline(dia, [[cx - R * 1.3, cy], [cx + R * 1.35, cy]], FAINT, 1.4, [6, 4]);
      label(dia, "equator", cx - R * 1.3, cy - 8, FAINT);
      polyline(dia, [[cx, cy + R * 1.2], [cx, 8]], CO_COLOUR, 1.4, [5, 5]);
      label(dia, "Earth's axis", cx + 7, cy - R * 1.12, CO_COLOUR);

      // The place, its radius, and the angle that names it.
      const px = cx + R * Math.cos(phi);
      const py = cy - R * Math.sin(phi);
      polyline(dia, [[cx, cy], [px, py]], INK, 2);
      arc(cx, cy, R * 0.26, 0, -phi, LAT_COLOUR, 2.5);
      angleLabel(cx, cy, 0, -phi, R * 0.38, "φ", LAT_COLOUR);
      arc(cx, cy, R * 0.46, -phi, -Math.PI / 2, CO_COLOUR, 1.8);
      angleLabel(cx, cy, -phi, -Math.PI / 2, R * 0.60, "θ", CO_COLOUR);

      // Horizon, zenith, and the sight line north.
      const zx = Math.cos(phi);
      const zy = -Math.sin(phi);
      const hx = -Math.sin(phi);
      const hy = -Math.cos(phi);
      const reach = R * 0.95;
      polyline(
        dia,
        [
          [px - hx * reach * 0.7, py - hy * reach * 0.7],
          [px + hx * reach, py + hy * reach],
        ],
        INK,
        2,
      );
      polyline(
        dia,
        [[px, py], [px + zx * reach * 0.6, py + zy * reach * 0.6]],
        FAINT,
        1.4,
        [4, 4],
      );

      // The true celestial pole: dotted, exactly parallel to the axis. This is
      // the direction the whole argument is about; Polaris only approximates it.
      const poleLength = R * 0.72;
      const poleY = py - poleLength;
      const blocked = !readout.visible && lat !== 0;
      polyline(
        dia,
        [[px, py], [px, poleY]],
        blocked ? "rgba(29,78,216,0.35)" : CO_COLOUR,
        1.8,
        [3, 4],
      );

      // Polaris rides a small circle round that pole, once a day. The radius of
      // this circle is the error, and it is what "approximately" means.
      const errorPx = poleLength * ERROR_DRAW;
      dottedCircle(px, poleY, errorPx, "rgba(194,65,12,0.55)", [3, 3]);
      const wander = -0.6;
      const sx = px + errorPx * Math.cos(wander);
      const sy = poleY + errorPx * Math.sin(wander);
      polyline(dia, [[px, py], [sx, sy]], LAT_COLOUR, 1.6);
      star(sx, sy, 9, blocked ? "rgba(194,65,12,0.45)" : "#e8a33d");
      label(dia, "Polaris", sx + 13, sy + 4, INK);
      label(dia, "true pole", px + 8, poleY - errorPx - 8, CO_COLOUR);
      label(
        dia,
        readout.polaris_separation_deg.toFixed(2) + "° off — drawn far larger",
        px + 8,
        poleY - errorPx - 24,
        LAT_COLOUR,
      );

      // The two angles the proof turns on, measured to the true pole.
      const toPole = -Math.PI / 2;
      const toHorizon = Math.atan2(hy, hx);
      const toZenith = Math.atan2(zy, zx);
      arc(px, py, R * 0.34, toHorizon, toPole, LAT_COLOUR, 2.5);
      angleLabel(px, py, toHorizon, toPole, R * 0.46, "φ′", LAT_COLOUR);
      arc(px, py, R * 0.50, toPole, toZenith, CO_COLOUR, 1.8);
      angleLabel(px, py, toPole, toZenith, R * 0.64, "θ′", CO_COLOUR);

      dot(dia, px, py, "#ff5f7e", 5, false);
      label(dia, "you", px + hx * 18 - 22, py + hy * 18 + 4, INK);
      label(dia, "horizon", px + hx * reach - 6, py + hy * reach - 8, INK, "right");
      label(dia, "zenith", px + zx * reach * 0.64, py + zy * reach * 0.64 + 4, FAINT);
      if (blocked) {
        label(dia, "Earth is in the way", px + 10, py - poleLength * 0.45, FAINT);
      }

      square(cx, cy, 1, 0, 0, -1, FAINT);
      square(px, py, hx, hy, zx, zy, FAINT);

      const co = 90 - lat;
      const lines = [
        "φ   angle at Earth's centre, equator to you   = " + lat.toFixed(1) + "°",
        "θ   angle at Earth's centre, axis to you      = " + co.toFixed(1) + "°",
        "θ′  angle at your feet, pole to your zenith   = " + co.toFixed(1) + "°",
        "φ′  angle at your feet, horizon to the pole   = " + lat.toFixed(1) + "°",
        "",
        "Polaris is 433 light years off, so every line drawn to it is parallel",
        "to Earth's axis. Your radius cuts both of those parallels, which makes",
        "θ′ = θ: alternate angles, nothing more.",
        "",
        "Your zenith runs along that radius and your horizon is square to it,",
        "so φ′ = 90° − θ′ = 90° − θ = φ.",
        "",
        "The two orange angles are therefore the same angle, which is why the",
        "height of the pole tells you where you are.",
        "",
        "The dotted circle is the only slack in it. Polaris sits "
          + readout.polaris_separation_deg.toFixed(2) + "° from",
        "the true pole and circles it once a day, so its height wanders that",
        "much either side of your latitude.",
        "",
        readout.headline,
      ];
      lines.forEach((line, i) => {
        label(
          dia,
          line,
          textX,
          32 + i * 19,
          i === lines.length - 1 ? LAT_COLOUR : INK,
        );
      });
    }

    function square(x, y, ax, ay, bx, by, colour) {
      const k = 11;
      polyline(
        dia,
        [
          [x + ax * k, y + ay * k],
          [x + ax * k + bx * k, y + ay * k + by * k],
          [x + bx * k, y + by * k],
        ],
        colour,
        1.2,
      );
    }

    /* -------------------------------------------------------------- state */

    const latitude = attachSlider(el, model, {
      name: "lat",
      trait: "latitude",
      min: -90,
      max: 90,
      step: 0.5,
      unit: "°",
      decimals: 1,
    });

    function place(lat, lon) {
      model.set("latitude", Math.round(lat * 100) / 100);
      model.set("longitude", Math.round(lon * 100) / 100);
      model.save_changes();
      latitude.set(Math.round(lat * 100) / 100);
    }

    let shownLat = null;
    let raf = 0;
    const gate = visibilityGate(el);

    function frame() {
      raf = requestAnimationFrame(frame);
      if (!gate.visible || document.hidden) return;

      const lat = latitude.value;
      const lon = model.get("longitude");
      if (lat !== shownLat) {
        shownLat = lat;
        drawParallel(lat);
      }
      pin.position.set(...latLonToVec3(lat, lon, 1.02));
      earth.uniforms.uSunDir.value.copy(camera.position).normalize();

      renderer.render(scene, camera);
      drawMap(lat, lon);
      drawDiagram(model.get("readout"));
      clockEl.textContent =
        Math.abs(lat).toFixed(1) + "°" + (lat >= 0 ? "N" : "S");
    }
    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      latitude.dispose();
      orbit.dispose();
      gate.dispose();
      ro3d.disconnect();
      ro2d.disconnect();
      roDia.disconnect();
      renderer.dispose();
    };
  },
};
