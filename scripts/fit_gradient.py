#!/usr/bin/env python3
"""Fit a source-sampled linear or elliptical radial paint to one material mask.

Requires numpy, Pillow, scipy and OpenCV. This is a simple lighting model, not
a general shader for branching metallic strokes. Inspect the rendered proof.
"""
import argparse
import json
import math
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter1d

def rgb(values):return '#'+''.join(f'{int(v):02x}' for v in np.clip(np.rint(values),0,255))

def radial_t(x,y,matrix,focal):
    a,b,c,d,cx,cy=matrix;det=a*d-b*c
    px=(d*(x-cx)-c*(y-cy))/det;py=(-b*(x-cx)+a*(y-cy))/det
    dx=px-focal[0];dy=py-focal[1];dot=dx*focal[0]+dy*focal[1];q=1-focal[0]**2-focal[1]**2
    return (dot+np.sqrt(np.maximum(0,dot*dot+q*(dx*dx+dy*dy))))/q

def fit_stops(t,colors,train,number):
    positions=np.linspace(0,1,number);bins=np.clip(np.rint(t*(number-1)).astype(int),0,number-1)
    values=np.full((number,3),np.nan)
    for i in range(number):
        selected=colors[train&(bins==i)]
        if len(selected):values[i]=np.median(selected,axis=0)
    known=np.isfinite(values[:,0])
    if not known.any():raise ValueError('No fit samples')
    for ch in range(3):values[:,ch]=np.interp(positions,positions[known],values[known,ch])
    values=gaussian_filter1d(values,.65,axis=0,mode='nearest')
    pred=np.column_stack([np.interp(t,positions,values[:,ch]) for ch in range(3)])
    rmse=float(np.sqrt(np.mean((pred[~train]-colors[~train])**2)))
    return rmse,[[float(p),rgb(c)] for p,c in zip(positions,values)]

def fit(source,mask,kind='auto',number=16,erosion=2,ellipse=None,samples=12000):
    rgba=np.asarray(Image.open(source).convert('RGBA'))
    gray=np.asarray(Image.open(mask).convert('L'))
    if gray.shape!=rgba.shape[:2]:raise ValueError('Source and mask must share their original canvas')
    region=(gray<128)&(rgba[:,:,3]>=250)
    if erosion:region=cv2.erode(region.astype('uint8'),np.ones((2*erosion+1,2*erosion+1),np.uint8)).astype(bool)
    yy,xx=np.where(region)
    if len(xx)<30:raise ValueError('Too few interior source samples; inspect mask or reduce erosion')
    bounds=[float(xx.min()),float(yy.min()),float(xx.max()),float(yy.max())]
    rng=np.random.default_rng(0)
    selected=rng.choice(len(xx),size=min(samples,len(xx)),replace=False);x=xx[selected].astype(float);y=yy[selected].astype(float)
    colors=rgba[y.astype(int),x.astype(int),:3].astype(float)
    train=rng.random(len(x))<.75
    if train.all() or (~train).all():raise ValueError('Insufficient independent sample split')
    candidates=[]
    if kind in ('auto','linear'):
        for angle in np.arange(0,180,5):
            u=math.cos(math.radians(angle));v=math.sin(math.radians(angle));s=x*u+y*v;lo=float(s.min());hi=float(s.max())
            if hi-lo<1e-6:continue
            t=(s-lo)/(hi-lo);error,stops=fit_stops(t,colors,train,number)
            center=np.array([(bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2]);projection=center@[u,v]
            a=center+np.array([u,v])*(lo-projection);b=center+np.array([u,v])*(hi-projection)
            candidates.append((error,{'kind':'linear','coordinates':[*a.tolist(),*b.tolist()],'stops':stops}))
    if kind in ('auto','radial'):
        if ellipse is None:ellipse=[(bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2,max(1,(bounds[2]-bounds[0])/2),max(1,(bounds[3]-bounds[1])/2),0]
        cx,cy,rx,ry,angle=ellipse
        if rx<=0 or ry<=0:raise ValueError('Ellipse radii must be positive')
        co=math.cos(math.radians(angle));si=math.sin(math.radians(angle));matrix=[co*rx,si*rx,-si*ry,co*ry,cx,cy]
        for fx in np.arange(-.75,.751,.15):
            for fy in np.arange(-.75,.751,.15):
                if fx*fx+fy*fy>=.85**2:continue
                focal=[float(fx),float(fy)];t=radial_t(x,y,matrix,focal)
                error,stops=fit_stops(t,colors,train,number)
                candidates.append((error,{'kind':'radial','matrix':matrix,'focal':focal,'stops':stops}))
        # A radial paint boundary need not coincide with the object boundary.
        # A larger displaced field can retain a bright rim on one side and a
        # dark rim on the other; an object-bounded radial cannot express that.
        for dx in np.linspace(-.9,.9,7):
            for dy in np.linspace(-.9,.9,7):
                broad=[co*rx*2.5,si*rx*2.5,-si*ry*2.5,co*ry*2.5,cx+co*rx*dx-si*ry*dy,cy+si*rx*dx+co*ry*dy]
                t=radial_t(x,y,broad,[0,0]);error,stops=fit_stops(t,colors,train,number)
                candidates.append((error,{'kind':'radial','matrix':broad,'focal':[0,0],'stops':stops,'parameterization':'expanded-center'}))
    if not candidates:raise ValueError('No usable gradient candidate')
    candidates.sort(key=lambda v:v[0]);error,model=candidates[0]
    report={'source':str(Path(source).resolve()),'mask':str(Path(mask).resolve()),'kind':model['kind'],'sample_count':len(x),'holdout_samples':int((~train).sum()),'holdout_rgb_rmse_0_255':error,'candidate_models':len(candidates),'stops':number,'scope':'Simple material paint fit; error is not an artist-quality score. Geometry, junction continuity, visual quality and editor import need separate review.'}
    return model,report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--mask',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--report',type=Path)
    parser.add_argument('--kind',choices=['auto','linear','radial'],default='auto')
    parser.add_argument('--stops',type=int,default=16);parser.add_argument('--erosion',type=int,default=2)
    parser.add_argument('--ellipse',help='Source-space cx,cy,rx,ry,angle_degrees for radial fitting')
    parser.add_argument('--samples',type=int,default=12000)
    args=parser.parse_args()
    try:
        if not 2<=args.stops<=64 or not 0<=args.erosion<=20 or not 100<=args.samples<=100000:raise ValueError('Invalid fit parameters')
        protected={args.source.resolve(),args.mask.resolve()}
        if args.output.resolve() in protected or (args.report and (args.report.resolve() in protected or args.report.resolve()==args.output.resolve())):raise ValueError('Outputs must be separate from inputs and each other')
        ellipse=[float(v) for v in args.ellipse.split(',')] if args.ellipse else None
        if ellipse is not None and (len(ellipse)!=5 or not all(math.isfinite(v) for v in ellipse)):raise ValueError('Ellipse needs five finite values')
        model,report=fit(args.source,args.mask,args.kind,args.stops,args.erosion,ellipse,args.samples)
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(model,indent=2),encoding='utf-8')
        if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report,indent=2));return 0
    except (ValueError,TypeError,OSError) as e:print(json.dumps({'valid':False,'error':str(e)}));return 2

if __name__=='__main__':sys.exit(main())
