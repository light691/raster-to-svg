#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const sharp = require('sharp');

function argumentsFor(values) {
  const options = { scales: '0.5,1,2' };
  const flags = new Set(['expect-opaque', 'matte-previews']);
  const named = new Set(['input', 'preview', 'report', 'scales']);
  for (let i = 0; i < values.length; i++) {
    if (values[i] === '--help') return { help: true };
    if (!values[i].startsWith('--')) throw new Error(`Unexpected argument: ${values[i]}`);
    const name = values[i].slice(2);
    if (flags.has(name)) { options[name] = true; continue; }
    if (!named.has(name) || !values[i + 1] || values[i + 1].startsWith('--'))
      throw new Error(`Unknown or missing option: ${values[i]}`);
    options[name] = values[++i];
  }
  if (!options.input || !options.preview) throw new Error('--input and --preview are required');
  if (path.extname(options.preview).toLowerCase() !== '.png') throw new Error('--preview must be a PNG');
  options.scales = [...new Set([1, ...options.scales.split(',').map(Number)])].sort((a, b) => a - b);
  if (options.scales.some(value => !Number.isFinite(value) || value <= 0 || value > 4))
    throw new Error('--scales must contain comma-separated numbers in (0, 4]');
  return options;
}

function outputPaths(options) {
  const input = path.resolve(options.input), preview = path.resolve(options.preview);
  const base = preview.slice(0, -4);
  const white = options['matte-previews'] ? `${base}-on-white.png` : null;
  const black = options['matte-previews'] ? `${base}-on-black.png` : null;
  const report = options.report ? path.resolve(options.report) : null;
  const all = [input, preview, white, black, report].filter(Boolean);
  const canonical = all.map(value => process.platform === 'win32' ? value.toLowerCase() : value);
  if (new Set(canonical).size !== canonical.length)
    throw new Error('Source, previews and report must have distinct paths');
  return { input, preview, white, black, report };
}

function checkStandalone(svg) {
  const body = svg.replace(/<!--[\s\S]*?-->/g, '');
  if (/<\s*(?:[\w-]+:)?(?:image|foreignObject|script)\b/i.test(body))
    throw new Error('This full-vector preview helper rejects raster or active content');
  if (/<!DOCTYPE|<!ENTITY/i.test(body)) throw new Error('DTD/entity declarations are unsupported');
  for (const match of body.matchAll(/\b(?:xlink:)?href\s*=\s*["']([^"']*)["']/gi))
    if (!match[1].startsWith('#')) throw new Error('External resource reference');
  for (const match of body.matchAll(/url\(\s*["']?([^\s)"']+)/gi))
    if (!match[1].startsWith('#')) throw new Error('External CSS resource reference');
}

async function writeBuffer(file, buffer) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  await fs.promises.writeFile(file, buffer);
}

async function main() {
  const options = argumentsFor(process.argv.slice(2));
  if (options.help) {
    console.log('Usage: node preview_svg.cjs --input FILE.svg --preview FILE.png [--expect-opaque] [--scales 0.5,1,2] [--matte-previews] [--report FILE.json]');
    console.log('Measures alpha before compositing. Opaque expectation failures exit with status 2. Native size is always included.');
    return;
  }
  const files = outputPaths(options);
  if (path.extname(files.input).toLowerCase() !== '.svg') throw new Error('--input must be an SVG');
  const svg = fs.readFileSync(files.input);
  checkStandalone(svg.toString('utf8'));
  const native = await sharp(svg, { density: 72 }).metadata();
  if (native.format !== 'svg') throw new Error('Input content is not SVG');
  if (!native.width || !native.height) throw new Error('SVG dimensions are unavailable');
  const renders = [];
  let nativeRaw = null, nativeInfo = null;
  for (const scale of options.scales) {
    const pixels = Math.ceil(native.width * scale) * Math.ceil(native.height * scale);
    if (pixels > 40000000) throw new Error(`Render at scale ${scale} exceeds 40 million pixels; use a crop or smaller scale`);
    const { data, info } = await sharp(svg, { density: 72 * scale })
      .toColourspace('srgb').ensureAlpha().raw().toBuffer({ resolveWithObject: true });
    let alphaMin = 255, alphaTotal = 0, nonopaque = 0;
    for (let i = 3; i < data.length; i += 4) {
      const alpha = data[i];
      if (alpha < alphaMin) alphaMin = alpha;
      alphaTotal += alpha;
      if (alpha !== 255) nonopaque++;
    }
    const count = info.width * info.height;
    renders.push({ scale, width: info.width, height: info.height,
      alpha_min: alphaMin, alpha_mean: +(alphaTotal / count).toFixed(6),
      nonopaque_pixels: nonopaque, fully_opaque: nonopaque === 0 });
    if (scale === 1) { nativeRaw = data; nativeInfo = info; }
  }
  const raw = { width: nativeInfo.width, height: nativeInfo.height, channels: 4 };
  await writeBuffer(files.preview, await sharp(nativeRaw, { raw }).png().toBuffer());
  if (files.white) {
    await writeBuffer(files.white, await sharp(nativeRaw, { raw }).flatten({ background: '#ffffff' }).png().toBuffer());
    await writeBuffer(files.black, await sharp(nativeRaw, { raw }).flatten({ background: '#000000' }).png().toBuffer());
  }
  const report = { input: files.input, preview: files.preview, white_preview: files.white,
    black_preview: files.black, renderer: 'Sharp/librsvg', expect_opaque: !!options['expect-opaque'],
    coverage_pass: !options['expect-opaque'] || renders.every(render => render.fully_opaque), renders };
  if (files.report) await writeBuffer(files.report, Buffer.from(JSON.stringify(report, null, 2) + '\n'));
  console.log(JSON.stringify(report));
  if (!report.coverage_pass) {
    console.error('Opaque coverage failed: transparent pixels remain. Inspect seams before delivery.');
    process.exitCode = 2;
  }
}

main().catch(error => { console.error(error.message); process.exitCode = 1; });
