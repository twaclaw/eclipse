/* earthkit - the drawing half of the Earth/Moon/Sun animations.
 *
 * There is deliberately no astronomy in this file. Python samples the motion
 * and ships a track (see earthsim/track.py); everything here either reads that
 * track or pushes pixels. If you find yourself reaching for a calendar, an
 * obliquity or Kepler's equation, it belongs on the Python side.
 */

const DEG = Math.PI / 180;
const TROPIC = 23.4392811;
const POLAR = 90 - TROPIC;

const TEX_BASE =
  "https://cdn.jsdelivr.net/gh/mrdoob/three.js@r160/examples/textures/planets/";
const TEX = {
  day: TEX_BASE + "earth_atmos_4096.jpg",
  night: TEX_BASE + "earth_lights_2048.png",
  moon: TEX_BASE + "moon_1024.jpg",
};

let _threePromise = null;
function getThree() {
  if (!_threePromise) _threePromise = import("https://esm.sh/three@0.160.0");
  return _threePromise;
}

const _imgCache = new Map();
function loadImage(url) {
  if (!_imgCache.has(url)) {
    _imgCache.set(
      url,
      new Promise((resolve, reject) => {
        const im = new Image();
        im.crossOrigin = "anonymous";
        im.onload = () => resolve(im);
        im.onerror = () => reject(new Error("could not load " + url));
        im.src = url;
      }),
    );
  }
  return _imgCache.get(url);
}

/* ------------------------------------------------------- reading the track */

/* Locate t in an ascending sample grid and return the index below it plus the
 * fraction across. Starts from a uniform-spacing guess and walks, so it copes
 * with grids that are not perfectly even. */
function locate(t, times) {
  const n = times.length;
  if (t <= times[0]) return { i: 0, f: 0 };
  if (t >= times[n - 1]) return { i: n - 2, f: 1 };
  const span = times[1] - times[0];
  let i = Math.min(n - 2, Math.max(0, Math.floor((t - times[0]) / span)));
  while (i + 1 < n - 1 && times[i + 1] < t) i++;
  while (i > 0 && times[i] > t) i--;
  return { i, f: (t - times[i]) / (times[i + 1] - times[i]) };
}

/* Channels arrive unwrapped from Python precisely so this can stay a lerp. */
function sampleChannel(t, times, values) {
  if (!values || values.length === 0) return 0;
  if (values.length === 1) return values[0];
  const { i, f } = locate(t, times);
  return values[i] + (values[i + 1] - values[i]) * f;
}

function sampleVector(t, times, values) {
  if (!values || values.length === 0) return [0, 0, 0];
  if (values.length === 1) return values[0];
  const { i, f } = locate(t, times);
  const a = values[i];
  const b = values[i + 1];
  return [
    a[0] + (b[0] - a[0]) * f,
    a[1] + (b[1] - a[1]) * f,
    a[2] + (b[2] - a[2]) * f,
  ];
}

/* Labels switch at a time rather than blending between two strings. */
function stepAt(steps, t) {
  let label = steps.length ? steps[0][1] : "";
  for (const [when, name] of steps) {
    if (t >= when) label = name;
    else break;
  }
  return label;
}

/* Everything the track knows at time t, in one object. */
function trackSample(track, t) {
  const out = Object.assign({}, track.scalars);
  for (const key in track.channels) {
    out[key] = sampleChannel(t, track.t, track.channels[key]);
  }
  for (const key in track.vectors) {
    out[key] = sampleVector(t, track.t, track.vectors[key]);
  }
  for (const key in track.steps) {
    out[key] = stepAt(track.steps[key], t);
  }
  return out;
}

/* Regularly spaced lookup. `wrap` lets a caller sweep straight past the end of
 * the table - the terminator is read this way so the map can be drawn from
 * -180 to 180 without worrying about the dateline. */
