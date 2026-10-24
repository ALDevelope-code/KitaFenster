# Zentrale auf der Synology mit DSM einrichten

Die NAS-Anwendung wird vollständig über **DSM → Container Manager → Projekt**
verwaltet. Dateien und Rechte bearbeitet ihr in **File Station**. Die Beispiele
verwenden den Projektordner `/volume1/docker/kitafenster` auf Volume 1.
Der Pi benötigt keine SMB-Zugangsdaten.

`admin` steht in den Beispielen für euer gewähltes NAS-Konto. Verwendet dessen
tatsächlichen Namen und Kennungen; ein deaktiviertes DSM-Standardkonto muss
dafür nicht aktiviert werden.

Für Installation, Start und Updates ist keine SSH-Verbindung zum NAS nötig.
Die SSH-Befehle stehen getrennt unter [NAS-Fehlersuche](NAS-FEHLERSUCHE.md).
Die Installation auf dem Pi hat ihren eigenen Ablauf: [Pi-Anleitung](INSTALLATION-PI.md).

## 1. Paket und Projektordner vorbereiten

1. **Container Manager** im DSM-Paketzentrum installieren beziehungsweise öffnen.
   Das veröffentlichte Image benötigt ein NAS mit **Intel-/AMD-Prozessor (AMD64)**.
