const { chromium } = require("playwright");
const path = require("path");

const jobs = [
  { file: "art_cover.html", out: "art_cover.png", w: 1920, h: 1080 },
  { file: "art_map.html", out: "art_map.png", w: 1920, h: 1080 },
  { file: "art_moments.html", out: "art_moments.png", w: 1920, h: 640, transparent: true },
];

(async () => {
  const browser = await chromium.launch({
    executablePath: "/opt/pw-browsers/chromium",
    args: ["--disable-gpu", "--no-sandbox"],
  });
  for (const j of jobs) {
    const page = await browser.newPage({ viewport: { width: j.w, height: j.h } });
    await page.goto("file://" + path.join(__dirname, j.file));
    await page.waitForTimeout(700);
    await page.screenshot({
      path: path.join(__dirname, j.out),
      omitBackground: !!j.transparent,
    });
    console.log("WROTE", j.out);
    await page.close();
  }
  await browser.close();
})();
