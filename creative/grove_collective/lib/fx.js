/* MCTV Digital, Inc. — Proprietary.
   Grove Collective campaign — hype effects layer.

   Everything in here exists to make a beat HIT: confetti on the payoff, a
   broadcast impact hit on cuts (radial pop + chromatic split + camera kick),
   pennant bunting, red shockwaves. All deterministic — seeded randomness
   only, pure functions of t — so renders stay reproducible. */

import { el, rng, clamp, seg, lerp, ease } from "./spot-engine.js";

/* -------------------------------------------------------------- confetti -- */

/**
 * A seeded confetti burst. Call `seek(t)` every frame; particles fly on the
 * configured `at` second and are gone ~2.6s later. Red / powder / cream
 * rectangles with tumble — reads as a stadium celebration, not a birthday.
 */
export function confetti(parent, { at = 6.0, seed = 99, count = 130, zIndex = 30 } = {}) {
  const layer = el("div", "layer", parent, { zIndex, pointerEvents: "none" });
  const rand = rng(seed);
  const colors = ["#e8243a", "#a5c8e1", "#f4f1ea", "#ce1126", "#ffffff"];
  const parts = [];

  for (let i = 0; i < count; i++) {
    const w = lerp(10, 26, rand());
    const node = el("div", null, layer, {
      position: "absolute",
      width: `${w}px`,
      height: `${w * lerp(0.35, 0.7, rand())}px`,
      background: colors[Math.floor(rand() * colors.length)],
      opacity: "0",
      willChange: "transform, opacity",
    });
    parts.push({
      node,
      /* Launch from two cannons at the lower corners, crossing the frame. */
      fromLeft: rand() < 0.5,
      x0: 0,
      vx: lerp(500, 1450, rand()),
      vy: lerp(-2400, -1150, rand()),
      spin: lerp(-720, 720, rand()),
      tumble: lerp(2, 7, rand()),
      delay: rand() * 0.22,
      life: lerp(1.7, 2.6, rand()),
    });
  }
  for (const p of parts) {
    p.x0 = p.fromLeft ? lerp(-60, 240, rand()) : lerp(1680, 1980, rand());
    if (!p.fromLeft) p.vx = -p.vx;
  }

  return {
    seek(t) {
      const lt = t - at;
      for (const p of parts) {
        const a = lt - p.delay;
        if (a <= 0 || a > p.life) {
          p.node.style.opacity = "0";
          continue;
        }
        /* Ballistic arc with gravity; drag eases the horizontal run. */
        const drag = 1 - Math.min(a * 0.35, 0.72);
        const x = p.x0 + p.vx * a * drag;
        const y = 1120 + p.vy * a + 1750 * a * a;
        const rot = p.spin * a;
        const flutter = Math.sin(a * p.tumble * 3.1) /* paper flip */;
        p.node.style.opacity = String(clamp(1 - seg(a, p.life - 0.5, p.life)));
        p.node.style.transform = `translate3d(${x}px, ${y}px, 0) rotate(${rot}deg) scaleY(${flutter})`;
      }
    },
  };
}

/* ------------------------------------------------------------ impact hit -- */

/**
 * Broadcast impact on cuts: radial white pop with a red bleed at the edge,
 * a 4-frame chromatic split, and a physical camera kick (scale jolt + shake
 * translate via the --jolt / --shakeX / --shakeY hooks on #stage).
 *
 * Cuts may be plain numbers or `{ t, color: 'red', k: 1.4 }` — `color:'red'`
 * makes the pop hit Ole Miss red (the money moment), `k` scales strength.
 */
