const root = document.documentElement;
const finePointer = matchMedia("(pointer: fine)").matches;
const motion = root.classList.contains("motion") && window.gsap && window.ScrollTrigger;
if (!motion) root.classList.remove("motion");

// ---------------------------------------------------------------- smooth scroll
let lenis = null;
if (motion) {
  gsap.registerPlugin(ScrollTrigger);
  if (window.Lenis) {
    lenis = new Lenis({ lerp: 0.09, smoothWheel: true });
    lenis.on("scroll", ScrollTrigger.update);
    gsap.ticker.add((t) => lenis.raf(t * 1000));
    gsap.ticker.lagSmoothing(0);
    document.querySelectorAll('a[href^="#"]').forEach((a) => a.addEventListener("click", (e) => {
      const target = document.querySelector(a.getAttribute("href"));
      if (target) { e.preventDefault(); lenis.scrollTo(target, { offset: -60, duration: 1.4 }); }
    }));
  }
}

// ---------------------------------------------------------------- ambient videos
// play only while on screen, to keep CPU and bandwidth low
const ambient = document.querySelectorAll("video[data-autoplay]");
const io = new IntersectionObserver((entries) => {
  for (const e of entries) {
    const v = e.target;
    if (e.isIntersecting) {
      if (v.preload === "none") v.preload = "auto";
      v.play().catch(() => {});
    } else {
      v.pause();
    }
  }
}, { rootMargin: "200px 0px" });
ambient.forEach((v) => io.observe(v));

// ---------------------------------------------------------------- lightbox
const box = document.querySelector(".lightbox");
const boxImg = box.querySelector("img");
const links = [...document.querySelectorAll("a[data-lightbox]")];
let index = -1;
let boxVideo = null;

function openBox() {
  box.hidden = false;
  document.body.style.overflow = "hidden";
  lenis?.stop();
}
function show(i) {
  index = (i + links.length) % links.length;
  boxImg.hidden = false;
  boxImg.src = links[index].href;
  boxImg.alt = links[index].querySelector("img")?.alt || "";
  openBox();
}
function close() {
  box.hidden = true;
  boxImg.removeAttribute("src");
  if (boxVideo) { boxVideo.remove(); boxVideo = null; }
  document.body.style.overflow = "";
  lenis?.start();
}
links.forEach((a, i) => a.addEventListener("click", (e) => { e.preventDefault(); show(i); }));
document.querySelectorAll("a[data-lightbox-video]").forEach((a) => a.addEventListener("click", (e) => {
  e.preventDefault();
  boxImg.hidden = true;
  boxVideo = document.createElement("video");
  boxVideo.src = a.href;
  boxVideo.controls = true;
  boxVideo.autoplay = true;
  boxVideo.playsInline = true;
  box.append(boxVideo);
  openBox();
}));
box.querySelector(".lb-close").addEventListener("click", close);
box.querySelector(".lb-prev").addEventListener("click", () => show(index - 1));
box.querySelector(".lb-next").addEventListener("click", () => show(index + 1));
box.addEventListener("click", (e) => { if (e.target === box) close(); });
document.addEventListener("keydown", (e) => {
  if (box.hidden) return;
  if (e.key === "Escape") close();
  if (!boxVideo && e.key === "ArrowLeft") show(index - 1);
  if (!boxVideo && e.key === "ArrowRight") show(index + 1);
});

// ---------------------------------------------------------------- header hide on scroll
const header = document.querySelector(".site-header");
let lastY = 0;
function onScroll(y) {
  header.classList.toggle("is-hidden", y > lastY && y > 160);
  lastY = y;
}
if (lenis) lenis.on("scroll", ({ scroll }) => onScroll(scroll));
else addEventListener("scroll", () => onScroll(scrollY), { passive: true });

// ---------------------------------------------------------------- custom cursor
if (finePointer && motion) {
  root.classList.add("has-cursor");
  const cursor = document.querySelector(".cursor");
  const dot = cursor.querySelector(".cursor-dot");
  const label = cursor.querySelector(".cursor-label");
  const xTo = gsap.quickTo([dot, label], "x", { duration: 0.45, ease: "power3" });
  const yTo = gsap.quickTo([dot, label], "y", { duration: 0.45, ease: "power3" });
  let seen = false;
  addEventListener("pointermove", (e) => {
    if (!seen) { seen = true; gsap.set([dot, label], { x: e.clientX, y: e.clientY }); gsap.to(cursor, { opacity: 1, duration: .3 }); }
    xTo(e.clientX); yTo(e.clientY);
  });
  document.addEventListener("pointerover", (e) => {
    const t = e.target.closest("[data-cursor], a, button");
    cursor.classList.toggle("is-label", !!t?.dataset.cursor);
    cursor.classList.toggle("is-link", !!t && !t.dataset.cursor);
    label.textContent = t?.dataset.cursor || "";
  });
  document.addEventListener("pointerleave", () => gsap.to(cursor, { opacity: 0, duration: .3 }));
  document.addEventListener("pointerenter", () => seen && gsap.to(cursor, { opacity: 1, duration: .3 }));

  // magnetic pills
  document.querySelectorAll(".pill, .btn").forEach((el) => {
    const mx = gsap.quickTo(el, "x", { duration: .6, ease: "elastic.out(1, .4)" });
    const my = gsap.quickTo(el, "y", { duration: .6, ease: "elastic.out(1, .4)" });
    el.addEventListener("pointermove", (e) => {
      const r = el.getBoundingClientRect();
      mx((e.clientX - r.left - r.width / 2) * .3);
      my((e.clientY - r.top - r.height / 2) * .4);
    });
    el.addEventListener("pointerleave", () => { mx(0); my(0); });
  });
}

