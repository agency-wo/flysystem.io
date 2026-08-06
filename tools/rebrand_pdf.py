"""Motore di rebranding PDF: audit / apply / render.

Sostituisce marchi e contatti dei produttori con il brand Fly System.
Le regole per singolo PDF vivono in file JSON (tools/rebrand_jobs/*.json).

usage:
  python rebrand_pdf.py audit  <pdf> [needle ...]
  python rebrand_pdf.py apply  <pdf> <job.json> <out.pdf>
  python rebrand_pdf.py render <pdf> <outdir> [--pages 1,5,9] [--px 720]

Job JSON:
{
  "text_rules": [{"needle": "...", "replace_with": "..."|null,
                  "whole_line": false, "pages": [..]|null}],
  "patches":    [{"page": 1, "rect": [x0,y0,x1,y1],
                  "bg": [r,g,b]|null, "logo": "navy"|"white"|null,
                  "logo_rect": [..]|null, "logo_max_frac": 0.8,
                  "text": {"lines": ["..."], "size": 9, "color": [r,g,b],
                           "rect": [..], "align": "left"}|null}],
  "shrink": {"dpi": 96, "quality": 70}|null
}
"""
import json
import statistics
import sys
from pathlib import Path

import fitz

NEEDLES = ["rikreo", "materika", "materica", "terraviva", "terra viva",
           "laterraviva", "castellarano", "maurizio", ".xyz", "sassuolo",
           "gardenliving", "outdoor living"]
KEEP = ["uniclic", "clicky"]
TOOLS = Path(__file__).parent
LOGOS = {"navy": TOOLS / "out" / "logo-navy.png",
         "white": TOOLS / "out" / "logo-white.png"}


def int_rgb(c):
    return ((c >> 16) & 255, (c >> 8) & 255, c & 255)


def redact_band(rect):
    """Rettangolo di redazione: banda verticale centrale del match.

    I glyph box di font con FontBBox ampio (es. AvenirNext) sconfinano nelle
    righe adiacenti: un rect pieno (o cresciuto) le cancellerebbe. La banda
    centrale interseca comunque i glifi bersaglio ma evita i vicini.
    """
    dy = rect.height * 0.3
    return fitz.Rect(rect.x0 - 0.5, rect.y0 + dy, rect.x1 + 0.5, rect.y1 - dy)


def span_for(page, rect, needle):
    """Trova lo span di testo che contiene il match (per size/colore/linea)."""
    d = page.get_text("dict")
    for block in d.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                sb = fitz.Rect(span["bbox"])
                if sb.intersects(rect) and needle.lower() in span["text"].lower():
                    return line, span
    # fallback: solo intersezione geometrica
    for block in d.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if fitz.Rect(span["bbox"]).intersects(rect):
                    return line, span
    return None, None


def audit(pdf: Path, needles):
    doc = fitz.open(pdf)
    total = 0
    for pno, page in enumerate(doc, start=1):
        chars = len(page.get_text())
        hits = []
        for n in needles:
            for r in page.search_for(n):
                _, span = span_for(page, r, n)
                size = f"{span['size']:.1f}pt" if span else "?"
                col = ("#%02x%02x%02x" % int_rgb(span["color"])) if span else "?"
                font = span["font"] if span else "?"
                hits.append(f"  '{n}' rect=({r.x0:.0f},{r.y0:.0f},{r.x1:.0f},{r.y1:.0f}) {size} {col} {font}")
                total += 1
        if hits:
            print(f"p{pno} (chars={chars}):")
            print("\n".join(hits))
    print(f"TOTAL HITS: {total}")
    return total


def apply_job(pdf: Path, job_p: Path, out: Path):
    job = json.loads(job_p.read_text(encoding="utf-8"))
    doc = fitz.open(pdf)

    for pno, page in enumerate(doc, start=1):
        retypes = []  # (rect, text, size, color, align) dopo le redazioni
        annots = 0
        for rule in job.get("text_rules", []):
            if rule.get("pages") and pno not in rule["pages"]:
                continue
            for r in page.search_for(rule["needle"]):
                line, span = span_for(page, r, rule["needle"])
                if rule.get("whole_line") and line:
                    lrect = fitz.Rect(line["bbox"])
                    ltext = "".join(s["text"] for s in line["spans"])
                    lo = ltext.lower().find(rule["needle"].lower())
                    new = (ltext[:lo] + (rule.get("replace_with") or "")
                           + ltext[lo + len(rule["needle"]):]) if lo >= 0 else ltext
                    page.add_redact_annot(redact_band(lrect))
                    annots += 1
                    if rule.get("replace_with") is not None and span:
                        retypes.append((lrect, new, span["size"],
                                        int_rgb(span["color"]),
                                        span["origin"][1]))
                else:
                    page.add_redact_annot(redact_band(r))
                    annots += 1
                    if rule.get("replace_with") and span:
                        retypes.append((r, rule["replace_with"], span["size"],
                                        int_rgb(span["color"]),
                                        span["origin"][1]))
        if annots:
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                                  graphics=fitz.PDF_REDACT_LINE_ART_NONE)
        for rect, text, size, col, baseline in retypes:
            page.insert_text((rect.x0, baseline), text, fontname="helv",
                             fontsize=size, color=tuple(c / 255 for c in col))

    for p in job.get("patches", []):
        page = doc[p["page"] - 1]
        rect = fitz.Rect(p["rect"])
        bg = p.get("bg")
        if bg is None:
            bg = sample_border(page, rect)
        page.draw_rect(rect, color=None, fill=tuple(c / 255 for c in bg))
        if p.get("logo"):
            lp = LOGOS[p["logo"]]
            if p.get("logo_rect"):
                lrect = fitz.Rect(p["logo_rect"])
            else:
                frac = p.get("logo_max_frac", 0.8)
                lrect = inset_center(rect, frac)
            page.insert_image(lrect, filename=str(lp), keep_proportion=True,
                              rotate=p.get("logo_rotate", 0))
        if p.get("text"):
            t = p["text"]
            page.insert_textbox(fitz.Rect(t["rect"]), "\n".join(t["lines"]),
                                fontname=t.get("font", "helv"),
                                fontsize=t["size"],
                                color=tuple(c / 255 for c in t["color"]),
                                align={"left": 0, "center": 1, "right": 2}[t.get("align", "left")])

    shr = job.get("shrink")
    if shr:
        doc.rewrite_images(dpi_threshold=shr.get("dpi_threshold", 120),
                           dpi_target=shr["dpi"], quality=shr["quality"])
        shrink_leftovers(doc, shr)
    doc.save(out, garbage=4, deflate=True)
    mb = out.stat().st_size / 1024 / 1024
    print(f"saved {out} ({mb:.1f} MB)")


