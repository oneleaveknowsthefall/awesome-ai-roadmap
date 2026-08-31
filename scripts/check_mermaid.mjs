import fs from "node:fs";
import path from "node:path";
import { JSDOM } from "jsdom";

const dom = new JSDOM("<!doctype html><body></body>");
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.Element = dom.window.Element;
globalThis.HTMLElement = dom.window.HTMLElement;
globalThis.SVGElement = dom.window.SVGElement;
globalThis.Node = dom.window.Node;
globalThis.DOMParser = dom.window.DOMParser;

const mermaid = (await import("mermaid")).default;
mermaid.initialize({ startOnLoad: false });

const files = [];
function walk(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    if (entry.isDirectory() && ["node_modules", ".git"].includes(entry.name)) {
      continue;
    }
    const candidate = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      walk(candidate);
    } else if (entry.name.endsWith(".md")) {
      files.push(candidate);
    }
  }
}

walk(".");
let diagrams = 0;
const failures = [];
for (const file of files) {
  const source = fs.readFileSync(file, "utf8");
  const blocks = source.matchAll(/```mermaid\n([\s\S]*?)```/g);
  let index = 0;
  for (const block of blocks) {
    diagrams += 1;
    index += 1;
    try {
      await mermaid.parse(block[1]);
    } catch (error) {
      failures.push(`${file} #${index}: ${error.message.split("\n")[0]}`);
    }
  }
}

if (failures.length > 0) {
  console.error(failures.join("\n"));
  process.exitCode = 1;
}
console.log(`diagrams=${diagrams} failures=${failures.length}`);
