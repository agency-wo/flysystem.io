# flysystem.io · Fly System Srls

Sito vetrina di Fly System Srls: **produzione italiana** di porte, serramenti, pavimenti e sistemi outdoor, in Italia e nel mondo. Linguaggio "quiet luxury" su riferimento RODA / Cassina / Gamma / Talenti: grigi freddi, blu Fly System (dal logo), fotografia protagonista. HTML/CSS/JS puro, nessun framework, nessun processo di build, zero richieste esterne.

## Struttura

```
index.html            Home (hero, Bolla, indice prodotti, Porte, Outdoor/Pergole con video, chi siamo, professionisti, teaser cataloghi)
bolla.html            Bolla: collezione Bolle Luxury 2026 (Ristorazione + Glamping, dati reali, gallery, video drone)
cataloghi.html        Libreria: 16 cataloghi PDF in 6 capitoli con Sfoglia/Scarica
contatti.html         Recapiti, modulo di contatto, FAQ
404.html              Pagina non trovata
assets/
  css/style.css       Design system completo (@layer tokens/base/components/pages)
  js/main.js          Solo progressive enhancement (menu, reveal, video loop in viewport, form): il sito funziona senza JS
  fonts/              Switzer (woff2, self-hosted, licenza Fontshare)
  img/                Immagini AVIF/WebP/JPEG responsive estratte dai cataloghi + foto reali + logo
  pdf/                16 cataloghi ufficiali (fly-system-*.pdf)
  video/              pergole-loop.mp4 (loop muto, gated da JS) + pergole-promo.mp4 (tap-to-play)
tools/                Script di sviluppo (non pubblicare): estrazione PDF, rebranding PDF, encoder immagini/video, screenshot QA
_sorgenti/            Materiali sorgente del cliente (in .gitignore, mai pubblicati)
```

## Brand

- Palette: grigi freddi con il blu del logo come unico accento. Carta `#F1F2F3`, carta alternata `#E7E9EB`, inchiostro `#14171D`, testo secondario `#3D434E`, grigio `#5D6470`, blu `#304890`, blu chiaro `#9FB0DC`, acciaio `#7D8494`. Tutto parte dai token in cima a `style.css`.
- Logo 2026 (lockup orizzontale, derivato da `_sorgenti/alllogosflysystem.jpeg` con `tools/prep_logo2.py`): header, favicon e immagine OG. La variante con sponsorizzazione sportiva NON si usa sul sito.
- Tipografia: una sola famiglia, Switzer. Titoli grandi in Light (300) con tracciatura stretta, testo in Regular, micro-etichette maiuscole in Medium, corsivo per la parola in evidenza nei titoli.
- Regola tipografica fissa: mai em dash (né en dash). Separatori: punto mediano (·), due punti, virgole; trattino semplice per gli intervalli (REI 30-120).
- White label: mai nominare i produttori o le società del gruppo. I due cataloghi ceramica sono già rebrandizzati Fly System via `tools/rebrand_pdf.py` (job in `tools/rebrand_jobs/`); verificare ogni nuova estrazione con l'audit (`python tools/rebrand_pdf.py audit <pdf>`).

## Anteprima locale

```
npx serve .
```

> Serve un server che supporti le richieste HTTP Range. **`python -m http.server` non le supporta**
> (risponde 200 con tutto il file e senza `Accept-Ranges`) e con quello **i video non partono su
> Safari**, pur funzionando su Chrome. Se un video sembra rotto, prima di indagare sul file
> verificare con che server lo si sta guardando. In produzione Cloudflare Pages risponde 206 correttamente.

## Da sapere

