#!/usr/bin/env python3
"""Exercise real conversion and packaging invariants with temporary synthetic art."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / 'scripts'


def run(command, expected=0):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True, cwd=ROOT, timeout=180)
    if result.returncode != expected:
        raise RuntimeError(f'{command}\nexit={result.returncode}\n{result.stdout}\n{result.stderr}')
    return result.stdout


def py(name, *args, expected=0):
    return run([sys.executable, SCRIPTS / name, *args], expected)


def node(name, *args):
    return run(['node', SCRIPTS / name, *args])


def strict(file):
    result = json.loads(py('verify_svg.py', file, '--strict'))
    assert result['valid'] and result['validation_scope'] == 'structure-only'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--playwright', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='raster-svg-smoke-') as temporary:
        work = Path(temporary)
        source = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(source)
        draw.rectangle((8, 8, 55, 55), fill='#3377cc')
        draw.rectangle((24, 24, 39, 39), fill=(0, 0, 0, 0))
        raster = work / 'source.png'
        source.save(raster)
        mask = Image.new('L', (64, 64), 255)
        draw = ImageDraw.Draw(mask)
        draw.rectangle((8, 8, 55, 55), fill=0)
        draw.rectangle((24, 24, 39, 39), fill=255)
        mask.save(work / 'mask.png')
        yy, xx = np.mgrid[:64, :64]
        rgb = np.stack((70 + xx * 2, 90 + xx, 40 + yy), axis=-1).astype('uint8')
        Image.fromarray(rgb).save(work / 'gradient.png')

        traced = work / 'trace.svg'
        node('vectorize.cjs', '--input', raster, '--output', traced, '--mode', 'import', '--preset', 'compact')
        strict(traced)
        node('preview_svg.cjs', '--input', traced, '--preview', work / 'trace.png', '--matte-previews', '--report', work / 'alpha.json')
        assert Image.open(work / 'trace.png').convert('RGBA').getpixel((32, 32))[3] == 0, 'Counter transparency lost'
        print('PASS: portable trace, strict validation, transparent counter and preview')

        # Reject bitmap-containing SVG and active content rather than accepting the extension.
        for name, extra in [('bitmap', '<image href="data:image/png;base64,AA=="/>'),
                            ('script', '<script>alert(1)</script>')]:
            bad = work / f'{name}.svg'
            bad.write_text(f'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0L1 1"/>{extra}</svg>')
            py('verify_svg.py', bad, '--strict', expected=1)
        print('PASS: structural rejection of raster and active content')

        # Nonzero origin, gradients, clips, unused defs and transparent canvas.
        master = work / 'master.svg'
        master.write_text('''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="-2 -2 64 64">
          <defs><linearGradient id="long-gradient-name" gradientUnits="userSpaceOnUse" x1="0.000" y1="0.000" x2="60.000" y2="60.000"><stop offset="0" stop-color="#aabbcc"/><stop offset="1" stop-color="#224466"/></linearGradient>
          <clipPath id="visible-clip"><circle cx="30" cy="30" r="26"/></clipPath>
          <linearGradient id="unused-gradient"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#000000"/></linearGradient></defs>
          <g id="semantic-artwork" clip-path="url(#visible-clip)"><path d="M 0.000 0.000 L 60.000 0.000 L 60.000 60.000 L 0.000 60.000 Z" fill="url(#long-gradient-name)"/></g></svg>''', encoding='utf-8')
        before = hashlib.sha256(master.read_bytes()).hexdigest()
        report = work / 'optimization.json'
        py('optimize_svg.py', master, '--output', work / 'selected.svg', '--work-dir', work / 'opt',
           '--preview', work / 'selected.png', '--report', report, '--svgz', work / 'selected.svgz')
        result = json.loads(report.read_text())
        assert result['output_bytes'] <= result['input_bytes']
        assert hashlib.sha256(master.read_bytes()).hexdigest() == before
        assert result['source_preserved']
        strict(work / 'selected.svg')
        print('PASS: optimization gate, preserved master, gradients/clips/nonzero origin and SVGZ')

        for helper, out in [('clean_mask.py', 'angular.svg'), ('fit_curves.py', 'curved.svg')]:
            py(helper, work / 'mask.png', work / out)
            strict(work / out)
            node('preview_svg.cjs', '--input', work / out, '--preview', work / f'{out}.png')
            assert Image.open(work / f'{out}.png').convert('RGBA').getpixel((32, 32))[3] == 0
        print('PASS: angular and cubic fitting preserve the counter')

        paint = work / 'paint.json'
        py('fit_gradient.py', '--source', work / 'gradient.png', '--mask', work / 'mask.png',
           '--output', paint, '--kind', 'linear', '--samples', '200', '--stops', '8')
        manifest = work / 'components.json'
        manifest.write_text(json.dumps({'components': [{'id': 'ring', 'outline': 'curved.svg', 'paint': 'paint.json'}]}))
        lock = work / 'geometry.lock.json'
        py('component_bundle.py', 'lock', manifest, lock)
        py('component_bundle.py', 'build', manifest, '--lock', lock, '--output', work / 'assembled.svg')
        py('component_bundle.py', 'audit', work / 'assembled.svg', '--lock', lock)
        outline = work / 'curved.svg'
        outline.write_bytes(outline.read_bytes().replace(b'width="64"', b'width="65"'))
        py('component_bundle.py', 'check', manifest, '--lock', lock, expected=2)
        print('PASS: source-fitted paint, locked assembly and geometry-change rejection')

        sections = work / 'sections.json'
        sections.write_text(json.dumps([{'name': 'synthetic ramp', 'start': [10, 16], 'end': [50, 16], 'radius': 1}]))
        py('compare_profiles.py', '--source', work / 'gradient.png', '--candidate', work / 'gradient.png',
           '--sections', sections, '--output', work / 'profiles')
        profiles = json.loads((work / 'profiles/profiles.json').read_text())
        assert profiles['diagnostic_only'] and profiles['sections'][0]['rgb_rmse'] == 0
        print('PASS: source-space profile diagnostics on an identical reference')

        py('vector_tones.py', '--source', work / 'gradient.png', '--material', work / 'mask.png',
           '--outline', work / 'angular.svg', '--output', work / 'tones.svg', '--color-step', '1')
        strict(work / 'tones.svg')
        py('photo_to_svg.py', '--input', work / 'gradient.png', '--output', work / 'photo.svg',
           '--max-vertices', '128', '--iterations', '1', '--spacing', '16')
        strict(work / 'photo.svg')
        node('preview_svg.cjs', '--input', work / 'photo.svg', '--preview', work / 'photo.png', '--expect-opaque')
        py('photo_to_svg.py', '--input', raster, '--output', work / 'invalid-photo.svg', expected=1)
        assert not (work / 'invalid-photo.svg').exists()
        print('PASS: curved tones, opaque photo surface and transparent-photo rejection')

        destination = work / 'installed'
        py('install_skill.py', '--destination', destination)
        installed = destination / 'raster-to-svg'
        assert (installed / 'SKILL.md').is_file() and (installed / 'scripts/vectorize.cjs').is_file()
        assert not (installed / '.venv').exists() and not (installed / 'scripts/node_modules').exists()
        py('install_skill.py', '--destination', destination, expected=2)
        py('install_skill.py', '--destination', ROOT / 'work/recursive-copy', '--dry-run', expected=2)
        print('PASS: installer copies a complete bundle, excludes runtimes and refuses overwrites/recursive copies')

        if sys.platform == 'win32' and platform.machine().lower() in {'amd64', 'x86_64'}:
            binary = SCRIPTS / 'bin/windows-x64/inkvec.exe'
            assert hashlib.sha256(binary.read_bytes()).hexdigest() == 'ee73487eb270beeacba5d9b991181b59b76c61f25d8d8f23067bdf9f493ffd7c'
            py('inkvec.py', '--version')
            py('inkvec.py', raster, '-o', work / 'inkvec.svg', '--mode', 'quality')
            strict(work / 'inkvec.svg')
            print('PASS: bundled Inkvec hash, launcher and real conversion')

        if args.playwright:
            helper = ROOT / 'optional-skills/playwright-svg-verification/scripts/verify_browser.cjs'
            output = work / 'browser'
            run(['node', helper, '--input', work / 'selected.svg', '--output-dir', output, '--python', sys.executable])
            captured = json.loads((output / 'browser-report.json').read_text())
            assert len(captured['captures']) == 6 and all((output / c['file']).is_file() for c in captured['captures'])
            assert not any(c['cropped'] for c in captured['captures'])
            assert captured['sha256'] == hashlib.sha256((work / 'selected.svg').read_bytes()).hexdigest()
            print('PASS: optional real Chromium captures at three sizes on white and black')
    print('All smoke checks passed. Visual quality and editor import are not graded.')


if __name__ == '__main__':
    main()
