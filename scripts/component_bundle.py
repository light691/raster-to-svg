#!/usr/bin/env python3
"""Lock filled SVG components, assemble paints, and reject geometry regressions.

Outline inputs must be standalone, transparent, same-canvas SVGs containing
direct filled shapes. Segmentation correctness is reviewed before locking.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import tempfile
import xml.etree.ElementTree as ET

from verify_svg import inspect_svg

NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)
SHAPES={'path','rect','circle','ellipse','polygon','polyline'}
GEOMETRY={'d','x','y','width','height','rx','ry','cx','cy','r','points','transform','fill-rule','clip-rule'}
PAINT_ATTRS={'fill','stroke','id'}

def tag(e):return e.tag.rsplit('}',1)[-1]
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2),encoding='utf-8')

def geometry(e):
    unknown=set(e.attrib)-GEOMETRY-PAINT_ATTRS
    if unknown:raise ValueError('Unsupported outline attributes: '+', '.join(sorted(unknown)))
    if e.get('stroke','none')!='none' or e.get('fill','black')=='none':
        raise ValueError('Outline inputs must use filled geometry without strokes')
    if not e.get('d') and tag(e)=='path':raise ValueError('Empty path')
    attrs={k:v for k,v in e.attrib.items() if k in GEOMETRY}
    attrs.setdefault('fill-rule','nonzero')
    attrs.setdefault('clip-rule',attrs['fill-rule'])
    if attrs['fill-rule'] not in {'evenodd','nonzero'} or attrs['clip-rule']!=attrs['fill-rule']:
        raise ValueError('Use matching valid fill-rule and clip-rule so counters survive clipping')
    return {'tag':tag(e),'attributes':attrs}

def canvas(root):
    result={k:root.get(k) for k in ('width','height','viewBox')}
    if any(v is None for v in result.values()):raise ValueError('Explicit width, height and viewBox required')
    try:
        dims=[float(re.sub(r'px$','',result[k])) for k in ('width','height')]
        box=[float(v) for v in re.split(r'[\s,]+',result['viewBox'].strip())]
        valid=len(box)==4 and all(math.isfinite(v) for v in [*dims,*box]) and min(*dims,*box[2:])>0
    except ValueError:valid=False
    if not valid:raise ValueError('Finite positive pixel width, height and viewBox extents required')
    if set(root.attrib)-{'width','height','viewBox','version'}:raise ValueError('Unsupported root placement/style; normalize outline first')
    return result

def read_components(manifest):
    data=load(manifest)
    if set(data)-{'title','components'}:raise ValueError('Unsupported manifest fields')
    if not isinstance(data.get('components'),list) or not data['components']:raise ValueError('Nonempty components list required')
    records=[];ids=set();common=None
    for component in data['components']:
        if set(component)-{'id','outline','fill','paint'}:raise ValueError('Unsupported component fields; geometry changes belong in a separately reviewed outline')
        name=component['id']
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',name) or name in ids:raise ValueError('Unique XML-safe component IDs required')
        ids.add(name);path=Path(manifest).parent/component['outline']
        check=inspect_svg(path,strict=True)
        if not check['valid']:raise ValueError('Invalid outline: '+str(check['issues']))
        root=ET.parse(path).getroot();space=canvas(root)
        if common is not None and space!=common:raise ValueError('Component canvases differ; preserve source coordinates')
        common=space;shapes=[]
        for e in root:
            if tag(e) in {'title','desc','metadata'}:continue
            if tag(e) not in SHAPES or len(e):raise ValueError('Use direct filled shapes; flatten inherited transforms/styles explicitly')
            shapes.append(geometry(e))
        if not shapes:raise ValueError('No outline geometry in '+str(path))
        records.append({'id':name,'shapes':shapes})
    return data,{'schema':1,'canvas':common,'components':records,'scope':'Geometry integrity only; operator reviews source fidelity before locking.'}

def checked(manifest,lock):
    data,current=read_components(manifest);expected=load(lock)
    if digest(current)!=expected.get('geometry_sha256'):raise ValueError('Locked geometry, component inventory, canvas or drawing order changed; repair the candidate or review a separate new geometry version')
    return data,current

def color(value):
    if not isinstance(value,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',value):raise ValueError('Use #RRGGBB colors')
    return value

def paint(parent,name,model):
    kind=model['kind']
    if kind=='linear':
        values=model['coordinates']
        if len(values)!=4 or not all(math.isfinite(float(v)) for v in values):raise ValueError('Invalid linear gradient coordinates')
        attrs=dict(zip(('x1','y1','x2','y2'),map(str,values)));gradient='linearGradient'
    elif kind=='radial':
        matrix=model['matrix'];focal=model.get('focal',[0,0])
        if len(matrix)!=6 or len(focal)!=2 or not all(math.isfinite(float(v)) for v in [*matrix,*focal]):raise ValueError('Invalid radial transform/focal point')
        if float(focal[0])**2+float(focal[1])**2>=1:raise ValueError('Radial focal point must be inside ellipse')
        if abs(float(matrix[0])*float(matrix[3])-float(matrix[1])*float(matrix[2]))<1e-10:raise ValueError('Degenerate gradient transform')
        attrs={'cx':'0','cy':'0','r':'1','fx':str(focal[0]),'fy':str(focal[1]),'gradientTransform':'matrix('+' '.join(map(str,matrix))+')'};gradient='radialGradient'
    else:raise ValueError('Paint kind must be linear or radial')
    e=ET.SubElement(parent,f'{{{NS}}}'+gradient,{'id':'paint-'+name,'gradientUnits':'userSpaceOnUse','color-interpolation':'sRGB',**attrs})
    stops=model['stops'];previous=-1
    if len(stops)<2:raise ValueError('At least two stops required')
    for offset,rgb in stops:
        offset=float(offset)
        if not math.isfinite(offset) or not 0<=offset<=1 or offset<previous:raise ValueError('Stops must be ordered in [0,1]')
        previous=offset
        ET.SubElement(e,f'{{{NS}}}stop',{'offset':str(offset),'stop-color':color(rgb)})
    return 'url(#paint-'+name+')'

def assemble(manifest,lock,output):
    data,record=checked(manifest,lock)
    protected={Path(manifest).resolve(),Path(lock).resolve()}
    protected.update((Path(manifest).parent/c['outline']).resolve() for c in data['components'])
    protected.update((Path(manifest).parent/c['paint']).resolve() for c in data['components'] if c.get('paint'))
    if Path(output).resolve() in protected:raise ValueError('Output cannot overwrite inputs or lock')
    if Path(output).suffix.lower()!='.svg':raise ValueError('Output must end in .svg')
    root=ET.Element(f'{{{NS}}}svg',record['canvas']);defs=ET.SubElement(root,f'{{{NS}}}defs')
    ET.SubElement(root,f'{{{NS}}}title').text=data.get('title','Locked component reconstruction')
    for component,geometry_record in zip(data['components'],record['components']):
        name=component['id']
        fill=paint(defs,name,load(Path(manifest).parent/component['paint'])) if component.get('paint') else color(component.get('fill','#808080'))
        group=ET.SubElement(root,f'{{{NS}}}g',{'id':'component-'+name})
        for i,shape in enumerate(geometry_record['shapes']):
            clip_id='clip-'+name+('' if len(geometry_record['shapes'])==1 else '-'+str(i))
            clip=ET.SubElement(defs,f'{{{NS}}}clipPath',{'id':clip_id,'clipPathUnits':'userSpaceOnUse'})
            ET.SubElement(clip,f'{{{NS}}}'+shape['tag'],{**shape['attributes'],'id':f'geometry-{name}-{i}'})
            # Paint in source space; clip each original filled shape separately.
            # Aggregating mixed winding rules can fill counters in a renderer.
            x,y,w,h=re.split(r'[\s,]+',record['canvas']['viewBox'].strip())
            ET.SubElement(group,f'{{{NS}}}rect',{'x':x,'y':y,'width':w,'height':h,'clip-path':'url(#'+clip_id+')','fill':fill})
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix='.svg',dir=Path(output).parent,delete=False) as handle:temporary=Path(handle.name)
    try:
        ET.ElementTree(root).write(temporary,encoding='utf-8',xml_declaration=True)
        audit(temporary,lock)
        temporary.replace(output)
    finally:
        if temporary.exists():temporary.unlink()
    return {'output':str(Path(output).resolve()),'geometry_sha256':digest(record),'components':len(record['components']),'geometry_intact':True,'visual_quality':'unevaluated','editor_import':'unverified'}

def audit(output,lock):
    expected=load(lock);record=expected['record'];root=ET.parse(output).getroot()
    if not inspect_svg(output,strict=True)['valid']:raise ValueError('Output is not strict full-vector SVG')
    if canvas(root)!=record['canvas']:raise ValueError('Output canvas changed')
    groups=[e for e in root if tag(e) not in {'title','desc','metadata','defs'}]
    if [e.get('id') for e in groups]!=['component-'+c['id'] for c in record['components']]:raise ValueError('Component inventory or drawing order changed')
    definitions={e.get('id'):e for e in root.iter() if e.get('id')}
    if len(definitions)!=sum(bool(e.get('id')) for e in root.iter()):raise ValueError('Duplicate resource IDs')
    for group,component in zip(groups,record['components']):
        if tag(group)!='g' or set(group.attrib)!={'id'}:raise ValueError('Unexpected component placement, clipping, opacity or styling')
        name=component['id']
        if len(group)!=len(component['shapes']):raise ValueError('Unexpected component paint inventory')
        fills=[]
        for i,(e,shape) in enumerate(zip(group,component['shapes'])):
            clip_id='clip-'+name+('' if len(component['shapes'])==1 else '-'+str(i));clip=definitions.get(clip_id)
            if clip is None or tag(clip)!='clipPath' or clip.attrib!={'id':clip_id,'clipPathUnits':'userSpaceOnUse'}:raise ValueError('Missing or changed component clip')
            if [geometry(v) for v in clip]!=[shape]:raise ValueError('Component geometry changed: '+name)
            if tag(e)!='rect' or len(e):raise ValueError('Unexpected component paint placement')
            x,y,w,h=re.split(r'[\s,]+',record['canvas']['viewBox'].strip())
            placement={'x':x,'y':y,'width':w,'height':h,'clip-path':'url(#'+clip_id+')'}
            if {k:v for k,v in e.attrib.items() if k!='fill'}!=placement:raise ValueError('Component paint coverage/placement changed')
            fill=e.get('fill','');fills.append(fill)
            if not re.fullmatch(r'#[0-9a-fA-F]{6}|url\(#paint-[A-Za-z][A-Za-z0-9_-]*\)',fill):raise ValueError('Unexpected paint')
        if len(set(fills))!=1:raise ValueError('Component paint differs between filled shapes')
    for e in root.iter():
        if tag(e)=='stop':
            if set(e.attrib)-{'offset','stop-color'}:raise ValueError('Unexpected gradient opacity/style')
            color(e.get('stop-color'))
        if tag(e) in {'linearGradient','radialGradient'} and set(e.attrib)-{'id','gradientUnits','color-interpolation','x1','x2','y1','y2','cx','cy','r','fx','fy','gradientTransform'}:
            raise ValueError('Unexpected gradient opacity, inheritance or styling')
    return {'geometry_intact':True,'components':len(groups),'scope':'Locked geometry, canvas and component coverage; visual quality/editor import unevaluated.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('lock');p.add_argument('manifest',type=Path);p.add_argument('record',type=Path)
    for name in ('check','build'):
        p=sub.add_parser(name);p.add_argument('manifest',type=Path);p.add_argument('--lock',type=Path,required=True)
        if name=='build':p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('audit');p.add_argument('svg',type=Path);p.add_argument('--lock',type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.command=='lock':
            if args.record.exists():raise ValueError('Lock exists; use a new record for an explicitly reviewed geometry revision')
            data,record=read_components(args.manifest)
            protected=[args.manifest.resolve(),*[(args.manifest.parent/c['outline']).resolve() for c in data['components']]]
            if args.record.resolve() in protected:raise ValueError('Lock cannot overwrite source')
            result={'record':record,'geometry_sha256':digest(record)};write(args.record,result)
        elif args.command=='check':_,record=checked(args.manifest,args.lock);result={'geometry_intact':True,'geometry_sha256':digest(record)}
        elif args.command=='build':result=assemble(args.manifest,args.lock,args.output)
        else:result=audit(args.svg,args.lock)
        print(json.dumps(result,indent=2));return 0
    except (ValueError,KeyError,TypeError,OSError,ET.ParseError) as e:
        print(json.dumps({'valid':False,'error':str(e)}));return 2

if __name__=='__main__':sys.exit(main())
