# Bedienung

## Einrichtung personalisieren

Die laufende **Serverversion** steht nach der Anmeldung unten auf jeder Seite
und unter **Einrichtung → Softwareversion**. Sie wird vom NAS-Server übernommen
und zeigt nach einem Update des DSM-Projekts den installierten Stand. Ein neues
GitHub-Release allein aktualisiert die NAS-Anwendung nicht. Die Versionsangabe gilt
für den Server; die Pi-Player werden separat aktualisiert.

Unter **Einrichtung → Namen ändern** den Namen eurer Kita eintragen. Unter **Logo hochladen** ein PNG-, JPEG- oder WebP-Bild auswählen, Vorschau prüfen und **Logo speichern** wählen. Maximal 2 MB, 4 Millionen Bildpunkte, keine Animationen. Das Logo wird ohne Metadaten als PNG auf höchstens 512 × 512 Pixel verkleinert; Transparenz bleibt erhalten.

Das Logo erscheint in der Webverwaltung und bei der Anmeldung. **Beispiel-Logo verwenden** setzt nur das Logo zurück; der Kita-Name bleibt erhalten. Änderungen sind auf angemeldete Administratoren beschränkt. Name und Logo sind vor der Anmeldung sichtbar. Die Gestaltung der Fotos und Meldungen auf den Pi-Bildschirmen bleibt bei den jeweiligen Inhalts- und Geräteeinstellungen.

Die Installation beginnt mit **Gruppe 1**, **Gruppe 2** und **Gruppe 3**. Diese unter **Gruppen & NAS** umbenennen und die tatsächlichen NAS-Ordner eintragen.

Unter **Gruppen & NAS → Gruppe bearbeiten → Gruppenbild (Icon)** kann jede Gruppe
ein eigenes Bild erhalten. **Eigenes Bild auswählen** zeigt vor dem Speichern eine
Vorschau. Erlaubt sind PNG, JPEG und WebP bis 2 MB und 4 Millionen Bildpunkte;
Transparenz bleibt erhalten, große Bilder werden auf höchstens 256 × 256 Pixel
verkleinert. Das Icon erscheint auf der Gruppenkarte in der Verwaltung.

**Bild entfernen** stellt nach dem Speichern das Standardsymbol wieder her.
**Änderung verwerfen** setzt die Bildauswahl zurück; **Abbrechen** verwirft alle
noch nicht gespeicherten Gruppenänderungen. Gruppenangaben und Icon werden
gemeinsam gespeichert. Die Bilder gehören zur Datenbanksicherung und werden
nicht in den NAS-Fotoordner oder die Diashow übernommen.

## Der normale Kita-Alltag

1. Fotos in den jeweiligen NAS-Gruppenordner kopieren.
2. Der Server gleicht die Ordner normalerweise alle 60 Sekunden ab.
3. Der zugeordnete Pi fragt die Zentrale alle 15 Sekunden ab und lädt neue vorbereitete Bilder.
4. Nach vollständigem Download ersetzt er seine lokale Konfiguration und entfernt veraltete Bilddateien.

Nur neue oder geänderte Dateien werden erneut eingelesen: Der Server erkennt unveränderte Dateien am Zeitstempel, an der Größe und an einer kurzen Inhaltsprobe. Bei großen Sammlungen kann deshalb vor allem der erste Abgleich länger dauern. Jeder Gruppenordner erhält einen eigenen Scanstatus. Existiert der Ordner, ist lesbar und leer, gilt das als beabsichtigtes Leeren. Fehlt der Ordner, fehlt der NAS-Marker oder ist eine Datei beschädigt, bleibt der letzte erfolgreiche Gruppenstand bestehen und die Verwaltung zeigt einen Fehler.

Dateien möglichst erst vollständig auf das NAS kopieren und dann in den angezeigten Ordner verschieben. Versteckte Dateien, Synology-Metadatenordner wie `@eaDir` und Symlinks werden ignoriert. Unterstützt: JPG/JPEG, PNG, WebP, BMP. HEIC vorab konvertieren.

## Anzeige wechseln

**Bilderrahmen → Anzeige wechseln** bietet einzelne Geräte, eine Gruppe oder alle aktuell registrierten Geräte als Ziel. Wähle Fotos, Dokument, Meldungen oder Gemischt. Ein optionales Ende gibt danach an die Automatik zurück. Ohne Ende bleibt der manuelle Modus bestehen, bis du **Automatisch** wählst. Bei „Dokument“ wird das unter Hauptanzeige · Standardinhalt ausgewählte Dokument verwendet, sonst die gemeinsame Dokumentenliste.

