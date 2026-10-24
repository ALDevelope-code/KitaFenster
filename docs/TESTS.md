# Tests und Abnahme

## Automatische Prüfungen

Im Projekt mit installierten Testabhängigkeiten unter Windows:

```powershell
$env:SDL_VIDEODRIVER='dummy'
$env:SDL_AUDIODRIVER='dummy'
.\.venv\Scripts\python.exe -m tools.release_info --check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check server player shared tests tools
.\.venv\Scripts\python.exe -m ruff format --check server player shared tests tools
node --check server/static/app.js
node --check server/static/motion.js
node --check server/static/device-settings.js
node --check server/static/document-actions.js
node --check server/static/split-display.js
node --check server/static/operating-hours.js
node --test tests/motion_ui.test.cjs
node --test tests/device_settings_ui.test.cjs
node --test tests/document_actions_ui.test.cjs
node --test tests/split_display_ui.test.cjs
node --test tests/operating_hours_ui.test.cjs
docker compose --env-file .env.example config --quiet
docker compose --env-file .env.example -f compose.yaml -f compose.build.yaml config --quiet
```

Die Tests decken Anmeldung, Gerätezugriff, Datei-/PDF-Verarbeitung, Freigaben,
Betriebszeiten, Inhaltszeitfenster, Wiedergabe, Cache, Backup/Restore, Branding und Release-Pakete ab.
Die Compose-Prüfungen kontrollieren auch Passwortübernahme sowie Benutzer- und
Gruppenzuordnung. Die NAS-Zugriffsprüfung wird mit lesbaren und fehlenden Quellen
sowie Datei- und Schreibfehlern getestet.

Sensorprüfungen simulieren GPIO und HDMI: deaktivierter Betrieb ohne Hardwarezugriff,
Einlaufzeit, Nachlaufzeit, Fehlerbehandlung, Aufwachen, Vorrang von Betriebszeiten
und Sofortmeldungen sowie Speicherung je Gerät und im Offline-Cache. Im echten
Player-Renderloop wird geprüft, dass bei abgeschaltetem HDMI keine Bildwechsel
angefordert werden und nach dem Aufwachen aktuelle Inhalte erscheinen.
Die Live-Diagnose wird zusätzlich auf getrennte Sensordauer und Software-Nachlaufzeit,
begrenzten Verlauf, unbekanntes Signal bei GPIO-Fehlern, ablaufende Diagnosesitzungen,
Geräte-/Admin-Zugriff, veraltete Messwerte und unveränderten Inhaltsabgleich geprüft. Node prüft die Darstellung
von HIGH/LOW, ausstehenden Einstellungen, Fehlern und das Beenden der Live-Abfragen.

GitHub Actions prüft zusätzlich mit Bash die Syntax aller `deploy/*.sh`, baut
den Linux/AMD64-Container und führt den Funktionstest vor Veröffentlichung aus.
Lokale Windows-Tests ersetzen diesen Linux-Lauf nicht. Details: [Releases](RELEASES.md).

## Bestätigter Hardwarestand

In der Testumgebung wurden NAS-Dateizugriff, PIN-Kopplung, Fotoanzeige und
**automatischer Start nach Neustart** auf einem Pi 3 A+ mit Raspberry Pi OS Lite
32-bit/Trixie und ASUS ZenScreen Go bestätigt. Der Player verwendet KMS/DRM;
LightDM bleibt gesperrt.

Das bestätigt nicht jede Monitor-/OS-Kombination. Dauerbetrieb, Leistungsaufnahme
und Wiederanlauf des Monitors nach Stromausfall werden am jeweiligen Standort geprüft.
HC-SR501, Verkabelung und HDMI-Standby/Aufwachen am jeweiligen Gerät prüfen;
automatische Tests mit simulierter Hardware ersetzen diese Abnahme nicht.

## Kurze Abnahme in der Kita

1. Pi einschalten: Bilder ohne Tastaturbedienung, Webseite **Verbunden**.
2. Quer-, Hochformat- und Quadratbild anzeigen; Ausrichtung und Ränder prüfen.
3. Am NAS ein Foto hinzufügen, ersetzen und löschen; Abgleich kontrollieren.
4. Öffentliche Meldung und ein für Eltern freigegebenes Dokument anzeigen. Ein internes Dokument darf
   auf einem Elternrahmen nicht sichtbar werden.
5. Bildschirmteilung mit 33 %, 40 % und 50 % Zusatzanteil, beiden Seiten und
   Hoch-/Querformat prüfen. Inhaltsvorschau und Pi müssen dieselbe Aufteilung zeigen.
   Zentrale und eigene Betriebszeiten sowie Inhaltszeitfenster für beide Bereiche
   prüfen. Sofortmeldungen mit Ablauf müssen auch außerhalb der Betriebszeiten
   im Vollbild erscheinen. Die gewählte Abschaltung muss dort auch ohne Sensor greifen.
6. WLAN-Verbindung unterbrechen: geladene Inhalte laufen weiter. Verbindung
   wiederherstellen: Änderungen werden übernommen.
7. Pi neu starten und einen mehrstündigen Lauf beobachten; Speicher mit
   `free -m` und `df -h` prüfen.
8. Wiederanlauf nach stromlosem Zustand einschließlich Monitor und Uhrzeit/NTP prüfen.
9. Nach einem [Monitorwechsel](INSTALLATION-PI.md#monitor-austauschen) Bildgröße,
   Ausrichtung und automatischen Start erneut prüfen.
10. Sicherung in einer separaten Testinstallation wiederherstellen.
11. Falls ein HC-SR501 verwendet wird: [Sensor-Abnahme](BEWEGUNGSSENSOR.md#4-am-echten-gerät-testen--auch-nach-monitorwechsel)
    durchführen. Einschlafen, dreimaliges Aufwachen, aktuelle Inhalte nach der Pause,
    Sofortmeldung, Betriebszeiten, Neustart und deaktivierten Sensorbetrieb prüfen.
