/* FLY SYSTEM · main.js
   Progressive enhancement only: il sito funziona interamente senza JS. */
(function () {
  "use strict";

  document.documentElement.classList.add("js");

  /* ---- Header: stato scrolled ---- */
  var head = document.querySelector(".site-head");
  if (head) {
    var onScroll = function () {
      head.classList.toggle("is-scrolled", window.scrollY > 8);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  /* ---- Menu mobile: apertura, focus trap, Esc ---- */
  var menu = document.getElementById("menu");
  var openBtn = document.querySelector(".nav-toggle");
  var closeBtn = menu && menu.querySelector(".menu__close");
  var lastFocus = null;

  function menuItems() {
    return menu.querySelectorAll("a, button");
  }

  function openMenu() {
    lastFocus = document.activeElement;
    menu.classList.add("is-open");
    openBtn.setAttribute("aria-expanded", "true");
    document.body.style.overflow = "hidden";
    menu.querySelectorAll("nav a").forEach(function (a, i) {
      a.style.setProperty("--i", i);
    });
    closeBtn.focus();
  }

  function closeMenu() {
    menu.classList.remove("is-open");
    openBtn.setAttribute("aria-expanded", "false");
    document.body.style.overflow = "";
    if (lastFocus) lastFocus.focus();
  }

  if (menu && openBtn && closeBtn) {
    openBtn.addEventListener("click", openMenu);
    closeBtn.addEventListener("click", closeMenu);
    menu.addEventListener("click", function (e) {
      if (e.target.closest("a")) closeMenu();
    });
    document.addEventListener("keydown", function (e) {
      if (!menu.classList.contains("is-open")) return;
      if (e.key === "Escape") {
        closeMenu();
        return;
      }
      if (e.key !== "Tab") return;
      var items = menuItems();
      var first = items[0];
      var last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    });
  }

  /* ---- Reveal on scroll ---- */
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var revealed = document.querySelectorAll(".rv, .rv-rule, .rv-img");
  if (!reduce && "IntersectionObserver" in window && revealed.length) {
    document.querySelectorAll("[data-rv-group]").forEach(function (group) {
      var kids = group.querySelectorAll(".rv");
      kids.forEach(function (el, i) {
        el.style.setProperty("--i", i);
      });
    });
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("in");
            io.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.05 }
    );
    revealed.forEach(function (el) {
      io.observe(el);
    });
  } else {
    revealed.forEach(function (el) {
      el.classList.add("in");
    });
  }

  /* ---- Video ----------------------------------------------------------
     Safari nega l'autoplay in parecchi stati comuni (risparmio energetico,
     riduci movimento, anteprime video disattivate). Prima il rifiuto veniva
     inghiottito da un catch vuoto e restava un poster morto, non avviabile.
     Qui ogni rifiuto vero fa comparire un pulsante di avvio, e con
     reduced-motion il video non parte da solo ma resta avviabile a mano. */
  document.querySelectorAll("[data-video]").forEach(function (fig) {
    var loop = fig.querySelector("video[data-loop]");
    var full = fig.querySelector("video[data-full]");
    var btn = fig.querySelector("[data-play]");
    var fullTrigger = fig.querySelector("[data-full-trigger]");
    if (!btn) return;

    // il video attualmente in scena (il loop, oppure l'integrale se richiesto)
    var current = loop;

    function showBtn() { btn.hidden = false; }
    function hideBtn() { btn.hidden = true; }

    // stato di attesa: lo mettiamo sul contenitore, ci pensa il CSS a mostrarlo
    function loading(on) {
      fig.classList.toggle("is-video-loading", !!on);
      fig.setAttribute("aria-busy", on ? "true" : "false");
    }

    // Scalda il buffer. Con preload="metadata" Safari prende i metadati e poi
    // sospende: il primo dato utile lo chiede solo al play(), e il poster resta
    // fermo per tutto il tempo di rete. Alzare preload ad "auto" fa ripartire il
    // caricamento senza toccare quello gia in corso. load() solo se non c'e
    // proprio nulla in volo, altrimenti azzererebbe il buffer invece di ampliarlo.
    function warm(v) {
      if (!v) return;
      v.preload = "auto";
      if (v.readyState === v.HAVE_NOTHING && v.networkState !== v.NETWORK_LOADING) v.load();
    }

    function attempt(v, gesture) {
      if (!v) return;
      // Safari controlla la proprieta muted al momento del play, non l'attributo
      if (v.hasAttribute("data-loop")) v.muted = true;
      // l'integrale pesa: se non e pronto, l'attesa va dichiarata subito
      if (v === full && v.readyState < v.HAVE_FUTURE_DATA) loading(true);
      var p = v.play();
      if (!p || !p.then) return;
      p.then(hideBtn).catch(function (err) {
        loading(false);
        // AbortError non e un rifiuto del browser: e la nostra pause() (uscita
        // dalla vista, o passaggio all'integrale) che ha interrotto un play()
        // ancora in attesa di dati. Mostrare il pulsante qui significa piazzare
        // un overlay sopra un video che sta funzionando.
        if (err && err.name === "AbortError") return;
        // niente autoplay: diamo all'utente un modo per avviarlo davvero.
        // Nessun `controls` qui: attivarlo mentre duration e ancora NaN fa
        // lanciare a Safari 26 un RangeError dentro i suoi media controls,
        // che abbandona il layout e puo far cadere nel vuoto il primo tap.
        showBtn();
      });
    }

    btn.addEventListener("click", function () { attempt(current, true); });

    // I controlli nativi solo a riproduzione avviata E con duration nota:
    // se `controls` compare mentre duration e ancora NaN, Safari 26 lancia un
    // RangeError dentro i propri media controls e abbandona quel layout.
    fig.addEventListener("play", hideBtn, true);
    fig.addEventListener(
      "playing",
      function (e) {
        hideBtn();
        loading(false);
        if (e.target === full && isFinite(full.duration)) full.controls = true;
      },
      true
    );
    // Solo sull'integrale: sul loop uno spinner a ogni scroll sarebbe rumore.
    fig.addEventListener(
      "waiting",
      function (e) { if (e.target === full && e.target === current) loading(true); },
      true
    );
    fig.addEventListener(
      "error",
      function (e) {
        if (e.target !== current) return;
        loading(false);
        showBtn(); // il file non arriva: almeno resta un comando per riprovare
      },
      true
    );

    if (full && fullTrigger) {
      // pointerdown arriva prima del click: gli 8 MB iniziano a scendere li
      fullTrigger.addEventListener("pointerdown", function () { warm(full); });
      fullTrigger.addEventListener("click", function () {
        if (loop) {
          loop.pause();
          loop.hidden = true;
        }
        full.hidden = false;
        current = full;
        fullTrigger.parentNode.hidden = true;
        loading(true); // il tap deve avere una risposta subito, non fra due secondi
        attempt(full, true); // i controlli arrivano su "playing", vedi sopra
      });
    }

    if (!loop) return;

    if (reduce) {
      showBtn(); // nessun autoplay, ma resta guardabile
      return;
    }

    if ("IntersectionObserver" in window) {
      // Due osservatori distinti. Il primo scalda molto prima che il video
      // arrivi in scena; il secondo avvia appena si vede il primo pixel.
      // Con un solo osservatore al 25% il poster restava fermo per tutta la
      // distanza fra il bordo e un quarto di video: qui misurati ~200 ms.
      new IntersectionObserver(
        function (entries, obs) {
          entries.forEach(function (entry) {
            if (!entry.isIntersecting) return;
            warm(entry.target);
            obs.unobserve(entry.target);
          });
        },
        { rootMargin: "200% 0px" }
      ).observe(loop);

      // Nota: niente `loop.autoplay = true`. Era inerte, perche la prima
      // notifica dell'osservatore chiamava pause() e la specifica azzera li il
      // can-autoplay flag. Ora la pausa scatta solo se il video sta davvero
      // andando, quindi rimetterlo lo farebbe partire fuori campo.
      new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.target !== current) return;
            if (entry.isIntersecting) attempt(entry.target, false);
            else if (!entry.target.paused) entry.target.pause();
          });
        },
        { threshold: 0 }
      ).observe(loop);
    } else {
      warm(loop);
      attempt(loop, false);
    }
  });

  /* ---- Form: validazione + preselezione ?oggetto= ---- */
  var form = document.querySelector("form[data-validate]");
  if (form) {
    form.addEventListener(
      "submit",
      function (e) {
        if (!form.checkValidity()) {
          e.preventDefault();
          form.classList.add("was-validated");
          var bad = form.querySelector(":invalid");
          if (bad) bad.focus();
        }
      },
      false
    );

    var oggetto = new URLSearchParams(window.location.search).get("oggetto");
    var select = form.querySelector("select[name='oggetto']");
    if (oggetto && select) {
      var opt = Array.prototype.find.call(select.options, function (o) {
        return o.value === oggetto;
      });
      if (opt) select.value = oggetto;
    }
  }
})();