Ein Gruppen-/Alle-Wechsel wird auf die aktuellen Geräte angewendet. Später hinzugefügte Geräte starten mit ihrer eigenen Standardanzeige. Neue Rahmen übernehmen die zentralen Betriebszeiten.

**Anzeigebereich** legt fest, ob die Hauptanzeige oder die zusätzliche Anzeige
umgeschaltet wird. Standard ist die Hauptanzeige. Bei „Dokument“ gilt die
Dokumentauswahl des jeweiligen Bereichs. Zusatz-Umschaltungen werden nur auf
Rahmen mit aktivierter Bildschirmteilung angewendet. Inhaltszeitfenster werden direkt am Rahmen für den gewünschten Bereich eingerichtet.

## Zentrale Betriebszeiten

Unter **Betriebszeiten → Betriebszeiten bearbeiten** festlegen, wann die Rahmen
anzeigen dürfen. Der zentrale Standard gilt für alle Rahmen ohne eigene
Betriebszeiten und auch für künftig angelegte Rahmen.

- **Betriebszeiten begrenzen** ausgeschaltet: rund um die Uhr freigegeben.
- Eingeschaltet: Nur die eingetragenen Wochentage und Uhrzeiten sind freigegeben.
- Eingeschaltet und keine Zeitfenster: durchgehend Ruhezeit.
- Überlappende Zeitfenster werden zusammengefasst. Gleiche Start-/Endzeit gilt
  ganztägig; ein Ende vor dem Start reicht bis zum Folgetag.

Betriebszeiten betreffen immer Haupt- und Zusatzanzeige gemeinsam. Außerhalb
wählt der Pi **HDMI abschalten** oder **Schwarzes Bild** entsprechend der
Rahmeneinstellung unter **Bewegungssensor & Energiesparen**. Dies gilt auch ohne
aktivierten Bewegungssensor. Der Pi bleibt erreichbar und synchronisiert weiter.
**Sofortmeldungen haben Vorrang** und können die Anzeige auch während der Ruhezeit wecken.

## Bilderrahmen verwalten

Unter **Bilderrahmen** steht die **Verbindungs-IP** eines Geräts direkt unter
dem Verbindungsstatus. Die Zentrale erfasst sie beim nächsten Abgleich; dafür
ist kein Player-Update nötig. Die Adresse ist die vom Server gesehene Quell-IP.
Bei einem Reverse Proxy oder NAT kann dort eine Zwischenadresse statt der
direkt per SSH erreichbaren Pi-Adresse stehen.

1. **Standort & Freigaben:** Name, Gruppe und Zulassung interner Inhalte.
2. **Hauptanzeige · Standardinhalt:** Fotos, Dokument oder gemeinsame Liste, Meldungen oder Gemischt.
3. **Bildschirm teilen:** Aufteilung, Hauptseite, Vorschau und Standardinhalt des Zusatzbereichs.
4. **Betriebszeiten:** Zentralen Standard verwenden oder **Eigene Betriebszeiten für diesen Rahmen verwenden** aktivieren. Eigene Zeiten ersetzen den zentralen Standard vollständig. Den Haken entfernen, um wieder allen zentralen Änderungen zu folgen.
5. **Inhaltszeitfenster:** **Inhalte zeitabhängig wechseln** aktivieren und Bereich, Wochentage, Uhrzeit und Inhalt wählen. Bei Überschneidungen gewinnt pro Bereich das oberste Fenster; mit ↑ / ↓ verschieben.
6. **Bild & Darstellung:** Ausrichtung, Bildausschnitt, Fotoreihenfolge und Übergänge.
7. **Bewegungssensor & Energiesparen:** Sensor, Nachlaufzeit, Abschaltung und Live-Diagnose.
8. **Gerät & Wartung:** Vorschau, Abgleich, Neustart und Kopplung.

Inhaltszeitfenster steuern **ausschließlich die Inhalte**. Sie öffnen und
verlängern keine Betriebszeiten. Ohne passendes Fenster oder bei ausgeschaltetem
**Inhalte zeitabhängig wechseln** gilt der Standardinhalt des jeweiligen Bereichs.
Die Auswahl **Standardinhalt dieses Bereichs** im obersten Fenster verwendet ebenfalls
den Standard und ignoriert darunterliegende Fenster.

Beispiel: Zentrale Betriebszeiten Mo–Fr 07:00–18:00. Hauptanzeige standardmäßig
Fotos, Zusatzanzeige Meldungen. Ein Inhaltszeitfenster für die Zusatzanzeige zeigt
11:00–13:00 den Speiseplan. Danach laufen dort wieder Meldungen; um 18:00 ruht der
ganze Bildschirm. Ein Rahmen im Personalraum kann eigene Betriebszeiten bis
20:00 erhalten, ohne die anderen Rahmen zu ändern.

