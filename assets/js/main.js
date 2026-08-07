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
     Qui ogni rifiuto fa comparire un vero pulsante di avvio, e con
     reduced-motion il video non parte da solo ma resta avviabile a mano. */
  document.querySelectorAll("[data-video]").forEach(function (fig) {
    var loop = fig.querySelector("video[data-loop]");
    var full = fig.querySelector("video[data-full]");
    var btn = fig.querySelector("[data-play]");
    var fullTrigger = fig.querySelector("[data-full-trigger]");
    if (!btn) return;

    // il video attualmente in scena (il loop, oppure l'integrale se richiesto)
    var current = loop;

    function showBtn() {
      btn.hidden = false;
    }
    function hideBtn() {
      btn.hidden = true;
    }

    function attempt(v, gesture) {
      if (!v) return;
      // Safari controlla la proprieta muted al momento del play, non l'attributo
      if (v.hasAttribute("data-loop")) v.muted = true;
      var p = v.play();
      if (!p || !p.then) return;
      p.then(hideBtn).catch(function () {
        // niente autoplay: diamo all'utente un modo per avviarlo davvero.
        // Nessun `controls` qui: attivarlo mentre duration e ancora NaN fa
        // lanciare a Safari 26 un RangeError dentro i suoi media controls,
        // che abbandona il layout e puo far cadere nel vuoto il primo tap.
        showBtn();
      });
    }

    btn.addEventListener("click", function () {
      attempt(current, true);
    });

    // I controlli nativi solo a riproduzione avviata E con duration nota:
    // se `controls` compare mentre duration e ancora NaN, Safari 26 lancia un
    // RangeError dentro i propri media controls e abbandona quel layout.
    fig.addEventListener("play", hideBtn, true);
    fig.addEventListener(
      "playing",
      function (e) {
        hideBtn();
        if (e.target === full && isFinite(full.duration)) full.controls = true;
      },
      true
    );

    if (full && fullTrigger) {
      fullTrigger.addEventListener("click", function () {
        if (loop) {
          loop.pause();
          loop.hidden = true;
        }
        full.hidden = false;
        current = full;
        fullTrigger.parentNode.hidden = true;
        attempt(full, true); // i controlli arrivano su "playing", vedi sopra
      });
    }

    if (!loop) return;

    if (reduce) {
      showBtn(); // nessun autoplay, ma resta guardabile
      return;
    }

    // l'attributo autoplay non e nel markup di proposito: la scelta deve passare
    // di qui, altrimenti il browser parte comunque anche con reduced-motion
    loop.autoplay = true;

    if ("IntersectionObserver" in window) {
      new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.target !== current) return;
            if (entry.isIntersecting) attempt(entry.target, false);
            else entry.target.pause();
          });
        },
        { threshold: 0.25 }
      ).observe(loop);
    } else {
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