// ---------------------------------------------------------------- page transitions
const veil = document.querySelector(".veil");
if (motion) {
  gsap.to(veil, { opacity: 0, duration: .8, ease: "power2.out", delay: .1 });
  document.addEventListener("click", (e) => {
    const a = e.target.closest("a[href]");
    if (!a || e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || a.target === "_blank") return;
    const url = new URL(a.href, location.href);
    if (url.origin !== location.origin || url.pathname === location.pathname || !/\.html$|\/$/.test(url.pathname)) return;
    e.preventDefault();
    gsap.to(veil, { opacity: 1, duration: .45, ease: "power2.in", onComplete: () => { location.href = a.href; } });
  });
  // back/forward cache restores the faded-out veil
  addEventListener("pageshow", (e) => { if (e.persisted) gsap.set(veil, { opacity: 0 }); });
}

// ---------------------------------------------------------------- reveals and scroll effects
function split(el, byWords) {
  const parts = byWords ? el.textContent.trim().split(/\s+/) : [...el.textContent];
  el.setAttribute("aria-label", el.textContent.trim());
  el.innerHTML = parts.map((p) => p === " "
    ? " "
    : `<span class="split-unit" aria-hidden="true"><span>${p}</span></span>`).join(byWords ? " " : "");
  return el.querySelectorAll(".split-unit > span");
}

if (motion) {
  // headings rise in word by word / letter by letter
  document.querySelectorAll("[data-split-words], [data-split]").forEach((el) => {
    const units = split(el, el.hasAttribute("data-split-words"));
    const inHero = el.closest(".hero, .page-hero, .project-head");
    gsap.to(units, {
      y: 0, duration: 1.1, ease: "power4.out", stagger: el.hasAttribute("data-split") ? .025 : .07,
      delay: inHero ? .35 : 0,
      scrollTrigger: inHero ? null : { trigger: el, start: "top 88%" },
    });
  });

  // generic reveal
  const revealSel = ".hero-actions, .eyebrow, .page-hero-text .btn, .crumbs, .card, .row, .gallery, .carousel, .banner, .pager, .section-head .count, .footer-card";
  gsap.utils.toArray(revealSel).forEach((el) => {
    el.setAttribute("data-reveal", "");
    const inHero = el.closest(".hero, .page-hero, .project-head");
    gsap.to(el, {
      opacity: 1, y: 0, duration: 1.2, ease: "power3.out", delay: inHero ? .6 : 0,
      scrollTrigger: inHero ? null : { trigger: el, start: "top 92%" },
    });
  });

  // cards: rounded curtain + inner parallax
  gsap.utils.toArray(".card-media").forEach((m) => {
    gsap.fromTo(m, { clipPath: "inset(18% 6% 0% 6% round 24px)" },
      { clipPath: "inset(0% 0% 0% 0% round 24px)", ease: "none",
        scrollTrigger: { trigger: m, start: "top 100%", end: "top 45%", scrub: true } });
    const inner = m.querySelector("img, video");
    gsap.fromTo(inner, { yPercent: -6, scale: 1.15 }, { yPercent: 6, scale: 1.15, ease: "none",
      scrollTrigger: { trigger: m, start: "top bottom", end: "bottom top", scrub: true } });
  });

  // project media parallax
  gsap.utils.toArray(".project .row .media:not(.icon) img, .banner > video, .banner > .media img").forEach((m) => {
    gsap.fromTo(m, { yPercent: -4, scale: 1.08 }, { yPercent: 4, scale: 1.08, ease: "none",
      scrollTrigger: { trigger: m.closest(".row, .banner"), start: "top bottom", end: "bottom top", scrub: true } });
  });

  // home hero: text drifts up and fades as you leave
  const heroText = document.querySelector(".hero-text");
  if (heroText) {
    gsap.to(heroText, { yPercent: -30, opacity: 0, ease: "none",
      scrollTrigger: { trigger: ".hero", start: "top top", end: "bottom top", scrub: true } });
  }

  // reel grows from a card into full width
  const reel = document.querySelector(".reel-frame");
  if (reel) {
    gsap.fromTo(reel, { scale: .62, borderRadius: 48 }, { scale: 1, borderRadius: 24, ease: "none",
      scrollTrigger: { trigger: ".reel", start: "top 95%", end: "center 55%", scrub: true } });
  }

  // page hero media zooms out as the page starts
  const pageHero = document.querySelector(".page-hero-media");
  if (pageHero) {
    gsap.fromTo(pageHero, { scale: .94, borderRadius: 48 }, { scale: 1, borderRadius: 24, duration: 1.4, ease: "power3.out", delay: .15 });
    const pm = pageHero.querySelector("img, video");
    gsap.to(pm, { yPercent: 12, ease: "none",
      scrollTrigger: { trigger: pageHero, start: "top top", end: "bottom top", scrub: true } });
  }

  // statement: words light up as you read
  const words = document.querySelectorAll(".statement span");
  if (words.length) {
    ScrollTrigger.create({
      trigger: ".statement", start: "top 75%", end: "bottom 45%", scrub: true,
      onUpdate: (st) => {
        const n = Math.round(st.progress * words.length);
        words.forEach((w, i) => w.classList.toggle("on", i < n));
      },
    });
  }

  addEventListener("load", () => ScrollTrigger.refresh());
}
