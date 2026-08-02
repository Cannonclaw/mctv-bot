/* MCTV Digital, Inc. — Proprietary.
   Grove Collective campaign — spot renderer.

   Renders a spot HTML to a broadcast-ready MP4 by stepping its deterministic
   timeline one frame at a time in headless Chromium and piping the frames
   into ffmpeg. Because each spot is a pure function of time, this is exact:
   no dropped frames, no timing drift, identical output on every run.

   Usage:
     node render.mjs                     # render every spot in spots/
     node render.mjs 01                  # render spots matching "01"
     node render.mjs --fps 30 --crf 16   # override encode settings

   Output lands in output/videos/grove_collective/ (gitignored). */

import { createServer } from "node:http";
import { readFile, mkdir, readdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { spawn, execSync } from "node:child_process";
import { join, extname, dirname, basename } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = join(HERE, "..", "..");
const OUT_DIR = join(REPO, "output", "videos", "grove_collective");

/* ------------------------------------------------------------- options -- */

const argv = process.argv.slice(2);
const flag = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i === -1 ? fallback : argv[i + 1];
};
const FPS = Number(flag("fps", 30));
const CRF = String(flag("crf", 17));

/* Positional args are name filters; anything consumed by a --flag is not. */
const positional = [];
for (let i = 0; i < argv.length; i++) {
  if (argv[i].startsWith("--")) { i++; continue; }
  positional.push(argv[i]);
}

/* --------------------------------------------------------- dependencies -- */

/** Playwright may live in a global install; fall back to `npm root -g`. */
async function loadPlaywright() {
  let mod;
  try {
    mod = await import("playwright");
  } catch {
    const root = execSync("npm root -g", { encoding: "utf8" }).trim();
    mod = await import(pathToFileURL(join(root, "playwright", "index.js")).href);
  }
  /* Playwright is CommonJS, so a path import lands its exports on `default`. */
  return mod.chromium ? mod : mod.default;
}

/**
 * Locate an ffmpeg with H.264 support. The ffmpeg bundled with Playwright is
 * VP8-only, so prefer a real build: $FFMPEG, then PATH, then the one shipped
 * by the imageio-ffmpeg Python wheel (`pip install imageio-ffmpeg`).
 */
function findFfmpeg() {
  if (process.env.FFMPEG) return process.env.FFMPEG;
  try {
    return execSync("command -v ffmpeg", { encoding: "utf8" }).trim();
  } catch {
    /* fall through */
  }
  try {
    return execSync(
      'python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"',
      { encoding: "utf8" }
    ).trim();
  } catch {
    throw new Error(
      "No ffmpeg with H.264 support found. Install one, or run:\n" +
        "  pip install imageio-ffmpeg\n" +
        "or point $FFMPEG at a build that has libx264."
    );
  }
}

/* ------------------------------------------------------ static file host -- */

/* Chromium refuses ES module imports over file://, so the spot is served. */
const MIME = {
  ".html": "text/html",
  ".css": "text/css",
  ".js": "text/javascript",
  ".woff2": "font/woff2",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".webp": "image/webp",
};

function serve(root) {
  return new Promise((resolve) => {
    const server = createServer(async (req, res) => {
      try {
        const rel = decodeURIComponent(req.url.split("?")[0]);
        const path = join(root, rel);
        if (!path.startsWith(root)) {
          res.writeHead(403).end();
          return;
        }
        const body = await readFile(path);
        res.writeHead(200, {
          "Content-Type": MIME[extname(path)] ?? "application/octet-stream",
        });
        res.end(body);
      } catch {
        res.writeHead(404).end("not found");
      }
    });
    server.listen(0, "127.0.0.1", () =>
      resolve({ server, port: server.address().port })
    );
  });
}

/* -------------------------------------------------------------- render  -- */

async function renderSpot(browser, port, file, ffmpeg) {
  const slug = basename(file, ".html");
  const outPath = join(OUT_DIR, `${slug}.mp4`);

  const page = await browser.newPage({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
  });
  /* Claim the timeline before any spot code runs, so the preview clock never
     starts and every frame is exactly the one we asked for. */
  await page.addInitScript(() => {
    window.__renderMode = true;
  });
  await page.goto(`http://127.0.0.1:${port}/spots/${basename(file)}`, {
    waitUntil: "load",
  });
  /* Wait for webfonts — the first second renders in a fallback face without
     this, and that is exactly the second with the biggest type on screen. */
  await page.waitForFunction("window.__ready === true", { timeout: 30000 });

  const duration = await page.evaluate("window.__duration");
  /* The spot declares its own canvas (vertical social cuts are 1080x1920). */
  const w = (await page.evaluate("window.__w")) ?? 1920;
  const h = (await page.evaluate("window.__h")) ?? 1080;
  await page.setViewportSize({ width: w, height: h });
  const total = Math.round(duration * FPS);

  const enc = spawn(ffmpeg, [
    "-y",
    "-f", "image2pipe",
    "-vcodec", "mjpeg",
    "-framerate", String(FPS),
    "-i", "-",
    "-c:v", "libx264",
    "-preset", "slow",
    "-crf", CRF,
    "-pix_fmt", "yuv420p",
    /* Closed GOP at one second keeps playout hardware happy on loop. */
    "-g", String(FPS),
    "-movflags", "+faststart",
    "-r", String(FPS),
    outPath,
  ], { stdio: ["pipe", "ignore", "pipe"] });

  let encErr = "";
  enc.stderr.on("data", (d) => (encErr += d.toString()));
  const encDone = new Promise((res, rej) =>
    enc.on("close", (code) =>
      code === 0 ? res() : rej(new Error(`ffmpeg exited ${code}:\n${encErr.slice(-1500)}`))
    )
  );

  process.stdout.write(`  ${slug}  `);
  for (let f = 0; f < total; f++) {
    /* Render mode is flagged so the preview clock never fights the seek. */
    await page.evaluate((t) => window.__seek(t), f / FPS);
    const buf = await page.screenshot({ type: "jpeg", quality: 95 });
    if (!enc.stdin.write(buf)) {
      await new Promise((r) => enc.stdin.once("drain", r));
    }
    if (f % Math.round(total / 20) === 0) process.stdout.write("▓");
  }
  enc.stdin.end();
  await encDone;
  await page.close();

  console.log(`  →  ${outPath}`);
  return outPath;
}

/* ---------------------------------------------------------------- main  -- */

const ffmpeg = findFfmpeg();
const { chromium } = await loadPlaywright();
await mkdir(OUT_DIR, { recursive: true });

const spotsDir = join(HERE, "spots");
let files = (await readdir(spotsDir)).filter((f) => f.endsWith(".html")).sort();
if (positional.length) {
  files = files.filter((f) => positional.some((p) => f.includes(p)));
}
if (!files.length) {
  console.error("No spots matched.");
  process.exit(1);
}

const { server, port } = await serve(HERE);
const browser = await chromium.launch({
  args: ["--force-color-profile=srgb", "--disable-lcd-text"],
});

console.log(`Rendering ${files.length} spot(s) at ${FPS}fps, crf ${CRF}`);
console.log(`ffmpeg: ${ffmpeg}\n`);

for (const f of files) {
  await renderSpot(browser, port, join(spotsDir, f), ffmpeg);
}

await browser.close();
server.close();
console.log(`\nDone. Files in ${OUT_DIR}`);