function tableLookup(tbl, x) {
  const values = tbl.values;
  const last = values.length - 1;
  let pos = (x - tbl.start) / tbl.step;
  if (tbl.wrap) {
    const span = tbl.wrap / tbl.step;
    pos = ((pos % span) + span) % span;
  }
  pos = Math.max(0, Math.min(last, pos));
  const i = Math.min(last - 1, Math.floor(pos));
  const f = pos - i;
  return values[i] + (values[i + 1] - values[i]) * f;
}

/* One whole row of a 2-D field, interpolated between the two rows either side.
 *
 * The seasons panel reads the sun's daily arc this way: the row index is the
 * declination, so the curve slides smoothly as the date advances instead of
 * stepping between samples.
 */
function gridRowAt(g, row) {
  const span = Math.max(1e-9, g.row_step);
  const pos = Math.max(0, Math.min(g.rows - 1, (row - g.row_start) / span));
  const i = Math.max(0, Math.min(g.rows - 2, Math.floor(pos)));
  const f = g.rows < 2 ? 0 : pos - i;
  const out = new Float64Array(g.cols);
  const a = i * g.cols;
  const b = Math.min(g.rows - 1, i + 1) * g.cols;
  for (let c = 0; c < g.cols; c++) {
    out[c] = g.values[a + c] + (g.values[b + c] - g.values[a + c]) * f;
  }
  return out;
}

/* One cell of a 2-D field, interpolated in both directions. */
function gridValueAt(g, row, col) {
  const values = gridRowAt(g, row);
  const span = Math.max(1e-9, g.col_step);
  const pos = Math.max(0, Math.min(g.cols - 1, (col - g.col_start) / span));
  const i = Math.max(0, Math.min(g.cols - 2, Math.floor(pos)));
  const f = g.cols < 2 ? 0 : pos - i;
  return values[i] + (values[i + 1] - values[i]) * f;
}

/* The value a column of a grid stands for. */
function gridColValue(g, col) {
  return g.col_start + col * g.col_step;
}

function wrapLon(lon) {
  return ((((lon + 180) % 360) + 360) % 360) - 180;
}

/* Rounds to the nearest minute rather than truncating: wrapping h into [0, 24)
 * loses a few ulps, and flooring that turned 3.7 into 03:41. Matches
 * earthsim.labels.hm exactly. */
function fmtHM(h) {
  const total = ((Math.round((h % 24) * 60) % 1440) + 1440) % 1440;
  return (
    String(Math.floor(total / 60)).padStart(2, "0") +
    ":" +
    String(total % 60).padStart(2, "0")
  );
}

/* -------------------------------------------------------------- 3d bodies */

const BODY_VERT = `
varying vec2 vUv;
varying vec3 vNormalW;
varying vec3 vViewW;
varying vec3 vPosW;
void main() {
  vUv = uv;
  vNormalW = normalize(mat3(modelMatrix) * normal);
  vec4 wp = modelMatrix * vec4(position, 1.0);
  vPosW = wp.xyz;
  vViewW = normalize(cameraPosition - wp.xyz);
  gl_Position = projectionMatrix * viewMatrix * wp;
}`;

/* Decides, per surface point, whether the sun is up, and blends the daylight
 * map into whatever stands in for its night side. Earth gets city lights and
 * an atmosphere; the Moon gets a hard terminator and a little earthshine. */
