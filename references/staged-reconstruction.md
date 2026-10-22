# Tool-supported reconstruction stages

Use for complex reconstructions, repeated geometry regressions, or delegated
component work. A supplied accepted outline is a stage input, not proof that an
agent independently reconstructed the source. Describe staged tests accordingly.

## Preserve accepted shapes

Prepare each reviewed component as a transparent SVG in the original canvas,
with direct filled paths or ordinary shapes. Preserve holes with explicit fill
rules. Normalize inherited transforms/styles explicitly before bundling; a
transform on an individual shape is supported. These helpers cannot judge a bad
initial mask. Review source-space edges and contacts before locking it.

A manifest lists components in drawing order:

```json
{"title":"Artwork","components":[
  {"id":"lettering","outline":"lettering.svg","fill":"#e4bd38"},
  {"id":"surface","outline":"surface.svg","paint":"surface.paint.json"}
]}
```

Use `scripts/component_bundle.py` to freeze the geometry and assemble paints:

```powershell
python "<skill>/scripts/component_bundle.py" lock "<components.json>" "<geometry.lock.json>"
python "<skill>/scripts/component_bundle.py" build "<components.json>" --lock "<geometry.lock.json>" --output "<master.svg>"
python "<skill>/scripts/component_bundle.py" audit "<master.svg>" --lock "<geometry.lock.json>"
```

Keep the accepted lock; give a reviewed geometry revision a separate record.
Do not rewrite the lock to silence a failed check. The helper rejects changed
outlines, missing components, drawing-order/canvas changes and altered output
coverage. Paint is applied in source space inside the locked outlines so an
outline's rotation does not rotate the light again. It preserves useful named
groups without cropping the glyph into guessed regions. A valid lock establishes
integrity, not source fidelity or professional approval.

Multiple filled shapes receive separate clips so a compound path's even-odd
counters are preserved alongside ordinary nonzero shapes. Check rendered holes
and coverage as well as geometry records; collecting mixed rules in one clip
can fill a counter in a renderer even when the path attributes are unchanged.

## Fit simple lighting from the source

For surfaces explained by one linear or elliptical radial field, use
`scripts/fit_gradient.py`. It samples the original image through an isolated
black-on-white material mask, robustly fits color stops, and compares linear and
radial models on a held-out pixel sample. It also tests expanded radial fields,
whose lighting boundary need not coincide with the object boundary. Keep seams,
lettering and other materials out of the sample mask.

```powershell
python "<skill>/scripts/fit_gradient.py" --source "<reference.png>" --mask "<material-mask.png>" --output "<surface.paint.json>" --report "<fit-report.json>" --kind auto --stops 24
```

For measured elliptical surfaces, `--ellipse "cx,cy,rx,ry,angle_degrees"` uses
source coordinates. `--erosion 0` retains an already reviewed interior sample
mask; the default erosion excludes uncertain edge pixels. The helper needs
NumPy, Pillow, SciPy and OpenCV. Use the paint JSON in the component manifest.

Render and inspect the native export and direct SVG detail crops. Check source
lighting direction, bright and dark rims, plateaus, and connected junctions.
Sample error is a diagnostic, not an art score. These paint models intentionally
omit fine texture. A branching gold monogram generally needs several intentional
curved highlight/shadow regions; a single fitted field is not sufficient. Reject
an unsuitable lighting proof rather than promoting it because it has low error.

## Review and preserve evidence

For each bounded assignment, keep the source, accepted geometry/lock, candidate,
fresh preview, guard result and actual visual findings. Correct one demonstrated
defect and compare before/after before moving on. A limitations list does not
complete a recoverable component. A grouping-only edit must preserve appearance
as well as the accepted outlines.

Audit the canonical master before the lossless optimization stage. The optimizer
may rewrite equivalent SVG syntax that this conservative geometry audit rejects;
use its independent exact-render gate for that separate step. Do not relock the
optimized syntax to manufacture a geometry pass. Complete the production review
and keep editor import distinct from structural and render checks.

## Delegate a bounded component

When evaluating a source-only constructor after prior quality regressions, split
the work into separate turns with externally checked artifacts. Asking one actor
to construct, self-review and finish every stage still lets an inadequate proof
advance. First request geometry only: component inventory, native neutral proof,
source-space edge overlay, and enlarged contacts. The coordinating agent checks
these before assigning a representative material proof, then the remaining art.
Do not provide a previous finished target in a blind test. Preserve the first
completed blind result before giving source-based corrective feedback, and label
subsequent work as coached. Record which geometry, masks or tools were supplied.

For raised lettering, isolate the projected silhouette, front face, pale trim,
inner bevel and sidewalls separately where visible. A whole-object color mask
already includes the extrusion; offsetting it again can double the depth and
clip the artboard. A uniform stroke around an inset is not a substitute for
source-specific bevel widths and corner transitions. Check bounds against the
source and inspect a color section across the bevel, including its bright and
dark bands, before repeating the paint across the glyph.

`scripts/compare_profiles.py` helps expose missing local lighting that a broad
gradient can hide. Render the candidate at the source's native canvas first.
Provide a JSON list such as
`[{"name":"upper bevel","start":[100,80],"end":[120,160],"radius":2}]`.
Endpoints cross the material in source pixels; radius samples a narrow median
strip. Run with `--source reference.png --candidate native-render.png
--sections sections.json --output profile-review`. Inspect its section-location
image and luminance curves together; misplaced samples and pixel error cannot
establish a quality grade. Use separate direct SVG enlargements for curve review.

Give the constructor one component, the original canvas/source, accepted outline
and lock, an isolated material mask, permitted helper commands, output paths and
the exact scope of the stage. State which inputs were supplied rather than
independently reconstructed. Keep previous finished candidates out of a blind
constructor's packet. Assign ownership and preserve other workers' edits.

Require an actual export, fresh native/detail renders and specific source
comparisons. A separate reviewer receives source and candidate without the
expected verdict or evaluative folder names. The main agent checks the evidence
and decides readiness. Verify claimed defect coordinates against uncropped source
pixels; a truncated crop or enlarged native PNG can produce a false finding.
Correct unsupported reviewer findings as well as constructor defects. When simple lighting cannot follow the form, retain the
geometry and build local curved shading regions; do not accept a flat substitute
or change the lock to obtain a pass. Judge this difficult stage separately before
combining it with approved components.
