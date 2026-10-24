"""Prueft die Fronttaschen direkt an der finalen Geometrie."""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET
if len(sys.argv)>1:
    sys.path.insert(0,sys.argv[1])
import numpy as np
import manifold3d as m
from build import as_solid, read_mesh

BASE=Path(__file__).resolve().parent
ns={'c':'http://www.collada.org/2005/11/COLLADASchema'}
report=['Front-Taschen aus den exportierten Dateien.']

def scene(folder):
    parts={}
    for g in ET.parse(folder/'gehaeuse_geteilt.dae').findall('.//c:geometry',ns):
        xyz=np.array(list(map(float,g.find('.//c:float_array',ns).text.split()))).reshape((-1,3))
        ix=np.array(list(map(int,g.find('.//c:triangles/c:p',ns).text.split())),dtype=np.uint64).reshape((-1,3))
        parts[g.get('name')]=m.Manifold(m.Mesh64(np.ascontiguousarray(xyz[:,[0,2,1]]),np.ascontiguousarray(ix[:,[0,2,1]])))
    return parts

def difference(a,b):
    d=(a-b)+(b-a)
    assert d.status()==m.Error.NoError
    return abs(d.volume())

parts=scene(BASE)
layout=json.loads((BASE/'cad_layout.json').read_text())
W,H,D,FD=layout['dims']; gap=layout['split_gap']
front=parts['Front_1']+parts['Front_2']
files={row['name']:row for row in json.loads((BASE/'print_files.json').read_text())}

for y in [3.5,H-3.5]:
    for z in [10,25]:
        line=m.Manifold.cube((.02,.02,13.6)).translate((W/2+8-.01,y-.01,z-6.8))
        opening=line-front
        assert len(opening.decompose())==1
        bounds=opening.bounding_box()
        # At X=seam+8 and local pocket depth=0.7, nominal height is 7.82.
        # The finite section adds 2*(0.01/6+0.01*0.18)=0.006933 mm.
        nominal=7.82+2*(.01/6+.01*.18)
        assert abs(bounds[5]-bounds[2]-(nominal+.4))<.003,(y,z,bounds)
        report.append(f'Tasche Y={y:.1f}, Z={z}: Druck-Z-Breitenzugabe 0.4 mm; Schnittgrenzen in Druck-Z {bounds[2]:.4f} / {bounds[5]:.4f} mm.')
report.append('Alle digitalen Frontpassungspruefungen bestanden.')
(BASE/'frontpassung_pruefung.txt').write_text('\n'.join(report)+'\n',encoding='utf-8')
print('\n'.join(report),flush=True)
