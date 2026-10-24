/* KitaFenster — direkt montierter Pi, Wandbefestigung von vorn.
   Alle Masse mm. Anschluss-/Polster-/Steckerpassung am Original pruefen.
   Rechenkoordinaten: X rechts, Y oben, Z-Tiefe zur Wand.
   Ausgabe: Z gespiegelt (Wand bei -36), damit links/rechts von vorn stimmen.
   Komponenten sind Platzhalter.
   Links-rechts-Teilung mit verklebten Naehten.
*/

include <metric_threads.scad>;

/* [Ansicht] */
part = "assembly"; // [assembly,front,rear,front_key,rear_key,pressure_cap,monitor_dummy,pi_dummy,pir_dummy,usb_dummy,power_dummy,layout]
seam_features = true; // false: ungeteilte Schalen ohne Klebekeiltaschen
half = -1; // [-1:Gesamt,0:links,1:rechts]
exploded = 0; // [0:1:60]
show_components = true;
show_joins = true;
show_keepouts = false;

/* [Monitor] */
monitor_w = 355.4;
monitor_h = 221;
monitor_d_lower = 10.4;
monitor_d_upper = 6.1;
monitor_step_y = 100; // von der Monitorunterkante; Front als gemeinsame Bezugsebene
clearance = 0.6;
bottom_locator_drop = 1; // Original-Gummipads: beide unteren Auflagen 1 mm in -Y versetzen
bottom_rubber_clearance = 0.2; // Abstand zum benachbarten unteren Schraubdom
bezel_overlap = 3;
bottom_bezel_overlap = 18; // unterer Originalrahmen 20 mm, 2 mm Reserve zur Bildflaeche
front_pad = 0.6;
rear_pad_gap = 0.8; // fuer ca. 1-mm-weiche Pads, nicht hart verspannen
pad_recess = 0.2;
locator_base_t = 6; // Haltestege am Vorderteil: mindestens 6 mm am Gehaeuseansatz
locator_tip_t = 3; // freie Kante; Schraege nur auf der monitorabgewandten Seite
pressure_post_gap = 6;
pressure_post_tip_w = 16;
pressure_post_tip_h = 16;
pressure_post_base_w = 24;
pressure_post_base_h = 18;
pressure_cap_t = 3.2;
pressure_hex_af = 16;
pressure_thread_d = 10;
pressure_thread_pitch = 1.5;
pressure_thread_length = 12;
pressure_male_radial = -0.05;
pressure_female_radial = 0.20; // radial zusammen 0.25 mm Nennspiel
pressure_blind_floor = 1.8;

/* [Gehaeuse] */
left_margin = 50; // vorlaeufig: HDMI-Stecker UND Biegung innerhalb des Kabelraums
right_margin = 18;
top_margin = 18;
bottom_margin = 8;
front_t = 3;
wall_t = 3;
back_t = 3;
total_depth = 36;
corner_r = 7;
split_gap = 0.25; // auch die Stossflaechen werden verklebt
rim_height = 5;
rim_t = 2;
rim_clearance = 0.25;
rim_lead = 0.5;
rim_lead_h = 0.8;
glue_gap = 0.2; // kleine Abstandspunkte halten den Boden-Klebespalt
glue_flank_gap = 0.15; // Klebstoffraum ausserhalb der vier Keil-Kontaktstreifen
glue_end_gap = 0.2;
front_pocket_z_extra = 0.4; // gesamte Zugabe zur Druck-Z-Breite der Fronttaschen
glue_land_t = 1; // lokale innere Verstaerkung um die Taschen
key_pocket_depth = 1.4; // 2.6 mm Restwand unter dem verstaerkten Klebesitz
key_t = 2.4;
key_taper = 0.18; // Y-Zunahme je Flanke pro mm Einschubweg
key_fit = 0; // Nennkontakt der Keilflanken
key_waist_x = 2;
front_key_w = 40;
front_key_h = 12;
front_key_waist = 6;
rear_key_w = 36;
rear_key_h = 24;
rear_key_waist = 10;

/* [Seitlicher Zugang - von vorne betrachtet] */
left_access_from_bottom = 20; // Bezug: Unterkante des Monitors
left_access_from_top = 60; // obere linke Zone fuer PIR reserviert
right_buttons_from_bottom = 5;
right_buttons_height = 90;
right_button_clearance = 2;
left_access_extra_depth = 8;
right_access_extra_depth = 3;

/* [Wandschrauben - tatsaechlichen Senkkopf messen] */
wall_screw_clearance = 4.5; // fuer Schraubenschaft ca. 4 mm
wall_head_d = 9.4; // Arbeitsmass, kein universelles Schraubenkopf-Normmass
wall_head_angle = 90;
wall_hole_inset = 10;
wall_post_d = 18;