const BODY_FRAG = `
uniform sampler2D uDay;
uniform sampler2D uNight;
uniform vec3  uSunDir;
uniform float uNightGain;
uniform float uAmbient;
uniform float uTwilight;
uniform float uAtmo;
uniform float uExposure;
uniform float uLimb;
uniform vec2  uShadowCentre;
uniform float uUmbraR;
uniform float uPenumbraR;
varying vec2 vUv;
varying vec3 vNormalW;
varying vec3 vViewW;
varying vec3 vPosW;
void main() {
  vec3  n   = normalize(vNormalW);
  float c   = dot(n, normalize(uSunDir));
  float lam = clamp(c, 0.0, 1.0);

  vec3 day   = texture2D(uDay, vUv).rgb;
  vec3 night = texture2D(uNight, vUv).rgb;

  vec3 lit  = day * (0.04 + 1.06 * pow(lam, uLimb)) * uExposure;
  vec3 dark = night * uNightGain + day * uAmbient;

  float t = smoothstep(-uTwilight, uTwilight, c);
  vec3 col = mix(dark, lit, t);

  // warm scattering in the twilight band, only where there is air to scatter
  float band = exp(-pow(c / max(uTwilight, 1e-3), 2.0) * 1.2);
  col += vec3(0.32, 0.14, 0.05) * band * 0.45 * uAtmo;

  // blue atmospheric limb, brightest on the sunlit side
  float rim = pow(1.0 - max(dot(n, normalize(vViewW)), 0.0), 3.0);
  col += vec3(0.25, 0.45, 0.95) * rim * uAtmo * (0.12 + 0.88 * t);

  // Another body's shadow falling across this one. Radii arrive in units of
  // this body's own radius, measured in the view plane, so the projected edge
  // is simply a circle. Off unless a caller sets a positive umbra.
  if (uUmbraR > 0.0) {
    float d = length(vPosW.xy - uShadowCentre);
    float shade = smoothstep(uUmbraR, uPenumbraR, d);
    float inUmbra = 1.0 - smoothstep(uUmbraR - 0.05, uUmbraR + 0.05, d);
    vec3 dimmed = col * mix(0.18, 1.0, shade);
    // Sunlight bent through the eclipsing planet's air, which is what stops
    // a totally eclipsed moon going black.
    vec3 copper = col * vec3(0.95, 0.32, 0.13) * 0.30;
    col = mix(dimmed, copper, inUmbra);
  }

  gl_FragColor = vec4(col, 1.0);
}`;

/* Surface point in a body's own frame. Longitude 0 lands on local +x, which is
 * where u = 0.5 of an equirectangular texture sits. */
function latLonToVec3(latDeg, lonDeg, r) {
  const la = latDeg * DEG;
  const lo = lonDeg * DEG;
  return [
    r * Math.cos(la) * Math.cos(lo),
    r * Math.sin(la),
    -r * Math.cos(la) * Math.sin(lo),
  ];
}

function makeTexture(THREE, img, maxAniso) {
  const t = new THREE.Texture(img);
  t.colorSpace = THREE.NoColorSpace;
  t.anisotropy = maxAniso || 1;
  t.needsUpdate = true;
  return t;
}

function blackTexture(THREE) {
  const c = document.createElement("canvas");
  c.width = 1;
  c.height = 1;
  const t = new THREE.Texture(c);
  t.needsUpdate = true;
  return t;
}

/* A textured sphere with a day/night shader.
 *
 * The tilt lives on the returned `group` and the daily rotation on `mesh`,
 * matching the two rotations Python's spin_angle() is derived against. Any
 * animation that needs Earth uses this, so there is one globe, not three.
 */
function buildBody(THREE, opts) {
  const uniforms = {
    uDay: { value: makeTexture(THREE, opts.dayImg, opts.maxAniso) },
    uNight: {
      value: opts.nightImg
        ? makeTexture(THREE, opts.nightImg, opts.maxAniso)
        : blackTexture(THREE),
    },
    uSunDir: { value: new THREE.Vector3(1, 0, 0) },
    uNightGain: { value: opts.nightGain === undefined ? 1 : opts.nightGain },
    uAmbient: { value: opts.ambient === undefined ? 0.015 : opts.ambient },
    uTwilight: { value: opts.twilight === undefined ? 0.1 : opts.twilight },
    uAtmo: { value: opts.atmosphere === undefined ? 1 : opts.atmosphere },
    uExposure: { value: opts.exposure === undefined ? 1 : opts.exposure },
    // A full moon looks flat, not like a shaded ball: the regolith throws
    // light straight back at the sun. A low exponent reproduces that.
    uLimb: { value: opts.limbDarkening === undefined ? 0.85 : opts.limbDarkening },
    uShadowCentre: { value: new THREE.Vector2(0, 0) },
    uUmbraR: { value: -1 },
    uPenumbraR: { value: -1 },
  };

  const radius = opts.radius || 1;
  const mesh = new THREE.Mesh(
    new THREE.SphereGeometry(radius, opts.segments || 128, (opts.segments || 128) / 2),
    new THREE.ShaderMaterial({
      uniforms,
      vertexShader: BODY_VERT,
      fragmentShader: BODY_FRAG,
    }),
  );

  const group = new THREE.Group();
  group.rotation.z = -(opts.tiltDeg || 0) * DEG;
  group.add(mesh);

  let axisLine = null;
  if (opts.axis) {
    axisLine = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, -radius * 1.42, 0),
        new THREE.Vector3(0, radius * 1.42, 0),
      ]),
      new THREE.LineBasicMaterial({
        color: 0x8fc0ff,
        transparent: true,
        opacity: 0.7,
      }),
    );
    group.add(axisLine);
  }

  let grid = null;
  if (opts.graticule) {
    grid = buildGraticule(THREE, 30, radius);
    mesh.add(grid);
  }

  return { group, mesh, uniforms, axisLine, grid };
}

