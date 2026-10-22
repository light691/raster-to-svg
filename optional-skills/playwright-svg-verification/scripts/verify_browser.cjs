#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
// A separately installed companion can reuse the core bundle's optional runtime.
const playwrightPaths = [__dirname,
  path.resolve(__dirname, '../../raster-to-svg/optional-skills/playwright-svg-verification/scripts')];
const { chromium } = require(require.resolve('playwright', { paths: playwrightPaths }));

function parse(values) {
  const a = { 'max-size': 4096 };
  for (let i = 0; i < values.length; i++) {
    if (values[i] === '--help') return { help: true };
    if (values[i] === '--headed') { a.headed = true; continue; }
    const key = values[i].slice(2);
    if (!values[i].startsWith('--') || !['input','output-dir','verifier','python','max-size'].includes(key)
        || !values[i + 1] || values[i + 1].startsWith('--')) throw Error(`Invalid option: ${values[i]}`);
    a[key] = values[++i];
  }
  if (!a.input || !a['output-dir']) throw Error('--input and --output-dir are required');
  a['max-size'] = Number(a['max-size']);
  if (!Number.isInteger(a['max-size']) || a['max-size'] < 64 || a['max-size'] > 8192)
    throw Error('--max-size must be an integer in 64..8192');
  return a;
}

async function main() {
  const a = parse(process.argv.slice(2));
  if (a.help) {
    console.log('Usage: node verify_browser.cjs --input ART.svg --output-dir DIR [--headed] [--verifier PATH] [--python PYTHON] [--max-size 4096]');
    return;
  }
  const input = path.resolve(a.input), out = path.resolve(a['output-dir']);
  if (path.extname(input).toLowerCase() !== '.svg') throw Error('--input must be an SVG');
  const verifier = a.verifier ? path.resolve(a.verifier) : [
    path.resolve(__dirname, '../../../scripts/verify_svg.py'),
    path.resolve(__dirname, '../../raster-to-svg/scripts/verify_svg.py')
  ].find(p => fs.existsSync(p));
  if (!verifier) throw Error('Core verify_svg.py not found; supply --verifier PATH');
  const guard = spawnSync(a.python || 'python', [verifier, input, '--strict'], { encoding: 'utf8' });
  if (guard.error || guard.status !== 0) throw Error(`Structural verification failed: ${guard.error || guard.stdout || guard.stderr}`);
  // Read only after the guard, and use the same bytes throughout the capture.
  const bytes = fs.readFileSync(input);
  const sourceDigest = require('node:crypto').createHash('sha256').update(bytes).digest('hex');
  const dataUrl = 'data:image/svg+xml;base64,' + bytes.toString('base64');
  const browser = await chromium.launch({ headless: !a.headed });
  try {
    const context = await browser.newContext({ deviceScaleFactor: 1, serviceWorkers: 'block' });
    await context.route('**/*', route => route.abort());
    const page = await context.newPage();
    await page.setContent('<!doctype html><html><head><style>html,body{margin:0;padding:0}img{display:block}</style></head><body><img id="art" alt="SVG verification"></body></html>');
    const size = await page.locator('#art').evaluate(async (img, url) => {
      img.src = url;
      await img.decode();
      return { width: img.naturalWidth, height: img.naturalHeight };
    }, dataUrl);
    if (!size.width || !size.height) throw Error('SVG has no usable browser dimensions');
    fs.mkdirSync(out, { recursive: true });
    const captures = [];
    for (const scale of [0.5, 1, 2]) {
      const width = Math.max(1, Math.ceil(size.width * scale));
      const height = Math.max(1, Math.ceil(size.height * scale));
      const viewport = { width: Math.min(a['max-size'], width), height: Math.min(a['max-size'], height) };
      await page.setViewportSize(viewport);
      for (const background of ['white', 'black']) {
        await page.locator('body').evaluate((body, options) => {
          body.style.background = options.background;
          const img = body.querySelector('img');
          img.style.width = `${options.width}px`;
          img.style.height = `${options.height}px`;
        }, { background, width, height });
        const name = `scale-${scale}-${background}.png`;
        const target = path.join(out, name);
        if (target.toLowerCase() === input.toLowerCase()) throw Error('Screenshot would overwrite input');
        await page.screenshot({ path: target, animations: 'disabled' });
        captures.push({ file: name, scale, background, intended_size: { width, height }, viewport,
          cropped: width > viewport.width || height > viewport.height });
      }
    }
    const digestNow = require('node:crypto').createHash('sha256').update(fs.readFileSync(input)).digest('hex');
    if (digestNow !== sourceDigest) throw Error('Input changed during capture; rerun against the saved deliverable');
    const report = { status: 'captured', input, sha256: sourceDigest,
      browser: 'Chromium', browser_version: browser.version(), dimensions: size,
      structural_check: JSON.parse(guard.stdout), captures,
      not_evaluated: ['visual_quality', 'source_fidelity', 'editor_import'] };
    fs.writeFileSync(path.join(out, 'browser-report.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