/* [Rueckseitige M3-Verschraubung] */
m3_clearance = 3.4;
m3_head_d = 6.6;
m3_insert_d = 4.1; // an den verwendeten M3-Einsatz anpassen
m3_insert_depth = 5.2;
closure_boss_d = 12;
bottom_boss_d = 8; // schmale untere Rahmenkante
bottom_screw_y = 4.4;
side_screw_inset = 8; // Mitte der zusaetzlichen Schrauben ab linker/rechter Aussenkante

/* [Pi 3 A+ - direkt an Rueckseite] */
pi_w = 65;
pi_h = 56;
pi_x = 55;
pi_y = 125; // hinter dem duenneren oberen Monitorbereich
pi_hole_x = 58;
pi_hole_y = 49;
pi_standoff = 4;
pi_pcb_t = 1.6;
pi_component_envelope = 16; // inkl. FLACHER GPIO-Stecker; messen!
pi_monitor_air = 1.4;
pi_insert_d = 3.5; // M2.5-Einsatz, reale Druckpassung testen
pi_insert_depth = 4.5;

/* [PIR und Stromanschluss - vorlaeufig] */
pir_pcb_w = 33; // neues Nutzerfoto; am Original pruefen
pir_pcb_h = 25;
pir_opening_d = 23;
pir_pcb_z = 10;
pir_x = 25;
pir_from_top = 50;
pir_pcb_t = 1.6;
pir_under_height = 15; // Bauteilreserve auch an den Ecken, nach neuem Foto
pir_lens_base_d = 23;
pir_hole_pitch = 28; // Mitte-Mitte in X, aus frueherer Zeichnung; Original messen
pir_pcb_hole_d = 2.3; // Arbeitsmass fuer M2; tatsaechlichen PCB-Lochdurchmesser pruefen
pir_seat_d = 4.6; // nur die freie Ringflaeche direkt um das Platinenloch
pir_seat_base_w = 10;
pir_seat_base_h = 16;
pir_component_gap = 0.8;
pir_brace_z = 30; // Querversteifung hinter der Bauteilhuelle
pir_insert_d = 3.2; // Arbeitsmass M2-Waermeeinsatz, mit den verwendeten Einsaetzen abgleichen
pir_insert_depth = 3.2;
pir_shaft_clearance = 2.3;
pir_shaft_depth = 4.2;
pir_screw_length = 6;
pir_screw_head_d = 3.8; // M2-Zylinder-/Linsenkopf, keine Senkung in der Platine
pir_screw_head_h = 2;
pir_washer_d = 4.5;
pir_washer_t = 0.5;
pir_post_clearance_d = 5.2; // freie Zonen fuer Stuetzen hinter den PCB-Loechern
usb_open_parallel = 12.5; // entlang des 17-mm-Lochabstands, Y; nach letzter beschrifteter Nutzerskizze
usb_open_depth = 10.5; // Richtung Gehaeusetiefe Z
usb_pitch = 17;
usb_screw_clearance = 3.4;
usb_y = 18;
usb_z = 25;
usb_flange_w = 26; // vorlaeufige Platzreserve, kein vermessenes Flanschmodell
usb_flange_h = 14;
usb_flange_t = 3;
usb_body_l = 30; // hinter Montageflaeche (Innenseite der Seitenwand), inkl. Kabelknick
usb_wire_room = 15;

/* [Hidden] */
raw_coordinates = false; // nur Build-Pipeline: ungespiegelte Rechenkoordinaten
$fn = 48;
eps = 0.02;
ow = monitor_w + 2*clearance + left_margin + right_margin;
oh = monitor_h + 2*clearance + top_margin + bottom_margin;
front_depth = total_depth-back_t;
mx = left_margin+clearance;
my = bottom_margin+clearance;
monitor_z = front_t+front_pad;
function monitor_thickness(y) = y < my+monitor_step_y ? monitor_d_lower : monitor_d_upper;
function monitor_back(y) = monitor_z+monitor_thickness(y);
function pressure_post_z(y) = monitor_back(y)+pressure_post_gap;
function pressure_cap_z(y) = monitor_back(y)+rear_pad_gap-pad_recess;
function guide_pad_h(y) = monitor_thickness(y)>8 ? 8 : 4;
pi_board_z = front_depth-pi_standoff-pi_pcb_t;
pi_front_z = pi_board_z-pi_component_envelope;
key_embed = key_pocket_depth-glue_gap;
front_key_base = wall_t+glue_land_t-key_pocket_depth+glue_gap;
rear_key_base = front_depth-glue_land_t+key_pocket_depth-glue_gap;
pir_y = oh-pir_from_top;
pir_back_z = pir_pcb_z+pir_pcb_t;
pir_shoulder_z = pir_back_z+pir_under_height+pir_component_gap;
left_y0 = my+left_access_from_bottom;
left_y1 = my+monitor_h-left_access_from_top;
right_y0 = my+right_buttons_from_bottom-right_button_clearance;
right_y1 = my+right_buttons_from_bottom+right_buttons_height+right_button_clearance;
left_access_z1 = 0;
//left_access_z1 = monitor_z+monitor_d_lower+left_access_extra_depth;
right_access_z1 = monitor_z+monitor_d_lower+right_access_extra_depth;
left_guide_y = [my+3,my+monitor_h-17];
right_guide_y = [my+monitor_step_y+1,my+monitor_h-17];
power_y = 125;
power_z = monitor_z+monitor_d_upper+pi_monitor_air;

