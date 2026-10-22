# Lossless SVG optimization

Apply this finishing workflow to every raster-to-SVG conversion, including original-style traces, clean reconstructions, and photographic surfaces. Preserve the approved master and generate a separate optimized candidate. An explicit request for an untouched export takes precedence.

## Preserve the intended representation

Optimize the chosen vector artwork after the last geometry or shading edit. If inspection leads to a repair, regenerate the optimized candidate and final preview. Do not retrace its preview, flatten it, remove texture, round coordinates, simplify curves, merge nearby colors, reduce mesh density, remove seam-covering strokes, or replace shading with a smaller approximation under a lossless label. Those alter the artwork and belong to a separately requested quality/size tradeoff.

Inspect what occupies the file: path data, gradient definitions and stops, duplicated geometry, unused resources, and verbose markup. An oversized clean editing master can signal a representation problem; minifying a dense mesh does not make it a manageable reconstruction. Keep the existing quality and editability requirements in force.

## Run the reusable pass

The helper uses Python's standard library, the sibling structural verifier, Node.js, and the skill's existing Sharp dependency. Run `npm ci --prefix "<skill>/scripts" --no-audit --no-fund` only if those pinned Node dependencies are missing. Pass a resolved Node executable with `--node` when it is not on PATH.

```powershell
python "<skill>/scripts/optimize_svg.py" "<master.svg>" --output "<optimized.svg>" --work-dir "<workspace>/work/svg-optimization" --preview "<optimized-preview.png>" --report "<workspace>/work/optimization-report.json"
```

The helper snapshots the input, creates isolated candidates, validates their structure, compares exact raw RGBA renders at 50%, 100%, and 200% size, and publishes the smallest smaller candidate that passes every comparison. Native size is always included. If no smaller candidate passes, it copies the unchanged master to the requested output and reports `unchanged`. If validation or rendering cannot run, it fails without publishing an unverified candidate. Keep the master and continue the underlying conversion; do not claim optimization succeeded.

The conservative passes shorten numeric spelling without rounding, compact triangle path commands with exact decimal arithmetic, prune unreachable definitions in standalone static SVGs, inherit redundant gradient attributes, shorten internal gradient IDs, and share identical unnamed shading groups. Semantic component groups and outline IDs remain intact. The renderer gate decides whether a rewrite is usable for the current artwork; a transformation's general plausibility is insufficient.

This is a bounded pass, not a mathematical search for the smallest possible SVG. Do not promise a universal size, reduction percentage, or maximum compression. Different representations have different limits. A further pass is justified by evidence of remaining redundancy; stop when candidates no longer improve size while passing the checks. Improvements to the helper should be checked against diverse fixtures, including gradients, clips, repeated groups, transparent counters, nonzero viewBox origins, and already compact artwork.

## Verify and deliver

Inspect the exact selected file's whole preview. If the optimizer's transforms introduce a renderer-specific issue, retain the master and investigate that issue. For dense meshes or existing seam complaints, also follow the browser and alpha review in the main skill. Exact raw RGBA equality preserves transparency and the tested composites; it does not establish that the source had good coverage or artwork quality.

Report source and optimized byte sizes, reduction, tested renderer/scales, structural validity, and whether editor import was tested. Say **render-identical at the tested sizes**, rather than claiming proof for all editors, renderers, zoom levels, or print workflows. Structural validation and optimization do not upgrade the source's visual-quality judgment.

Use the selected optimized SVG and its fresh preview as the deliverables. Preserve the master in scratch space or in the user's requested location. Keep intermediate candidates and diagnostic reports out of the deliverables folder.

For transport, `--svgz "<compressed.svgz>"` creates a deterministic gzip copy and verifies its decompressed bytes. A ZIP can also reduce download size. Distinguish compressed transport size from the SVG's uncompressed bytes, object count, memory use, and editability. Deliver a normal `.svg` by default; compressed SVG support and editor import are separate checks.
