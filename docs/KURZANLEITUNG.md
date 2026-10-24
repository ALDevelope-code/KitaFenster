# Kurzanleitung: NAS, Pi und Monitorwechsel

Für die Einrichtung mit KMS/DRM-Autostart. `VERSION`, `NAS-IP`, `PI-IP` und
Kontonamen durch die eigenen Werte ersetzen. NAS und Pi aus demselben
veröffentlichten Release installieren.

`admin` ist ein neutraler Beispielname für euer Administrationskonto.
Bei einem anderen Benutzernamen auch die Pfade unter `/home/admin` anpassen.

## A. NAS einmalig über DSM einrichten

Die NAS-Anwendung wird als Projekt im **Container Manager** eingerichtet und
verwaltet. SSH ist dafür nicht nötig. Eine bereits funktionierende Installation
nicht neu anlegen; für einen Versionswechsel die [DSM-Update-Anleitung](BETRIEB.md#nas-aktualisieren) verwenden.

1. **Dateien:** `kitafenster-nas-VERSION.zip` herunterladen, mit File Station
   nach `/volume1/docker/kitafenster` hochladen und dort entpacken.
   `.env.example` als `.env` speichern; diese liegt neben `compose.yaml`.
2. **Bilder und Daten:** Die Freigabe `Kita-Bilderrahmen` mit Gruppenordnern und
   `.bilderrahmen-source` vorbereiten. Im Projektordner `data` anlegen.
   In File Station dem gewählten NAS-Konto Leserechte auf die Bilder und
   Besitzer-/Schreibrechte auf `data` geben, einschließlich Unterordnern und Dateien.
3. **Kennungen:** UID/GID des NAS-Kontos bei Bedarf einmalig über den
   [DSM-Aufgabenplaner ermitteln](INSTALLATION-NAS.md#uid-und-gid-einmalig-über-dsm-ermitteln).
   Bei bestehenden Installationen die funktionierenden Werte beibehalten.
4. **Konfiguration:** `.env` mit dem DSM-Text-Editor bearbeiten:

   | Wert | Eintrag |
   |---|---|
   | `KITAFENSTER_VERSION` | Gewählte veröffentlichte Version ohne `v` |
   | `NAS_PATH` | `/volume1/Kita-Bilderrahmen` |
   | `DATA_PATH` | `/volume1/docker/kitafenster/data` |
   | `NAS_UID`, `NAS_GID` | Numerische Kennungen des gewählten NAS-Kontos |
   | `NAS_READ_GID` | Benötigte Zusatzgruppe; sonst leer |
   | `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Web-Anmeldung; Passwort in einfachen Anführungszeichen |

5. **Projekt:** In **Container Manager → Projekt → Erstellen** `kitafenster`
   anlegen, den vorbereiteten Ordner als Projektpfad wählen und `compose.yaml`
   importieren. Den Assistenten abschließen und das Projekt starten lassen.
   Bei bestehenden Projekten deren Namen beibehalten. DSM kann die aktive YAML
   als `docker-compose.yml` verwalten; danach ist der YAML-Editor des Projekts
   maßgeblich, während `.env` im Projektordner bleibt.
6. **Prüfen:** Containerstatus und Protokoll im DSM prüfen. `http://NAS-IP:8088`
   öffnen, anmelden und unter **Gruppen & NAS** die Fotoordner zuweisen.
   **NAS abgleichen** wählen; erst nach erfolgreichem Abgleich den Pi koppeln.

Konfigurationsänderungen benötigen eine [Neuerstellung des Projekts](BETRIEB.md#konfiguration-übernehmen);
**Neu starten** allein übernimmt keine geänderte `.env`.
Details: [NAS-Installation](INSTALLATION-NAS.md), [Sicherung und Updates über DSM](BETRIEB.md)
und [Fehlersuche mit optionalem SSH](NAS-FEHLERSUCHE.md).

## B. Pi einmalig einrichten

1. Mit Raspberry Pi Imager **Raspberry Pi OS Lite 32-bit (Trixie)** schreiben.
   Hostname, Benutzer `admin`, Passwort, WLAN, Deutschland und SSH einrichten.
2. Monitor an HDMI anschließen, einschalten und HDMI wählen; dann den Pi starten.
   `PI-IP` in der Router-Geräteliste nachsehen.
3. `kitafenster-VERSION.zip` auf Windows entpacken. Im Ordner **oberhalb** des
   enthaltenen Verzeichnisses `kitafenster` PowerShell öffnen:

   ```powershell
   scp -r .\kitafenster admin@PI-IP:~/
   ssh admin@PI-IP
   ```

4. In der geöffneten **Pi-SSH-Sitzung** installieren:

   ```bash
   sudo bash /home/admin/kitafenster/deploy/install-player.sh
   ```

5. Auf der NAS-Webseite **Bilderrahmen → Rahmen hinzufügen**: Gruppe und
   Ausrichtung wählen, Kopplungscode bereithalten. Auf dem Pi:

   ```bash
   sudo -u frame -H bash -c 'cd /opt/kita-frame && python3 -m player --pair http://NAS-IP:8088'
   ```

   `NAS-IP` ersetzen, Code verdeckt eingeben und danach `sudo reboot` ausführen.
   Für Elternrahmen **Interne Inhalte zulassen** ausgeschaltet lassen.
6. Nach dem Neustart müssen Bilder erscheinen und die Webseite **Verbunden**
   anzeigen. Dienstprüfung über SSH:

   ```bash
   sudo systemctl status kita-player-kms.service --no-pager
   ```

Der Player startet automatisch als `frame`. LightDM bleibt gesperrt.
Samba ist für diesen Installationsweg nicht erforderlich.
Details und erneutes Koppeln: [Pi-Installation](INSTALLATION-PI.md).

## C. Nur den Monitor austauschen

**Pi und SD-Karte bleiben gleich: nichts neu installieren oder koppeln.**

1. Per SSH `sudo poweroff` ausführen und das Herunterfahren abwarten.
2. Pi vom Strom trennen und den neuen Monitor per HDMI anschließen.
3. Monitor einschalten und HDMI wählen; erst dann den Pi einschalten.
4. Der Player übernimmt die erkannte Auflösung. Bei Bedarf in der Webverwaltung
   Ausrichtung und **Ganzes Bild / Bildschirm füllen** ändern.
5. Bilder, Bildränder und einen weiteren Neustart prüfen. Full HD ist die
   bevorzugte Auflösung; Monitorstandby am neuen Gerät kontrollieren.

Bei schwarzem Bild zuerst Betriebszeiten und HDMI-Eingang prüfen, dann:

```bash
sudo journalctl -b -u kita-player-kms.service --no-pager -n 50
```

**Pi oder SD-Karte ersetzt?** Abschnitt B auf dem Ersatzgerät durchführen und
beim vorhandenen Rahmen einen neuen Kopplungscode erzeugen. Das alte Gerät
außer Betrieb nehmen. **Umzug in ein anderes WLAN/NAS?** Siehe
[Anderes WLAN oder anderes NAS](INSTALLATION-PI.md#anderes-wlan-oder-anderes-nas).

## D. Optional: Display durch Bewegung aktivieren

1. Pi herunterfahren und vom Strom trennen. HC-SR501 anschließen:
   **VCC → Pin 2 (5 V), GND → Pin 6, OUT → Pin 11 (GPIO17)**.
   Sensorbeschriftung beachten; niemals 5 V auf GPIO17 legen.
2. Wieder starten. Auf der Webseite beim Rahmen **Verwalten → Bewegungssensor & Energiesparen**:
   Sensor aktivieren, Nachlaufzeit wählen (Standard 5 Minuten), speichern.
3. Nach 60 Sekunden Einlaufzeit Einschlafen und Aufwachen mit Bewegung testen.
   Den Test auch nach jedem Monitorwechsel wiederholen. Bei Problemen mit
   HDMI-Standby ist **Schwarzes Bild** als Alternative wählbar.

Ohne angeschlossenen Sensor die Funktion ausgeschaltet lassen. Jeder Rahmen
kann anders eingestellt werden. Vollständiger Anschlussplan, Signalprüfung
und Verhalten außerhalb der Betriebszeiten: [Bewegungssensor](BEWEGUNGSSENSOR.md).
