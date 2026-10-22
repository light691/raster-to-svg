# Reference-preserving reconstruction

## Lock the source geometry

Work in the highest-resolution source's coordinate system. Record the canvas, visible artboard, foreground bounds, principal centers, text bounds, and important curve endpoints. Preserve asymmetry that belongs to the source. A screenshot's outer margin must not accidentally shift all artwork when removed.

Identify components in drawing order: background, structural silhouette, material surfaces, decorative marks, plaques, ribbon tails and folds, front ribbon, lettering, and foreground symbols. Keep each meaningful component in a named group. Draw occluded parts simply beneath their covering shapes. Segment objects and visible boundaries, not colors alone: a cream highlight and a white opening may have similar colors but different roles. Use source-space regions and explicit local corrections where thresholding mixes adjacent objects.

A segmented visible edge is not necessarily the object's physical boundary. At overlaps, continue the concealed silhouette beneath the foreground shape instead of fitting two independently antialiased contact edges. Otherwise smoothing can open white or transparent slivers. Repair the hidden geometry while preserving the visible contour; a global outline stroke can thicken the design and conceal the wrong problem.

Before developing the shading, render a neutral-fill geometry proof from source-derived contours or measured landmarks and compare it with the reference in the same coordinates. Check the silhouettes, holes, separate shapes, and contacts, not just matching overall bounds. Do not substitute plausible freehand loops, a uniform stroked approximation, or a similar glyph for recoverable source geometry. Resolve material differences in this proof before polishing gradients.

For complex artwork, save this checkpoint separately from the shaded export. Include a same-scale edge overlay and enlarged views of ambiguous contacts; neutral fills alone can hide which edge belongs to which object. Record the unresolved locations in source coordinates and repair them before advancing. The executing agent can make this decision without asking the user to approve routine cleanup.

For repeated regressions or delegated component work, use [staged-reconstruction.md](staged-reconstruction.md): lock reviewed outlines, assemble paints without changing those outlines, and audit the canonical export. It includes reusable component assembly and source-sampled linear/radial lighting tools. Use its simple lighting models only where they explain the surface; connected metallic strokes still need a representative junction proof.

When using masks, distinguish low-saturation highlights from background holes and nearby components from parts that are actually connected. Large morphological closing or area-only hole filling can fuse separate forms or erase a real counter. Inspect the source and mask together, repairing local segmentation errors while preserving topology instead of globally thickening the artwork.

## Preserve lettering

Use the exact font only if it is identified and matches the reference. Otherwise isolate the original glyph silhouettes using color or lightness plus a spatial region. Retain antialiased boundaries and connected components above a meaningful minimum area. Inspect an overlay before tracing: missing counters, merged letters, highlights, or nearby white lines can corrupt the mask.

Trace the isolated masks with smooth contour fitting. Inkvec through the portable launcher can produce an initial outline (see [setup notes](quality-and-import.md)):

```powershell
python "<skill>/scripts/inkvec.py" "<mask.png>" -o "<outlines.svg>" --bilevel --no-background --min-area 3 --tau 2 --editability
```

This is a starting point, not a final-quality preset. A mask carries source compression and stair steps; trace settings alone may faithfully reproduce that damage. Fit long edges and curves with a tolerance smaller than the glyph's distinctive features, keeping corners and counters. For medium-size glyphs, compare approximately 0.5–2 source pixels of contour simplification, then inspect the result. Uniform broad strokes can distort the type.

For angular varsity lettering or geometric masks, `scripts/clean_mask.py` simplifies contours, robustly fits long straight edges, and intersects them at the source corners. It preserves the canvas and counter holes. It needs Python with NumPy, Pillow, and opencv-python-headless. Use this optional helper for angular forms, not rounded type or curved illustrations:

```powershell
python -m pip install numpy pillow opencv-python-headless
python "<skill>/scripts/clean_mask.py" "<black-on-white-mask.png>" "<clean-outlines.svg>" --tolerance 2.4 --blur .85 --round .3
```

Tolerance is in source pixels and should be smaller than important serifs and strokes. Compare the resulting glyphs with the source; do not increase it until small features disappear. Avoid applying a rounded autotrace to an angular varsity font merely to make it smoother. Clean edge fits can remove wobble while keeping its distinctive corners. For curved forms use a suitable Bézier fit instead.

Preserve each traced SVG's viewBox origin when integrating it. Do not reset a nonzero origin and silently shift the glyph. A counter must remain a hole: preserve contour winding or use `fill-rule="evenodd"`, including `clip-rule="evenodd"` when using the same compound path in a clip.

