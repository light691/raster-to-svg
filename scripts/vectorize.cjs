#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { performance } = require('node:perf_hooks');
const sharp = require('sharp');
const vtracer = require('@visioncortex/vtracer');

const detail = { clustering: 'color-cluster', hierarchical: 'cutout', colorPrecision: 8,
  layerDifference: 1, filterSpeckle: 0, mode: 'spline', cornerThreshold: 60,
  lengthThreshold: 3, maxIterations: 30, spliceThreshold: 45, simplify: 0.2,
  pathPrecision: 3, optimize: 2 };
const compact = { ...detail, colorPrecision: 6, layerDifference: 8,
  filterSpeckle: 4, simplify: 0.7 };

function args(values) {
  const result = {};
  const names = new Set(['input','output','mode','preset','overlap','matte',
    'density','preview','report','options','reuse-trace']);
  for (let i = 0; i < values.length; i++) {
    if (values[i] === '--help') return { help: true };
    const key = values[i].replace(/^--/, '');
    if (!values[i].startsWith('--') || !names.has(key)) throw new Error(`Unknown option: ${values[i]}`);
    if (i + 1 >= values.length || values[i + 1].startsWith('--')) throw new Error(`Missing value: --${key}`);
    result[key] = values[++i];
  }
  return result;
}