def shrink_leftovers(doc, shr):
    """Ricampiona le immagini che rewrite_images salta (es. JPEG CMYK).

    Converte in RGB (stessa resa con cui MuPDF le mostra), riduce alla
    densita' target e ricomprime JPEG. Salta immagini con maschera.
    """
    import io
    from PIL import Image
    thr = shr.get("dpi_threshold", 120)
    target = shr["dpi"]
    quality = shr["quality"]
    done = set()
    n_done = 0
    for page in doc:
        for img in page.get_images(full=True):
            xref, smask = img[0], img[1]
            if xref in done:
                continue
            done.add(xref)
            if smask:
                continue
            rects = page.get_image_rects(xref)
            if not rects:
                continue
            r = max(rects, key=lambda rc: rc.width * rc.height)
            if not r.width:
                continue
            dpi = img[2] / (r.width / 72)
            if dpi <= thr:
                continue
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.alpha:
                    continue
                if pix.colorspace is None:
                    continue
                if pix.colorspace.n >= 4 or pix.n > 3:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                mode = "RGB" if pix.n == 3 else "L"
                im = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
                scale = target / dpi
                im = im.resize((max(1, round(pix.width * scale)),
                                max(1, round(pix.height * scale))), Image.LANCZOS)
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=quality)
                page.replace_image(xref, stream=buf.getvalue())
                n_done += 1
            except Exception as e:
                print(f"  WARN shrink: xref {xref} saltato ({e})")
    if n_done:
        print(f"  shrink extra: {n_done} immagini ricampionate")


def sample_border(page, rect):
    """Colore mediano dei pixel sul bordo esterno del rettangolo."""
    pad = 4
    outer = fitz.Rect(rect.x0 - pad, rect.y0 - pad, rect.x1 + pad, rect.y1 + pad)
    outer.intersect(page.rect)
    pm = page.get_pixmap(clip=outer, matrix=fitz.Matrix(2, 2))
    w, h, n = pm.width, pm.height, pm.n
    px = pm.samples
    vals = []
    edge = 3
    for y in range(h):
        for x in range(w):
            if edge <= x < w - edge and edge <= y < h - edge:
                continue
            o = (y * w + x) * n
            vals.append((px[o], px[o + 1], px[o + 2]))
    med = tuple(int(statistics.median(c[i] for c in vals)) for i in range(3))
    spread = max(max(c[i] for c in vals) - min(c[i] for c in vals) for i in range(3))
    if spread > 60:
        print(f"  WARN: fondo non uniforme attorno a {rect} (spread {spread}), mediano {med}")
    return med


def inset_center(rect, frac):
    from PIL import Image
    im = Image.open(LOGOS["navy"])
    ar = im.width / im.height
    w = rect.width * frac
    h = w / ar
    if h > rect.height * frac:
        h = rect.height * frac
        w = h * ar
    cx, cy = (rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2
    return fitz.Rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def render(pdf: Path, outdir: Path, pages=None, px=720):
    outdir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf)
    sel = pages or range(1, doc.page_count + 1)
    for pno in sel:
        page = doc[pno - 1]
        scale = px / max(page.rect.width, page.rect.height)
        pm = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
        pm.save(outdir / f"p{pno:03d}.png")
    print(f"rendered {len(list(sel))} pages -> {outdir}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "audit":
        extra = sys.argv[3:]
        audit(Path(sys.argv[2]), extra or NEEDLES)
    elif cmd == "apply":
        apply_job(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    elif cmd == "render":
        args = sys.argv[2:]
        pdf, outdir = Path(args[0]), Path(args[1])
        pages = None
        px = 720
        if "--pages" in args:
            pages = [int(x) for x in args[args.index("--pages") + 1].split(",")]
        if "--px" in args:
            px = int(args[args.index("--px") + 1])
        render(pdf, outdir, pages, px)
