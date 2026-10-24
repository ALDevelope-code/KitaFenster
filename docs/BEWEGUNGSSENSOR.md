# Optionaler Bewegungssensor HC-SR501

Jeder Pi kann einen eigenen HC-SR501 bekommen. Die Einstellungen gelten je
**Bilderrahmen**, beispielsweise für den jeweiligen Raum. Ohne aktivierte
Sensorfunktion richtet sich die Anzeige nach Betriebszeiten und Inhaltsauswahl;
ein Sensor ist nicht erforderlich.

Ein PIR erkennt Bewegung anhand wechselnder Wärmestrahlung. Er erkennt nicht
zuverlässig, ob jemand still im Raum sitzt. Die Nachlaufzeit deshalb für den
Raum ausreichend lang wählen. Das Modul bietet einstellbare Empfindlichkeit
und Haltezeit. [HC-SR501 von Joy-IT](https://joy-it.net/en/products/SEN-HC-SR501).

## 1. Am ausgeschalteten Pi anschließen

`sudo poweroff` ausführen, das Herunterfahren abwarten und den Pi vom Strom
trennen. Drei Jumperkabel mit Buchsen verbinden den Sensor mit der GPIO-Leiste
des Pi 3 A+. **Die Beschriftung auf der Sensorplatine beachten**; die Reihenfolge
der Sensorpins kann je nach Ausführung und Blickrichtung unterschiedlich sein.

| Anschluss am HC-SR501 | Physischer Pin am Pi | Funktion |
|---|---:|---|
| VCC / + | **2** | 5 V Versorgung |
| GND / − | **6** | Masse |
| OUT / DATA | **11** | GPIO17, Eingang für das Bewegungssignal |

Die Nummern 2, 6 und 11 bezeichnen die **Positionen auf der Steckerleiste**.
GPIO17 ist die BCM-Bezeichnung von Pin 11, nicht Pin 17. Pin 1 anhand der
Platinenmarkierung bzw. der offiziellen Pinbelegung bestimmen; nicht vom
USB-Anschluss aus raten. [Raspberry-Pi-GPIO und Pinbelegung](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#gpio).

**5 V gehören ausschließlich an VCC, niemals an GPIO17.** Der GPIO-Eingang
verträgt höchstens 3,3 V. Der HC-SR501 liefert trotz seiner 5-V-Versorgung ein
Signal von etwa 3–3,3 V; bei einem abweichenden Sensormodul dessen Datenblatt
prüfen. [Sensor-Spezifikation](https://joy-it.net/en/products/SEN-HC-SR501),
[GPIO-Spannungsgrenzen](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#gpio).

Am Sensor den Jumper, sofern vorhanden, auf **H / wiederholte Auslösung** setzen.
Die Hardware-Haltezeit zunächst kurz einstellen, die Empfindlichkeit für den
Raum anpassen. Die Potentiometer nach der Anleitung des eigenen Moduls zuordnen;
eine allgemeine Links-/Rechts-Regel ist nicht verlässlich.
[Modulanleitung](https://joy-it.net/files/files/Produkte/SEN-HC-SR501/SEN-HC-SR501_Anleitung_2024-04-16.pdf).

Den Sensor fest und mit freier Sicht in den Raum montieren. Direkte Sonne,
Heizkörper und bewegte warme Luft im Blickfeld möglichst vermeiden. Kabel und
Platine geschützt und außerhalb der Reichweite der Kinder befestigen. Danach
Monitor und Pi wieder einschalten.

## 2. Software vorbereiten

NAS und Pi nach der [Installationsanleitung](INSTALLATION-PI.md) einrichten.
Der Pi-Installer installiert `python3-gpiozero`, `python3-lgpio` und `libdrm2`
und gibt dem Konto `frame` Zugriff über die Gruppe `gpio`. Es ist keine
zusätzliche Sensorinstallation erforderlich.

Der Dienst verwendet `/run/kita-player` als beschreibbares Arbeitsverzeichnis
für die temporären GPIO-Dateien. systemd legt es beim Start für `frame` an;
die Programmdateien werden über `PYTHONPATH=/opt/kita-frame` geladen.
Der Player läuft als `frame`. Kein zusätzlicher Dienst und kein
NAS-Freigabepasswort sind für den Sensor erforderlich.

## 3. Je Raum einstellen

Auf der Webseite **Bilderrahmen → Verwalten → Bewegungssensor & Energiesparen** öffnen:

| Einstellung | Bedeutung |
|---|---|
| Bewegungssensor verwenden | Einschalten, wenn der Sensor angeschlossen und geprüft ist. Standard: aus. |
| Nachlaufzeit ohne Bewegung | 1 bis 240 Minuten; Standard: 5 Minuten. Jede erkannte Bewegung verlängert die Zeit. |
| HDMI abschalten · Monitor-Standby | Der Pi schaltet sein HDMI-Bildsignal ab und bei Bewegung wieder ein. |
| Schwarzes Bild · Beleuchtung bleibt an | Alternative, wenn der Monitor mit HDMI-Standby Probleme hat; spart keine verlässliche Monitorleistung. |

**Einstellungen speichern** wählen. Bei bestehender Verbindung übernimmt der Pi die Änderung
normalerweise beim nächsten Abgleich innerhalb von 15 Sekunden. Nach Start oder
Aktivierung hat der Sensor 60 Sekunden Einlaufzeit. Innerhalb der Betriebszeiten
bleibt die Anzeige währenddessen aktiv; anschließend beginnt die Nachlaufzeit.

Die Software zählt ab dem letzten aktiven Sensorsignal. Hält das Modul seinen
Ausgang nach einer Bewegung noch auf HIGH, läuft diese Hardware-Haltezeit
zusätzlich zur eingestellten Nachlaufzeit. Zum Testen daher die Hardware-Haltezeit
kurz einstellen.

### Live-Diagnose und Einstellhilfe

Unter **Bilderrahmen → Verwalten → Bewegungssensor & Energiesparen → Sensor live prüfen**
auf **Live-Diagnose starten** klicken. Der Pi beginnt beim nächsten Abgleich
(normalerweise innerhalb von 15 Sekunden) mit der schnellen Übertragung.
Anschließend aktualisiert sich die Anzeige ungefähr jede Sekunde; Netzwerk
und größere Inhaltsdownloads können sie verzögern. Mehr als fünf Sekunden alte
Messwerte werden ausdrücklich als veraltet angezeigt.

Die Diagnose zeigt:

- **HIGH / LOW / Unbekannt** am GPIO17 (physischer Pin 11), auch während der
  Einlaufzeit. Unbekannt bedeutet: deaktiviert oder nicht lesbar, nicht LOW.
- Dauer der aktuell beobachteten Signalphase und die letzten 20 Beobachtungen.
  Erstbeobachtungen nach Start oder einem Lesefehler sind als solche markiert.
- Einlaufzeit, verbleibende Software-Nachlaufzeit und Vorrang einer Sofortmeldung.
- Tatsächlich am Pi verwendete Einstellungen; noch nicht übernommene Änderungen
  werden gekennzeichnet. **Einstellungen übernehmen** speichert die Eingaben.
  Während einer laufenden Diagnose bleibt das Fenster danach geöffnet.
- Ausgabe des Players: Bildsignal an, HDMI abgeschaltet oder Schwarzbild.
  GPIO- und HDMI-Fehler enthalten zusätzlich die technische Fehlermeldung.

Die Live-Diagnose verändert keine Sensor- oder Anzeigeeinstellungen. Die
Sensorfunktion muss ausdrücklich aktiviert und gespeichert sein, damit der
Player den Eingang liest. Es wird kein zweiter GPIO-Leser geöffnet; das
Konsolen-Testprogramm deshalb nicht gleichzeitig starten.

**Zum Einstellen:** Hardware-Haltezeit TIME möglichst kurz, Empfindlichkeit SENS
zunächst mittig und Jumper auf H wählen. Zuordnung und Drehrichtung anhand der
eigenen Modulanleitung prüfen. Software-Nachlaufzeit vorübergehend auf eine
Minute stellen und übernehmen. Einlaufzeit abwarten, im gewünschten Bereich
gehen und auf HIGH achten. Danach den Bereich verlassen: Auf LOW muss der
Countdown und anschließend die Abschaltung folgen. Den Monitor vor Ort prüfen.

**Wenn der Bildschirm dauerhaft anbleibt:**

| Live-Anzeige | Bedeutung / Prüfung |
|---|---|
| Keine Messwerte | Pi-Verbindung, aktuellen Geräteabgleich und Dienstprotokoll prüfen. |
| Sensorfunktion am Pi ausgeschaltet | Oben aktivieren und übernehmen; bei ausstehender Übernahme nächsten Abgleich prüfen. |
| Sensor nicht lesbar | Die Software lässt die Anzeige innerhalb der Betriebszeiten aktiv. Konkreten Fehler, GPIO17, Installation und gpio-Rechte prüfen. |
| Dauerhaft HIGH | Hardware-Haltezeit oder weitere Auslösungen halten das Signal aktiv. TIME verkürzen; Empfindlichkeit, Position und Wärmequellen prüfen. |
| LOW, Nachlaufzeit läuft | Ablauf abwarten oder Nachlaufzeit zum Test auf eine Minute verkürzen. |
| Sofortmeldung | Diese hält die Anzeige unabhängig vom Sensor aktiv. |
| Schwarzbild | Die Beleuchtung kann anbleiben. Gewählte Abschaltung und möglichen HDMI-Fehler prüfen. |
| HDMI abgeschaltet, Monitor bleibt beleuchtet | Die Software hat abgeschaltet; Standby-Verhalten und Einstellungen des Monitors vor Ort prüfen. |

Ein dauerhaftes LOW beweist keinen intakten Anschluss: Auch ein abgezogener
Sensor kann LOW liefern. HIGH bedeutet nicht zwingend eine neue Bewegung.
Die Signalphasen sind keine Personenzählung und erlauben bei wiederholten
Auslösungen keine eindeutige Messung der Poti-Haltezeit. Potistellungen,
Entfernung und Bewegungsstärke sind nicht auslesbar.

**Live-Diagnose beenden** oder das Fenster schließen beendet die Ansicht. Die
schnelle Übertragung endet spätestens 30 Sekunden nach der letzten Erneuerung
durch eine Diagnoseansicht. Andere offene Diagnoseansichten können sie weiter
aktiv halten. Die letzten 20 Signalbeobachtungen liegen nur im Arbeitsspeicher
des Players; der Server hält Messwerte nur während der aktiven Diagnose im
Arbeitsspeicher. Es entsteht keine dauerhafte Bewegungshistorie. Der reguläre
Inhaltsabgleich und der Offlinebetrieb bleiben bestehen.

## Verhalten im Alltag

- **Bewegung innerhalb der Betriebszeiten:** Die aktuellen Inhalte erscheinen.
- **Keine Bewegung bis zum Ablauf:** Die gewählte Abschaltung wird aktiv.
  Der Pi läuft weiter, bleibt online und synchronisiert seine Inhalte.
- **Außerhalb der Betriebszeiten:** Die gewählte Abschaltung gilt unabhängig von
  Bewegung, auch bei ausgeschalteter Sensorfunktion.
- **Sofortmeldung:** Hat Vorrang vor Betriebszeiten und Bewegungspause und weckt
  die Anzeige. Nach ihrem Ende beginnt die Nachlaufzeit erneut.
- **Ohne NAS-Verbindung:** Der Sensor arbeitet mit den zuletzt übernommenen
  Einstellungen weiter. Neue Einstellungen kommen nach der Wiederverbindung an.
- **Sensorfunktion ausgeschaltet:** Der GPIO wird freigegeben. Die Anzeige
  arbeitet wieder ausschließlich nach Betriebszeiten und Inhaltsauswahl.

Unter **Gemeldet** zeigt die Webseite beispielsweise **Ruhemodus** und
**Keine Bewegung erkannt · HDMI aus**. Das ist der letzte gemeldete Softwarezustand,
keine Messung der Monitorbeleuchtung. Die Vorschau zeigt weiterhin die vorgesehenen
Inhalte; sie stellt die aktuelle lokale Bewegungspause nicht nach.

Die HDMI-Schaltung verwendet KMS/DRM direkt im Player. Sie unterbricht das
Bildsignal, nicht die Stromversorgung des Monitors. Ob und wie schnell der Monitor
in Standby geht bzw. aufwacht, hängt vom Gerät ab. Einige zeigen zuerst „Kein
Signal“. [KMS-Anschlusseigenschaften](https://www.kernel.org/doc/html/latest/gpu/drm-kms.html#standard-connector-properties).

## 4. Am echten Gerät testen – auch nach Monitorwechsel

1. Nachlaufzeit vorübergehend auf **1 Minute** stellen und Sensorfunktion
   einschalten. Die 60 Sekunden Einlaufzeit abwarten.
2. Vor dem Sensor bewegen: Bilder müssen sichtbar sein.
3. Den Erfassungsbereich verlassen und Hardware-Haltezeit plus Nachlaufzeit
   abwarten. Die Webseite muss **Ruhemodus** mit dem Grund **Keine Bewegung erkannt** melden; den Bildschirm und
   seine Beleuchtung selbst kontrollieren.
4. Wieder vor dem Sensor bewegen. Das Bild muss nach der Aufwachzeit des Monitors
   zurückkehren. Mindestens drei Einschlaf-/Aufwachvorgänge prüfen.
5. Während einer Pause Inhalte ändern: Nach Bewegung müssen die inzwischen
   synchronisierten Inhalte erscheinen. Auch eine Sofortmeldung testen.
6. Pi neu starten, Betriebszeiten prüfen und den Test wiederholen. Anschließend
   die passende Nachlaufzeit für den Raum einstellen.
7. Die Sensorfunktion ausschalten: Innerhalb der Betriebszeiten muss die Anzeige
   auch ohne Bewegung dauerhaft laufen.

Die Steuerlogik ist automatisiert mit simuliertem GPIO und HDMI geprüft.
**Ein physischer HC-SR501-/HDMI-Standby-Test ist damit nicht ersetzt.** Nach einem
Monitorwechsel diese Prüfung wiederholen; eine neue Kopplung ist nicht nötig.

## Fehler eingrenzen

| Beobachtung | Nächster Schritt |
|---|---|
| Sensor nicht lesbar | Installer und Neustart durchführen; `id frame` muss `gpio` enthalten. GPIO17 darf nicht von einem anderen Programm belegt sein. |
| `xCreatePipe` / `.lgd-nfy` im Protokoll | Beschreibbares Arbeitsverzeichnis für die GPIO-Bibliothek fehlt; siehe Prüfung unten. |
| HDMI-Abschaltung nicht verfügbar | Der Player verwendet Schwarzbild und meldet den Fehler. KMS-Dienst und Monitor prüfen. |
| Monitor wacht nicht zuverlässig auf | In der Webverwaltung die Abschaltung auf **Schwarzes Bild** umstellen. Das gilt für Betriebsruhezeiten und Bewegungspausen. |
| Anzeige geht nie aus | Hardware-Haltezeit, dauerndes HIGH, Einlaufzeit, Nachlaufzeit und aktive Sofortmeldungen prüfen. |
| Anzeige geht trotz Personen aus | Sensorposition/Empfindlichkeit prüfen und Nachlaufzeit verlängern. Stillsitzen kann ein PIR nicht zuverlässig erkennen. |

Erkennbare GPIO-Zugriffsfehler lassen die Anzeige innerhalb der Betriebszeiten
aktiv und erscheinen im Gerätestatus. **Ein abgezogener oder falsch verdrahteter
Sensor kann einfach LOW liefern und ist so nicht sicher erkennbar.** Bei Betrieb
ohne Sensor die Funktion ausdrücklich ausgeschaltet lassen.

Zum Prüfen des Signals zuerst die Sensorfunktion auf der Webseite ausschalten
und den nächsten erfolgreichen Abgleich abwarten. Dann auf dem Pi ausführen:

```bash
sudo -u frame -H bash -c 'cd /home/frame && PYTHONPATH=/opt/kita-frame python3 -m player.motion'
```

Das Programm beobachtet GPIO17 zwei Minuten und zeigt Änderungen als **HIGH /
Bewegung** oder **LOW / Ruhe**. Mit `Strg+C` abbrechen. Erst nach dem Ende die
Sensorfunktion wieder auf der Webseite einschalten. Falls GPIO noch belegt ist,
erneut prüfen, ob die ausgeschaltete Einstellung am Pi angekommen ist.
Das Testprogramm startet im beschreibbaren Home-Verzeichnis von `frame`, damit
auch hier die GPIO-Bibliothek ihre temporären Dateien anlegen kann.

### GPIO-Arbeitsverzeichnis prüfen

Bei `xCreatePipe`- oder `.lgd-nfy`-Fehlern kann die GPIO-Bibliothek ihre
temporären Dateien nicht anlegen. Das ist ein Zugriffsfehler vor dem Lesen
des Sensors und kein Nachweis falscher Verkabelung. Innerhalb der
Betriebszeiten lässt der Player die Anzeige bei einem solchen Fehler aktiv.

Der Dienst muss als `frame` mit `WorkingDirectory=/run/kita-player` und
`RuntimeDirectory=kita-player` laufen. Auf dem Pi prüfen:

```bash
systemctl show kita-player-kms.service -p User -p WorkingDirectory -p RuntimeDirectory
sudo -u frame test -w /run/kita-player && echo "GPIO-Arbeitsverzeichnis beschreibbar"
id frame
ls -l /dev/gpiochip*
sudo journalctl -b -u kita-player-kms.service --no-pager -n 80
```

Bei abweichenden Einstellungen die Dienstdatei einschließlich zusätzlicher
Konfigurationen mit `systemctl cat kita-player-kms.service` prüfen und den
mitgelieferten Installer erneut ausführen. Anschließend den Pi neu starten
und die Live-Diagnose öffnen.
