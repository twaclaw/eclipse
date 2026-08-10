/* Animation 3 - rotation, day and night.
 *
 * Globe  : the tilted Earth spinning on its axis, lit from the sun's direction.
 * Map    : the same instant unrolled, where the day/night boundary shows up as
 *          the familiar sine-like curve.
 * Sky    : optional. What the sun is doing in the sky of one chosen place -
 *          a dome showing where it is, and a timeline showing when it rises
 *          and sets.
 *
 * All three read the same track, so they cannot drift apart.
 */

export default {
  async render({ model, el }) {
    el.classList.add("es-root");
    el.innerHTML = `
      <div class="es-grid">
        <div class="es-panel es-globe">
          <canvas class="es-c3d"></canvas>
          <div class="es-sun-tag">&#9788; Sun</div>
          <div class="es-clock"></div>
          <div class="es-hint">drag to orbit &middot; scroll to zoom</div>
        </div>
        <div class="es-panel es-map">
          <canvas class="es-c2d"></canvas>
          <div class="es-date"></div>
          <div class="es-hint">click to pick a location</div>
        </div>
      </div>
      <div class="es-panel es-skypanel">
        <canvas class="es-csky"></canvas>
      </div>
      <div class="es-status">loading textures&hellip;</div>`;

    const c3d = el.querySelector(".es-c3d");
    const c2d = el.querySelector(".es-c2d");
    const csky = el.querySelector(".es-csky");
    const skyPanel = el.querySelector(".es-skypanel");
    const clockEl = el.querySelector(".es-clock");
    const dateEl = el.querySelector(".es-date");
    const sunTag = el.querySelector(".es-sun-tag");
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

    /* ------------------------------------------------------------- 3d scene */

    const renderer = new THREE.WebGLRenderer({ canvas: c3d, antialias: true });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
    renderer.setClearColor(0x04060e, 1);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(36, 1, 0.05, 200);
    scene.add(buildStars(THREE, 1600, 60));

    const earth = buildBody(THREE, {
      dayImg,
      nightImg,
      tiltDeg: model.get("obliquity_deg"),
      axis: true,
      graticule: true,
      maxAniso: renderer.capabilities.getMaxAnisotropy(),
    });
    scene.add(earth.group);

    // A stub pointing at the sun, so the lit hemisphere has a visible cause.
    const sunRay = makeLine(
      THREE,
      [new THREE.Vector3(1.12, 0, 0), new THREE.Vector3(2.0, 0, 0)],
      0xffd27f,
      0.85,
    );
    scene.add(sunRay);

    const orbit = attachOrbit(c3d, camera, { radius: 3.3, phi: 1.32 });
    const ro3d = autoSize(c3d, (w, h, dpr) => {
      renderer.setPixelRatio(dpr);
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    });

    /* -------------------------------------------------------------- flat map */

    const ctx = c2d.getContext("2d");
    let mapW = 1;
    let mapH = 1;
    const ro2d = autoSize(c2d, (w, h, dpr) => {
      mapW = w;
      mapH = h;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    });

    const xOfLon = (lon) => ((lon + 180) / 360) * mapW;
    const yOfLat = (lat) => ((90 - lat) / 180) * mapH;

    function hLine(lat, style, dash) {
      polyline(ctx, [[0, yOfLat(lat)], [mapW, yOfLat(lat)]], style, 1, dash);
    }

    function drawMap(track, at) {
      const decDeg = at.declination_deg;
      const lonSs = wrapLon(at.subsolar_lon);

      ctx.clearRect(0, 0, mapW, mapH);
      ctx.drawImage(dayImg, 0, 0, mapW, mapH);

      // Sweep straight across the map; the table lookup handles the dateline.
      const curve = new Path2D();
      const steps = 360;
      for (let i = 0; i <= steps; i++) {
        const lon = -180 + (360 * i) / steps;
        const py = yOfLat(tableLookup(track.tables.terminator_lat, lon - lonSs));
        if (i === 0) curve.moveTo(xOfLon(lon), py);
        else curve.lineTo(xOfLon(lon), py);
      }

      // Night is whichever pole the sun is turned away from.
      const region = new Path2D(curve);
      if (decDeg >= 0) {
        region.lineTo(mapW, mapH);
        region.lineTo(0, mapH);
      } else {
        region.lineTo(mapW, 0);
        region.lineTo(0, 0);
      }
      region.closePath();

      ctx.save();
      ctx.clip(region);
      ctx.fillStyle = "rgba(3,7,20,0.74)";
      ctx.fillRect(0, 0, mapW, mapH);
      if (model.get("show_lights")) {
        ctx.globalCompositeOperation = "lighter";
        ctx.globalAlpha = 0.9;
        ctx.drawImage(nightImg, 0, 0, mapW, mapH);
        ctx.globalAlpha = 1;
        ctx.globalCompositeOperation = "source-over";
      }
      ctx.restore();

      if (model.get("show_graticule")) {
        ctx.save();
        ctx.strokeStyle = "rgba(255,255,255,0.13)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let lon = -150; lon <= 150; lon += 30) {
          ctx.moveTo(xOfLon(lon), 0);
          ctx.lineTo(xOfLon(lon), mapH);
        }
        for (let lat = -60; lat <= 60; lat += 30) {
          ctx.moveTo(0, yOfLat(lat));
          ctx.lineTo(mapW, yOfLat(lat));
        }
        ctx.stroke();
        ctx.restore();
      }

      hLine(0, "rgba(255,255,255,0.34)");
      hLine(TROPIC, "rgba(255,214,120,0.42)", [5, 4]);
      hLine(-TROPIC, "rgba(255,214,120,0.42)", [5, 4]);
      hLine(POLAR, "rgba(140,200,255,0.42)", [5, 4]);
      hLine(-POLAR, "rgba(140,200,255,0.42)", [5, 4]);

      ctx.save();
      ctx.strokeStyle = "rgba(255,198,96,0.95)";
      ctx.lineWidth = 2;
      ctx.lineJoin = "round";
      ctx.stroke(curve);
      ctx.restore();

      dot(ctx, xOfLon(lonSs), yOfLat(decDeg), "#ffd66b", 5.5, true);
      dot(ctx, xOfLon(wrapLon(lonSs + 180)), yOfLat(-decDeg), "#7fa8ff", 4, false);

      const m = model.get("marker");
      if (m && m.length === 2) {
        const mx = xOfLon(wrapLon(m[1]));
        polyline(ctx, [[mx, 0], [mx, mapH]], "rgba(255,255,255,0.55)", 1, [3, 3]);
        dot(ctx, mx, yOfLat(m[0]), "#ff5f7e", 5, true);
      }

      for (const [lat, txt] of [
        [POLAR, "66.6°N"],
        [TROPIC, "23.4°N"],
        [0, "0°"],
        [-TROPIC, "23.4°S"],
        [-POLAR, "66.6°S"],
      ]) {
        label(ctx, txt, mapW - 6, yOfLat(lat) - 3, "rgba(255,255,255,0.62)", "right");
      }
    }

    c2d.addEventListener("click", (e) => {
      const rect = c2d.getBoundingClientRect();
      const lon = ((e.clientX - rect.left) / rect.width) * 360 - 180;
      const lat = 90 - ((e.clientY - rect.top) / rect.height) * 180;
      model.set("marker", [
        Math.round(lat * 100) / 100,
        Math.round(lon * 100) / 100,
      ]);
      model.save_changes();
    });

    /* ------------------------------------------------------------ sky panel */

    const sky = csky.getContext("2d");
    let skyW = 1;
    let skyH = 1;
    const roSky = autoSize(csky, (w, h, dpr) => {
      skyW = w;
      skyH = h;
      sky.setTransform(dpr, 0, 0, dpr, 0, 0);
    });

    const SKY_NIGHT = "#070b18";
    const SKY_DAY = "#12203a";

    /* Dome: looking straight up. Zenith at the centre, horizon at the rim,
     * north at the top and east to the right. */
    function drawDome(track, at, box) {
      const cx = box.x + box.w / 2;
      const cy = box.y + box.h / 2;
      const R = Math.min(box.w, box.h) / 2 - 18;
      const project = (azDeg, elDeg) => {
        const r = (R * (90 - elDeg)) / 90;
        return [cx + r * Math.sin(azDeg * DEG), cy - r * Math.cos(azDeg * DEG)];
      };

      sky.save();
      sky.beginPath();
      sky.arc(cx, cy, R, 0, Math.PI * 2);
      sky.fillStyle = at.sun_elevation > 0 ? SKY_DAY : SKY_NIGHT;
      sky.fill();
      sky.clip();

      for (const elev of [0, 30, 60]) {
        const rr = (R * (90 - elev)) / 90;
        sky.beginPath();
        sky.arc(cx, cy, rr, 0, Math.PI * 2);
        sky.strokeStyle = "rgba(255,255,255,0.16)";
        sky.lineWidth = 1;
        sky.stroke();
      }
      for (let az = 0; az < 360; az += 45) {
        const [x, y] = project(az, 0);
        polyline(sky, [[cx, cy], [x, y]], "rgba(255,255,255,0.10)", 1);
      }

      // Solstice arcs bracket the range the sun can ever occupy here.
      for (const [name, style] of [
        ["sky_june", "rgba(255,214,120,0.35)"],
        ["sky_december", "rgba(140,200,255,0.35)"],
      ]) {
        drawArc(track.paths[name], project, style, 1.5, [4, 3]);
      }
      drawArc(track.paths.sky_today, project, "rgba(255,208,110,0.95)", 2.4, null);
      sky.restore();

      sky.beginPath();
      sky.arc(cx, cy, R, 0, Math.PI * 2);
      sky.strokeStyle = "rgba(255,255,255,0.45)";
      sky.lineWidth = 1.5;
      sky.stroke();

      for (const [az, txt] of [[0, "N"], [90, "E"], [180, "S"], [270, "W"]]) {
        const [x, y] = project(az, -7);
        label(sky, txt, x, y, "rgba(255,255,255,0.72)", "center", "middle");
      }

      if (at.sun_elevation > -1) {
        const [x, y] = project(at.sun_azimuth, Math.max(at.sun_elevation, 0));
        dot(sky, x, y, "#ffd45e", 7, true);
      }
      label(sky, "the sky overhead", cx, box.y + box.h - 2,
            "rgba(255,255,255,0.4)", "center");
    }

    function drawArc(path, project, style, width, dash) {
      if (!path) return;
      let run = [];
      for (const [az, elev] of path) {
        if (elev >= 0) run.push(project(az, elev));
        else if (run.length) {
          polyline(sky, run, style, width, dash);
          run = [];
        }
      }
      if (run.length) polyline(sky, run, style, width, dash);
    }

    /* Timeline: elevation against the clock, which is where sunrise and sunset
     * become times rather than directions. */
    function drawTimeline(track, at, box, hours) {
      const x = (h) => box.x + (h / 24) * box.w;
      const y = (elev) => box.y + ((60 - elev) / 120) * box.h;
      const horizon = y(0);

      sky.fillStyle = SKY_NIGHT;
      sky.fillRect(box.x, box.y, box.w, box.h);
      sky.fillStyle = SKY_DAY;
      sky.fillRect(box.x, box.y, box.w, horizon - box.y);

      const path = track.paths.sky_today || [];
      const above = [];
      for (const [, elev, h] of path) above.push([x(h), y(elev)]);

      // Shade the daylight hours behind the curve.
      sky.save();
      sky.beginPath();
      sky.moveTo(box.x, horizon);
      for (const [, elev, h] of path) sky.lineTo(x(h), y(Math.max(elev, 0)));
      sky.lineTo(box.x + box.w, horizon);
      sky.closePath();
      sky.fillStyle = "rgba(255,205,110,0.16)";
      sky.fill();
      sky.restore();

      for (const elev of [-30, 30, 60]) {
        polyline(sky, [[box.x, y(elev)], [box.x + box.w, y(elev)]],
                 "rgba(255,255,255,0.10)", 1);
        label(sky, elev + "°", box.x + 3, y(elev) - 2, "rgba(255,255,255,0.35)");
      }
      polyline(sky, [[box.x, horizon], [box.x + box.w, horizon]],
               "rgba(255,255,255,0.55)", 1.5);
      label(sky, "horizon", box.x + 3, horizon - 3, "rgba(255,255,255,0.6)");

      for (let h = 0; h <= 24; h += 3) {
        polyline(sky, [[x(h), box.y], [x(h), box.y + box.h]],
                 "rgba(255,255,255,0.09)", 1);
        label(sky, String(h).padStart(2, "0"), x(h), box.y + box.h - 4,
              "rgba(255,255,255,0.4)", "center");
      }

      polyline(sky, above, "rgba(255,208,110,0.95)", 2.2);

      for (const [when, txt, colour] of [
        [at.sunrise_hours, "sunrise " + (at.sunrise_hours === null ? "" : fmtHM(at.sunrise_hours)), "#ffd45e"],
        [at.sunset_hours, "sunset " + (at.sunset_hours === null ? "" : fmtHM(at.sunset_hours)), "#ff9d5e"],
      ]) {
        if (when === null || when === undefined) continue;
        polyline(sky, [[x(when), box.y], [x(when), box.y + box.h]], colour, 1, [4, 3]);
        label(sky, txt, x(when) + 4, box.y + 12, colour);
      }

      dot(sky, x(hours), y(at.sun_elevation), "#ffd45e", 6, true);
    }

    function drawSky(track, at, hours) {
      sky.clearRect(0, 0, skyW, skyH);
      if (!at.has_marker) {
        label(sky, "click the map to pick a location", skyW / 2, skyH / 2,
              "rgba(255,255,255,0.5)", "center", "middle");
        return;
      }
      const pad = 10;
      const domeSize = Math.min(skyH - 2 * pad, skyW * 0.42);
      drawDome(track, at, { x: pad, y: pad, w: domeSize, h: skyH - 2 * pad });
      drawTimeline(track, at, {
        x: pad * 2 + domeSize,
        y: pad,
        w: skyW - domeSize - 3 * pad,
        h: skyH - 2 * pad,
      }, hours);
    }

    /* ------------------------------------------------------------------ loop */

    let hours = model.get("utc_hour");
    let last = performance.now();
    let raf = 0;
    const gate = visibilityGate(el);
    const sunVec = new THREE.Vector3();
    const proj = new THREE.Vector3();
    const xAxis = new THREE.Vector3(1, 0, 0);

    model.on("change:utc_hour", () => {
      hours = model.get("utc_hour");
    });

    function frame(now) {
      raf = requestAnimationFrame(frame);
      const dt = Math.min(0.08, (now - last) / 1000);
      last = now;
      if (!gate.visible || document.hidden) return;

      const track = model.get("track");
      if (!track || !track.t) return;

      if (model.get("playing")) {
        hours = (hours + dt * model.get("speed")) % 24;
        if (hours < 0) hours += 24;
      }
      const at = trackSample(track, hours);

      sunVec.set(at.sun[0], at.sun[1], at.sun[2]);
      earth.uniforms.uSunDir.value.copy(sunVec);
      earth.uniforms.uTwilight.value = model.get("twilight_cos");
      earth.uniforms.uNightGain.value = model.get("show_lights") ? 1.0 : 0.0;
      earth.mesh.rotation.y = at.spin;
      earth.grid.visible = model.get("show_graticule");
      sunRay.quaternion.setFromUnitVectors(xAxis, sunVec);

      renderer.render(scene, camera);

      // Park the sun caption where the ray leaves the globe.
      proj.copy(sunVec).multiplyScalar(2.15).project(camera);
      if (proj.z < 1) {
        sunTag.style.display = "block";
        sunTag.style.left = ((proj.x * 0.5 + 0.5) * 100).toFixed(2) + "%";
        sunTag.style.top = ((-proj.y * 0.5 + 0.5) * 100).toFixed(2) + "%";
      } else {
        sunTag.style.display = "none";
      }

      drawMap(track, at);
      const wantSky = model.get("show_sky");
      skyPanel.style.display = wantSky ? "block" : "none";
      if (wantSky) drawSky(track, at, hours);

      clockEl.textContent = fmtHM(hours) + " solar";
      dateEl.textContent = track.scalars.date_label;
    }
    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      orbit.dispose();
      gate.dispose();
      ro3d.disconnect();
      ro2d.disconnect();
      roSky.disconnect();
      renderer.dispose();
    };
  },
};