wall_points = [[wall_hole_inset,oh-wall_hole_inset],
               [ow-wall_hole_inset,oh-wall_hole_inset]];
corner_closure_points = [for(x=[65,ow-65],y=[bottom_screw_y,oh-8]) [x,y]];
side_closure_points = [[side_screw_inset,oh/2],[ow-side_screw_inset,oh/2]];
closure_points = concat(corner_closure_points,side_closure_points);
pi_points = [for(x=[pi_x+3.5,pi_x+3.5+pi_hole_x],
                 y=[pi_y+3.5,pi_y+3.5+pi_hole_y]) [x,y]];
// Die Rueckhalter beruehren nur die Randzone des geschlossenen Monitorgehaeuses.
retainer_points = [for(x=[mx+10,mx+monitor_w-10],
                      y=[my+9,my+monitor_h-9]) [x,y]];
pir_points = [for(x=[-pir_hole_pitch/2,pir_hole_pitch/2]) [pir_x+x,pir_y]];

front_key_positions = [for(side=[0:1],z=[10,front_depth-8])
    [[ow/2,side==0 ? front_key_base : oh-front_key_base,z],side==0 ? -90 : 90]];
rear_key_positions = [for(y=[28,oh/2,oh-28]) [[ow/2,y,rear_key_base],180]];

assert(total_depth>=36);
assert(pi_y>=my+monitor_step_y && pi_y+pi_h<my+monitor_h);
assert(pi_front_z >= monitor_back(pi_y)+pi_monitor_air,
       "Zu flach fuer Pi und seine Kabel im oberen Monitorbereich");
assert(top_margin>=18 && left_margin>=18 && right_margin>=18);
assert(front_depth-rim_height > max(left_access_z1,right_access_z1),
       "Fuehrungsrand darf nicht in die seitlichen Zugangsfenster reichen");
assert(wall_t+glue_land_t-key_pocket_depth>=2.5 && back_t+glue_land_t-key_pocket_depth>=2.5);
assert(key_embed>0 && key_t>key_embed && glue_gap>0);
assert(rim_t>rim_lead && rim_clearance>0);
assert(left_access_from_bottom>=20 && left_access_from_top>=20);
assert(right_y0>wall_t && right_y1+3<right_guide_y[0]);
assert(wall_head_d<wall_post_d-5);
assert(rear_pad_gap>0 && bezel_overlap>0);
assert(locator_base_t>=6 && locator_tip_t>=3 && locator_base_t>locator_tip_t);
assert(half>=-1 && half<=1);
assert(pi_x+pi_w < ow/2-20 && pi_y+pi_h < oh-35,
       "Pi muss vollstaendig auf der linken Rueckseite bleiben");
assert(oh+4<256 && ow/2+4<256,
       "Passt nicht flach auf den P1S mit 2-mm-Brim: Monitorhoehe/Raender pruefen");
assert(bottom_screw_y+bottom_boss_d/2 < my);
assert(len(closure_points)==6);
assert(side_screw_inset-closure_boss_d/2>0 &&
       side_screw_inset-closure_boss_d/2<wall_t,
       "Seitliche Schraubdome muessen mit der Aussenwand verbunden sein");
assert(front_depth-m3_insert_depth>left_access_z1+2,
       "HDMI-Kabelraum muss unter dem linken Gewindesitz frei bleiben");
assert(oh/2-closure_boss_d/2>right_y1,
       "Rechter Schraubdom muss oberhalb des Tastenfensters sitzen");
assert(pir_y-pir_pcb_h/2-8 > left_y1, "PIR und HDMI-Zone ueberschneiden sich");
assert(pir_hole_pitch-pir_seat_d > pir_lens_base_d,
       "PIR-Auflager und Linsensockel brauchen seitlichen Abstand");
assert(pir_hole_pitch+pir_seat_d <= pir_pcb_w,
       "PIR-Auflager muessen vollstaendig unter der Platine liegen");
