// Optional maintainer check: Node.js, Playwright/Chromium and a local Mermaid UMD bundle.
import { createRequire } from 'node:module';
import { readFileSync, readdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.HARNESS_PLAYWRIGHT_MODULE || 'playwright');
if (!process.env.HARNESS_MERMAID_BUNDLE) throw new Error('Set HARNESS_MERMAID_BUNDLE to a local mermaid.min.js');
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const paths = ['README.md', ...readdirSync(join(root, 'docs')).filter(p => p.endsWith('.md')).map(p => `docs/${p}`)];
const browser = await chromium.launch({
  headless: true,
  ...(process.env.HARNESS_CHROME ? { executablePath: process.env.HARNESS_CHROME } : {}),
});
try {
  const context = await browser.newContext({ offline: true, serviceWorkers: 'block' });
  await context.route('**/*', route => route.abort());
  const page = await context.newPage();
  await page.setContent('<!doctype html><html><body></body></html>');
  await page.addScriptTag({ path: process.env.HARNESS_MERMAID_BUNDLE });
  const result = await page.evaluate(async files => {
    const mermaid = window.mermaid;
    mermaid.initialize({ startOnLoad: false, securityLevel: 'strict' });
    const results = [];
    for (const { path, source } of files) {
      for (const match of source.matchAll(/```mermaid\s*\n([\s\S]*?)```/g)) {
        await mermaid.parse(match[1]);
        const { svg } = await mermaid.render(`diagram_${results.length}`, match[1]);
        if (!svg.includes('<svg')) throw new Error(`No SVG for ${path}`);
        results.push({ path, rendered: true, svgBytes: svg.length });
      }
    }
    if (!results.length) throw new Error('No Mermaid diagrams found');
    let rejectsOldSyntax = false;
    try { await mermaid.parse('flowchart TD\n brief -->|人工批准| style[style-spec]'); }
    catch { rejectsOldSyntax = true; }
    if (!rejectsOldSyntax) throw new Error('Expected the reported syntax to fail');
    return { offline: true, rejectsOldSyntax, diagrams: results };
  }, paths.map(path => ({ path, source: readFileSync(join(root, path), 'utf8') })));
  console.log(JSON.stringify(result, null, 2));
} finally {
  await browser.close();
}
