"""Independent assembly and STL/DAE checks. Optional argv[1]: library directory."""
from pathlib import Path
import itertools
import json
import re
import sys
import xml.etree.ElementTree as ET
if len(sys.argv)>1:
    sys.path.insert(0,sys.argv[1])
import numpy as np
import manifold3d as m

BASE=Path(__file__).resolve().parent
source=(BASE/'gehaeuse.scad').read_text(encoding='utf-8')
def value(name):
    return float(re.search(rf'^{name}\s*=\s*([\d.]+);',source,re.M).group(1))
W=value('monitor_w')+2*value('clearance')+value('left_margin')+value('right_margin')
H=value('monitor_h')+2*value('clearance')+value('bottom_margin')+value('top_margin')
D=value('total_depth')
mx=value('left_margin')+value('clearance')
my=value('bottom_margin')+value('clearance')
mz=value('front_t')+value('front_pad')
def thickness(y):
    return value('monitor_d_lower') if y<my+value('monitor_step_y') else value('monitor_d_upper')
def back(y):
    return mz+thickness(y)
manifest={row['name']:row for row in json.loads((BASE/'export_manifest.json').read_text())}
ns={'c':'http://www.collada.org/2005/11/COLLADASchema'}
vertex_pattern=re.compile(r'vertex\s+([-+\deE.]+)\s+([-+\deE.]+)\s+([-+\deE.]+)')
report=['unabhaengige Pruefung der exportierten Bauteile mit manifold3d.',
        'Keine physische Passungs-, Werkstoff-, Temperatur- oder Wandlastpruefung.']
failed=[]
def make(xyz,indices):
    solid=m.Manifold(m.Mesh64(np.ascontiguousarray(xyz,dtype=np.float64),np.ascontiguousarray(indices,dtype=np.uint64)))
    assert solid.status()==m.Error.NoError and solid.volume()>0,solid.status()
    return solid
def stl(path):
    points=[tuple(map(float,p)) for p in vertex_pattern.findall(path.read_text())]
    unique=list(dict.fromkeys(points)); lookup={p:i for i,p in enumerate(unique)}
    return make(unique,np.array([lookup[p] for p in points]).reshape((-1,3)))
def cube(dims,origin):
    return m.Manifold.cube(dims).translate(origin)
def check(label,a,b):
    overlap=a^b
    assert overlap.status()==m.Error.NoError,(label,overlap.status())
    vol=abs(overlap.volume())
    if vol>.02:
        failed.append(f'{label}: {vol:.6f} mm3')
    return vol

