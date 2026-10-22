#!/usr/bin/env python3
"""Fit cubic outlines to an isolated binary mask in its original coordinates.

Needs numpy, Pillow, scipy and opencv-python. This fits geometry only: it cannot
decide whether a pale region is a highlight, an opening or another object.
"""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter1d

NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)

def unit(v):
    return v/max(float(np.linalg.norm(v)),1e-12)

def evaluate(b,t):
    t=np.asarray(t);u=1-t
    return (u**3)[:,None]*b[0]+(3*u*u*t)[:,None]*b[1]+(3*u*t*t)[:,None]*b[2]+(t**3)[:,None]*b[3]

def fit(points,left,right,tolerance):
    if len(points)<=2:
        length=np.linalg.norm(points[-1]-points[0])/3
        return [np.array([points[0],points[0]+left*length,points[-1]+right*length,points[-1]])]
    distance=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
    if distance[-1]<1e-8:return []
    t=distance/distance[-1];best_error=float('inf');best_split=len(points)//2
    for _ in range(6):
        u=1-t;b0=u**3;b1=3*u*u*t;b2=3*u*t*t;b3=t**3
        a1=b1[:,None]*left;a2=b2[:,None]*right
        matrix=np.array([[np.sum(a1*a1),np.sum(a1*a2)],[np.sum(a1*a2),np.sum(a2*a2)]])
        residual=points-(b0+b1)[:,None]*points[0]-(b2+b3)[:,None]*points[-1]
        rhs=np.array([np.sum(a1*residual),np.sum(a2*residual)])
        try:al,ar=np.linalg.solve(matrix,rhs)
        except np.linalg.LinAlgError:al=ar=distance[-1]/3
        if min(al,ar)<1e-6 or max(al,ar)>distance[-1]*1.5:al=ar=distance[-1]/3
        curve=np.array([points[0],points[0]+left*al,points[-1]+right*ar,points[-1]])
        value=evaluate(curve,t);error=np.sum((value-points)**2,axis=1)
        split=int(np.argmax(error));maximum=error[split]
        if maximum<best_error:best_error=maximum;best_split=split
        if maximum<=tolerance*tolerance:return [curve]
        derivative=3*u[:,None]**2*(curve[1]-curve[0])+6*(u*t)[:,None]*(curve[2]-curve[1])+3*t[:,None]**2*(curve[3]-curve[2])
        second=6*u[:,None]*(curve[2]-2*curve[1]+curve[0])+6*t[:,None]*(curve[3]-2*curve[2]+curve[1])
        diff=value-points;denominator=np.sum(derivative*derivative+diff*second,axis=1)
        step=np.divide(np.sum(diff*derivative,axis=1),denominator,out=np.zeros(len(t)),where=np.abs(denominator)>1e-10)
        updated=np.clip(t-step,0,1);updated[0]=0;updated[-1]=1
        if np.any(np.diff(updated)<=0) or np.max(np.abs(updated-t))<1e-6:break
        t=updated
    split=max(1,min(len(points)-2,best_split));radius=min(5,split,len(points)-split-1)
    tangent=unit(points[split-radius]-points[split+radius])
    return fit(points[:split+1],left,tangent,tolerance)+fit(points[split:],-tangent,right,tolerance)

def resample(raw):
    closed=np.vstack([raw,raw[0]])
    distance=np.r_[0,np.cumsum(np.linalg.norm(np.diff(closed,axis=0),axis=1))]
    good=np.r_[True,np.diff(distance)>1e-9];distance=distance[good];closed=closed[good]
    positions=np.linspace(0,distance[-1],max(8,int(np.ceil(distance[-1]))),endpoint=False)
    return np.c_[np.interp(positions,distance,closed[:,0]),np.interp(positions,distance,closed[:,1])]

