// Controlla che le fotografie in parallasse non finiscano sopra la loro
// didascalia mentre si scorre.
//
// Difetto trovato dal cliente e non visto da nessun controllo esistente: la
// regola di ritaglio stava sulla <figure>, che contiene ANCHE il figcaption,
// quindi l'immagine ingrandita del 12% dalla parallasse scivolava sul testo e
// lo copriva. Misurato: fino a 30 px di sovrapposizione su una didascalia alta
// 21, cioe nascosta del tutto.
//
// Perche serviva un controllo nuovo: overflow.mjs misura la larghezza a pagina
// ferma, nitidezza.mjs la risoluzione, didascalie.py il testo. Nessuno guarda
// cosa succede DURANTE lo scorrimento, che e l'unico momento in cui questo
// difetto esiste.
//
// uso: node parallasse.mjs

import { chromium } from "playwright-core";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";
import { readdirSync } from "node:fs";

const BANDE = ".hero-band, .photo-band, .cat-lead";
const PASSO = 40;   // px fra un campione e il successivo
const RAGGIO = 800; // quanto sopra e sotto la banda si campiona

const pagine = readdirSync(".").filter((f) => f.endsWith(".html"));
const viste = [
  { w: 390, h: 844, nome: "telefono" },
  { w: 1440, h: 900, nome: "desktop" },
];

const browser = await chromium.launch({ channel: "msedge", headless: true });
let rotti = 0, controllate = 0;

for (const { w, h, nome } of viste) {
  for (const f of pagine) {
    const page = await browser.newPage({ viewport: { width: w, height: h } });
    await page.goto(pathToFileURL(resolve(f)).href, { waitUntil: "load" });
    await page.evaluate(() => document.fonts.ready);
    await page.addStyleTag({ content: "html{scroll-behavior:auto!important}" });
    await page.evaluate(() => {
      document.querySelectorAll("img[loading='lazy']").forEach((i) => (i.loading = "eager"));
      document.querySelectorAll(".rv, .rv-img, .rv-rule").forEach((el) => el.classList.add("in"));
    });

    const bande = await page.evaluate((sel) =>
      [...document.querySelectorAll(sel)]
        .map((el, i) => ({ i, ha: !!el.querySelector("figcaption") }))
        .filter((b) => b.ha)
        .map((b) => b.i), BANDE);

    for (const idx of bande) {
      controllate++;
      const base = await page.evaluate(({ sel, idx }) => {
        const el = document.querySelectorAll(sel)[idx];
        return window.scrollY + el.getBoundingClientRect().top;
      }, { sel: BANDE, idx });

      let peggio = -9999;
      for (let off = -RAGGIO; off <= RAGGIO; off += PASSO) {
        await page.evaluate((y) => window.scrollTo(0, Math.max(0, y)), base + off);
        await page.waitForTimeout(35);
        const v = await page.evaluate(({ sel, idx }) => {
          const el = document.querySelectorAll(sel)[idx];
          const cap = el.querySelector("figcaption");
          const img = el.querySelector("img");
          if (!cap || !img) return -9999;
          // Il bordo inferiore DIPINTO: il rect dell'img comprende gia le
          // trasformazioni, ma va poi tagliato dal primo antenato che ritaglia.
          // Misurare il <picture> non basta: quando e display:contents non ha
          // una scatola propria e restituisce un rect privo di senso.
          let giu = img.getBoundingClientRect().bottom;
          let n = img.parentElement;
          while (n && n !== document.body) {
            if (getComputedStyle(n).overflowY !== "visible")
              giu = Math.min(giu, n.getBoundingClientRect().bottom);
            n = n.parentElement;
          }
          return Math.round(giu - cap.getBoundingClientRect().top);
        }, { sel: BANDE, idx });
        if (v > peggio) peggio = v;
      }

      if (peggio > 0) {
        rotti++;
        console.log(`  COPERTA  ${f} @${w} (${nome}) banda ${idx}: la foto copre la didascalia per ${peggio}px`);
      }
    }
    await page.close();
  }
}
await browser.close();

console.log(`\n  didascalie sotto banda in parallasse controllate: ${controllate}`);
console.log(`  coperte dalla fotografia durante lo scorrimento: ${rotti}`);
process.exitCode = rotti ? 1 : 0;
