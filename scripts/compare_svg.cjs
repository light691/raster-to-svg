#!/usr/bin/env node
'use strict';
// Internal renderer for optimize_svg.py. Raw RGBA equality also preserves alpha.
const fs = require('node:fs');
const path = require('node:path');
const sharp = require('sharp');

function compare(a, b) {
  if (a.length !== b.length) throw new Error('Different buffer dimensions');
  let sum = 0, max = 0, alphaMax = 0, changed = 0;
  for (let i = 0; i < a.length; i++) {
    const delta = Math.abs(a[i] - b[i]);
    sum += delta;
    if (delta) changed++;
    if (delta > max) max = delta;
    if (i % 4 === 3 && delta > alphaMax) alphaMax = delta;
  }
  return { identical: changed === 0, rgba_mae: sum / a.length,
    max_channel_delta: max, max_alpha_delta: alphaMax, changed_channels: changed };
}

async function render(file, scale) {
  // Bound total pixels before allocating native buffers, including at native scale.
  const meta = await sharp(file, { density: 72 * scale }).metadata();
  if (!meta.width || !meta.height || meta.width * meta.height > 40000000)
    throw new Error('Missing dimensions or render exceeds 40 million pixels; reduce optional enlarged scales, or retain the master if native size exceeds the limit');
  return sharp(file, { density: 72 * scale }).toColourspace('srgb').ensureAlpha().raw()
    .toBuffer({ resolveWithObject: true });
}

async function main() {
  const manifest = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const report = { renderer: `Sharp ${sharp.versions.sharp} / librsvg ${sharp.versions.rsvg || 'unknown'}`,
    comparison: 'exact raw RGBA bytes', candidates: manifest.candidates.map(c => ({
      name: c.name, render_identical: true, renders: [] })) };
  for (const scale of manifest.scales) {
    const ref = await render(manifest.reference, scale);
    if (scale === 1) await sharp(ref.data, { raw: ref.info }).png()
      .toFile(path.join(manifest.work, 'reference.png'));
    for (let i = 0; i < manifest.candidates.length; i++) {
      const candidate = manifest.candidates[i];
      try {
        const actual = await render(candidate.path, scale);
        if (actual.info.width !== ref.info.width || actual.info.height !== ref.info.height)
          throw new Error('Canvas dimensions changed');
        const result = { scale, width: ref.info.width, height: ref.info.height, ...compare(ref.data, actual.data) };
        report.candidates[i].renders.push(result);
        report.candidates[i].render_identical &&= result.identical;
        if (scale === 1) await sharp(actual.data, { raw: actual.info }).png()
          .toFile(path.join(manifest.work, candidate.name + '.png'));
      } catch (error) {
        report.candidates[i].render_identical = false;
        report.candidates[i].renders.push({ scale, error: String(error.message || error) });
      }
    }
  }
  fs.writeFileSync(path.join(manifest.work, 'render-comparison.json'), JSON.stringify(report, null, 2));
}

main().catch(error => { process.stderr.write(String(error.stack || error)); process.exitCode = 1; });