def closed_curve(raw,tolerance,sigma,guides,corner_angle):
    raw=resample(raw);n=len(raw)
    smooth=gaussian_filter1d(raw,sigma,axis=0,mode='wrap') if sigma else raw.copy()
    radius=min(8,max(1,n//12));before=np.roll(raw,radius,axis=0)-raw;after=np.roll(raw,-radius,axis=0)-raw
    dot=np.sum(before*after,axis=1)/np.maximum(np.linalg.norm(before,axis=1)*np.linalg.norm(after,axis=1),1e-12)
    corners=set()
    if corner_angle:
        candidates=np.flatnonzero(dot>-np.cos(np.deg2rad(corner_angle)))
        for k in candidates[np.argsort(dot[candidates])[::-1]]:
            if all(min((int(k)-j)%n,(j-int(k))%n)>radius*2 for j in corners):corners.add(int(k))
    for guide in guides:
        distances=np.linalg.norm(raw-guide,axis=1)
        if distances.min()<=12:
            nearby=np.flatnonzero(distances<=max(2.,distances.min()+3))
            corners.add(int(nearby[np.argmax(dot[nearby])]))
    for k in sorted(corners):
        distance=np.minimum((np.arange(n)-k)%n,(k-np.arange(n))%n)
        smooth+=np.exp(-.5*(distance/max(1.,sigma*2))**2)[:,None]*(raw[k]-smooth[k])
    splits=sorted(corners|{int(np.argmin(smooth[:,0])),int(np.argmax(smooth[:,0])),int(np.argmin(smooth[:,1])),int(np.argmax(smooth[:,1]))})
    curves=[]
    for j,start in enumerate(splits):
        end=splits[(j+1)%len(splits)]
        if end<=start:end+=n
        points=smooth[np.arange(start,end+1)%n];r=min(5,len(points)-1)
        left=unit(points[r]-points[0]) if start in corners else unit(smooth[(start+5)%n]-smooth[(start-5)%n])
        right=unit(points[-r-1]-points[-1]) if end%n in corners else unit(smooth[(end-5)%n]-smooth[(end+5)%n])
        curves.extend(fit(points,left,right,tolerance))
    return curves,len(corners)

def outline(mask,tolerance=.8,sigma=1.,min_area=3.,guides=(),corner_angle=65.):
    # Trace closer to pixel edges than contouring the original pixel centers.
    # Coordinates return immediately to source units; this adds no source detail.
    expanded=cv2.resize(mask.astype('uint8'),None,fx=2,fy=2,interpolation=cv2.INTER_NEAREST)
    contours,hierarchy=cv2.findContours(expanded,cv2.RETR_TREE,cv2.CHAIN_APPROX_NONE)
    commands=[];segments=0;retained=0;discarded=0;corners=0;holes=0
    for index,contour in enumerate(contours):
        if cv2.contourArea(contour)/4<min_area or len(contour)<3:discarded+=1;continue
        curves,count=closed_curve((contour[:,0,:].astype(float)+.5)/2,tolerance,sigma,guides,corner_angle)
        if not curves:continue
        pair=lambda p:f'{p[0]:.4f},{p[1]:.4f}'
        commands.append('M'+pair(curves[0][0])+''.join('C'+' '.join(pair(p) for p in c[1:]) for c in curves)+'Z')
        segments+=len(curves);corners+=count;retained+=1
        parent=int(hierarchy[0,index,3]);depth=0
        while parent!=-1:depth+=1;parent=int(hierarchy[0,parent,3])
        if depth%2:holes+=1
    return ''.join(commands),{'contours':retained,'hole_contours':holes,'discarded_small_contours':discarded,'cubic_segments':segments,'corner_anchors':corners}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--white-ink',action='store_true')
    parser.add_argument('--tolerance',type=float,default=.8,help='Fit error relative to the smoothed contour, in source pixels')
    parser.add_argument('--sigma',type=float,default=1.,help='Contour smoothing in source pixels; 0 disables')
    parser.add_argument('--min-area',type=float,default=3.)
    parser.add_argument('--corner-angle',type=float,default=65.,help='Minimum local turn for a corner anchor; 0 disables automatic anchors')
    parser.add_argument('--corners',type=Path,help='Optional JSON list of [x,y] corner guides in source coordinates')
    args=parser.parse_args()
    if args.input.resolve()==args.output.resolve():parser.error('Keep input and output separate')
    if args.output.suffix.lower()!='.svg':parser.error('Output must end in .svg')
    if not .05<=args.tolerance<=10 or not 0<=args.sigma<=5 or args.min_area<0 or not 0<=args.corner_angle<=170:parser.error('Invalid fit parameter')
    source=Image.open(args.input).convert('RGBA')
    matte=Image.new('RGBA',source.size,'black' if args.white_ink else 'white')
    gray=np.asarray(Image.alpha_composite(matte,source).convert('L'))
    mask=gray>=128 if args.white_ink else gray<128
    guides=[]
    if args.corners:
        guides=np.asarray(json.loads(args.corners.read_text(encoding='utf-8')),dtype=float)
        if guides.ndim!=2 or guides.shape[1]!=2 or not np.isfinite(guides).all():parser.error('Corners must be a finite list of [x,y]')
    d,report=outline(mask,args.tolerance,args.sigma,args.min_area,guides,args.corner_angle)
    if not d:parser.error('No foreground contours remain')
    width,height=source.size
    root=ET.Element(f'{{{NS}}}svg',{'width':str(width),'height':str(height),'viewBox':f'0 0 {width} {height}'})
    ET.SubElement(root,f'{{{NS}}}path',{'id':'outline','d':d,'fill':'#000000','fill-rule':'evenodd','clip-rule':'evenodd'})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    ET.ElementTree(root).write(args.output,encoding='utf-8',xml_declaration=True)
    print(json.dumps({'output':str(args.output.resolve()),'dimensions':[width,height],**report,'tolerance_to_smoothed_contour':args.tolerance,'smoothing_sigma':args.sigma,'scope':'geometry fitting only; segmentation and visual fidelity require review'}))

if __name__=='__main__':main()
