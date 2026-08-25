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
        res({ geometry: mesh.geometry, bodyFat: bf,
          nMus: (ex.muscle || []).length, pose: ex.pose || [] });
      }, undefined, rej);
    }));
  }
  return cache.get(sex);
}

// Warm the cache before any canvas exists. Importing this module already
// cost the caller three.js; this starts the mesh itself, so by the time a
// screen wants the figure both are in hand.
export function preload(sex) { return loadBody(sex); }

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
  const FRAME = 2.2, FLOOR = -1.0;
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
  // The second figure: the goal. Same geometry, its own material, because the
  // unfocused body dims by COLOUR rather than opacity — a self-overlapping
  // mesh goes wrong under transparency and stays honest under darkness.
  const materialB = material.clone();
  const BRIGHT = new THREE.Color(0x4d6b80), DIMC = new THREE.Color(0x263640);

  const pivot = new THREE.Group();
  scene.add(pivot);
  const pivotB = new THREE.Group();
  pivotB.visible = false;
  scene.add(pivotB);

  let mesh = null, meshB = null, geoRef = null, levels = null, nMus = 0,
    poseIx = null,
    want = { sex: "m", bf: 20, ht: 175, kg: 0 },
    wantB = null, focus = "a", pairOn = false;
  // The activity animation: a position on the calorie-burn axis, eased, plus
  // a gait clock. At the bottom the figure sits at a laptop; sliding up it
  // pushes out of the chair, stands, walks, and finally runs — the pose
  // keyframes baked by tools/pose_rig.py, blended here.
  let actOn = false, actP = 0, actEase = 0, actLast = 0, gaitTh = 0;
  let pressOn = false, pressPin = null, pressTh = 0, pressLast = 0;
  let props = null, chairG = null, lapG = null, recG = null, remG = null,
    chairMat = null, lapMat = null, screenMat = null, recMat = null,
    remMat = null, benchG = null, barG = null, benchMat = null,
    barMat = null;
  // The slide-and-dim: pivot x positions, the camera's pull-back, and each
  // material's brightness, eased toward their targets every frame.
  const anim = { ax: 0, bx: 0, cam: 1, aB: 1, bB: 1 };
  let tgt = { ax: 0, bx: 0.45, cam: 1, aB: 1, bB: 1 };
  const XOFF = 0.45;
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
    camera.position.set(0, panY, BASE_D * anim.cam / zoom);
    camera.lookAt(0, panY, 0);
    dirty = true;
  };
  // In pair mode the camera pulls back until both figures fit the width; on
  // its own the frame stays fixed, which is what lets height changes show.
  const retarget = () => {
    const kPair = Math.max(1, 1.5 / (FRAME * (camera.aspect || 1)));
    tgt = {
      ax: pairOn ? -XOFF : 0,
      bx: XOFF,
      cam: pairOn ? kPair : 1,
      aB: pairOn && focus === "b" ? 0 : 1,
      bB: focus === "b" ? 1 : 0
    };
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
      retarget();
      dirty = true;
    }
  };

  const applyTo = (msh, cfg) => {
    // With a weight in hand the fat axis runs on fat-mass index, so the same
    // percentage on a heavier body is visibly more fat; without one (an older
    // caller), it falls back to the percentage against the baked levels.
    const hm = Math.pow((cfg.ht || 175) / 100, 2);
    const w = cfg.kg > 0 && FMI_LEVELS[cfg.sex]
      ? weightsFor(FMI_LEVELS[cfg.sex], cfg.kg * (cfg.bf / 100) / hm)
      : weightsFor(levels, cfg.bf);
    // Only the shape targets — fat and muscle. The pose targets after them
    // belong to the activity clock in tick(), which must not be stomped
    // every time a slider recomputes the body.
    const nShape = (levels.length - 1) + nMus;
    const nInfl = Math.min(msh.morphTargetInfluences.length, nShape);
    for (let i = 0; i < nInfl; i++)
      msh.morphTargetInfluences[i] = w[i] || 0;
    // Lean mass is its own axis. Body fat alone cannot tell a wiry 60 kg
    // frame from a solid 100 kg one, and worse, sliding it down strips lean
    // mass with the fat — everyone bottoms out looking starved. So the
    // muscle pair is driven by FFMI, lean kilograms over height squared:
    // at a constant weight, less fat now means more muscle, which is what
    // the arithmetic says it means.
    if (nMus >= 2 && cfg.kg > 0) {
      const nFat = levels.length - 1;
      const ffmi = cfg.kg * (1 - cfg.bf / 100) / hm;
      // Anchors: population-average FFMI maps to the baked average body,
      // the max-muscle target sits at a clearly athletic figure, and the
      // min-muscle one at the low end of normal.
      const A = cfg.sex === "f"
        ? { lo: 12.5, avg: 15.0, hi: 18.5 }
        : { lo: 15.5, avg: 18.5, hi: 22.5 };
      // Fat buries definition: the muscle target carries the V-taper and the
      // ab tone, and at 30% body fat nobody shows either, whatever their lean
      // mass. So the muscular side is damped as fat climbs — a strongman at
      // 30% reads bulky, not sculpted. The LOW side has the mirror problem:
      // MakeHuman's min-muscle is an untrained softness, and softness is a
      // fat-adjacent look — a 44 kg man at 9% is wiry, not flabby — so it is
      // damped as fat falls instead.
      const mask = Math.max(0.35, Math.min(1, 1.35 - 0.03 * cfg.bf));
      const loMask = Math.max(0.25, Math.min(1, 0.2 + (cfg.bf - 10) / 25));
      const m = ffmi >= A.avg
        ? Math.min(1.3, (ffmi - A.avg) / (A.hi - A.avg)) * mask
        : -Math.min(1, (A.avg - ffmi) / (A.avg - A.lo)) * loMask;
      // Below the low anchor the pair runs out of body: the emaciated target
      // takes over, gaunt face and narrowed frame, ramping in as FFMI falls
      // under it and pushing the plain low-muscle softness out of its way.
      const thin = nMus >= 3
        ? Math.max(0, Math.min(1.2, (A.lo - ffmi) / 3.5)) : 0;
      msh.morphTargetInfluences[nFat] = (m < 0 ? -m : 0) * (1 - Math.min(1, thin));
      msh.morphTargetInfluences[nFat + 1] = m > 0 ? m : 0;
      if (nMus >= 3) msh.morphTargetInfluences[nFat + 2] = thin;
    }
    // The mesh is authored at 1.75 m, so height is a scale about the feet.
    msh.scale.setScalar((cfg.ht || 175) / 175);
  };

  const ensureB = () => {
    if (meshB || !geoRef) return;
    meshB = new THREE.Mesh(geoRef, materialB);
    meshB.position.y = FLOOR;
    pivotB.add(meshB);
  };

  const apply = () => {
    if (!levels) return;
    if (mesh) applyTo(mesh, want);
    if (pairOn) { ensureB(); if (meshB && wantB) applyTo(meshB, wantB); }
    dirty = true;
  };

  const swap = sex => loadBody(sex).then(b => {
    if (!alive) return;
    if (mesh) { pivot.remove(mesh); }
    if (meshB) { pivotB.remove(meshB); meshB = null; }
    geoRef = b.geometry;
    mesh = new THREE.Mesh(geoRef, material);
    mesh.position.y = FLOOR;      // feet on the floor of the frame, not centred
    levels = b.bodyFat;
    nMus = b.nMus || 0;
    poseIx = null;
    if (b.pose && b.pose.length) {
      poseIx = {};
      const base = (levels.length - 1) + nMus;
      b.pose.forEach((n, i) => { poseIx[n] = base + i; });
    }
    if (props) mesh.add(props);   // the chair follows the body across a swap
    pivot.add(mesh);
    apply();
  }).catch(() => { canvas.setAttribute("data-body-failed", "1"); });

  let loaded = null;

  // The chair and the laptop: dark slabs in the body's own space (child of
  // the mesh, so they scale with height and turn with the spin), present
  // only while the figure is seated and fading as it gets up and walks off.
  const ensureProps = () => {
    if (!mesh) return;
    if (props) {
      if (props.parent !== mesh) mesh.add(props);
      return;
    }
    props = new THREE.Group();
    chairMat = new THREE.MeshStandardMaterial({
      color: 0x24363f, roughness: 0.85, metalness: 0.1, transparent: true });
    lapMat = new THREE.MeshStandardMaterial({
      color: 0x2c3f4a, roughness: 0.6, metalness: 0.25, transparent: true });
    screenMat = new THREE.MeshStandardMaterial({
      color: 0x16272e, roughness: 0.4, metalness: 0.1, transparent: true,
      emissive: 0x17414e, emissiveIntensity: 1.1 });
    chairG = new THREE.Group();
    const part = (g, geo, m2, x, y, z, rx) => {
      const p = new THREE.Mesh(geo, m2);
      p.position.set(x, y, z);
      if (rx) p.rotation.x = rx;
      g.add(p);
    };
    part(chairG, new THREE.BoxGeometry(0.46, 0.06, 0.44), chairMat,
      0, 0.44, -0.20);
    part(chairG, new THREE.BoxGeometry(0.44, 0.52, 0.05), chairMat,
      0, 0.76, -0.44, -0.09);
    part(chairG, new THREE.CylinderGeometry(0.028, 0.028, 0.38, 16), chairMat,
      0, 0.22, -0.20);
    part(chairG, new THREE.CylinderGeometry(0.20, 0.24, 0.035, 24), chairMat,
      0, 0.02, -0.20);
    lapG = new THREE.Group();
    part(lapG, new THREE.BoxGeometry(0.30, 0.012, 0.21), lapMat,
      0, 0.615, 0.02);
    part(lapG, new THREE.BoxGeometry(0.30, 0.20, 0.01), screenMat,
      0, 0.70, 0.15, 0.30);
    // The recliner at the very bottom of the scale: cushion, tipped-back
    // backrest, armrests, an ottoman under the calves — and a TV remote in
    // the raised right hand.
    recMat = new THREE.MeshStandardMaterial({
      color: 0x202f39, roughness: 0.9, metalness: 0.05, transparent: true });
    remMat = new THREE.MeshStandardMaterial({
      color: 0x24343d, roughness: 0.5, metalness: 0.2, transparent: true,
      emissive: 0x155060, emissiveIntensity: 1.0 });
    recG = new THREE.Group();
    part(recG, new THREE.BoxGeometry(0.52, 0.10, 0.50), recMat,
      0, 0.42, -0.16);
    part(recG, new THREE.BoxGeometry(0.52, 0.62, 0.10), recMat,
      0, 0.72, -0.47, -0.40);
    part(recG, new THREE.BoxGeometry(0.10, 0.10, 0.50), recMat,
      0.33, 0.55, -0.10);
    part(recG, new THREE.BoxGeometry(0.10, 0.10, 0.50), recMat,
      -0.33, 0.55, -0.10);
    part(recG, new THREE.BoxGeometry(0.40, 0.20, 0.30), recMat,
      0, 0.12, 0.44);
    part(recG, new THREE.BoxGeometry(0.50, 0.06, 0.48), recMat,
      0, 0.03, -0.15);
    remG = new THREE.Group();
    part(remG, new THREE.BoxGeometry(0.045, 0.035, 0.17), remMat,
      -0.315, 0.925, 0.145, -0.95);
    // The incline bench and its bar. The pad leans back at the angle the
    // press keyframes sit into; the bar is a rod with a plate at each end,
    // and the runtime slides it between two anchors on the press clock so
    // it stays in the moving hands.
    benchMat = new THREE.MeshStandardMaterial({
      color: 0x202f39, roughness: 0.9, metalness: 0.05, transparent: true });
    barMat = new THREE.MeshStandardMaterial({
      color: 0x2c3f4a, roughness: 0.35, metalness: 0.55, transparent: true,
      emissive: 0x123a46, emissiveIntensity: 0.7 });
    // Measured against the baked keyframes: the pad lies along the
    // reclined back line, the seat under the hips.
    benchG = new THREE.Group();
    part(benchG, new THREE.BoxGeometry(0.46, 1.0, 0.09), benchMat,
      0, 0.92, -0.357, -0.53);
    part(benchG, new THREE.BoxGeometry(0.44, 0.07, 0.38), benchMat,
      0, 0.445, -0.10);
    part(benchG, new THREE.BoxGeometry(0.09, 0.42, 0.09), benchMat,
      0, 0.21, 0.0);
    part(benchG, new THREE.BoxGeometry(0.09, 0.42, 0.09), benchMat,
      0, 0.21, -0.34);
    part(benchG, new THREE.BoxGeometry(0.40, 0.05, 0.70), benchMat,
      0, 0.03, -0.17);
    barG = new THREE.Group();
    const rod = new THREE.Mesh(
      new THREE.CylinderGeometry(0.018, 0.018, 1.16, 14), barMat);
    rod.rotation.z = Math.PI / 2;
    barG.add(rod);
    const plate = x => {
      const pl = new THREE.Mesh(
        new THREE.CylinderGeometry(0.115, 0.115, 0.045, 22), barMat);
      pl.rotation.z = Math.PI / 2;
      pl.position.x = x;
      barG.add(pl);
    };
    plate(0.5); plate(-0.5);
    props.add(chairG);
    props.add(lapG);
    props.add(recG);
    props.add(remG);
    props.add(benchG);
    props.add(barG);
    props.visible = false;
    mesh.add(props);
  };
  // Each prop follows the pose that uses it: the recliner and remote belong
  // to the reclining couch potato, the office chair to the sit and the push
  // out of it, the laptop to the sit alone.
  const setPropOp = w => {
    if (!props) return;
    // The hand-held props keep to their poses: the laptop only fades in over
    // the last stretch of the sit blend, and the remote lets go over the
    // first stretch of leaving the recline — neither hovers over a body
    // that is between poses.
    const cOp = Math.min(1, w.sit + w.rise),
      lOp = Math.max(0, Math.min(1, (w.sit - 0.55) / 0.45)),
      rOp = w.recline,
      mOp = Math.max(0, Math.min(1, (w.recline - 0.5) / 0.5));
    props.visible = cOp > 0.01 || rOp > 0.01;
    if (benchG) { benchG.visible = false; barG.visible = false; }
    chairG.visible = cOp > 0.01;
    lapG.visible = lOp > 0.01;
    recG.visible = rOp > 0.01;
    remG.visible = mOp > 0.01;
    chairMat.opacity = cOp;
    lapMat.opacity = lOp;
    screenMat.opacity = lOp;
    recMat.opacity = rOp;
    remMat.opacity = mOp;
  };
  // Slider position -> pose weights. Reclined with the remote at the very
  // bottom; at a laptop through the sedentary band; pushing out of the
  // chair around lightly-active; on their feet; walking from .38; running
  // from .72. The walk and run each blend two mirrored stride keyframes on
  // the gait clock, so the figure moves rather than freezes mid-step.
  // Measured off the baked keyframes: where the fists actually are at the
  // bottom of the press and at lockout, plus a couple of centimetres for
  // the palm. The grip width is the same at both, because a bar is rigid.
  const BAR_DN = [1.205, -0.100], BAR_UP = [1.475, -0.058];
  const poseWeightsAt = (p, s) => {
    // The press keys are listed so the walk and run write them back to
    // zero: stepping from the bench to the treadmill must not leave a
    // barbell pose stacked under the stride.
    const w = { recline: 0, sit: 0, rise: 0,
      walkA: 0, walkB: 0, runA: 0, runB: 0, pressDn: 0, pressUp: 0 };
    if (p < 0.065) w.recline = 1;
    else if (p < 0.13) {
      const t = (p - 0.065) / 0.065;
      w.recline = 1 - t;
      w.sit = t;
    } else if (p < 0.20) w.sit = 1;
    else if (p < 0.32) {
      const t = (p - 0.20) / 0.12;
      w.sit = Math.max(0, 1 - 2 * t);
      w.rise = 1 - Math.abs(2 * t - 1);
    }
    const wa = Math.max(0, Math.min(1, (p - 0.38) / 0.14));
    const ru = Math.max(0, Math.min(1, (p - 0.72) / 0.12));
    const g = wa * (1 - ru);
    w.walkA = g * s; w.walkB = g * (1 - s);
    w.runA = ru * s; w.runB = ru * (1 - s);
    return w;
  };

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
    // Ease the slide-and-dim toward its targets: positions, camera, and the
    // two brightnesses, all in one motion.
    let mv = false;
    for (const k in anim) {
      const d = tgt[k] - anim[k];
      if (Math.abs(d) > 0.003) { anim[k] += d * 0.14; mv = true; }
      else if (anim[k] !== tgt[k]) { anim[k] = tgt[k]; mv = true; }
    }
    if (mv) {
      pivot.position.x = anim.ax;
      pivotB.position.x = anim.bx;
      material.color.copy(DIMC).lerp(BRIGHT, anim.aB);
      materialB.color.copy(DIMC).lerp(BRIGHT, anim.bB);
      place();
    }
    // The activity clock. The slider position is eased so a jump across the
    // scale plays through the story — up out of the chair, walking, breaking
    // into a run — rather than teleporting between poses.
    if (actOn && mesh && poseIx) {
      const now = performance.now() / 1000;
      const dt = actLast ? Math.min(0.05, now - actLast) : 0;
      actLast = now;
      actEase += (actP - actEase) * Math.min(1, dt * 5);
      if (Math.abs(actP - actEase) < 0.002) actEase = actP;
      const p = actEase;
      const ru = Math.max(0, Math.min(1, (p - 0.72) / 0.12));
      if (!still && p > 0.38) gaitTh += dt * 2 * Math.PI * (0.9 + 0.45 * ru);
      const s = still ? 1 : 0.5 + 0.5 * Math.sin(gaitTh);
      const w = poseWeightsAt(p, s);
      for (const k in w) if (poseIx[k] != null)
        mesh.morphTargetInfluences[poseIx[k]] = w[k];
      ensureProps();
      setPropOp(w);
      dirty = true;
    }
    // The press clock: the figure swings between the two press keyframes
    // and the bar rides between its anchors in the moving hands.
    if (pressOn && mesh && poseIx) {
      const now = performance.now() / 1000;
      const dt = pressLast ? Math.min(0.05, now - pressLast) : 0;
      pressLast = now;
      if (pressPin == null && !still) pressTh += dt * 2 * Math.PI * 0.42;
      const ph = pressPin != null ? pressPin
        : still ? 1 : 0.5 - 0.5 * Math.cos(pressTh);
      for (const k in poseIx) mesh.morphTargetInfluences[poseIx[k]] = 0;
      if (poseIx.pressDn != null)
        mesh.morphTargetInfluences[poseIx.pressDn] = 1 - ph;
      if (poseIx.pressUp != null)
        mesh.morphTargetInfluences[poseIx.pressUp] = ph;
      ensureProps();
      props.visible = true;
      chairG.visible = lapG.visible = recG.visible = remG.visible = false;
      benchG.visible = true; barG.visible = true;
      benchMat.opacity = 1; barMat.opacity = 1;
      barG.position.set(0,
        BAR_DN[0] + (BAR_UP[0] - BAR_DN[0]) * ph,
        BAR_DN[1] + (BAR_UP[1] - BAR_DN[1]) * ph);
      dirty = true;
    }
    if (!dirty) return;
    pivot.rotation.y = spin;
    pivotB.rotation.y = spin;
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
  // A tap on one of the pair is a tab switch: the host registers a callback
  // and a press that neither dragged nor lingered picks the figure under it
  // by screen half — current on the left, goal on the right.
  let pickCb = null, tap0 = null;
  const down = e => {
    pts.set(e.pointerId, { x: e.clientX, y: e.clientY });
    vel = 0;
    if (pts.size === 2) { pinch0 = spread(); zoom0 = zoom; drag = null; tap0 = null; }
    else if (pts.size === 1) {
      drag = { x: e.clientX, y: e.clientY };
      tap0 = { x: e.clientX, y: e.clientY, t: performance.now() };
    }
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
    if (tap0 && pts.size === 0 && pairOn && pickCb
        && Math.hypot(e.clientX - tap0.x, e.clientY - tap0.y) < 8
        && performance.now() - tap0.t < 450) {
      const r = canvas.getBoundingClientRect();
      pickCb(e.clientX - r.left < r.width / 2 ? "a" : "b");
    }
    if (pts.size === 0) tap0 = null;
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
    // Prop visibility snapshot — the preview harness again.
    props() {
      return props ? {
        chair: [chairG.visible, chairMat.opacity],
        lap: [lapG.visible, lapMat.opacity],
        rec: [recG.visible, recMat.opacity],
        rem: [remG.visible, remMat.opacity]
      } : null;
    },
    // Pin one pose keyframe at full weight — the preview harness again.
    pose(name, v) {
      if (!mesh || !poseIx) return null;
      actOn = false;
      for (const k in poseIx) mesh.morphTargetInfluences[poseIx[k]] = 0;
      const w = { recline: 0, sit: 0, rise: 0 };
      if (name && poseIx[name] != null) {
        mesh.morphTargetInfluences[poseIx[name]] = v == null ? 1 : v;
        if (name in w) w[name] = v == null ? 1 : v;
      }
      ensureProps();
      setPropOp(w);
      dirty = true;
      return Object.keys(poseIx);
    },
    // Register the tap-to-pick callback: called with "a" (current) or "b"
    // (goal) when a figure of the pair is tapped.
    onPick(fn) { pickCb = fn; },
    // The activity animation, driven by the calorie-burn slider: p in [0,1]
    // across the burn range, or null to stand the figure back up.
    // The press animation: true to run the clock, a number to pin its
    // phase (the tuning harness), null to put the bar down.
    press(v) {
      if (v == null || v === false) {
        if (pressOn) {
          pressOn = false; pressPin = null;
          if (mesh && poseIx)
            for (const k in poseIx) mesh.morphTargetInfluences[poseIx[k]] = 0;
          if (props) props.visible = false;
          dirty = true;
        }
        return;
      }
      if (!pressOn) { pressTh = 0; pressLast = 0; }
      pressOn = true; actOn = false;
      pressPin = typeof v === "number" ? Math.max(0, Math.min(1, v)) : null;
      dirty = true;
    },
    act(p) {
      if (p == null) {
        if (actOn) {
          actOn = false;
          if (mesh && poseIx)
            for (const k in poseIx) mesh.morphTargetInfluences[poseIx[k]] = 0;
          if (props) props.visible = false;
          dirty = true;
        }
        return;
      }
      const v = Math.max(0, Math.min(1, p));
      if (!actOn) { actLast = 0; actEase = v; gaitTh = 0; }
      actOn = true; pressOn = false;
      actP = v;
      dirty = true;
    },
    set(sex, bf, ht, kg) {
      if (pairOn) { pairOn = false; wantB = null; pivotB.visible = false; retarget(); }
      want.bf = bf;
      if (ht) want.ht = ht;
      if (kg) want.kg = kg;
      if (sex !== loaded) { loaded = sex; want.sex = sex; swap(sex); }
      else apply();
    },
    // Two figures: the current body and the goal, side by side. On the first
    // call the goal is born where the current stands and slides to the right
    // while the camera pulls back; whichever holds focus is lit, the other
    // dims. f is "a" (current) or "b" (goal).
    setPair(a, b, f) {
      const was = pairOn;
      want = Object.assign({}, a);
      wantB = Object.assign({}, b);
      focus = f === "b" ? "b" : "a";
      pairOn = true;
      pivotB.visible = true;
      if (!was) { anim.bx = anim.ax; anim.bB = anim.aB; }
      if (a.sex !== loaded) { loaded = a.sex; swap(a.sex); }
      else apply();
      retarget();
      dirty = true;
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
