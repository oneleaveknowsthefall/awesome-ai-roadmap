import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { localPath, render, tiles, validateJob } from "./render.mjs";

test("detail tiles preserve the entire large figure, with overlap", () => {
  assert.deepEqual(tiles(400, 400), []);
  const panels = tiles(1300, 1700);
  assert.equal(panels.length, 9);
  assert.equal(Math.max(...panels.map((p) => p.x + p.width)), 1300);
  assert.equal(Math.max(...panels.map((p) => p.y + p.height)), 1700);
  assert.ok(panels.every((p) => p.width <= 560 && p.height <= 880));
  assert.throws(() => localPath("http://localhost/%2e%2e%2fsecret"), /escapes/);
  assert.throws(() => validateJob({
    key: "a".repeat(64), kind: "mermaid",
    source: 'flowchart LR\n A["<img src=\\"https://example.org/image.png\\">"]',
  }), /explicit static conversion/);
});

test("real offline Chinese diagram and math, deduplicated cache, and hard math errors", async () => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "epub-render-test-"));
  try {
    const request = path.join(directory, "jobs.json");
    const jobs = [
      { kind: "mermaid", source: 'flowchart LR\n A["中文：检索"] --> B["生成"]' },
      { kind: "inline", source: "x_i^2" },
      { kind: "display", source: "\\frac{e^{z_i}}{\\sum_j e^{z_j}}" },
    ].map((job) => ({ ...job, key: createHash("sha256").update(job.kind + "\0" + job.source).digest("hex") }));
    await fs.writeFile(request, JSON.stringify(jobs));
    const first = await render(request, directory);
    assert.equal(first.results.length, 3);
    assert.equal(first.network_requests_blocked, 0);
    for (const image of first.results) {
      const png = await fs.readFile(path.join(directory, image.file));
      assert.equal(png.subarray(1, 4).toString(), "PNG");
      assert.ok(image.width > 10 && image.height > 10);
      if (image.kind !== "mermaid") {
        assert.equal(image.svgCount, 1, "capture exactly one rendered formula");
        assert.equal(image.mathmlCount, 0, "assistive MathML must not be visibly captured");
      }
    }
    assert.deepEqual(await render(request, directory), first);
    await fs.writeFile(path.join(directory, `${jobs[0].key}.json`), '{"truncated":');
    assert.deepEqual(await render(request, directory), first);
    const invalid = { kind: "inline", source: "\\notARealCommand{x}", key: "a".repeat(64) };
    await fs.writeFile(request, JSON.stringify([invalid]));
    await assert.rejects(render(request, directory), /Undefined control sequence|merror/);
  } finally {
    await fs.rm(directory, { recursive: true, force: true });
  }
});
