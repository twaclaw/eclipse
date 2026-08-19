/* Runs each animation's render() under node against stub globals.
 *
 *     node smoke_driver.mjs <static dir> <spec.json>
 *
 * This does not check what anything looks like. It checks that the code runs:
 * that setup completes, that a frame can be drawn with a real track, and that
 * no line throws. A temporal dead zone or a misspelled property fails here
 * rather than silently blanking a panel in the browser.
 */

import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const STATIC = process.argv[2];
const spec = JSON.parse(readFileSync(process.argv[3], "utf8"));
const STUB = pathToFileURL(
  join(dirname(fileURLToPath(import.meta.url)), "three_stub.mjs"),
).href;

/* ------------------------------------------------------------ fake browser */

function context2d() {
  const target = {
    createImageData: (w, h) => ({
      width: w,
      height: h,
      data: new Uint8ClampedArray(Math.max(0, w * h * 4)),
    }),
    measureText: () => ({ width: 10 }),
    getImageData: (x, y, w, h) => ({
      width: w,
      height: h,
      data: new Uint8ClampedArray(Math.max(0, w * h * 4)),
    }),
    createLinearGradient: () => ({ addColorStop() {} }),
    createRadialGradient: () => ({ addColorStop() {} }),
    createPattern: () => null,
  };
  return new Proxy(target, {
    get: (t, k) => (k in t ? t[k] : () => undefined),
    set: (t, k, v) => {
      t[k] = v;
      return true;
    },
  });
}

function element(tag = "div") {
  const found = new Map();
  const listeners = new Map();
  const el = {
    tag,
    style: {},
    classList: { add() {}, remove() {} },
    width: 0,
    height: 0,
    textContent: "",
    innerHTML: "",
    parentElement: { clientWidth: 900, clientHeight: 420 },
    getContext: () => context2d(),
    addEventListener(type, fn) {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(fn);
    },
    removeEventListener(type, fn) {
      const list = listeners.get(type) || [];
      const at = list.indexOf(fn);
      if (at >= 0) list.splice(at, 1);
    },
    // Lets a run send a real click through the real handler, which is the only
    // way to cover picking without a browser.
    dispatch(type, event) {
      for (const fn of listeners.get(type) || []) fn(event);
    },
    requestFullscreen: () => Promise.resolve(),
    setPointerCapture() {},
    releasePointerCapture() {},
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 900, height: 420 }),
    remove() {
      el.removed = true;
    },
    // Only class selectors are used in this codebase, so a crude substring
    // check against the markup is enough to tell present from absent. Handing
    // back an element for everything would hide a control that was never
    // rendered - which throws in a real browser.
    querySelector: (sel) => {
      if (!String(el.innerHTML).includes(sel.replace(/^\./, ""))) return null;
      if (!found.has(sel)) found.set(sel, element());
      return found.get(sel);
    },
    appendChild() {},
  };
  return el;
}

const frames = [];
globalThis.window = {
  devicePixelRatio: 2,
  addEventListener() {},
  removeEventListener() {},
};
globalThis.document = {
  hidden: false,
  fullscreenElement: null,
  createElement: () => element("canvas"),
  addEventListener() {},
  removeEventListener() {},
};
globalThis.performance = performance;
globalThis.requestAnimationFrame = (cb) => {
  frames.push(cb);
  return frames.length;
};
globalThis.cancelAnimationFrame = () => {};
globalThis.ResizeObserver = class {
  observe() {}
  disconnect() {}
};
globalThis.IntersectionObserver = class {
  observe() {}
  disconnect() {}
};
globalThis.Path2D = class {
  moveTo() {}
  lineTo() {}
  closePath() {}
};
globalThis.Image = class {
  constructor() {
    setTimeout(() => this.onload && this.onload(), 0);
  }
};

/* --------------------------------------------------------------- the runs */

function fakeModel(state) {
  const store = { ...state };
  return {
    get: (key) => store[key],
    set: (key, value) => {
      store[key] = value;
    },
    save_changes() {},
    on() {},
  };
}

const results = {};

for (const run of spec.runs) {
  const source = run.modules
    .map((name) => readFileSync(join(STATIC, name), "utf8"))
    .join("\n")
    .replace('"https://esm.sh/three@0.160.0"', JSON.stringify(STUB));

  const record = { ok: false, frames: 0 };
  try {
    const mod = await import(
      "data:text/javascript," + encodeURIComponent(source)
    );
    const el = element();
    frames.length = 0;
    const model = fakeModel(run.state);
    const cleanup = await mod.default.render({ model, el });

    // Setup reports a texture failure by writing into the status line rather
    // than throwing, so check that separately.
    const text = (sel) => {
      const node = el.querySelector(sel);
      return node ? node.textContent : null;
    };
    const status = text(".es-status");
    if (String(status).includes("could not load")) throw new Error(status);

    // Start from the real clock: render() stamped performance.now(), and a
    // timestamp behind that would hand the first frame a negative dt.
    let tick = performance.now();
    const wanted = run.frames || 4;
    const clocks = [];
    for (let i = 0; i < wanted; i++) {
      const cb = frames.shift();
      if (!cb) break;
      frames.length = 0; // drop anything else queued; cb re-queues itself
      tick += 16.7;
      cb(tick);
      clocks.push(text(".es-clock"));
      record.frames += 1;
    }
    // Optional: press and release on a canvas, and see where it puts things.
    if (run.click) {
      const target = el.querySelector(run.click.selector);
      const at = {
        clientX: run.click.x,
        clientY: run.click.y,
        pointerId: 1,
      };
      if (target) {
        target.dispatch("pointerdown", at);
        target.dispatch("pointerup", at);
        target.dispatch("click", at);
      }
      const three = await import(STUB);
      record.click = {
        latitude: model.get("latitude"),
        longitude: model.get("longitude"),
        marker: model.get("marker"),
        recursive: three.Raycaster.lastRecursive,
      };
    }

    record.clock = text(".es-clock");
    record.clocks = clocks;
    record.transport = text(".es-play");
    record.fullscreen = text(".es-full");
    record.bigname = text(".es-bigname");
    record.readouts = {
      speed: text(".es-ctl-out-speed"),
      light: text(".es-ctl-out-light"),
      sunlight: text(".es-ctl-out-sunlight"),
      node: text(".es-ctl-out-node"),
      zoom: text(".es-ctl-out-zoom"),
      when: text(".es-ctl-out-when"),
      lat: text(".es-ctl-out-lat"),
    };
    record.scale = text(".es-scale");
    if (typeof cleanup === "function") cleanup();
    record.ok = record.frames >= Math.min(2, wanted);
    if (!record.ok) record.error = "render() never queued a frame";
  } catch (err) {
    record.error = String((err && err.stack) || err);
  }
  results[run.name] = record;
}

console.log(JSON.stringify(results));
