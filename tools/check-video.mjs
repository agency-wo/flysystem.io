/* Verifica dei video in WebKit reale (il motore di Safari).
 *
 * Controlla i tre stati in cui Safari nega l'autoplay e in cui prima restava
 * un poster morto:
 *   1. normale                -> il loop parte da solo
 *   2. prefers-reduced-motion -> non parte da solo, ma il pulsante c'e e funziona
 *   3. play() negato           -> compare il pulsante e il click avvia davvero
 * Pretende inoltre zero errori di pagina, con una sola eccezione dichiarata:
 * il RangeError che i media controls di Safari 26 lanciano da soli quando
 * compaiono (vedi KNOWN_WEBKIT_BUG piu sotto). Qualunque altro errore fa
 * fallire il controllo.
 *
 * Il server interno risponde alle richieste Range: `python -m http.server` NON
 * lo fa e questo da solo basta a rompere i video su Safari.
 *
 * usage: node tools/check-video.mjs
 */
import { webkit } from "playwright";
import { createServer } from "node:http";
import { createReadStream, statSync } from "node:fs";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = normalize(join(fileURLToPath(new URL(".", import.meta.url)), ".."));
const TYPES = {
  ".html": "text/html", ".css": "text/css", ".js": "text/javascript",
  ".mp4": "video/mp4", ".jpg": "image/jpeg", ".png": "image/png",
  ".webp": "image/webp", ".avif": "image/avif", ".woff2": "font/woff2",
  ".svg": "image/svg+xml", ".pdf": "application/pdf",
};

const server = createServer((req, res) => {
  const path = join(ROOT, decodeURIComponent(req.url.split("?")[0]));
  let st;
  try {
    st = statSync(path);
  } catch {
    res.writeHead(404).end("not found");
    return;
  }
  const type = TYPES[extname(path)] || "application/octet-stream";
  const range = req.headers.range;
  if (range) {
    const m = /bytes=(\d*)-(\d*)/.exec(range);
    const start = m[1] ? parseInt(m[1], 10) : 0;
    const end = m[2] ? parseInt(m[2], 10) : st.size - 1;
    res.writeHead(206, {
      "Content-Type": type,
      "Content-Range": `bytes ${start}-${end}/${st.size}`,
      "Accept-Ranges": "bytes",
      "Content-Length": end - start + 1,
    });
    createReadStream(path, { start, end }).pipe(res);
  } else {
    res.writeHead(200, { "Content-Type": type, "Content-Length": st.size, "Accept-Ranges": "bytes" });
    createReadStream(path).pipe(res);
  }
});
await new Promise((r) => server.listen(8044, r));
const BASE = "http://127.0.0.1:8044/";

// Simula il risparmio energetico iOS: play() viene negato finche non c'e un vero
// gesto dell'utente, che invece e sempre sufficiente. Cosi si verifica davvero
// che il pulsante di recupero funzioni, non solo che compaia.
const DENY = `
  (() => {
    let allowed = false;
    addEventListener("pointerdown", () => { allowed = true; }, true);
    const real = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = function () {
      if (!allowed) return Promise.reject(new DOMException("denied", "NotAllowedError"));
      return real.apply(this, arguments);
    };
  })();
`;

const CASES = [
  { page: "bolla.html", label: "bolla drone" },
  { page: "index.html", label: "home pergole" },
];

/* Bug noto del motore, non nostro: quando si attiva `controls`, i media controls
   di Safari 26 lanciano una volta un RangeError formattando il tempo. Verificato
   che accade con qualunque tempistica (anche con duration gia nota e video in
   riproduzione) e che NON interrompe la riproduzione. Per questo il primo avvio
   passa dal nostro pulsante e non dai controlli di sistema. Qui lo tolleriamo in
   modo esplicito, cosi qualunque ALTRO errore fa comunque fallire il controllo. */
const KNOWN_WEBKIT_BUG = /Temporal\.Duration properties must be finite/;
const unexpected = (list) => list.filter((e) => !KNOWN_WEBKIT_BUG.test(e));

