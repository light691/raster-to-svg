# Third-party dependencies and provenance

The skill instructions, original helpers, packaging, documentation and optional
verification companion in this repository are MIT licensed; see [LICENSE](LICENSE).
Third-party software retains its upstream license. This project is independent
of Anthropic, Google, OpenAI, Microsoft, LogoLabs and Vision Cortex.

## Bundled Inkvec executable

- Project: [LogoLabs Inkvec](https://github.com/logolabs/inkvec).
- Version: 0.2.6, Windows x64 CLI, verified byte-identical to the executable in the
  official upstream release archive.
- Release: [v0.2.6](https://github.com/logolabs/inkvec/releases/tag/v0.2.6).
- Location: `scripts/bin/windows-x64/inkvec.exe`.
- Executable SHA-256: `ee73487eb270beeacba5d9b991181b59b76c61f25d8d8f23067bdf9f493ffd7c`.
- Release ZIP: `inkvec-0.2.6-x86_64-pc-windows-msvc.zip`, SHA-256
  `f41d12526748576e035d9f339981762a882269990921928e7dc1732a2430f325`.
- License: Apache-2.0. Copyright 2026 LogoLabs and Stefan-Lucian Deleanu.
- The upstream [LICENSE](scripts/bin/windows-x64/LICENSE),
  [NOTICE](scripts/bin/windows-x64/NOTICE), and generated
  [THIRD_PARTY.md](scripts/bin/windows-x64/THIRD_PARTY.md) are preserved verbatim.
- Only the CLI executable and notices are redistributed. No model weights,
  ONNX Runtime library, DirectML runtime, studio application, or benchmark images
  are included. Upstream's third-party inventory also discusses optional features
  and benchmark corpora that are not shipped in this bundle.

The recorded executable hash identifies these exact bytes; it is distinct from
the hash of the upstream release ZIP archive. Do not represent it as a signature
or a source-to-binary reproducibility guarantee.

## Installed dependencies

| Package | Direct version | Upstream | License |
| --- | --- | --- | --- |
| `@visioncortex/vtracer` | 1.0.0-alpha.4 | [vtracer](https://github.com/visioncortex/vtracer) | MIT OR Apache-2.0 |
| `sharp` | 0.35.5 | [sharp](https://github.com/lovell/sharp) | Apache-2.0; libvips and other native dependencies have their own notices |
| `numpy` | 2.4.3 | [NumPy](https://numpy.org/) | BSD-3-Clause |
| `Pillow` | 12.1.1 | [Pillow](https://python-pillow.github.io/) | MIT-CMU |
| `scipy` | 1.18.1 | [SciPy](https://scipy.org/) | BSD-3-Clause |
| `opencv-python-headless` | 4.13.0.92 | [opencv-python](https://github.com/opencv/opencv-python) | Wrapper MIT; OpenCV Apache-2.0; wheel components retain their licenses |
| `contourpy` | 1.4.0 | [ContourPy](https://github.com/contourpy/contourpy) | BSD-3-Clause |
| `playwright` (optional) | 1.64.1 | [Playwright](https://github.com/microsoft/playwright) | Apache-2.0; browser has its own notices |

npm and pip retrieve these packages during setup; their full source trees are not
vendored here. Their package distributions contain applicable license and native
library notices. Preserve those notices when redistributing installed runtimes.
Browser binaries download separately and are not part of this Git repository.
Agent products and editors are separate software, not dependencies redistributed
under this project's MIT license.
