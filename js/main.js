const root = document.documentElement;
const motion = root.classList.contains("motion") && window.gsap && window.ScrollTrigger;
if (!motion) root.classList.remove("motion");
const finePointer = matchMedia("(pointer: fine)").matches;
const ease = "power3.out";

// ---------------------------------------------------------------- smooth scroll
let lenis = null;
if (motion) {
  gsap.registerPlugin(ScrollTrigger);
  if (window.Lenis) {
    lenis = new Lenis({ lerp: 0.085, smoothWheel: true });
    lenis.on("scroll", ScrollTrigger.update);
    gsap.ticker.add((t) => lenis.raf(t * 1000));
    gsap.ticker.lagSmoothing(0);
    document.querySelectorAll('a[href^="#"], a[href$="#work"]').forEach((a) => a.addEventListener("click", (e) => {
      const url = new URL(a.href, location.href);
      const target = url.pathname === location.pathname && url.hash && document.querySelector(url.hash);
      if (target) { e.preventDefault(); e.stopPropagation(); lenis.scrollTo(target, { offset: -40, duration: 1.6 }); }
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

function openBox(el) {
  box.hidden = false;
  document.body.style.overflow = "hidden";
  lenis?.stop();
  if (motion) {
    gsap.fromTo(box, { opacity: 0 }, { opacity: 1, duration: .35 });
    gsap.fromTo(el, { scale: .92, opacity: 0, y: 20 }, { scale: 1, opacity: 1, y: 0, duration: .7, ease: "expo.out" });
  }
}
function show(i, dir = 0) {
  index = (i + links.length) % links.length;
  boxImg.hidden = false;
  boxImg.src = links[index].href;
  boxImg.alt = links[index].querySelector("img")?.alt || "";
  if (box.hidden) openBox(boxImg);
  else if (motion) gsap.fromTo(boxImg, { x: dir * 60, opacity: 0 }, { x: 0, opacity: 1, duration: .5, ease });
}
function close() {
  const done = () => {
    box.hidden = true;
    boxImg.removeAttribute("src");
    if (boxVideo) { boxVideo.remove(); boxVideo = null; }
    document.body.style.overflow = "";
    lenis?.start();
  };
  if (motion) gsap.to(box, { opacity: 0, duration: .3, onComplete: done });
  else done();
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
  openBox(boxVideo);
}));
box.querySelector(".lb-close").addEventListener("click", close);
box.querySelector(".lb-prev").addEventListener("click", () => show(index - 1, -1));
box.querySelector(".lb-next").addEventListener("click", () => show(index + 1, 1));
box.addEventListener("click", (e) => { if (e.target === box) close(); });
document.addEventListener("keydown", (e) => {
  if (box.hidden) return;
  if (e.key === "Escape") close();
  if (!boxVideo && e.key === "ArrowLeft") show(index - 1, -1);
  if (!boxVideo && e.key === "ArrowRight") show(index + 1, 1);
});

// ---------------------------------------------------------------- header + progress
const header = document.querySelector(".site-header");
const progress = document.createElement("div");
progress.className = "progress";
document.body.append(progress);
let lastY = 0;
function onScroll(y) {
  header.classList.toggle("is-hidden", y > lastY && y > 200);
  lastY = y;
  const max = document.documentElement.scrollHeight - innerHeight;
  progress.style.transform = `scaleX(${max > 0 ? y / max : 0})`;
}
if (lenis) lenis.on("scroll", ({ scroll }) => onScroll(scroll));
else addEventListener("scroll", () => onScroll(scrollY), { passive: true });

// ---------------------------------------------------------------- page transitions
const veil = document.querySelector(".veil");
function isPageLink(a, e) {
  if (!a || e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || e.button || a.target === "_blank") return false;
  if (a.hasAttribute("data-lightbox") || a.hasAttribute("data-lightbox-video")) return false;
  const url = new URL(a.href, location.href);
  return url.origin === location.origin && url.pathname !== location.pathname && /(\.html|\/)$/.test(url.pathname);
}
if (motion) {
  gsap.to(veil, { opacity: 0, duration: .7, ease: "power2.out", delay: .05 });
  addEventListener("pageshow", (e) => { if (e.persisted) { gsap.set(veil, { opacity: 0 }); document.querySelector(".zoom-clone")?.remove(); } });
  document.addEventListener("click", (e) => {
    const a = e.target.closest("a[href]");
    if (!isPageLink(a, e)) return;
    e.preventDefault();
    const media = a.matches(".card") && a.querySelector(".card-media");
    if (media) {
      // the card's picture grows to fill the screen, then the project opens
      const r = media.getBoundingClientRect();
      const clone = document.createElement("div");
      clone.className = "zoom-clone";
      const src = media.querySelector("video, img").cloneNode(true);
      if (src.tagName === "VIDEO") { src.muted = true; src.currentTime = media.querySelector("video").currentTime; src.play?.().catch(() => {}); }
      clone.append(src);
      Object.assign(clone.style, { left: r.left + "px", top: r.top + "px", width: r.width + "px", height: r.height + "px" });
      document.body.append(clone);
      lenis?.stop();
      gsap.to(".card", { opacity: 0, duration: .4 });
      gsap.to(clone, { left: 0, top: 0, width: innerWidth, height: innerHeight, borderRadius: 0, duration: .9, ease: "expo.inOut",
        onComplete: () => { location.href = a.href; } });
    } else {
      gsap.to(veil, { opacity: 1, duration: .45, ease: "power2.in", onComplete: () => { location.href = a.href; } });
    }
  });
}

// ---------------------------------------------------------------- cursor + hover effects
if (motion && finePointer) {
  root.classList.add("has-cursor");
  const cursor = document.querySelector(".cursor");
  const parts = cursor.querySelectorAll(".cursor-ring, .cursor-label");
  const label = cursor.querySelector(".cursor-label");
  const xTo = gsap.quickTo(parts, "x", { duration: .5, ease: "power3" });
  const yTo = gsap.quickTo(parts, "y", { duration: .5, ease: "power3" });
  let seen = false;
  addEventListener("pointermove", (e) => {
    if (!seen) { seen = true; gsap.set(parts, { x: e.clientX, y: e.clientY }); gsap.to(cursor, { opacity: 1, duration: .3 }); }
    xTo(e.clientX); yTo(e.clientY);
  });
  document.addEventListener("pointerover", (e) => {
    const t = e.target.closest("[data-cursor], a, button");
    cursor.classList.toggle("is-label", !!t?.dataset.cursor);
    cursor.classList.toggle("is-link", !!t && !t.dataset.cursor);
    label.textContent = t?.dataset.cursor || "";
  });
  addEventListener("pointerdown", () => cursor.classList.add("is-down"));
  addEventListener("pointerup", () => cursor.classList.remove("is-down"));
  document.documentElement.addEventListener("pointerleave", () => gsap.to(cursor, { opacity: 0, duration: .3 }));
  document.documentElement.addEventListener("pointerenter", () => seen && gsap.to(cursor, { opacity: 1, duration: .3 }));

  // cards tilt toward the pointer and their picture zooms
  document.querySelectorAll(".card").forEach((card) => {
    const media = card.querySelector(".card-media");
    const inner = media.querySelector("img, video");
    gsap.set(media, { transformPerspective: 900 });
    const rx = gsap.quickTo(media, "rotationX", { duration: .6, ease: "power3" });
    const ry = gsap.quickTo(media, "rotationY", { duration: .6, ease: "power3" });
    card.addEventListener("pointermove", (e) => {
      const r = media.getBoundingClientRect();
      ry(((e.clientX - r.left) / r.width - .5) * 8);
      rx(-((e.clientY - r.top) / r.height - .5) * 8);
    });
    card.addEventListener("pointerenter", () => gsap.to(inner, { scale: 1.12, duration: 1, ease }));
    card.addEventListener("pointerleave", () => { rx(0); ry(0); gsap.to(inner, { scale: 1.04, duration: 1, ease }); });
  });

  // magnetic buttons and pager links
  document.querySelectorAll(".btn, .site-header nav a, .pager a, .social a").forEach((el) => {
    const mx = gsap.quickTo(el, "x", { duration: .7, ease: "elastic.out(1, .4)" });
    const my = gsap.quickTo(el, "y", { duration: .7, ease: "elastic.out(1, .4)" });
    el.addEventListener("pointermove", (e) => {
      const r = el.getBoundingClientRect();
      mx((e.clientX - r.left - r.width / 2) * .3);
      my((e.clientY - r.top - r.height / 2) * .4);
    });
    el.addEventListener("pointerleave", () => { mx(0); my(0); });
  });
}

// ---------------------------------------------------------------- scroll choreography
function split(el) {
  const text = el.textContent.trim();
  el.setAttribute("aria-label", text);
  el.innerHTML = text.split(/(\s+)/).map((w) => /^\s+$/.test(w) ? " "
    : `<span class="split-unit" aria-hidden="true">${[...w].map((c) => `<span>${c}</span>`).join("")}</span>`).join("");
  return el.querySelectorAll(".split-unit > span");
}

if (motion) {
  // headings: letters rise in
  document.querySelectorAll("[data-split]").forEach((el) => {
    gsap.to(split(el), { y: 0, duration: 1.1, ease: "power4.out", stagger: .03, delay: .25 });
  });

  // hero: video slowly zooms and text drifts away as you scroll
  const hero = document.querySelector(".hero");
  if (hero) {
    gsap.from(".hero-text .eyebrow, .hero-text > p:not(.eyebrow), .hero-text .btn", { y: 30, opacity: 0, duration: 1, ease, stagger: .12, delay: .7 });
    gsap.to(".hero video", { scale: 1.18, yPercent: 12, ease: "none", scrollTrigger: { trigger: hero, start: "top top", end: "bottom top", scrub: true } });
    gsap.to(".hero-text", { yPercent: -40, opacity: 0, ease: "none", scrollTrigger: { trigger: hero, start: "top top", end: "bottom 20%", scrub: true } });
  }

  // cards: curtain reveal, staggered by column, with inner parallax
  gsap.utils.toArray(".card").forEach((card, i) => {
    const media = card.querySelector(".card-media");
    const inner = media.querySelector("img, video");
    const info = card.querySelector(".card-info");
    const tl = gsap.timeline({ scrollTrigger: { trigger: card, start: "top 88%" } });
    tl.fromTo(media, { clipPath: "inset(100% 0% 0% 0%)" }, { clipPath: "inset(0% 0% 0% 0%)", duration: 1.2, ease: "expo.out", delay: (i % 2) * .12 })
      .fromTo(inner, { scale: 1.4 }, { scale: 1.04, duration: 1.6, ease: "expo.out" }, "<")
      .from(info.children, { y: 24, opacity: 0, duration: .8, ease, stagger: .07 }, "<.3");
    gsap.fromTo(inner, { yPercent: -5 }, { yPercent: 5, ease: "none",
      scrollTrigger: { trigger: card, start: "top bottom", end: "bottom top", scrub: true } });
  });

  // project pages: blocks fade up, images unmask, galleries cascade
  gsap.utils.toArray(".crumbs, .project .row, .project .banner, .project .icons, .pager, .site-footer > *").forEach((el) => {
    if (el.closest(".banner-over")) return;
    el.setAttribute("data-reveal", "");
    gsap.to(el, { opacity: 1, y: 0, duration: 1.1, ease, scrollTrigger: { trigger: el, start: "top 90%" } });
  });
  gsap.utils.toArray(".project .row .media:not(.icon)").forEach((m) => {
    const inner = m.querySelector("img") || m;
    gsap.fromTo(m, { clipPath: "inset(12% 8% 12% 8%)" }, { clipPath: "inset(0% 0% 0% 0%)", ease: "none",
      scrollTrigger: { trigger: m, start: "top 95%", end: "top 55%", scrub: true } });
    if (inner !== m) gsap.fromTo(inner, { scale: 1.15 }, { scale: 1, ease: "none",
      scrollTrigger: { trigger: m, start: "top 95%", end: "bottom 30%", scrub: true } });
  });
  gsap.utils.toArray(".gallery, .carousel").forEach((g) => {
    gsap.from(g.children, { y: 60, opacity: 0, scale: .94, duration: 1, ease, stagger: { each: .06, from: "start" },
      scrollTrigger: { trigger: g, start: "top 88%" } });
  });
  gsap.utils.toArray(".banner").forEach((b) => {
    const m = b.querySelector(":scope > video, :scope > .media img");
    if (m) gsap.fromTo(m, { scale: 1.2, yPercent: -6 }, { scale: 1.05, yPercent: 6, ease: "none",
      scrollTrigger: { trigger: b, start: "top bottom", end: "bottom top", scrub: true } });
    const over = b.querySelector(".banner-over");
    if (over) gsap.from(over.children, { y: 40, opacity: 0, duration: 1, ease, stagger: .1, scrollTrigger: { trigger: b, start: "top 70%" } });
  });

  // carousels also drift sideways with scroll
  gsap.utils.toArray(".carousel").forEach((c) => {
    gsap.fromTo(c, { x: 60 }, { x: -60, ease: "none", scrollTrigger: { trigger: c, start: "top bottom", end: "bottom top", scrub: true } });
  });

  addEventListener("load", () => ScrollTrigger.refresh());
}
