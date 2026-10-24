# Raspberry Pi einrichten

Für einen dedizierten Bilderrahmen mit **Raspberry Pi OS Lite 32-bit,
Debian 13/Trixie**. Fotoanzeige und Autostart nach Neustart wurden auf dem
Pi 3 A+ mit ASUS ZenScreen Go bestätigt.

Schneller Einstieg: [Kurzanleitung](KURZANLEITUNG.md). Der Player verwendet
KMS/DRM und startet über `kita-player-kms.service`.

`admin` ist in dieser Anleitung ein Beispielname. Verwendet euren eigenen
Administrationsbenutzer und passt auch Pfade wie `/home/admin` entsprechend an.
Das vom Installer angelegte Dienstkonto `frame` bleibt unverändert.

## 1. SD-Karte und Zugang vorbereiten

Im Raspberry Pi Imager den Pi, **Raspberry Pi OS Lite (32-bit)** und die SD-Karte
wählen. Vor dem Schreiben einstellen:

- Eindeutiger Hostname, beispielsweise `rahmen-gruppe1`.
- Administrationskonto `admin` mit eigenem Passwort; SSH aktivieren.
- WLAN, WLAN-Land Deutschland und Zeitzone Europe/Berlin.

Monitor per HDMI anschließen, einschalten und HDMI auswählen; danach den Pi
starten. Die IP in der Geräteliste des Routers nachsehen. In Windows PowerShell:

```powershell
ssh admin@PI-IP
```

`PI-IP` ersetzen. Beim ersten Kontakt den Hostschlüssel dem Pi zuordnen und
bestätigen. `admin` verwaltet den Pi mit sudo; der Installer legt für die
Anzeige das separate Konto `frame` an.

## 2. Programmdateien übertragen