export function impact(stage, parent) {
  const popWhite = el("div", "layer", parent, {
    zIndex: 55,
    background:
      "radial-gradient(circle at 50% 50%, rgba(255,255,255,0.95) 0%, rgba(232,36,58,0.45) 60%, transparent 82%)",
    opacity: "0",
    mixBlendMode: "screen",
    pointerEvents: "none",
  });
  const popRed = el("div", "layer", parent, {
    zIndex: 55,
    background:
      "radial-gradient(circle at 50% 50%, rgba(255,120,134,0.9) 0%, rgba(232,36,58,0.75) 55%, transparent 82%)",
    opacity: "0",
    mixBlendMode: "screen",
    pointerEvents: "none",
  });
  /* Two tinted ghost planes shifted opposite ways fake chromatic aberration
     without filters (filters on the full stage are too slow at 1080p). */
  const ghostR = el("div", "layer", parent, {
    zIndex: 54, background: "rgba(232,36,58,0.5)", opacity: "0",
    mixBlendMode: "screen", pointerEvents: "none",
  });
  const ghostB = el("div", "layer", parent, {
    zIndex: 54, background: "rgba(90,160,255,0.5)", opacity: "0",
    mixBlendMode: "screen", pointerEvents: "none",
  });

  return {
    seek(t, cuts = []) {
      let white = 0, red = 0, split = 0, kick = 0, ks = 0;
      for (const c of cuts) {
        const ct = typeof c === "number" ? c : c.t;
        const k = typeof c === "number" ? 1 : c.k ?? 1;
        const isRed = typeof c !== "number" && c.color === "red";
        if (t >= ct && t < ct + 0.12) {
          const v = Math.pow(1 - (t - ct) / 0.12, 3) * 0.55 * k;
          if (isRed) red = Math.max(red, v * 1.25);
          else white = Math.max(white, v);
        }
        if (t >= ct && t < ct + 0.14) {
          split = Math.max(split, (1 - (t - ct) / 0.14) * k);
        }
        if (t >= ct && t < ct + 0.2) {
          const decay = Math.pow(1 - (t - ct) / 0.2, 2) * k;
          if (decay > kick) {
            kick = decay;
            ks = t - ct;
          }
        }
      }
      popWhite.style.opacity = String(clamp(white));
      popRed.style.opacity = String(clamp(red));
      ghostR.style.opacity = String(clamp(split * 0.55));
      ghostB.style.opacity = String(clamp(split * 0.55));
      ghostR.style.transform = `translate3d(${split * 14}px, 0, 0)`;
      ghostB.style.transform = `translate3d(${-split * 14}px, 0, 0)`;
      /* Physical hit: scale jolt plus a decaying lateral shake. */
      stage.style.setProperty("--jolt", String(1 + kick * 0.035));
      stage.style.setProperty("--shakeX", `${Math.sin(ks * 140) * 6 * kick}px`);
      stage.style.setProperty("--shakeY", `${Math.cos(ks * 110) * 4 * kick}px`);
    },
  };
}

/* ------------------------------------------------------------ shockwave  -- */

/** A red ring that detonates outward from a point — put it under a number. */
export function shockwave(parent, { at, x = 960, y = 540, zIndex = 21 } = {}) {
  const node = el("div", null, parent, {
    position: "absolute",
    left: `${x - 300}px`,
    top: `${y - 300}px`,
    width: "600px",
    height: "600px",
    border: "3px solid rgba(232,36,58,0.9)",
    borderRadius: "50%",
    opacity: "0",
    zIndex: String(zIndex),
    pointerEvents: "none",
    willChange: "transform, opacity",
  });
  return {
    seek(t) {
      const p = seg(t, at, at + 0.65);
      if (p <= 0 || p >= 1) {
        node.style.opacity = "0";
        return;
      }
      node.style.opacity = String((1 - p) * 0.9);
      node.style.transform = `scale(${lerp(0.2, 2.6, ease.out(p))})`;
    },
  };
}

/* -------------------------------------------------------------- pennants -- */

/**
 * A string of little triangle pennants across the top of frame — game-day
 * bunting. Subtle sway; used on the lockup so the close feels like the
 * tailgate, not a title card.
 */
export function pennants(parent, { y = 54, seed = 7, zIndex = 28 } = {}) {
  const layer = el("div", null, parent, {
    position: "absolute", left: "0", right: "0", top: "0",
    height: "140px", zIndex, pointerEvents: "none",
  });
  const rand = rng(seed);
  const colors = ["#ce1126", "#a5c8e1", "#f4f1ea"];
  const flags = [];
  const n = 26;
  for (let i = 0; i < n; i++) {
    const x = (i + 0.5) * (1920 / n);
    const c = colors[i % colors.length];
    const node = el("div", null, layer, {
      position: "absolute",
      left: `${x - 26}px`,
      top: `${y + Math.sin((i / n) * Math.PI) * 26}px`,
      width: "0", height: "0",
      borderLeft: "26px solid transparent",
      borderRight: "26px solid transparent",
      borderTop: `44px solid ${c}`,
      transformOrigin: "50% 0%",
      willChange: "transform, opacity",
    });
    flags.push({ node, phase: rand() * Math.PI * 2 });
  }
  /* The string itself: a soft curve drawn as a thin bar. */
  el("div", null, layer, {
    position: "absolute", left: "-2%", right: "-2%", top: `${y - 3}px`,
    height: "3px", background: "rgba(244,241,234,0.35)",
    borderRadius: "50%",
  });

  return {
    seek(t, on = 1) {
      layer.style.opacity = String(on);
      for (const f of flags) {
        f.node.style.transform = `rotate(${Math.sin(t * 1.8 + f.phase) * 7}deg)`;
      }
    },
  };
}

/* ---------------------------------------------------------- kicker chip  -- */

/** The campaign kicker as a hard red chip instead of floating tracked type. */
export function chip(parent, text, style = {}) {
  const node = el("div", null, parent, {
    display: "inline-block",
    background: "var(--red)",
    color: "var(--white)",
    fontFamily: "Oswald, sans-serif",
    fontWeight: "700",
    fontSize: "34px",
    letterSpacing: "0.3em",
    textTransform: "uppercase",
    padding: "12px 30px 12px 38px",
    transform: "skewX(-8deg)",
    boxShadow: "0 4px 30px rgba(206,17,38,0.45)",
    ...style,
  });
  const inner = el("span", null, node, { display: "inline-block", transform: "skewX(8deg)" });
  inner.textContent = text;
  return node;
}
