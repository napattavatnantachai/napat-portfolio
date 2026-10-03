// Home hero: floating glossy shapes (indigo, chrome, lime, glass) that drift,
// lean toward the pointer and scatter as the page scrolls.
(() => {
  const canvas = document.querySelector(".hero-canvas");
  if (!canvas || !window.THREE) return;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const small = innerWidth < 760;

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.95;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 100);
  camera.position.set(0, 0, 14);

  // studio-like environment so metal and lacquer have something to reflect
  const pmrem = new THREE.PMREMGenerator(renderer);
  const env = new THREE.Scene();
  env.add(new THREE.Mesh(new THREE.BoxGeometry(30, 30, 30),
    new THREE.MeshBasicMaterial({ color: 0xe9ebf6, side: THREE.BackSide })));
  const panel = (w, h, x, y, z, c) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: c, side: THREE.DoubleSide }));
    m.position.set(x, y, z); m.lookAt(0, 0, 0); env.add(m);
  };
  panel(12, 4, 0, 12, 4, 0xffffff);
  panel(4, 10, -13, 2, 2, 0xffffff);
  panel(6, 6, 12, -4, 6, 0x9aa4ff);
  panel(20, 3, 0, -13, -2, 0x30333f);
  scene.environment = pmrem.fromScene(env, 0.02).texture;

  const key = new THREE.DirectionalLight(0xffffff, 1.2);
  key.position.set(4, 6, 8);
  scene.add(key, new THREE.AmbientLight(0xffffff, 0.25));
  const pointer = new THREE.PointLight(0x8f9bff, 1.4, 20);
  pointer.position.set(0, 0, 5);
  scene.add(pointer);

  const srgb = (hex) => new THREE.Color(hex).convertSRGBToLinear();
  const mats = {
    indigo: new THREE.MeshPhysicalMaterial({ color: srgb(0x1a2ffb), metalness: 0.25, roughness: 0.18, clearcoat: 1, clearcoatRoughness: 0.08 }),
    chrome: new THREE.MeshPhysicalMaterial({ color: srgb(0xd6d9e6), metalness: 1, roughness: 0.12 }),
    lime: new THREE.MeshPhysicalMaterial({ color: srgb(0xc1ff00), metalness: 0.1, roughness: 0.3, clearcoat: 1 }),
    glass: new THREE.MeshPhysicalMaterial({ color: srgb(0xffffff), metalness: 0, roughness: 0.04, transmission: 1, transparent: true, opacity: 0.9, clearcoat: 1 }),
    ink: new THREE.MeshPhysicalMaterial({ color: srgb(0x0b0b0f), metalness: 0.6, roughness: 0.25, clearcoat: 1 }),
  };
  const geos = {
    knot: new THREE.TorusKnotGeometry(0.9, 0.32, 220, 32),
    torus: new THREE.TorusGeometry(0.75, 0.28, 48, 120),
    pill: new THREE.CylinderGeometry(0.45, 0.45, 1.8, 64),
    ball: new THREE.SphereGeometry(0.6, 64, 64),
    gem: new THREE.IcosahedronGeometry(0.75, 0),
    cone: new THREE.ConeGeometry(0.6, 1.3, 64),
  };
  // [geometry, material, x, y, z, scale]
  const layout = [
    ["knot", "indigo", 3.2, 0.9, 0, 1.25],
    ["torus", "chrome", 6.3, 2.8, -2, 1],
    ["pill", "glass", 1.2, 3.2, -1, 0.9],
    ["ball", "lime", 5.0, -1.6, 1.2, 0.55],
    ["gem", "ink", 7.6, -0.6, -3, 1],
    ["pill", "indigo", 7.4, 3.6, -4, 0.8],
    ["ball", "chrome", 1.8, -2.4, -2, 0.8],
    ["cone", "chrome", -0.8, 3.8, -5, 0.9],
    ["torus", "indigo", -3.0, 3.0, -6, 0.9],
    ["gem", "glass", 4.6, 4.0, -3, 0.7],
    ["ball", "indigo", 8.8, 1.4, -1, 0.45],
    ["pill", "chrome", -5.5, 4.2, -7, 0.9],
  ];
  const group = new THREE.Group();
  scene.add(group);
  const items = (small ? layout.slice(0, 7) : layout).map(([g, m, x, y, z, s], i) => {
    const mesh = new THREE.Mesh(geos[g], mats[m]);
    mesh.position.set(x, y, z);
    mesh.scale.setScalar(s);
    mesh.rotation.set(Math.random() * 3, Math.random() * 3, Math.random() * 3);
    group.add(mesh);
    return { mesh, base: mesh.position.clone(), phase: i * 1.7, spin: 0.15 + Math.random() * 0.25 };
  });

  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    // keep the cluster on the right on wide screens, centered above the text on narrow ones
    group.position.set(camera.aspect > 1.2 ? -1.2 : -3.6, camera.aspect > 1.2 ? 0 : 1.4, 0);
    group.scale.setScalar(camera.aspect > 1.2 ? 1 : 0.7);
  }
  addEventListener("resize", resize);
  resize();

  const mouse = new THREE.Vector2(), target = new THREE.Vector2();
  addEventListener("pointermove", (e) => {
    target.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1);
  }, { passive: true });

  let visible = true;
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; }).observe(canvas);

  const clock = new THREE.Clock();
  const tmp = new THREE.Vector3();
  function frame() {
    requestAnimationFrame(frame);
    if (!visible) return;
    const t = reduced ? 0 : clock.getElapsedTime();
    mouse.lerp(target, 0.06);
    const scroll = Math.min(scrollY / innerHeight, 1.2);

    group.rotation.y = mouse.x * 0.18;
    group.rotation.x = -mouse.y * 0.12;
    pointer.position.set(mouse.x * 7, mouse.y * 4, 5);

    // pointer position in world space at z = 0, used to push nearby shapes away
    tmp.set(mouse.x, mouse.y, 0.5).unproject(camera).sub(camera.position).normalize();
    const hit = camera.position.clone().add(tmp.multiplyScalar(-camera.position.z / tmp.z)).sub(group.position);

    for (const it of items) {
      const p = it.base;
      const dx = p.x - hit.x, dy = p.y - hit.y;
      const d = Math.hypot(dx, dy) || 1;
      const push = Math.max(0, 1.8 - d) * 0.6;
      it.mesh.position.x += ((p.x + (dx / d) * push) - it.mesh.position.x) * 0.08;
      it.mesh.position.y += ((p.y + Math.sin(t * 0.8 + it.phase) * 0.18 + (dy / d) * push + scroll * (2 + it.phase % 3)) - it.mesh.position.y) * 0.08;
      it.mesh.rotation.x += 0.004 * it.spin * (reduced ? 0 : 1) * 4;
      it.mesh.rotation.y += 0.006 * it.spin * (reduced ? 0 : 1) * 4;
    }
    renderer.render(scene, camera);
  }
  frame();
})();
