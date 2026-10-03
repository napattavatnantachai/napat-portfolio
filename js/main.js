// Ambient videos: play only while on screen, to keep CPU and bandwidth low.
const ambient = document.querySelectorAll("video[data-autoplay]");
if ("IntersectionObserver" in window) {
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
} else {
  ambient.forEach((v) => { v.preload = "auto"; v.play().catch(() => {}); });
}

// Lightbox for images (with prev/next) and for video-only cards.
const box = document.querySelector(".lightbox");
const boxImg = box.querySelector("img");
const links = [...document.querySelectorAll("a[data-lightbox]")];
let index = -1;
let boxVideo = null;

function show(i) {
  index = (i + links.length) % links.length;
  boxImg.hidden = false;
  boxImg.src = links[index].href;
  boxImg.alt = links[index].querySelector("img")?.alt || "";
  box.hidden = false;
  document.body.style.overflow = "hidden";
}
function close() {
  box.hidden = true;
  boxImg.removeAttribute("src");
  if (boxVideo) { boxVideo.remove(); boxVideo = null; }
  document.body.style.overflow = "";
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
  box.hidden = false;
  document.body.style.overflow = "hidden";
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