- **Modulo contatti**: `action` punta a `https://formsubmit.co/info@flysystemrn.it`. Al primo invio FormSubmit manda una mail di conferma da approvare. In alternativa sostituire l'endpoint (Formspree, PHP dell'hosting): è un solo attributo in `contatti.html`.
- **Video**: il loop pergole in home parte solo in viewport e mai con `prefers-reduced-motion` (gestito in main.js via `video[data-loop]`); il promo pergole è `preload="none"` + poster, scarica solo al tap.
- **Passata white label del 2026-09-03**: i marchi dei fornitori sono stati tolti da porte-tagliafuoco (29 pagine), porte-rei (6), collezione-2025 (copertina) e dal nuovo porte-ei (10 pagine), e il logo Fly System vecchio e' stato sostituito su controtelai-tecnico. Le regole stanno in `tools/rebrand_jobs/`, i rettangoli sono stati misurati con `tools/misura_marchio.py` perche' questi PDF non hanno livello di testo e `rebrand_pdf.py audit` su di loro risponde sempre zero. **Restano due cose fuori, per scelta**: il nome stampato sul ventaglio colori fotografato di porte-ei p29, che in diagonale su un oggetto in ombra non si copre senza fare peggio del problema; e `fly-system-pedana-termica.pdf`, che non e' un catalogo Fly System con sopra un logo altrui ma il prodotto di un'altra azienda, nominato nei titoli e in ogni paragrafo, quindi non si rimarchia coprendo: o si tiene, o si toglie dalla libreria, o si chiede al fornitore una versione neutra.
- **Cataloghi porte in arrivo**: il cliente inviera' nuove edizioni; sostituire il file in `assets/pdf/` mantenendo lo stesso nome, aggiornare pagine/MB sulla card e rigenerare la copertina con `tools/make_covers.py` (che pero' fa solo 480 e 960: la 1440 che ogni srcset cita non ha generatore).
- **Deploy**: Cloudflare Pages, progetto `flysystem`. **Non e collegato a git**
  (`Git Provider: No` in `wrangler pages project list`): fare push su GitHub **non pubblica
  niente**. Si pubblica cosi, e solo cosi:

  ```bash
  python tools/pubblica.py            # costruisce _dist/ e dice cosa contiene
  python tools/pubblica.py --deploy   # costruisce e pubblica
  ```

  **Le credenziali non sono il login di wrangler.** Quel login e' uno solo per tutta la
  macchina e si sposta fra aziende: il 2026-11-13 un altro progetto lo aveva spostato su un
  altro account e il deploy falliva con `Authentication error [code: 10000]` pur avendo un
  token valido, perche' quel token non vedeva questo progetto. Adesso servono un token API
  con permesso Pages:Edit e l'id dell'account, in `_private/cloudflare.json`, che e' ignorato
  da git e che `pubblica.py` non copia mai. Se manca, `--deploy` si rifiuta **prima** di
  caricare qualcosa e stampa come crearlo. Il modulo e' `tools/credenziali.py`, e non stampa
  mai il valore del token.

  **Non usare `wrangler pages deploy .` dalla radice.** Quel comando carica tutta la cartella,
  e su Pages `.assetsignore` **non viene letto** (e una funzione dei Workers static assets:
  verificato nel codice di wrangler, dove la lista di esclusione di Pages e fissa e non
  comprende quel file). Dalla radice finirebbero online `_sorgenti/`, cioe le fotografie
  originali del cliente e i PDF che portano nel nome le societa del gruppo, piu `tools/` e
  `README.md`. Oggi sembra andar bene solo perche il limite di 25 MiB per file fa abortire il
  deploy: su un clone pulito quei file non esistono, il limite non scatta e la pubblicazione
  riesce, in silenzio.

  `tools/pubblica.py` lavora con una lista di cose **ammesse**, non di cose escluse: se
  dimentichi una riga manca una pagina e te ne accorgi subito, invece di pubblicare per errore.
  Dopo ogni pubblicazione verificare che `_sorgenti/bobo.jpeg`, `tools/enhance.py` e
  `README.md` rispondano 404.
- **Header/footer**: duplicati nelle 5 pagine, marcati `<!-- shared: ... keep in sync -->`. Modificarli ovunque insieme.
- **Cache e impronte**: `style.css` e `main.js` sono citati con `?v=<8 cifre>`, l'impronta del contenuto. Serve perche la CSS viaggia con `Cache-Control: max-age=14400` (4 ore) e senza impronta una modifica resta invisibile ai visitatori per tutto quel tempo. **Dopo ogni modifica a CSS o JS: `python tools/versiona.py`.** Con `--check` esce con 1 se un'impronta e vecchia, e `--hook` installa un pre-commit che fa quel controllo da solo. I font non si versionano di proposito: li cita anche `@font-face`, e versionarne uno solo dei due li farebbe scaricare due volte.

## Ingrandimento delle fotografie

Quasi tutte le fotografie del sito nascono piccole: gli scatti del cliente sono da telefono
(1040-1600 px) e il catalogo Bolla ha raster incorporati da 344-691 px. Vengono ingrandite in
locale con **Real-ESRGAN**, sulla GPU, senza caricare niente su servizi esterni.

Il binario e i modelli stanno in `tools/bin/` e **non sono nel repo** (43 MB). Per rimetterli:

```bash
curl -L -o rev.zip https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip
# estrarre in tools/bin/ ; serve anche realesrnet-x4plus, che sta solo nel pacchetto vecchio:
curl -L -o old.zip https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.3.0/realesrgan-ncnn-vulkan-20211212-windows.zip
# da old.zip copiare models/realesrnet-x4plus.{bin,param} in tools/bin/models/
```

Due modelli, e la scelta non e stilistica:

- **`realesrgan-x4plus`** (generativo) per cupole, pergole, architettura: li la texture
  ricostruita e erba, cielo e vetro, non una specifica di prodotto.
- **`realesrnet-x4plus`** (fedele, senza perdita GAN) per porte, gres e copertine, dove **la
  finitura E il prodotto**. Verificato sui provini: su una porta laccata i due modelli danno
  lo stesso risultato, e sul pavimento in gres il generativo **leviga la venatura del marmo**
  mentre il fedele la conserva. Qui il fedele non e una rinuncia, e la scelta migliore.

```bash
python tools/enhance.py --tutto            # tutta la tabella JOBS
python tools/enhance.py --tutto bolla/     # solo un ramo
python tools/sync_srcset.py --pulisci      # allinea le srcset ai file su disco
node tools/nitidezza.mjs                   # gate: nessuna immagine sotto-risoluta
```