assert(pir_insert_depth<pir_shaft_depth && pir_back_z+pir_shaft_depth<pir_shoulder_z);
assert(pir_pcb_z+pir_pcb_t+pir_under_height < front_depth-rim_height);
assert(pir_post_clearance_d > pir_seat_d);
assert(pir_shoulder_z<pir_brace_z && pir_brace_z<front_depth);
assert(pir_x-pir_hole_pitch/2-pir_seat_base_w/2 > wall_t+rim_clearance+rim_t);
assert(usb_z+usb_flange_h/2<front_depth && usb_y-usb_flange_w/2>wall_t);
assert(usb_open_parallel+usb_screw_clearance<usb_pitch);
assert(wall_t+usb_body_l+usb_wire_room<mx-2);
echo("Gehaeuse", [ow,oh,total_depth]);
echo("Monitor-Pi Abstand",pi_front_z-monitor_back(pi_y));
echo("Wandbohrungen XY",wall_points,"Lochabstand",ow-2*wall_hole_inset);
echo("M3 Rueckseitenverschraubung",len(closure_points));
echo("HDMI-Kabelraum B/H/T",[mx-clearance-wall_t,left_y1-left_y0,left_access_z1-monitor_z]);
echo("Tastenfenster H/T",[right_y1-right_y0,right_access_z1-monitor_z]);

module rounded_box(w,h,d,r=3) {
    linear_extrude(d) hull()
        for(x=[r,w-r],y=[r,h-r]) translate([x,y]) circle(r=r);
}

module countersink_front(d,head,depth,angle=90) {
    cylinder(d=d,h=depth+2*eps);
    cylinder(d1=head,d2=d,h=(head-d)/(2*tan(angle/2)));
}

module rear_screw_hole(z0,z1) {
    translate([0,0,z0-eps]) cylinder(d=m3_clearance,h=z1-z0+2*eps);
    translate([0,0,z1-(m3_head_d-m3_clearance)/2])
        cylinder(d1=m3_clearance,d2=m3_head_d,h=(m3_head_d-m3_clearance)/2+eps);
}

module tapered_locator(length,depth) {
    // Lokale Achsen: X Steglaenge, +Y vom Monitor weg, +Z zur freien Kante.
    // Y=0 bleibt eine gerade Monitorauflage. Die Rueckseite laeuft 6 -> 3 mm.
    hull() {
        translate([0,0,-eps]) cube([length,locator_base_t,eps]);
        translate([0,0,front_pad+depth-eps]) cube([length,locator_tip_t,eps]);
    }
}
module monitor_locators() {
    for(x=[mx+30,mx+monitor_w-54]) {
        translate([x,my-clearance-bottom_locator_drop,front_t]) mirror([0,1,0]) tapered_locator(24,monitor_d_lower);
        translate([x,my+monitor_h+clearance,front_t]) tapered_locator(24,monitor_d_upper);
    }
    // Kurze Endfuehrungen lassen den mittleren Bereich fuer Kabel und Finger frei.
    for(y=left_guide_y)
        translate([mx-clearance,y,front_t]) rotate([0,0,90]) tapered_locator(14,monitor_thickness(y));
    for(y=right_guide_y)
        translate([mx+monitor_w+clearance,y+14,front_t]) rotate([0,0,-90]) tapered_locator(14,monitor_thickness(y));
}

module monitor_pad_pockets() {
    // 1-mm-Polster in 0.2-mm-Taschen: bei 0.6-mm-Spiel rund 0.2 mm Vorspannung.
    for(x=[mx+35,mx+monitor_w-49]) {
        translate([x,my-clearance-bottom_locator_drop-pad_recess,monitor_z+1]) cube([14,pad_recess+eps,8]);
        translate([x,my+monitor_h+clearance-eps,monitor_z+1]) cube([14,pad_recess+eps,4]);
        translate([x,my+5,front_t-pad_recess]) cube([14,8,pad_recess+eps]);
        translate([x,my+monitor_h-2.5,front_t-pad_recess]) cube([14,2,pad_recess+eps]);
    }
    for(y=left_guide_y) {
        translate([mx-clearance-pad_recess,y+3,monitor_z+1]) cube([pad_recess+eps,8,guide_pad_h(y)]);
        translate([mx+0.5,y+3,front_t-pad_recess]) cube([2,8,pad_recess+eps]);
    }
    for(y=right_guide_y) {
        translate([mx+monitor_w+clearance-eps,y+3,monitor_z+1]) cube([pad_recess+eps,8,guide_pad_h(y)]);
        translate([mx+monitor_w-2.5,y+3,front_t-pad_recess]) cube([2,8,pad_recess+eps]);
    }
}

