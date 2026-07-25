/* MCTV Digital, Inc. — Proprietary.
   Grove Collective campaign — reusable scene primitives.

   These build the "night game" world procedurally: light rig, crowd bowl,
   atmosphere. They exist so a spot reads as a packed stadium on a screen
   across the room without depending on cleared photography. When real
   photography is bound to a spot's slots, these sit behind it as environment
   rather than being replaced. */

import { el, rng, clamp, seg, tw, ease, lerp } from "./spot-engine.js";

/* ------------------------------------------------------------ light rig  -- */

/**
 * Four overhead light banks that bloom up and sweep. `seek(t, power)` takes a
 * 0..1 power level so a spot can bring the house lights up on its own beat.
 */
export function stadiumLights(parent) {
  const layer = el("div", "layer", parent, { zIndex: 2 });

  /* Overhead bloom. */
  const banks = [-340, 420, 1100, 1860].map((x, i) => {
    const node = el("div", "lightbank", layer);
    node.style.left = `${x}px`;
    return { node, phase: i * 0.7 };
  });

  /* Hard light shafts raking down through the haze. These are what actually
     sell "night game" — without them the top of frame is dead navy. */
  const shafts = [140, 520, 980, 1420, 1760].map((x, i) => {
    const node = el("div", null, layer, {
      position: "absolute",
      left: `${x}px`,
      top: "-180px",
      width: `${lerp(120, 260, (i % 3) / 2)}px`,
      height: "1180px",
      background:
        "linear-gradient(to bottom, rgba(214,234,255,0.4) 0%, rgba(180,212,246,0.16) 34%, rgba(150,190,235,0.04) 62%, transparent 82%)",
      transform: `skewX(${i % 2 ? 11 : -13}deg)`,
      filter: "blur(20px)",
      mixBlendMode: "screen",
      willChange: "opacity, transform",
    });
    return { node, phase: i * 1.3, skew: i % 2 ? 11 : -13 };
  });

  /* Field horizon: the bright line the crowd is silhouetted against. */
  const horizon = el("div", null, layer, {
    position: "absolute",
    left: "-10%",
    right: "-10%",
    bottom: "120px",
    height: "420px",
    background:
      "radial-gradient(ellipse 60% 100% at 50% 100%, rgba(196,224,255,0.5) 0%, rgba(120,170,225,0.2) 38%, transparent 72%)",
    filter: "blur(34px)",
    mixBlendMode: "screen",
    willChange: "opacity",
  });

  return {
    seek(t, power = 1) {
      for (const b of banks) {
        /* A slow drift keeps the flares alive between beats without ever
           calling attention to itself. */
        const drift = Math.sin(t * 0.55 + b.phase) * 46;
        const bloom = 0.78 + Math.sin(t * 1.25 + b.phase * 1.7) * 0.18;
        b.node.style.opacity = clamp(power * bloom, 0, 1);
        b.node.style.transform = `translate3d(${drift}px, 0, 0) scaleX(${lerp(
          0.82,
          1.08,
          power
        )})`;
      }
      for (const s of shafts) {
        const flick = 0.66 + Math.sin(t * 0.9 + s.phase) * 0.24;
        s.node.style.opacity = String(clamp(power * flick));
        s.node.style.transform = `skewX(${s.skew}deg) translate3d(${
          Math.sin(t * 0.4 + s.phase) * 22
        }px, 0, 0)`;
      }
      horizon.style.opacity = String(clamp(power * 0.95));
    },
  };
}

/* ---------------------------------------------------------------- crowd  -- */

/** Far rows lift toward the haze so the back of the bowl doesn't read as
    hard black speckle against the lit field. */
const depthLift = (depth) => Math.pow(depth, 1.4) * 46;

/**
 * A stadium bowl built from ~1,600 seated silhouettes in receding rows.
 * `seek(t, fill)` reveals the crowd from the lower bowl upward as `fill`
 * climbs 0..1, which is how the membership-drive spot turns a number into a
 * room full of people.
 *
 * @param {number} seed fixed so every render produces the identical crowd
 */
