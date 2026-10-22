#!/usr/bin/env python3
"""Compact standalone full-vector SVGs; publish only render-identical candidates."""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal, localcontext
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

from verify_svg import inspect_svg

SVG = 'http://www.w3.org/2000/svg'
XLINK = 'http://www.w3.org/1999/xlink'
ET.register_namespace('', SVG)
ET.register_namespace('xlink', XLINK)
NUMBER = re.compile(r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?')
URL = re.compile(r'url\(\s*([\"\x27]?)(#[^\s)\"\x27]+)\1\s*\)')
NUMERIC = {'x', 'y', 'x1', 'y1', 'x2', 'y2', 'cx', 'cy', 'r', 'rx', 'ry',
           'width', 'height', 'offset', 'stop-opacity', 'opacity', 'fill-opacity',
           'stroke-opacity', 'stroke-width', 'stroke-miterlimit', 'stroke-dashoffset',
           'stroke-dasharray', 'gradientTransform', 'transform', 'viewBox', 'points'}


def tag(e):
    return e.tag.rsplit('}', 1)[-1]


def number(s):
    """Remove redundant decimal syntax; never round or pass through binary floats."""
    if 'e' in s.lower():
        mantissa, exponent = re.split('[eE]', s)
        exp = str(int(exponent))
        compact = number(mantissa) + ('e' + exp if exp != '0' else '')
        return compact if len(compact) < len(s) else s
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    if s in ('', '-0', '+0'):
        return '0'
    if s.startswith('+'):
        s = s[1:]
    if s.startswith('0.'):
        s = s[1:]
    if s.startswith('-0.'):
        s = '-' + s[2:]
    return s


def numbers(s):
    return NUMBER.sub(lambda m: number(m.group()), s)


def decimal_text(v):
    return number(format(v, 'f'))


def join_numbers(values):
    out = ''
    for v in values:
        text = decimal_text(v)
        out += ('' if not out or text.startswith('-') else ' ') + text
    return out


def compact_path(d):
    # Triangle meshes are common; exact Decimal deltas avoid coordinate rounding.
    match = re.fullmatch(r'\s*M([^A-Za-z]+)L([^A-Za-z]+)L([^A-Za-z]+)[Zz]\s*', d)
    if match:
        pts = [[Decimal(n) for n in NUMBER.findall(part)] for part in match.groups()]
        if all(len(p) == 2 for p in pts):
            values = [v for point in pts for v in point]
            with localcontext() as ctx:
                ctx.prec = max(v.adjusted() + 1 for v in values) + max(-v.as_tuple().exponent for v in values) + 4
                ctx.prec = max(ctx.prec, 28)
                out = 'M' + join_numbers(pts[0])
                prev = pts[0]
                previous_command = 'M'
                for point in pts[1:]:
                    choices = [('L', point), ('l', [point[0] - prev[0], point[1] - prev[1]])]
                    if point[0] == prev[0]:
                        choices += [('V', [point[1]]), ('v', [point[1] - prev[1]])]
                    if point[1] == prev[1]:
                        choices += [('H', [point[0]]), ('h', [point[0] - prev[0]])]
                    def emit(item):
                        command, values = item
                        value = join_numbers(values)
                        return (('' if value.startswith('-') else ' ') if command == previous_command else command) + value
                    choice = min(choices, key=lambda item: len(emit(item)))
                    out += emit(choice)
                    previous_command = choice[0]
                    prev = point
                return out + 'z'
    d = numbers(d)
    d = re.sub(r'\s*,\s*', ',', d)
    return re.sub(r'(?<=\d)[ ,]+(?=-)', '', d).strip()


def references(e):
    found = set()
    for node in e.iter():
        for key, value in node.attrib.items():
            found.update(m.group(2)[1:] for m in URL.finditer(value))
            if key.rsplit('}', 1)[-1] == 'href' and value.startswith('#'):
                found.add(value[1:])
            if key in {'aria-labelledby', 'aria-describedby'}:
                found.update(value.split())
    return found


def rewrite_references(root, mapping):
    for e in root.iter():
        for key, value in list(e.attrib.items()):
            if key == 'id':
                value = mapping.get(value, value)
            elif key.rsplit('}', 1)[-1] == 'href' and value.startswith('#'):
                value = '#' + mapping.get(value[1:], value[1:])
            elif key in {'aria-labelledby', 'aria-describedby'}:
                value = ' '.join(mapping.get(v, v) for v in value.split())
            else:
                value = URL.sub(lambda m: 'url(#' + mapping.get(m.group(2)[1:], m.group(2)[1:]) + ')', value)
            e.set(key, value)


def prune_definitions(root):
    # Static, standalone SVG only. All renderable resources are local references.
    ids = {e.get('id'): e for e in root.iter() if e.get('id')}
    defs_list = [e for e in root.iter() if tag(e) == 'defs']
    defs_elements = {id(n) for d in defs_list for n in d.iter()}
    live = set()
    for e in root.iter():
        if id(e) not in defs_elements:
            for key, value in e.attrib.items():
                live.update(m.group(2)[1:] for m in URL.finditer(value))
                if key.rsplit('}', 1)[-1] == 'href' and value.startswith('#'):
                    live.add(value[1:])
                if key in {'aria-labelledby', 'aria-describedby'}:
                    live.update(value.split())
    todo = list(live)
    while todo:
        key = todo.pop()
        # Dangling accessibility labels are non-rendering source metadata. Keep
        # their spelling; broken paint/href references fail structural preflight.
        if key not in ids:
            continue
        new = references(ids[key]) - live
        live.update(new)
        todo.extend(new)
    removed = 0
    for defs in defs_list:
        for child in list(defs):
            descendant_ids = {n.get('id') for n in child.iter() if n.get('id')}
            if not (descendant_ids & live) and tag(child) != 'metadata':
                defs.remove(child)
                removed += 1
    return removed


def inherit_gradient_units(root):
    ids = {e.get('id'): e for e in root.iter() if e.get('id')}
    users = defaultdict(list)
    painted = set()
    for e in root.iter():
        for value in e.attrib.values():
            painted.update(m.group(2)[1:] for m in URL.finditer(value))
        href = e.get('{' + XLINK + '}href', e.get('href', ''))
        if tag(e) in {'linearGradient', 'radialGradient'} and href.startswith('#'):
            users[href[1:]].append(e)
    count = 0
    for key, children in users.items():
        parent = ids[key]
        if tag(parent) not in {'linearGradient', 'radialGradient'}:
            continue
        for attr in ('gradientUnits', 'spreadMethod'):
            values = [child.get(attr) for child in children]
            if key not in painted and values and None not in values and len(set(values)) == 1:
                parent.set(attr, values[0])
            if parent.get(attr) is not None:
                for child in children:
                    if child.get(attr) == parent.get(attr):
                        del child.attrib[attr]
                        count += 1
    return count


def short_id(i):
    alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    result = ''
    while True:
        result = alphabet[i % 52] + result
        i = i // 52 - 1
        if i < 0:
            return result


def compact_resources(root):
    ids = {e.get('id') for e in root.iter() if e.get('id')}
    counts = Counter()
    for e in root.iter():
        for key, value in e.attrib.items():
            counts.update(m.group(2)[1:] for m in URL.finditer(value))
            if key.rsplit('}', 1)[-1] == 'href' and value.startswith('#'):
                counts[value[1:]] += 1
    gradients = [e.get('id') for e in root.iter() if tag(e) in {'linearGradient', 'radialGradient'} and e.get('id')]
    mapping = {}
    i = 0
    for old in sorted(gradients, key=lambda key: (-counts[key], key)):
        while short_id(i) in ids:
            i += 1
        new = short_id(i)
        if len(new) < len(old):
            mapping[old] = new
            i += 1
    rewrite_references(root, mapping)
    return len(mapping)


def share_groups(root):
    seen = {}
    used = {e.get('id') for e in root.iter() if e.get('id')}
    serial = 0
    count = 0
    for parent in list(root.iter()):
        for e in list(parent):
            if tag(e) != 'g' or e.get('id') or len(e) < 4:
                continue
            if any(n.get('id') for n in e.iter()):
                continue
            data = ET.tostring(e)
            if len(data) < 2048:
                continue
            signature = hashlib.sha256(data).digest()
            if signature not in seen:
                seen[signature] = e
                continue
            first = seen[signature]
            if not first.get('id'):
                name = 'shared-shading-' + str(serial)
                while name in used:
                    serial += 1
                    name = 'shared-shading-' + str(serial)
                first.set('id', name)
                used.add(name)
                serial += 1
            replacement = ET.Element('{' + SVG + '}use', {'{' + XLINK + '}href': '#' + first.get('id')})
            index = list(parent).index(e)
            parent.remove(e)
            parent.insert(index, replacement)
            count += 1
    return count


def serialize(root):
    return ET.tostring(root, encoding='utf-8', xml_declaration=True).replace(b' />', b'/>')


def statistics(root):
    return dict(Counter(tag(e) for e in root.iter()))


def build_candidates(data, work):
    root = ET.fromstring(data)
    protected_text = {id(n) for e in root.iter() if tag(e) in {'title', 'desc', 'metadata'} for n in e.iter()}
    for e in root.iter():
        # Preserve meaningful title/description/metadata text, including xml:space.
        if id(e) not in protected_text and e.text is not None and not e.text.strip():
            e.text = None
        if id(e) not in protected_text and e.tail is not None and not e.tail.strip():
            e.tail = None
        for key, value in list(e.attrib.items()):
            if key == 'd':
                value = compact_path(value)
            elif key in NUMERIC:
                value = numbers(value)
            if key in {'fill', 'stroke', 'stop-color'} and re.fullmatch('#[0-9a-fA-F]{6}', value):
                value = value.lower()
                if value[1] == value[2] and value[3] == value[4] and value[5] == value[6]:
                    value = '#' + value[1] + value[3] + value[5]
            e.set(key, value)
    actions = {'unused_definitions_removed': prune_definitions(root), 'gradient_attributes_inherited': inherit_gradient_units(root)}
    actions['gradient_ids_shortened'] = compact_resources(root)
    candidates = []
    for name in ('compact', 'shared'):
        if name == 'shared':
            actions['identical_shading_groups_shared'] = share_groups(root)
            if not actions['identical_shading_groups_shared']:
                continue
            prune_definitions(root)
        path = work / (name + '.svg')
        path.write_bytes(serialize(root))
        structure = inspect_svg(path, strict=True)
        candidates.append({'name': name, 'path': str(path), 'bytes': path.stat().st_size,
                           'actions': dict(actions), 'structure': structure})
    return candidates


def distinct_paths(paths):
    keys = [os.path.normcase(str(p.resolve())) for p in paths if p is not None]
    if len(keys) != len(set(keys)):
        raise ValueError('Input, output, preview, report, and compressed paths must be distinct')


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temp.write_bytes(data)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--work-dir', required=True, type=Path, help='Workspace scratch directory; creates an isolated run folder')
    parser.add_argument('--preview', type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--svgz', type=Path, help='Optional compressed transport copy; does not reduce editing complexity')
    parser.add_argument('--node', default='node')
    parser.add_argument('--scales', default='0.5,1,2')
    parser.add_argument('--timeout', type=int, default=240, help='Total renderer subprocess timeout, in seconds')
    args = parser.parse_args()
    distinct_paths([args.input, args.output, args.preview, args.report, args.svgz])
    if args.input.suffix.lower() != '.svg' or args.output.suffix.lower() != '.svg':
        raise ValueError('Input and output must be .svg files')
    if args.preview and args.preview.suffix.lower() != '.png':
        raise ValueError('Preview must be .png')
    if args.svgz and args.svgz.suffix.lower() != '.svgz':
        raise ValueError('Compressed copy must be .svgz')
    scales = sorted(set([1.0] + [float(s) for s in args.scales.split(',')]))
    if any(not (0 < s <= 4) for s in scales):
        raise ValueError('Render scales must be in (0, 4]')
    data = args.input.read_bytes()
    if re.search(br'<!DOCTYPE|<!ENTITY', data, re.I):
        raise ValueError('DTD/entity declarations are unsupported')
    structure = inspect_svg(args.input, strict=True)
    if not structure['valid']:
        raise ValueError('Input must already be standalone full-vector SVG: ' + '; '.join(structure['issues']))
    root = ET.fromstring(data)
    ids = [e.get('id') for e in root.iter() if e.get('id')]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate IDs make resource rewriting ambiguous')
    work = args.work_dir.resolve() / ('run-' + uuid.uuid4().hex[:12])
    work.mkdir(parents=True)
    reference = work / 'reference.svg'
    reference.write_bytes(data)
    candidates = [c for c in build_candidates(data, work) if c['bytes'] < len(data) and c['structure']['valid']]
    manifest = {'reference': str(reference), 'scales': scales, 'work': str(work),
                'candidates': [{'name': c['name'], 'path': c['path']} for c in candidates]}
    manifest_path = work / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    renderer = Path(__file__).with_name('compare_svg.cjs')
    completed = subprocess.run([args.node, str(renderer), str(manifest_path)], capture_output=True,
                               text=True, timeout=args.timeout)
    if completed.returncode:
        raise RuntimeError('Render comparison failed; no candidate published: ' + completed.stderr[-2000:])
    comparison = json.loads((work / 'render-comparison.json').read_text(encoding='utf-8'))
    verified = {c['name']: c for c in comparison['candidates']}
    accepted = [c for c in candidates if verified[c['name']]['render_identical']]
    chosen = min(accepted, key=lambda c: c['bytes']) if accepted else None
    selected_path = Path(chosen['path']) if chosen else reference
    selected_data = selected_path.read_bytes()
    if args.input.read_bytes() != data:
        raise RuntimeError('Source changed during optimization; no output published')
    # Validation and comparisons refer to these exact bytes; do not mutate after selection.
    atomic_write(args.output, selected_data)
    selected_name = chosen['name'] if chosen else 'reference'
    if args.preview:
        atomic_write(args.preview, (work / (selected_name + '.png')).read_bytes())
    compressed_bytes = None
    if args.svgz:
        compressed = gzip.compress(selected_data, compresslevel=9, mtime=0)
        assert gzip.decompress(compressed) == selected_data
        atomic_write(args.svgz, compressed)
        compressed_bytes = len(compressed)
    report = {'status': 'optimized' if chosen else 'unchanged', 'validation_scope': 'structure-and-render-comparison',
              'not_evaluated': ['source_art_quality', 'vector_editor_import', 'all_possible_renderers_and_scales'],
              'input': str(args.input.resolve()), 'output': str(args.output.resolve()),
              'input_bytes': len(data), 'output_bytes': len(selected_data),
              'saved_percent': round(100 * (1 - len(selected_data) / len(data)), 3),
              'compressed_transport_bytes': compressed_bytes, 'chosen_candidate': selected_name,
              'source_preserved': True, 'counts_before': statistics(ET.fromstring(data)),
              'counts_after': statistics(ET.fromstring(selected_data)),
              'actions': chosen['actions'] if chosen else {}, 'candidates': candidates,
              'comparison': comparison, 'work_dir': str(work)}
    report_data = json.dumps(report, indent=2).encode('utf-8')
    atomic_write(work / 'optimization-report.json', report_data)
    if args.report:
        atomic_write(args.report, report_data)
    print(json.dumps({k: report[k] for k in ['status', 'input_bytes', 'output_bytes', 'saved_percent',
                                           'chosen_candidate', 'source_preserved', 'not_evaluated', 'work_dir']}))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, ET.ParseError, subprocess.TimeoutExpired, RuntimeError) as error:
        print(json.dumps({'status': 'error', 'error': str(error), 'source_preserved': True}), file=sys.stderr)
        sys.exit(1)