function assertVector(svg, strict) {
  const body = svg.replace(/<!--[\s\S]*?-->/g, '');
  const forbidden = strict ? ['image','foreignObject','script','filter','mask','text','pattern','style']
    : ['image','foreignObject','script','text','pattern','style'];
  for (const tag of forbidden)
    if (new RegExp(`<\\s*(?:[\\w-]+:)?${tag}[\\s/>]`, 'i').test(body))
      throw new Error(`Unsupported content for this mode: ${tag}`);
  if (strict && /\s(?:filter|mask)\s*=/i.test(body)) throw new Error('Filter/mask attribute remains');
  for (const match of body.matchAll(/\b(?:xlink:)?href\s*=\s*["']([^"']*)["']/gi))
    if (!match[1].startsWith('#')) throw new Error('External resource reference');
  for (const match of body.matchAll(/url\(\s*["']?([^\s)"']+)/gi))
    if (!match[1].startsWith('#')) throw new Error('External CSS resource');
  if (!/<path\b/i.test(body)) throw new Error('Trace contains no paths');
}

function rootSize(svg) {
  const root = svg.match(/<svg\b[^>]*>/i)?.[0];
  if (!root) throw new Error('Missing SVG root');
  return { w: Number(root.match(/\bwidth="([\d.]+)"/)?.[1]),
    h: Number(root.match(/\bheight="([\d.]+)"/)?.[1]) };
}

function compare(source, rendered) {
  if (source.length !== rendered.length) throw new Error('QA dimensions differ');
  let white = 0, black = 0, alpha = 0;
  const pixels = source.length / 4;
  for (let i = 0; i < source.length; i += 4) {
    const a = source[i + 3] / 255, b = rendered[i + 3] / 255;
    alpha += Math.abs(source[i + 3] - rendered[i + 3]);
    for (let c = 0; c < 3; c++) {
      const x = source[i + c] * a, y = rendered[i + c] * b;
      black += Math.abs(x - y);
      white += Math.abs(x + 255 * (1 - a) - y - 255 * (1 - b));
    }
  }
  return { rgb_mae_on_white: +(white / (pixels * 3)).toFixed(4),
    rgb_mae_on_black: +(black / (pixels * 3)).toFixed(4),
    alpha_mae: +(alpha / pixels).toFixed(4) };
}

async function main() {
  const a = args(process.argv.slice(2));
  if (a.help) {
    console.log('Usage: node vectorize.cjs --input IMAGE --output FILE.svg [--mode import|fidelity] [--preset detail|compact] [--overlap PIXELS] [--matte #rrggbb|none] [--density DPI] [--options OPTIONS.json] [--reuse-trace TRACE.svg] [--preview FILE.png] [--report FILE.json]');
    return;
  }
  if (!a.input || !a.output) throw new Error('--input and --output are required');
  const input = path.resolve(a.input), output = path.resolve(a.output);
  const artifactPaths = [input, output, a.preview, a.report].filter(Boolean).map(x=>path.resolve(x).toLowerCase());
  if (new Set(artifactPaths).size !== artifactPaths.length) throw new Error('Source, SVG, preview and report must have separate paths');
  if (a['reuse-trace'] && path.resolve(a['reuse-trace']).toLowerCase() === output.toLowerCase()) throw new Error('Output must differ from reused trace');
  if (path.extname(output).toLowerCase() !== '.svg') throw new Error('Output must have .svg extension');
  const mode = a.mode || 'import';
  if (!['import','fidelity'].includes(mode)) throw new Error('Mode must be import or fidelity');
  const preset = a.preset || 'detail';
  if (!['detail','compact'].includes(preset)) throw new Error('Preset must be detail or compact');
  const density = a.density === undefined ? 72 : Number(a.density);
  if (!Number.isFinite(density) || density < 36 || density > 600) throw new Error('Density must be 36-600 dpi');
  if (a.overlap !== undefined && mode !== 'import') throw new Error('--overlap applies only to import mode');
  const started = performance.now();
  const native = await sharp(input).metadata();
  const isSvg = native.format === 'svg';
  const { data: png, info } = await sharp(input, isSvg ? { density } : {})
    .rotate().toColourspace('srgb').ensureAlpha().png().toBuffer({ resolveWithObject: true });
  const workW = info.width, workH = info.height;
  const displayW = isSvg ? native.width : workW, displayH = isSvg ? native.height : workH;
  const raw = await sharp(png).ensureAlpha().raw().toBuffer();
  let opaque = true;
  for (let i = 3; i < raw.length; i += 4) if (raw[i] !== 255) { opaque = false; break; }
  const options = { ...(preset === 'detail' ? detail : compact),
    ...(a.options ? JSON.parse(fs.readFileSync(path.resolve(a.options), 'utf8')) : {}) };
  let svg;
  if (a['reuse-trace']) {
    svg = fs.readFileSync(path.resolve(a['reuse-trace']), 'utf8');
    assertVector(svg, true);
    const size = rootSize(svg);
    if (size.w !== workW || size.h !== workH) throw new Error('Reused trace dimensions differ from normalized source');
    const viewBox = svg.match(/<svg\b[^>]*\bviewBox=["']([^"']+)["']/i)?.[1];
    if (viewBox && viewBox.trim().split(/[\s,]+/).map(Number).some((v,i)=>v !== [0,0,workW,workH][i]))
      throw new Error('Reuse requires a zero-origin VTracer viewBox; preserve other SVGs directly');
  } else svg = vtracer.convertBuffer(png, options);
  assertVector(svg, true);
  svg = svg.replace(/<svg\b[^>]*>/i,
    `<svg version="1.1" xmlns="http://www.w3.org/2000/svg" width="${displayW}" height="${displayH}" viewBox="0 0 ${workW} ${workH}">`);
  let overlap = 0, matte = null;
  if (mode === 'fidelity' && opaque) {
    const prefix = `<defs><filter id="raster_to_svg_coverage" x="0" y="0" width="${workW}" height="${workH}" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB"><feComponentTransfer><feFuncA type="linear" slope="0" intercept="1"/></feComponentTransfer></filter></defs><g filter="url(#raster_to_svg_coverage)">`;
    svg = svg.replace(/(<svg\b[^>]*>)/i, '$1' + prefix).replace(/<\/svg>\s*$/i, '</g></svg>');
  } else if (mode === 'import') {
    overlap = a.overlap === undefined ? (opaque ? 0.5 : 0) : Number(a.overlap);
    if (!Number.isFinite(overlap) || overlap < 0 || overlap > 2) throw new Error('Overlap must be 0-2 source pixels');
    if (overlap > 0) {
      svg = svg.replace(/(<svg\b[^>]*)(>)/i, `$1 stroke-width="${overlap}" stroke-linejoin="round" stroke-linecap="round"$2`);
      svg = svg.replace(/fill="(#[0-9a-f]{6})"/gi, 'fill="$1" stroke="$1"');
    }
    if (a.matte && a.matte !== 'none') {
      if (!/^#[0-9a-f]{6}$/i.test(a.matte)) throw new Error('Matte must be #rrggbb or none');
      matte = a.matte;
    } else if (a.matte !== 'none' && opaque) {
      matte = '#' + [...raw.subarray(0,3)].map(x => x.toString(16).padStart(2,'0')).join('');
    }
    if (matte) svg = svg.replace(/(<svg\b[^>]*>)/i, `$1<rect width="${workW}" height="${workH}" fill="${matte}" stroke="none"/>`);
  }
  assertVector(svg, mode === 'import');
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, svg);
  const rendered = await sharp(Buffer.from(svg)).resize(workW, workH).ensureAlpha().raw().toBuffer();
  if (a.preview) {
    const preview = path.resolve(a.preview);
    fs.mkdirSync(path.dirname(preview), { recursive: true });
    await sharp(Buffer.from(svg)).png().toFile(preview);
  }
  const report = { input, output, mode, preset, dimensions: [displayW, displayH],
    tracing_dimensions: [workW, workH], source_is_opaque: opaque,
    source_svg_retraced: isSvg && !a['reuse-trace'], reused_trace: Boolean(a['reuse-trace']),
    path_count: (svg.match(/<path\b/g) || []).length, bytes: Buffer.byteLength(svg),
    filters: (svg.match(/<filter\b/g) || []).length, overlap, matte, options,
    comparison: compare(raw, rendered), seconds: +((performance.now()-started)/1000).toFixed(2) };
  if (a.report) {
    const reportPath = path.resolve(a.report);
    fs.mkdirSync(path.dirname(reportPath), { recursive: true });
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
  }
  console.log(JSON.stringify(report));
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
