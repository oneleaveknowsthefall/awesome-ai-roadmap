import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import fs from "node:fs/promises";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import puppeteer from "puppeteer";

const directory = path.dirname(fileURLToPath(import.meta.url));
const epub = path.resolve(directory, "../zh-CN/generated/epub/ai-engineering-interview-zh-CN.epub");

test("actual EPUB at 375px and 16/24/32px: tables, math and code remain within the page", async () => {
  const extracted = await fs.mkdtemp(path.join(os.tmpdir(), "epub-layout-"));
  let server;
  let browser;
  const measurements = [];
  try {
    execFileSync("python3", ["-m", "zipfile", "-e", epub, extracted]);
    server = http.createServer(async (request, response) => {
      const target = path.resolve(extracted, `.${decodeURIComponent(new URL(request.url, "http://localhost").pathname)}`);
      if (!target.startsWith(extracted + path.sep)) {
        response.writeHead(403).end();
        return;
      }
      try {
        const mime = { ".xhtml": "application/xhtml+xml", ".css": "text/css", ".png": "image/png" };
        response.setHeader("Content-Type", mime[path.extname(target)] || "application/octet-stream");
        response.end(await fs.readFile(target));
      } catch (error) {
        if (error.code !== "ENOENT") throw error;
        response.writeHead(404).end();
      }
    });
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    const origin = `http://127.0.0.1:${server.address().port}`;
    browser = await puppeteer.launch({
      headless: true, args: process.env.EPUB_NO_SANDBOX === "1" ? ["--no-sandbox"] : [],
    });
    const page = await browser.newPage();
    await page.setViewport({ width: 375, height: 812 });
    await page.setRequestInterception(true);
    page.on("request", (request) => {
      if (new URL(request.url()).origin === origin) request.continue();
      else request.abort();
    });
    for (const chapter of ["ch005", "ch006", "ch019"]) {
      await page.goto(`${origin}/EPUB/text/${chapter}.xhtml`, { waitUntil: "networkidle0" });
      for (const fontSize of [16, 24, 32]) {
        const geometry = await page.evaluate(async (fontSize) => {
          document.body.style.fontSize = `${fontSize}px`;
          await document.fonts.ready;
          const formulas = Array.from(document.querySelectorAll("img.inline-math, img.display-math"));
          const sizes = formulas.map((image) => {
            const style = getComputedStyle(image);
            return {
              ratio: parseFloat(style.width) / parseFloat(style.height),
              naturalRatio: image.naturalWidth / image.naturalHeight,
              linked: image.parentElement.matches("a.formula-link"),
            };
          });
          return {
            width: document.documentElement.clientWidth,
            scrollWidth: document.documentElement.scrollWidth,
            sizes,
            overflowingCode: Array.from(document.querySelectorAll("pre"))
              .filter((block) => block.scrollWidth > block.clientWidth + 1).length,
            clipped: Array.from(document.querySelectorAll("pre, table, td, .formula"))
              .filter((element) => ["hidden", "clip"].includes(getComputedStyle(element).overflowX)).length,
          };
        }, fontSize);
        assert.ok(geometry.scrollWidth <= geometry.width + 1,
          `${chapter} font ${fontSize}: scrollWidth=${geometry.scrollWidth}, viewport=${geometry.width}`);
        assert.equal(geometry.overflowingCode, 0, `${chapter}: code wraps without truncation`);
        assert.equal(geometry.clipped, 0, `${chapter}: content is not hidden to fake a layout pass`);
        measurements.push({ chapter, fontSize, ...geometry });
        for (const image of geometry.sizes) {
          assert.ok(Math.abs(image.ratio / image.naturalRatio - 1) < 0.02, "formula must keep its aspect ratio");
          assert.ok(image.linked, "a constrained formula must open its complete image");
        }
      }
    }
    await page.goto(`${origin}/EPUB/text/ch019.xhtml`, { waitUntil: "networkidle0" });
    const target = await page.$eval("a.formula-link", (link) => link.href);
    await page.goto(target, { waitUntil: "networkidle0" });
    assert.equal(await page.$$eval("img.full-formula", (images) => images.length), 1);
    const back = await page.$eval("body > a", (link) => link.href);
    assert.match(back, /\/text\/ch019\.xhtml#formula-\d+$/);
    await page.goto(back, { waitUntil: "networkidle0" });
    assert.ok(await page.evaluate(() => Boolean(document.getElementById(location.hash.slice(1)))));
    await fs.writeFile(path.join(path.dirname(epub), "layout.json"), JSON.stringify({
      epub_sha256: createHash("sha256").update(await fs.readFile(epub)).digest("hex"),
      viewport_width: 375, passed: true, measurements,
    }, null, 2));
  } finally {
    if (browser) await browser.close();
    if (server?.listening) await new Promise((resolve) => server.close(resolve));
    await fs.rm(extracted, { recursive: true, force: true });
  }
});
