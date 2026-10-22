# Contributing

Use Python 3.12+ and Node.js 22+. Run `python scripts/setup.py`, activate `.venv`,
then run `python scripts/doctor.py` and `python tests/smoke.py`.

For changes to browser verification, run `python scripts/setup.py --playwright`
and `python tests/smoke.py --playwright`. Do not commit `.venv`, `node_modules`,
browser downloads, private reference artwork, scratch renders, or credentials.

The smoke suite uses temporary synthetic artwork to exercise tracing, strict
validation, transparent previews, optimization, contour fitting, gradient fitting,
photo surfaces, component locks, and installer behavior. Browser checks capture
the synthetic SVG. They verify execution and observable invariants; they do not
grade artist-quality reconstruction or model behavior.

Keep a failing visual example minimal and share only artwork you have permission
to redistribute. State the source dimensions, command/parameters, operating system,
dependency versions, renderer/editor version, and what differs in the exported
SVG. Compare the actual alpha channel for coverage issues. Include a fresh preview
from the exact SVG instead of an old screenshot.

Preserve source geometry and intent. Any change to an optimization transform must
keep the master and pass exact RGBA comparisons. A smaller file with different
geometry or shading is a separate appearance tradeoff. Expand meaningful fixtures
when a regression demonstrates a gap; do not add tests that merely match wording.

Document dependency updates in manifests and regenerate the corresponding npm
lockfile. Review third-party notices before replacing the bundled Inkvec binary.
Keep host-specific paths out of shared skill instructions and keep Playwright
optional. Pull requests should state the problem, resulting behavior, and actual
validation performed.
