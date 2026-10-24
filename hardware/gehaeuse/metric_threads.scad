/* Metrisches 60-Grad-Profil mit abgeflachten Spitzen/Grund.
   Grundmasse nach TR Fastenings, Metric Coarse (ISO965).
   Druckspiel ist zusaetzlich und keine zertifizierte ISO-Toleranzklasse.
   ACHTUNG: Die Gehaeuse-Pipeline spiegelt ihre Rechenkoordinaten.
   Dieser Rohkoerper ist linksgaengig; SCAD-Ansicht, SKP und Druck-STLs
   sind dadurch RECHTSgaengig. Nicht ungespiegelt fuer andere Projekte nutzen.
*/
module metric_thread(d=10,p=1.5,z0=0,z1=12,radial=0,internal=false,segments=48) {
    H=sqrt(3)*p/2;
    depth=(internal ? 5/8 : 17/24)*H;
    major=d/2+radial;
    root=major-depth;
    crest=p/16;
    base=crest+depth/sqrt(3);
    first=floor(z0/p)-1;
    last=ceil(z1/p)+1;
    n=(last-first)*segments;
    profile=[[root-0.03,-base],[major,-crest],[major,crest],[root-0.03,base]];
    points=[for(i=[0:n]) let(z=(first+i/segments)*p,a=-360*z/p)
            each [for(v=profile) [v[0]*cos(a),v[0]*sin(a),z+v[1]]]];
    // OpenSCAD-Flaechenreihenfolge (von aussen im Uhrzeigersinn).
    faces=concat([[0,1,2,3],[4*n+3,4*n+2,4*n+1,4*n]],
                 [for(i=[0:n-1],j=[0:3]) each
                  [[4*i+j,4*(i+1)+j,4*(i+1)+(j+1)%4],
                   [4*i+j,4*(i+1)+(j+1)%4,4*i+(j+1)%4]]]);
    intersection() {
        union() {
            translate([0,0,z0]) cylinder(r=root,h=z1-z0,$fn=segments);
            polyhedron(points=points,faces=faces,convexity=30);
        }
        translate([-major-1,-major-1,z0]) cube([2*major+2,2*major+2,z1-z0]);
    }
}
