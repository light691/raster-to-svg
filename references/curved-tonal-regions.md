# Curved material tones

Use this optional construction for one isolated, narrow-hue material whose
connected highlights cannot be described adequately by a few native gradients.
It builds nested curved tonal regions, similar to expanded vector blend steps.
It is not a native Illustrator blend or a general photo-to-vector replacement.
Prefer a few gradients for planar surfaces and simple lighting.

`scripts/vector_tones.py` samples source color through a black-on-white material
mask, extends valid interior samples to uncertain edges, smooths a luminance
field, and fits its tonal boundaries with cubic paths. The accepted outline is
copied into a clip; lighting does not replace the silhouette or its holes.
It requires the original source pixel canvas in every input.
Dependencies are NumPy, Pillow, SciPy, OpenCV and ContourPy. ContourPy extracts
interpolated subpixel level sets; thresholding a raster into binary masks first
can give several tones the same whole-pixel boundary and produce enlarged bands.

```powershell
python "<skill>/scripts/vector_tones.py" --source "<reference.png>" --material "<visible-material-mask.png>" --outline "<accepted-outline.svg>" --output "<material.svg>" --report "<material-report.json>"
```

Use `--exclude <mask.png>` to remove known occluders, nearby pale trim or other
contaminated samples; black marks excluded pixels. A highlight and an occluder
must be distinguished from source geometry, not saturation alone. An optional
`--palette-mask` selects a representative subset of the remaining samples for
the color curve. Split distinct materials rather than sharing their palette.
Neither mask changes the accepted outer geometry.

The default `--color-step .6` spaces regions by color change rather than equal
luminance intervals. Equal luminance steps can still cause large RGB jumps in
specular gold. Opaque tonal fills also avoid repeated low-opacity rounding. The
report includes path/curve counts and the largest scheduled channel step;
neither proves smooth appearance after contour fitting. `--blur`, `--tolerance`
and `--curve-sigma` are in source pixels and should scale with the reference.
Tonal boundaries use periodic cubic splines converted to exact Bézier spans,
with continuous tangents and curvature. Here `--tolerance` is a smoothing RMS
budget, not a maximum geometric error. The separate accepted silhouette is
unchanged. Inspect both visible approximation error and the reported curve count.

The fitter reduces weights for contour points more than eight source pixels
outside the material mask. Nearest-sample extensions in empty holes can otherwise
consume many unnecessary knots. This saves complexity outside the clip; it is
not permission to simplify visible shading. Check contact edges and enlarged
tonal transitions after any fit change. Raising curve tolerance independently
can misalign adjacent tonal boundaries and bring back bands. Smoothing the
sampled field first can remove source noise more consistently, but can also
soften a real narrow highlight; compare that tradeoff against the source.

The helper uses group opacity `.999999` to composite the material before its
outer clip. In tested 8-bit renders this avoids accumulated clip antialiasing
while retaining opaque interiors. Verify alpha against a single-fill outline,
plus source-guided contact samples, rather than assuming a good white preview
establishes coverage. Continue concealed objects underneath their covers; a
shared antialiased boundary can otherwise leave a sliver or colored fringe.

Inspect the actual export at native and 300–400% size, including a curved arc,
junction and contact. Compare in another renderer when effects appear specific
to a viewer. If a browser's SVG DOM snapshot times out, an HTML `img` wrapper
can still provide a direct renderer check without expanding that DOM snapshot.

This construction may require hundreds of compound shading paths per material
and many repeated control points. Keep outline, material, highlights/shadows and
occlusions in useful groups. Report that editing tradeoff, inspect practical
performance, and reject visible bands or an impractical master. Do not promote
the result solely because it has fewer objects than a prior triangle surface.
Full-art source fidelity and actual editor import remain separate judgments.