Betriebszeiten und Inhaltszeitfenster haben jeweils eine angegebene Zeitzone.
Sommer-/Winterzeit wird berücksichtigt. Die gespeicherten Zeiten funktionieren
automatisch offline; neue Einstellungen kommen beim nächsten erfolgreichen
Abgleich an.

### Zwei Inhalte gleichzeitig anzeigen

Unter **Bildschirm teilen → Zwei Inhalte gleichzeitig anzeigen** die Teilung
einschalten. **Automatisch nach Ausrichtung** verwendet bei Querformat zwei
Bereiche nebeneinander, bei Hochformat zwei Bereiche untereinander. Unter
**Bild & Darstellung → Ausrichtung** wird das Format gewählt. Nebeneinander
oder untereinander lässt sich auch ausdrücklich festlegen.

Unter **Größe der zusätzlichen Anzeige** stehen **33 %**, **40 %** und **50 %**
zur Wahl. Die Hauptanzeige nutzt den übrigen Platz. Die Größe der zusätzlichen
Anzeige bleibt beim Wechsel der Seite gleich. **Hauptanzeige (Default)** legt
fest, ob die Hauptanzeige links/oben oder rechts/unten liegt. Die andere Seite erhält
einen eigenen Standardinhalt, Bildwechsel und bei Bedarf eine gemischte Liste.
Beide Bereiche wechseln ihre Bilder, Dokumentseiten und Meldungen unabhängig voneinander.

Die Vorschau im Editor zeigt unmittelbar die Aufteilung. Nach dem Speichern
zeigt **Vorschau** die aktuell vorgesehenen Inhalte beider Bereiche mit
unabhängigen Seitenwechseln und Vor-/Zurück-Schaltflächen. Das ist eine
inhaltliche Vorschau; Schriftgrößen und Übergänge können am Pi abweichen.

Beispiel: Hauptanzeige links mit Fotos, Zusatzanzeige rechts mit Meldungen.
Ein Zusatz-Zeitfenster von 11:00 bis 13:00 zeigt dort stattdessen den Speiseplan.
Danach erscheinen wieder Meldungen. Gibt es im Zusatzbereich keine aktuellen,
freigegebenen Inhalte, nutzt die Hauptanzeige automatisch den ganzen Bildschirm.

Sofortmeldungen erscheinen immer im Vollbild. Bewegungssensor und Abschaltung
gelten gemeinsam. Die Freigabe **Interne Inhalte** gilt für beide Bereiche;
interne Dokumente und Meldungen gelangen nicht durch die Teilung auf Elternrahmen.
Dokumente in kleinen Bereichen können schwer lesbar sein: Vorschau und Anzeige
am tatsächlichen Standort prüfen.

Die Bildschirmteilung ist standardmäßig ausgeschaltet. Inhaltszeitfenster und
manuelle Umschaltungen können Haupt- oder Zusatzanzeige steuern.

## Prioritäten

| Vorrang | Einstellung | Verhalten |
|---|---|---|
| 1 | Aktive Sofortmeldung | Immer Vollbild, auch außerhalb der Betriebszeiten und bei Bewegungspause. |
| 2 | Betriebszeiten und Bewegungspause | Gemeinsame Ruhezeit für den gesamten Bildschirm. |
| 3 | Manuell gewählter Modus | Innerhalb der Betriebszeiten bis zum Ende oder bis „Automatisch“. |
| 4 | Inhaltszeitfenster | Das oberste passende Fenster pro Bereich bestimmt den Inhalt. |
| 5 | Standardinhalt | Gilt ohne passendes Fenster oder bei deaktivierten Inhaltszeitfenstern. |

Zeitfenster gelten am Start einschließlich, am Ende ausschließlich. 22:00–02:00
gehört zum Starttag. Eine bei der Zeitumstellung doppelt auftretende Stunde wird
beide Male ausgewertet. Dieselbe Logik läuft auf Server und Pi. Ohne Zusatzinhalt
entfällt die Teilung automatisch.

## Optional: Bewegung im Raum

Unter **Bilderrahmen → Verwalten → Bewegungssensor & Energiesparen** lässt sich je Rahmen ein
HC-SR501 aktivieren. Nachlaufzeit ohne Bewegung (1–240 Minuten, Standard 5) und
**HDMI abschalten** oder **Schwarzes Bild** einstellen. Ohne Sensor die Funktion
ausgeschaltet lassen. Anschluss und Prüfung: [Bewegungssensor](BEWEGUNGSSENSOR.md).
**Sensor live prüfen** zeigt
das Sensorsignal, den Nachlauf und GPIO-/HDMI-Fehler etwa jede Sekunde. Bei
laufender Diagnose bleibt das Fenster nach **Einstellungen übernehmen** geöffnet.

