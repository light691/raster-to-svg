#!/usr/bin/env python3
"""Fit clean angular outlines to an isolated mask; preserve its source canvas."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import cv2
import numpy as np
from PIL import Image

NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)

def linefit(points):
    weights=np.ones(len(points))
    for _ in range(4):
        center=np.average(points,axis=0,weights=weights)
        centered=points-center
        covariance=(centered*weights[:,None]).T@centered
        _,vectors=np.linalg.eigh(covariance)
        direction=vectors[:,-1]
        normal=np.array([-direction[1],direction[0]])
        errors=np.abs(centered@normal)
        weights=np.minimum(1,1.1/np.maximum(errors,1e-6))
    return center,direction

def outline(mask,tolerance,blur,rounding,min_area):
    if blur:mask=cv2.GaussianBlur(mask,(0,0),blur)
    contours,_=cv2.findContours((mask>=128).astype(np.uint8),cv2.RETR_TREE,cv2.CHAIN_APPROX_NONE)
    paths=[];vertices=0
    for contour in contours:
        if cv2.contourArea(contour)<min_area:continue
        points=contour[:,0,:].astype(float)
        polygon=cv2.approxPolyDP(contour,tolerance,True)[:,0,:].astype(float)
        if len(polygon)<3:continue
        indices=[int(np.argmin(np.sum((points-p)**2,axis=1))) for p in polygon]
        lines=[]
        for i,start in enumerate(indices):
            end=indices[(i+1)%len(indices)]
            span=points[start:end+1] if end>start else np.concatenate([points[start:],points[:end+1]])
            if len(span)>12:lines.append(linefit(span[2:-2]))
            else:
                delta=polygon[(i+1)%len(polygon)]-polygon[i]
                lines.append((polygon[i],delta/max(np.linalg.norm(delta),1e-9)))
        revised=[]
        for i,corner in enumerate(polygon):
            p,u=lines[(i-1)%len(lines)];q,v=lines[i]
            matrix=np.column_stack([u,-v])
            if abs(np.linalg.det(matrix))>.15:
                crossing=p+u*np.linalg.solve(matrix,q-p)[0]
                revised.append(crossing if np.linalg.norm(crossing-corner)<max(1.25*tolerance,.5) else corner)
            else:revised.append(corner)
        polygon=np.array(revised)
        before=[];after=[]
        for i,point in enumerate(polygon):
            left=polygon[(i-1)%len(polygon)]-point;right=polygon[(i+1)%len(polygon)]-point
            la=np.linalg.norm(left);lb=np.linalg.norm(right)
            radius=min(rounding,la*.07,lb*.07)
            before.append(point+left/max(la,1e-9)*radius)
            after.append(point+right/max(lb,1e-9)*radius)
        d=f'M{after[-1][0]:.3f} {after[-1][1]:.3f}'
        for point,pre,post in zip(polygon,before,after):
            d+=f'L{pre[0]:.3f} {pre[1]:.3f}Q{point[0]:.3f} {point[1]:.3f} {post[0]:.3f} {post[1]:.3f}'
        paths.append(d+'Z');vertices+=len(polygon)
    return ' '.join(paths),len(paths),vertices

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--tolerance',type=float,default=1.5,help='Contour simplification in source pixels')
    parser.add_argument('--blur',type=float,default=.85,help='Mask denoising sigma in pixels, 0 disables')
    parser.add_argument('--round',type=float,default=.3,help='Subpixel corner rounding; 0 keeps sharp corners')
    parser.add_argument('--min-area',type=float,default=3)
    parser.add_argument('--white-ink',action='store_true',help='White foreground on black rather than black on white')
    args=parser.parse_args()
    if args.input.resolve()==args.output.resolve():parser.error('Keep source and output paths separate')
    if args.output.suffix.lower()!='.svg':parser.error('Output must end in .svg')
    if not .05<=args.tolerance<=10 or not 0<=args.blur<=5 or not 0<=args.round<=5 or args.min_area<0:parser.error('Invalid fit parameter')
    source=Image.open(args.input).convert('RGBA')
    matte=Image.new('RGBA',source.size,'black' if args.white_ink else 'white')
    gray=np.asarray(Image.alpha_composite(matte,source).convert('L'))
    mask=gray if args.white_ink else 255-gray
    d,contours,vertices=outline(mask,args.tolerance,args.blur,args.round,args.min_area)
    if not contours:parser.error('No foreground contours remain')
    width,height=source.size
    root=ET.Element(f'{{{NS}}}svg',{'width':str(width),'height':str(height),'viewBox':f'0 0 {width} {height}'})
    ET.SubElement(root,f'{{{NS}}}path',{'d':d,'fill':'#000000','fill-rule':'evenodd','clip-rule':'evenodd'})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    ET.ElementTree(root).write(args.output,encoding='utf-8',xml_declaration=True)
    print(json.dumps({'output':str(args.output.resolve()),'dimensions':[width,height],'contours':contours,'corners':vertices,'tolerance':args.tolerance}))

if __name__=='__main__':main()
