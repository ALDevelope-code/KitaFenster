"""Create native SKP files with the locally installed SketchUp C API.

Usage: python export_native_skp.py [PATH_TO_NUMPY] [PATH_TO_SketchUpAPI.dll]
Does not open or modify an interactive SketchUp document.
All C API calls are made on the main thread; all lengths in the API are inches.
"""
import ctypes as C
from collections import defaultdict
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
if len(sys.argv)>1:
    sys.path.insert(0,sys.argv[1])
import numpy as np

BASE=Path(__file__).resolve().parent
DLL=Path(sys.argv[2]) if len(sys.argv)>2 else Path('C:/Program Files/SketchUp/SketchUp 2026/SketchUp/SketchUpAPI.dll')
search_path=os.add_dll_directory(str(DLL.parent))
api=C.CDLL(str(DLL))
class Ref(C.Structure):
    _fields_=[('ptr',C.c_void_p)]
class Point(C.Structure):
    _fields_=[('x',C.c_double),('y',C.c_double),('z',C.c_double)]
class Bounds(C.Structure):
    _fields_=[('minimum',Point),('maximum',Point)]
class Transform(C.Structure):
    _fields_=[('values',C.c_double*16)]
class Color(C.Structure):
    _fields_=[('r',C.c_uint8),('g',C.c_uint8),('b',C.c_uint8),('a',C.c_uint8)]
P=C.POINTER
R=Ref
size=C.c_size_t
def bind(name,args,restype=C.c_int):
    fn=getattr(api,name); fn.argtypes=args; fn.restype=restype
    return fn
signatures={
 'SUModelCreate':[P(R)],'SUModelRelease':[P(R)],'SUModelGetEntities':[R,P(R)],
 'SUModelSetName':[R,C.c_char_p],'SUModelSaveToFile':[R,C.c_char_p],
 'SUModelCreateFromFile':[P(R),C.c_char_p],
 'SUGroupCreate':[P(R)],'SUEntitiesAddGroup':[R,R],
 'SUGroupGetEntities':[R,P(R)],'SUGroupSetName':[R,C.c_char_p],
 'SUGroupGetName':[R,P(R)],'SUGroupSetTransform':[R,P(Transform)],
 'SUGeometryInputCreate':[P(R)],'SUGeometryInputRelease':[P(R)],
 'SUGeometryInputSetVertices':[R,size,P(Point)],
 'SULoopInputCreate':[P(R)],'SULoopInputAddVertexIndex':[R,size],
 'SULoopInputEdgeSetHidden':[R,size,C.c_bool],
 'SULoopInputEdgeSetSoft':[R,size,C.c_bool],
 'SULoopInputEdgeSetSmooth':[R,size,C.c_bool],
 'SUGeometryInputAddFace':[R,P(R),P(size)],'SUEntitiesFill':[R,R,C.c_bool],
 'SUComponentInstanceComputeVolume':[R,P(Transform),P(C.c_double)],
 'SUEntitiesGetBoundingBox':[R,P(Bounds)],'SUEntitiesGetNumGroups':[R,P(size)],
 'SUEntitiesGetGroups':[R,size,P(R),P(size)],'SUEntitiesGetNumFaces':[R,P(size)],
 'SUMaterialCreate':[P(R)],'SUMaterialSetName':[R,C.c_char_p],
 'SUMaterialSetColor':[R,P(Color)],'SUModelAddMaterials':[R,size,P(R)],
 'SUDrawingElementSetMaterial':[R,R],
 'SUModelGetOptionsManager':[R,P(R)],
 'SUOptionsManagerGetOptionsProviderByName':[R,C.c_char_p,P(R)],
 'SUTypedValueCreate':[P(R)],'SUTypedValueRelease':[P(R)],
 'SUTypedValueSetInt32':[R,C.c_int32],'SUTypedValueSetBool':[R,C.c_bool],
 'SUOptionsProviderSetValue':[R,C.c_char_p,R],
 'SUCameraCreate':[P(R)],'SUCameraSetOrientation':[R,P(Point),P(Point),P(Point)],
 'SUCameraSetOrthographicFrustumHeight':[R,C.c_double],
 'SUCameraSetAspectRatio':[R,C.c_double],'SUModelSetCamera':[R,P(R)],
 'SUStringCreate':[P(R)],'SUStringRelease':[P(R)],
 'SUStringGetUTF8Length':[R,P(size)],'SUStringGetUTF8':[R,size,C.c_char_p,P(size)],
 'SUGroupGetTransform':[R,P(Transform)],
}
for name,args in signatures.items(): bind(name,args)
for name in ['SUGroupToComponentInstance','SUGroupToDrawingElement']:
    bind(name,[R],R)
