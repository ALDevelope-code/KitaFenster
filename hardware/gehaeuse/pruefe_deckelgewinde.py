"""Prueft Durchmesser und Steigung der acht exportierten M10-Aufnahmen.
Optional argv[1]: Python library directory.
"""
from pathlib import Path
import json
import re
import sys
import xml.etree.ElementTree as ET
if len(sys.argv)>1: sys.path.insert(0,sys.argv[1])
import numpy as np
import manifold3d as m
from build import read_mesh,as_solid

BASE=Path(__file__).resolve().parent
source=(BASE/'gehaeuse.scad').read_text(encoding='utf-8')
def val(name): return float(re.search(rf'^{name}\s*=\s*([\d.]+);',source,re.M).group(1))
assert val('pressure_female_radial')==.2
assert val('front_pocket_z_extra')==.4
ns={'c':'http://www.collada.org/2005/11/COLLADASchema'}
def scene(folder,mode):
    parts={}
    for g in ET.parse(folder/f'gehaeuse_{mode}.dae').findall('.//c:geometry',ns):
        xyz=np.array(list(map(float,g.find('.//c:float_array',ns).text.split()))).reshape((-1,3))
        ix=np.array(list(map(int,g.find('.//c:triangles/c:p',ns).text.split())),dtype=np.uint64).reshape((-1,3))
        parts[g.get('name')]=m.Manifold(m.Mesh64(np.ascontiguousarray(xyz[:,[0,2,1]]),np.ascontiguousarray(ix[:,[0,2,1]])))
    return parts

def boundary_error(a,b):
    """Largest vertex-to-edge deviation, in mm, in both directions."""
    def directed(points,poly):
        start=np.array(poly); edges=np.roll(start,-1,axis=0)-start
        rel=np.array(points)[:,None,:]-start[None,:,:]
        t=np.clip(np.sum(rel*edges,axis=2)/np.sum(edges*edges,axis=1),0,1)
        return np.linalg.norm(rel-t[:,:,None]*edges,axis=2).min(axis=1).max()
    return max(directed(a,b),directed(b,a))

layout=json.loads((BASE/'cad_layout.json').read_text())
report=['M10-Innengewinde: 0.20 mm radiale Zugabe, grosser Durchmesser 10.40 mm, Steigung 1.5 mm.']
for mode in ['geteilt','komplett']:
    parts=scene(BASE,mode)
    rear=m.Manifold.batch_boolean([s for n,s in parts.items() if n.startswith('Rueckseite_')],m.OpType.Add)
    for i,(x,y,cap_z) in enumerate(layout['cap_centers']):
        entry=cap_z+val('pressure_post_gap')-val('rear_pad_gap')+val('pad_recess')
        sample=m.Manifold.cylinder(11,5.6,circular_segments=96).translate((x,y,entry+.5))
        hole=sample-rear
        errors=[]
        radii=[]
        for z in np.linspace(entry+1.05,entry+8.95,33):
            section=hole.slice(z).to_polygons()
            next_turn=hole.slice(z+1.5).to_polygons()
            assert len(section)==len(next_turn)==1,(mode,i+1,z)
            errors.append(boundary_error(section[0],next_turn[0]))
            radii.append(np.linalg.norm(np.array(section[0])-[x,y],axis=1).max())
        assert max(errors)<.003,(mode,i+1,'Falsche Steigung',max(errors))
        assert max(abs(2*r-10.4) for r in radii)<.003,(mode,i+1,'Falscher Durchmesser',radii)
        report.append(f'{mode}, Halter {i+1}: 33 Gewindeschnitte; Durchmesser 10.400 mm; Steigung 1.5 mm; maximale Konturabweichung nach einer Windung {max(errors):.6f} mm.')
report.append('Alle digitalen Deckelgewinde-Pruefungen bestanden.')
(BASE/'deckelgewinde_pruefung.txt').write_text('\n'.join(report)+'\n',encoding='utf-8')
print('\n'.join(report),flush=True)
