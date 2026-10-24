"""Render the actual exported meshes, avoiding OpenCSG preview artifacts.
Usage: python render_ansichten.py OPENSCAD_COM [PYTHON_LIB_DIRECTORY] [ONLY_VIEW]
"""
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
if len(sys.argv)>2: sys.path.insert(0,sys.argv[2])
import numpy as np
import manifold3d as m
from build import write_stl,read_mesh

BASE=Path(__file__).resolve().parent
source=(BASE/'gehaeuse.scad').read_text(encoding='utf-8')
def value(name): return float(re.search(rf'^{name}\s*=\s*([\d.]+);',source,re.M).group(1))
layout=json.loads((BASE/'cad_layout.json').read_text())
W,H,D,FD=layout['dims']
mx=value('left_margin')+value('clearance')
my=value('bottom_margin')+value('clearance')
mz=value('front_t')+value('front_pad')
px,py,pz=layout['pir_center']
WORK=Path(tempfile.gettempdir())/'kitafenster-gehaeuse-ansichten'
WORK.mkdir(exist_ok=True)
ns={'c':'http://www.collada.org/2005/11/COLLADASchema'}
doc=ET.parse(BASE/'gehaeuse_geteilt.dae')
parts={}
for g in doc.findall('.//c:geometry',ns):
    xyz=np.array(list(map(float,g.find('.//c:float_array',ns).text.split()))).reshape((-1,3))
    ix=np.array(list(map(int,g.find('.//c:triangles/c:p',ns).text.split())),dtype=np.uint64).reshape((-1,3))
    # DAE to right-handed SCAD view axes, front at Z=0, wall at Z=-D.
    points=np.column_stack((xyz[:,0],xyz[:,2],-xyz[:,1]))
    name=g.get('name')
    color=list(map(float,doc.find(f'.//c:effect[@id="{name}-effect"]//c:diffuse/c:color',ns).text.split()))
    solid=m.Manifold(m.Mesh64(np.ascontiguousarray(points),ix))
    parts[name]=(solid,color)
def save_mesh(name,solid,color):
    mesh=solid.to_mesh64()
    path=WORK/(name+'.stl')
    write_stl(path,[tuple(mesh.vert_properties[i][:3]) for tri in mesh.tri_verts for i in tri])
    return 'color(['+','.join(map(str,color))+']) import("'+path.as_posix()+'");'
def render(view,items,camera,size=(1200,760)):
    if len(sys.argv)>3 and view!=sys.argv[3]: return
    script=WORK/(view+'.scad')
    script.write_text('\n'.join(save_mesh(view+'_'+str(i),s,col) for i,(s,col) in enumerate(items)))
    args=[sys.argv[1],'--hardwarnings','-o',str(BASE/(view+'.png')),'--imgsize',','.join(map(str,size)),
        '--camera',camera,'--autocenter','--viewall','--projection','ortho','--colorscheme','Tomorrow',str(script)]
    result=subprocess.run(args,capture_output=True,text=True,timeout=60)
    assert result.returncode==0 and 'ERROR:' not in result.stderr,result.stderr
    print(view+'.png',flush=True)
views={
 'rueckseite_aussen':([n for n in parts if n.startswith('Rueckseite_')],'0,0,0,0,180,0,700'),
 'vorn':([n for n in parts if n.startswith('Front_') or n in ['REFERENZ_Monitor','REFERENZ_PIR','REFERENZ_USB_C']],'0,0,0,20,-20,5,700'),
 'front_innen':([n for n in parts if n.startswith(('Front_','Klebekeil_Front')) or n=='REFERENZ_USB_C'],'0,0,0,15,165,0,700'),
 'rueckseite_innen':([n for n in parts if n.startswith(('Rueckseite','Klebekeil_Deckel','Andruck')) or n in ['REFERENZ_Pi_Platine','REFERENZ_PIR']],'0,0,0,22,-15,0,700'),
}
for view,(names,camera) in views.items(): render(view,[parts[n] for n in names],camera)
# Neuer unterer Auflager mit Freistellung des benachbarten Schraubdoms.
bottom_crop=m.Manifold.cube((40,15,17)).translate((mx+value('monitor_w')-60,0,-16))
bottom_detail=(parts['Front_2'][0]^bottom_crop).rotate((180,0,0))
render('untere_auflage',[(bottom_detail,[.60,.66,.72,1])],
       '0,0,0,45,20,15,70',(1000,760))
# Echter Ausschnitt eines oberen Haltestegs. Gehaeuseansatz hinten,
# freie Kante vorne; die Drehung stellt den Steg wie in der Nutzerskizze dar.
locator_crop=m.Manifold.cube((32,14,28)).translate((76.6,226.2,-27))
locator=(parts['Front_1'][0]^locator_crop).translate((-80.6,-230.2,3)).rotate((90,0,0))
render('monitorhaltesteg',[(locator,[.60,.66,.72,1])],
       '-27,57,28,12,9,2',(1000,760))