Innerhalb der Betriebszeiten pausiert der Pi nach Ablauf der Nachlaufzeit und
zeigt bei Bewegung wieder die aktuellen Inhalte. Außerhalb der Betriebszeiten
bleibt er auch bei Bewegung in der gewählten Abschaltung. **Sofortmeldungen
wecken die Anzeige unabhängig davon.** Nach Aktivierung gibt es 60 Sekunden
Einlaufzeit. Hardware-Haltezeit des Sensors und Monitor-Aufwachzeit kommen hinzu.

Die lokale Bewegungspause übersteuert die normale Inhaltsauswahl, aber nicht
die Sofortmeldungen. Sie wird unter **Gemeldet** als **Ruhemodus** mit dem Grund
**Keine Bewegung erkannt** sichtbar.
Die Zentrale berechnet weiterhin die vorgesehenen Inhalte; ihre Vorschau ist
keine Live-Anzeige des Sensors. Der Pi synchronisiert auch während der Pause.

## Meldung erstellen

**Inhalte → Meldung erstellen**. Vorlage auswählen oder Text selbst schreiben, Zielgruppe und Farbstil wählen. Optional zuerst ein Meldungsbild hochladen und dann auswählen. Die Vorschau zeigt den Inhalt vor der Veröffentlichung. Kurze Texte sind im Vorraum besser lesbar; lange Texte verkleinert der Player.

„Sofortmeldung“ nur für Inhalte verwenden, die tatsächlich alle anderen Modi unterbrechen sollen. Ein Ende setzen, wenn die Information automatisch verschwinden soll. Nach Ablauf greift die übrige Prioritätslogik. „Meldung beenden und entfernen“ entfernt sie nach dem nächsten erfolgreichen Geräteabgleich.

„Intern“ gekennzeichnete Meldungen werden **gar nicht** an Geräte ohne interne Freigabe ausgeliefert, auch wenn als Ziel „Alle“ gewählt ist. Elternanzeigen bleiben ohne interne Freigabe.

## Dokumente: Speiseplan, Dienstplan oder Elterninformation

**Inhalte → Dokument (PDF) hochladen** akzeptiert PDF oder Bild. Bereits beim
Upload lassen sich **Art** und **interne Verwendung** festlegen. Unter
**Inhalte → Bearbeiten** können Name, Art und Freigabe später geändert werden;
die Datei, ihre Seiten und bestehenden Verweise bleiben erhalten. Für die Art
gibt es Vorschläge wie Speiseplan oder Elterninformation; eigene Bezeichnungen
sind ebenfalls möglich. Meldungsbilder behalten ihre Verwendung in Meldungen.
Eine Änderung nur an Name oder Art behält bestehende Gruppenfreigaben. Wenn die
Elternfreigabe auf **nur intern** umgestellt wird, werden diese Freigaben entzogen.

Die Vorschau zeigt alle vorbereiteten Seiten. Das Dokument anschließend direkt
in der Standardanzeige, einem Inhaltszeitfenster oder einem
Eintrag der gemischten Wiedergabe auswählen. Alternativ die **Gemeinsame Dokumentenliste** verwenden.

- Neue Dokumente sind standardmäßig für Elternanzeigen freigegeben. Für interne Dokumente unter **Bearbeiten** den Haken **Dieses Dokument ist nur für interne Zwecke** setzen.
- Die Freigabe erlaubt die Anzeige, fügt das Dokument aber nicht automatisch einer Wiedergabeliste hinzu.
- Dokumente bleiben unabhängig von ihrer Listenaufnahme direkt auswählbar.

### Gemeinsame Dokumentenliste

Unter **Inhalte → Dokumentenliste** für jedes Dokument wählen:

- **Alle Gruppen:** gilt auch für künftig angelegte Gruppen.
- **Ausgewählte Gruppen:** eine oder mehrere Gruppen anhaken.
- **Keine:** entfernt das Dokument aus der gemeinsamen Liste, ohne die Datei oder direkte Auswahlen zu löschen.

Beliebig viele Dokumente können gleichzeitig aufgenommen werden; eine Aufnahme
ersetzt keine andere. Die Liste läuft nach Dateinamen, bei gleichem Namen nach
fester ID. Alle Seiten eines Dokuments werden nacheinander gezeigt. Interne
Dokumente werden nur für entsprechend freigegebene Rahmen ausgeliefert.

