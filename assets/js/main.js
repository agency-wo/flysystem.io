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

  /* ---- Video loop: play solo in viewport, mai con reduced-motion ---- */
  var loops = document.querySelectorAll("video[data-loop]");
  if (loops.length && !reduce && "IntersectionObserver" in window) {
    var vio = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          var v = entry.target;
          if (entry.isIntersecting) {
            v.play().catch(function () {});
          } else {
            v.pause();
          }
        });
      },
      { threshold: 0.25 }
    );
    loops.forEach(function (v) {
      vio.observe(v);
    });
  }

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
