const { chromium } = require("playwright");
const path = require("path");
(async () => {
  const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium", args: ["--disable-gpu","--no-sandbox"] });
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  await p.goto("file://" + path.join(__dirname, "market_ticker.html"));
  await p.waitForTimeout(5200); // intro gone
  // freeze the tape at a clean offset: promo chip fully visible, no clipped fragment at the cap edge
  await p.evaluate(() => {
    const t = document.getElementById("tape");
    t.style.animation = "none";
    t.style.transform = "translateX(-1150px)";
  });
  await p.waitForTimeout(300);
  await p.screenshot({ path: path.join(__dirname, "frame_product.png") });
  console.log("WROTE frame_product.png");
  await b.close();
})();