for mode in ['geteilt','komplett']:
    solids={}; originals={}
    for g in ET.parse(BASE/f'gehaeuse_{mode}.dae').findall('.//c:geometry',ns):
        xyz=np.array(list(map(float,g.find('.//c:float_array',ns).text.split()))).reshape((-1,3))
        ix=np.array(list(map(int,g.find('.//c:triangles/c:p',ns).text.split()))).reshape((-1,3))
        originals[g.get('name')]=make(xyz,ix)
        solids[g.get('name')]=make(xyz[:,[0,2,1]],ix[:,[0,2,1]])
    printed={n:s for n,s in solids.items() if not n.startswith('REFERENZ_')}
    refs={n:s for n,s in solids.items() if n.startswith('REFERENZ_')}
    for name in printed:
        entry=manifest[name]
        rotation=np.column_stack((np.array(entry['dae_to_stl_rotation']),np.zeros(3)))
        assert abs(np.linalg.det(rotation[:,:3])-1)<1e-9
        aligned=originals[name].transform(rotation)
        aligned=aligned.translate(tuple(-v for v in aligned.bounding_box()[:3]))
        other=stl(BASE/entry['file'])
        difference=abs((aligned-other).volume())+abs((other-aligned).volume())
        assert difference<.03,(mode,name,'DAE/STL Ausrichtung',difference)
    count=0; maximum=0
    for (na,a),(nb,b) in itertools.combinations(printed.items(),2):
        maximum=max(maximum,check(f'{mode}: {na} / {nb}',a,b)); count+=1
    for na,a in refs.items():
        for nb,b in printed.items():
            maximum=max(maximum,check(f'{mode}: {na} / {nb}',a,b)); count+=1
    case=m.Manifold.batch_boolean(list(printed.values()),m.OpType.Add)
    front=m.Manifold.batch_boolean([s for n,s in printed.items() if n.startswith('Front_')],m.OpType.Add)
    rear=m.Manifold.batch_boolean([s for n,s in printed.items() if n.startswith('Rueckseite_')],m.OpType.Add)
    # Messung an den exportierten Stegen, ausserhalb der Polstertaschen.
    # Unten verschmilzt der Ansatz mit der Aussenwand und wird dort staerker.
    locator_specs=[]
    for x in [mx+30,mx+value('monitor_w')-54]:
        locator_specs += [(x+1,my-value('clearance')-value('bottom_locator_drop'),1,-1),
                          (x+1,my+value('monitor_h')+value('clearance'),1,1)]
    for y in [my+3,my+value('monitor_h')-17]:
        locator_specs += [(mx-value('clearance'),y+1,0,-1)]
    for y in [my+value('monitor_step_y')+1,my+value('monitor_h')-17]:
        locator_specs += [(mx+value('monitor_w')+value('clearance'),y+1,0,1)]
    roots=[]; tips=[]
    for x,y,axis,sign in locator_specs:
        mb=back(y)
        inner=[x,y][axis]
        measured=[]
        for z in [value('front_t')+.001,(value('front_t')+mb)/2,mb-.01]:
            dims=[.02,.02,.002]; origin=[x-.01,y-.01,z]
            dims[axis]=9.001
            origin[axis]=inner-9 if sign<0 else inner-.001
            section=front ^ cube(dims,origin)
            touching=[]
            for piece in section.decompose():
                bb=piece.bounding_box()
                face=bb[axis+3] if sign<0 else bb[axis]
                if abs(face-inner)<.005: touching.append(bb[axis+3]-bb[axis])
            assert len(touching)==1,(mode,'Haltesteg fehlt',x,y,z,touching)
            measured.append(touching[0])
        # Abgesenkte untere Stege verschmelzen auch in mittlerer Hoehe mit der Aussenwand.
        lower=axis==1 and sign==-1
        middle=y if lower and y-4.5<=value('wall_t') else 4.5
        assert measured[0]>=5.99 and abs(measured[1]-middle)<.01 and abs(measured[2]-3)<.01,(mode,'6/3-mm-Haltesteg',x,y,measured)
        roots.append(measured[0]); tips.append(measured[2])
    report.append(f'{mode}: acht Haltestege gemessen: Ansatz {min(roots):.3f} bis {max(roots):.3f} mm (unten inkl. Wand); freie Kante {min(tips):.3f} bis {max(tips):.3f} mm. Untere Auflagen Y={my-value("clearance")-value("bottom_locator_drop"):.3f} mm.')
    for x in [mx+30,mx+value('monitor_w')-54]:
        # Vollstaendige bisherige Auflagebreite reservieren, ohne unbekannte Padkontur zu erfinden.
        rubber=cube((24,1,value('monitor_d_lower')),(x,my-1,mz))
        check(mode+': vorhandenes 1-mm-Gummipad unten / Gehaeuse',rubber,case)
    report.append(f'{mode}: beide unteren Original-Gummipads (1 mm) haben freien Raum; Monitorposition unveraendert.')
    for lift in [0,.5,2.5,5,8]:
        check(f'{mode}: Deckel-Einfuehrweg {lift} mm',front,rear.translate((0,0,lift)))
    for dx,dy in [(0.2,0),(-0.2,0),(0,.2),(0,-.2)]:
        check(f'{mode}: Rand-Freiraum {dx}/{dy} mm',front,rear.translate((dx,dy,0)))
    guided=abs((front ^ rear.translate((.35,0,0))).volume())
    assert guided>.05,(mode,'Rand begrenzt Querversatz nicht',guided)
    report.append(f'{mode}: Deckel axial einfuehrbar; 0.2 mm Querversatz frei, 0.35 mm wird vom Rand begrenzt.')
    if mode=='geteilt':
        for name,key in printed.items():
            if not name.startswith('Klebekeil_'): continue
            is_front=name.startswith('Klebekeil_Front_')
            prefix='Front_' if is_front else 'Rueckseite_'
            pair=[printed[prefix+'1'],printed[prefix+'2']]
            stem='front' if is_front else 'rear'
            k=(value(stem+'_key_h')-value(stem+'_key_waist'))/(value(stem+'_key_w')-2*value('key_waist_x'))
            taper=value('key_taper')
            normal=np.array(manifest[name]['raw_placement']['rotation']) @ np.array([0,0,1.])
            if is_front:
                # Die vergroesserte Tasche hat bewusst Spiel. Die Teile werden
                # beim Kleben ausgerichtet, kein automatisches Zuziehen behauptet.
                for height in [0,.2,.5,1,2,3]:
                    check(name+f': Einfuehrweg {height} mm',pair[0]+pair[1],key.translate(tuple(normal*height)))
                stop=abs(((pair[0]+pair[1]) ^ key.translate(tuple(-normal*.1))).volume())
                assert stop>.05,(name,'Tiefenanschlag fehlt',stop)
                report.append(f'{name}: Einfuehren mit vergroessertem Z-Spiel frei; 0.1 mm Ueberhub blockiert; kein Selbstspannen vorausgesetzt.')
                continue
            spread=.15
            opened=pair[0].translate((-spread,0,0))+pair[1].translate((spread,0,0))
            obstruction=abs((opened ^ key).volume())
            assert obstruction>.05,(name,'Keil zieht nicht zusammen',obstruction)
            lift=spread*k/taper+.1
            for step in range(7):
                height=lift*(1-step/6)
                delta=min(spread,taper*height/k)
                moving=pair[0].translate((-delta,0,0))+pair[1].translate((delta,0,0))
                check(name+f': Keilweg Schritt {step}',moving,key.translate(tuple(normal*height)))
            stop=abs(((pair[0]+pair[1]) ^ key.translate(tuple(-normal*.1))).volume())
            assert stop>.05,(name,'Tiefenanschlag fehlt',stop)
            report.append(f'{name}: Einfuehr-/Schliessweg geprueft; 0.30 mm zusaetzliche Fuge muss sich beim Setzen schliessen; 0.1 mm Ueberhub blockiert.')
    monitor=refs['REFERENZ_Monitor']
    board_z=D-value('back_t')-value('pi_standoff')-value('pi_pcb_t')
    pi_min=board_z-value('pi_component_envelope')
    hdmi=cube((value('left_margin')-value('wall_t'),value('monitor_h')-value('left_access_from_bottom')-value('left_access_from_top'),value('monitor_d_lower')+value('left_access_extra_depth')),(value('wall_t'),my+value('left_access_from_bottom'),mz))
    # USB-Flansch belegt die aeussersten 3 mm im unteren Eck des HDMI-Kabelraums.
    flange=cube((value('usb_flange_t')+.5,value('usb_flange_w')+1,value('usb_flange_h')+1),
                (value('wall_t'),value('usb_y')-value('usb_flange_w')/2-.5,value('usb_z')-value('usb_flange_h')/2-.5))
    hdmi-=flange
    keepouts={
      'Pi-Steckerhuelle':cube((value('pi_w'),value('pi_h'),value('pi_component_envelope')+value('pi_pcb_t')),(value('pi_x'),value('pi_y'),pi_min)),
      'HDMI-Kabelraum':hdmi,
      'Fingerzugang':cube((value('right_margin')+5,value('right_buttons_height')+2*value('right_button_clearance'),value('monitor_d_lower')+value('right_access_extra_depth')),(mx+value('monitor_w')+value('clearance'),my+value('right_buttons_from_bottom')-value('right_button_clearance'),mz)),
      'Strommodul-Reserve':cube((80,50,17),(W-143,value('power_y'),mz+value('monitor_d_upper')+value('pi_monitor_air'))),
      'USB-C-Leitungsausgang':cube((value('usb_wire_room'),4,4),(value('wall_t')+value('usb_body_l'),value('usb_y')-2,value('usb_z')-2)),
    }
    for name,solid in keepouts.items():
        for other_name,other in [('Druckteile',case),('Monitor',monitor)]:
            vol=check(f'{mode}: {name} / {other_name}',solid,other)
            report.append(f'{mode}: {name} / {other_name}: {vol:.6f} mm3')
    check(mode+': HDMI / PIR',hdmi,refs['REFERENZ_PIR'])
    check(mode+': HDMI / USB-C-Flansch',hdmi,refs['REFERENZ_USB_C'])
    for y in [my+25,my+value('monitor_step_y')+25]:
        section=monitor ^ cube((1,1,30),(mx+25,y,0))
        bb=section.bounding_box()
        assert abs(bb[2]-mz)<.001 and abs(bb[5]-back(y))<.001,(mode,'Monitorstufe',bb)
    opening=cube((value('monitor_w')-2*value('bezel_overlap'),value('monitor_h')-value('bottom_bezel_overlap')-value('bezel_overlap'),value('front_t')),
                 (mx+value('bezel_overlap'),my+value('bottom_bezel_overlap'),0))
    check(mode+': Sichtfenster frei',opening,front)
    uy,uz=value('usb_y'),value('usb_z')
    opening=cube((value('wall_t'),value('usb_open_parallel'),value('usb_open_depth')),
                 (0,uy-value('usb_open_parallel')/2,uz-value('usb_open_depth')/2))
    check(mode+': USB-Rechteckmass',opening,front)
    for y in [uy-value('usb_pitch')/2,uy+value('usb_pitch')/2]:
        screw=m.Manifold.cylinder(6,1.5,circular_segments=48).rotate((0,90,0)).translate((0,y,uz))
        screw+=m.Manifold.cylinder(2,2.75,circular_segments=48).rotate((0,90,0)).translate((-2,y,uz))
        check(mode+': USB-M3x6 / Druckteile',screw,case)
        check(mode+': USB-M3x6 / Kupplung',screw,refs['REFERENZ_USB_C'])
    report.append(f'{mode}: Monitorstufe 10.4/6.1 mm, Sichtfenster und USB-Ausschnitt mit M3x6 geprueft.')
    # Neue PIR-Befestigung: Schrauben ausschliesslich in den zwei PCB-Loechern.
    px=value('pir_x'); py=H-value('pir_from_top')
    pcb_front=value('pir_pcb_z'); pcb_back=pcb_front+value('pir_pcb_t')
    head_z=pcb_front-value('pir_washer_t')
    for x in [px-value('pir_hole_pitch')/2,px+value('pir_hole_pitch')/2]:
        screw=m.Manifold.cylinder(value('pir_screw_length'),1,circular_segments=48).translate((x,py,head_z))
        screw+=m.Manifold.cylinder(value('pir_screw_head_h'),value('pir_screw_head_d')/2,circular_segments=48).translate((x,py,head_z-value('pir_screw_head_h')))
        washer=m.Manifold.cylinder(value('pir_washer_t'),value('pir_washer_d')/2,circular_segments=48)
        washer-=m.Manifold.cylinder(value('pir_washer_t')+2,value('pir_shaft_clearance')/2,circular_segments=48).translate((0,0,-1))
        hardware=screw+washer.translate((x,py,head_z))
        check(mode+': PIR-M2-Schraube und Scheibe / Druckteile',hardware,case)
        check(mode+': PIR-M2-Schraube und Scheibe / PCB-Bauteilhuelle',hardware,refs['REFERENZ_PIR'])
        # Bei abgenommenem Deckel von der Linsenseite zugaenglich.
        driver=m.Manifold.cylinder(head_z-value('pir_screw_head_h')+5,2,circular_segments=48).translate((x,py,-5))
        check(mode+': PIR-Werkzeugzugang / Deckel',driver,rear)
        check(mode+': PIR-Werkzeugzugang / Bauteilhuelle',driver,refs['REFERENZ_PIR'])
    for dx in [-value('pir_pcb_w')/2,value('pir_pcb_w')/2-5]:
        for dy in [-value('pir_pcb_h')/2,value('pir_pcb_h')/2-5]:
            corner=cube((5,5,pcb_back+value('pir_under_height')-value('front_t')-.1),
                        (px+dx,py+dy,value('front_t')+.1))
            check(mode+': PIR-Eckbereich frei von Haltestegen',corner,case)
    for lift in [0,2,8]:
        check(mode+': PIR auf Deckelhalter aufsetzbar',rear,refs['REFERENZ_PIR'].translate((0,0,-lift)))
    moving_lid=rear+refs['REFERENZ_PIR']+refs['REFERENZ_Pi_Platine']
    for lift in [0,.25,.5,1,2.5,5,8,20]:
        check(mode+': Deckel mit Pi/PIR axial herausziehbar',front,moving_lid.translate((0,0,lift)))
        check(mode+': Deckel mit Pi/PIR / Monitor beim Oeffnen',monitor,moving_lid.translate((0,0,lift)))
    report.append(f'{mode}: PIR sitzt am Deckel; M2-Schrauben/Scheiben, Zugriff von Linsenseite, Aufsetzweg und Herausziehen durch Frontoeffnung frei; vier Eckbereiche ohne Haltestege.')
    for x in [value('wall_hole_inset'),W-value('wall_hole_inset')]:
        shaft=m.Manifold.cylinder(D+2,2,circular_segments=48).translate((x,H-value('wall_hole_inset'),-1))
        check(mode+': 4-mm-Wandschraubenkanal',case,shaft)
    layout=json.loads((BASE/'cad_layout.json').read_text())
    assert len(layout['closure'])==6
    expected={(65,value('bottom_screw_y')),(65,H-8),
              (W-65,value('bottom_screw_y')),(W-65,H-8),
              (value('side_screw_inset'),H/2),(W-value('side_screw_inset'),H/2)}
    assert np.allclose(sorted(map(tuple,layout['closure'])),sorted(expected),atol=1e-6,rtol=0)
    for x,y in layout['closure']:
        shaft=m.Manifold.cylinder(8,1.5,circular_segments=48).translate((x,y,D-8))
        check(mode+': M3-Deckelschraube',case,shaft)
        head_h=(value('m3_head_d')-value('m3_clearance'))/2
        head=m.Manifold.cylinder(head_h,value('m3_clearance')/2-.05,
            value('m3_head_d')/2-.05,circular_segments=48).translate((x,y,D-head_h))
        check(mode+': M3-Senkkopfraum',case,head)
        entry=D-value('back_t')-value('m3_insert_depth')
        insert=m.Manifold.cylinder(value('m3_insert_depth'),value('m3_insert_d')/2-.05,
            circular_segments=48).translate((x,y,entry))
        check(mode+': M3-Einsatzbohrung frei',front,insert)
        # Die Bohrung allein genuegt nicht: umlaufendes Material und Blindboden
        # muessen auch am linken, ueber dem HDMI-Raum liegenden Dom vorhanden sein.
        radius=(value('bottom_boss_d') if y==value('bottom_screw_y') else value('closure_boss_d'))/2-.1
        sleeve=m.Manifold.cylinder(value('m3_insert_depth')-.2,radius,circular_segments=48)
        sleeve-=m.Manifold.cylinder(value('m3_insert_depth'),value('m3_insert_d')/2+.1,circular_segments=48).translate((0,0,-.1))
        sleeve=sleeve.translate((x,y,entry+.1))
        assert abs((sleeve-front).volume())<.02,(mode,'M3-Gewindesitz ohne tragenden Ring',x,y)
        floor=m.Manifold.cylinder(.8,value('m3_insert_d')/2,circular_segments=48).translate((x,y,entry-.9))
        assert abs((floor-front).volume())<.02,(mode,'M3-Blindboden fehlt',x,y)
    for i,(x,y,z) in enumerate(layout['cap_centers']):
        cap=printed[f'Andruckteller_{i+1}'].translate((-x,-y,-z))
        for angle in range(-360,361,45):
            # Rohkoordinaten sind gespiegelt: +Drehung ergibt -Z, exportiert Rechtsgewinde.
            travel=-angle*value('pressure_thread_pitch')/360
            moved=cap.rotate((0,0,angle)).translate((x,y,z+travel))
            check(mode+f': M10-Teller {i+1}, Schraubweg {angle} Grad',moved,front+rear)
    report += [f'{mode}: {len(printed)} Druckteile durch reine Rotation/Translation deckungsgleich mit STL; keine Spiegelung.',
      f'{mode}: {count} paarweise Schnittpruefungen; groesstes Schnittvolumen {maximum:.6f} mm3.',
      f'{mode}: Wandschraubenkanale und vier gedruckte M10-Teller inkl. Schraubweg +/-1.5 mm geprueft.',
      f'{mode}: sechs M3-Schliessschrauben samt Senkungen, Einsatzbohrungen, tragenden Ringen und Blindboeden; seitliche Mittelpunkte Y={H/2:.1f} mm; keine Schrauben in der permanenten Teilungsnaht.',
      f'{mode}: Monitor-Pi Mindestabstand in der angenommenen Huelle: {pi_min-back(value("pi_y")):.2f} mm.']

report += ['1-mm-Polster in 0.2-mm-Taschen: nominal 0.8 mm Einbauraum / 0.2 mm Kompression.',
 'Reale Kabelbiegeradien, Monitorrueckkontur, PIR-Unterseite und Polsterhaerte muessen am Original geprueft werden.']
report += ['FEHLER: '+line for line in failed] if failed else ['Alle digitalen Schnitt- und Formatpruefungen bestanden.']
(BASE/'kollisionspruefung.txt').write_text('\n'.join(report)+'\n',encoding='utf-8')
print('\n'.join(report),flush=True)
assert not failed,'\n'.join(failed)
