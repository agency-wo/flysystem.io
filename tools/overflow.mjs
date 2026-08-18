// Matrice di controlli di impaginazione: tutte le pagine per tutte le
// larghezze, riusando un solo browser. Il ciclo che lanciava shot.mjs una
// volta per combinazione impiegava oltre due minuti per 35 controlli.
//
// Due controlli distinti:
//   1. overflow orizzontale del documento (chi sfora, ignorando i discendenti
//      gia tagliati da un antenato);
//   2. le foto a vivo sono davvero a vivo. Serve perche una foto ridotta a una
//      scheggia di 20 px NON produce overflow e passava il primo controllo:
//      e successo davvero, la regola da desktop .bleed-grid--sx
//      .bleed-grid__foto batteva per specificita l'override da telefono e la
//      foto restava larga quanto il margine, sovrapposta al testo.
//
// uso: node overflow.mjs [larghezze separate da virgola]
import { chromium } from "playwright-core";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";
import { readdirSync } from "node:fs";

const widths = (process.argv[2] || "320,360,390,414,768,960,1440,1907")
  .split(",").map(Number);
const pages = readdirSync(".").filter((f) => f.endsWith(".html"));

const browser = await chromium.launch({ channel: "msedge", headless: true });
let rotti = 0;
for (const f of pages) {
  const url = pathToFileURL(resolve(f)).href;
  const riga = [];
  for (const w of widths) {
    const page = await browser.newPage({ viewport: { width: w, height: 900 } });
    await page.goto(url, { waitUntil: "load" });
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(() => {
      document.querySelectorAll("img[loading='lazy']").forEach((i) => (i.loading = "eager"));
      document.querySelectorAll(".rv, .rv-rule, .rv-img").forEach((el) => el.classList.add("in"));
    });
    const bad = await page.evaluate(() => {
      const doc = document.documentElement;
      const out = [];
      if (doc.scrollWidth > doc.clientWidth + 1) {
        document.querySelectorAll("body *").forEach((el) => {
          const r = el.getBoundingClientRect();
          if (r.right <= doc.clientWidth + 1 || r.width === 0 || out.length >= 4) return;
          // Un elemento dentro un antenato che taglia non allarga il documento:
          // senza questo controllo le immagini in parallasse (scale 1.12 dentro
          // una figure con overflow:clip) risultavano tutte colpevoli.
          let n = el.parentElement, tagliato = false;
          while (n && n !== document.body) {
            if (getComputedStyle(n).overflowX !== "visible") { tagliato = true; break; }
            n = n.parentElement;
          }
          if (!tagliato)
            out.push(`${el.tagName.toLowerCase()}.${[...el.classList].join(".")}@${Math.round(r.right)}`);
        });
      }
      return out;
    });
    const vivo = await page.evaluate(() => {
      const vw = document.documentElement.clientWidth;
      const guai = [];
      document.querySelectorAll(".bleed-grid__foto").forEach((el) => {
        const r = el.getBoundingClientRect();
        const tocca = r.left <= 1 || r.right >= vw - 1;
        if (r.width < vw * 0.3) guai.push(`foto-a-vivo larga ${Math.round(r.width)}px su ${vw}`);
        else if (!tocca) guai.push(`foto-a-vivo non tocca il bordo (${Math.round(r.left)}..${Math.round(r.right)})`);
      });
      return guai;
    });
    await page.close();
    const tutti = [...bad, ...vivo];
    if (tutti.length) { rotti++; riga.push(`${w}:ROTTO ${tutti.join(" ")}`); }
    else riga.push(`${w}:ok`);
  }
  console.log(`  ${f.padEnd(16)} ${riga.join("  ")}`);
}
await browser.close();
console.log(rotti ? `\n${rotti} combinazioni rotte` : `\nnessun overflow: ${pages.length} pagine x ${widths.length} larghezze`);