module threaded_pressure_plate(d,p,length,radial) {
    root=d/2+radial-17/24*sqrt(3)*p/2;
    major=d/2+radial;
    difference() {
        union() {
            cylinder(d=pressure_hex_af/cos(30),h=pressure_cap_t,$fn=6);
            // Kleine konische Verstaerkung bleibt vor dem Gewindeeingang.
            translate([0,0,pressure_cap_t-eps])
                cylinder(r1=d==4 ? 3 : 5.75,r2=root,h=1.2+eps);
            translate([0,0,pressure_cap_t-eps]) intersection() {
                metric_thread(d,p,-eps,length+eps,radial);
                union() {
                    cylinder(r=major+eps,h=length-p);
                    translate([0,0,length-p-eps]) cylinder(r1=major+eps,r2=root,h=p+2*eps);
                }
            }
        }
        // Polster bedeckt die Kontaktflaeche; Verstellung von Hand am Sechskant.
        translate([-6,-4,-eps]) cube([12,8,pad_recess+eps]);
    }
}
module pressure_cap() {
    threaded_pressure_plate(pressure_thread_d,pressure_thread_pitch,pressure_thread_length,pressure_male_radial);
}
module pressure_thread_hole(p,radial=pressure_female_radial) {
    start=pressure_cap_z(p[1])+pressure_cap_t-eps;
    entry=pressure_post_z(p[1]);
    // Gemeinsamer Phasenbezug zum Aussengewinde des Tellers in Nennstellung.
    translate([p[0],p[1],start])
        metric_thread(pressure_thread_d,pressure_thread_pitch,entry-start-eps,
                      total_depth-pressure_blind_floor-start,radial,true);
    translate([p[0],p[1],entry-eps])
        cylinder(d1=pressure_thread_d+2*radial+1,d2=pressure_thread_d+2*radial,h=0.6+eps);
}
// Doppelter Schwalbenschwanz: nur Y verbreitert sich mit der Einschubhoehe.
// Die schraegen Flanken druecken jede Haelfte zur Mitte. Stirnflaechen in X
// haben Spiel, damit sie die Teile nicht wieder voneinander wegdruecken.
function key_outline(w,h,waist,z,add_y=0,extra_x=0) =
    let(k=(h-waist)/(w-2*key_waist_x),
        a=h/2+extra_x*k+key_taper*(z-key_embed)+add_y,
        b=waist/2+key_taper*(z-key_embed)+add_y,
        x=w/2+extra_x)
    [[-x,-a],[-key_waist_x,-b],[key_waist_x,-b],[x,-a],
     [x,a],[key_waist_x,b],[-key_waist_x,b],[-x,a]];

module tapered_key_shape(w,h,waist,z0,z1,add_y=0,extra_x=0) {
    pts=[for(z=[z0,z1]) each [for(p=key_outline(w,h,waist,z,add_y,extra_x)) [p[0],p[1],z]]];
    polyhedron(points=pts,faces=concat(
        [[0,1,2,3,4,5,6,7],[15,14,13,12,11,10,9,8]],
        [for(j=[0:7]) [j,j+8,(j+1)%8+8,(j+1)%8]]),convexity=6);
}
module glue_key(is_front=true) {
    w=is_front ? front_key_w : rear_key_w;
    h=is_front ? front_key_h : rear_key_h;
    waist=is_front ? front_key_waist : rear_key_waist;
    union() {
        tapered_key_shape(w,h,waist,0,key_t,-glue_flank_gap+key_fit);
        // Vier schmale Kontaktstreifen; die uebrigen Flanken erhalten Klebstoff.
        for(x=[-12,6]) intersection() {
            tapered_key_shape(w,h,waist,0,key_t,key_fit);
            translate([x,-h,-eps]) cube([6,2*h,key_t+2*eps]);
        }
        // Tiefenanschlag und definierte Klebefilmstaerke.
        for(x=[-10,10],y=[-2,2]) translate([x,y,-glue_gap])
            cylinder(d=1.2,h=glue_gap+eps,$fn=16);
    }
}
module glue_key_pocket(is_front=true) {
    tapered_key_shape(is_front ? front_key_w : rear_key_w,
        is_front ? front_key_h : rear_key_h,
        is_front ? front_key_waist : rear_key_waist,
        -glue_gap,key_embed+eps,is_front ? front_pocket_z_extra/2 : 0,glue_end_gap);
}
module glue_land(is_front=true) {
    w=(is_front ? front_key_w : rear_key_w)+4;
    h=(is_front ? front_key_h+2 : rear_key_h+4);
    translate([-w/2,-h/2,key_embed-glue_land_t-eps])
        rounded_box(w,h,glue_land_t+eps,1.2);
}
module place_lands(is_front=true) {
    for(pos=is_front ? front_key_positions : rear_key_positions)
        translate(pos[0]) rotate([pos[1],0,0]) glue_land(is_front);
}
module place_keys(is_front=true,pocket=false) {
    for(pos=is_front ? front_key_positions : rear_key_positions)
        translate(pos[0]) rotate([pos[1],0,0])
            if(pocket) glue_key_pocket(is_front); else glue_key(is_front);
}

