/* MCTV Digital, Inc. — Proprietary.
   Grove Collective campaign — key-frame grabber.

   Pulls stills out of a spot's timeline without sitting through a full render.
   Use it to check a beat, to pull a static frame for a proposal or a social
   post, or to review a change in seconds instead of minutes.

   Usage:
     node frames.mjs 01                       # default review times
     node frames.mjs 01 --at 1.2,5.8,9.4      # specific seconds
     node frames.mjs --all --scale 0.5        # every spot, half size

   Output lands in output/videos/grove_collective/frames/ (gitignored). */

import { createServer } from "node:http";
import { readFile, mkdir, readdir } from "node:fs/promises";
import { execSync } from "node:child_process";
import { join, extname, dirname, basename } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = join(HERE, "..", "..", "output", "videos", "grove_collective", "frames");

const argv = process.argv.slice(2);
const flag = (n, d) => {
  const i = argv.indexOf(`--${n}`);
  return i === -1 ? d : argv[i + 1];
};
const positional = [];
for (let i = 0; i < argv.length; i++) {
  if (argv[i].startsWith("--")) {
    /* --all is a bare switch; every other flag consumes its value. */
    if (argv[i] !== "--all") i++;
    continue;
  }
  positional.push(argv[i]);
}

/* Spread across the runtime by default: one frame inside each major beat. */
const times = String(flag("at", "1.4,3.8,6.4,9.0,10.6,13.4"))
  .split(",")
  .map(Number);
const scale = Number(flag("scale", 1));

async function loadPlaywright() {
  let mod;
  try {
    mod = await import("playwright");
  } catch {
    const root = execSync("npm root -g", { encoding: "utf8" }).trim();
    mod = await import(pathToFileURL(join(root, "playwright", "index.js")).href);
  }
  return mod.chromium ? mod : mod.default;
}

const MIME = {
  ".html": "text/html",
  ".css": "text/css",
  ".js": "text/javascript",
  ".woff2": "font/woff2",
  ".jpg": "image/jpeg",
  ".png": "image/png",
  ".webp": "image/webp",
};

function serve(root) {
  return new Promise((resolve) => {
    const server = createServer(async (req, res) => {
      try {
        const path = join(root, decodeURIComponent(req.url.split("?")[0]));
        if (!path.startsWith(root)) return res.writeHead(403).end();
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

const { chromium } = await loadPlaywright();
await mkdir(OUT_DIR, { recursive: true });

let files = (await readdir(join(HERE, "spots")))
  .filter((f) => f.endsWith(".html"))
  .sort();
if (positional.length) {
  files = files.filter((f) => positional.some((p) => f.includes(p)));
}

const { server, port } = await serve(HERE);
const browser = await chromium.launch({ args: ["--force-color-profile=srgb"] });

for (const file of files) {
  const slug = basename(file, ".html");
  const page = await browser.newPage({
    viewport: {
      width: Math.round(1920 * scale),
      height: Math.round(1080 * scale),
    },
    deviceScaleFactor: 1,
  });
  /* Same contract as render.mjs: take the timeline before the spot boots. */
  await page.addInitScript(() => {
    window.__renderMode = true;
  });
  await page.goto(`http://127.0.0.1:${port}/spots/${file}`, { waitUntil: "load" });
  await page.waitForFunction("window.__ready === true", { timeout: 30000 });
  /* The spot declares its own canvas (vertical social cuts are 1080x1920). */
  const w = (await page.evaluate("window.__w")) ?? 1920;
  const h = (await page.evaluate("window.__h")) ?? 1080;
  await page.setViewportSize({
    width: Math.round(w * scale),
    height: Math.round(h * scale),
  });

  for (const t of times) {
    await page.evaluate((s) => window.__seek(s), t);
    const name = `${slug}_t${String(t).replace(".", "-")}.jpg`;
    await page.screenshot({
      path: join(OUT_DIR, name),
      type: "jpeg",
      quality: 88,
    });
    console.log(`  ${name}`);
  }
  await page.close();
}

await browser.close();
server.close();
console.log(`\nFrames in ${OUT_DIR}`);
