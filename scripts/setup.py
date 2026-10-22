#!/usr/bin/env python3
"""Install local dependencies; optionally install the Playwright verification extra."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent.parent


def run(command, **kwargs):
    print('+', ' '.join(map(str, command)), flush=True)
    subprocess.run(list(map(str, command)), check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--playwright', action='store_true', help='Install optional browser verification and Chromium')
    parser.add_argument('--skip-python', action='store_true', help='Only install Node dependencies')
    parser.add_argument('--skip-node', action='store_true', help='Only install Python dependencies')
    args = parser.parse_args()
    if args.skip_node and args.playwright:
        parser.error('--playwright requires Node setup')
    if sys.version_info < (3, 12):
        parser.error('Python 3.12 or newer is required')
    node, npm = shutil.which('node'), shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    if not args.skip_node:
        if not node or not npm:
            parser.error('Install Node.js 22+ with npm and rerun setup')
        version = subprocess.check_output([node, '--version'], text=True).strip()
        if int(re.match(r'v?(\d+)', version)[1]) < 22:
            parser.error('Node.js 22 or newer is required')
    if not args.skip_python:
        environment = ROOT / '.venv'
        python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        if not python.is_file() or not (environment / 'pyvenv.cfg').is_file():
            venv.EnvBuilder(with_pip=True).create(environment)
        run([python, '-m', 'pip', 'install', '--requirement', ROOT / 'requirements.txt'])
    if not args.skip_node:
        run([npm, 'ci', '--prefix', ROOT / 'scripts', '--no-audit', '--no-fund'])
    if args.playwright:
        extra = ROOT / 'optional-skills' / 'playwright-svg-verification' / 'scripts'
        run([npm, 'ci', '--prefix', extra, '--no-audit', '--no-fund'])
        cli = extra / 'node_modules' / 'playwright' / 'cli.js'
        run([node, cli, 'install', 'chromium'])
    print('Setup complete. Activate .venv, then run: python scripts/doctor.py')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, subprocess.CalledProcessError) as error:
        print(f'Setup failed: {error}', file=sys.stderr)
        sys.exit(1)
