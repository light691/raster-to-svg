---
name: raster-to-svg
description: Convert raster artwork and photographs to editable SVG while preserving the reference, or repair raster-containing SVGs. Use for image vectorization, smooth photographic shading, blocky trace cleanup, mesh seam repair, and faithful logo reconstruction.
license: MIT
metadata:
  version: "1.0.0"
  author: light691
---

# Raster to SVG

Preserve the supplied design while replacing raster roughness with clean vector geometry. An embedded bitmap, a pixel mosaic, and a new design do not meet an artist-quality reconstruction request.

## Portable setup

Resolve `<skill>` as the directory containing this file, independently of the host agent. Run `python "<skill>/scripts/setup.py"` once and use its `.venv` Python for numerical helpers; run `python "<skill>/scripts/doctor.py"` in that environment to check readiness. The [README](README.md) covers Windows, macOS, Linux and agent installation. Helpers run locally without an API key or MCP server. Use the host's file-viewing and image-inspection tools; do not assume Codex-specific tools are available.

For Inkvec, use `python "<skill>/scripts/inkvec.py"` followed by ordinary Inkvec arguments. It resolves `INKVEC_BIN`, an executable on PATH, or the included Windows x64 build. On other platforms install the upstream CLI as documented in [quality-and-import.md](references/quality-and-import.md). VTracer is a portable fallback.

## Choose the approach

- **Artist-quality reconstruction:** use for highest quality, clean curves, low-resolution logo restoration, or artist-style vectorization. Follow [references/artist-reconstruction.md](references/artist-reconstruction.md). Rebuild major shapes, retain the original lettering outlines, and model shading with gradients. Use tracing as an intermediate aid.
- **Automatic trace:** useful for quick conversion, simple artwork, or when the user prioritizes retention of raster texture. Start with the gradient-aware Inkvec engine when available. The VTracer helper is another option, but a detailed trace may retain pixel noise or flatten gradients. See [references/quality-and-import.md](references/quality-and-import.md).
- **Smooth photographic shading:** for photographs, portraits, or requests to remove blockiness from a detailed trace, see [references/photo-shading-and-seams.md](references/photo-shading-and-seams.md). The reusable photo helper fits an adaptive gradient surface and preserves source placement. This softens fine texture and can produce a large, dense document; it is an alternative to texture tracing, not a hand-reconstructed illustration.
- **Existing SVG:** preserve and edit usable vector geometry directly. If the SVG wraps a bitmap or contains effects that must be converted, reconstruct those components or render and retrace them, explaining the approximation.

When the user requests a clean professional editing master, stay on the reconstruction route. A failed trace or difficult shading does not justify substituting a whole-image photo surface. Keep a dense surface as a diagnostic reference in scratch space; it does not complete that deliverable. For complex shaded artwork, use the geometry and lighting checkpoints in the reconstruction reference before spending effort on a complete shaded export.

Use the highest-resolution supplied reference. Keep its wording, glyph shapes, composition, spacing, proportions, ribbon curves, silhouettes, colors, and relative placement. "Highest quality" authorizes cleanup, not redesign. Do not substitute a similar font when the original can be outlined from the image. Changes to the design require the user's request.

## Full-vector deliverable

For full vector, editor import, or editable artwork, use paths, ordinary SVG shapes, gradients, and clip paths. Outline lettering. Exclude bitmap images, filters, masks, live text, external resources, and scripts. A PNG preview is separate from the SVG.

Preserve useful semantic groups and source coordinates. Many tiny color islands can technically be vector yet remain unsuitable for clean editing. Vector structure and visual fidelity are separate requirements.

The optional VTracer `--mode fidelity` uses a coverage filter on opaque art. Label this as a filtered preview; it does not satisfy a filter-free full-vector request.

## Optimize every conversion

After the artwork is ready, apply [references/lossless-optimization.md](references/lossless-optimization.md) as the standard finishing sub-workflow for every conversion. Preserve the master; accept a smaller export only after structural validation and exact render comparisons. Preserve the chosen geometry, texture, shading, transparency, and useful component groups. File-size targets do not authorize approximation. Use the selected file for the final preview and checks; if optimization cannot be verified, deliver the master and report that limit.

## Inspect and refine

For artist-quality work or cleanup of a rejected trace, follow [references/production-review.md](references/production-review.md). Review the entire exported artwork, including apparently unchanged areas, after the last geometry or shading edit. A few successful detail crops do not establish whole-art readiness.

Render in the reference coordinate system and compare at native size. Use overlays or close-ups to check text, arch curves, contour widths, ball or face features, thin lines, and shading direction. Keep source-derived geometry fixed while polishing it. Account for object transforms when positioning user-space gradients; rotating a shape can accidentally rotate its lighting.

Inspect high magnification for stair steps and unwanted path islands. Straight stems should be straight and intended corners should remain corners. Do not smooth by globally thickening letters or rounding every corner. Retain counters and thin strokes.

Iterate demonstrated defects. Pixel error can help compare candidates, but it is not a percentage of design quality; a noisy trace may score better than a clean reconstruction. Never claim recovered missing detail, font identity, or a pixel-perfect texture match.

Run the structural check on a full-vector deliverable:

```powershell
python "<skill>/scripts/verify_svg.py" "<output.svg>" --strict
```

Validate a fresh preview rendered from the exact SVG being delivered. Report structural validity, visual quality/editability, and editor testing separately. The verifier's `valid` result covers structure only; it is not an artist-quality or production approval. Continue correcting demonstrated, fixable visual defects within the requested scope. Calling an inaccurate redraw a candidate and documenting its differences does not complete a faithful reconstruction. If a concrete constraint prevents completion, identify it, deliver the clearly labeled candidate, and withhold visual approval. If the requested editor is unavailable, say import is unverified without treating a browser preview as an editor test. Deliver the SVG and preview, identify meaningful approximations, and open the output folder when requested.

For dense photo surfaces, inspect the actual alpha channel and composite over white and black. When an opaque source fills the canvas, the rendered result should remain fully opaque: a plausible RGB preview can conceal transparent mesh seams. Use `scripts/preview_svg.cjs --help` for coverage checks at multiple sizes. For mesh shading or a viewer-specific line complaint, also inspect a real browser at reduced, native, and enlarged sizes. Follow the targeted seam repair in [references/photo-shading-and-seams.md](references/photo-shading-and-seams.md); applying crisp edges to an entire logo or replacing transparency with a matte can damage other artwork.

The optional [Playwright verification companion](optional-skills/playwright-svg-verification/SKILL.md) captures real Chromium views at 50%, 100% and 200% on white and black. Install it only when browser verification is useful; see [docs/browser-verification.md](docs/browser-verification.md). If unavailable, report browser verification as unperformed. Browser capture and structural validity do not replace visual inspection or editor testing.
