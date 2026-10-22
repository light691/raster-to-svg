#!/usr/bin/env python3
"""Fit an opaque photograph with a smooth, filter-free SVG gradient surface."""
import argparse
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--spacing', type=float, default=12, help='Initial grid spacing in working pixels')
    parser.add_argument('--error', type=float, default=1.9, help='Refinement RGB error threshold')
    parser.add_argument('--max-vertices', type=int, default=48000)
    parser.add_argument('--iterations', type=int, default=12)
    parser.add_argument('--max-dim', type=int, default=1600, help='Working resolution cap; 0 disables')
    parser.add_argument('--smoothing', type=float, default=1, help='Texture softening; 0 disables, default 1')
    parser.add_argument('--force', action='store_true', help='Replace existing output/report files')
    args = parser.parse_args()
    if not math.isfinite(args.spacing) or args.spacing < 2:
        parser.error('--spacing must be finite and at least 2')
    if not math.isfinite(args.error) or args.error <= 0:
        parser.error('--error must be finite and positive')
    if args.max_vertices < 16 or not 0 <= args.iterations <= 30:
        parser.error('--max-vertices must be at least 16 and --iterations must be 0..30')
    if args.max_dim != 0 and args.max_dim < 2:
        parser.error('--max-dim must be 0 or at least 2')
    if not math.isfinite(args.smoothing) or not 0 <= args.smoothing <= 3:
        parser.error('--smoothing must be 0..3')
    if args.output.suffix.lower() != '.svg':
        parser.error('--output must have an .svg extension')
    paths = [args.input.resolve(), args.output.resolve()]
    if args.report:
        paths.append(args.report.resolve())
    if len(set(paths)) != len(paths):
        parser.error('Source, SVG and report paths must be distinct')
    for path in [args.output, args.report]:
        if path and path.exists() and not args.force:
            parser.error(f'File exists; use --force to replace it: {path}')
    return args


@contextmanager
def atomic_text(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                         prefix='.svg-', suffix='.tmp',
                                         dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            yield stream
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def load_photo(path, max_dim, smoothing):
    from io import BytesIO
    from PIL import Image, ImageCms, ImageOps
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened)
        alpha = np.asarray(image.convert('RGBA'))[:, :, 3]
        if (alpha != 255).any():
            raise ValueError('Transparent input is unsupported; use the native-alpha trace route instead')
        native = image.size
        if min(native) < 2:
            raise ValueError('Both source dimensions must be at least 2 pixels')
        profile = image.info.get('icc_profile')
        if profile:
            image = ImageCms.profileToProfile(image, ImageCms.ImageCmsProfile(BytesIO(profile)),
                                               ImageCms.createProfile('sRGB'), outputMode='RGB')
        else:
            image = image.convert('RGB')
        if max_dim and max(image.size) > max_dim:
            scale = max_dim / max(image.size)
            size = tuple(max(2, round(dimension * scale)) for dimension in image.size)
            image = image.resize(size, Image.Resampling.LANCZOS)
        rgb = np.array(image)
    field = rgb
    if smoothing:
        field = cv2.bilateralFilter(field, 9, 16 * smoothing, 4)
        field = cv2.bilateralFilter(field, 13, 18 * smoothing, 6)
        field = cv2.GaussianBlur(field, (0, 0), .8 * smoothing)
    return native, rgb, field.astype(np.float64)


def sampler(field):
    height, width = field.shape[:2]

    def sample(points):
        x = np.clip(points[..., 0], 0, width - 1)
        y = np.clip(points[..., 1], 0, height - 1)
        x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
        x1, y1 = np.minimum(x0 + 1, width - 1), np.minimum(y0 + 1, height - 1)
        fx, fy = (x - x0)[..., None], (y - y0)[..., None]
        return ((field[y0, x0] * (1 - fx) + field[y0, x1] * fx) * (1 - fy)
                + (field[y1, x0] * (1 - fx) + field[y1, x1] * fx) * fy)
    return sample