module rear_rim() {
    a=wall_t+rim_clearance;
    ri=max(1,corner_r-a-rim_t);
    difference() {
        union() {
            translate([a,a,front_depth-rim_height+rim_lead_h])
                rounded_box(ow-2*a,oh-2*a,rim_height-rim_lead_h+eps,corner_r-a);
            hull() {
                translate([a+rim_lead,a+rim_lead,front_depth-rim_height])
                    rounded_box(ow-2*(a+rim_lead),oh-2*(a+rim_lead),eps,corner_r-a-rim_lead);
                translate([a,a,front_depth-rim_height+rim_lead_h])
                    rounded_box(ow-2*a,oh-2*a,eps,corner_r-a);
            }
        }
        translate([a+rim_t,a+rim_t,front_depth-rim_height-eps])
            rounded_box(ow-2*(a+rim_t),oh-2*(a+rim_t),rim_height+3*eps,ri);
        // Lokale Aussparungen um die Drucksaeulen und Schliessdome.
        for(p=wall_points) translate([p[0],p[1],front_depth-rim_height-eps])
            cylinder(d=wall_post_d+2*rim_clearance,h=rim_height+3*eps);
        for(p=closure_points) translate([p[0],p[1],front_depth-rim_height-eps])
            cylinder(d=(p[1]==bottom_screw_y ? bottom_boss_d : closure_boss_d)+2*rim_clearance,h=rim_height+3*eps);
        // Freiraum fuer den innen anliegenden USB-C-Flansch.
        translate([-eps,usb_y-usb_flange_w/2-2,front_depth-rim_height-eps])
            cube([12,usb_flange_w+4,rim_height+3*eps]);
        // Bei der flachen Schale reichen die hinteren Frontkeile bis nahe an den Deckel.
        // Nur hier den Fuehrungsrand aussparen; Rueckenplatte bleibt durchgehend.
        if(seam_features) for(y=[-eps,oh-8])
            translate([ow/2-front_key_w/2-3,y,front_depth-rim_height-eps])
                cube([front_key_w+6,8+2*eps,rim_height+3*eps]);
    }
}

module usb_panel_holes() {
    translate([-eps,usb_y-usb_open_parallel/2,usb_z-usb_open_depth/2])
        cube([wall_t+2*eps,usb_open_parallel,usb_open_depth]);
    for(y=[usb_y-usb_pitch/2,usb_y+usb_pitch/2])
        translate([-eps,y,usb_z]) rotate([0,90,0]) cylinder(d=usb_screw_clearance,h=wall_t+2*eps);
}

module side_access() {
    // Links bleibt die 3-mm-Aussenwand geschlossen; Kabel werden innen gefuehrt.
    translate([wall_t,left_y0,monitor_z])
        cube([mx-clearance-wall_t,left_y1-left_y0,left_access_z1-monitor_z]);
    // Rechts durchgehendes Seitenfenster; Frontlippe und hinterer Wandsteg bleiben.
    translate([mx+monitor_w+clearance,right_y0,monitor_z])
        cube([ow-mx-monitor_w-clearance+eps,right_y1-right_y0,right_access_z1-monitor_z]);
}

// PIR und Pi sitzen gemeinsam auf dem Deckel. Nur zwei Loch-Ringflaechen
// beruehren die PCB-Rueckseite; die Ecken und Bestueckung bleiben frei.
module pir_rear_mount() {
    for(p=pir_points) translate([p[0],p[1],0]) {
        translate([0,0,pir_back_z]) cylinder(d=pir_seat_d,h=pir_shoulder_z-pir_back_z+eps);
        hull() {
            translate([0,0,pir_shoulder_z]) cylinder(d=pir_seat_d,h=eps);
            translate([-pir_seat_base_w/2,-pir_seat_base_h/2,front_depth-eps])
                rounded_box(pir_seat_base_w,pir_seat_base_h,2*eps,1);
        }
    }
    // Verbindung beider Fuesse, hinter der 15-mm-Bauteilreserve.
    translate([pir_x-pir_hole_pitch/2,pir_y-3,pir_brace_z])
        cube([pir_hole_pitch,6,front_depth-pir_brace_z+eps]);
}
module pir_mount_holes() {
    for(p=pir_points) {
        translate([p[0],p[1],pir_back_z-eps])
            cylinder(d=pir_insert_d,h=pir_insert_depth+eps);
        translate([p[0],p[1],pir_back_z-eps])
            cylinder(d=pir_shaft_clearance,h=pir_shaft_depth+eps);
    }
}
module pressure_posts() {
    // Druckteller/Schraubenposition bleiben erhalten; Fuss wird zum Deckel breiter.
    for(p=retainer_points) hull() {
        translate([p[0]-pressure_post_tip_w/2,p[1]-pressure_post_tip_h/2,pressure_post_z(p[1])])
            cube([pressure_post_tip_w,pressure_post_tip_h,eps]);
        translate([p[0]-pressure_post_base_w/2,p[1]-pressure_post_base_h/2,front_depth-eps])
            cube([pressure_post_base_w,pressure_post_base_h,2*eps]);
        }
}

