/* Evaluates earthkit.js's track readers outside a browser.
 *
 *     node contract_driver.mjs <earthkit.js> <queries.json>
 *
 * Everything above the "3d bodies" banner is free of three.js and the DOM, so
 * it can be imported on its own. Reads a JSON payload of tracks plus the times
 * to sample, and prints what the JavaScript makes of them.
 */

import { readFileSync } from "node:fs";

const source = readFileSync(process.argv[2], "utf8");
const banner = source.indexOf("3d bodies");
if (banner < 0) throw new Error("could not locate the 3d-bodies banner");
const head = source.slice(0, source.lastIndexOf("/* ---", banner));

const exported = [
  "sampleChannel",
  "sampleVector",
  "stepAt",
  "trackSample",
  "tableLookup",
  "gridRowAt",
  "gridColValue",
  "wrapLon",
  "fmtHM",
];
const kit = await import(
  "data:text/javascript," +
    encodeURIComponent(head + `\nexport {${exported.join(",")}};\n`)
);

const spec = JSON.parse(readFileSync(process.argv[3], "utf8"));
const out = { samples: {}, tables: {}, gridRows: {}, gridCols: {}, clock: [] };

for (const [name, track] of Object.entries(spec.tracks)) {
  out.samples[name] = (spec.times[name] || []).map((t) =>
    kit.trackSample(track, t),
  );
}

for (const [name, query] of Object.entries(spec.tableQueries || {})) {
  const tbl = spec.tracks[query.track].tables[query.table];
  out.tables[name] = query.at.map((x) => kit.tableLookup(tbl, x));
}

// Hand back the whole interpolated row: that is literally the curve the
// seasons panel draws, so Python can check it point for point.
for (const [name, query] of Object.entries(spec.gridQueries || {})) {
  const g = spec.tracks[query.track].grids[query.grid];
  out.gridRows[name] = query.at.map((row) => Array.from(kit.gridRowAt(g, row)));
  out.gridCols[name] = Array.from({ length: g.cols }, (_, c) =>
    kit.gridColValue(g, c),
  );
}

out.clock = (spec.clock || []).map((h) => kit.fmtHM(h));

console.log(JSON.stringify(out));
