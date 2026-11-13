/* COSMOS-AI website: starfield backdrop and mobile navigation. No dependencies, no network calls. */
(function () {
  "use strict";

  /* ---- mobile nav ---------------------------------------------------- */
  var toggle = document.querySelector(".nav-toggle");
  var links = document.querySelector(".nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", function () {
      var open = links.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    links.addEventListener("click", function (e) {
      if (e.target.tagName === "A") {
        links.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* ---- starfield ------------------------------------------------------
     Decorative only: a static field of dim points with a slow parallax drift,
     drawn once per resize and translated on scroll. Honours reduced-motion. */
  var canvas = document.getElementById("stars");
  if (!canvas || !canvas.getContext) return;
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var ctx = canvas.getContext("2d");
  var dpr = Math.min(window.devicePixelRatio || 1, 2);
  var stars = [];

  function seed(w, h) {
    var n = Math.min(260, Math.round((w * h) / 9000));
    stars = [];
    for (var i = 0; i < n; i++) {
      stars.push({
        x: Math.random() * w,
        y: Math.random() * h * 1.5,
        r: Math.random() * 1.1 + 0.25,
        a: Math.random() * 0.5 + 0.16,
        d: Math.random() * 0.5 + 0.25          // parallax depth
      });
    }
  }

  function resize() {
    var w = window.innerWidth, h = window.innerHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    seed(w, h);
    draw();
  }

  function draw() {
    var w = window.innerWidth, h = window.innerHeight;
    var off = reduce ? 0 : (window.scrollY || 0);
    ctx.clearRect(0, 0, w, h);

    // faint horizon glow, anchored to the top-right like the reference imagery
    var g = ctx.createRadialGradient(w * 0.82, h * 0.08, 0, w * 0.82, h * 0.08, Math.max(w, h) * 0.85);
    g.addColorStop(0, "rgba(40, 96, 170, 0.22)");
    g.addColorStop(0.45, "rgba(18, 38, 78, 0.10)");
    g.addColorStop(1, "rgba(5, 8, 15, 0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);

    for (var i = 0; i < stars.length; i++) {
      var s = stars[i];
      var y = s.y - off * s.d * 0.25;
      y = ((y % (h * 1.5)) + h * 1.5) % (h * 1.5);
      if (y > h + 2) continue;
      ctx.globalAlpha = s.a;
      ctx.fillStyle = "#cfe2ff";
      ctx.beginPath();
      ctx.arc(s.x, y, s.r, 0, 6.2832);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  var ticking = false;
  function onScroll() {
    if (reduce || ticking) return;
    ticking = true;
    window.requestAnimationFrame(function () { draw(); ticking = false; });
  }

  var rt;
  window.addEventListener("resize", function () {
    clearTimeout(rt);
    rt = setTimeout(resize, 150);
  });
  window.addEventListener("scroll", onScroll, { passive: true });
  resize();
})();