const browser = await webkit.launch();
let failures = 0;

function report(ok, msg) {
  if (!ok) failures++;
  console.log(`${ok ? "  ok  " : "  FAIL"}  ${msg}`);
}

for (const { page: file, label } of CASES) {
  for (const mode of ["normale", "reduced-motion", "autoplay-negato"]) {
    const ctx = await browser.newContext({
      viewport: { width: 390, height: 844 },
      reducedMotion: mode === "reduced-motion" ? "reduce" : "no-preference",
    });
    const p = await ctx.newPage();
    const errors = [];
    p.on("pageerror", (e) => errors.push(String(e)));
    if (mode === "autoplay-negato") await p.addInitScript(DENY);

    await p.goto(BASE + file, { waitUntil: "load" });
    await p.locator("[data-video] video[data-loop]").scrollIntoViewIfNeeded();
    await p.waitForTimeout(3000);

    const s = await p.evaluate(() => {
      const v = document.querySelector("[data-video] video[data-loop]");
      const b = document.querySelector("[data-video] [data-play]");
      return {
        paused: v.paused, t: +v.currentTime.toFixed(2), ready: v.readyState,
        err: v.error && v.error.code, btn: b ? !b.hidden : null,
      };
    });

    if (mode === "normale") {
      report(!s.paused && s.t > 0, `${label} / ${mode}: parte da solo (t=${s.t}s, paused=${s.paused})`);
      report(s.btn === false, `${label} / ${mode}: nessun pulsante quando parte da solo`);
    } else {
      report(s.paused, `${label} / ${mode}: non parte da solo, come deve`);
      report(s.btn === true, `${label} / ${mode}: il pulsante di avvio e visibile`);
      await p.locator("[data-video] [data-play]").click();
      await p.waitForTimeout(1500);
      const after = await p.evaluate(() => {
        const v = document.querySelector("[data-video] video[data-loop]");
        return { paused: v.paused, t: +v.currentTime.toFixed(2) };
      });
      report(!after.paused && after.t > 0, `${label} / ${mode}: il click lo avvia (t=${after.t}s)`);
    }
    report(!s.err, `${label} / ${mode}: nessun MediaError`);
    report(errors.length === 0, `${label} / ${mode}: zero errori di pagina${errors.length ? " -> " + errors[0].slice(0, 120) : ""}`);
    await ctx.close();
  }
}

// il video integrale parte al click e mostra i controlli solo dopo l'avvio
{
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const p = await ctx.newPage();
  const errors = [];
  p.on("pageerror", (e) => errors.push(String(e)));
  await p.goto(BASE + "index.html", { waitUntil: "load" });
  await p.locator("[data-full-trigger]").scrollIntoViewIfNeeded();
  await p.locator("[data-full-trigger]").click();
  await p.waitForTimeout(2500);
  const s = await p.evaluate(() => {
    const f = document.querySelector("video[data-full]");
    const l = document.querySelector("video[data-loop]");
    return { hidden: f.hidden, paused: f.paused, t: +f.currentTime.toFixed(2), controls: f.controls, loopPaused: l.paused };
  });
  report(!s.hidden && !s.paused && s.t > 0, `home integrale: parte al click (t=${s.t}s)`);
  report(s.controls, "home integrale: controlli attivi dopo l'avvio");
  report(s.loopPaused, "home integrale: il loop viene messo in pausa");
  const other = unexpected(errors);
  report(other.length === 0, `home integrale: nessun errore oltre al bug noto di WebKit${other.length ? " -> " + other[0].slice(0, 120) : ""}`);
  report(errors.every((e) => KNOWN_WEBKIT_BUG.test(e)), "home integrale: gli errori presenti sono solo quello noto del motore");
  await ctx.close();
}

await browser.close();
server.close();
console.log(failures ? `\n${failures} controlli falliti` : "\nTutti i controlli video superati");
process.exit(failures ? 1 : 0);
