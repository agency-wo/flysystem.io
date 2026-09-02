# -*- coding: utf-8 -*-
"""Controllo unico del sito: SEO, dati strutturati, immagini, coerenza.

Portato da `kun/_tools/verify.py`, che fa lo stesso mestiere per un altro sito
statico a lingua singola. Quello non e' una libreria: host, numero WhatsApp e
endpoint del modulo sono scritti dentro, quindi si riusa copiando e adattando,
non importando. Qui restano i controlli che valgono per flysystem e cadono
quelli che non c'entrano (Web3Forms, WhatsApp, foto stock di quel cliente).

Due differenze deliberate rispetto all'originale:

1. **L'host non e' scritto qui dentro.** Viene letto dalla canonical di
   `index.html`, come fa `rebase.py`. Cosi' il giorno in cui il sito passa a
   MarketingPro o al dominio del cliente questo file non va toccato, e anzi e'
   proprio lui ad accorgersi se lo spostamento e' rimasto a meta'.
2. **I percorsi sono relativi, e devono restarlo.** L'originale pretende
   percorsi assoluti dalla radice; qui sarebbe un errore, perche' il sito e'
   servito da una sottocartella e `/assets/...` uscirebbe dal sito.

    python tools/verify.py

Esce con 1 se trova un problema. Gli avvisi non fanno fallire.
"""
import io
import json
import os
import re
import sys
from collections import defaultdict

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# L'elenco si ricava dal disco invece di stare scritto qui. Era una lista fissa,
# e aggiungere privacy.html ha fatto fallire il check 12 con un messaggio che
# accusava la sitemap ("solo in sitemap: privacy.html") mentre il file c'era
# davvero: era il cancello a non saperlo. Una lista fissa dentro il controllore
# trasforma ogni pagina nuova in un falso allarme.
TUTTE = sorted(f for f in os.listdir(RADICE) if f.endswith(".html"))
PAGINE = [f for f in TUTTE if f != "404.html"]

problemi, avvisi = [], []


def guasto(pagina, msg):
    problemi.append("%s: %s" % (pagina, msg))


def avviso(pagina, msg):
    avvisi.append("%s: %s" % (pagina, msg))


def leggi(nome):
    with io.open(os.path.join(RADICE, nome), encoding="utf-8") as f:
        return f.read()


def pulito(s):
    """Per stamparlo su una console Windows senza far esplodere cp1252."""
    return s.encode("ascii", "replace").decode("ascii")


def senza_commenti(s):
    return re.sub(r"<!--.*?-->", "", s, flags=re.S)


SRC = {n: leggi(n) for n in TUTTE}

# ---- l'host, dedotto dalla pagina invece che dichiarato qui ----
m = re.search(r'<link rel="canonical" href="(https?://[^"]+?)/?"', SRC["index.html"])
if not m:
    print("  index.html non ha una canonical: non so quale sia l'host")
    sys.exit(1)
BASE = m.group(1) + "/"


def url_di(nome):
    """L'indirizzo pubblico di una pagina, che NON porta l'estensione.

    Cloudflare Pages risponde 308 da /bolla.html a /bolla: l'indirizzo che
    restituisce 200 e' quello senza estensione, e la canonical deve puntare li'.
    Puntarla al .html significherebbe dichiarare canonica una URL che rimanda
    altrove. Il file su disco resta bolla.html: cambia l'indirizzo, non il nome.
    """
    return BASE if nome == "index.html" else BASE + nome[:-len(".html")]


# ---- 1. un solo h1 ----
for n in TUTTE:
    k = len(re.findall(r"<h1[\s>]", SRC[n]))
    if k != 1:
        guasto(n, "check 1: attesi 1 <h1>, trovati %d" % k)

