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
      // Not recursive: the mesh carries a graticule, a parallel and a pin, and
      // three's line intersections use a world-space threshold of 1 - enormous
      // against a globe of radius 1. Left on, every click snapped to the
      // nearest 30-degree line instead of landing where it was aimed.
      const hit = raycaster.intersectObject(earth.mesh, false)[0];
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

    function arc(ctx, cx, cy, r, from, to, colour, width) {
      ctx.save();
      ctx.strokeStyle = colour;
      ctx.lineWidth = width || 2;
      ctx.beginPath();
      ctx.arc(cx, cy, r, from, to, to < from);
      ctx.stroke();
      ctx.restore();
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

    function angleLabel(ctx, x, y, from, to, r, text, colour) {
      const at = midAngle(from, to);
      label(ctx, text, x + r * Math.cos(at), y + r * Math.sin(at) + 4, colour, "center");
    }

    function star(ctx, x, y, r, colour) {
      ctx.save();
      ctx.fillStyle = colour;
      ctx.beginPath();
      for (let i = 0; i < 10; i++) {
        const a = -Math.PI / 2 + (i * Math.PI) / 5;
        const rad = i % 2 ? r * 0.42 : r;
        const sx = x + Math.cos(a) * rad;
        const sy = y + Math.sin(a) * rad;
        if (i) ctx.lineTo(sx, sy);
        else ctx.moveTo(sx, sy);
      }
      ctx.closePath();
      ctx.fill();
      ctx.restore();
    }

    function dottedCircle(ctx, x, y, r, colour, dash, width) {
      ctx.save();
      ctx.setLineDash(dash || []);
      ctx.strokeStyle = colour;
      ctx.lineWidth = width || 1.4;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.stroke();
      ctx.restore();
    }

    /* The right-angle mark, for the two corners the proof leans on. */
    function square(ctx, x, y, ax, ay, bx, by, colour) {
      const k = 10;
      polyline(
        ctx,
        [
          [x + ax * k, y + ay * k],
          [x + ax * k + bx * k, y + ay * k + by * k],
          [x + bx * k, y + by * k],
        ],
        colour,
        1.2,
      );
    }

    /* A standing figure, facing the way the sight line goes. */
    function person(ctx, x, groundY, height, aimX, aimY, colour) {
      const headR = height * 0.115;
      const headY = groundY - height + headR;
      const shoulderY = headY + headR * 1.9;
      ctx.save();
      ctx.strokeStyle = colour;
      ctx.fillStyle = colour;
      ctx.lineWidth = Math.max(2, height * 0.05);
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.arc(x, headY, headR, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.moveTo(x, headY + headR);
      ctx.lineTo(x, groundY - height * 0.34);
      ctx.moveTo(x, groundY - height * 0.34);
      ctx.lineTo(x - height * 0.15, groundY);
      ctx.moveTo(x, groundY - height * 0.34);
      ctx.lineTo(x + height * 0.17, groundY);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(x, shoulderY);
      ctx.lineTo(x + aimX * height * 0.46, shoulderY + aimY * height * 0.46);
      ctx.stroke();
      ctx.restore();
      return { x, y: headY };
    }

    /* The foreground: one person, one horizon, and the angle they can measure.
     * It is the corner of the section behind it, blown up. */
    function drawScene(readout, box) {
      const lat = readout.latitude_deg;
      const phi = lat * DEG;
      const groundY = box.y + box.h * 0.72;
      const blocked = !readout.visible && lat !== 0;

      dia.save();
      dia.beginPath();
      dia.rect(box.x, box.y, box.w, box.h);
      dia.clip();

      dia.fillStyle = "#eef2fa";
      dia.fillRect(box.x, box.y, box.w, groundY - box.y);
      dia.fillStyle = "#dfe3d6";
      dia.fillRect(box.x, groundY, box.w, box.y + box.h - groundY);
      polyline(dia, [[box.x, groundY], [box.x + box.w, groundY]], INK, 2);

      const height = Math.min(box.h * 0.17, 86);
      const aim = { x: Math.cos(phi), y: -Math.sin(phi) };
      const eye = person(
        dia, box.x + box.w * 0.20, groundY, height, aim.x, aim.y, INK,
      );
      const reach = Math.min(
        box.w * 0.62,
        (eye.y - box.y - 34) / Math.max(0.16, Math.sin(Math.abs(phi))),
      );
      const poleX = eye.x + aim.x * reach;
      const poleY = eye.y + aim.y * reach;

      // Everything in the sky turns about the pole, which is how you find it.
      for (const fraction of [0.24, 0.44, 0.64]) {
        dottedCircle(
          dia, poleX, poleY, reach * fraction, "rgba(29,78,216,0.20)", [2, 5],
        );
      }

      polyline(dia, [[eye.x, eye.y], [eye.x + reach * 1.05, eye.y]], FAINT, 1.4, [6, 4]);
      label(dia, "horizon", eye.x + reach * 0.86, eye.y - 8, FAINT);
      polyline(
        dia,
        [[eye.x, eye.y], [eye.x, Math.max(box.y + 6, eye.y - reach * 0.92)]],
        FAINT, 1.4, [4, 4],
      );
      label(dia, "zenith", eye.x + 8, Math.max(box.y + 18, eye.y - reach * 0.88), FAINT);
      label(dia, "north", box.x + box.w - 10, groundY + 20, INK, "right");

      polyline(
        dia, [[eye.x, eye.y], [poleX, poleY]],
        blocked ? "rgba(29,78,216,0.35)" : CO_COLOUR, 1.8, [3, 4],
      );

      const errorPx = reach * 0.055;
      dottedCircle(dia, poleX, poleY, errorPx, "rgba(194,65,12,0.55)", [3, 3]);
      const sx = poleX + errorPx * Math.cos(-0.6);
      const sy = poleY + errorPx * Math.sin(-0.6);
      polyline(dia, [[eye.x, eye.y], [sx, sy]], LAT_COLOUR, 1.4);
      star(dia, sx, sy, 9, blocked ? "rgba(194,65,12,0.4)" : "#e8a33d");
      label(dia, "Polaris", sx + 13, sy + 4, INK);
      label(dia, "true pole", poleX - 12, poleY - errorPx - 10, CO_COLOUR, "right");

      const toPole = Math.atan2(aim.y, aim.x);
      arc(dia, eye.x, eye.y, reach * 0.30, 0, toPole, LAT_COLOUR, 2.5);
      angleLabel(dia, eye.x, eye.y, 0, toPole, reach * 0.40, "φ′", LAT_COLOUR);
      arc(dia, eye.x, eye.y, reach * 0.46, toPole, -Math.PI / 2, CO_COLOUR, 1.8);
      angleLabel(dia, eye.x, eye.y, toPole, -Math.PI / 2, reach * 0.56, "θ′", CO_COLOUR);

      if (blocked) {
        label(dia, "the ground is in the way", box.x + 12, box.y + box.h - 14, INK);
      }
      dia.restore();

      dia.save();
      dia.strokeStyle = "rgba(60,70,90,0.4)";
      dia.lineWidth = 1.2;
      dia.strokeRect(box.x, box.y, box.w, box.h);
      dia.restore();
      label(dia, "what you can measure", box.x + 10, box.y + 20, INK);
      return eye;
    }

    /* The background: Earth in section, and the angle nobody can reach. */
    function drawSection(readout, cx, cy, R) {
      const lat = readout.latitude_deg;
      const phi = lat * DEG;

      dia.save();
      dia.strokeStyle = INK;
      dia.lineWidth = 2;
      dia.beginPath();
      dia.arc(cx, cy, R, 0, Math.PI * 2);
      dia.stroke();
      dia.restore();

      polyline(dia, [[cx - R * 1.25, cy], [cx + R * 1.3, cy]], FAINT, 1.4, [6, 4]);
      label(dia, "equator", cx - R * 1.25, cy - 8, FAINT);
      polyline(dia, [[cx, cy + R * 1.15], [cx, cy - R * 2.1]], CO_COLOUR, 1.4, [5, 5]);
      label(dia, "axis → pole", cx + 7, cy - R * 1.95, CO_COLOUR);

      const px = cx + R * Math.cos(phi);
      const py = cy - R * Math.sin(phi);
      polyline(dia, [[cx, cy], [px, py]], INK, 2);
      arc(dia, cx, cy, R * 0.26, 0, -phi, LAT_COLOUR, 2.5);
      angleLabel(dia, cx, cy, 0, -phi, R * 0.38, "φ", LAT_COLOUR);
      arc(dia, cx, cy, R * 0.46, -phi, -Math.PI / 2, CO_COLOUR, 1.8);
      angleLabel(dia, cx, cy, -phi, -Math.PI / 2, R * 0.60, "θ", CO_COLOUR);

      const zx = Math.cos(phi);
      const zy = -Math.sin(phi);
      const hx = -Math.sin(phi);
      const hy = -Math.cos(phi);
      const reach = R * 0.85;
      polyline(
        dia,
        [
          [px - hx * reach * 0.6, py - hy * reach * 0.6],
          [px + hx * reach, py + hy * reach],
        ],
        INK, 2,
      );
      polyline(dia, [[px, py], [px + zx * reach * 0.5, py + zy * reach * 0.5]],
               FAINT, 1.4, [4, 4]);
      polyline(dia, [[px, py], [px, py - reach * 0.95]], CO_COLOUR, 1.8, [3, 4]);
      star(dia, px, py - reach * 0.95, 7, "#e8a33d");

      const toPole = -Math.PI / 2;
      arc(dia, px, py, R * 0.30, Math.atan2(hy, hx), toPole, LAT_COLOUR, 2.5);
      angleLabel(dia, px, py, Math.atan2(hy, hx), toPole, R * 0.42, "φ′", LAT_COLOUR);
      arc(dia, px, py, R * 0.44, toPole, Math.atan2(zy, zx), CO_COLOUR, 1.8);
      angleLabel(dia, px, py, toPole, Math.atan2(zy, zx), R * 0.56, "θ′", CO_COLOUR);

      dot(dia, px, py, "#ff5f7e", 5, false);
      square(dia, cx, cy, 1, 0, 0, -1, FAINT);
      square(dia, px, py, hx, hy, zx, zy, FAINT);
      label(dia, "why it is your latitude", cx - R, cy + R * 1.42, INK, "center");
      return { x: px, y: py };
    }

    function drawDiagram(readout) {
      const lat = readout.latitude_deg;

      dia.clearRect(0, 0, diaW, diaH);
      dia.fillStyle = "#fbfaf6";
      dia.fillRect(0, 0, diaW, diaH);

      const box = {
        x: 26,
        y: 22,
        w: Math.min(diaW * 0.50, 560),
        h: diaH * 0.60,
      };
      const R = Math.min(diaW * 0.17, diaH * 0.20);
      const cx = Math.min(diaW - R * 1.4 - 24, box.x + box.w + R * 1.5 + 30);
      const cy = box.y + R * 2.3;

      const P = drawSection(readout, cx, cy, R);
      const eye = drawScene(readout, box);

      // The callout: the scene is that point on the section, magnified.
      polyline(dia, [[P.x, P.y], [box.x + box.w, box.y]], FAINT, 1, [4, 4]);
      polyline(dia, [[P.x, P.y], [box.x + box.w, box.y + box.h]], FAINT, 1, [4, 4]);

      const co = 90 - lat;
      const lines = [
        "φ   at Earth's centre, equator to you        = " + lat.toFixed(1) + "°",
        "θ   at Earth's centre, axis to you           = " + co.toFixed(1) + "°",
        "θ′  at your feet, pole to your zenith        = " + co.toFixed(1) + "°",
        "φ′  at your feet, horizon to the pole        = " + lat.toFixed(1) + "°",
        "",
        "Polaris is 433 light years off, so every line drawn to it is parallel to Earth's axis.",
        "Your radius cuts both of those parallels, which makes θ′ = θ: alternate angles, nothing more.",
        "Your zenith runs along that radius and your horizon is square to it, so φ′ = 90° − θ′ = 90° − θ = φ.",
        "",
        "The dotted circle is the only slack in it. Polaris sits "
          + readout.polaris_separation_deg.toFixed(2)
          + "° from the true pole and circles it once a day,",
        "so its height wanders that much either side of your latitude. It is drawn far larger than that here.",
        "",
        readout.headline,
      ];
      lines.forEach((line, i) =>
        label(
          dia, line, 26, box.y + box.h + 34 + i * 19,
          i === lines.length - 1 ? LAT_COLOUR : INK,
        ),
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