cx,cy,cz=layout['cap_centers'][0]
clip=m.Manifold.cube((32,26,D+2)).translate((cx-16,cy-13,-D-1))
rear=parts['Rueckseite_1'][0]^clip
cap=parts['Andruckteller_1']
pad=m.Manifold.cube((12,8,.8)).translate((cx-6,cy-4,-cz-value('pad_recess')))
render('andruck',[(rear,[.60,.66,.72,1]),cap,(pad,[.1,.1,.1,1])],
       '0,0,0,65,-20,15,65',(900,660))

# Echter Ausschnitt des Deckels mit den beiden erhoehten PIR-Schraubstuetzen.
pir_crop=m.Manifold.cube((44,36,D+2)).translate((px-22,py-18,-D-1))
pir_mount=(parts['Rueckseite_1'][0]^pir_crop).translate((-px,-py,D))
render('pir_aufnahme',[(pir_mount,[.60,.66,.72,1])],
       '70,60,55,0,0,18',(1000,760))
# Explosionsansicht: nur Platine/Linse der Referenz; Bauteilreserve weggelassen,
# damit die Auflagen und die beiden Montageloecher sichtbar bleiben.
pcb_crop=m.Manifold.cube((40,32,1.6)).translate((px-20,py-16,-pz-1.6))
pcb=(parts['REFERENZ_PIR'][0]^pcb_crop).translate((-px,-py,D+8))
render('pir_befestigung',[(pir_mount,[.60,.66,.72,1]),(pcb,[.15,.48,.29,1])],
       '70,60,55,0,0,23',(1000,760))
usb_clip=m.Manifold.cube((40,36,D+2)).translate((-3,0,-D-1))
render('usb_c',[(parts['Front_1'][0]^usb_clip,parts['Front_1'][1]),parts['REFERENZ_USB_C']],
       '0,0,0,10,-70,0,70',(900,660))
# Aus den exportierten Netzen: tatsaechliche Rueckenstufe und neuer Tastenzugang.
lower_zone=m.Manifold.cube((W,my+value('monitor_step_y'),D)).translate((0,0,-D))
monitor=parts['REFERENZ_Monitor'][0]
render('monitor_rueckseite',[(monitor^lower_zone,[.35,.53,.68,1]),(monitor-lower_zone,[.72,.75,.78,1])],
       '0,0,0,35,150,5,550',(1200,760))
button_clip=m.Manifold.cube((28,122,D+2)).translate((W-27,my-2,-D-1))
render('tastenfenster',[(parts['Front_2'][0]^button_clip,parts['Front_2'][1]),
       (parts['REFERENZ_Monitor'][0]^button_clip,parts['REFERENZ_Monitor'][1])],
       '0,0,0,20,72,5,160',(900,760))
cache=Path(tempfile.gettempdir())/'kitafenster-gehaeuse-build-cache'/hashlib.sha256((BASE/'gehaeuse.scad').read_bytes()+(BASE/'metric_threads.scad').read_bytes()).hexdigest()[:16]
def raw_solid(name):
    points=read_mesh(cache/(name+'.stl')); unique=list(dict.fromkeys(points)); lookup={p:i for i,p in enumerate(unique)}
    ix=np.array([lookup[p] for p in points],dtype=np.uint64).reshape((-1,3))
    xyz=np.array(unique,dtype=np.float64); xyz[:,2]*=-1
    return m.Manifold(m.Mesh64(xyz,np.ascontiguousarray(ix[:,[0,2,1]])))
render('teller_M10',[(raw_solid('Andruckteller_M10').rotate((180,0,0)),[.22,.43,.63,1])],
       '0,0,0,60,0,25,50',(900,760))
render('teller_M4',[(raw_solid('Andruckteller_M4').rotate((180,0,0)),[.22,.43,.63,1])],
       '0,0,0,65,0,25,50',(900,760))
# Laengsschnitt des echten Innengewindes mit etwas herausgedrehtem Teller.
half_crop=m.Manifold.cube((24,10,D+2)).translate((cx-12,cy,-D-1))
render('M10_schnitt',[(rear^half_crop,[.60,.66,.72,1]),
       (cap[0].translate((0,0,3)),cap[1])],
       '0,0,0,80,0,0,65',(1000,760))
crop=m.Manifold.cube((50,12,D)).translate((W/2-25,0,-D))
render('frontnaht_innen',[(parts[n][0]^crop,parts[n][1]) for n in ['Front_1','Front_2']]+
       [parts['Klebekeil_Front_1'],parts['Klebekeil_Front_2']],
       f'{W/2+32},90,-8,{W/2},3,{-D/2}',(1000,760))
crop=m.Manifold.cube((12,12,11)).translate((110,H-12,-D-1))
render('deckelrand',[(parts['Front_1'][0]^crop,[.8,.82,.85,1]),
    (parts['Rueckseite_1'][0]^crop,[.22,.43,.63,1])],
    f'150,{H-22},{-D+22},116,{H-6},{-FD+2}',(1000,760))
