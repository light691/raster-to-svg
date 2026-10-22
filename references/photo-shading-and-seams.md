# Smooth photographs and repair mesh seams

Use this route when a photographic trace has blocky shading, noisy color islands, or visible edges between tessellated shapes. Keep logo lettering and intentionally sharp artwork on the reconstruction or ordinary trace routes.

## Choose the representation

A detailed trace can contain hundreds of thousands of shapes and still look pixelated. More shapes do not guarantee smoother shading. Color merging and speckle filtering can instead flatten a cheek or shadow into a large patch. If the user wants a smoother photographic appearance, fit continuous gradients and accept a modest loss of skin, hair, and fabric texture. Preserve the expression, feature positions, silhouette, and lighting.

The `photo_to_svg.py` helper uses mild edge-preserving smoothing, an adaptive triangulation with shared vertices, and ordinary linear gradients. A second translucent gradient approximates local hue variation where needed. Its internal shared edges use `shape-rendering="crispEdges"` without overlapping strokes, to prevent transparent cracks. This remains a dense approximation, not a recovered original vector drawing or a semantic face model.

The helper needs Python with NumPy, Pillow, SciPy, and OpenCV. Check the environment first; install missing packages if necessary:

```powershell
python -m pip install numpy Pillow scipy opencv-python-headless
python "<skill>/scripts/photo_to_svg.py" --input "<photo.png>" --output "<photo-smooth.svg>" --report "<trace-report.json>"
python "<skill>/scripts/verify_svg.py" "<photo-smooth.svg>" --strict
node "<skill>/scripts/preview_svg.cjs" --input "<photo-smooth.svg>" --preview "<preview.png>" --expect-opaque --scales 0.5,1,2 --matte-previews --report "<render-report.json>"
```

`preview_svg.cjs` uses the skill's existing Sharp dependency. Its `--matte-previews` option also writes `preview-on-white.png` and `preview-on-black.png`; keep QA-only images in scratch space when they do not help the user.

The photo helper normalizes EXIF orientation and emits the original oriented dimensions with a viewBox for its working resolution. It limits tracing to 1600 px on the longer side by default. It rejects transparent input rather than silently removing its transparency; use the native-alpha trace route for cutouts. Do not use this helper on a raster-containing SVG: recover usable vectors directly or deliberately render the unsupported content first.

Useful controls, in working-image pixels:

- `--spacing 12`, `--error 1.9`, `--max-vertices 48000`, and `--iterations 12` are the detailed starting point observed to work on a portrait. They are not guarantees for all photos.
- Smaller `--spacing`, lower `--error`, or a higher vertex budget can reduce facets, at a cost in file size and rendering time. The vertex budget limits mesh vertices, not SVG object count; each triangle can use two gradients and two shapes.
- `--smoothing 1` is the mild default; lower values preserve more texture, while higher values soften it further. Compare eyes, eyelids, nostrils, lips, and important seams after changing it.
- `--max-dim 0` disables the working-resolution cap. It does not add source detail.
- `--force` explicitly permits replacing existing output/report files. Source and output paths must remain distinct.

A detailed 1344 px photograph in this workflow produced roughly 95,000 triangles and a file of tens of megabytes. A lower working-resolution cap alone can still leave a large file; reduce the vertex budget or relax the error threshold when compactness matters, then compare the visual result. Report a large file plainly and avoid promising effortless editing. Offer a compact or more illustrative version only when it helps the request. Keep the previous candidate available while comparing.

## Diagnose white or dark hairlines

Thin repeated diagonal lines usually indicate seams between adjacent shapes. First distinguish transparent gaps from actual stroke colors, gradient mismatches, or an editor's selection overlay. Reproduce them in an exported/rendered view with selections cleared. Inspect the alpha channel and compare over white and black before changing the artwork.

An RGB conversion that discards alpha can hide the defect: the color values may look plausible while the pixels remain partly transparent. Likewise, a structural SVG check cannot prove continuous coverage. In the observed photo, narrow 0.45 px overlap strokes still left alpha as low as 232/255, and a browser showed a white lattice.

For a tessellation that is intended to fill an opaque surface continuously:

1. Identify the group of shared internal triangles. Preserve exactly matching vertices at shared boundaries.
2. On that group, try `shape-rendering="crispEdges"` and remove the overlapping strokes from those triangles. This changes their coverage rasterization while leaving the gradient fills in place. Keep this treatment off lettering and exterior curved outlines. Rendering hints can vary by application, so inspect the target renderer.
3. Check raw alpha before compositing. For an opaque rectangular photo, every pixel should remain opaque at the tested sizes. For partially transparent artwork, compare coverage only where opacity is actually expected; do not force the whole canvas opaque.
4. Inspect the SVG in a real browser or the requested editor at reduced, native, and enlarged sizes (50%, 100%, and 200% are useful starting points). A Sharp/librsvg preview alone does not establish browser or editor behavior.

If there is no transparency but the mesh remains visible, inspect shared-edge colors, hue correction, coarse triangles, and gradient direction. Refine the surface where the defect occurs. If a renderer ignores the edge treatment, choose another continuous-coverage vector construction and verify it there; do not claim the hint universally fixes seams. A flat backing rectangle merely conceals white exposure and may leave a colored lattice.

Distinguish coverage seams from surface facets. Shared vertices and matching edge colors can provide continuous color while changes in gradient slope still expose triangles at high magnification. A shared material palette avoids independent color jumps but does not prove a smooth surface. Refine or soften only the demonstrated shading defect, comparing distinctive features with the reference; do not call a dense photographic surface an artist-quality logo reconstruction.

Overlap widths are scale-dependent. A narrow overlap that appears clean at native size can reveal a grid when reduced. If testing an overlap construction, keep it inside the original smooth silhouette clip and compare color as well as alpha at all target scales. Ordinary overlap strokes remain vector, but they can alter local color and do not guarantee seam-free rendering. Blur filters still violate the strict full-vector requirement. Do not promote one observed stroke width or rendering hint into a universal fix.

Deliver the SVG and a fresh rendered preview, state meaningful softening or residual faceting, and identify which renderer was actually checked. When repairing the user's existing result, update that result or use a clearly identified revised filename, then tell them to reopen/reload it if their viewer still displays a cached version.