Das vollständige **kitafenster-VERSION.zip** aus einem erfolgreich gebauten
[Release](https://github.com/ALDevelope-code/KitaFenster/releases) auf Windows
entpacken. Im enthaltenen Ordner `kitafenster` müssen `deploy`, `player`,
`shared`, `LICENSE` und `NOTICE` liegen. Das NAS-ZIP eignet sich dafür nicht.

Eine neue PowerShell **im übergeordneten Ordner** öffnen und übertragen:

```powershell
scp -r .\kitafenster admin@PI-IP:~/
```

Das ergibt `/home/admin/kitafenster/deploy/install-player.sh` auf dem Pi.
SCP nutzt den SSH-Zugang und braucht keine zusätzliche Freigabe. Nur
vertrauenswürdige Installationsdateien übertragen und ausführen.

## 3. Installieren

In der **SSH-Sitzung auf dem Pi**:

```bash
sudo bash /home/admin/kitafenster/deploy/install-player.sh
```

Der Installer bezieht Python/Pygame aus den OS-Paketquellen, kopiert die Anwendung
nach `/opt/kita-frame`, setzt Leserechte für `frame` und aktiviert NTP sowie
`kita-player-kms.service`. Konsole 1 wird für den Player reserviert; SSH und die
anderen Textkonsolen bleiben für Administration verfügbar.

**LightDM gesperrt lassen**, damit die direkte Bildschirmausgabe des Players
verfügbar bleibt. Nach der Installation neu starten. Kopplung und Cache liegen
unter `/home/frame/.config/kita-frame/`.

Falls der Installer nicht gefunden wird, den übertragenen Pfad prüfen:

```bash
find /home/admin/kitafenster -name install-player.sh
```

Den gefundenen vollständigen Pfad mit `sudo bash` verwenden. Selbst bearbeitete
Shell-Dateien mit Linux-Zeilenenden (LF) speichern; die mitgelieferten Skripte
verwenden bereits LF.

## 4. Mit der NAS-Zentrale koppeln

1. Auf der Webseite **Bilderrahmen → Rahmen hinzufügen** öffnen.
2. Gruppe, Name und Ausrichtung einstellen. Im Elternbereich **Interne Inhalte
   zulassen** ausgeschaltet lassen.
3. Den 15 Minuten gültigen Kopplungscode bereithalten und auf dem Pi ausführen:

```bash
sudo -u frame -H bash -c 'cd /opt/kita-frame && python3 -m player --pair http://NAS-IP:8088'
```

`NAS-IP` ersetzen und den Code verdeckt eingeben. Bei HTTPS den entsprechenden
Hostnamen verwenden; eine eigene CA mit `--ca-file /pfad/zur/ca.pem` ergänzen.
Die Zugangsdaten stehen ausschließlich für `frame` lesbar in
`/home/frame/.config/kita-frame/player.json`.

```bash
sudo reboot
```

## 5. Funktion prüfen

Nach dem Neustart erneut per SSH verbinden:

```bash
sudo systemctl status kita-player-kms.service --no-pager
sudo journalctl -b -u kita-player-kms.service --no-pager -n 50
```

Erwartet: **active (running)**, sichtbare Bilder und **Verbunden** mit aktuellem
Abgleich in der Webverwaltung. An jedem neuen Standort zusätzlich Ausrichtung,
Lesbarkeit, Ruhezeiten und einen längeren Lauf prüfen.

Der Dienst startet unter `frame`; nur der kurze Wechsel auf Konsole 1 benötigt
Root. Ein gefüllter Cache ermöglicht die Anzeige auch ohne NAS-Verbindung.
Nach stromlosem Start braucht ein Pi ohne Echtzeituhr NTP für verlässliche Uhrzeit
und Ablaufzeiten. Außerhalb der Betriebszeiten gilt die am Rahmen gewählte
Abschaltung: HDMI-Standby oder Schwarzbild, auch ohne Bewegungssensor.

Optional lässt sich ein **HC-SR501** anschließen und je Bilderrahmen in der
Webverwaltung aktivieren. Anschluss an Pin 2, 6 und 11, Einstellungen und
Funktionstest: [Bewegungssensor](BEWEGUNGSSENSOR.md). Der Installer richtet die
GPIO-Abhängigkeiten bereits ein; ohne Aktivierung wird kein GPIO angesprochen.

## Monitor austauschen

**Bei demselben Pi und derselben SD-Karte sind keine Neuinstallation und keine
neue Kopplung nötig.**

1. Auf dem Pi `sudo poweroff` ausführen und das Herunterfahren abwarten.
2. Pi vom Strom trennen, HDMI-Kabel und Monitor austauschen.
3. Neuen Monitor mit Strom versorgen, einschalten und HDMI auswählen.
4. Pi einschalten. Der Player verwendet die beim Start erkannte Auflösung.
5. In der Webverwaltung gegebenenfalls Drehung (0/90/180/270°) und **Ganzes Bild**
   oder **Bildschirm füllen** anpassen. Keine zusätzliche Betriebssystem-Drehung setzen.
6. Ein Quer- und Hochformatbild sowie die Ränder prüfen und nochmals neu starten.
7. Bei aktiviertem Bewegungssensor auch Einschlafen und Aufwachen am neuen
   Monitor testen: [Standby-Prüfung](BEWEGUNGSSENSOR.md#4-am-echten-gerät-testen--auch-nach-monitorwechsel).

Bevorzugt Full HD (1920 × 1080) verwenden; andere Auflösungen am Gerät prüfen.
Es ist kein ASUS-spezifischer HDMI-Modus fest vorgegeben. Ob der Monitor nach
Stromausfall selbst wieder auf HDMI einschaltet, am konkreten Gerät prüfen.

Ein Tausch bei laufendem Pi wird nicht automatisch vom Player neu eingerichtet.
Wurde das Kabel im Betrieb umgesteckt, mit `sudo reboot` neu starten.
Für diese Einrichtung werden keine `xrandr`-Befehle benötigt.

## Anderes WLAN oder anderes NAS

Das zusätzliche Kita-WLAN noch im Heimnetz mit `sudo nmtui` unter
**Eine Verbindung bearbeiten → Hinzufügen → Wi-Fi** speichern und automatisch
verbinden lassen. Das Heimnetzprofil behalten; die neue Verbindung zu Hause
nicht aktivieren. In der Kita die neue Pi-IP am Router ablesen. Ein isoliertes
Gast-WLAN eignet sich nicht, wenn darüber das NAS unerreichbar ist.

Auf der Webseite des Ziel-NAS einen Rahmen anlegen oder beim vorhandenen Rahmen
**Verwalten → Gerät & Wartung → Neuen Kopplungscode erstellen** wählen. Auf dem Pi:

```bash
sudo systemctl stop kita-player-kms.service &&
sudo -u frame -H bash -c 'cd /opt/kita-frame && python3 -m player --pair http://NEUE-NAS-IP:8088' &&
sudo -u frame -H rm -rf -- /home/frame/.config/kita-frame/cache &&
sudo reboot
```

Die neue Adresse einsetzen. Nach erfolgreicher Kopplung wird der bisherige lokale
Bildercache gelöscht; Originalfotos auf dem NAS bleiben erhalten. Bei einem Fehler
bleibt der Dienst gestoppt: Ursache beheben und erneut koppeln. Einen alten Rahmen
auf einer separaten Heim-Zentrale entfernen, wenn er dort nicht mehr gebraucht wird.
Ein Monitorwechsel allein erfordert diese Schritte nicht.

Bei Ersatz von **Pi oder SD-Karte** das Ersatzgerät nach dieser Anleitung
installieren und mit einem neuen Code des vorhandenen Rahmens koppeln. Das alte
Gerät außer Betrieb nehmen. Keine Geräteschlüssel auf mehrere aktive Pis kopieren.

## Wenn etwas nicht funktioniert

| Beobachtung | Prüfen / ausführen |
|---|---|
| Pi nicht per SSH erreichbar | Strom, Router-Geräteliste, neue IP und WLAN prüfen. Mit Tastatur `Strg+Alt+F2` zur Anmeldung wechseln; `sudo nmtui`. |
| Dienst fehlt | Aktuellen Installer mit `kita-player-kms.service` verwenden. |
| Dienst meldet fehlende `player.json` | Unter `frame` koppeln, dann neu starten. |
| Dienst startet immer wieder neu | `sudo journalctl -b -u kita-player-kms.service --no-pager -n 80`; Speicher und Dateirechte prüfen. |
| `pygame.error: EGL not initialized` | Grafikpakete fehlen möglicherweise auf Raspberry Pi OS Lite; siehe Reparatur unten. |
| Verbunden, aber schwarzer Bildschirm | Betriebszeiten, Bewegungspause und gemeldeten Modus, HDMI, Monitorstrom und Neustart nach Monitorwechsel prüfen. |
| Player läuft, Fotos sind geladen, HDMI-Testbild funktioniert, trotzdem schwarz | SDL-Grafiktreiber auf `opengles2` festlegen; siehe unten. |
| NAS-Abgleich meldet Fehler | [NAS-Rechte prüfen](NAS-FEHLERSUCHE.md#dateirechte-korrigieren); Kopplung behebt keine Ordnerrechte. |

Installierte Programmdateien müssen für `frame` lesbar sein; der Installer setzt
diese Rechte beim Kopieren der Programmdateien. Ein `Input/output error`
beim Lesen normaler Systemdateien deutet auf ein Speicher-/Dateisystemproblem hin
und wird nicht durch eine neue Kopplung repariert.

Weitere Befehle und Sicherungen: [Betrieb](BETRIEB.md).

### Player startet mit „EGL not initialized“ nicht

Der Fehler tritt vor dem ersten NAS-Abgleich auf: Linux und SSH können erreichbar
sein, während der Bilderrahmen in der Verwaltung offline bleibt. Auf einer
Lite-Installation fehlen unter Umständen EGL/Mesa-Bibliotheken, die der Player
für die direkte KMS/DRM-Grafikausgabe benötigt. Der aktuelle Installer installiert
sie ausdrücklich. Fehlen sie in der Installation, lassen sie sich per SSH ergänzen:

```bash
sudo apt-get update
sudo apt-get install --no-install-recommends libdrm2 libgbm1 libegl1 libegl-mesa0 libgles2 libgl1-mesa-dri fontconfig
sudo systemctl restart kita-player-kms.service
sudo systemctl status kita-player-kms.service --no-pager
sudo journalctl -b -u kita-player-kms.service --no-pager -n 50
```

Bleibt der Fehler bestehen, zusätzlich HDMI-Erkennung, Grafiktreiber und freien
Speicher prüfen:

```bash
cat /sys/class/drm/card*-HDMI-A-*/status
df -h /
sudo du -xhd1 /home /var /opt
sudo journalctl -b -k --no-pager | grep -Ei 'drm|vc4|v3d|cma|oom|voltage|error'
```

### Player läuft, aber die Fotoausgabe bleibt schwarz

Zuerst Betriebszeiten, Bewegungspause und den gemeldeten Modus in der
Webverwaltung prüfen. Der Dienst verwendet `SDL_VIDEODRIVER=KMSDRM` und
`SDL_RENDER_DRIVER=opengles2`. Die tatsächlich wirksamen Einstellungen zeigen:

```bash
systemctl cat kita-player-kms.service
systemctl show kita-player-kms.service -p Environment -p WorkingDirectory
cat /sys/class/drm/card*-HDMI-A-*/status
```

Auch zusätzliche Dienstdateien unter `kita-player-kms.service.d` berücksichtigen:
Sie können die mitgelieferte Konfiguration überschreiben. Bei abweichenden
Einstellungen den Installer aus dem vollständigen Projektordner ausführen
und den Pi neu starten. Bei weiterhin schwarzem Bild HDMI-Verbindung,
Monitor-Eingang und das Dienstprotokoll prüfen.

### Freien Speicher prüfen

Große Sicherungsdateien erst nach Prüfung auf einen anderen Datenträger übertragen
oder gezielt entfernen. Ein Windows-Zielpfad in einer auf dem Pi ausgeführten
Shell schreibt keine Datei auf den PC; dadurch kann eine Sicherung versehentlich
die SD-Karte füllen.

Quellen: [Raspberry Pi OS und Einrichtung](https://www.raspberrypi.com/documentation/computers/getting-started.html),
[Raspberry Pi: Bildschirme](https://www.raspberrypi.com/documentation/computers/configuration.html),
[Mesa-EGL-Paket](https://packages.debian.org/trixie/libegl-mesa0),
[SDL-Grafiktreiberwahl](https://wiki.libsdl.org/SDL2/SDL_HINT_RENDER_DRIVER),
[NetworkManager: nmtui](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nmtui.html).
