// The figure in CALORIE CALC.
//
// A glTF with morph targets, blended continuously from two numbers: body fat
// and lean mass. Fat sweeps the ascending fat levels; lean mass — computed as
// FFMI from the weight, height and body fat actually entered — drives an
// optional pair of muscle targets, so at a constant weight a lower body fat
// reads as a fitter body, not a smaller one. The mesh that ships is baked from
// MakeHuman's CC0 data by tools/makehuman_bake.py; the contract is written in
// tools/build_body_glb.py — base mesh leanest, fat targets ascending with
// mesh.extras.bodyFat listing their percentages, then the muscle pair named
// in mesh.extras.muscle.
//
// Loaded on demand, and only ever once: three is 670 KB and has no business
// being fetched by anyone who opens the food table.

import * as THREE from "./vendor/three/three.module.min.js";
import { GLTFLoader } from "./vendor/three/GLTFLoader.js";

const CYAN = 0x22d3ee;
const cache = new Map();      // sex -> Promise<{ geometry, bodyFat }>

function loadBody(sex) {
  if (!cache.has(sex)) {
    cache.set(sex, new Promise((res, rej) => {
      new GLTFLoader().load("data/body/body-" + sex + ".glb", g => {
        let mesh = null;
        g.scene.traverse(o => { if (o.isMesh && !mesh) mesh = o; });
        if (!mesh) return rej(new Error("no mesh"));
        const ex = g.parser.json.meshes[0].extras || {};
        const bf = (mesh.geometry.userData && mesh.geometry.userData.bodyFat)
          || ex.bodyFat;
        res({ geometry: mesh.geometry, bodyFat: bf, nMus: (ex.muscle || []).length });
      }, undefined, rej);
    }));
  }
  return cache.get(sex);
}

// The blend. With one parameter swept across N shapes, the influence of each is
// a hat function on the level axis — which makes the result exactly the linear
// interpolation between the two shapes either side, and nothing else.
function weightsFor(levels, bf) {
  const w = new Array(levels.length - 1).fill(0);
  const v = Math.max(levels[0], Math.min(levels[levels.length - 1], bf));
  for (let i = 0; i < levels.length - 1; i++) {
    const a = levels[i], b = levels[i + 1];
    if (v >= a && v <= b) {
      const t = (v - a) / (b - a);
      if (i > 0) w[i - 1] = 1 - t;
      w[i] = t;
      // Every target below the bracket is fully on: the deltas are measured from
      // the base, so leaving them out would snap back to the leanest shape.
      for (let k = 0; k < i - 1; k++) w[k] = 0;
      break;
    }
  }
  return w;
}

// What the fat axis actually answers to when the weight is known: fat MASS over
// height squared, not the percentage. 104 kg and 70 kg at the same 30% carry
// 31 kg and 21 kg of fat — one is bulky fat, the other skinny fat — and a
// percentage-driven morph would dress them identically. Each baked level is
// anchored at the fat-mass index of the reference body it was sculpted as
// (e.g. the male 30% level as a 92 kg man: 27.6 kg fat / 1.75² ≈ 9.0).
const FMI_LEVELS = {
  m: [1.9, 3.7, 5.9, 9.0, 13.2, 18.6],
  f: [2.4, 3.8, 5.8, 8.2, 12.1, 17.3]
};

