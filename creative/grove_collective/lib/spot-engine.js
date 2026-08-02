/* MCTV Digital, Inc. — Proprietary.
   Grove Collective campaign — deterministic spot timeline engine.

   Every spot is a pure function of time. Nothing animates on its own: a spot
   declares a `seek(t)` that paints the frame for second `t`, and the engine
   drives it either from requestAnimationFrame (browser preview) or from the
   renderer one exact frame at a time (video export). Same function, same
   pixels, every run — which is what makes the MP4s reproducible. */

/* ------------------------------------------------------------- math bits -- */

export const clamp = (v, lo = 0, hi = 1) => (v < lo ? lo : v > hi ? hi : v);
export const lerp = (a, b, p) => a + (b - a) * p;

/** Progress through the window [t0, t1], clamped to 0..1. */
export const seg = (t, t0, t1) => clamp((t - t0) / (t1 - t0));

export const ease = {
  linear: (p) => p,
  out: (p) => 1 - Math.pow(1 - p, 3),
  outQuint: (p) => 1 - Math.pow(1 - p, 5),
  in: (p) => p * p * p,
  inOut: (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
  /* Overshoots then settles — the punch-in every sports cut is built on. */
  back: (p) => {
    const c = 1.9;
    return 1 + (c + 1) * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2);
  },
};

/** Tween a scalar across [t0,t1]. */
export const tw = (t, t0, t1, from, to, fn = ease.out) =>
  lerp(from, to, fn(seg(t, t0, t1)));

/** 1 while inside [t0,t1] with eased fades of `fade` seconds on each end. */
export const band = (t, t0, t1, fade = 0.25) =>
  Math.min(seg(t, t0, t0 + fade), 1 - seg(t, t1 - fade, t1));

/** Deterministic PRNG (mulberry32). Seeded so crowds render identically. */
export function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let x = Math.imul(a ^ (a >>> 15), 1 | a);
    x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x;
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };
}

/* ----------------------------------------------------------------- DOM   -- */

export function el(tag, className, parent, style) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (style) Object.assign(node.style, style);
  if (parent) parent.appendChild(node);
  return node;
}

/**
 * Split a string into per-character spans for kinetic type.
 * Spaces become fixed-width gaps so characters can be animated independently
 * without the line collapsing.
 */
export function splitChars(node, text) {
  node.textContent = "";
  const chars = [];
  for (const ch of text) {
    const span = el("span", null, node, {
      display: "inline-block",
      whiteSpace: "pre",
      willChange: "transform, opacity",
    });
    span.textContent = ch;
    chars.push(span);
  }
  return chars;
}

/** Bind a photo to a named slot, or leave it in its designed empty state. */
export function bindPhoto(slot, src, focal) {
  if (!src) return;
  slot.style.setProperty("--img", `url("${src}")`);
  if (focal) slot.style.setProperty("--focal", focal);
  slot.setAttribute("data-filled", "");
}

/* --------------------------------------------------------------- engine  -- */

export class Spot {
  /**
   * @param {object} opts
   * @param {number} opts.duration seconds of finished runtime
   * @param {number} opts.fps frame rate the spot is authored and exported at
   * @param {number} opts.width canvas width — 1920 for the screen network,
   *   1080 for vertical social cuts
   * @param {number} opts.height canvas height
   * @param {(stage: HTMLElement) => (t: number) => void} opts.build
   *   Builds the DOM once and returns the per-frame paint function.
   */
  constructor({ duration = 15, fps = 30, width = 1920, height = 1080, build }) {
    this.duration = duration;
    this.fps = fps;
    this.width = width;
    this.height = height;
    this.build = build;
    this.seekFn = null;
  }

  mount() {
    const stage = document.getElementById("stage");
    this.stage = stage;
    stage.style.width = `${this.width}px`;
    stage.style.height = `${this.height}px`;
    this.seekFn = this.build(stage);

    /* Scale the fixed canvas to whatever box it has been dropped into. The
       renderer sizes the viewport to the canvas, so this resolves to 1. */
    const fit = () => {
      const s = Math.min(
        window.innerWidth / this.width,
        window.innerHeight / this.height
      );
      stage.style.setProperty("--fit", s);
    };
    fit();
    window.addEventListener("resize", fit);

    /* Contract with render.mjs: seek one exact frame, then flag readiness. */
    window.__seek = (t) => this.seekFn(t);
    window.__duration = this.duration;
    window.__fps = this.fps;
    window.__w = this.width;
    window.__h = this.height;

    this.seekFn(0);

    /* Only start the preview clock once type is actually resolved, otherwise
       the first second renders in a fallback face. */
    const start = () => {
      window.__ready = true;
      if (!window.__renderMode) this.play();
    };
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(start);
    } else {
      start();
    }
    return this;
  }

  /** Browser-preview clock. Loops, and supports click to pause / scrub. */
  play() {
    let t0 = performance.now();
    let paused = false;
    let pausedAt = 0;

    const frame = (now) => {
      /* A capture tool can claim the timeline at any point; when it does, the
         preview clock must get out of the way or it overwrites every seek. */
      if (window.__renderMode) return;
      if (!paused) {
        const t = ((now - t0) / 1000) % this.duration;
        this.seekFn(t);
        pausedAt = t;
      }
      requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);

    document.body.addEventListener("click", () => {
      paused = !paused;
      if (!paused) t0 = performance.now() - pausedAt * 1000;
    });

    /* Arrow keys scrub a tenth of a second at a time for reviewing beats. */
    window.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      paused = true;
      pausedAt = clamp(
        pausedAt + (e.key === "ArrowRight" ? 0.1 : -0.1),
        0,
        this.duration
      );
      this.seekFn(pausedAt);
    });
  }
}
