// Dimensioni reali dei video. ffprobe non e installato e il moov di questi file
// non espone avc1 in chiaro all'inizio, quindi li interroga il browser da una
// pagina file:// same-origin.
// uso: node vdim.mjs <pagina.html>
import { chromium } from "playwright-core";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";
const b = await chromium.launch({ channel: "msedge", headless: true });
const p = await b.newPage();
await p.goto(pathToFileURL(resolve(process.argv[2])).href, { waitUntil: "load" });
const out = await p.evaluate(async () => {
  const vs = [...document.querySelectorAll("video")];
  await Promise.all(vs.map((v) => v.readyState >= 1 ? null :
    new Promise((r) => { v.onloadedmetadata = r; v.onerror = r; setTimeout(r, 8000); })));
  return vs.map((v) => ({ n: v.dataset.n, w: v.videoWidth, h: v.videoHeight, d: Math.round(v.duration * 10) / 10 }));
});
for (const v of out) console.log(`  ${v.n.padEnd(16)} ${v.w}x${v.h}  ${v.d}s`);
await b.close();