# ---- 2/3. title e description: limiti e unicita' ----
titoli, descr = {}, {}
for n in TUTTE:
    src = SRC[n]
    mt = re.search(r"<title>(.*?)</title>", src, re.S)
    t = (mt.group(1).strip() if mt else "")
    if not t:
        guasto(n, "check 2: title mancante")
    elif not (20 <= len(t) <= 60):
        guasto(n, "check 2: title di %d caratteri (voluti 20-60)" % len(t))
    if t in titoli:
        guasto(n, "check 2: title duplicato, gia' su %s" % titoli[t])
    titoli[t] = n

    md = re.search(r'<meta name="description" content="(.*?)"', src, re.S)
    if n == "404.html":
        if 'name="robots" content="noindex"' not in src:
            guasto(n, "check 3: la 404 deve avere noindex")
        continue
    if not md:
        guasto(n, "check 3: description mancante")
    else:
        d = md.group(1).strip()
        if not (70 <= len(d) <= 160):
            guasto(n, "check 3: description di %d caratteri (voluti 70-160)" % len(d))
        if d in descr:
            guasto(n, "check 3: description duplicata, gia' su %s" % descr[d])
        descr[d] = n

# ---- 4. canonical presente e concorde ----
for n in PAGINE:
    mc = re.search(r'<link rel="canonical" href="([^"]+)"', SRC[n])
    if not mc:
        guasto(n, "check 4: canonical mancante")
    elif mc.group(1) != url_di(n):
        guasto(n, "check 4: canonical %s invece di %s" % (pulito(mc.group(1)), pulito(url_di(n))))

# ---- 5. Open Graph completo e concorde col title ----
for n in PAGINE:
    src = SRC[n]
    og = dict(re.findall(r'<meta property="(og:[a-z:]+)" content="([^"]*)"', src))
    for k in ("og:type", "og:title", "og:description", "og:image", "og:url", "og:locale"):
        if k not in og:
            guasto(n, "check 5: manca %s" % k)
    if og.get("og:url") and og["og:url"] != url_di(n):
        guasto(n, "check 5: og:url diverso dalla canonical")
    if og.get("og:image", "").startswith(BASE):
        f = og["og:image"][len(BASE):]
        if not os.path.exists(os.path.join(RADICE, f)):
            guasto(n, "check 5: og:image inesistente: %s" % f)
    if 'name="twitter:card"' not in src:
        guasto(n, "check 5: twitter:card mancante")

# ---- 6. JSON-LD: parsa, nodi attesi, nessun @id pendente ----
definiti, citati, prodotti = set(), [], 0
for n in PAGINE:
    blocchi = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', SRC[n], re.S)
    if not blocchi:
        guasto(n, "check 6: nessun blocco JSON-LD")
        continue
    tipi = set()
    for b in blocchi:
        try:
            dati = json.loads(b)
        except Exception as e:
            guasto(n, "check 6: JSON-LD non parsa: %s" % e)
            continue

        def gira(x):
            global prodotti
            if isinstance(x, list):
                for y in x:
                    gira(y)
            elif isinstance(x, dict):
                t = x.get("@type")
                if isinstance(t, str):
                    tipi.add(t)
                if t == "Product":
                    prodotti += 1
                    if not x.get("name") or not x.get("image"):
                        guasto(n, "check 6: Product senza name o image")
                if x.get("@id") and t:
                    definiti.add(x["@id"])
                if x.get("@id") and len(x) == 1:
                    citati.append((n, x["@id"]))
                for v in x.values():
                    gira(v)
        gira(dati)

    if "LocalBusiness" not in tipi:
        guasto(n, "check 6: manca il nodo LocalBusiness")
    if n != "index.html" and "BreadcrumbList" not in tipi:
        guasto(n, "check 6: manca BreadcrumbList su una sottopagina")

atteso = BASE + "#business"
if atteso not in definiti:
    guasto("JSON-LD", "check 6: il nodo %s non e' definito da nessuna pagina" % pulito(atteso))
for n, rid in citati:
    if rid not in definiti:
        guasto(n, "check 6: @id citato e mai definito: %s" % pulito(rid))
