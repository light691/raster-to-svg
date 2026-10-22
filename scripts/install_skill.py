#!/usr/bin/env python3
"""Copy a portable skill bundle into an agent's discovery directory; never overwrite."""
import argparse
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
SKILLS = {'raster-to-svg': ROOT,
          'playwright-svg-verification': ROOT / 'optional-skills/playwright-svg-verification'}
DIRECTORIES = {'claude': '.claude/skills', 'gemini': '.gemini/skills',
               'codex': '.agents/skills', 'agents': '.agents/skills'}
IGNORED = shutil.ignore_patterns('.git', '.venv', 'node_modules', '__pycache__', '*.pyc',
                                'work', 'output', '.env', '.env.*')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent', choices=DIRECTORIES, default='agents')
    parser.add_argument('--scope', choices=('user', 'project'), default='user')
    parser.add_argument('--project-dir', type=Path, default=Path.cwd())
    parser.add_argument('--destination', type=Path, help='Explicit parent skill directory (overrides agent/scope)')
    parser.add_argument('--skill', choices=SKILLS, default='raster-to-svg')
    parser.add_argument('--with-playwright', action='store_true', help='Install the companion alongside the core skill')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    base = Path.home() if args.scope == 'user' else args.project_dir.resolve()
    parent = (args.destination or base / DIRECTORIES[args.agent]).expanduser().resolve()
    names = [args.skill]
    if args.with_playwright and 'playwright-svg-verification' not in names:
        names.append('playwright-svg-verification')
    plans = [(SKILLS[name].resolve(), parent / name) for name in names]
    for source, target in plans:
        if target.exists():
            parser.error(f'Destination already exists; preserve or move it first: {target}')
        if target == source or source in target.parents:
            parser.error('Destination must be outside the source skill to avoid recursive copies')
        print(f'{source} -> {target}')
    if args.dry_run:
        return 0
    for source, target in plans:
        shutil.copytree(source, target, ignore=IGNORED)
    if args.skill == 'raster-to-svg':
        print(f'Next: run Python on {parent / "raster-to-svg/scripts/setup.py"}'
              + (' --playwright' if args.with_playwright else ''))
    else:
        print('Install npm dependencies and Chromium in the companion scripts directory; see its SKILL.md.')
    print('Dependencies and virtual environments are not copied. Restart or refresh the agent after setup.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except OSError as error:
        print(f'Installation failed: {error}', file=sys.stderr)
        sys.exit(1)