For rounded lettering and curved illustrations, `scripts/fit_curves.py` fits cubic Bézier contours from an isolated black-on-white mask while keeping its full canvas and holes. It requires NumPy, Pillow, SciPy and OpenCV. This provides a curved alternative to the angular helper; it cannot correct an incorrectly segmented mask.

```powershell
python "<skill>/scripts/fit_curves.py" "<mask.png>" "<outline.svg>" --tolerance .8 --sigma 1
```

The reported tolerance is relative to the smoothed contour, not a guarantee of source accuracy. Inspect the output against the source. Use less smoothing for fine features, `--corner-angle 0` for entirely smooth contours, and optional `--corners <guides.json>` containing source-space `[x,y]` pairs for distinctive tips. Review the reported discarded contours before accepting small-feature loss. Keep a separate mask for each object rather than fitting a combined color threshold across the image.

Add modest vector bevels or shadows after the silhouettes are correct. Clip shifted highlight geometry to the original outlines so edge treatments cannot change the letter shapes or spacing. Outlined letters are editable paths, not font text.

## Rebuild shapes and shading

Use lines, ellipses, and a few Bézier segments for structural forms. Match endpoints, extrema, tangent directions, and stroke widths against the source. A ribbon's arch, folds, and tails must retain the same proportions; a merely similar sports ribbon is a redesign.

Inspect tangents where lines meet curves and where fitted Bézier segments join. Coincident endpoints alone can leave a visible kink. Preserve intended tips, thorns, serifs, folds, and corners while making continuous arcs tangent-continuous. Exclude occluded edges and overlapping colors when fitting a visible source boundary; they can pull an otherwise smooth curve away from the reference.

Replace color banding with linear or radial gradients fitted to the reference's lighting and tones. Estimate colors from broad surface samples, excluding white markings, dark seams, and overlaying objects. Maintain source lighting direction. Use source-space gradients or correctly transformed gradients rather than accepting a shape transform that rotates the highlight.

Prove the shading approach on a representative curved area and a junction before repeating it across the illustration. Independent gradient strips can leave bands, diagonal seams, or a cylindrical stem apparently pasted over an integrated monogram. Match both the source silhouette and how the highlight passes through the junction.

Make this a separate lighting checkpoint when a previous trace or shaded reconstruction has failed. Fit broad highlight and shadow regions to the object's curvature, using clipped linear/radial gradients and intentional curved shading paths. Render the proof directly from SVG at native and 300–400% size. Reject flat shading, facets, bands and blotchy overlapping glows before replicating the method. Adding more unconstrained radial spots can reduce pixel error while producing a lumpy surface; it is not a replacement for following the material's form. If the proof fails, revise its construction rather than increasing density across the whole composition.

For a narrow-hue connected material that still needs source-following curved lighting, [curved-tonal-regions.md](curved-tonal-regions.md) provides an optional vector blend construction. Its color-adaptive steps avoid assuming equal brightness steps look equally smooth. Review its compound path/control-point cost and actual enlarged appearance; it does not automatically establish a practical artist master. Keep simpler surfaces in native gradients, and reduce overlapping light fields when they cause visible rounding or dithering patterns in a renderer.

Prefer a manageable set of intentional shading shapes for an editable logo. Native gradient triangles are still a dense surface approximation: matching colors across edges does not eliminate visible facets or make tens of thousands of objects easy to edit. Do not substitute a larger mesh for clean reconstruction and call the result artist-ready. A dense candidate may satisfy a request that explicitly accepts that tradeoff, with its density and residual faceting disclosed; it does not satisfy a clean professional editing-master request merely because it is full vector.

For materials such as wood or leather, use a restrained, intentional vector texture in the appropriate group and clip it to the surface. Do not turn every noisy pixel into a separate object. Match the broad grain and tonal pattern first. Texture recreation is an approximation unless its exact source geometry is known.

Use gradients and ordinary clipping for soft highlights when filter-free output matters. Do not flatten the whole composition to simulate effects. Reconstruct distinctive internal lines as smooth strokes or clean filled outlines using their original routes and varying widths where needed.

## Compare without changing the target

Compare source and result side by side at the same scale, then overlay geometry or inspect crops where the design differs. Check original wording, original glyph widths and tilt, arch depth, outer silhouette, object size and position, seam or facial feature routes, and color direction before polishing texture.

Keep both the source and prior candidates in scratch space. Put only clearly named deliverables in the output directory. Avoid calling a candidate "exact" or "final quality met" while visible design differences remain. Explain any remaining material approximation plainly.

Complete the [production review](production-review.md) on the exported file before assigning a visual readiness judgment.