if prodotti == 0:
    avviso("bolla.html", "check 6: nessun Product nei dati strutturati")

# ---- 7. immagini: alt sempre presente, dimensioni dichiarate ----
for n in TUTTE:
    for tag in re.findall(r"<img\s[^>]*>", SRC[n]):
        a = dict(re.findall(r'([a-zA-Z-]+)="([^"]*)"', tag))
        if "alt" not in a:
            guasto(n, "check 7: <img> senza alt: %s" % pulito(tag[:90]))
        if not a.get("width") or not a.get("height"):
            guasto(n, "check 7: <img> senza width/height: %s" % pulito(tag[:90]))
        if a.get("fetchpriority") == "high" and a.get("loading") == "lazy":
            guasto(n, "check 7: immagine hero in lazy: %s" % pulito(tag[:90]))

# ---- 8. link e risorse locali: esistono; le ancore hanno un bersaglio ----
for n in TUTTE:
    src = senza_commenti(SRC[n])
    ids = set(re.findall(r'id="([^"]+)"', src))
    riferimenti = set(re.findall(r'(?:href|src|poster)="([^"]+)"', src))
    # Anche le srcset: e' li' che vive la maggior parte delle immagini, e una
    # rendition mancante non si vede finche' non capita la larghezza giusta.
    for gruppo in re.findall(r'(?:srcset|imagesrcset)="([^"]+)"', src):
        for cand in gruppo.split(","):
            u = cand.strip().split(" ")[0]
            if u:
                riferimenti.add(u)
    for h in riferimenti:
        if h.startswith(("http://", "https://", "mailto:", "tel:", "data:")):
            continue
        if h.startswith("#"):
            if len(h) > 1 and h[1:] not in ids:
                guasto(n, "check 8: ancora %s senza bersaglio" % h)
            continue
        if h.startswith("/"):
            guasto(n, "check 8: percorso assoluto %s: il sito sta in una "
                      "sottocartella, deve restare relativo" % h)
            continue
        percorso, _, frammento = h.partition("#")
        # La stringa di query non fa parte del nome del file: `style.css?v=1e52e5f2`
        # e' l'impronta di versiona.py, `contatti.html?oggetto=bolla` precompila
        # il modulo. Guardare il file senza toglierla vuol dire non trovarlo mai.
        percorso = percorso.split("?")[0]
        if not percorso:
            continue
        # I link fra pagine sono senza estensione (vedi url_di): sul disco il
        # file ce l'ha. "./" e' la home. Le risorse - css, js, immagini, pdf -
        # mantengono la loro estensione e passano dal primo ramo.
        if percorso in ("./", "."):
            fisico = "index.html"
        elif os.path.exists(os.path.join(RADICE, percorso)):
            fisico = percorso
        elif os.path.exists(os.path.join(RADICE, percorso + ".html")):
            fisico = percorso + ".html"
        else:
            guasto(n, "check 8: link o risorsa rotta: %s" % pulito(percorso))
            continue
        if frammento and fisico.endswith(".html"):
            if 'id="%s"' % frammento not in leggi(fisico):
                guasto(n, "check 8: frammento #%s assente in %s" % (frammento, fisico))

# ---- 9. niente risorse di terze parti ----
# canonical e alternate sono dichiarazioni di identita', non risorse caricate:
# puntano al sito stesso per definizione e non vanno contate come esterne.
for n in TUTTE:
    for tag in re.findall(r"<(?:script|link|img|iframe)\s[^>]*>", SRC[n]):
        if re.search(r'rel="(canonical|alternate)"', tag):
            continue
        for attr, val in re.findall(r'\b(src|href)="(https?://[^"]+)"', tag):
            if val.startswith(BASE):
                continue
            guasto(n, "check 9: risorsa esterna %s: %s" % (attr, pulito(val[:70])))

