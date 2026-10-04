const root = document.documentElement;
const motion = root.classList.contains("motion") && window.gsap && window.ScrollTrigger;
if (!motion) root.classList.remove("motion");
const ease = "power3.out";

// ---------------------------------------------------------------- smooth scroll
let lenis = null;
if (motion) {
  gsap.registerPlugin(ScrollTrigger);
  if (window.Lenis) {
    lenis = new Lenis({ lerp: 0.1, smoothWheel: true });
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

// ---------------------------------------------------------------- hero reel
// Cross-fade through the project clips; only the current and next clip load.
const reel = [...document.querySelectorAll(".hero-reel video")];
if (reel.length) {
  const now = document.querySelector(".hero-now");
  const nowTitle = now.querySelector(".hero-now-title");
  const SHOW = 7000;  // ms per clip
  let cur = 0, timer = null, inView = true;
  const label = (v) => { nowTitle.textContent = v.dataset.title; now.href = v.dataset.href; };
  const prep = (v) => { if (v.preload !== "auto") { v.preload = "auto"; v.load(); } };
  function next() {
    const prev = reel[cur];
    cur = (cur + 1) % reel.length;
    const v = reel[cur];
    v.currentTime = 0;
    v.play().catch(() => {});
    v.classList.add("is-active");
    prev.classList.remove("is-active");
    setTimeout(() => prev.pause(), 1500);
    nowTitle.style.opacity = 0;
    setTimeout(() => { label(v); nowTitle.style.opacity = 1; }, 400);
    prep(reel[(cur + 1) % reel.length]);
  }
  const start = () => { if (!timer) timer = setInterval(next, SHOW); reel[cur].play().catch(() => {}); };
  const stop = () => { clearInterval(timer); timer = null; reel[cur].pause(); };
  reel.forEach((v) => { v.loop = true; });
  label(reel[0]);
  prep(reel[1 % reel.length]);
  new IntersectionObserver(([e]) => { inView = e.isIntersecting; inView && !document.hidden ? start() : stop(); })
    .observe(document.querySelector(".hero"));
  document.addEventListener("visibilitychange", () => { document.hidden ? stop() : inView && start(); });
}

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
    gsap.fromTo(el, { scale: .94, opacity: 0 }, { scale: 1, opacity: 1, duration: .6, ease: "expo.out" });
  }
}
function show(i, dir = 0) {
  index = (i + links.length) % links.length;
  boxImg.hidden = false;
  boxImg.src = links[index].href;
  boxImg.alt = links[index].querySelector("img")?.alt || "";
  if (box.hidden) openBox(boxImg);
  else if (motion) gsap.fromTo(boxImg, { x: dir * 40, opacity: 0 }, { x: 0, opacity: 1, duration: .45, ease });
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
  toggleFloatBack(y);
}
if (lenis) lenis.on("scroll", ({ scroll }) => onScroll(scroll));
else addEventListener("scroll", () => onScroll(scrollY), { passive: true });

// ---------------------------------------------------------------- back buttons
// "Back" returns to the previous page when we came from this site; otherwise it
// follows its link to the parent page.
function cameFromSite() {
  try { return document.referrer && new URL(document.referrer).origin === location.origin && history.length > 1; }
  catch { return false; }
}
document.querySelectorAll("a[data-back]").forEach((a) => a.addEventListener("click", (e) => {
  if (!cameFromSite()) return;  // let the normal link (and page transition) handle it
  e.preventDefault();
  e.stopImmediatePropagation();
  const href = a.href;
  const goBack = () => {
    let left = false;
    addEventListener("pagehide", () => { left = true; }, { once: true });
    history.back();
    // if the browser had nothing to go back to, don't leave the page covered
    setTimeout(() => { if (!left) location.href = href; }, 1200);
  };
  if (motion) gsap.to(document.querySelector(".veil"), { opacity: 1, duration: .3, onComplete: goBack });
  else goBack();
}, true));
const floatBack = document.querySelector(".float-back");
function toggleFloatBack(y) { floatBack?.classList.toggle("is-visible", y > 400); }

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
  // coming back via Back/Forward restores this page from the browser cache exactly as we
  // left it (veil up, cards faded, scrolling paused) -- undo all of that
  addEventListener("pageshow", (e) => {
    if (!e.persisted) return;
    gsap.killTweensOf([veil, ".card"]);
    gsap.set(veil, { opacity: 0 });
    gsap.set(".card", { opacity: 1 });
    document.querySelector(".zoom-clone")?.remove();
    lenis?.start();
    ScrollTrigger.refresh();
  });
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

// ---------------------------------------------------------------- calm reveals
// Everything fades in and rises once as it arrives; nothing moves after that.
if (motion) {
  gsap.from(".hero-text > *", { y: 30, opacity: 0, duration: 1.2, ease, stagger: .12, delay: .3 });
  gsap.from(".project-title", { y: 30, opacity: 0, duration: 1.2, ease, delay: .2 });

  gsap.utils.toArray(".card, .crumbs, .project .row, .project .banner, .project .icons, .gallery, .carousel, .pager, .site-footer > *")
    .forEach((el) => {
      if (el.closest(".banner-over")) return;
      el.setAttribute("data-reveal", "");
      gsap.to(el, { opacity: 1, y: 0, duration: 1.2, ease, scrollTrigger: { trigger: el, start: "top 90%", once: true } });
    });

  // card pictures settle into their frame as the card appears
  gsap.utils.toArray(".card-media").forEach((m) => {
    const inner = m.querySelector("img, video");
    gsap.fromTo(inner, { scale: 1.06, transition: "none" }, { scale: 1, duration: 1.4, ease, clearProps: "transform,transition",
      scrollTrigger: { trigger: m, start: "top 90%", once: true } });
  });

  addEventListener("load", () => ScrollTrigger.refresh());
}