function buildGraticule(THREE, step, radius) {
  const pts = [];
  const r = radius * 1.002;
  const push = (a, b) => pts.push(...a, ...b);
  for (let lat = -90 + step; lat <= 90 - step; lat += step) {
    for (let lon = -180; lon < 180; lon += 3) {
      push(latLonToVec3(lat, lon, r), latLonToVec3(lat, lon + 3, r));
    }
  }
  for (let lon = -180; lon < 180; lon += step) {
    for (let lat = -90; lat < 90; lat += 3) {
      push(latLonToVec3(lat, lon, r), latLonToVec3(lat + 3, lon, r));
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
  return new THREE.LineSegments(
    geo,
    new THREE.LineBasicMaterial({
      color: 0x9fd0ff,
      transparent: true,
      opacity: 0.22,
    }),
  );
}

function buildStars(THREE, count, radius) {
  const pos = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    const u = Math.random() * 2 - 1;
    const th = Math.random() * Math.PI * 2;
    const s = Math.sqrt(1 - u * u);
    pos[i * 3] = radius * s * Math.cos(th);
    pos[i * 3 + 1] = radius * u;
    pos[i * 3 + 2] = radius * s * Math.sin(th);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  return new THREE.Points(
    geo,
    new THREE.PointsMaterial({
      color: 0xffffff,
      size: radius * 0.0037,
      sizeAttenuation: true,
      transparent: true,
      opacity: 0.75,
    }),
  );
}

function makeLine(THREE, points, color, opacity) {
  return new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(points),
    new THREE.LineBasicMaterial({
      color,
      transparent: true,
      opacity: opacity === undefined ? 1 : opacity,
    }),
  );
}

/* ----------------------------------------------------------------- controls */

/* Controls rendered inside the widget rather than in the notebook, so they
 * travel with it and stay reachable when a panel is maximised.
 *
 * A widget owns whatever it exposes this way. If a notebook cell also pushed
 * the value down, every change made here would re-run that cell and be
 * overwritten by whatever its slider said.
 */
function controlBar(...parts) {
  return `<div class="es-controls">${parts.join("")}</div>`;
}

function playHTML() {
  return `<button class="es-play" type="button" title="play or pause"></button>`;
}

function sliderHTML(name, label) {
  return `<span class="es-ctl">
    <span class="es-ctl-name">${label}</span>
    <input class="es-ctl-${name}" type="range" />
    <span class="es-ctl-out-${name}"></span>
  </span>`;
}

function attachPlay(el, model) {
  const button = el.querySelector(".es-play");
  const state = { playing: model.get("playing") };
  const paint = () => {
    button.textContent = state.playing ? "\u2759\u2759" : "\u25B6";
  };
  const onClick = () => {
    state.playing = !state.playing;
    paint();
    model.set("playing", state.playing);
    model.save_changes();
  };
  button.addEventListener("click", onClick);
  model.on("change:playing", () => {
    state.playing = model.get("playing");
    paint();
  });
  paint();
  return {
    get playing() {
      return state.playing;
    },
    dispose() {
      button.removeEventListener("click", onClick);
    },
  };
}

/* Binds one range input to one trait. Dragging updates the animation at once
 * but only tells Python on release, so a sweep is a single round trip. */
function attachSlider(el, model, spec) {
  const range = el.querySelector(".es-ctl-" + spec.name);
  const out = el.querySelector(".es-ctl-out-" + spec.name);
  range.min = spec.min;
  range.max = spec.max;
  range.step = spec.step;

  const state = { value: model.get(spec.trait) };
  const paint = () => {
    range.value = state.value;
    out.textContent =
      Number(state.value).toFixed(spec.decimals || 0) +
      (spec.unit ? " " + spec.unit : "");
  };
  const onInput = () => {
    state.value = Number(range.value);
    paint();
  };
  const commit = () => {
    model.set(spec.trait, state.value);
    model.save_changes();
  };

  range.addEventListener("input", onInput);
  range.addEventListener("change", commit);
  model.on("change:" + spec.trait, () => {
    state.value = model.get(spec.trait);
    paint();
  });
  paint();
  return {
    get value() {
      return state.value;
    },
    /* For controls that can also be driven another way, such as a wheel. */
    set(value) {
      state.value = Math.max(spec.min, Math.min(spec.max, value));
      paint();
    },
    commit,
    dispose() {
      range.removeEventListener("input", onInput);
      range.removeEventListener("change", commit);
    },
  };
}

/* A time slider that runs with the animation and can be dragged against it.
 *
 * Different from attachSlider in one way that matters: the render loop pushes
 * the clock in through follow(), so the handle tracks playback, but that push
 * is ignored while the user has hold of it. Otherwise every frame would yank
 * the handle back out from under the pointer.
 */
function attachScrubber(el, model, spec) {
  const range = el.querySelector(".es-ctl-" + spec.name);
  const out = el.querySelector(".es-ctl-out-" + spec.name);
  range.min = spec.min;
  range.max = spec.max;
  range.step = spec.step;

  const show = spec.format
    ? spec.format
    : (v) => Number(v).toFixed(spec.decimals || 0) + (spec.unit ? " " + spec.unit : "");
  const state = { value: model.get(spec.trait), scrubbing: false };
  const paint = () => {
    range.value = state.value;
    out.textContent = show(state.value);
  };

  const onDown = () => {
    state.scrubbing = true;
  };
  const onInput = () => {
    state.scrubbing = true;
    state.value = Number(range.value);
    paint();
  };
  const onRelease = () => {
    if (!state.scrubbing) return;
    state.scrubbing = false;
    // Tell Python where we stopped, so its readouts follow. Once only, on
    // release, rather than throughout the drag.
    model.set(spec.trait, state.value);
    model.save_changes();
  };

  range.addEventListener("pointerdown", onDown);
  range.addEventListener("input", onInput);
  range.addEventListener("change", onRelease);
  // A drag that ends off the slider still counts as letting go.
  window.addEventListener("pointerup", onRelease);

  model.on("change:" + spec.trait, () => {
    if (state.scrubbing) return;
    state.value = model.get(spec.trait);
    paint();
  });
  paint();

  return {
    get value() {
      return state.value;
    },
    get scrubbing() {
      return state.scrubbing;
    },
    follow(value) {
      if (state.scrubbing) return;
      state.value = value;
      paint();
    },
    dispose() {
      range.removeEventListener("pointerdown", onDown);
      range.removeEventListener("input", onInput);
      range.removeEventListener("change", onRelease);
      window.removeEventListener("pointerup", onRelease);
    },
  };
}

/* ------------------------------------------------------- pointer navigation */

/* Hand-rolled rather than pulled from three's addons, so there is only one
 * copy of three on the page and no version pinning to keep in step. */
function attachOrbit(dom, camera, opts) {
  const st = {
    radius: opts.radius,
    phi: opts.phi,
    theta: opts.theta || 0,
    target: opts.target || [0, 0, 0],
  };
  const minR = opts.minR || 1.6;
  const maxR = opts.maxR || 14;
  const minPhi = 0.08;
  const maxPhi = Math.PI - 0.08;

  const apply = () => {
    camera.position.set(
      st.target[0] + st.radius * Math.sin(st.phi) * Math.sin(st.theta),
      st.target[1] + st.radius * Math.cos(st.phi),
      st.target[2] + st.radius * Math.sin(st.phi) * Math.cos(st.theta),
    );
    camera.lookAt(st.target[0], st.target[1], st.target[2]);
  };

  let drag = null;
  const onDown = (e) => {
    drag = { x: e.clientX, y: e.clientY };
    dom.setPointerCapture(e.pointerId);
  };
  const onMove = (e) => {
    if (!drag) return;
    st.theta -= (e.clientX - drag.x) * 0.0065;
    st.phi = Math.min(
      maxPhi,
      Math.max(minPhi, st.phi - (e.clientY - drag.y) * 0.0065),
    );
    drag = { x: e.clientX, y: e.clientY };
    apply();
  };
  const onUp = (e) => {
    drag = null;
    try {
      dom.releasePointerCapture(e.pointerId);
    } catch (_) {}
  };
  const onWheel = (e) => {
    e.preventDefault();
    st.radius = Math.min(
      maxR,
      Math.max(minR, st.radius * Math.exp(e.deltaY * 0.0012)),
    );
    apply();
  };

  dom.addEventListener("pointerdown", onDown);
  dom.addEventListener("pointermove", onMove);
  dom.addEventListener("pointerup", onUp);
  dom.addEventListener("pointercancel", onUp);
  dom.addEventListener("wheel", onWheel, { passive: false });
  apply();

  return {
    state: st,
    apply,
    dispose() {
      dom.removeEventListener("pointerdown", onDown);
      dom.removeEventListener("pointermove", onMove);
      dom.removeEventListener("pointerup", onUp);
      dom.removeEventListener("pointercancel", onUp);
      dom.removeEventListener("wheel", onWheel);
    },
  };
}

/* Turntable for an orthographic view.
 *
 * Orthographic cameras do not zoom by moving, so the wheel resizes the frustum
 * instead and the distance is fixed. Drag turns the scene; the projection stays
 * parallel, so a view built to scale is still to scale from any angle.
 */
function attachOrthoView(dom, camera, opts) {
  const st = {
    yaw: (opts && opts.yaw) || 0,
    pitch: (opts && opts.pitch) || 0,
    zoom: (opts && opts.zoom) || 1,
    span: (opts && opts.span) || 10,
    aspect: 3,
    target: [0, 0, 0],
  };
  const minZoom = (opts && opts.minZoom) || 1;
  const maxZoom = (opts && opts.maxZoom) || 20;
  const onZoom = (opts && opts.onZoom) || (() => {});

  function apply() {
    const halfW = st.span / (2 * st.zoom);
    const halfH = halfW / Math.max(0.2, st.aspect);
    camera.left = -halfW;
    camera.right = halfW;
    camera.top = halfH;
    camera.bottom = -halfH;
    camera.updateProjectionMatrix();
    const away = Math.max(400, st.span * 4);
    camera.position.set(
      st.target[0] + away * Math.cos(st.pitch) * Math.sin(st.yaw),
      st.target[1] + away * Math.sin(st.pitch),
      st.target[2] + away * Math.cos(st.pitch) * Math.cos(st.yaw),
    );
    camera.lookAt(st.target[0], st.target[1], st.target[2]);
  }

  let drag = null;
  const onDown = (e) => {
    drag = { x: e.clientX, y: e.clientY };
    dom.setPointerCapture(e.pointerId);
  };
  const onMove = (e) => {
    if (!drag) return;
    st.yaw += (e.clientX - drag.x) * 0.006;
    st.pitch = Math.max(-1.2, Math.min(1.2, st.pitch + (e.clientY - drag.y) * 0.006));
    drag = { x: e.clientX, y: e.clientY };
    apply();
  };
  const onUp = (e) => {
    drag = null;
    try {
      dom.releasePointerCapture(e.pointerId);
    } catch (_) {}
  };
  const onWheel = (e) => {
    e.preventDefault();
    st.zoom = Math.max(
      minZoom,
      Math.min(maxZoom, st.zoom * Math.exp(-e.deltaY * 0.0015)),
    );
    apply();
    onZoom(st.zoom);
  };

  dom.addEventListener("pointerdown", onDown);
  dom.addEventListener("pointermove", onMove);
  dom.addEventListener("pointerup", onUp);
  dom.addEventListener("pointercancel", onUp);
  dom.addEventListener("wheel", onWheel, { passive: false });
  apply();

  return {
    state: st,
    apply,
    dispose() {
      dom.removeEventListener("pointerdown", onDown);
      dom.removeEventListener("pointermove", onMove);
      dom.removeEventListener("pointerup", onUp);
      dom.removeEventListener("pointercancel", onUp);
      dom.removeEventListener("wheel", onWheel);
    },
  };
}

/* Keeps a canvas matched to its box, at device resolution. */
function autoSize(canvas, onResize) {
  const box = canvas.parentElement;
  const fit = () => {
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const w = Math.max(1, box.clientWidth);
    const h = Math.max(1, box.clientHeight);
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";
    onResize(w, h, dpr);
  };
  const ro = new ResizeObserver(fit);
  ro.observe(box);
  fit();
  return ro;
}

/* Renders only while the widget is actually on screen. */
function visibilityGate(el) {
  const gate = { visible: true };
  const io = new IntersectionObserver(
    (entries) => {
      gate.visible = entries[0].isIntersecting;
    },
    { threshold: 0 },
  );
  io.observe(el);
  gate.dispose = () => io.disconnect();
  return gate;
}

/* ------------------------------------------------------- 2d canvas helpers */

const MONO = "11px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";

function dot(ctx, x, y, color, r, halo) {
  ctx.save();
  if (halo) {
    ctx.fillStyle = color;
    ctx.globalAlpha = 0.22;
    ctx.beginPath();
    ctx.arc(x, y, r * 2.6, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
  }
  ctx.fillStyle = color;
  ctx.strokeStyle = "rgba(0,0,0,0.55)";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.arc(x, y, r, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.restore();
}

function polyline(ctx, points, style, width, dash) {
  if (points.length < 2) return;
  ctx.save();
  ctx.setLineDash(dash || []);
  ctx.strokeStyle = style;
  ctx.lineWidth = width;
  ctx.lineJoin = "round";
  ctx.beginPath();
  points.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
  ctx.stroke();
  ctx.restore();
}

/* Projects an equirectangular texture onto a disc, the way a globe looks from
 * far away. Returns a canvas with transparent corners, ready to blit.
 *
 * Used where a photographic Earth is wanted in a 2-D panel: drawing the flat
 * texture into a circle would look like a sticker, not a planet.
 */
function globeDisc(img, size, centreLonDeg, sunlit) {
  const source = document.createElement("canvas");
  source.width = img.width;
  source.height = img.height;
  const sctx = source.getContext("2d");
  sctx.drawImage(img, 0, 0);
  let texels;
  try {
    texels = sctx.getImageData(0, 0, img.width, img.height).data;
  } catch (_) {
    // Reading pixels back needs the image to have arrived with CORS headers.
    // If it ever does not, fall back to a plain shaded ball rather than
    // taking the whole panel down.
    return shadedDisc(size, "#4f7fb8");
  }

  const out = document.createElement("canvas");
  out.width = size;
  out.height = size;
  const octx = out.getContext("2d");
  const pixels = octx.createImageData(size, size);
  const radius = size / 2;

  for (let py = 0; py < size; py++) {
    const v = (py - radius + 0.5) / radius;
    for (let px = 0; px < size; px++) {
      const u = (px - radius + 0.5) / radius;
      const rho = u * u + v * v;
      const at = (py * size + px) * 4;
      if (rho > 1) {
        pixels.data[at + 3] = 0;
        continue;
      }
      const z = Math.sqrt(1 - rho);
      const lat = Math.asin(Math.max(-1, Math.min(1, -v))) / DEG;
      const lon = centreLonDeg + Math.atan2(u, z) / DEG;
      const sx = Math.min(
        img.width - 1,
        Math.max(0, Math.floor((((lon + 180) % 360 + 360) % 360) / 360 * img.width)),
      );
      const sy = Math.min(
        img.height - 1,
        Math.max(0, Math.floor(((90 - lat) / 180) * img.height)),
      );
      const from = (sy * img.width + sx) * 4;
      // A little limb darkening, so the edge falls away like a sphere.
      const shade = sunlit === false ? 1 : 0.55 + 0.45 * z;
      pixels.data[at] = texels[from] * shade;
      pixels.data[at + 1] = texels[from + 1] * shade;
      pixels.data[at + 2] = texels[from + 2] * shade;
      pixels.data[at + 3] = 255;
    }
  }
  octx.putImageData(pixels, 0, 0);
  return out;
}

/* A plain lit sphere, for when the real texture cannot be read back. */
function shadedDisc(size, colour) {
  const out = document.createElement("canvas");
  out.width = size;
  out.height = size;
  const ctx = out.getContext("2d");
  const g = ctx.createRadialGradient(
    size * 0.36, size * 0.32, size * 0.05,
    size * 0.5, size * 0.5, size * 0.5,
  );
  g.addColorStop(0, colour);
  g.addColorStop(1, "#0a1424");
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2);
  ctx.fill();
  return out;
}

/* Equirectangular projection, shared by every flat map here. */
function mapProjection(w, h) {
  return {
    x: (lon) => ((lon + 180) / 360) * w,
    y: (lat) => ((90 - lat) / 180) * h,
    lon: (px) => (px / w) * 360 - 180,
    lat: (py) => 90 - (py / h) * 180,
  };
}

/* Graticule plus the four latitudes the tilt marks out. Both flat maps draw
 * this, so it lives here rather than in either of them. */
function drawMapFrame(ctx, proj, w, h, opts) {
  if (opts && opts.graticule) {
    ctx.save();
    ctx.strokeStyle = "rgba(255,255,255,0.13)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let lon = -150; lon <= 150; lon += 30) {
      ctx.moveTo(proj.x(lon), 0);
      ctx.lineTo(proj.x(lon), h);
    }
    for (let lat = -60; lat <= 60; lat += 30) {
      ctx.moveTo(0, proj.y(lat));
      ctx.lineTo(w, proj.y(lat));
    }
    ctx.stroke();
    ctx.restore();
  }

  const line = (lat, style, dash) =>
    polyline(ctx, [[0, proj.y(lat)], [w, proj.y(lat)]], style, 1, dash);
  line(0, "rgba(255,255,255,0.34)");
  line(TROPIC, "rgba(255,214,120,0.42)", [5, 4]);
  line(-TROPIC, "rgba(255,214,120,0.42)", [5, 4]);
  line(POLAR, "rgba(140,200,255,0.42)", [5, 4]);
  line(-POLAR, "rgba(140,200,255,0.42)", [5, 4]);

  for (const [lat, txt] of [
    [POLAR, "66.6°N"],
    [TROPIC, "23.4°N"],
    [0, "0°"],
    [-TROPIC, "23.4°S"],
    [-POLAR, "66.6°S"],
  ]) {
    label(ctx, txt, w - 6, proj.y(lat) - 3, "rgba(255,255,255,0.62)", "right");
  }
}

/* Where a click landed, in degrees. */
function pickLatLon(canvas, event) {
  const rect = canvas.getBoundingClientRect();
  return [
    Math.round((90 - ((event.clientY - rect.top) / rect.height) * 180) * 100) / 100,
    Math.round((((event.clientX - rect.left) / rect.width) * 360 - 180) * 100) / 100,
  ];
}

function label(ctx, text, x, y, color, align, baseline) {
  ctx.save();
  ctx.font = MONO;
  ctx.fillStyle = color;
  ctx.textAlign = align || "left";
  ctx.textBaseline = baseline || "alphabetic";
  ctx.fillText(text, x, y);
  ctx.restore();
}
