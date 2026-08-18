// Misura le grandezze che V14 dichiara di cambiare, invece di dedurle.
//
// La diagnosi di V14 nasce da un confronto numerico col riferimento a 1907px:
// la nostra foto di punta stava a 607px contro ~920, con 273px di margine
// morto per lato contro ~30. Questo script rimisura le stesse cose dopo ogni
// modifica, cosi "e piu grande" resta un numero e non un'impressione.
//
// uso: node measure.mjs <file.html> [width] [selettore-extra ...]
import { chromium } from "playwright-core";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const [, , target, w = "1907", ...extra] = process.argv;
if (!target) {
  console.error("uso: node measure.mjs <file.html> [width] [selettore ...]");
  process.exit(1);
}
const url = pathToFileURL(resolve(target)).href;

const browser = await chromium.launch({ channel: "msedge", headless: true });
const page = await browser.newPage({ viewport: { width: Number(w), height: 900 } });
await page.goto(url, { waitUntil: "load" });
await page.evaluate(() => document.fonts.ready);
await page.evaluate(() => {
  document.querySelectorAll("img[loading='lazy']").forEach((i) => (i.loading = "eager"));
  document.querySelectorAll(".rv, .rv-rule, .rv-img").forEach((el) => el.classList.add("in"));
});
await page.waitForTimeout(300);

const out = await page.evaluate((extraSel) => {
  const px = (n) => Math.round(n);
  const one = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return {
      sel,
      w: px(r.width),
      h: px(r.height),
      left: px(r.left),
      right: px(r.right),
      font: cs.fontSize,
      transform: cs.textTransform,
      tracking: cs.letterSpacing,
    };
  };

  const doc = document.documentElement;
  const wrap = document.querySelector(".wrap");
  const wrapR = wrap && wrap.getBoundingClientRect();

  // overflow orizzontale: lo stesso gate usato da shot.mjs
  const bad = [];
  if (doc.scrollWidth > doc.clientWidth + 1) {
    document.querySelectorAll("body *").forEach((el) => {
      const r = el.getBoundingClientRect();
      if (r.right > doc.clientWidth + 1 && r.width > 0 && bad.length < 8) {
        bad.push(`${el.tagName.toLowerCase()}.${[...el.classList].join(".")} right=${px(r.right)}`);
      }
    });
  }

  const sels = [
    ".dome-fig img",
    ".bolla-feature__grid",
    ".h-display",
    ".h2",
    ".lead",
    ".modello__num",
    ...extraSel,
  ];

  return {
    viewport: doc.clientWidth,
    scrollWidth: doc.scrollWidth,
    wrap: wrapR ? { w: px(wrapR.width), margine_morto_per_lato: px(wrapR.left) } : null,
    elementi: sels.map(one).filter(Boolean),
    bad,
  };
}, extra);

const pad = (s, n) => String(s).padEnd(n);
console.log(`\nviewport ${out.viewport}  scrollWidth ${out.scrollWidth}`);
if (out.wrap) console.log(`.wrap    ${out.wrap.w} px, margine morto ${out.wrap.margine_morto_per_lato} px per lato`);
console.log("");
for (const e of out.elementi) {
  console.log(
    `  ${pad(e.sel, 24)} ${pad(e.w + "x" + e.h, 12)} font ${pad(e.font, 8)} ${pad(e.transform, 10)} tracking ${e.tracking}`
  );
}
console.log(`\noverflow: ${out.bad.length ? JSON.stringify(out.bad, null, 2) : "[] ok"}`);
await browser.close();