export function mount(canvas) {
  if (canvas.__body) return canvas.__body;

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  } catch (e) { return null; }
  renderer.setClearAlpha(0);

  const scene = new THREE.Scene();
  // The mesh is authored feet-at-origin in metres, so it is dropped by half its
  // height and the camera sits square on the middle of it. A 1.95 m frame at 26
  // degrees puts the whole figure in the box with a little air top and bottom,
  // and since the vertical field of view maps to the box height, the figure fills
  // whatever height the layout gives it without any per-screen fitting.
  // The frame is FIXED at 2.35 m of world height with the floor at a fixed place,
  // rather than fitted to whatever body is in it. That is the only way a change of
  // height can be seen: fit the camera to the body and every body fills the box.
  // 2.2 m of frame: a 1.75 m body fills four fifths of it, and the whole 140-215
  // range fits without the tallest clipping its crown. Feet a little above the
  // floor of the frame, so the figure stands on something rather than in the
  // exact middle of nothing.
  const FRAME = 2.2, FLOOR = -1.07;
  const camera = new THREE.PerspectiveCamera(26, 1, 0.1, 20);
  camera.position.set(0, 0, (FRAME / 2) / Math.tan(26 * Math.PI / 360));
  camera.lookAt(0, 0, 0);

  // Lit so the body is legible on a phone in daylight, which the first pass was
  // not: it was a dark shape on a dark page and only the cyan edge showed. The
  // surface is a couple of steps lighter, there is a fill from the other side so
  // nothing goes to pure black, and the cyan is now a rim rather than the only
  // light in the room.
  scene.add(new THREE.HemisphereLight(0x51708a, 0x0d1620, 1.5));
  const key = new THREE.DirectionalLight(0xdcecf7, 1.9);
  key.position.set(-2.2, 2.6, 3.4);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0x8fb3c8, 0.75);
  fill.position.set(2.6, 0.6, 2.2);
  scene.add(fill);
  const rim = new THREE.DirectionalLight(CYAN, 2.6);
  rim.position.set(3.4, 1.4, -2.6);
  scene.add(rim);

  const material = new THREE.MeshStandardMaterial({
    color: 0x4d6b80, roughness: 0.66, metalness: 0.04, flatShading: false
  });

  const pivot = new THREE.Group();
  scene.add(pivot);

  let mesh = null, levels = null, nMus = 0,
    want = { sex: "m", bf: 20, ht: 175, kg: 0 };
  let spin = 0, drag = null, vel = 0, raf = 0, alive = true, dirty = true;
  // Pinch. The camera pulls in and out rather than the body scaling, so the
  // perspective stays honest at every zoom.
  const BASE_D = camera.position.z;
  let zoom = 1, pinch0 = 0, zoom0 = 1, panY = 0;
  const ZOOM_MIN = 0.8, ZOOM_MAX = 2.4;
  // Zoomed in, the camera is looking at the middle of the body, which is the hips —
  // so a vertical drag walks it up and down. Clamped to the body's own extent, so
  // you can reach the head and the feet and nothing beyond them.
  const place = () => {
    const half = (FRAME / 2) / zoom;              // half the visible height, metres
    const lim = Math.max(0, FRAME / 2 - half);
    panY = Math.max(-lim, Math.min(lim, panY));
    camera.position.set(0, panY, BASE_D / zoom);
    camera.lookAt(0, panY, 0);
    dirty = true;
  };
  const setZoom = z => {
    zoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, z));
    place();
  };
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;

  const size = () => {
    const r = canvas.getBoundingClientRect();
    const w = Math.max(1, Math.round(r.width)), h = Math.max(1, Math.round(r.height));
    if (canvas.width !== w * devicePixelRatio || canvas.height !== h * devicePixelRatio) {
      renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      dirty = true;
    }
  };

  const apply = () => {
    if (!mesh || !levels) return;
    // With a weight in hand the fat axis runs on fat-mass index, so the same
    // percentage on a heavier body is visibly more fat; without one (an older
    // caller), it falls back to the percentage against the baked levels.
    const hm = Math.pow((want.ht || 175) / 100, 2);
    const w = want.kg > 0 && FMI_LEVELS[want.sex]
      ? weightsFor(FMI_LEVELS[want.sex], want.kg * (want.bf / 100) / hm)
      : weightsFor(levels, want.bf);
    for (let i = 0; i < mesh.morphTargetInfluences.length; i++)
      mesh.morphTargetInfluences[i] = w[i] || 0;
    // Lean mass is its own axis. Body fat alone cannot tell a wiry 60 kg
    // frame from a solid 100 kg one, and worse, sliding it down strips lean
    // mass with the fat — everyone bottoms out looking starved. So the
    // muscle pair is driven by FFMI, lean kilograms over height squared:
    // at a constant weight, less fat now means more muscle, which is what
    // the arithmetic says it means.
    if (nMus >= 2 && want.kg > 0) {
      const nFat = levels.length - 1;
      const ffmi = want.kg * (1 - want.bf / 100) / hm;
      // Anchors: population-average FFMI maps to the baked average body,
      // the max-muscle target sits at a clearly athletic figure, and the
      // min-muscle one at the low end of normal.
      const A = want.sex === "f"
        ? { lo: 12.5, avg: 15.0, hi: 18.5 }
        : { lo: 15.5, avg: 18.5, hi: 22.5 };
      // Fat buries definition: the muscle target carries the V-taper and the
      // ab tone, and at 30% body fat nobody shows either, whatever their lean
      // mass. So the muscular side is damped as fat climbs — a strongman at
      // 30% reads bulky, not sculpted. The LOW side has the mirror problem:
      // MakeHuman's min-muscle is an untrained softness, and softness is a
      // fat-adjacent look — a 44 kg man at 9% is wiry, not flabby — so it is
      // damped as fat falls instead.
      const mask = Math.max(0.35, Math.min(1, 1.35 - 0.03 * want.bf));
      const loMask = Math.max(0.25, Math.min(1, 0.2 + (want.bf - 10) / 25));
      const m = ffmi >= A.avg
        ? Math.min(1.3, (ffmi - A.avg) / (A.hi - A.avg)) * mask
        : -Math.min(1, (A.avg - ffmi) / (A.avg - A.lo)) * loMask;
      // Below the low anchor the pair runs out of body: the emaciated target
      // takes over, gaunt face and narrowed frame, ramping in as FFMI falls
      // under it and pushing the plain low-muscle softness out of its way.
      const thin = nMus >= 3
        ? Math.max(0, Math.min(1.2, (A.lo - ffmi) / 3.5)) : 0;
      mesh.morphTargetInfluences[nFat] = (m < 0 ? -m : 0) * (1 - Math.min(1, thin));
      mesh.morphTargetInfluences[nFat + 1] = m > 0 ? m : 0;
      if (nMus >= 3) mesh.morphTargetInfluences[nFat + 2] = thin;
    }
    // The mesh is authored at 1.75 m, so height is a scale about the feet.
    mesh.scale.setScalar((want.ht || 175) / 175);
    dirty = true;
  };

  const swap = sex => loadBody(sex).then(b => {
    if (!alive) return;
    if (mesh) { pivot.remove(mesh); }
    mesh = new THREE.Mesh(b.geometry, material);
    mesh.position.y = FLOOR;      // feet on the floor of the frame, not centred
    levels = b.bodyFat;
    nMus = b.nMus || 0;
    pivot.add(mesh);
    apply();
  }).catch(() => { canvas.setAttribute("data-body-failed", "1"); });

  let loaded = null;

  const tick = () => {
    if (!alive) return;
    raf = requestAnimationFrame(tick);
    size();
    if (pts.size === 0 && !still) {
      spin += 0.0042 + vel;
      vel *= 0.94;
      dirty = true;
    } else if (Math.abs(vel) > 1e-5) {
      spin += vel; vel *= 0.9; dirty = true;
    }
    if (!dirty) return;
    pivot.rotation.y = spin;
    renderer.render(scene, camera);
    dirty = false;
  };

  // Pointer events rather than mouse and touch separately: a Map keyed by pointerId
  // gives one finger, two fingers and a mouse the same code path, and the canvas
  // carries touch-action:none so the browser hands the gesture over intact.
  const pts = new Map();
  const spread = () => {
    const [a2, b2] = [...pts.values()];
    return Math.hypot(a2.x - b2.x, a2.y - b2.y);
  };
  const down = e => {
    pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
    vel = 0;
    if (pts.size === 2) { pinch0 = spread(); zoom0 = zoom; drag = null; }
    else if (pts.size === 1) drag = { x: e.clientX, y: e.clientY };
    if (canvas.setPointerCapture) try { canvas.setPointerCapture(e.pointerId); } catch (x) {}
  };
  const move = e => {
    if (!pts.has(e.pointerId)) return;
    pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pts.size >= 2) {
      if (pinch0 > 0) setZoom(zoom0 * (spread() / pinch0));
    } else if (drag != null) {
      vel = (e.clientX - drag.x) * 0.012;
      spin += vel;
      if (zoom > 1.05) { panY += (e.clientY - drag.y) * 0.0032 * ((FRAME / 2) / zoom); place(); }
      drag = { x: e.clientX, y: e.clientY };
      dirty = true;
    }
    if (e.cancelable) e.preventDefault();
  };
  const up = e => {
    pts.delete(e.pointerId);
    if (pts.size < 2) pinch0 = 0;
    // Whichever finger is left takes over the drag, so lifting one out of a pinch
    // does not jump the body.
    drag = pts.size === 1 ? { ...[...pts.values()][0] } : null;
  };
  const wheel = e => { setZoom(zoom * (e.deltaY < 0 ? 1.1 : 1 / 1.1)); e.preventDefault(); };

  canvas.addEventListener("pointerdown", down);
  canvas.addEventListener("pointermove", move, { passive: false });
  canvas.addEventListener("pointerup", up);
  canvas.addEventListener("pointercancel", up);
  canvas.addEventListener("pointerleave", up);
  canvas.addEventListener("wheel", wheel, { passive: false });

  tick();

  const api = {
    // Turn to an exact angle — used by the preview harness, harmless to keep.
    view(rad) { spin = rad; vel = 0; pivot.rotation.y = spin; dirty = true; },
    infl() { return mesh ? Array.from(mesh.morphTargetInfluences) : null; },
    set(sex, bf, ht, kg) {
      want.bf = bf;
      if (ht) want.ht = ht;
      if (kg) want.kg = kg;
      if (sex !== loaded) { loaded = sex; want.sex = sex; swap(sex); }
      else apply();
    },
    dispose() {
      alive = false;
      cancelAnimationFrame(raf);
      canvas.removeEventListener("pointerdown", down);
      canvas.removeEventListener("pointermove", move);
      canvas.removeEventListener("pointerup", up);
      canvas.removeEventListener("pointercancel", up);
      canvas.removeEventListener("pointerleave", up);
      canvas.removeEventListener("wheel", wheel);
      renderer.dispose();
      delete canvas.__body;
    }
  };
  canvas.__body = api;
  return api;
}
