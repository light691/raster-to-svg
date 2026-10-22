# Quality and import notes

## Gradient-aware tracing

The included `scripts/bin/windows-x64/inkvec.exe` is Inkvec 0.2.6 for Windows x64, distributed with its license and notices. It supports native transparency and gradient fitting. The portable launcher resolves `INKVEC_BIN`, then PATH, then this bundled Windows x64 executable. On macOS or Linux, download the matching non-restorer CLI archive from the [official v0.2.6 release](https://github.com/logolabs/inkvec/releases/tag/v0.2.6), verify it against the release's `SHA256SUMS`, extract it, and place `inkvec` on PATH or set `INKVEC_BIN` to its absolute path. No GPU, model weights, or restoration runtime is needed. Other platforms can use VTracer or build Inkvec from its source; see the upstream build instructions.

```powershell
python "<skill>/scripts/inkvec.py" "<source.png>" -o "<output.svg>" --mode quality
python "<skill>/scripts/verify_svg.py" "<output.svg>" --strict
```

On two simple logo fixtures this preserved a blue gradient and transparent ground that a VTracer trace flattened. It remains automatic tracing: intricate artwork or damaged glyphs can require component reconstruction. Inspect every result. Inkvec does not take SVG input; render a raster-containing SVG at an appropriate resolution first. Preserve usable source vector parts instead of retracing them unnecessarily.

Inkvec can emit a viewBox beginning at `-0.5 -0.5`; preserve that origin. The verifier accepts its inert RDF metadata while still checking content and resource references.

## VTracer fallback

The helper requires Node.js 22 or newer and pinned npm dependencies:

```powershell
npm ci --prefix "<skill>/scripts" --no-audit --no-fund
node "<skill>/scripts/vectorize.cjs" --input "<source>" --output "<output.svg>" --mode import --preview "<preview.png>"
```

Resolve paths relative to this skill. Install dependencies once; use `npm install` only if the lockfile is absent. Sharp normalizes orientation and color and decodes PNG, JPEG, WebP, TIFF, and other supported inputs. It renders SVG inputs before tracing. Upscaling does not recover missing detail.

VTracer `1.0.0-alpha.4` through `@visioncortex/vtracer` produced a substantially closer match on a detailed sports logo than Python `vtracer 0.6.15` through the older MCP wrapper. This is an observed starting point, not a guarantee for other artwork.

The detail preset uses color-cluster segmentation, cutout mosaic geometry, eight-bit color precision, layer difference 1, speckle filter 0, spline curves, corner threshold 60, length threshold 3, 30 fitting iterations, splice threshold 45, simplification 0.2, coordinate precision 3, and optimizer level 2.

This retains texture through many small paths. Detailed artwork can generate hundreds of thousands of paths and tens of megabytes before optional overlap strokes. At that density, pixel-like texture can remain unsuitable for artist-quality vectorization. Use this preset only when dense texture tracing fits the request. A clean document needs reconstruction with gradients and smooth silhouettes. Import and editing may be slow on dense traces.

Aggressive color merging made shading patchy. Upscaling sometimes improved lettering but also enlarged files or worsened shading. More iterations and finer thresholds did not consistently improve fidelity. Render and select rather than assuming bigger settings are better.

For photographs whose detailed trace still looks pixelated, use the [smooth photographic shading workflow](photo-shading-and-seams.md). It replaces flat color islands with a gradient surface; it does not recover missing photographic detail. Increasing trace density or speckle thresholds alone can preserve pixel noise or merge subtle tones into large patches.

## Full-vector meaning

An SVG can contain bitmaps or effects that editors rasterize. Absence of an `image` element alone does not establish filter-free import.

Adobe documents SVG filters as raster effects: [Apply SVG filter effects in Illustrator](https://helpx.adobe.com/ae_en/illustrator/desktop/special-effects-styles/apply-filter-effects/apply-svg-filter-effects.html). Import mode avoids filters and bitmap content, using ordinary vector shapes and optional ordinary strokes. Fidelity mode can add a coverage filter.

Vector editors can import supported SVG geometry. A raster editor or an explicit rasterize workflow still produces pixels. Lettering is outlines, not font text; semantic layers and font identity are not recovered. Do not promise behavior in a particular untested app/version.

## Options

`vectorize.cjs --help` lists the supported arguments.

- `--preset detail`: high-fidelity baseline. `--preset compact`: smaller trial.
- `--options <json>` overrides engine options after the preset. Record winning settings.
- `--mode import`: no filters or embedded images. `--mode fidelity`: coverage filter only on opaque sources.
- `--overlap <px>`: same-color vector strokes in import mode. Auto is 0.5 px for opaque art and 0 for transparent art. Compare 0, 0.25 and 0.5 if seams appear. This is an appearance tradeoff, not an exact substitute for a filter.
- `--matte '#rrggbb'`: import-mode backing rectangle; auto samples the first pixel on opaque sources. `--matte none` disables it. Transparent sources get no matte by default.
- `--density <dpi>`: SVG input rendering resolution. Native output dimensions are preserved using a viewBox.
- `--reuse-trace <svg>`: reuse a prior VTracer filter-free trace, reading the source for dimensions, opacity and QA. The trace must match normalized source dimensions and use a zero-origin viewBox. It rejects filters, text, raster images and external references. Useful for comparing seam treatments without retracing. Do not pass a nonzero-origin Inkvec trace through this mode.
- `--report <json>`: parameters, dimensions, path count and measured render errors. `--preview <png>`: rendered result.

## Existing filtered or raster-wrapped SVGs

Use the SVG as `--input`, choose a useful density, and use import mode. The helper renders and retraces its appearance; it does not recover live text or semantic layers. Inspect thin strokes and shadows. Reuse a known filter-free trace when available instead of rerasterizing it.

## Validation

`verify_svg.py <file> --strict` parses XML, rejects raster and active content, rejects filters/masks/live text in strict mode, checks resource references, counts geometry and reports dimensions. Its allowlist is conservative; inspect legitimate unsupported constructs before changing it. The JSON labels its scope `structure-only` and lists visual quality, editability, and editor import as unevaluated. Its `valid` flag must not be reported as a production or artist-quality approval.

`preview_svg.cjs --input <file.svg> --preview <preview.png> --expect-opaque --scales 0.5,1,2 --matte-previews --report <qa.json>` renders through Sharp/librsvg and measures alpha before compositing. Use `--expect-opaque` only for a source that really fills the canvas opaquely. The command exits unsuccessfully if any tested render contains transparency under that expectation. White/black comparison previews expose seams that dropping the alpha channel with an RGB conversion would hide. Browser/editor checks remain separate.

For professional reconstruction or rejected-trace cleanup, use the whole-export review and separate readiness judgments in [production-review.md](production-review.md). Preview success establishes neither clean geometry nor practical editability.
