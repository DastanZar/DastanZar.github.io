const { chromium } = require("playwright-core");
const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");

(async () => {
  const root = "C:/Users/abhinav.chauhan_ultr/mlsys-site";
  const url = pathToFileURL(path.join(root, "index.html")).href + "?static=1";
  const browser = await chromium.launch({
    executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    headless: true,
    args: ["--disable-gpu", "--hide-scrollbars"],
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  await page.goto(url, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(400);

  const report = await page.evaluate(() => {
    const missingAnchors = [];
    for (const a of document.querySelectorAll('a[href^="#"]')) {
      const id = decodeURIComponent(a.getAttribute("href").slice(1));
      if (id && !document.getElementById(id)) missingAnchors.push(a.getAttribute("href"));
    }
    const ids = [...document.querySelectorAll("[id]")].map((n) => n.id);
    const duplicateIds = [...new Set(ids.filter((id, index) => ids.indexOf(id) !== index))];
    const localRefs = [];
    for (const el of document.querySelectorAll("img[src], script[src], link[href], source[src], video[src], video[poster]")) {
      const ref = el.getAttribute("src") || el.getAttribute("href") || el.getAttribute("poster");
      if (!ref || /^(https?:|data:|mailto:|#)/.test(ref)) continue;
      localRefs.push({ tag: el.tagName, ref, ok: true });
    }
    const tabs = [...document.querySelectorAll("[data-receipt]")];
    const receipts = window.RECEIPTS || {};
    return {
      missingAnchors,
      duplicateIds,
      localRefs,
      receiptTabs: tabs.length,
      receiptKeys: Object.keys(receipts),
      tabsMissingReceipt: tabs.map((t) => t.dataset.receipt).filter((key) => !(key in receipts)),
      brokenImages: [...document.images].filter((img) => !img.complete || img.naturalWidth === 0).map((img) => img.getAttribute("src")),
      title: document.title,
      h1: document.querySelector("h1")?.innerText.replace(/\s+/g, " "),
      figure: Boolean(document.querySelector("[data-ink-figure]")),
      stage: Boolean(document.querySelector("[data-ink-stage]")),
      tab: Boolean(document.querySelector("[data-ink-tab]")),
    };
  });

  for (const ref of report.localRefs) {
    const clean = decodeURIComponent(ref.ref.split("?")[0].split("#")[0]);
    const target = path.join(root, clean);
    ref.ok = fs.existsSync(target);
  }

  for (const [key, receipt] of Object.entries(await page.evaluate(() => window.RECEIPTS || {}))) {
    for (const field of ["label", "source", "project", "data"]) {
      if (!(field in receipt)) {
        errors.push(`receipt ${key} missing ${field}`);
      }
    }
  }

  report.errors = errors;
  report.allLocalRefsExist = report.localRefs.every((ref) => ref.ok);
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
})();
