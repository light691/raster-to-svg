#!/usr/bin/env python3
"""Check this interpreter, core Node dependencies, Inkvec, and optional Playwright."""
import argparse
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from inkvec import find_inkvec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--playwright', action='store_true', help='Also require the browser verification extra')
    args = parser.parse_args()
    checks = []
    checks.append(dict(name='Python 3.12+', ok=sys.version_info >= (3, 12), detail=sys.version.split()[0]))
    for module in ('numpy', 'PIL', 'scipy', 'cv2', 'contourpy'):
        try:
            loaded = importlib.import_module(module)
            checks.append(dict(name=module, ok=True, detail=getattr(loaded, '__version__', 'installed')))
        except ImportError as error:
            checks.append(dict(name=module, ok=False, detail=str(error)))
    node = shutil.which('node')
    script_dir = Path(__file__).resolve().parent
    code = "const sharp=require('sharp');require('@visioncortex/vtracer');if(Number(process.versions.node.split('.')[0])<22)process.exit(1);console.log(JSON.stringify({node:process.versions.node,sharp:sharp.versions.sharp,librsvg:sharp.versions.rsvg}));"
    if node:
        result = subprocess.run([node, '-e', code], cwd=script_dir, capture_output=True, text=True)
        checks.append(dict(name='Node core', ok=result.returncode == 0, detail=(result.stdout or result.stderr).strip()))
    else:
        checks.append(dict(name='Node core', ok=False, detail='node is not on PATH'))
    try:
        inkvec = find_inkvec()
        result = subprocess.run([inkvec, '--version'], capture_output=True, text=True)
        checks.append(dict(name='Inkvec (optional)', ok=result.returncode == 0, required=False, detail=result.stdout.strip()))
    except OSError as error:
        checks.append(dict(name='Inkvec (optional)', ok=False, required=False, detail=str(error)))
    if args.playwright:
        extra = script_dir.parent / 'optional-skills/playwright-svg-verification/scripts'
        code = "const fs=require('node:fs');const {chromium}=require('playwright');if(!fs.existsSync(chromium.executablePath()))throw Error('Chromium missing: run setup.py --playwright');console.log(require('playwright/package.json').version);"
        if node:
            result = subprocess.run([node, '-e', code], cwd=extra, capture_output=True, text=True)
            checks.append(dict(name='Playwright + Chromium', ok=result.returncode == 0, detail=(result.stdout or result.stderr).strip()))
        else:
            checks.append(dict(name='Playwright + Chromium', ok=False, detail='Node is required'))
    valid = all(check['ok'] for check in checks if check.get('required', True))
    print(json.dumps(dict(ready=valid, checks=checks), indent=2))
    return 0 if valid else 1


if __name__ == '__main__':
    sys.exit(main())
