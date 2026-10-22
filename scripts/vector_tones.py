#!/usr/bin/env python3
"""Source-sampled curved tonal regions for one accepted material outline.

Uses ordinary filled cubic paths, not triangles, filters or embedded pixels.
This is a finite vector blend: inspect banding and editing complexity. Prefer
native gradients when a small set describes the form. Needs NumPy, Pillow,
SciPy, OpenCV and ContourPy plus the sibling fit_curves/component_bundle helpers.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

import cv2
import contourpy
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt,gaussian_filter,gaussian_filter1d
from scipy.interpolate import splprep,BSpline

from component_bundle import canvas,geometry,NS
from fit_curves import resample
from verify_svg import inspect_svg

ET.register_namespace('',NS)
XL='http://www.w3.org/1999/xlink'
ET.register_namespace('xlink',XL)
q=lambda name:'{'+NS+'}'+name

def fit_tone_curve(points,tolerance=.2,sigma=.4,importance=None,origin=(0,0)):
    """Periodic cubic spline; exact Bezier spans keep C2 tonal boundaries."""
    points=resample(points)
    if len(points)<4:return []
    if sigma:points=gaussian_filter1d(points,sigma,axis=0,mode='wrap')
    weights=None
    budget=len(points)*tolerance*tolerance
    if importance is not None:
        # Clipped-away nearest-sample extensions can dominate the knot count.
        # Keep the same budget near visible material; de-emphasize only distant
        # exterior points. The caller must include a guard around the material.
        xy=np.rint(points-np.array(origin)).astype(int)
        inside=(xy[:,0]>=0)&(xy[:,0]<importance.shape[1])&(xy[:,1]>=0)&(xy[:,1]<importance.shape[0])
        weights=np.full(len(points),.03)
        weights[inside]=np.where(importance[xy[inside,1],xy[inside,0]],1.,.03)
        budget=float(np.sum(weights*weights))*tolerance*tolerance
        weights=np.r_[weights,weights[0]]
    points=np.vstack([points,points[0]])
    tck,_=splprep(points.T,u=np.linspace(0,1,len(points)),w=weights,s=budget,per=True,k=3)
    knots,coefficients,degree=tck;spline=BSpline(knots,np.column_stack(coefficients),degree)
    breaks=np.unique(knots[(knots>=0)&(knots<=1)]);curves=[]
    for a,b in zip(breaks[:-1],breaks[1:]):
        if b-a<1e-12:continue
        p0=spline(a);p3=spline(b);span=(b-a)/3
        curves.append(np.array([p0,p0+spline(a,nu=1)*span,p3-spline(b,nu=1)*span,p3]))
    return curves

def mask_image(path,shape):
    value=np.array(Image.open(path).convert('L'))<128
    if value.shape!=shape:raise ValueError('All masks must retain the source pixel canvas')
    return value

def build(source,material,outline,output,color_step=.6,blur=3.8,tolerance=.2,curve_sigma=.4,exclude=None,palette_mask=None):
    inputs={Path(v).resolve() for v in [source,material,outline,exclude,palette_mask] if v}
    if Path(output).suffix.lower()!='.svg' or Path(output).resolve() in inputs:raise ValueError('Output SVG must be separate from source inputs')
    rgba=np.array(Image.open(source).convert('RGBA'));height,width=rgba.shape[:2]
    root=ET.parse(outline).getroot();space=canvas(root)
    if [float(v) for v in space['viewBox'].replace(',',' ').split()]!=[0,0,width,height]:raise ValueError('Outline viewBox must match the original source pixel canvas')
    if [float(space[k].removesuffix('px')) for k in ('width','height')]!=[width,height]:raise ValueError('Outline dimensions must match the source pixels')
    if not inspect_svg(outline,strict=True)['valid']:raise ValueError('Outline must be strict standalone vector')
    shapes=[]
    for e in root:
        if e.tag.rsplit('}',1)[-1] in {'title','desc','metadata'}:continue
        if e.tag.rsplit('}',1)[-1] not in {'path','rect','circle','ellipse','polygon','polyline'} or len(e):raise ValueError('Use direct filled outline shapes')
        shapes.append(geometry(e))
    if not shapes:raise ValueError('Outline has no filled shapes')
    region=mask_image(material,(height,width))
    yy,xx=np.where(region)
    if len(xx)<30:raise ValueError('Material mask has too few source pixels')
    x0=max(0,int(xx.min())-24);x1=min(width,int(xx.max())+25)
    y0=max(0,int(yy.min())-24);y1=min(height,int(yy.max())+25)
    m=region[y0:y1,x0:x1];rgb=rgba[y0:y1,x0:x1,:3].astype(float)
    valid=cv2.erode(m.astype('uint8'),np.ones((5,5),np.uint8)).astype(bool)&(rgba[y0:y1,x0:x1,3]>=250)
    if exclude:valid&=~mask_image(exclude,(height,width))[y0:y1,x0:x1]
    if valid.sum()<30:raise ValueError('Too few uncontaminated interior source samples')
    nearest=distance_transform_edt(~valid,return_distances=False,return_indices=True)
    field=gaussian_filter(rgb[nearest[0],nearest[1]]@np.array([.2126,.7152,.0722]),blur)
    palette_valid=valid.copy()
    if palette_mask:palette_valid&=mask_image(palette_mask,(height,width))[y0:y1,x0:x1]
    if palette_valid.sum()<30:raise ValueError('Too few palette samples')
    bins=np.clip(np.rint(field[palette_valid]).astype(int),0,255);pixels=rgb[palette_valid]
    counts=np.bincount(bins,minlength=256).astype(float)
    sums=np.array([np.bincount(bins,weights=pixels[:,k],minlength=256) for k in range(3)]).T
    nc=gaussian_filter1d(counts,1.5);palette=gaussian_filter1d(sums,1.5,axis=0)/np.maximum(nc[:,None],1e-9)
    known=nc>.05
    for k in range(3):palette[:,k]=np.interp(np.arange(256),np.flatnonzero(known),palette[known,k])
    palette=gaussian_filter1d(palette,.7,axis=0)
    def color(t):return '#'+''.join(f'{int(v):02x}' for v in np.clip(np.rint([np.interp(t,np.arange(256),palette[:,k]) for k in range(3)]),0,255))
    low=float(field[m].min());high=float(field[m].max())
    out=ET.Element(q('svg'),space);ET.SubElement(out,q('title')).text='Curved material tonal regions'
    defs=ET.SubElement(out,q('defs'))
    for i,shape in enumerate(shapes):
        clip=ET.SubElement(defs,q('clipPath'),{'id':f'material-outline-{i}','clipPathUnits':'userSpaceOnUse'})
        ET.SubElement(clip,q(shape['tag']),shape['attributes'])
    # A non-unit group opacity forces one compositing operation before clipping.
    # The difference rounds to opaque at 8-bit output, avoiding accumulated
    # antialias coverage along a silhouette shared by many nested shapes.
    group=ET.SubElement(defs,q('g'),{'id':'material-paint'})
    ET.SubElement(group,q('rect'),{'width':str(width),'height':str(height),'fill':color(low)})
    segments=0;paths=0
    dense=np.linspace(low,high,16384);colors=np.column_stack([np.interp(dense,np.arange(256),palette[:,k]) for k in range(3)])
    thresholds=[];previous=colors[0];last=color(low);last_rgb=np.rint(previous).astype(int);max_step=0
    if high-low>=.5:
        for k in range(1,len(dense)):
            if np.max(abs(colors[k]-previous))<color_step:continue
            previous=colors[k];current=color(float(dense[k]))
            if current==last:continue
            this_rgb=np.rint(previous).astype(int);max_step=max(max_step,int(abs(this_rgb-last_rgb).max()))
            thresholds.append((float(dense[k]),current));last=current;last_rgb=this_rgb
    generator=contourpy.contour_generator(z=np.pad(field,2,constant_values=low-1),line_type='Separate')
    importance=cv2.dilate(m.astype('uint8'),np.ones((17,17),np.uint8)).astype(bool)
    for i,(t,fill) in enumerate(thresholds):
        contours=generator.lines(t);parts=[]
        for contour in contours:
            if cv2.contourArea(contour.astype('float32'))<25:continue
            points=contour+np.array([x0-1.5,y0-1.5])
            curves=fit_tone_curve(points,tolerance,curve_sigma,importance,(x0,y0))
            if not curves:continue
            pair=lambda p:f'{p[0]:.2f},{p[1]:.2f}'
            parts.append('M'+pair(curves[0][0])+''.join('C'+' '.join(pair(p) for p in curve[1:]) for curve in curves)+'Z')
            segments+=len(curves)
        if parts:
            ET.SubElement(group,q('path'),{'id':f'tone-{i+1}','d':''.join(parts),'fill':fill,'fill-rule':'evenodd'});paths+=1
    visible=ET.SubElement(out,q('g'),{'id':'material-tones'})
    for i in range(len(shapes)):
        clipped=ET.SubElement(visible,q('g'),{'clip-path':f'url(#material-outline-{i})','opacity':'.999999'})
        ET.SubElement(clipped,q('use'),{'{'+XL+'}href':'#material-paint'})
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix='.svg',dir=output.parent,delete=False) as handle:temporary=Path(handle.name)
    try:
        ET.ElementTree(out).write(temporary,encoding='utf-8',xml_declaration=True)
        if not inspect_svg(temporary,strict=True)['valid']:raise ValueError('Export failed strict full-vector validation')
        temporary.replace(output)
    finally:
        if temporary.exists():temporary.unlink()
    return {'output':str(output.resolve()),'source_samples':int(valid.sum()),'tonal_paths':paths,'cubic_segments':segments,
            'outline_geometry_sha256':hashlib.sha256(json.dumps(shapes,sort_keys=True).encode()).hexdigest(),
            'bytes':output.stat().st_size,'maximum_scheduled_rgb_step':max_step,'representation':'Finite curved tonal regions; native gradients remain preferable for simpler surfaces.',
            'not_evaluated':['source segmentation','banding and contour quality','editing practicality','editor import']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','material','outline','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--exclude',type=Path);p.add_argument('--palette-mask',type=Path);p.add_argument('--report',type=Path)
    p.add_argument('--color-step',type=float,default=.6);p.add_argument('--blur',type=float,default=3.8)
    p.add_argument('--tolerance',type=float,default=.2);p.add_argument('--curve-sigma',type=float,default=.4)
    a=p.parse_args()
    try:
        if not .2<=a.color_step<=1 or not 0<=a.blur<=20 or not .05<=a.tolerance<=5 or not 0<=a.curve_sigma<=10:raise ValueError('Invalid fitting parameters')
        inputs={v.resolve() for v in [a.source,a.material,a.outline,a.exclude,a.palette_mask] if v}
        if a.output.suffix.lower()!='.svg' or a.output.resolve() in inputs or (a.report and (a.report.resolve() in inputs or a.report.resolve()==a.output.resolve())):raise ValueError('Keep SVG and report separate from source inputs and each other')
        result=build(a.source,a.material,a.outline,a.output,a.color_step,a.blur,a.tolerance,a.curve_sigma,a.exclude,a.palette_mask)
        if a.report:a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result,indent=2));return 0
    except (ValueError,TypeError,OSError,KeyError,ET.ParseError) as e:print(json.dumps({'valid':False,'error':str(e)}));return 2
if __name__=='__main__':raise SystemExit(main())
