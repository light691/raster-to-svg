# Example images and correction history

These PNG comparison sheets were saved during raster-to-SVG development and
visual review. They include outputs from different reconstruction stages and
later v2 experiments. They are illustrative results from agent-guided work, not
a benchmark of the quick-start automatic tracing commands. The gallery adds
documentation assets; it does not change the bundled conversion helpers.

The original panels and labels are preserved. Each PNG can be opened at full
resolution from the [main README gallery](../../README.md#examples-before-after-and-corrections).

## Stretch Gillam crest

These three sheets come from the same v2 crest reconstruction and focused
letter-edge repair.

| Image | Panels and purpose |
| --- | --- |
| [Before and after](stretch-gillam-before-after.png) | Original raster on the left; v2 SVG render on the right. Compare the full wording, crest, scrollwork, and basketball. |
| [Edge corrections](stretch-gillam-edge-corrections.png) | Original raster, previous vector, and repaired vector at the same 400% display scale. Near-vertical strokes were straightened in 13 large glyph groups across 39 outline/rim/face shapes. Endpoints and the surrounding corners and counters were retained. |
| [Detail comparisons](stretch-gillam-details.png) | Source crops on the left and direct SVG renders on the right at 400%. Covers lettering, basketball curves and highlights, and arrow/trim overlap. |

The pale strips at the basketball seam junctions were present in the source and
retained. The basketball crop was unchanged by the letter-edge repair. The
reconstruction smooths source compression texture and approximates fine tonal
noise; the ball's lower curved shade transition is also an approximation.

## Gold apple emblem

The full reconstruction and its source-aligned crops belong together. The
previous/cleaned sheet records an earlier cleanup stage and is labeled separately.

| Image | Panels and purpose |
| --- | --- |
| [Before and after](apple-before-after.png) | Source raster on the left; curved vector reconstruction on the right. The unrelated dark screenshot corners are removed from the reconstruction. |
| [Earlier cleanup corrections](apple-cleanup-corrections.png) | Previous vector on the left; cleaned vector on the right. Compares the monogram join, bite overlap, and lower crossing. This is an earlier correction stage, not a crop of the later full reconstruction. |
| [Upper junction](apple-upper-junction.png) | Source and vector close-ups of the upper vine junction, thorn, and small red opening. |
| [Bite contact](apple-bite-contact.png) | Source and vector close-ups of the gold curl meeting the cream trim. |

The later full reconstruction replaced faceted shading with curved tonal regions
and refitted the leaf and upper vine against the source. Fine lighting remains
geometrically dense, so visual smoothness does not imply a compact editing master.

## Z and Camp Rock

[The comparison sheet](z-camp-rock-before-after.png) shows **two vector versions**
of each design. The original-style traces on the left retain texture and edge
irregularities. The clean reconstructions on the right remove that texture and
use simpler grouped geometry, outlined lettering, and smooth gradients. Some
contour and shading details are intentionally approximated in the clean versions.

## Scope and artwork

The images show visual comparisons and specific corrections. They do not
establish one-click conversion quality or Illustrator/Inkscape import and editing
performance. No vector-editor import result is claimed for these examples.

Reference artwork, names, logos, and trademarks remain the property of their
respective owners. Their appearance documents conversion and reconstruction
examples and does not imply endorsement. The repository's MIT license applies to
the original tooling and documentation, and does not grant rights to third-party
reference artwork.