# ---- 10. NAP identico ovunque compaia ----
for n in TUTTE:
    for t in set(re.findall(r'href="tel:([^"]+)"', SRC[n])):
        if t not in ("+390541011058", "+393808972795"):
            guasto(n, "check 10: numero di telefono estraneo: %s" % t)
    for e in set(re.findall(r'href="mailto:([^"]+)"', SRC[n])):
        if e != "info@flysystemrn.it":
            guasto(n, "check 10: indirizzo email estraneo: %s" % e)

# ---- 11. lingua unica ----
for n in TUTTE:
    if '<html lang="it">' not in SRC[n]:
        guasto(n, 'check 11: manca <html lang="it">')
    if "hreflang" in SRC[n]:
        guasto(n, "check 11: hreflang su un sito monolingua")

# ---- 12. sitemap == pagine indicizzabili; robots nomina la sitemap ----
sm = os.path.join(RADICE, "sitemap.xml")
if not os.path.exists(sm):
    guasto("sitemap.xml", "check 12: sitemap assente")
else:
    nella_sitemap = set(re.findall(r"<loc>([^<]+)</loc>", leggi("sitemap.xml")))
    sul_disco = {url_di(n) for n in PAGINE}
    if nella_sitemap != sul_disco:
        guasto("sitemap.xml", "check 12: solo in sitemap %s; solo su disco %s"
               % (pulito(str(sorted(nella_sitemap - sul_disco))),
                  pulito(str(sorted(sul_disco - nella_sitemap)))))
rb = os.path.join(RADICE, "robots.txt")
if not os.path.exists(rb):
    guasto("robots.txt", "check 12: robots.txt assente")
elif ("Sitemap: " + BASE + "sitemap.xml") not in leggi("robots.txt"):
    guasto("robots.txt", "check 12: robots.txt non nomina la sitemap giusta")

# ---- 13. header e footer identici su tutte le pagine ----
firme = defaultdict(list)
for n in TUTTE:
    mnav = re.search(r'<nav class="site-nav".*?</nav>', SRC[n], re.S)
    # aria-current="page" marca la voce attiva e cambia per definizione da una
    # pagina all'altra: e' la cosa giusta da fare, non una difformita'.
    firma = re.sub(r'\s*aria-current="page"', "", mnav.group(0)) if mnav else None
    firme[firma].append(n)
if len(firme) > 1:
    guasto("chrome", "check 13: la navigazione non e' identica su tutte le pagine: %s"
           % pulito(str({k is not None: v for k, v in firme.items()})))

# ---- 14. impronte di cache allineate al contenuto ----
for asset in ("assets/css/style.css", "assets/js/main.js"):
    import hashlib
    with io.open(os.path.join(RADICE, asset), "rb") as f:
        imp = hashlib.sha1(f.read()).hexdigest()[:8]
    for n in TUTTE:
        if asset in SRC[n] and ("%s?v=%s" % (asset, imp)) not in SRC[n]:
            guasto(n, "check 14: impronta vecchia per %s, esegui tools/versiona.py" % asset)

# ---- 15. viewport, theme-color, target=_blank sicuro ----
for n in TUTTE:
    if 'name="viewport"' not in SRC[n]:
        guasto(n, "check 15: viewport mancante")
    if 'name="theme-color"' not in SRC[n]:
        guasto(n, "check 15: theme-color mancante")
    for tag in re.findall(r'<a\s[^>]*target="_blank"[^>]*>', SRC[n]):
        if "noopener" not in tag:
            guasto(n, "check 15: target=_blank senza rel=noopener: %s" % pulito(tag[:80]))

# ---- esito ----
print("  host        %s" % pulito(BASE))
print("  pagine      %d indicizzabili + 404" % len(PAGINE))
print("  Product     %d" % prodotti)
print("  @id         %d definiti, %d citati" % (len(definiti), len(citati)))
for a in avvisi:
    print("  avviso: %s" % pulito(a))
if problemi:
    print("\n  %d PROBLEMA/I:" % len(problemi))
    for p in problemi:
        print("   - %s" % pulito(p))
    sys.exit(1)
print("\n  tutto a posto")
