/* MCTV Digital, Inc. — Proprietary.
   Grove Collective campaign — reusable scene primitives.

   These build the "night game" world procedurally: light rig, crowd bowl,
   atmosphere. They exist so a spot reads as a packed stadium on a screen
   across the room without depending on cleared photography. When real
   photography is bound to a spot's slots, these sit behind it as environment
   rather than being replaced.

   Punch-up pass (critique panel, 5 reviewers): the world now carries Ole
   Miss red (jersey crowd, red light shafts, ignition underglow), the crowd
   jumps instead of swaying (jumpers, arms up, section-synced hops, rolling
   wave), the rig gained procedural yard lines, and the closing lockup is a
   single shared component with frozen geometry so all four spots end on the
   identical brand event. */

import { el, rng, clamp, seg, tw, ease, lerp } from "./spot-engine.js";

/* ------------------------------------------------------------ light rig  -- */

/**
 * Stadium light rig. `seek(t, power, bankPower, heat)`:
 *  - `power`     0..1 overall house-light level
 *  - `bankPower` optional per-bank multipliers, one per bank left to right,
 *                for snapping banks on one at a time — an empty stadium
 *                coming to life is a beat you can only get this way
 *  - `heat`      0..1 Ole Miss red takeover: red shafts + field underglow
 *                fade in over the blue rig. Drive it on the payoff so the
 *                bowl visibly ignites when the hero lands.
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
  const shaftAt = (x, i, red) =>
    el("div", null, layer, {
      position: "absolute",
      left: `${x}px`,
      top: "-180px",
      width: `${lerp(120, 260, (i % 3) / 2)}px`,
      height: "1180px",
      background: red
        ? "linear-gradient(to bottom, rgba(232,36,58,0.34) 0%, rgba(232,36,58,0.12) 40%, rgba(232,36,58,0.03) 66%, transparent 82%)"
        : "linear-gradient(to bottom, rgba(214,234,255,0.4) 0%, rgba(180,212,246,0.16) 34%, rgba(150,190,235,0.04) 62%, transparent 82%)",
      transform: `skewX(${i % 2 ? 11 : -13}deg)`,
      filter: "blur(20px)",
      mixBlendMode: "screen",
      opacity: "0",
      willChange: "opacity, transform",
    });
  const shafts = [140, 520, 980, 1420, 1760].map((x, i) => ({
    node: shaftAt(x, i, false),
    red: shaftAt(x, i, true),
    phase: i * 1.3,
    skew: i % 2 ? 11 : -13,
  }));

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

  /* Procedural yard lines under the horizon glow — the one graphic that
     instantly says FOOTBALL instead of "night event". */
  const field = el("div", null, layer, {
    position: "absolute",
    left: "-20%",
    right: "-20%",
    bottom: "0",
    height: "250px",
    background:
      "repeating-linear-gradient(90deg, rgba(214,234,255,0.32) 0 3px, transparent 3px 96px)",
    transform: "perspective(700px) rotateX(64deg)",
    transformOrigin: "50% 100%",
    maskImage: "linear-gradient(to top, rgba(0,0,0,0.8), transparent 90%)",
    WebkitMaskImage: "linear-gradient(to top, rgba(0,0,0,0.8), transparent 90%)",
    willChange: "opacity",
  });

  /* Red ignition underglow: the fire the brief asked for, off until `heat`. */
  const ember = el("div", null, layer, {
    position: "absolute",
    left: "-10%",
    right: "-10%",
    bottom: "0",
    height: "520px",
    background:
      "radial-gradient(ellipse 62% 100% at 50% 100%, rgba(232,36,58,0.42) 0%, rgba(206,17,38,0.18) 42%, transparent 75%)",
    filter: "blur(40px)",
    mixBlendMode: "screen",
    opacity: "0",
    willChange: "opacity",
  });

  return {
    seek(t, power = 1, bankPower = null, heat = 0) {
      banks.forEach((b, i) => {
        /* A slow drift keeps the flares alive between beats without ever
           calling attention to itself. */
        const drift = Math.sin(t * 0.55 + b.phase) * 46;
        const bloom = 0.78 + Math.sin(t * 1.25 + b.phase * 1.7) * 0.18;
        const p = bankPower ? clamp(bankPower[i] ?? 1) * Math.max(power, 0.9) : power;
        b.node.style.opacity = clamp(p * bloom, 0, 1);
        b.node.style.transform = `translate3d(${drift}px, 0, 0) scaleX(${lerp(
          0.82,
          1.08,
          clamp(p)
        )})`;
      });
      for (const s of shafts) {
        /* Heat pushes the shafts harder as well as redder. */
        const flick = 0.66 + Math.sin(t * (0.9 + heat * 0.7) + s.phase) * 0.24;
        const drift = Math.sin(t * 0.4 + s.phase) * lerp(22, 48, heat);
        const xf = `skewX(${s.skew}deg) translate3d(${drift}px, 0, 0)`;
        s.node.style.opacity = String(clamp(power * flick * (1 - heat * 0.55)));
        s.node.style.transform = xf;
        s.red.style.opacity = String(clamp(power * flick * heat));
        s.red.style.transform = xf;
      }
      horizon.style.opacity = String(clamp(power * 0.95));
      field.style.opacity = String(clamp(power));
      ember.style.opacity = String(clamp(heat));
    },
  };
}

