#!/usr/bin/env python3
"""Locate and invoke Inkvec without a shell; forward its CLI arguments unchanged."""
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys


def find_inkvec():
    override = os.environ.get('INKVEC_BIN')
    if override:
        candidate = shutil.which(override) or override
        if not Path(candidate).is_file():
            raise FileNotFoundError('INKVEC_BIN does not point to an executable file')
        return str(Path(candidate).resolve())
    installed = shutil.which('inkvec')
    if installed:
        return installed
    if sys.platform == 'win32' and platform.machine().lower() in {'amd64', 'x86_64'}:
        bundled = Path(__file__).parent / 'bin' / 'windows-x64' / 'inkvec.exe'
        if bundled.is_file():
            return str(bundled.resolve())
    raise FileNotFoundError(
        'Inkvec is not installed for this platform. Download the CLI from '
        'https://github.com/logolabs/inkvec/releases/tag/v0.2.6 and add it to PATH, '
        'or set INKVEC_BIN to its executable. VTracer remains available without Inkvec.')


def main():
    try:
        return subprocess.run([find_inkvec(), *sys.argv[1:]], check=False).returncode
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