bind('SUInitialize',[],None); bind('SUTerminate',[],None)
def call(name,*args):
    result=getattr(api,name)(*args)
    if result!=0: raise RuntimeError(f'{name}: SUResult {result}')
def create(kind):
    ref=R(); call(kind,C.byref(ref)); return ref
def get_name(group):
    s=create('SUStringCreate')
    call('SUGroupGetName',group,C.byref(s))
    length=size(); call('SUStringGetUTF8Length',s,C.byref(length))
    buffer=C.create_string_buffer(length.value+1); written=size()
    call('SUStringGetUTF8',s,len(buffer),buffer,C.byref(written))
    result=buffer.value.decode('utf-8'); call('SUStringRelease',C.byref(s))
    return result
def geometry(path):
    ns={'c':'http://www.collada.org/2005/11/COLLADASchema'}
    root=ET.parse(path)
    result={}
    for g in root.findall('.//c:geometry',ns):
        name=g.get('name')
        xyz=np.array(list(map(float,g.find('.//c:float_array',ns).text.split()))).reshape((-1,3))
        ix=np.array(list(map(int,g.find('.//c:triangles/c:p',ns).text.split()))).reshape((-1,3))
        color=list(map(float,root.find(f'.//c:effect[@id="{name}-effect"]//c:diffuse/c:color',ns).text.split()))
        result[name]=(xyz,ix,color)
    return result
def volume(xyz,ix):
    # Translate near the origin to reduce cancellation.
    p=xyz[ix]-xyz.mean(axis=0)
    return float(np.einsum('ij,ij->i',p[:,0],np.cross(p[:,1],p[:,2])).sum()/6)
def units(model):
    manager=R(); provider=R()
    call('SUModelGetOptionsManager',model,C.byref(manager))
    call('SUOptionsManagerGetOptionsProviderByName',manager,b'UnitsOptions',C.byref(provider))
    typed=create('SUTypedValueCreate')
    for key,val in [('LengthFormat',0),('LengthUnit',2),('LengthPrecision',2)]:
        call('SUTypedValueSetInt32',typed,val)
        call('SUOptionsProviderSetValue',provider,key.encode(),typed)
    call('SUTypedValueSetBool',typed,False)
    call('SUOptionsProviderSetValue',provider,b'LengthSnapEnabled',typed)
    call('SUTypedValueRelease',C.byref(typed))
def add_group(model,entities,name,xyz,ix,rgba,scale):
    group=create('SUGroupCreate')
    call('SUGroupSetName',group,name.encode('utf-8'))
    call('SUEntitiesAddGroup',entities,group)
    contents=R(); call('SUGroupGetEntities',group,C.byref(contents))
    geom=create('SUGeometryInputCreate')
    vertices=(Point*len(xyz))(*(Point(*(p*scale/25.4)) for p in xyz))
    call('SUGeometryInputSetVertices',geom,len(vertices),vertices)
    normals=np.cross(xyz[ix[:,1]]-xyz[ix[:,0]],xyz[ix[:,2]]-xyz[ix[:,0]])
    normals/=np.linalg.norm(normals,axis=1)[:,None]
    edges=defaultdict(list)
    for i,tri in enumerate(ix):
        for j in range(3): edges[tuple(sorted((int(tri[j]),int(tri[(j+1)%3]))))].append((i,j))
    hidden=set(); soft=set()
    for adj in edges.values():
        if len(adj)!=2: continue
        dot=float(normals[adj[0][0]] @ normals[adj[1][0]])
        if dot>1-1e-9: hidden.update(adj)
        if dot>0.98: soft.update(adj)
    for i,tri in enumerate(ix):
        loop=create('SULoopInputCreate')
        for vertex in (*tri,tri[0]): call('SULoopInputAddVertexIndex',loop,int(vertex))
        for j in range(3):
            if (i,j) in hidden: call('SULoopInputEdgeSetHidden',loop,j,True)
            if (i,j) in soft:
                call('SULoopInputEdgeSetSoft',loop,j,True)
                call('SULoopInputEdgeSetSmooth',loop,j,True)
        call('SUGeometryInputAddFace',geom,C.byref(loop),None)
    call('SUEntitiesFill',contents,geom,False)
    call('SUGeometryInputRelease',C.byref(geom))
    transform=Transform((C.c_double*16)(1/scale,0,0,0,0,1/scale,0,0,0,0,1/scale,0,0,0,0,1))
    call('SUGroupSetTransform',group,C.byref(transform))
    material=create('SUMaterialCreate')
    call('SUMaterialSetName',material,('Farbe_'+name).encode())
    color=Color(*(round(v*255) for v in rgba))
    call('SUMaterialSetColor',material,C.byref(color))
    call('SUModelAddMaterials',model,1,C.byref(material))
    call('SUDrawingElementSetMaterial',api.SUGroupToDrawingElement(group),material)
    return group
