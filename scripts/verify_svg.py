#!/usr/bin/env python3
"""Check SVG structure only; does not assess visual quality or editor behavior."""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SHAPES={'path','rect','circle','ellipse','line','polygon','polyline'}
STRICT_TAGS=SHAPES|{'svg','g','defs','title','desc','linearGradient','radialGradient','stop','clipPath','use','metadata'}
METADATA_NAMESPACES={'http://www.w3.org/1999/02/22-rdf-syntax-ns#','http://purl.org/dc/elements/1.1/','http://creativecommons.org/ns#'}

def inspect_svg(path,strict=False):
    counts={}; issues=[]; dimensions={}; ids=set(); refs=set(); depth=0; metadata_depth=None
    for event,element in ET.iterparse(path,events=('start','end')):
        tag=element.tag.rsplit('}',1)[-1]
        if event=='start':
            if depth==0:
                if tag!='svg': issues.append('Root element is not svg')
                dimensions={k:element.get(k) for k in ('width','height','viewBox')}
            depth+=1
            if tag=='metadata': metadata_depth=depth
            counts[tag]=counts.get(tag,0)+1
            if tag in {'image','foreignObject','script'}: issues.append(f'Forbidden element: {tag}')
            namespace=element.tag[1:].split('}',1)[0] if element.tag.startswith('{') else ''
            inert_metadata=metadata_depth is not None and namespace in METADATA_NAMESPACES
            if strict and tag not in STRICT_TAGS and not inert_metadata: issues.append(f'Unsupported full-vector element: {tag}')
            if element.get('id'): ids.add(element.get('id'))
            for key,value in element.attrib.items():
                name=key.rsplit('}',1)[-1]
                if name.lower().startswith('on'): issues.append(f'Active event handler: {name}')
                if name=='href':
                    if value.startswith('#'): refs.add(value[1:])
                    else: issues.append('External or embedded href')
                for target in re.findall(r'url\(\s*[\"\x27]?([^\s)\"\x27]+)',value,re.I):
                    if target.startswith('#'): refs.add(target[1:])
                    else: issues.append('External CSS resource')
                if strict and (name in {'filter','mask'} or (name=='style' and re.search(r'\b(filter|mask|mix-blend-mode)\s*:',value,re.I))):
                    issues.append(f'Rasterizing/unsupported effect attribute: {name}')
        else:
            if depth==metadata_depth: metadata_depth=None
            depth-=1
            element.clear()
    if sum(counts.get(tag,0) for tag in SHAPES)==0: issues.append('No vector geometry')
    for missing in refs-ids: issues.append(f'Missing local resource: {missing}')
    return {'file':str(Path(path).resolve()),'strict':strict,'validation_scope':'structure-only',
            'not_evaluated':['visual_quality','editability','editor_import'],'valid':not issues,'dimensions':dimensions,
            'counts':counts,'issues':sorted(set(issues))}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('svg',type=Path)
    parser.add_argument('--strict',action='store_true')
    args=parser.parse_args()
    try: report=inspect_svg(args.svg,args.strict)
    except (ET.ParseError,OSError) as error:
        print(json.dumps({'validation_scope':'structure-only','valid':False,'error':str(error)}));return 1
    print(json.dumps(report,indent=2))
    return 0 if report['valid'] else 1

if __name__=='__main__':sys.exit(main())