/* ---------------------------------------------------------------- crowd  -- */

/** Far rows lift toward the haze so the back of the bowl doesn't read as
    hard black speckle against the lit field. */
const depthLift = (depth) => Math.pow(depth, 1.4) * 46;

/**
 * A stadium bowl of ~2,000 silhouettes in receding rows. `seek(t, fill,
 * energy, opts)`:
 *  - `fill`   0..1 reveals the crowd from the lower bowl upward
 *  - `energy` 0..1 crowd excitement. Low = restless sway. High = the bowl
 *             ROARS: jumpers hop in section-synced bursts, a wave rolls
 *             through, red jerseys saturate and shake, arms go up, a second
 *             cohort of phone lights ignites.
 *  - `opts.dormant` 0..1 paints the bowl as empty seats — dim flat-navy
 *             architecture. Cross-fade it against `fill` for the
 *             "empty stadium waking up" beat.
 *
 * @param {number} seed fixed so every render produces the identical crowd
 */
export function crowd(parent, { seed = 20260725, rows = 26, zIndex = 3 } = {}) {
  const layer = el("div", "layer", parent, { zIndex });
  const rand = rng(seed);
  const people = [];
  const bands = [];

  for (let r = 0; r < rows; r++) {
    /* Rows recede toward the top of frame: smaller, dimmer, tighter packed. */
    const depth = r / (rows - 1);
    const y = 1080 - 18 - Math.pow(depth, 0.74) * 700;
    const size = lerp(30, 8, depth);
    const count = Math.round(lerp(44, 118, depth));

    /* One near-black band per row gives the bowl mass behind the heads, so
       it reads as packed stands rather than scattered dots. */
    const band = el("div", null, layer, {
      position: "absolute",
      left: "0",
      right: "0",
      top: `${y - size * 0.6}px`,
      height: `${size * 1.25}px`,
      background: `rgba(7, 13, 30, ${lerp(0.55, 0.25, depth)})`,
      opacity: "0",
      willChange: "opacity",
    });
    bands.push({ node: band, order: clamp(depth * 0.82 + 0.12) });

    for (let c = 0; c < count; c++) {
      const jitterX = (rand() - 0.5) * (1920 / count) * 0.9;
      const x = (c + 0.5) * (1920 / count) + jitterX;
      const h = size * lerp(1.25, 1.95, rand());
      const yj = (rand() - 0.5) * size * 0.8;
      const node = el("div", null, layer, {
        position: "absolute",
        left: `${x - size / 2}px`,
        top: `${y + yj - h}px`,
        width: `${size}px`,
        height: `${h}px`,
        /* Head-and-shoulders silhouette, cheap enough to draw 2,000 of. */
        borderRadius: `${size * 0.5}px ${size * 0.5}px ${size * 0.18}px ${
          size * 0.18
        }px`,
        willChange: "opacity, transform",
      });

      const lit = rand() < 0.1;
      const person = {
        node,
        depth,
        px: x / 1920,
        /* Reveal order runs bottom-up with a little scatter so the bowl fills
           like a crowd arriving, not like a progress bar. */
        order: clamp(depth * 0.82 + rand() * 0.3),
        /* Section-quantized phase: whole blocks of seats move together like
           a student section, instead of 2,000 independent metronomes. */
        phase: Math.floor(x / 240) * 1.7 + rand() * 0.6,
        /* Phone lights: a base cohort always on, a second that only ignites
           when the bowl is roaring — the stands visibly spark brighter. */
        lit,
        lit2: !lit && rand() < 0.12,
        /* Red jerseys — the fanbase, not a graphics choice. Saturate and
           shake with energy so red floods the bowl as the spot heats up. */
        jersey: !lit && rand() < 0.26,
        /* Jumpers: near-bowl fans who leave their seats at high energy. */
        jumper: depth < 0.55 && rand() < 0.14,
        tone: rand(),
        arms: null,
      };

      /* Raised arms on a slice of the near rows — sprout at high energy. */
      if (depth < 0.4 && rand() < 0.1) {
        person.arms = [-0.32, 1.04].map((fx) =>
          el("div", null, node, {
            position: "absolute",
            left: `${fx * size}px`,
            top: `${-h * 0.52}px`,
            width: `${size * 0.24}px`,
            height: `${h * 0.62}px`,
            borderRadius: `${size * 0.12}px`,
            background: "inherit",
            transformOrigin: "50% 100%",
            opacity: "0",
            willChange: "opacity, transform",
          })
        );
      }
      people.push(person);
    }
  }

  return {
    node: layer,
    seek(t, fill = 1, energy = 1, opts = {}) {
      const dormant = clamp(opts.dormant ?? 0);
      const roar = clamp((energy - 0.7) / 0.3); /* 0 until 0.7, 1 at full */

      for (const b of bands) {
        b.node.style.opacity = String(
          Math.max(clamp((fill - b.order) * 8), dormant * 0.5)
        );
      }

      for (const p of people) {
        /* Each silhouette has its own short fade-in around its order point. */
        const on = clamp((fill - p.order) * 10);
        if (on <= 0 && dormant <= 0) {
          p.node.style.opacity = "0";
          continue;
        }

        /* Empty-seat architecture: flat dim navy, no motion. */
        if (dormant > on) {
          p.node.style.opacity = String(0.085 * dormant);
          p.node.style.background = "#1a2c55";
          p.node.style.boxShadow = "none";
          p.node.style.transform = "none";
          if (p.arms) for (const a of p.arms) a.style.opacity = "0";
          continue;
        }

        /* Motion: an asymmetric hop (fast up, hang, drop) reads as jumping;
           a plain sine reads as a screensaver. Jumpers spike above it, and
           a slow wave rolls the whole bowl left to right. */
        const hopBase = Math.pow(
          Math.max(0, Math.sin(t * 3.1 + p.phase)),
          1.5
        );
        let dy = -hopBase * lerp(10, 3, p.depth) * energy;
        if (p.jumper && energy > 0.55) {
          dy -=
            Math.pow(Math.max(0, Math.sin(t * 2.2 + p.phase)), 7) *
            17 *
            energy;
        }
        dy -=
          (Math.sin(t * 1.4 - p.px * 6.28) * 5 + 5) *
          0.5 *
          energy *
          (1 - p.depth * 0.5);
        let dx = 0;

        if (p.lit || (p.lit2 && roar > 0)) {
          /* Phone lights twinkle out of phase with the bob. */
          const flick = 0.55 + Math.sin(t * 4.3 + p.phase * 2.1) * 0.45;
          const ign = p.lit ? 1 : roar;
          p.node.style.background = `rgba(255, 248, 226, ${(0.55 + flick * 0.45) * ign})`;
          p.node.style.boxShadow = `0 0 ${lerp(12, 44, flick)}px rgba(255,238,196,${
            0.75 * flick * ign
          })`;
          p.node.style.opacity = String(on * (0.7 + flick * 0.3) * Math.max(ign, 0.4));
        } else if (p.jersey) {
          /* Desaturated crimson at rest, saturating toward hot red as the
             bowl heats up; at full roar they shake like pompoms. */
          const rBase = lerp(130, 58, p.depth) + depthLift(p.depth) * 0.4;
          const r = Math.round(lerp(rBase, 210, energy * 0.55));
          p.node.style.background = `rgb(${r}, ${Math.round(r * 0.17)}, ${Math.round(
            r * 0.24
          )})`;
          p.node.style.boxShadow =
            roar > 0
              ? `0 0 18px rgba(232,36,58,${0.5 * roar})`
              : "none";
          p.node.style.opacity = String(on * lerp(0.95, 0.5, p.depth));
          if (roar > 0) dx = Math.sin(t * 9 + p.phase) * 3 * roar;
        } else {
          /* Unlit heads read as dark silhouettes cut against the lit field
             behind them — the near rows nearly black, the far rows hazing
             out into the atmosphere. */
          const shade = lerp(10, 52, p.tone) + depthLift(p.depth);
          p.node.style.background = `rgb(${Math.round(shade * 0.55)}, ${Math.round(
            shade * 0.8
          )}, ${Math.round(shade + 30)})`;
          p.node.style.boxShadow = "none";
          p.node.style.opacity = String(on * lerp(0.96, 0.5, p.depth));
        }

        p.node.style.transform = `translate3d(${dx}px, ${dy}px, 0)`;

        if (p.arms) {
          const up = clamp(roar) * on;
          for (let i = 0; i < 2; i++) {
            const a = p.arms[i];
            a.style.opacity = String(up);
            a.style.transform = `scaleY(${lerp(0.3, 1, up)}) rotate(${
              (i ? 14 : -14) + Math.sin(t * 5 + p.phase + i) * 9 * up
            }deg)`;
          }
        }
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

/* ---------------------------------------------------------------- lockup -- */

/**
 * The shared campaign lockup — THE GROVE / COLLECTIVE with frozen geometry
 * and one identical entrance across all four spots, so the ending becomes a
 * recognizable event instead of four slightly different cards. The eyebrow
 * and CTA vary per spot; nothing else may.
 */
export function lockup(parent, { at, kicker = "OLE MISS EXCLUSIVE NIL", cta, url = "THEGROVECOLLECTIVE.COM", zIndex = 26 } = {}) {
  const node = el("div", "center", parent, { zIndex });
  const kick = el("div", "kicker", node);
  kick.textContent = kicker;
  const name = el("div", "headline", node, {
    fontSize: "160px",
    marginTop: "20px",
    color: "var(--white)",
  });
  name.textContent = "THE GROVE";
  const name2 = el("div", "headline", node, {
    fontSize: "160px",
    color: "var(--red-hot)",
  });
  name2.textContent = "COLLECTIVE";
  const rule = el("div", "rule", node, {
    width: "620px",
    marginTop: "30px",
    background: "var(--powder)",
    transformOrigin: "left center",
  });
  const ctaEl = el("div", "sub", node, {
    fontSize: "48px",
    marginTop: "30px",
    color: "var(--white)",
  });
  ctaEl.textContent = cta;
  const urlEl = el("div", "fine", node, {
    fontSize: "46px",
    marginTop: "18px",
    color: "var(--white)",
    letterSpacing: "0.14em",
  });
  urlEl.textContent = url;

  return {
    node,
    seek(t) {
      const on = seg(t, at, at + 0.4);
      node.style.opacity = String(on);
      name.style.transform = `translate3d(0, ${tw(t, at, at + 0.6, 55, 0, ease.out)}px, 0)`;
      /* COLLECTIVE stamps — the campaign's signature hit. */
      name2.style.transform = `translate3d(0, ${tw(t, at + 0.08, at + 0.66, 55, 0, ease.out)}px, 0) scale(${tw(
        t,
        at + 0.35,
        at + 0.6,
        1.12,
        1,
        ease.outQuint
      )})`;
      rule.style.transform = `scaleX(${ease.out(seg(t, at + 0.5, at + 1.0))})`;
      ctaEl.style.opacity = String(seg(t, at + 0.7, at + 1.1));
      urlEl.style.opacity = String(seg(t, at + 0.9, at + 1.3));
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
 * Legacy soft flash. Prefer fx.impact() — it hits harder (radial pop, red
 * bleed, chromatic split, camera kick). Kept for compatibility.
 */
export function flash(parent) {
  const node = el("div", "layer", parent, {
    zIndex: 55,
    background:
      "radial-gradient(circle at 50% 50%, rgba(255,255,255,0.95) 0%, rgba(232,36,58,0.5) 62%, transparent 82%)",
    opacity: "0",
    mixBlendMode: "screen",
    pointerEvents: "none",
  });
  return {
    seek(t, cuts = []) {
      let v = 0;
      for (const c of cuts) {
        if (t >= c && t < c + 0.12) {
          v = Math.max(v, Math.pow(1 - (t - c) / 0.12, 3) * 0.55);
        }
      }
      node.style.opacity = String(v);
    },
  };
}