def seed_surface(rgb, spacing, limit):
    height, width = rgb.shape[:2]
    budget = max(4, int(limit * .6))
    spacing = max(spacing, math.sqrt(width * height / max(4, budget * .7)))
    while True:
        xs = np.unique(np.r_[np.arange(0, width, spacing), width])
        ys = np.unique(np.r_[np.arange(0, height, spacing), height])
        xx, yy = np.meshgrid(xs, ys)
        points = np.column_stack((xx.ravel(), yy.ravel())).astype(float)
        if len(points) <= budget:
            break
        spacing *= 1.2
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(float)
    gray = cv2.GaussianBlur(gray, (0, 0), 1.1)
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3) / 8
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3) / 8
    magnitude = np.hypot(gx, gy)
    candidates = []
    for top in range(0, height, 7):
        for left in range(0, width, 7):
            tile = magnitude[top:top + 7, left:left + 7]
            iy, ix = np.unravel_index(tile.argmax(), tile.shape)
            y, x = top + iy, left + ix
            strength = magnitude[y, x]
            if strength >= 9:
                normal = np.array([gx[y, x], gy[y, x]]) / strength
                position = np.array([x, y], dtype=float)
                candidates.append((strength, position - normal * 1.4, position + normal * 1.4))
    candidates.sort(key=lambda item: item[0], reverse=True)
    chosen = candidates[:max(0, (budget - len(points)) // 2)]
    if chosen:
        edges = np.array([point for _, before, after in chosen for point in [before, after]])
        points = np.vstack((points, np.clip(edges, [0, 0], [width, height])))
    return np.unique(np.round(points, 3), axis=0)


def refine_surface(points, sample, threshold, limit, iterations):
    weights = np.array([[1/3, 1/3, 1/3], [.6, .2, .2], [.2, .6, .2],
                        [.2, .2, .6], [.5, .5, 0], [0, .5, .5], [.5, 0, .5]])
    print(f'Initial surface: {len(points)} vertices', file=sys.stderr)
    for iteration in range(iterations):
        room = limit - len(points)
        if room <= 0:
            break
        mesh = Delaunay(points)
        triangles = points[mesh.simplices]
        colors = sample(triangles)
        probes = np.einsum('kj,njd->nkd', weights, triangles)
        predicted = np.einsum('kj,njc->nkc', weights, colors)
        error = np.sqrt(np.mean((sample(probes) - predicted) ** 2, axis=2))
        worst = error.argmax(axis=1)
        maximum = error[np.arange(len(error)), worst]
        chosen = np.flatnonzero(maximum > threshold)
        if not len(chosen):
            break
        chosen = chosen[np.argsort(maximum[chosen])[::-1]][:min(4000, room)]
        additions = probes[chosen, worst[chosen]]
        revised = np.unique(np.round(np.vstack((points, additions)), 3), axis=0)
        if len(revised) == len(points):
            break
        points = revised
        print(f'Refine {iteration + 1}: {len(points)} vertices', file=sys.stderr)
    return points, points[Delaunay(points).simplices]


def gradient_endpoints(triangles, values):
    matrix = np.concatenate((triangles, np.ones((len(triangles), 3, 1))), axis=2)
    plane = np.linalg.solve(matrix, values[..., None])[..., 0]
    direction = plane[:, :2]
    length2 = np.maximum((direction * direction).sum(axis=1), 1e-12)
    center = triangles.mean(axis=1)
    at_center = np.einsum('ni,ni->n', direction, center) + plane[:, 2]
    low, high = values.min(axis=1), values.max(axis=1)
    start = center + direction * ((low - at_center) / length2)[:, None]
    end = center + direction * ((high - at_center) / length2)[:, None]
    return start, end, low, high


def fit_gradients(triangles, colors):
    mean = colors.mean(axis=1)
    deviation = colors - mean[:, None, :]
    _, _, basis = np.linalg.svd(deviation, full_matrices=False)
    axis = basis[:, 0]
    values = np.einsum('nvc,nc->nv', deviation, axis)
    start, end, low, high = gradient_endpoints(triangles, values)
    flat = high - low < 1.8
    c0 = np.clip(mean + axis * low[:, None], 0, 255)
    c1 = np.clip(mean + axis * high[:, None], 0, 255)

    # Recover the second local color direction with a low-opacity overlay.
    # This approximates affine RGB shading with a second-order residual rather
    # than dropping hue variation, which can make neighboring facets visible.
    axis2 = basis[:, 1].copy()

    def gamut_distance(direction):
        safe = np.where(abs(direction) > 1e-10, direction, 1e-10)
        room = np.where(direction > 0, (255 - mean) / safe, -mean / safe)
        room[abs(direction) < 1e-10] = 1e12
        return room.min(axis=1)

    flip = gamut_distance(-axis2) > gamut_distance(axis2)
    axis2[flip] *= -1
    extent = np.maximum(gamut_distance(axis2), 1)
    values2 = np.einsum('nvc,nc->nv', deviation, axis2)
    start2, end2, low2, high2 = gradient_endpoints(triangles, values2)
    second = (high2 - low2 > .65) & ~flat
    opacity = np.clip((high2 - low2) / (extent - low2), 0, 1)
    overlay = np.clip(mean + extent[:, None] * axis2, 0, 255)
    baseline = mean + low2[:, None] * axis2
    factor = (extent - low2) / extent
    for target, value in [(c0, low), (c1, high)]:
        corrected = np.clip(baseline + axis * (value * factor)[:, None], 0, 255)
        target[second] = corrected[second]
    return dict(mean=mean, flat=flat, second=second, start=start, end=end,
                c0=c0, c1=c1, start2=start2, end2=end2, opacity=opacity, overlay=overlay)


def svg_color(value):
    return 'rgb(' + ','.join(f'{x / 255 * 100:.3f}%' for x in value) + ')'


def emit_svg(path, native, working, triangles, fitted):
    def attributes(first, last):
        return (f'gradientUnits="userSpaceOnUse" x1="{first[0]:.3f}" y1="{first[1]:.3f}" '
                f'x2="{last[0]:.3f}" y2="{last[1]:.3f}"')

    with atomic_text(path) as stream:
        stream.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{native[0]}" height="{native[1]}" '
                     f'viewBox="0 0 {working[0]} {working[1]}" preserveAspectRatio="none" color-interpolation="sRGB">\n')
        stream.write('<title>Smooth vector photograph</title>\n'
                     '<desc>Adaptive gradient approximation of the supplied photograph. '
                     'Fine photographic texture is softened.</desc>\n<defs>\n')
        for i in np.flatnonzero(~fitted['flat']):
            geometry = attributes(fitted['start'][i], fitted['end'][i])
            stream.write(f'<linearGradient id="s{i}" {geometry}>'
                         f'<stop stop-color="{svg_color(fitted["c0"][i])}"/>'
                         f'<stop offset="1" stop-color="{svg_color(fitted["c1"][i])}"/>'
                         '</linearGradient>\n')
        for i in np.flatnonzero(fitted['second']):
            geometry = attributes(fitted['start2'][i], fitted['end2'][i])
            color = svg_color(fitted['overlay'][i])
            stream.write(f'<linearGradient id="h{i}" {geometry}>'
                         f'<stop stop-color="{color}" stop-opacity="0"/>'
                         f'<stop offset="1" stop-color="{color}" stop-opacity="{fitted["opacity"][i]:.5f}"/>'
                         '</linearGradient>\n')
        # Binary coverage on shared internal edges prevents antialiased cracks.
        # The fills still use smooth gradients. Do not stroke the tessellation.
        stream.write('</defs>\n<g id="photo-surface" shape-rendering="crispEdges">\n')
        for i, triangle in enumerate(triangles):
            fill = svg_color(fitted['mean'][i]) if fitted['flat'][i] else f'url(#s{i})'
            coordinates = ' '.join(f'{x:.3f},{y:.3f}' for x, y in triangle)
            stream.write(f'<polygon points="{coordinates}" fill="{fill}"/>\n')
            if fitted['second'][i]:
                stream.write(f'<polygon points="{coordinates}" fill="url(#h{i})"/>\n')
        stream.write('</g>\n</svg>\n')


def main():
    args = arguments()
    global cv2, np, Delaunay
    try:
        import cv2
        import numpy as np
        from scipy.spatial import Delaunay
        started = time.perf_counter()
        native, rgb, field = load_photo(args.input, args.max_dim, args.smoothing)
        sample = sampler(field)
        points = seed_surface(rgb, args.spacing, args.max_vertices)
        points, triangles = refine_surface(points, sample, args.error,
                                           args.max_vertices, args.iterations)
        fitted = fit_gradients(triangles, sample(triangles))
        working = (rgb.shape[1], rgb.shape[0])
        emit_svg(args.output, native, working, triangles, fitted)
        second = int(fitted['second'].sum())
        report = dict(input=str(args.input.resolve()), output=str(args.output.resolve()),
                      dimensions=list(native), working_dimensions=list(working),
                      source_is_opaque=True, vertices=len(points), triangles=len(triangles),
                      shapes=len(triangles) + second,
                      gradients=int((~fitted['flat']).sum()) + second,
                      bytes=args.output.stat().st_size, filters=0, embedded_images=0,
                      parameters={key: getattr(args, key) for key in
                                  ['spacing', 'error', 'max_vertices', 'iterations', 'max_dim', 'smoothing']},
                      seconds=round(time.perf_counter() - started, 2))
        if args.report:
            with atomic_text(args.report) as stream:
                json.dump(report, stream, indent=2)
                stream.write('\n')
        print(json.dumps(report))
        return 0
    except ImportError as error:
        print(f'Missing dependency: {error}. Needs numpy Pillow scipy opencv-python-headless.', file=sys.stderr)
    except Exception as error:
        print(f'Photo vectorization failed: {error}', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