module front() {
    difference() {
        union() {
            difference() {
                rounded_box(ow,oh,front_depth,corner_r);
                translate([wall_t,wall_t,front_t])
                    cube([ow-2*wall_t,oh-2*wall_t,front_depth+eps]);
                translate([mx+bezel_overlap,my+bottom_bezel_overlap,-eps])
                    cube([monitor_w-2*bezel_overlap,monitor_h-bottom_bezel_overlap-bezel_overlap,front_t+2*eps]);
                translate([pir_x,pir_y,-eps]) cylinder(d=pir_opening_d,h=front_t+2*eps);
            }
            monitor_locators();
            if(seam_features) place_lands(true);
            // Drucksaeulen bis zur Rueckplatte: Wandschrauben belasten nicht das Panel.
            for(p=wall_points) translate([p[0],p[1],0]) cylinder(d=wall_post_d,h=front_depth);
            for(p=closure_points) translate([p[0],p[1],front_t-eps])
                cylinder(d=p[1]==bottom_screw_y ? bottom_boss_d : closure_boss_d,h=front_depth-front_t+eps);
        }
        // Links bleibt der Kabelraum auch unter dem mittleren Schraubdom frei.
        // Der Gewindesitz liegt vollstaendig dahinter und ist mit der Wand verbunden.
        side_access();
        monitor_pad_pockets();
        // Original-Gummipads an den unteren Auflagen: auch den angrenzenden
        // rechten Schraubdom lokal freistellen. Sein hinterer Gewindesitz bleibt erhalten.
        for(x=[mx+30,mx+monitor_w-54])
            translate([x,my-bottom_locator_drop-bottom_rubber_clearance,monitor_z])
                cube([24,bottom_locator_drop+bottom_rubber_clearance+eps,monitor_d_lower]);
        usb_panel_holes();
        if(seam_features) place_keys(true,true);
        for(p=wall_points) translate([p[0],p[1],-eps])
            countersink_front(wall_screw_clearance,wall_head_d,front_depth+eps,wall_head_angle);
        for(p=closure_points) translate([p[0],p[1],front_depth-m3_insert_depth])
            cylinder(d=m3_insert_d,h=m3_insert_depth+eps);
        // Schlitze nur in freien Bereichen der Ober-/Unterkante.
        for(x=[34:12:ow-34]) if(abs(x-ow/2)>55 && abs(abs(x-ow/2)-75)>13 && x<ow-108)
            if(min([for(p=closure_points) abs(x+3-p[0])]) > closure_boss_d/2+4)
                for(y=[-eps,oh-wall_t-eps])
                    translate([x,y,front_depth-rim_height-10]) cube([6,wall_t+2*eps,8]);
    }
}

module rear() {
    difference() {
        union() {
            translate([0,0,front_depth]) rounded_box(ow,oh,back_t,corner_r);
            rear_rim();
            if(seam_features) place_lands(false);
            // Integrierte Pi-Abstandhalter, kein Zwischenbrett/Traeger.
            for(p=pi_points) translate([p[0],p[1],front_depth-pi_standoff])
                cylinder(d=7.5,h=pi_standoff+eps);
            pressure_posts();
            pir_rear_mount();
        }
        for(p=wall_points) translate([p[0],p[1],front_depth-eps])
            cylinder(d=wall_screw_clearance,h=back_t+2*eps);
        for(p=closure_points) translate([p[0],p[1],0]) rear_screw_hole(front_depth,total_depth);
        for(p=pi_points) translate([p[0],p[1],front_depth-pi_standoff-eps])
            cylinder(d=pi_insert_d,h=pi_insert_depth+eps);
        if(seam_features) place_keys(false,true);
        pir_mount_holes();
        for(p=retainer_points) pressure_thread_hole(p);
    }
}

module half_cut(q) {
    if(q<0) children();
    else intersection() {
        children();
        // Fugen nur in der Mitte; Aussenkontur und Bohrungskoordinaten bleiben erhalten.
        translate([q==0 ? -1 : ow/2+split_gap/2,-1,-100])
            cube([ow/2+1-split_gap/2,oh+2,300]);
    }
}