2. `kitafenster-nas-VERSION.zip` aus einem erfolgreich gebauten
   [Release](https://github.com/ALDevelope-code/KitaFenster/releases) herunterladen.
3. In File Station unter der Freigabe `docker` den Ordner `kitafenster` anlegen,
   das ZIP hochladen und dort entpacken. `compose.yaml` und `.env.example`
   müssen direkt im Projektordner liegen, nicht in einem zusätzlichen Unterordner.
4. `.env.example` kopieren und die Kopie in **.env** umbenennen, ohne `.txt`.
   Zum Bearbeiten den **Text Editor** aus dem DSM-Paketzentrum verwenden und
   die Datei in File Station damit öffnen. `.env` liegt neben der Compose-Datei.
   Bei einer bestehenden Installation die eigene `.env` erhalten.

`VERSION` steht hier für die gewünschte veröffentlichte Versionsnummer.
Das Paket enthält außerdem `pruefe-nas.py` für die Fehlersuche und die Anleitungen
unter `docs/`. Es wird das fertige GitHub-Container-Image verwendet; auf dem NAS
muss kein eigener Quellcode-Build ausgeführt werden.

## 2. Bilderfreigabe und Dateirechte

In **DSM → Systemsteuerung → Gemeinsamer Ordner** `Kita-Bilderrahmen` anlegen.
Den tatsächlichen Pfad in File Station unter **Eigenschaften → Allgemein → Ort**
prüfen. Die gewünschte Struktur lautet beispielsweise:

```text
/volume1/Kita-Bilderrahmen/
  .bilderrahmen-source
  Gruppe 1/
  Gruppe 2/
  Gruppe 3/
```

Die Datei `.bilderrahmen-source` markiert die Bilderquelle. Sie verhindert, dass
ein fehlender Mount als leere Fotosammlung behandelt wird. Die Markerdatei und
Gruppenordner aus den separaten
[Testdaten](https://github.com/ALDevelope-code/KitaFenster/tree/HEAD/testdaten)
herunterladen und mit File Station direkt hierher hochladen. Keinen zusätzlichen
Ordner `testdaten` dazwischenschieben. Alternativ eine leere Textdatei hochladen
und in File Station exakt `.bilderrahmen-source` nennen, ohne `.txt`.

Ein vorhandenes NAS-Konto mit passenden Rechten wählen, beispielsweise `admin`,
oder einen eigenen Dienstbenutzer unter **Benutzer und Gruppe** anlegen.
Unter **File Station → Eigenschaften → Berechtigung** diesem Konto Leserecht
auf die Bilderfreigabe einschließlich Unterordner und Dateien geben.
Mitarbeitende behalten ihre Schreibrechte. Der Container bindet diese Quelle
nur lesbar ein und kann die Originale darüber nicht ändern.

Im Projektordner zusätzlich **data** anlegen. Unter **Eigenschaften → Allgemein**
den gewählten NAS-Benutzer als Besitzer setzen. Unter **Berechtigung** diesem
Benutzer Lese- und Schreibzugriff geben; der Ordner ist für Anwendungsdaten und
soll nicht allgemein freigegeben werden. Bei bereits vorhandenen Daten Besitzer
und Rechte auf **diesen Ordner, Unterordner und Dateien** anwenden; zuvor das
Projekt stoppen und [sichern](BETRIEB.md#nas-sichern-und-wiederherstellen).
Verweigern-Einträge und fehlende Zugriffsrechte auf übergeordnete Ordner ebenfalls prüfen.
[Synology beschreibt die Vergabe von Dateirechten in File Station](https://kb.synology.com/en-global/DSM/help/FileStation/privilege?version=7).

### UID und GID einmalig über DSM ermitteln

Der Container benötigt die numerischen Benutzer- und Gruppenkennungen. Bei einer
funktionierenden Installation die vorhandenen Werte in `.env` beibehalten.
Für die Ersteinrichtung lassen sie sich ohne SSH mit einer einmaligen DSM-Aufgabe ablesen:

1. **Systemsteuerung → Aufgabenplaner → Einstellungen** öffnen, die
   **Ausgabeergebnisse speichern** und einen nur für Administratoren zugänglichen
   Ausgabeordner wählen.
2. **Erstellen → Geplante Aufgabe → Benutzerdefiniertes Skript** wählen.
   Einen Namen wie `KitaFenster Benutzerkennung` vergeben und als Benutzer das
   oben gewählte NAS-Konto auswählen. Keine wiederkehrende Ausführung einrichten.
3. Unter **Aufgabeneinstellungen → Benutzerdefiniertes Skript** nur `id` eintragen.
4. Speichern, die Aufgabe markieren und **Ausführen** wählen. Danach unter
   **Aktion → Ergebnis anzeigen** die Ausgabe ansehen und die Aufgabe deaktivieren
   oder entfernen.

Beispielausgabe: `uid=1026(admin) gid=100(users) groups=100(users),101(administrators)`.
`1026` ist hier die UID, `100` die Hauptgruppen-GID. Diese Zahlen sind nur ein
Beispiel; verwendet die Werte eures NAS. Eine zusätzliche Gruppenkennung ist nur
nötig, wenn der Dateizugriff von dieser Gruppe abhängt.
Das Verfahren zum Ausführen und Anzeigen von Aufgabenergebnissen ist in der
[Synology-Anleitung zum Aufgabenplaner](https://kb.synology.com/en-global/DSM/tutorial/inconsistent_file_list_between_Drive_File_Station)
beschrieben; hier wird ausschließlich die Benutzerkennung abgefragt.

## 3. .env im DSM bearbeiten

Pfade, Kennungen und Web-Zugangsdaten anpassen. Die Versionsnummer aus dem gewählten
Paket übernehmen; in `.env` steht sie **ohne** führendes `v`.

```dotenv
KITAFENSTER_IMAGE=ghcr.io/aldevelope-code/kitafenster
KITAFENSTER_VERSION=VERSION
NAS_PATH=/volume1/Kita-Bilderrahmen
DATA_PATH=/volume1/docker/kitafenster/data
NAS_UID=1026
NAS_GID=100
NAS_READ_GID=
BIND_ADDRESS=0.0.0.0
COOKIE_SECURE=false
ADMIN_USERNAME=admin
ADMIN_PASSWORD='dein eigenes Passwort'
```

| Variable | Bedeutung |
|---|---|
| `NAS_UID`, `NAS_GID` | Kennungen des NAS-Kontos aus Abschnitt 2; die Vorgabe `10001` ist kein allgemein gültiges Synology-Konto |
| `NAS_READ_GID` | Zusätzliche Gruppe für Dateirechte; sonst leer lassen |
| `NAS_PATH` | Stamm der Bilderfreigabe, kein einzelner Gruppenordner und kein Windows-Netzwerkpfad |
| `DATA_PATH` | Beschreibbarer Anwendungsordner; bei Updates denselben Pfad beibehalten |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Anmeldung auf der KitaFenster-Webseite, unabhängig vom DSM-Konto |

Das Konto, mit dem ihr das DSM-Projekt anlegt, wird nicht automatisch zum
Containerbenutzer. Die Compose-Datei verwendet die Kennungen aus `.env` bereits;
keine weiteren `user`- oder `group_add`-Zeilen ergänzen. Bei leerem `NAS_READ_GID`
wird die Hauptgruppe verwendet.

Einfache Anführungszeichen erhalten `$` und `#` im Passwort. Ein enthaltenes
Apostroph wird als `\'` geschrieben. `ADMIN_PASSWORD` muss für die erste Anmeldung
gesetzt sein. Ohne diese Variable bleibt bei späteren Starts das bestehende
Webkonto erhalten. Die leere Zeile `ADMIN_PASSWORD:` in Compose übernimmt den
Wert aus `.env`; das Passwort dort nicht zusätzlich eintragen.
[Docker erläutert die Verarbeitung der .env-Datei](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/).

## 4. Projekt KitaFenster im Container Manager anlegen

1. **Container Manager → Projekt → Erstellen** öffnen.
2. Als Projektnamen `kitafenster` verwenden. Bei einem vorhandenen Projekt
   **dessen Namen beibehalten** und kein zweites Projekt anlegen.
3. Als **Pfad** `/volume1/docker/kitafenster` auswählen: genau den Ordner mit
   `.env` und der Compose-Datei.
4. Als Quelle die vorbereitete `compose.yaml` importieren. Wenn DSM eine
   hochzuladende Datei verlangt, dieselbe Datei vom heruntergeladenen Paket
   auswählen. Im YAML-Editor keine zweite, abweichende Konfiguration anlegen.
5. Ein zusätzliches Web-Station-Portal ist für den direkten Zugriff über Port
   `8088` nicht nötig. Den Assistenten abschließen und das Projekt starten lassen.
6. Im Projekt den Abschluss der Erstellung und den Containerstatus prüfen.
   Das benötigte Image wird aus der in `.env` angegebenen Registry geladen.

DSM kann die importierte YAML als **docker-compose.yml** im Projektordner
verwalten. Maßgeblich ist danach die Konfiguration unter
**Projekt → Details → YAML-Konfigurationen**. Wenn dort Änderungen nötig sind,
diese dort bearbeiten und übernehmen; eine Änderung an einer ungenutzten Kopie
`compose.yaml` wirkt sich nicht auf das Projekt aus. Die `.env` bleibt im
Projektpfad. Die aktiven YAML-Einstellungen auch bei Sicherungen berücksichtigen.
Die [Synology-Projekthilfe](https://kb.synology.com/en-global/DSM/help/ContainerManager/docker_project)
beschreibt Projektpfad, YAML-Editor und Projektaktionen. Die Beschriftungen können
je nach Sprache und Container-Manager-Ausgabe leicht abweichen.

## 5. Anwendung prüfen und Inhalte einrichten

`http://NAS-IP:8088` öffnen und mit den Web-Zugangsdaten aus `.env` anmelden.
Die laufende Serverversion steht in der Fußzeile und unter **Einrichtung → Softwareversion**.
Unter **Gruppen & NAS** die Fotoordner zuweisen und **NAS abgleichen** wählen.
Mit den Testdaten `Gruppe 1`, `Gruppe 2` und `Gruppe 3` verwenden; erwartet werden
jeweils **3 Fotos**. Erst nach erfolgreichem Abgleich den Pi koppeln.

PDFs werden separat unter **Inhalte → Dokument (PDF) hochladen** aufgenommen.
Die Testdateien `Gruppe N/Infos/Elternplan.pdf` ergeben je zwei Seiten. Anschließend
am Rahmen direkt auswählen oder in die **Dokumentenliste** für alle beziehungsweise
ausgewählte Gruppen aufnehmen. Neue Dokumente sind öffentlich; bei internen
Unterlagen **Dieses Dokument ist nur für interne Zwecke** aktivieren.

Fotos, Dokumente, Meldungen, Betriebszeiten und Rahmen verwaltet ihr auf der
**KitaFenster-Webseite**. Containerstatus, Neustarts, Konfiguration, Sicherungen
und Imagewechsel erfolgen über **DSM**. Details: [Bedienung](BEDIENUNG.md) und
[Betrieb und Updates](BETRIEB.md).

## HTTPS

Für HTTPS den DSM-Reverse-Proxy vom eigenen HTTPS-Hostnamen auf
`http://127.0.0.1:8088` richten und ein auf PCs und Pis vertrauenswürdiges Zertifikat
verwenden. Bei einer auf die NAS-LAN-IP begrenzten `BIND_ADDRESS` auch das Proxy-Ziel
auf diese IP setzen. In `.env` `COOKIE_SECURE=true` setzen und das
[Projekt mit den geänderten Einstellungen neu erstellen](BETRIEB.md#konfiguration-übernehmen).
Upload-Limit mindestens 41 MB und ausreichend Zeit für PDF-Verarbeitung vorsehen.
Die Pi-Kopplung verwendet dieselbe HTTPS-Adresse. Externer Zugriff erfolgt über VPN.

## Wenn etwas nicht funktioniert

Zuerst **Container Manager → Projekt → Details** und beim zugehörigen Container
**Details → Protokoll** prüfen. Bei `Permission denied` Dateirechte und Kennungen
abgleichen; bei fehlendem Marker Pfad und Ordnerstruktur prüfen. Die weitere
[Fehlersuche mit optionalem SSH-Zugriff](NAS-FEHLERSUCHE.md) beschreibt gezielte Prüfungen.
