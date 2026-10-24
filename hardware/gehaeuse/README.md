# Monitor-Wandgehäuse

Das Gehäuse ist für einen Monitor mit 355,4 × 221 mm, einen Raspberry Pi 3 A+
und einen PIR-Sensor ausgelegt. Pi und PIR sitzen am abnehmbaren Deckel; eine
USB-C-Panelbuchse wird seitlich befestigt. Alle Maße sind in Millimetern.

Die Konstruktions- und Druckdateien stehen unter
[AGPL-3.0-only](../../LICENSE). Den Geltungsbereich beschreibt der
[Projekthinweis](../../NOTICE).

## 3D-Dateien

- [OpenSCAD-Quelle](gehaeuse.scad) mit benötigter
  [Gewindebibliothek](metric_threads.scad)
- [SketchUp-Modell, geteilt](gehaeuse_geteilt.skp): Druckteile als einzelne
  Gruppen mit Bauteilreferenzen
- [SketchUp-Modell, komplett](gehaeuse_komplett.skp): durchgehende Front und
  Rückseite zum eigenen Teilen
- Druckfertige STL-Dateien im Ordner [stl_geteilt/](stl_geteilt/)
- Ungeteilte STL-Schalen im Ordner [stl_komplett/](stl_komplett/)

Die SketchUp-Modelle haben für jede Gruppe einen eigenen Tag. Die Tags sind
in den Ordnern **Gehäuse** (Front und Rückseite), **Halter** (Andruckteller),
**Anbauteile** (Klebekeile) und **Referenzen** (Monitor, Pi, PIR, USB-C)
organisiert. So lassen sich ganze Kategorien oder einzelne Teile ausblenden.
Nach einem erneuten SketchUp-Export weist das
[Tag-Werkzeug](../../tools/tag_gehaeuse_sketchup.py) die Tags wieder zu:

```text
python tools/tag_gehaeuse_sketchup.py
```

SketchUp-Gruppen mit `REFERENZ_` sind Platzhalter und werden nicht gedruckt.
Die ungeteilten Schalen sind größer als das Druckbett des Bambu Lab P1S; vor
dem Druck müssen sie geteilt und mit einer passenden Verbindung versehen werden.
Die geteilten STL-Dateien enthalten die dafür vorgesehenen Klebekeile.

## Druckteile für das geteilte Gehäuse

| Datei | Anzahl |
|---|---:|
| [Front_1.stl](stl_geteilt/Front_1.stl), [Front_2.stl](stl_geteilt/Front_2.stl) | je 1 |
| [Rueckseite_1.stl](stl_geteilt/Rueckseite_1.stl), [Rueckseite_2.stl](stl_geteilt/Rueckseite_2.stl) | je 1 |
| [Klebekeil_Front.stl](stl_geteilt/Klebekeil_Front.stl) | 4 |
| [Klebekeil_Deckel.stl](stl_geteilt/Klebekeil_Deckel.stl) | 3 |
| [Andruckteller_M10.stl](stl_geteilt/Andruckteller_M10.stl) | 4 |

Ein großes Teil pro Druckplatte bei 100 % Maßstab drucken und die
STL-Ausrichtung beibehalten. Die Keile mit Klebeflächen und Abstandspunkten
nach oben, die Teller mit der breiten Monitorseite auf dem Druckbett platzieren.
Die 0,2-mm-Abstandspunkte der Keile in der Schichtvorschau kontrollieren.
Gewinde mit 0,12–0,16 mm Schichthöhe und Teller massiv drucken. Drucklage,
Stützen und Haftung vor dem Druck im Slicer prüfen.

## Montage

1. Die Maße der realen Bauteile prüfen. Das Gehäuse misst außen
   424,6 × 248,2 × 36 mm ohne Linse, Stecker und Schraubenköpfe.
2. Die zwei Fronthälften mit vier Klebekeilen und die zwei Deckelhälften mit
   drei Klebekeilen ausrichten, dauerhaft verkleben und aushärten lassen.
3. Gewindeeinsätze und weiche Polster montieren, USB-C-Kupplung befestigen
   und den Monitor einlegen. Führungen und Polster dürfen nur auf dem
   Monitorgehäuse aufliegen, nicht auf der Bildfläche.
4. Pi und PIR am Deckel befestigen. Kabel mit einer spannungsfreien
   Serviceschlaufe führen. Die vier M10 × 1,5-Andruckteller von der
   Monitorseite einschrauben, weich polstern und von Hand auf leichten,
   gleichmäßigen Kontakt einstellen. Den Monitor nicht verspannen.
5. Deckel aufsetzen und mit sechs M3 × 8-Senkkopfschrauben von hinten
   schließen. Das geschlossene Gehäuse über die zwei vorderen Senkbohrungen
   mit zur Wand passenden Schrauben befestigen.

Die Seitenverschraubungen des Deckels liegen 124,1 mm über der Unterkante
und jeweils 8 mm von der Außenkante entfernt. Die Wandbohrungen liegen
404,6 mm auseinander und 10 mm unter der Oberkante.

Die CAD-Dateien beschreiben die mechanische Konstruktion. Die interne
elektrische Stromverteilung ist darin nicht enthalten.