module monitor_dummy() {
    translate([mx,my,monitor_z]) union() {
        rounded_box(monitor_w,monitor_h,monitor_d_upper,3);
        intersection() {
            rounded_box(monitor_w,monitor_h,monitor_d_lower,3);
            translate([-eps,-eps,0]) cube([monitor_w+2*eps,monitor_step_y+eps,monitor_d_lower]);
        }
    }
}
module pi_dummy() {
    difference() {
        translate([pi_x,pi_y,pi_board_z]) cube([pi_w,pi_h,pi_pcb_t]);
        for(p=pi_points) translate([p[0],p[1],pi_board_z-eps]) cylinder(d=2.75,h=pi_pcb_t+2*eps);
    }
}
module pir_dummy() {
    translate([pir_x,pir_y,0]) difference() {
      union() {
        translate([-pir_pcb_w/2,-pir_pcb_h/2,pir_pcb_z])
            cube([pir_pcb_w,pir_pcb_h,pir_pcb_t]);
        translate([0,0,pir_pcb_z-3]) {
            intersection() { sphere(r=pir_lens_base_d/2); translate([-12,-12,-12]) cube([24,24,12]); }
            cylinder(d=pir_lens_base_d,h=3+eps);
        }
        // Konservative Platzreserve inkl. bestueckter Ecken, kein exaktes Bauteilmodell.
        translate([-pir_pcb_w/2,-pir_pcb_h/2,pir_pcb_z+pir_pcb_t-eps])
            cube([pir_pcb_w,pir_pcb_h,pir_under_height+eps]);
      }
      for(x=[-pir_hole_pitch/2,pir_hole_pitch/2]) {
        translate([x,0,pir_pcb_z-eps]) cylinder(d=pir_pcb_hole_d,h=pir_pcb_t+2*eps);
        translate([x,0,pir_pcb_z+pir_pcb_t]) cylinder(d=pir_post_clearance_d,h=pir_under_height+eps);
      }
    }
}
module power_dummy() {
    translate([ow-143,power_y,power_z]) cube([80,50,17]);
}
module usb_dummy() {
    // Platzreserve fuer die Panelkupplung. Nur Ausschnitt und Lochabstand bestaetigt.
    difference() {
        union() {
            translate([0,usb_y-(usb_open_parallel-0.4)/2,usb_z-(usb_open_depth-0.4)/2])
                cube([wall_t+eps,usb_open_parallel-0.4,usb_open_depth-0.4]);
            translate([wall_t,usb_y-usb_flange_w/2,usb_z-usb_flange_h/2])
                cube([usb_flange_t,usb_flange_w,usb_flange_h]);
            translate([wall_t+usb_flange_t-eps,usb_y-usb_open_parallel/2,usb_z-usb_open_depth/2])
                cube([usb_body_l-usb_flange_t+eps,usb_open_parallel,usb_open_depth]);
        }
        for(y=[usb_y-usb_pitch/2,usb_y+usb_pitch/2])
            translate([-eps,y,usb_z]) rotate([0,90,0]) cylinder(d=3,h=wall_t+usb_flange_t+2*eps);
    }
}
// X rechts + Y oben verlangt die Wand auf der negativen Z-Seite.
// Einzelteile und Gesamtansicht erhalten dieselbe Haendigkeit.
scale([1,1,raw_coordinates ? 1 : -1]) {
if(part=="assembly") {
    for(q=[0:1]) color("Gainsboro") if(seam_features) half_cut(q) front(); else if(q==0) front();
    for(q=[0:1]) color([0.52,0.58,0.64]) translate([0,0,exploded]) if(seam_features) half_cut(q) rear(); else if(q==0) rear();
    if(show_joins) {
        if(seam_features) {
        color("SteelBlue") place_keys(true);
        color("SteelBlue") translate([0,0,exploded]) place_keys(false);
        }
        for(p=retainer_points) color("SteelBlue") translate([p[0],p[1],pressure_cap_z(p[1])+exploded]) pressure_cap();
    }
    if(show_components) {
        color([0.16,0.18,0.20]) monitor_dummy();
        color("SeaGreen") translate([0,0,exploded]) pi_dummy();
        color("Ivory") translate([0,0,exploded]) pir_dummy();
        color("DimGray") usb_dummy();
    }
    if(show_keepouts) {
        color([0.1,0.6,0.3,0.25]) translate([pi_x-5,pi_y-24,pi_front_z]) cube([pi_w+29,pi_h+32,pi_component_envelope]);
        color([0.9,0.6,0.2,0.25]) power_dummy();
    }
} else if(part=="front") half_cut(half) front();
else if(part=="rear") half_cut(half) rear();
else if(part=="front_key") glue_key(true);
else if(part=="rear_key") glue_key(false);
else if(part=="pressure_cap") pressure_cap();
else if(part=="monitor_dummy") monitor_dummy();
else if(part=="pi_dummy") pi_dummy();
else if(part=="pir_dummy") pir_dummy();
else if(part=="power_dummy") power_dummy();
else if(part=="usb_dummy") usb_dummy();
else if(part=="layout") echo("LAYOUT",[ow,oh,total_depth,front_depth],
                              front_key_positions,rear_key_positions,
                              [pir_x,pir_y,pir_pcb_z],
                              [for(p=retainer_points) [p[0],p[1],pressure_cap_z(p[1])]],split_gap,
                              closure_points,[key_embed,front_key_w,front_key_h,front_key_waist,key_taper]);
else assert(false,"Unbekanntes Bauteil");
}
