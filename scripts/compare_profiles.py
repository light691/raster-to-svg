#!/usr/bin/env python3
"""Compare source-space color sections through bevels or connected shading.

Inputs are same-canvas source and freshly rendered candidate PNGs. Emits
source/candidate line overlays, luminance charts and measured RGB samples.
These diagnostics do not decide artistic quality or replace SVG detail renders.
Requires Pillow and NumPy.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw


def pixels(image,xy):
    x=np.clip(xy[...,0],0,image.shape[1]-1);y=np.clip(xy[...,1],0,image.shape[0]-1)
    x0=x.astype(int);y0=y.astype(int);x1=np.minimum(x0+1,image.shape[1]-1);y1=np.minimum(y0+1,image.shape[0]-1)
    tx=(x-x0)[...,None];ty=(y-y0)[...,None]
    return (image[y0,x0]*(1-tx)+image[y0,x1]*tx)*(1-ty)+(image[y1,x0]*(1-tx)+image[y1,x1]*tx)*ty


def analyze(source,candidate,sections,output):
    output=Path(output)
    inputs=[Path(source).resolve(),Path(candidate).resolve(),Path(sections).resolve()]
    if output.resolve() in inputs or any(output.resolve() in p.parents for p in inputs):
        raise ValueError('Keep the report directory separate from the inputs')
    images=[Image.open(p).convert('RGBA') for p in inputs[:2]]
    if images[0].size!=images[1].size:raise ValueError('Source and candidate must use the same native pixel canvas')
    arrays=[]
    for im in images:
        a=np.array(im).astype(float);alpha=a[:,:,3:4]/255
        arrays.append(a[:,:,:3]*alpha+255*(1-alpha))
    config=json.loads(inputs[2].read_text(encoding='utf-8'))
    if not isinstance(config,list) or not config:raise ValueError('Sections must be a nonempty list')
    rows=[];panels=[]
    for index,section in enumerate(config):
        ends=np.asarray([section['start'],section['end']],dtype=float)
        if ends.shape!=(2,2) or not np.isfinite(ends).all():raise ValueError('Use finite [x,y] section endpoints')
        w,h=images[0].size
        if np.any(ends<0) or np.any(ends[:,0]>w-1) or np.any(ends[:,1]>h-1):raise ValueError('Section endpoint lies outside source canvas')
        v=ends[1]-ends[0];length=float(np.linalg.norm(v))
        if length<1:raise ValueError('Section must be at least one source pixel long')
        normal=np.array([-v[1],v[0]])/length
        radius=section.get('radius',2)
        if not isinstance(radius,int) or not 0<=radius<=20:raise ValueError('Radius must be an integer from 0 to 20')
        coordinates=ends[0]+np.linspace(0,1,256)[:,None]*v
        sample_xy=coordinates[:,None,:]+np.arange(-radius,radius+1)[None,:,None]*normal
        samples=[np.median(pixels(a,sample_xy),axis=1) for a in arrays]
        lum=[s@np.array([.2126,.7152,.0722]) for s in samples]
        rows.append({'name':str(section.get('name',index+1)),'start':ends[0].tolist(),'end':ends[1].tolist(),
                     'strip_radius_source_px':radius,'rgb_rmse':float(np.sqrt(np.mean((samples[0]-samples[1])**2))),
                     'source_luminance_range':[float(lum[0].min()),float(lum[0].max())],
                     'candidate_luminance_range':[float(lum[1].min()),float(lum[1].max())],
                     'source_rgb':samples[0].round(3).tolist(),'candidate_rgb':samples[1].round(3).tolist()})
        panel=Image.new('RGB',(1000,430),'white');draw=ImageDraw.Draw(panel)
        draw.text((15,10),rows[-1]['name']+' | source blue, candidate orange | white composite',fill='black')
        draw.rectangle((50,55,965,320),outline='#777777')
        for y in [0,64,128,192,255]:
            py=320-y;draw.line((50,py,965,py),fill='#eeeeee');draw.text((12,py-5),str(y),fill='#666666')
        for color,values in zip(['#1673b1','#d56b15'],lum):
            draw.line([(50+i*915/255,320-value) for i,value in enumerate(values)],fill=color,width=2)
        draw.text((50,334),f"A {ends[0].tolist()} -> B {ends[1].tolist()}; {length:.1f} source px",fill='black')
        draw.text((50,354),f"RGB RMSE {rows[-1]['rgb_rmse']:.2f}. Use line placement and the source to interpret differences; no pass score.",fill='black')
        panels.append(panel)
    output.mkdir(parents=True,exist_ok=True)
    chart=Image.new('RGB',(1000,430*len(panels)),'white')
    for i,p in enumerate(panels):chart.paste(p,(0,430*i))
    chart.save(output/'profiles.png')
    overlay=Image.new('RGB',(images[0].width*2,images[0].height),'white')
    for i,array in enumerate(arrays):
        im=Image.fromarray(np.clip(np.rint(array),0,255).astype('uint8'));d=ImageDraw.Draw(im)
        for j,s in enumerate(config):
            d.line([tuple(s['start']),tuple(s['end'])],fill='#00b4ff',width=3)
            d.text(tuple(s['start']),str(j+1)+' A',fill='#000000');d.text(tuple(s['end']),'B',fill='#000000')
        overlay.paste(im,(images[0].width*i,0))
    overlay.save(output/'section-locations.png')
    report={'diagnostic_only':True,'canvas':list(images[0].size),'sections':rows}
    (output/'profiles.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['source','candidate','sections','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    try:
        result=analyze(a.source,a.candidate,a.sections,a.output)
        print(json.dumps({'diagnostic_only':True,'sections':len(result['sections']),'output':str(a.output.resolve())}));return 0
    except (ValueError,KeyError,TypeError,OSError) as e:print(json.dumps({'error':str(e)}));return 2


if __name__=='__main__':raise SystemExit(main())