**Si parte sempre dal raster originale**, non da cio che gia serviamo: `enhance.py` estrae
l'immagine incorporata nel PDF (`pdf:<catalogo>:<xref>`), cosi il modello lavora su pixel veri
e non sopra un nostro ingrandimento. Il ritaglio viene ritrovato da solo confrontando con
l'immagine attuale, quindi l'inquadratura approvata non cambia.

**Dopo ogni ingrandimento va riguardato il provino**: alzando la risoluzione possono diventare
leggibili insegne e marchi di altre aziende che prima non lo erano.

## SEO e dati strutturati

Ogni pagina porta un blocco `application/ld+json` con un `@graph`. La scheda dell'azienda e
definita una volta sola, con `@id` `<base>#business`, e tutto il resto la cita per riferimento:
cosi non puo' nascere il caso di un `@id` citato e mai definito.

| Pagina | Nodi |
|---|---|
| `index.html` | `LocalBusiness` |
| `bolla.html` | `LocalBusiness`, `BreadcrumbList`, `ItemList` con i **7 modelli** come `Product` |
| `cataloghi.html` | `LocalBusiness`, `BreadcrumbList` |
| `contatti.html` | `LocalBusiness`, `BreadcrumbList`, `ContactPage` |

I `Product` dei modelli Bolla sono generati leggendo `bolla.html`, non trascritti a mano: nome,
descrizione, foto e le voci del `<dl>` (Diametro, Superficie, Coperti/Ospiti) diventano
`additionalProperty`. Se un modello cambia in pagina, il JSON-LD va rigenerato perche' non si
disallinei. **Nessun `Offer`**: sul sito non compare un prezzo, quindi non se ne dichiara uno.
Fuori anche `geo`, `openingHours` e `vatID`, che sono fra i dati ancora in attesa qui sotto.

`sitemap.xml` elenca le 4 pagine indicizzabili (`404.html` resta fuori, ha gia' `noindex`).
`robots.txt` sta alla radice del dominio e indica la sitemap.

## Dove vive il sito

Il sito risponde da `https://flysystem.io/`, servito dal progetto Cloudflare Pages `flysystem`
(sopra, "Deploy"). Canonical, `og:url`, ogni URL assoluto nei dati strutturati, la sitemap e la riga
`Sitemap:` di robots.txt puntano tutti li'. GitHub Pages e' spento su questo repository: il
repository non pubblica nulla da solo.

**Resta sul dominio del cliente.** Spostarlo su un sottodominio o in una sottocartella del sito
dell'agenzia trasformerebbe il credito nel footer in un link interno, e porterebbe le pagine del
cliente dentro l'albero degli indirizzi e la sitemap dell'agenzia.

### Se un giorno il dominio cambia

Canonical, `og:url`, ogni URL assoluto nei dati strutturati, la sitemap e la riga `Sitemap:` di
robots.txt usano la stessa identica stringa, in ogni file. `tools/rebase.py` la cambia
tutta insieme e si rifiuta di lasciare il lavoro a meta':

```bash
python tools/rebase.py https://nuovo-dominio.it/
python tools/verify.py          # sitemap, canonical e JSON-LD devono ancora concordare
```

L'indirizzo di partenza non e' scritto nello script: lo legge dalla canonical di `index.html`.
`python tools/rebase.py --check` dice se le pagine hanno smesso di concordare. Il cambio va fatto
solo quando il nuovo dominio serve davvero questo sito: una canonical che punta a un indirizzo che
risponde con altro dice a Google di preferire quell'altro.

`tools/` e `_sorgenti/` non si pubblicano mai: `tools/pubblica.py` copia solo un elenco chiuso di
file e si ferma se uno dei due finisse nella cartella di pubblicazione.

## Controlli

```bash
python tools/verify.py      # 15 controlli: SEO, dati strutturati, immagini, coerenza
python tools/rebase.py --check
python tools/versiona.py --check
python tools/linkcheck.py
node tools/shot.mjs index.html out.png 390 844   # riporta gli sforamenti orizzontali
```

`verify.py` controlla un solo `h1`, lunghezza e unicita' di title e description, canonical, Open Graph,
JSON-LD (parsing, `LocalBusiness`, `BreadcrumbList`, `Product`, **nessun `@id` citato e mai definito**),
`alt`/`width`/`height` sulle immagini, link e risorse esistenti, nessuna risorsa di terze parti, NAP
identico ovunque, sitemap uguale alle pagine, navigazione identica fra le pagine, impronte di cache
allineate. **I percorsi devono restare relativi** (lo controlla `verify.py`): cosi' le pagine
funzionano uguali da qualunque cartella o anteprima.

## Dati in attesa di conferma (placeholder nel sito)

1. P.IVA per il footer legale
2. Orari di apertura / showroom (Contatti)
3. Numero mobile: il sito usa 380 897 2795 (catalogo 2026); il flyer 2025 riporta 327 4679241
4. Testo privacy/cookie (il sito non usa cookie)
5. Nome della serie ceramica rinominata nel catalogo gres (proposta: MATERIA) e titoli card ("Collezione Gres 2026", "Gres e SPC · Edition Two")
6. File vettoriale del logo, se disponibile
