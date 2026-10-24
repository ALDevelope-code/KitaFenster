"""Build: python build.py PFAD_ZU_OPENSCAD_COM

Exports separate SketchUp objects, oriented STLs, and geometry checks.
Requires numpy and manifold3d for mesh normalization (0.001 mm tolerance).
Optional second argument: path containing these Python libraries.
Physical fit and wall capacity are not tested.
"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import hashlib
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
if len(sys.argv)>2:
    sys.path.insert(0,sys.argv[2])
import numpy as np
import manifold3d as manifold

BASE = Path(__file__).resolve().parent
SCAD = BASE / "gehaeuse.scad"
sys.path.insert(0, str(BASE))
from export_sketchup import element, NS
from pruefe_geometrie import mesh_check

VERTEX = re.compile(r"vertex\s+([-+\deE.]+)\s+([-+\deE.]+)\s+([-+\deE.]+)")


def read_mesh(path):
    raw = [tuple(map(float,m)) for m in VERTEX.findall(path.read_text(encoding='ascii'))]
    unique=list(dict.fromkeys(raw))
    lookup={p:i for i,p in enumerate(unique)}
    vertices=np.array(unique,dtype=np.float64)
    triangles=np.array([lookup[p] for p in raw],dtype=np.uint64).reshape((-1,3))
    solid=manifold.Manifold(manifold.Mesh64(vertices,triangles))
    assert solid.status()==manifold.Error.NoError,(path,solid.status())
    # OpenSCAD can emit collapsed sliver faces after ASCII coordinate rounding.
    # Retriangulate within one micron; then check the exported closed surface.
    clean=solid.simplify(0.001).to_mesh64()
    # Helix-Schnittkanten koennen nach ASCII-Rundung fast gleiche Punkte erzeugen.
    # Auf 0.00001 mm zusammenfassen und kollabierte Flaechen vor dem Export entfernen.
    snapped,lookup=np.unique(np.round(clean.vert_properties[:,:3],5),axis=0,return_inverse=True)
    faces=lookup[clean.tri_verts]
    faces=faces[(faces[:,0]!=faces[:,1]) & (faces[:,1]!=faces[:,2]) & (faces[:,0]!=faces[:,2])]
    normalized=manifold.Manifold(manifold.Mesh64(np.ascontiguousarray(snapped),np.ascontiguousarray(faces,dtype=np.uint64)))
    assert normalized.status()==manifold.Error.NoError,(path,normalized.status())
    clean=normalized.to_mesh64()
    return [tuple(clean.vert_properties[i][:3]) for tri in clean.tri_verts for i in tri]


def write_stl(path, points):
    lines = ['solid gehaeuse']
    for i in range(0,len(points),3):
        a,b,c = points[i:i+3]
        u = [b[j]-a[j] for j in range(3)]
        v = [c[j]-a[j] for j in range(3)]
        n = [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        length = math.sqrt(sum(x*x for x in n))
        assert length>0
        lines.append('  facet normal '+' '.join(f'{x/length:.9g}' for x in n))
        lines.append('    outer loop')
        lines += ['      vertex '+' '.join(f'{x:.9g}' for x in p) for p in (a,b,c)]
        lines += ['    endloop','  endfacet']
    lines.append('endsolid gehaeuse')
    path.write_text('\n'.join(lines)+'\n',encoding='ascii')


def write_dae(parts,target):
    ET.register_namespace('',NS)
    root=ET.Element(f'{{{NS}}}COLLADA',{'version':'1.4.1'})
    asset=element(root,'asset')
    element(element(asset,'contributor'),'authoring_tool','KitaFenster')
    timestamp=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    element(asset,'created',timestamp)
    element(asset,'modified',timestamp)
    element(asset,'title','Wandgehaeuse - vermessener Monitor, USB-C')
    element(asset,'unit',name='millimeter',meter='0.001')
    element(asset,'up_axis','Z_UP')
    effects=element(root,'library_effects')
    materials=element(root,'library_materials')
    geometries=element(root,'library_geometries')
    scene=element(element(root,'library_visual_scenes'),'visual_scene',id='Scene',name='Wandgehaeuse')
    for name,points,color in parts:
        # Front is at world Y=0, wall at Y=+depth; view from negative Y.
        # Reflection matches the SCAD output (wall at negative SCAD Z).
        points=[(x,z,y) for x,y,z in points]
        points=[points[i+j] for i in range(0,len(points),3) for j in (0,2,1)]
        unique=list(dict.fromkeys(points))
        lookup={v:i for i,v in enumerate(unique)}
        indices=[lookup[v] for v in points]
        effect=element(effects,'effect',id=f'{name}-effect')
        lambert=element(element(element(effect,'profile_COMMON'),'technique',sid='common'),'lambert')
        element(element(lambert,'diffuse'),'color',color)
        element(element(materials,'material',id=f'{name}-material',name=name),'instance_effect',url=f'#{name}-effect')
        mesh=element(element(geometries,'geometry',id=name,name=name),'mesh')
        source=element(mesh,'source',id=f'{name}-positions')
        element(source,'float_array',' '.join(f'{c:.9g}' for p in unique for c in p),id=f'{name}-array',count=len(unique)*3)
        accessor=element(element(source,'technique_common'),'accessor',source=f'#{name}-array',count=len(unique),stride=3)
        for axis in 'XYZ':
            element(accessor,'param',name=axis,type='float')
        element(element(mesh,'vertices',id=f'{name}-vertices'),'input',semantic='POSITION',source=f'#{name}-positions')
        triangles=element(mesh,'triangles',count=len(indices)//3,material='surface')
        element(triangles,'input',semantic='VERTEX',source=f'#{name}-vertices',offset=0)
        element(triangles,'p',' '.join(map(str,indices)))
        instance=element(element(scene,'node',id=f'{name}-node',name=name,type='NODE'),'instance_geometry',url=f'#{name}')
        element(element(element(instance,'bind_material'),'technique_common'),'instance_material',symbol='surface',target=f'#{name}-material')
    element(element(root,'scene'),'instance_visual_scene',url='#Scene')
    ET.indent(root,space='  ')
    ET.ElementTree(root).write(target,encoding='utf-8',xml_declaration=True)
    parsed=ET.parse(target)
    ids=[e.get('id') for e in parsed.iter() if e.get('id')]
    assert len(ids)==len(set(ids))
    for e in parsed.iter():
        for attr in ('source','target','url'):
            link=e.get(attr,'')
            assert not link.startswith('#') or link[1:] in ids
    assert len(parsed.findall(f'.//{{{NS}}}geometry'))==len(parts)

def as_solid(points):
    unique=list(dict.fromkeys(points)); lookup={p:i for i,p in enumerate(unique)}
    return manifold.Manifold(manifold.Mesh64(np.array(unique,dtype=np.float64),
        np.array([lookup[p] for p in points],dtype=np.uint64).reshape((-1,3))))

def solid_points(solid):
    assert solid.status()==manifold.Error.NoError
    mesh=solid.simplify(.001).to_mesh64()
    return [tuple(mesh.vert_properties[i][:3]) for tri in mesh.tri_verts for i in tri]

def main():
    executable=sys.argv[1]
    cache=Path(tempfile.gettempdir())/'kitafenster-gehaeuse-build-cache'/hashlib.sha256(SCAD.read_bytes()+(BASE/'metric_threads.scad').read_bytes()).hexdigest()[:16]
    cache.mkdir(parents=True,exist_ok=True)
    def export(name,part,**parameters):
        target=cache/(name+'.stl')
        if target.exists(): return
        args=[executable,'--hardwarnings','--export-format','asciistl','-o',str(target),'-D',f'part="{part}"','-D','raw_coordinates=true']
        for key,val in parameters.items(): args+=['-D',f'{key}={str(val).lower() if isinstance(val,bool) else val}']
        result=subprocess.run(args+[str(SCAD)],capture_output=True,text=True,timeout=600)
        if result.returncode or re.search('WARNING:|ERROR:',result.stderr): raise RuntimeError(result.stderr)
        print('CAD-Export: '+name,flush=True)
    layout=cache/'layout.echo'
    result=subprocess.run([executable,'--hardwarnings','-o',str(layout),'-D','part="layout"',str(SCAD)],capture_output=True,text=True,timeout=20)
    assert result.returncode==0 and 'ERROR:' not in result.stderr,result.stderr
    line=next(line for line in layout.read_text().splitlines() if '"LAYOUT"' in line)
    dims,front_keys,rear_keys,pir_center,cap_centers,gap,closure,wedge_params=json.loads('['+line.split('"LAYOUT",',1)[1]+']')
    width,height,depth,front_depth=dims
    (BASE/'cad_layout.json').write_text(json.dumps(dict(dims=dims,front_keys=front_keys,rear_keys=rear_keys,
        pir_center=pir_center,cap_centers=cap_centers,split_gap=gap,closure=closure,wedge_params=wedge_params),indent=2),encoding='utf-8')
    jobs=[(f'Basis_{part}_{mode}',part,{'seam_features':mode=='geteilt'}) for mode in ['geteilt','komplett'] for part in ['front','rear']]
    jobs += [('Klebekeil_Front','front_key',{}),('Klebekeil_Deckel','rear_key',{}),
        ('Andruckteller_M10','pressure_cap',{}),('Andruckteller_M4','pressure_m4',{})]
    refs=[('REFERENZ_Monitor','monitor_dummy','0.15 0.17 0.20 1'),('REFERENZ_Pi_Platine','pi_dummy','0.15 0.48 0.29 1'),
        ('REFERENZ_PIR','pir_dummy','0.88 0.86 0.75 1'),('REFERENZ_USB_C','usb_dummy','0.25 0.25 0.25 1')]
    jobs += [(name,part,{}) for name,part,_ in refs]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda j:export(j[0],j[1],**j[2]),jobs))
    raw={name:read_mesh(cache/(name+'.stl')) for name,_,_ in jobs}
    report=['digitale Geometriepruefung. Kein physischer Montage-/Belastungsversuch.',
        'Netze innerhalb 0.001 mm normalisiert; geteilte Schalen aus derselben Gesamtgeometrie geschnitten.']
    split=[]; whole=[]; manifest={}; files={}
    swap=np.array([[1,0,0],[0,0,1],[0,1,0]])
    def rx(angle):
        c=round(math.cos(math.radians(angle)),12); s=round(math.sin(math.radians(angle)),12)
        return np.array([[1,0,0],[0,c,-s],[0,s,c]])
    def output(name,points,category,folder='stl_geteilt',limit=252):
        matrix=np.diag([-1,1,1])
        if category in ('rear','small_rear','glue_key'):
            matrix=rx(180) @ matrix
        if category in ('front','rear'):
            matrix=np.array([[0,-1,0],[1,0,0],[0,0,1]]) @ matrix
        assert abs(np.linalg.det(matrix)+1)<1e-9
        array=np.array(points) @ matrix.T
        array=array.reshape((-1,3,3))[:,[0,2,1],:].reshape((-1,3))
        array-=array.min(axis=0)
        dest=BASE/folder; dest.mkdir(exist_ok=True)
        path=dest/(name+'.stl'); write_stl(path,array.tolist())
        check=mesh_check(path,xy_limit=limit)
        report.append(name+': '+check); print(name+': '+check,flush=True)
        files[name]={'name':name,'file':path.relative_to(BASE).as_posix(),'raw_to_print':matrix.tolist()}
        if category in ('front','rear') and folder=='stl_geteilt':
            size=array.max(axis=0); x,y=(256-size[0])/2,30.5
            assert x-2>0 and x+size[0]+2<256 and y-2>28 and y+size[1]+2<256
            report.append(f'  P1S, 2-mm-Brim: Modell-Minimum X={x:.3f}, Y={y:.3f}; Sperrflaeche frei.')
    def instance(name,source,points,color,targets,offset=(0,0,0),angle=0):
        rotation=rx(angle)
        placed=np.array(points) @ rotation.T+offset
        component=(name,[tuple(p) for p in placed],color)
        for target in targets: target.append(component)
        file=files[source]
        matrix=np.array(file['raw_to_print']) @ rotation.T @ swap.T
        assert abs(np.linalg.det(matrix)-1)<1e-9
        manifest[name]={'name':name,'source':source,'file':file['file'],
            'raw_placement':{'rotation':rotation.tolist(),'offset':list(offset)},
            'dae_to_stl_rotation':matrix.tolist()}
    for part,label,color in [('front','Front','0.78 0.80 0.83 1'),('rear','Rueckseite','0.52 0.58 0.64 1')]:
        base=as_solid(raw[f'Basis_{part}_geteilt'])
        for q in range(2):
            clip=manifold.Manifold.cube((width/2+1-gap/2,height+2,100)).translate((-1 if q==0 else width/2+gap/2,-1,-1))
            points=solid_points(base^clip); name=f'{label}_{q+1}'
            output(name,points,part); instance(name,name,points,color,[split])
        name=label+'_komplett'; points=raw[f'Basis_{part}_komplett']
        output(name,points,part,'stl_komplett',None); instance(name,name,points,color,[whole])
    for name,positions in [('Klebekeil_Front',front_keys),('Klebekeil_Deckel',rear_keys)]:
        points=raw[name]; output(name,points,'glue_key')
        for i,(offset,angle) in enumerate(positions):
            instance(name+f'_{i+1}',name,points,'0.22 0.43 0.63 1',[split],offset,angle)
    points=raw['Andruckteller_M10']; output('Andruckteller_M10',points,'pressure_cap')
    for i,c in enumerate(cap_centers):
        instance(f'Andruckteller_{i+1}','Andruckteller_M10',points,'0.22 0.43 0.63 1',[split,whole],c)
    points=raw['Andruckteller_M4']; output('Andruckteller_M4',points,'pressure_cap','nachruestung_M4')
    write_dae([('Andruckteller_M4',points,'0.22 0.43 0.63 1')],BASE/'andruckteller_M4.dae')
    for name,_,color in refs:
        split.append((name,raw[name],color)); whole.append((name,raw[name],color))
    write_dae(split,BASE/'gehaeuse_geteilt.dae'); write_dae(whole,BASE/'gehaeuse_komplett.dae')
    for label,parts in [('geteilt',split),('komplett',whole)]:
        points=np.array([p for n,pts,_ in parts if not n.startswith('REFERENZ_') for p in pts])
        extent=points.max(axis=0)-points.min(axis=0)
        assert np.allclose(extent,[width,height,depth],atol=.01)
        report.append(f'DAE {label}: {len(parts)} Objekte, mm-Einheit; B/H/T {extent.tolist()}.')
    (BASE/'pruefung.txt').write_text('\n'.join(report)+'\n',encoding='utf-8')
    (BASE/'export_manifest.json').write_text(json.dumps(list(manifest.values()),indent=2),encoding='utf-8')
    (BASE/'print_files.json').write_text(json.dumps(list(files.values()),indent=2),encoding='utf-8')
    print('Beide Modelle und STL-Dateien erstellt.',flush=True)

if __name__=='__main__': main()
