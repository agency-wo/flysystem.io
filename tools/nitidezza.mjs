// Misura se le fotografie sono servite abbastanza grandi per lo spazio in cui
// vengono rese, cioe il difetto che l'utente ha visto ("sembrano tutte di bassa
// qualita tranne l'edificio").
//
// Nessun controllo esistente lo vedeva: overflow.mjs guarda la larghezza,
// check-video.mjs i video, e Lighthouse segnala il problema opposto (immagini
// troppo grandi per il riquadro), mai troppo piccole.
//
// Due trappole, in cui sono gia caduto misurando a mano:
//
//   1. NON usare getBoundingClientRect(): le immagini in parallasse hanno
//      scale(1.12) e la larghezza risulta gonfiata del 12%. Serve offsetWidth,
//      che e la larghezza di impaginazione, senza transform.
//
//   2. NON usare naturalWidth come larghezza del file: con srcset a descrittori
//      "w" il browser restituisce la dimensione intrinseca CORRETTA PER
//      DENSITA, quindi il rapporto viene sempre esattamente dpr e sembra che
//      vada tutto bene. La larghezza vera si legge dal file su disco.
//
// uso: node nitidezza.mjs [--json]

import { chromium } from "playwright-core";
import { pathToFileURL } from "node:url";
import { resolve, join } from "node:path";
import { readdirSync, readFileSync, existsSync } from "node:fs";

const SOGLIA = 1.35;

// Immagini che restano sopra soglia per limite della sorgente, non per errore
// nostro. Dichiararle una per una e onesto; abbassare SOGLIA per farle passare
// no. Ogni voce dice DA DOVE viene il limite, cosi la prossima persona sa se
// e ancora vero o se nel frattempo e arrivata una fotografia migliore.
const ECCEZIONI = {
  "img/home/selezione": "foto del cliente fly8.jpeg, 1040 px: e tutto quello che esiste",
  "img/contatti/lead": "foto del cliente fly9.jpeg, 1210 px",
  "img/outdoor/montaggio": "foto del cliente perg2.jpeg, 1280 px",
  "img/home/hero-edificio": "stock 1920 px, il piu grande del sito",
  "img/cataloghi/lead": "master perduto, nessun originale piu grande nei PDF (cercato)",
  // il catalogo Bolla ha raster incorporati da 344x543 px, i due aerei 691x517:
  // nessuna larghezza generata puo aggiungere dettaglio che non esiste
  "img/bolla/": "catalogo Bolla, sorgente 344-691 px: vedi la nota in memoria",
};

function larghezzaReale(rel) {
  // legge la larghezza dall'intestazione del file, senza decodificarlo
  const p = join("assets", rel);
  if (!existsSync(p)) return null;
  const b = readFileSync(p);

  if (b.length > 24 && b.readUInt32BE(0) === 0x89504e47) return b.readUInt32BE(16); // PNG

  if (b[0] === 0xff && b[1] === 0xd8) { // JPEG
    let i = 2;
    while (i < b.length - 9) {
      if (b[i] !== 0xff) { i++; continue; }
      const m = b[i + 1];
      if (m >= 0xc0 && m <= 0xcf && m !== 0xc4 && m !== 0xc8 && m !== 0xcc)
        return b.readUInt16BE(i + 7);
      i += 2 + b.readUInt16BE(i + 2);
    }
    return null;
  }

  const ftyp = b.slice(4, 8).toString("latin1");
  if (ftyp === "ftyp") { // AVIF / HEIF: larghezza dentro la box ispe
    const k = b.indexOf(Buffer.from("ispe", "latin1"));
    if (k > 0) return b.readUInt32BE(k + 8);
    return null;
  }

  if (b.slice(0, 4).toString("latin1") === "RIFF" && b.slice(8, 12).toString("latin1") === "WEBP") {
    const f = b.slice(12, 16).toString("latin1");
    if (f === "VP8X") return (b.readUIntLE(24, 3) & 0xffffff) + 1;
    if (f === "VP8 ") return b.readUInt16LE(26) & 0x3fff;
    if (f === "VP8L") {
      const n = b.readUInt32LE(21);
      return (n & 0x3fff) + 1;
    }
  }
  return null;
}

const pagine = readdirSync(".").filter((f) => f.endsWith(".html"));
const casi = [
  { w: 1440, dpr: 2, nome: "portatile retina" },
  { w: 390, dpr: 3, nome: "telefono" },
];

const browser = await chromium.launch({ channel: "msedge", headless: true });
const tutte = [];

for (const { w, dpr, nome } of casi) {
  for (const f of pagine) {
    const page = await browser.newPage({ viewport: { width: w, height: 900 }, deviceScaleFactor: dpr });
    await page.goto(pathToFileURL(resolve(f)).href, { waitUntil: "load" });
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(() => {
      document.querySelectorAll("img[loading='lazy']").forEach((i) => (i.loading = "eager"));
      document.querySelectorAll(".rv, .rv-img, .rv-rule").forEach((el) => el.classList.add("in"));
    });
    await page.evaluate(async () => {
      for (let y = 0; y < document.body.scrollHeight; y += 700) {
        window.scrollTo(0, y);
        await new Promise((r) => setTimeout(r, 25));
      }
      window.scrollTo(0, 0);
    });
    await page.waitForTimeout(500);
    const imgs = await page.evaluate(() =>
      [...document.images]
        .filter((i) => i.offsetWidth > 40)
        .map((i) => ({
          src: ((i.currentSrc || i.src).split("/assets/")[1] || ""),
          box: i.offsetWidth,
        }))
    );
    await page.close();

    for (const im of imgs) {
      if (!im.src) continue;
      const reale = larghezzaReale(im.src);
      if (!reale) continue;
      const serve = Math.round(im.box * dpr);
      tutte.push({ caso: nome, w, dpr, pagina: f, ...im, reale, x: +(serve / reale).toFixed(2), serve });
    }
  }
}
await browser.close();

// una riga per file, tenendo il caso peggiore
const peggiore = new Map();
for (const r of tutte) {
  const k = r.src;
  if (!peggiore.has(k) || peggiore.get(k).x < r.x) peggiore.set(k, r);
}
const righe = [...peggiore.values()].sort((a, b) => b.x - a.x);

if (process.argv.includes("--json")) {
  console.log(JSON.stringify(righe, null, 1));
} else {
  let rotti = 0, scusati = 0;
  console.log(`\nsoglia ${SOGLIA}x  ·  caso peggiore fra portatile retina (1440@2x) e telefono (390@3x)\n`);
  for (const r of righe) {
    const ecc = Object.keys(ECCEZIONI).find((k) => r.src.startsWith(k));
    const sopra = r.x > SOGLIA;
    if (sopra && ecc) scusati++;
    else if (sopra) rotti++;
    const tag = !sopra ? "  ok    " : ecc ? "eccezione" : " SCARSA ";
    if (sopra || process.argv.includes("--tutte"))
      console.log(
        `  ${tag} x${String(r.x).padEnd(5)} file ${String(r.reale).padStart(4)}px  riquadro ${String(r.box).padStart(4)}css@${r.dpr}x -> servono ${String(r.serve).padStart(4)}px  ${r.src}` +
          (ecc ? `
              ^ ${ECCEZIONI[ecc]}` : "")
      );
  }
  console.log(`\n  immagini controllate: ${righe.length}`);
  console.log(`  sopra soglia per errore nostro: ${rotti}`);
  console.log(`  sopra soglia per limite di sorgente (dichiarate): ${scusati}`);
  process.exitCode = rotti ? 1 : 0;
}