export function crowd(parent, { seed = 20260725, rows = 26, zIndex = 3 } = {}) {
  const layer = el("div", "layer", parent, { zIndex });
  const rand = rng(seed);
  const people = [];

  for (let r = 0; r < rows; r++) {
    /* Rows recede toward the top of frame: smaller, dimmer, tighter packed. */
    const depth = r / (rows - 1);
    const y = 1080 - 18 - Math.pow(depth, 0.74) * 700;
    const size = lerp(23, 6, depth);
    const count = Math.round(lerp(38, 104, depth));

    for (let c = 0; c < count; c++) {
      const jitterX = (rand() - 0.5) * (1920 / count) * 0.8;
      const x = (c + 0.5) * (1920 / count) + jitterX;
      const node = el("div", null, layer, {
        position: "absolute",
        left: `${x - size / 2}px`,
        top: `${y - size * 1.5}px`,
        width: `${size}px`,
        height: `${size * 1.5}px`,
        /* Head-and-shoulders silhouette, cheap enough to draw 1,100 of. */
        borderRadius: `${size * 0.5}px ${size * 0.5}px ${size * 0.18}px ${
          size * 0.18
        }px`,
        willChange: "opacity, transform",
      });

      people.push({
        node,
        depth,
        /* Reveal order runs bottom-up with a little scatter so the bowl fills
           like a crowd arriving, not like a progress bar. */
        order: clamp(depth * 0.82 + rand() * 0.3),
        phase: rand() * Math.PI * 2,
        /* Roughly one in eight is holding a phone light. Those are the
           sparkle that keeps the bowl from reading as wallpaper. */
        lit: rand() < 0.12,
        tone: rand(),
      });
    }
  }

  return {
    node: layer,
    seek(t, fill = 1, energy = 1) {
      for (const p of people) {
        /* Each silhouette has its own short fade-in around its order point. */
        const on = clamp((fill - p.order) * 7);
        if (on <= 0) {
          p.node.style.opacity = "0";
          continue;
        }

        /* Bob amplitude rises with `energy` — this is the crowd "roar". */
        const bob = Math.sin(t * 3.1 + p.phase) * 3.4 * energy * (1 - p.depth * 0.5);

        if (p.lit) {
          /* Phone lights twinkle out of phase with the bob. */
          const flick = 0.55 + Math.sin(t * 4.3 + p.phase * 2.1) * 0.45;
          p.node.style.background = `rgba(255, 248, 226, ${0.55 + flick * 0.45})`;
          p.node.style.boxShadow = `0 0 ${lerp(12, 44, flick)}px rgba(255,238,196,${
            0.75 * flick
          })`;
          p.node.style.opacity = String(on * (0.7 + flick * 0.3));
        } else {
          /* Unlit heads read as dark silhouettes cut against the lit field
             behind them — the near rows nearly black, the far rows hazing
             out into the atmosphere. */
          const shade = lerp(10, 52, p.tone) + depthLift(p.depth);
          p.node.style.background = `rgb(${Math.round(shade * 0.55)}, ${Math.round(
            shade * 0.8
          )}, ${Math.round(shade + 30)})`;
          p.node.style.opacity = String(on * lerp(0.96, 0.5, p.depth));
        }

        p.node.style.transform = `translate3d(0, ${bob}px, 0)`;
      }
    },
  };
}

/* ----------------------------------------------------------- atmosphere  -- */

/** Haze, vignette and grain — the layers that sell depth. */
export function atmosphere(parent, { zIndex = 40 } = {}) {
  const haze = el("div", "haze", parent, { zIndex: zIndex - 30 });
  el("div", "vignette", parent, { zIndex });
  el("div", "grain", parent, { zIndex: zIndex + 1 });
  return {
    seek(t, power = 1) {
      haze.style.opacity = String(0.55 + power * 0.45);
    },
  };
}

/* -------------------------------------------------------------- endcard  -- */

/**
 * The persistent MCTV attribution bar. Slides up at `at` seconds and holds.
 * Keeping this identical across the campaign is what makes three different
 * spots read as one buy.
 */
export function endcard(parent, { at = 12.4, market = "Oxford, Mississippi" } = {}) {
  const bar = el("div", "endcard-bar", parent, { zIndex: 60 });
  const left = el("div", "mctv-mark", bar);
  left.textContent = "MCTV Elite Advertising";
  const right = el("div", "fine", bar, {
    fontSize: "19px",
    letterSpacing: "0.22em",
    color: "rgba(255,255,255,0.62)",
    textTransform: "uppercase",
  });
  right.textContent = market;

  return {
    seek(t) {
      const p = seg(t, at, at + 0.55);
      bar.style.transform = `translate3d(0, ${tw(
        t,
        at,
        at + 0.55,
        96,
        0,
        ease.out
      )}px, 0)`;
      bar.style.opacity = String(p);
    },
  };
}

/* ------------------------------------------------------------ shot flash -- */

/**
 * A hard white flash used on cuts. Sports motion graphics live on these —
 * they hide the seam between two ideas and read as impact.
 */
export function flash(parent) {
  const node = el("div", "layer", parent, {
    zIndex: 55,
    background: "#fff",
    opacity: "0",
    mixBlendMode: "screen",
    pointerEvents: "none",
  });
  return {
    /** Call with the cut times; the sharpest flash is a fast asymmetric decay. */
    seek(t, cuts = []) {
      let v = 0;
      for (const c of cuts) {
        if (t >= c && t < c + 0.24) {
          v = Math.max(v, Math.pow(1 - (t - c) / 0.24, 2.4) * 0.82);
        }
      }
      node.style.opacity = String(v);
    },
  };
}
