"""Gewindesteigung/-richtung aus den fertigen Druck-STLs messen; digitale Geometriepruefung.
Usage: python pruefe_gewinde.py [PYTHON_BIBLIOTHEKSORDNER]
"""
from pathlib import Path
import math
import sys
import xml.etree.ElementTree as ET
if len(sys.argv)>1: sys.path.insert(0,sys.argv[1])
import numpy as np
import manifold3d as m
from build import read_mesh,as_solid

BASE=Path(__file__).resolve().parent
report=['Zusatzpruefung an den exportierten Gewinden.']

def phase(solid,z,inside=False):
    bb=solid.bounding_box()
    center=np.array([(bb[0]+bb[3])/2,(bb[1]+bb[4])/2])
    polygons=solid.slice(z).to_polygons()
    # Bei einem Innengewinde ist das kleinere Polygon die Kontur des Innengewindes.
    polygon=min(polygons,key=lambda p:np.mean(np.linalg.norm(np.array(p)-center,axis=1))) if inside else polygons[0]
    xy=np.array(polygon)-center
    radius=np.linalg.norm(xy,axis=1)
    selected=xy[radius>=radius.max()-.02]
    angles=np.arctan2(selected[:,1],selected[:,0])
    direction=math.degrees(math.atan2(np.sin(angles).mean(),np.cos(angles).mean()))
    return direction,float(radius.max())

for name,pitch,inside in [('stl_geteilt/Andruckteller_M10.stl',1.5,False),
                         ('nachruestung_M4/Andruckteller_M4.stl',.7,False)]:
    solid=as_solid(read_mesh(BASE/name))
    a,r=phase(solid,5.1,inside)
    b,_=phase(solid,5.1+pitch/4,inside)
    c,_=phase(solid,5.1+pitch,inside)
    quarter=(b-a+180)%360-180
    full=(c-a+180)%360-180
    assert abs(quarter-90)<8,(name,'kein Rechtsgewinde',quarter)
    assert abs(full)<8,(name,'falsche Steigung',full)
    report.append(f'{name}: Rechtsgewinde; nach P/4 +{quarter:.2f} Grad, nach P Rest {full:.2f} Grad; P={pitch} mm, gemessener Aussendurchmesser {2*r:.3f} mm.')

ns={'c':'http://www.collada.org/2005/11/COLLADASchema'}
solids={}
for g in ET.parse(BASE/'gehaeuse_geteilt.dae').findall('.//c:geometry',ns):
    xyz=np.array(list(map(float,g.find('.//c:float_array',ns).text.split()))).reshape((-1,3))
    ix=np.array(list(map(int,g.find('.//c:triangles/c:p',ns).text.split())),dtype=np.uint64).reshape((-1,3))
    solids[g.get('name')]=m.Manifold(m.Mesh64(np.ascontiguousarray(xyz[:,[0,2,1]]),np.ascontiguousarray(ix[:,[0,2,1]])))
rear=solids['Rueckseite_1']; cap=solids['Andruckteller_1']
assert abs((rear^cap).volume())<.02
blocked=abs((rear^cap.translate((0,0,.75))).volume())
assert blocked>1,('Gewinde hat keinen axialen Formschluss',blocked)
report.append(f'M10: ohne Drehung ist 0.75 mm Vorschub blockiert ({blocked:.3f} mm3 Ueberschneidung); im Schraubweg hingegen kollisionsfrei laut Montagepruefung.')

report.append('Alle digitalen Gewindepruefungen bestanden.')
(BASE/'gewindepruefung.txt').write_text('\n'.join(report)+'\n',encoding='utf-8')
print('\n'.join(report))
