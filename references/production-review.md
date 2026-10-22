# Review reconstructed artwork before delivery

Use for artist-quality reconstruction, professional handoff requests, and cleanup of a result the user has rejected. Keep the review proportional to the artwork; it should catch visible defects, not turn a simple silhouette into an unrelated audit.

## Review the delivered export

Render the exact saved SVG intended for delivery. Keep its source coordinate system and compare at native size. Inspect the whole composition at reduced size, then cover every major component at enlarged size. Do not stop after the original problem areas look better. Render enlarged crops directly from the SVG; enlarging a PNG does not demonstrate vector quality.

For smooth shaded artwork, 300–400% detail views can reveal facets, kinks, and shading joins hidden by a fitted preview. Also inspect reduced, native, and enlarged browser views for mesh shading or renderer-specific seam complaints. A good result in one raster renderer can still show a grid elsewhere.

Review these distinct properties:

- **Design fidelity:** composition, proportions, glyph shapes, counters, negative spaces, stroke widths, placement, and lighting direction match the supplied design.
- **Contours and joins:** continuous arcs have smooth tangents; straight stems stay straight; intended corners and sharp tips survive; there are no accidental islands, doubled edges, or polygonal bumps.
- **Layer contacts:** inspect every crossing, fold, and foreground/background contact. Confirm that concealed shapes overlap beneath their cover, without unwanted gaps, exposed slivers, or protrusions.
- **Shading:** inspect highlights and shadows for strip bands, triangle facets, color jumps, clipped patches, flat tonal plateaus, and joins that look like separate parts pasted together. Confirm that the source's connected forms still read as connected.
- **Transparency:** inspect raw alpha and white/black composites. For a cutout, test opacity inside expected solid regions, allowing exterior antialiasing and intended holes. A source mask near a pale boundary may itself be uncertain; distinguish a contour approximation from a true internal coverage gap. A backing fill can make alpha opaque while leaving a colored mesh visible.
- **Editability:** inspect meaningful groups, outline complexity, object count, file size, and shading representation. A dense tessellation can be fully vector while remaining a poor professional editing master. Use density as evidence of an editing tradeoff, not as a universal numerical failure threshold.

## Repair demonstrated defects

Treat visible defects as work to resolve within the user's authorized scope. Follow contact gaps back to the layer geometry, contour kinks back to tangent handling, and grids back to coverage or gradient continuity. Preserve source-specific corners and negative spaces; do not globally thicken or round the design to make defects disappear.

After a repair, regenerate the preview and recheck the whole export plus affected enlarged details. Ensure a corrected overlap did not expose another edge or change the source silhouette. Cache-bust or reload a browser view when necessary so the screenshot shows the current SVG. Keep rejected candidates and diagnostic renders in scratch space rather than presenting them as current deliverables.

## Give a bounded readiness judgment

Keep three conclusions separate:

1. **Structure:** what the strict verifier actually established, such as allowed SVG content and local resources.
2. **Visual quality and editability:** what was inspected and which material defects or approximations remain. Full-vector status, a low pixel-error score, or a successful render cannot establish this judgment.
3. **Editor behavior:** which application/version was actually used to open and inspect the exported SVG, if any. When requested and available, check appearance with selections cleared, clipping, gradients, scale, and editable outlines. Otherwise state that editor import is unverified.

Do not issue a professional or production green pass while known material visual defects remain. Do not stop repairing an otherwise fixable defect merely because the structural checker passes, and do not request confirmation just to continue an already authorized cleanup. If a limitation prevents further progress, deliver the clearly labeled candidate with the remaining issue and the checks actually performed; avoid an unconditional readiness claim.
