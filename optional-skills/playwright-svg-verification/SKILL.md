---
name: playwright-svg-verification
description: Verify an exported SVG in a real Chromium browser using Playwright, capturing reduced, native, and enlarged views on light and dark backgrounds. Use for browser rendering, mesh seams, transparency, or final SVG visual verification after raster-to-vector conversion.
license: MIT
metadata:
  version: "1.0.0"
  author: light691
---

# Optional Playwright SVG verification

Use this companion after saving the exact SVG intended for delivery. It complements
the raster-to-svg structural verifier and Sharp/librsvg alpha checks.

Resolve `<skill>` as this companion's directory. Setup is explicit and separate
from the core skill:

```sh
npm ci --prefix "<skill>/scripts" --no-audit --no-fund
node "<skill>/scripts/node_modules/playwright/cli.js" install chromium
node "<skill>/scripts/verify_browser.cjs" --input "<artwork.svg>" --output-dir "<scratch>/browser-qa"
```

On minimal Linux systems, browser system libraries may also be required; use
Playwright's documented `install --with-deps chromium` setup with the host's
permission rules. Use `--headed` when a visible browser helps inspection.

The helper validates the SVG with the core Python verifier first, then renders
it as an image at CSS scales 0.5, 1 and 2 on white and black. It blocks network
requests and writes six PNGs plus a report naming the actual browser/version.
If this companion is installed alone, pass `--verifier /path/to/verify_svg.py`.
Pass `--python /path/to/python` if Python is not on PATH.

Inspect every screenshot, especially contours, thin lettering, internal contacts,
holes, gradient direction, and repeated diagonal seams. Enlarge directly from the
SVG rather than enlarging a PNG. Large canvases use a top-left viewport crop; the
report states this. Use `--max-size` to increase the viewport within the documented
bound, or make explicit SVG detail crops and review them separately. Do not call a
cropped view a whole-art inspection.

Fix demonstrated defects in the SVG, regenerate screenshots and inspect again.
A successful capture means the browser loaded and rendered the file. The helper
does not grade source fidelity, detect all seams, inspect editor import, or grant
professional approval. State the visual findings after inspecting the pixels.
