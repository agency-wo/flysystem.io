// Screenshot harness: node shot.mjs <url-or-file> <out.png> [width] [height] [--full] [--menu]
// Uses installed Edge via playwright-core (no browser download). --menu opens the mobile menu first.
import { chromium } from "playwright-core";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const [, , target, out, w = "1440", h = "900", ...flags] = process.argv;
const full = flags.includes("--full") ? "--full" : "";
const menu = flags.includes("--menu");
if (!target || !out) {
  console.error("usage: node shot.mjs <url-or-file> <out.png> [width] [height] [--full] [--menu]");
  process.exit(1);
}
const url = /^https?:|^file:/.test(target) ? target : pathToFileURL(resolve(target)).href;

const browser = await chromium.launch({ channel: "msedge", headless: true });
const page = await browser.newPage({
  viewport: { width: Number(w), height: Number(h) },
  deviceScaleFactor: 1.5,
});
await page.goto(url, { waitUntil: "networkidle" });
await page.evaluate(() => document.fonts.ready);
// force lazy images + let reveal animations settle
await page.evaluate(() => {
  document.querySelectorAll("img[loading='lazy']").forEach((img) => (img.loading = "eager"));
  document.querySelectorAll(".rv, .rv-rule, .rv-img").forEach((el) => el.classList.add("in"));
});
await page.evaluate(async () => {
  for (let y = 0; y < document.body.scrollHeight; y += 800) {
    window.scrollTo(0, y);
    await new Promise((r) => setTimeout(r, 40));
  }
  window.scrollTo(0, 0);
});
await page.waitForLoadState("networkidle");
// ensure every image is decoded before capture (large below-fold AVIFs race the screenshot)
await page.evaluate(() => Promise.all([...document.images].map((i) => i.decode().catch(() => {}))));
await page.waitForTimeout(400);
if (menu) {
  await page.click(".nav-toggle");
  await page.waitForTimeout(600);
}
await page.screenshot({ path: out, fullPage: full === "--full" });
// report layout health
const overflow = await page.evaluate(() => {
  const doc = document.documentElement;
  const bad = [];
  if (doc.scrollWidth > doc.clientWidth + 1) {
    document.querySelectorAll("body *").forEach((el) => {
      const r = el.getBoundingClientRect();
      if (r.right > doc.clientWidth + 1 && r.width > 0 && bad.length < 8) {
        bad.push(`${el.tagName.toLowerCase()}.${[...el.classList].join(".")} right=${Math.round(r.right)}`);
      }
    });
  }
  return { scrollWidth: doc.scrollWidth, clientWidth: doc.clientWidth, bad };
});
console.log(JSON.stringify(overflow));
await browser.close();
