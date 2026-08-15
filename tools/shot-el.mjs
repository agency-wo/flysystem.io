/* Screenshot di un singolo elemento, per controllare un componente senza
   doverlo cercare a occhio dentro una pagina intera.

   node tools/shot-el.mjs <url> <selettore> <out.png> [larghezza]

   Stesse accortezze di shot.mjs: headless esplicito (senza, il lancio resta
   appeso), attesa del decode delle immagini, e soprattutto le classi di
   reveal forzate a "in", altrimenti gli elementi con .rv sono ancora a
   opacita' zero e lo scatto esce vuoto. */
import { chromium } from "playwright-core";

const [url, sel, out, w] = process.argv.slice(2);
if (!url || !sel || !out) {
  console.error("uso: node tools/shot-el.mjs <url> <selettore> <out.png> [larghezza]");
  process.exit(2);
}
const width = Number(w) || 1440;

const browser = await chromium.launch({ channel: "msedge", headless: true });
const page = await browser.newPage({
  viewport: { width, height: 900 },
  deviceScaleFactor: 2,
});

/* "load" e non "networkidle": con i video in loop la rete non resta mai ferma
   abbastanza e networkidle puo' non scattare mai. */
await page.goto(url, { waitUntil: "load" });
await page.addStyleTag({ content: "html { scroll-behavior: auto !important }" });
await page.evaluate(() => document.fonts.ready);
await page.evaluate(() => {
  document.querySelectorAll("img[loading='lazy']").forEach((img) => (img.loading = "eager"));
  document.querySelectorAll(".rv, .rv-rule, .rv-img").forEach((el) => el.classList.add("in"));
});
await page.evaluate(() =>
  Promise.all([...document.images].map((i) => i.decode().catch(() => {})))
);

const el = await page.$(sel);
if (!el) {
  console.log("SELETTORE NON TROVATO: " + sel);
  await browser.close();
  process.exit(1);
}
await el.scrollIntoViewIfNeeded();
await page.waitForTimeout(300);

const box = await el.boundingBox();
const pad = 30;
await page.screenshot({
  path: out,
  clip: {
    x: Math.max(0, box.x - pad),
    y: Math.max(0, box.y - pad),
    width: Math.min(box.width + pad * 2, width),
    height: box.height + pad * 2,
  },
});
console.log(JSON.stringify({ sel, w: Math.round(box.width), h: Math.round(box.height) }));
await browser.close();
