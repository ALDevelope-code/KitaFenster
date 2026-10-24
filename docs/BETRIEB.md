# Betrieb, Sicherung und Updates

Die NAS-Anwendung wird über **DSM → Container Manager → Projekt** verwaltet.
Die Beispiele verwenden das Projekt `kitafenster` (KitaFenster) und den Ordner
`/volume1/docker/kitafenster`. Bei eurer Installation den vorhandenen Projektnamen,
Projektpfad und Datenpfad beibehalten. Die Benutzerrechte erklärt die
[NAS-Anleitung](INSTALLATION-NAS.md).

Inhalte und Rahmen werden auf der KitaFenster-Webseite verwaltet. Für die normale
NAS-Verwaltung sind keine SSH-Befehle erforderlich. Der Pi wird separat aktualisiert.

## Projekt im DSM verwalten

In **Container Manager → Projekt** das vorhandene KitaFenster-Projekt auswählen.
Die wichtigsten Aktionen unterscheiden sich wie folgt:

| Aufgabe | Vorgehen |
|---|---|
| Anwendung kurz anhalten | Projekt **Stoppen**; danach **Starten** |
| Laufende Anwendung neu starten | **Neu starten**; bestehende Einstellungen bleiben erhalten |
| `.env`, Dateirechte/Kennungen oder YAML ändern | [Konfiguration übernehmen](#konfiguration-übernehmen) |
| Neue veröffentlichte Anwendungsversion installieren | [NAS aktualisieren](#nas-aktualisieren) |
| Fehler ansehen | Container des Projekts öffnen und dessen **Protokoll** lesen |

Nicht über die Image-Seite einen zusätzlichen Einzelcontainer starten. Das
vorhandene Projekt bündelt Ports, Benutzerrechte, Datenpfade und Umgebungsvariablen.
Für einen normalen Neustart oder ein Update wird das Projekt nicht gelöscht.

## Konfiguration übernehmen

1. Die betreffende Einstellung in **File Station → Projektordner → .env** mit
   dem DSM-Text-Editor ändern und speichern. Für Compose-Änderungen die aktive
   **YAML-Konfiguration** des Projekts im Container Manager bearbeiten.
2. Das vorhandene Projekt **Stoppen**.
3. Unter **Aktion → Erstellen (Build)** das Projekt erneut erstellen lassen;
   bei Änderungen im YAML-Editor dessen angebotene Neuerstellung ausführen.
4. Nach erfolgreichem Abschluss das Projekt **Starten**, falls DSM dies nicht
   bereits erledigt hat. Containerstatus, Protokoll und Webseite prüfen.

Dadurch werden geänderte Einstellungen in den Container übernommen. Ein bloßes
**Neu starten** liest die `.env` nicht erneut ein. Der in `DATA_PATH` eingebundene
Datenordner bleibt beim Neuerstellen erhalten. Die Aktion **Erstellen/Build**
verwendet bei diesem Projekt das angegebene fertige Image; es ist kein eigener
Quellcode-Build erforderlich.
[Synology beschreibt die Projektaktionen und den YAML-Editor](https://kb.synology.com/en-global/DSM/help/ContainerManager/docker_project).

## Anmeldung ändern

In `.env` `ADMIN_USERNAME` und `ADMIN_PASSWORD` ändern und die
[Konfiguration übernehmen](#konfiguration-übernehmen). Der nächste Containerstart
übernimmt die Zugangsdaten und meldet bisherige Browsersitzungen ab. Pi-Kopplungen
bleiben erhalten. Ohne `ADMIN_PASSWORD` bleibt das bestehende Webkonto unverändert.

## NAS sichern und wiederherstellen

### Sicherung über DSM

Die einfachste vollständige Sicherung ist eine Kopie der Anwendungsdaten bei
**gestopptem Projekt**. Die Datenbank darf während dieser Kopie nicht verändert
werden. Ein Container- oder Image-Export allein enthält die eingebundenen
Anwendungsdaten nicht.

1. Die angezeigte **Serverversion**, Projektname und Projektpfad notieren.
2. In Container Manager das Projekt **Stoppen** und warten, bis der zugehörige
   Container gestoppt ist. Die Pis können bereits geladene Inhalte weiter anzeigen.
3. In File Station den vollständigen Ordner aus `DATA_PATH`, `.env` und die
   **aktive Projekt-YAML** in einen neuen, datierten Sicherungsordner kopieren.
   Liegt `data` im Projektordner, kann der gesamte Projektordner kopiert werden.
   Das Sicherungsziel muss außerhalb des kopierten Ordners liegen. Verwendet DSM
   `docker-compose.yml`, gehört diese Datei mit in die Sicherung.
4. Den Abschluss aller Kopiervorgänge abwarten und die gesicherten Dateien prüfen.
   Erst danach das Projekt wieder **Starten**.
5. Zusätzlich die NAS-Originalbilder, separat aufbewahrte Original-PDFs/Bilder
   sowie gegebenenfalls Reverse-Proxy- und Zertifikatskonfiguration sichern.
   Die vorbereiteten Anwendungsmedien ersetzen diese Originale nicht.

Alternativ lässt sich die Kopie mit einem über DSM bedienten **Hyper-Backup-Auftrag**
erstellen. Für eine direkte Sicherung des laufenden Datenordners muss das Projekt
auch dabei vom Beginn bis zum Abschluss des Sicherungslaufs gestoppt bleiben.
Eine vorher bei gestopptem Projekt angefertigte Kopie kann anschließend gesichert
werden, während die Anwendung wieder läuft.

Sicherungen enthalten Zugangsdaten und Inhalte. Zugriff beschränken und eine
Kopie außerhalb des NAS aufbewahren. Nicht mehr verwendete vorbereitete Medien
räumt die Anwendung nach einer Schutzfrist auf; diese Bereinigung ersetzt keine
Sicherung der Originale.

### Wiederherstellung über DSM

1. Das Projekt **Stoppen**. Den aktuellen Datenbestand vor Änderungen ebenfalls
   sichern, dann den vorhandenen `data`-Ordner in File Station umbenennen.
2. Den **vollständigen gesicherten Datenordner** an den in `DATA_PATH` erwarteten
   Ort zurückkopieren beziehungsweise über Hyper Backup dorthin wiederherstellen.
   Keine Datenbank oder einzelne Medien mit einem anderen Datenstand mischen.
3. Die dazugehörige `.env` und aktive YAML wiederherstellen. Bei einem anderen
   NAS Pfade und UID/GID anpassen. Besitzer und Zugriffsrechte des gesamten
   Datenordners in File Station kontrollieren, siehe [NAS-Anleitung](INSTALLATION-NAS.md#2-bilderfreigabe-und-dateirechte).
4. Auf einem vorhandenen Projekt die aktive YAML im Container Manager mit dem
   gesicherten Inhalt abgleichen. Ist noch kein Projekt vorhanden, es wie in der
   [NAS-Anleitung](INSTALLATION-NAS.md#4-projekt-kitafenster-im-container-manager-anlegen)
   mit diesem Ordner und dieser YAML anlegen. Die zum Sicherungsstand gehörende
   Image-Version verwenden.
5. Die [Konfiguration übernehmen](#konfiguration-übernehmen), anschließend
   Anmeldung, Gruppen, Dokumente, NAS-Abgleich und einen Pi prüfen.

NAS-Quelle und Marker müssen erreichbar sein. In der Sicherung enthaltene
Pi-Kopplungen bleiben gültig; nach dem Sicherungszeitpunkt gekoppelte Pis müssen
gegebenenfalls erneut gekoppelt werden. Die vorhandene Projektdefinition und der
wiederhergestellte Datenpfad müssen zusammenpassen, bevor die Anwendung startet.

## NAS aktualisieren

Ein erfolgreicher GitHub-Release stellt das Image bereit. Die Installation auf
dem NAS wird anschließend im **Container Manager** aktualisiert:

1. Die neue Version unter [GitHub Releases](https://github.com/ALDevelope-code/KitaFenster/releases)
   auswählen. Erst fortfahren, wenn Image und Installationspakete erfolgreich
   veröffentlicht wurden. Release-Hinweise lesen und [eine Sicherung anlegen](#nas-sichern-und-wiederherstellen).
2. In File Station die vorhandene `.env` im **Projektpfad** öffnen und ausschließlich
   `KITAFENSTER_VERSION` auf die gewünschte Versionsnummer **ohne `v`** setzen.
   Die eigene `.env` nicht durch `.env.example` aus dem Paket ersetzen.
3. Falls das Release Änderungen an Compose benötigt, diese aus dem NAS-Paket in
   **Projekt → Details → YAML-Konfigurationen** übernehmen. Eigene Pfade, UID/GID,
   Zusatzgruppen, Netzkonfiguration und Portbelegung beibehalten.
4. Das vorhandene Projekt **Stoppen**, mit **Aktion → Erstellen (Build)** erneut
   erstellen und anschließend **Starten**. Ein noch nicht lokal vorhandenes Image
   mit dem neuen Versions-Tag wird dabei heruntergeladen. Den Vorgang vollständig
   abwarten; bei einem Fehler das Projektprotokoll prüfen.
5. Beim Container die verwendete Image-Adresse einschließlich Versions-Tag
   kontrollieren. Die Webseite mit **Strg+F5** neu laden und die **Serverversion**
   in der Fußzeile oder unter **Einrichtung → Softwareversion** prüfen.
6. Anmeldung, NAS-Abgleich und die Anzeige auf einem Pi kontrollieren. Der
   Datenordner bleibt erhalten. NAS und Pi-Player aus demselben Release verwenden.

**Ein neues Image herunterzuladen oder den Container nur neu zu starten reicht
nicht aus, um einen anderen Versions-Tag auszuwählen.** Maßgeblich ist die Version
in `.env` und die anschließende Neuerstellung des bestehenden Projekts. KitaFenster
verwendet feste Versions-Tags; die Image-Aktualisierung für einen bereits gewählten
Tag wechselt nicht automatisch zur nächsten KitaFenster-Version.

### Images im DSM aufräumen

Nach erfolgreichem Update unter **Container Manager → Image** prüfen, welche
Images nicht mehr verwendet werden. Falls gewünscht, gezielt ein unbenutztes
KitaFenster-Image auswählen und **Löschen** verwenden. Das aktive Image und den
Datenordner behalten. **Nicht verwendete Images entfernen** betrifft sämtliche
Projekte auf dem NAS und ist für ein KitaFenster-Update nicht erforderlich.
[Synology erläutert Image-Verwaltung und Aktualisierung eines Tags](https://kb.synology.com/tr-tr/DSM/help/ContainerManager/docker_image?version=7).

## Pi aktualisieren

Der NAS-Imagewechsel aktualisiert keine Pis. Für jeden Pi das vollständige
Quellcode-Paket `kitafenster-VERSION.zip` verwenden, nicht das NAS-Paket.
`VERSION` in den folgenden Befehlen durch die gewünschte veröffentlichte
Versionsnummer ersetzen und `PI-IP` anpassen. `admin` ist ein Beispielname;
bei einem anderen Pi-Benutzer auch `/home/admin` entsprechend ersetzen.

1. In **Windows PowerShell**, im Ordner mit dem ZIP, übertragen und verbinden:

   ```powershell
   scp .\kitafenster-VERSION.zip admin@PI-IP:~/
   ssh admin@PI-IP
   ```

2. In der **SSH-Sitzung auf dem Pi** den vollständigen Block ausführen.
   Auch darin den ZIP-Dateinamen anpassen. Der Block prüft die Quelldateien,
   stoppt den Player, sichert Programm und Konfiguration und installiert neu:

   ```bash
   sudo bash <<'SH'
   set -euo pipefail
   UPDATE=$(mktemp -d /var/tmp/kitafenster-update.XXXXXX)
   python3 -m zipfile -e \
     /home/admin/kitafenster-VERSION.zip "$UPDATE"
   SOURCE="$UPDATE/kitafenster"

   test -f "$SOURCE/player/__main__.py"
   test -f "$SOURCE/shared/schedule.py"
   test -f "$SOURCE/deploy/install-player.sh"
   test -f "$SOURCE/deploy/kita-player-kms.service"
   test -f "$SOURCE/LICENSE"
   test -f "$SOURCE/NOTICE"

   systemctl stop kita-player-kms.service
   install -d -m 0700 /var/backups/kitafenster
   STAMP=$(date +%Y%m%d-%H%M%S-%N)
   tar -czf "/var/backups/kitafenster/pi-$STAMP.tar.gz" \
     -C / opt/kita-frame home/frame/.config/kita-frame
   mv /opt/kita-frame "/opt/kita-frame.vor-update-$STAMP"
   bash "$SOURCE/deploy/install-player.sh"
   reboot
   SH
   ```

Die Kopplung und der Bildercache liegen außerhalb des Programmordners und
bleiben erhalten. Bei einem Fehler nach dem Stoppen bleibt der Player gestoppt;
den Fehler beheben und die Installation fortsetzen. Sicherungen unter
`/var/backups/kitafenster` geschützt aufbewahren und deren Speicherbedarf prüfen.

3. Nach dem Neustart neu per SSH verbinden und kontrollieren:

   ```bash
   sudo systemctl status kita-player-kms.service --no-pager
   sudo journalctl -b -u kita-player-kms.service --no-pager -n 50
   ```

Auf der Webseite müssen **Verbunden** und ein aktueller **Letzter Abgleich**
erscheinen. Die sichtbaren Inhalte, Bildschirmteilung und das Aufwachen des
Monitors vor Ort prüfen. Die Serverversionsanzeige auf der Webseite bestätigt
nur den NAS-Stand, nicht die installierte Pi-Version.

## Monitor, Gerät oder Standort wechseln

- **Nur Monitor:** herunterfahren, tauschen, Monitor vor dem Pi einschalten;
  keine neue Kopplung. [Monitorwechsel](INSTALLATION-PI.md#monitor-austauschen).
- **Pi/SD-Karte ersetzt:** Ersatzgerät installieren und mit neuem Code des
  vorhandenen Rahmens koppeln; altes Gerät außer Betrieb nehmen.
- **Anderes WLAN/NAS:** zusätzliches WLAN behalten/anlegen, neue NAS-Adresse
  koppeln und alten Cache entfernen. [Umzug](INSTALLATION-PI.md#anderes-wlan-oder-anderes-nas).

## Offlinebetrieb und Uhrzeit

Bei Netzwerkausfall läuft der letzte vollständig geladene Stand weiter.
Downloads werden vor Übernahme geprüft; bestätigte Änderungen und Löschungen
werden auf den Pi übernommen. Bei Gruppenwechsel, geändertem Zugriff oder
bestätigtem Schlüsselwiderruf wird der bisherige Cache geleert. Ein offline
befindlicher Pi kann neue Widerrufe oder Löschungen erst bei der nächsten
Verbindung erfahren. Bei sofortigem Entzug Gerät vor Ort ausschalten.

Der Cache ist standardmäßig auf 1 GB begrenzt. Der Pi misst zusätzlich den
freien Platz auf dem Dateisystem seines Cache-Ordners und lässt mindestens
10 % der Gesamtkapazität sowie 32 MiB für andere Schreibvorgänge frei. Die
Kartengröße muss auf dem NAS nicht eingetragen werden. Überschreiten die
zugewiesenen Inhalte das Cache-Limit oder die freie Speicherreserve, lädt der
Pi einen Teilbestand und meldet den ausgelassenen Umfang im Gerätestatus.
Unter **Bilderrahmen** erscheinen der zuletzt gemeldete freie Platz und die
Gesamtkapazität jedes aktualisierten Pi. Die Meldung kommt beim Geräteabgleich;
bei offline befindlichen Geräten ist sie entsprechend alt. Bei Austausch
kann vorübergehend zusätzlicher freier Speicher nötig sein. Auch freien NAS-Speicher überwachen. Nicht mehr verwendete
vorbereitete Medien werden nach einer Schutzfrist automatisch bereinigt.
Sicherungen und Originaldateien separat verwalten.

Ein Pi ohne Echtzeituhr benötigt nach stromlosem Start NTP für zuverlässige
Betriebszeiten und Ablaufdaten. Außerhalb der Betriebszeiten gilt die gewählte
Abschaltung auch ohne Bewegungssensor. Die optionale Bewegungserkennung arbeitet
auch offline mit ihren zuletzt geladenen Einstellungen. HDMI-Standby und
Wiederanlauf des Monitors am Gerät prüfen: [Bewegungssensor](BEWEGUNGSSENSOR.md).

Eine unvollständige gespeicherte Konfiguration wird nicht zur Anzeige verwendet.
Der Player lädt beim nächsten erfolgreichen Abgleich eine gültige Konfiguration;
bereits intakte Bilddateien müssen dafür nicht erneut heruntergeladen werden.

## Diagnose

Auf dem NAS zuerst in **DSM → Container Manager** den Projektstatus und das
Protokoll des zugehörigen Containers ansehen. Für gezielte Prüfungen von
Dateirechten, Verbindung oder Netzwerkproblemen gibt es die getrennte
[NAS-Fehlersuche mit SSH](NAS-FEHLERSUCHE.md).

Auf dem **Pi** erfolgt die Dienstdiagnose weiterhin über SSH:

```bash
sudo systemctl status kita-player-kms.service --no-pager
sudo journalctl -b -u kita-player-kms.service --no-pager -n 80
timedatectl status
df -h /home/frame
```

Die Fernaktion **Player neu starten** startet nur die Anwendung. Über Pi-SSH
startet `sudo systemctl restart kita-player-kms.service` den Dienst neu;
`sudo reboot` startet den ganzen Pi. Keine `player.json` oder vollständige
`.env` als Diagnose veröffentlichen: sie enthalten Zugangsdaten.