def verify(model,expected,report,prefix):
    entities=R(); call('SUModelGetEntities',model,C.byref(entities))
    count=size(); call('SUEntitiesGetNumGroups',entities,C.byref(count))
    assert count.value==len(expected),(count.value,len(expected))
    groups=(R*count.value)(); got=size()
    call('SUEntitiesGetGroups',entities,count.value,groups,C.byref(got))
    names=[]
    for group in groups:
        name=get_name(group); names.append(name)
        xyz,ix,_=expected[name]
        computed=C.c_double()
        result=api.SUComponentInstanceComputeVolume(api.SUGroupToComponentInstance(group),None,C.byref(computed))
        if result: raise RuntimeError(f'{name}: SUComponentInstanceComputeVolume: SUResult {result}')
        actual=computed.value*25.4**3; target=volume(xyz,ix)
        assert actual>0 and abs(actual-target)<max(.03,target*1e-7),(name,'volume',actual,target)
        content=R(); call('SUGroupGetEntities',group,C.byref(content))
        bb=Bounds(); call('SUEntitiesGetBoundingBox',content,C.byref(bb))
        t=Transform(); call('SUGroupGetTransform',group,C.byref(t))
        mat=np.array(t.values).reshape((4,4),order='F')
        lower=np.array([bb.minimum.x,bb.minimum.y,bb.minimum.z,1.])
        upper=np.array([bb.maximum.x,bb.maximum.y,bb.maximum.z,1.])
        low=(mat @ lower)[:3]*25.4; high=(mat @ upper)[:3]*25.4
        assert np.allclose(low,xyz.min(axis=0),atol=.002),(name,low,xyz.min(axis=0))
        assert np.allclose(high,xyz.max(axis=0),atol=.002),(name,high,xyz.max(axis=0))
        faces=size(); call('SUEntitiesGetNumFaces',content,C.byref(faces))
        report.append(f'{prefix} {name}: Volumen {actual:.3f} mm3; geschlossen; Masse und Lage stimmen; {faces.value} Flaechen.')
    assert set(names)==set(expected)
def export(mode,scale=10000):
    parts=geometry(BASE/(f'gehaeuse_{mode}.dae' if mode!='M4' else 'andruckteller_M4.dae'))
    report=[f'Native SketchUp-C-API-Pruefung: {mode}. Laengeneinheit mm. Geometriefaktor {scale}.']
    model=create('SUModelCreate')
    try:
        points=np.concatenate([xyz for n,(xyz,_,_) in parts.items() if not n.startswith('REFERENZ_')])
        low,high=points.min(axis=0),points.max(axis=0)
        w,d,h=high-low
        call('SUModelSetName',model,f'KitaFenster {mode} - {w:.1f} x {h:.1f} x {d:.1f} mm'.encode())
        entities=R(); call('SUModelGetEntities',model,C.byref(entities))
        for name,(xyz,ix,color) in parts.items():
            print(f'SKP {mode}: {name}',flush=True)
            add_group(model,entities,name,xyz,ix,color,scale)
        units(model)
        camera=create('SUCameraCreate')
        eye=Point(*(((low+high)/2+np.array([-w*.8,-max(w,d,h)*1.8,h*.7]))/25.4))
        target=Point(*((low+high)/2/25.4)); up=Point(0,0,1)
        call('SUCameraSetOrientation',camera,C.byref(eye),C.byref(target),C.byref(up))
        call('SUCameraSetAspectRatio',camera,1.6)
        call('SUCameraSetOrthographicFrustumHeight',camera,max(w/1.6,h,d)*1.45/25.4)
        call('SUModelSetCamera',model,C.byref(camera))
        verify(model,parts,report,'Vor Speichern:')
        target_file=BASE/(f'gehaeuse_{mode}.skp' if mode!='M4' else 'andruckteller_M4.skp')
        call('SUModelSaveToFile',model,str(target_file).encode('utf-8'))
    finally:
        call('SUModelRelease',C.byref(model))
    reloaded=R()
    call('SUModelCreateFromFile',C.byref(reloaded),str(target_file).encode('utf-8'))
    try: verify(reloaded,parts,report,'Nach erneutem Laden:')
    finally: call('SUModelRelease',C.byref(reloaded))
    (BASE/f'sketchup_pruefung_{mode}.txt').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print(f'Native Datei gespeichert und erneut erfolgreich geprueft: {target_file.name}',flush=True)

if __name__=='__main__':
    api.SUInitialize()
    try:
        for mode in ['geteilt','komplett','M4']: export(mode)
    finally:
        api.SUTerminate()
        search_path.close()
