# flysystem.io · Fly System Srls

Sito vetrina di Fly System Srls: **produzione italiana** di porte, serramenti, pavimenti e sistemi outdoor, in Italia e nel mondo. Linguaggio "quiet luxury" su riferimento RODA / Cassina / Gamma / Talenti: grigi freddi, blu Fly System (dal logo), fotografia protagonista. HTML/CSS/JS puro, nessun framework, nessun processo di build, zero richieste esterne.

## Struttura

```
index.html            Home (hero, Bolla, indice prodotti, Porte, Outdoor/Pergole con video, chi siamo, professionisti, teaser cataloghi)
bolla.html            Bolla: collezione Bolle Luxury 2026 (Ristorazione + Glamping, dati reali, gallery, video drone)
cataloghi.html        Libreria: 14 cataloghi PDF in 6 capitoli con Sfoglia/Scarica
contatti.html         Recapiti, modulo di contatto, FAQ
404.html              Pagina non trovata
assets/
  css/style.css       Design system completo (@layer tokens/base/components/pages)
  js/main.js          Solo progressive enhancement (menu, reveal, video loop in viewport, form): il sito funziona senza JS
  fonts/              Switzer (woff2, self-hosted, licenza Fontshare)
  img/                Immagini AVIF/WebP/JPEG responsive estratte dai cataloghi + foto reali + logo
  pdf/                14 cataloghi ufficiali (fly-system-*.pdf)
  video/              bolla-drone.mp4 (loop muto, gated da JS) + pergole-promo.mp4 (tap-to-play)
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
> verificare con che server lo si sta guardando. In produzione GitHub Pages risponde 206 correttamente.

## Da sapere

- **Modulo contatti**: `action` punta a `https://formsubmit.co/info@flysystemrn.it`. Al primo invio FormSubmit manda una mail di conferma da approvare. In alternativa sostituire l'endpoint (Formspree, PHP dell'hosting): è un solo attributo in `contatti.html`.
- **Video**: il drone su bolla.html parte solo in viewport e mai con `prefers-reduced-motion` (gestito in main.js via `video[data-loop]`); il promo pergole è `preload="none"` + poster, scarica solo al tap.
- **Cataloghi porte in arrivo**: il cliente invierà nuove edizioni; sostituire il file in `assets/pdf/` mantenendo lo stesso nome, aggiornare pagine/MB sulla card e rigenerare la copertina con `tools/make_covers.py`.
- **Deploy**: GitHub Pages dal branch main (repo agency-wo/flysystem.io). Escludere `tools/` e `_sorgenti/` da altri hosting.
- **Header/footer**: duplicati nelle 5 pagine, marcati `<!-- shared: ... keep in sync -->`. Modificarli ovunque insieme.

## Dati in attesa di conferma (placeholder nel sito)

1. P.IVA per il footer legale
2. Orari di apertura / showroom (Contatti)
3. Numero mobile: il sito usa 380 897 2795 (catalogo 2026); il flyer 2025 riporta 327 4679241
4. Testo privacy/cookie (il sito non usa cookie)
5. Nome della serie ceramica rinominata nel catalogo gres (proposta: MATERIA) e titoli card ("Collezione Gres 2026", "Gres e SPC · Edition Two")
6. File vettoriale del logo, se disponibile