Am Rahmen unter **Dokument** oder in einem **Gemischt**-Eintrag die Quelle
**Gemeinsame Dokumentenliste** wählen. Das gilt für Haupt- und Zusatzanzeige
sowie deren Inhaltszeitfenster. Beispiel im Zusatzbereich: **Meldungen**
und **Dokument → Gemeinsame Dokumentenliste**. Neue Listenaufnahmen erreichen
alle passenden Rahmen beim nächsten Abgleich, ohne deren Einstellungen zu ändern.
Eine leere Liste wird übersprungen; ein vollständig leerer Zusatzbereich entfällt.
Der Pi speichert die erlaubten Seiten auch für den Offlinebetrieb.

Dokumente werden zentral unter **Inhalte** hochgeladen und verwaltet. Unter
**Gruppen & NAS** werden Gruppenname, Gruppenbild und NAS-Fotoordner eingerichtet.

### Dokument löschen

**Inhalte → Entfernen** zeigt vor dem Löschen alle betroffenen Gruppen,
Meldungen, Standardanzeigen, Inhaltszeitfenster und gemischten Listen. Bei bestehenden Verwendungen zuerst **Alle oben genannten Zuordnungen
lösen und dieses Dokument löschen** anhaken und dann **Zuordnungen lösen und
löschen** wählen. Dokument und Verweise werden gemeinsam gespeichert oder bei
einem Fehler vollständig unverändert gelassen. Ändern sich die Verwendungen
nach dem Öffnen des Fensters, muss der Löschdialog erneut geöffnet werden.

Direkte Dokumentanzeigen wechseln dabei zu Fotos. Betroffene Dokumenteinträge
werden aus gemischten Listen entfernt; eine sonst leere Liste erhält einen
Fotoeintrag. Inhaltszeitfenster bleiben erhalten. Eine manuelle Dokumentumschaltung,
die das entfernte Standarddokument verwendet, kehrt zur Automatik zurück.
Meldungen bleiben ohne das entfernte Bild erhalten. Andere Dokumente und Dateien
auf dem NAS werden nicht gelöscht. Die Pis übernehmen die Änderung beim nächsten
Abgleich; offline bleibt ihr letzter Stand bestehen.

PDF-Seiten werden maximal mit 1920 Pixeln an der längsten Kante vorbereitet und vollständig angezeigt. Eine dichte A4-Tabelle kann auf einem 15,6-Zoll-Bildschirm zu klein sein. Für Eltern besser eine kurze, eigens gestaltete Übersicht einsetzen; Lesbarkeit am tatsächlichen Standort prüfen.

## Gemischte Wiedergabe

Unter **Bilderrahmen → Verwalten → Hauptanzeige · Standardinhalt → Gemischte Anzeige zusammenstellen** eine Reihenfolge aus Fotos, Dokumenten und Meldungen anlegen und mit ↑ / ↓ ändern. Jeder Dokumenteintrag kann eine eigene Datei oder die gemeinsame Dokumentenliste verwenden. Die Dauer gilt für jeden Inhalt dieses Eintrags. Beispiel: „Fotos 12 s, Meldungen 20 s“ zeigt zuerst alle Fotos je 12 Sekunden und anschließend alle aktiven Meldungen je 20 Sekunden. Mehrere Einträge derselben Art sind möglich. Leere Inhaltsarten werden übersprungen; ist alles leer, erscheint die neutrale Begrüßung.

## Status und Fernverwaltung

- **Verbunden:** Rückmeldung innerhalb der letzten 90 Sekunden.
- **Soll-Anzeige:** Berechnung der Zentrale; zeigt auch, welche Einstellung Vorrang hat.
- **Gemeldet:** Modus der letzten Pi-Rückmeldung, bei Offline-Geräten naturgemäß veraltet.
- **Letzter Abgleich:** letzter erfolgreicher Konfigurations-/Inhaltsabgleich des Pi.
- **NAS-Status:** gesondert bei jeder Gruppe, einschließlich des letzten erfolgreichen Quellscans.
- **Vorschau:** berechtigte Soll-Inhalte, kein Bildschirmfoto des laufenden Pi; genaue Schriftgrößen und Übergänge können abweichen.
- **Abgleichen:** NAS-Scan auslösen und einen Gerätebefehl bereitstellen.
- **Player neu starten:** startet die Anzeige-Anwendung neu, nicht das Betriebssystem.

Ein Befehl wartet höchstens 24 Stunden auf das Gerät. Bereits quittierte Neustarts werden auf dem Pi dauerhaft gespeichert, damit eine erneute Zustellung keine Neustartschleife auslöst.
