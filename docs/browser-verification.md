# Optional browser verification with Playwright

The optional companion adds real Chromium screenshots to the core SVG workflow.
Use it for mesh seams, transparency complaints, renderer differences, and final
browser review. It does not replace the strict verifier, raw-alpha checks, visual
comparison with the reference, or target-editor import testing.

## Install

From the repository root, opt in explicitly:

```sh
python scripts/setup.py --playwright
python scripts/doctor.py --playwright
```

This installs pinned Playwright packages in the companion's own `scripts/`
directory and downloads its Chromium browser. The core npm package never requires
Playwright. Use `--skip-python --playwright` if Python dependencies are already
ready and you only need Node packages/browser setup.

Alternatively, install just the companion's JavaScript dependencies:

```sh
npm ci --prefix optional-skills/playwright-svg-verification/scripts --no-audit --no-fund
node optional-skills/playwright-svg-verification/scripts/node_modules/playwright/cli.js install chromium
```

On a minimal Linux host, Playwright's [browser setup documentation](https://playwright.dev/docs/browsers)
explains required system libraries. If the host permits system package changes:

```sh
node optional-skills/playwright-svg-verification/scripts/node_modules/playwright/cli.js install --with-deps chromium
```

That command can require administrator privileges. Ordinary setup intentionally
does not install OS packages automatically.

## Capture and inspect

```sh
node optional-skills/playwright-svg-verification/scripts/verify_browser.cjs --input work/artwork.svg --output-dir work/browser-qa
```

The helper writes:

```text
browser-qa/
  scale-0.5-white.png       scale-0.5-black.png
  scale-1-white.png         scale-1-black.png
  scale-2-white.png         scale-2-black.png
  browser-report.json
```

The report records the input SHA-256, Chromium version, source dimensions, scale,
background, viewport, crop status, and structural result. Input changes during
capture cause a failure. `status: captured` means artifact capture succeeded;
`not_evaluated` explicitly includes aesthetic quality, source fidelity and editor
import. Inspect the PNGs before writing a visual conclusion.

The default maximum viewport dimension is 4096 CSS pixels. Larger artwork is
captured from its top-left and marked `cropped`; use `--max-size 8192` within the
helper's bound or make deliberate SVG detail crops. Do not infer whole-art
coverage from a cropped screenshot. `--headed` shows the browser when useful.

Inspect lettering counters, fine strokes, overlap contacts, connected highlights,
and repeated diagonal lines. Compare both backgrounds; the core raw-alpha helper
is still the direct coverage measurement. For production artwork, review native
and enlarged details from the exact SVG, repair demonstrated defects, then repeat
capture after the last edit.

## Install the companion as a skill

```sh
python scripts/install_skill.py --agent claude --with-playwright
```

This copies the main skill and a sibling `playwright-svg-verification` entrypoint.
Use `--agent gemini`, `codex`, or `agents` for other hosts. Setup of the installed
core copy with `--playwright` installs the nested companion's packages. That
nested helper is immediately runnable from the main skill. A sibling companion
entrypoint first looks for its own Playwright package, then reuses the installed
core bundle's optional runtime. A companion installed elsewhere needs its own
`npm ci` and browser installation using the paths in its `SKILL.md`.

To install only that entrypoint:

```sh
python scripts/install_skill.py --agent gemini --skill playwright-svg-verification
```

When the core skill is not a sibling or parent bundle, pass
`--verifier /absolute/path/to/verify_svg.py`. Pass `--python` for an explicit Python
executable. The validator uses only Python's standard library.

Example agent request:

```text
Use raster-to-svg for this conversion, then use playwright-svg-verification to
inspect the exact final SVG at several sizes on light and dark backgrounds.
Report browser findings separately from structural validity and editor import.
```

The browser helper uses Playwright's [library API](https://playwright.dev/docs/library)
for bounded local screenshot capture; no Playwright Test project or test spec is
needed. Browser binaries remain in Playwright's normal per-user cache unless the
user configures `PLAYWRIGHT_BROWSERS_PATH` consistently during setup and capture.
