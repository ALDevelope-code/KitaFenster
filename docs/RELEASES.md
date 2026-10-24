# Projektversion und Releases

Der Workflow `.github/workflows/container.yml` prüft das Projekt, baut ein
Linux/AMD64-Image und veröffentlicht bei einem stabilen Release das geprüfte
Image plus Installationspakete. Er installiert nichts automatisch auf NAS oder Pi.

## Auslöser

| Aktion | Ergebnis |
|---|---|
| Push auf einen Branch / Pull Request | Tests, Syntax-/Formatprüfungen, Container-Build und Funktionstest |
| Actions → Test and release → Run workflow | Dieselben Prüfungen, keine Veröffentlichung |
| Stabiles GitHub-Release veröffentlichen | Prüfungen, danach Image zu GHCR und ZIPs zum Release |
| Release-Entwurf | Kein Lauf |
| Prerelease | Prüfungen, keine Image-/ZIP-Veröffentlichung |

Der Container-Funktionstest prüft Anmeldung, Fotoimport, Quellcodeangebot und
Datenbestand nach Neustart. Erst wenn alle Jobs erfolgreich sind, ist das
Release vollständig. **Ein Push allein aktualisiert kein veröffentlichtes Image.**

## Neue Version erstellen

Im Projektordner die gewünschte Versionsnummer im Format `X.Y.Z` ohne `v`
eingeben und alle Versionsangaben gemeinsam setzen:

```powershell
$ReleaseVersion = Read-Host "Neue Projektversion (drei Zahlen, durch Punkte getrennt)"
python -m tools.release_info --set $ReleaseVersion
```

Das Werkzeug benötigt Python ab 3.11, keine zusätzlichen Pakete. Mit der
Projektumgebung funktioniert auch
`.\.venv\Scripts\python.exe -m tools.release_info --set $ReleaseVersion`.

Es prüft zunächst, ob jede Fundstelle genau einmal vorhanden ist, und ersetzt
dann nur die Versionswerte. Unterschiedliche bisherige Versionswerte werden
dabei vereinheitlicht. Zeilenenden und übrige Dateiinhalte bleiben erhalten.
Ein erneuter Aufruf mit derselben Nummer ist möglich.

Automatisch aktualisiert werden:

| Datei | Angabe |
|---|---|
| `pyproject.toml` | `version` unter `[project]` |
| `README.md` | Angezeigte Projektversion im Quellcode |
| `.env.example` | `KITAFENSTER_VERSION` |
| `compose.yaml` | Fallback in `${KITAFENSTER_VERSION:-…}` |
| `Dockerfile` | `ARG APP_VERSION` |
| `server/app.py` | Serverversion in `/api/health` und der Weboberfläche |

Aktuelle Version anzeigen und Übereinstimmung prüfen:

```powershell
python -m tools.release_info
python -m tools.release_info --check
```

GitHub Actions prüft die Übereinstimmung ebenfalls bei jedem Lauf. Der Befehl
ändert den Quellstand; Commit, Push und Veröffentlichung folgen anschließend.
Die eigene `.env` auf dem NAS wird erst nach erfolgreicher Veröffentlichung
über File Station auf die neue Image-Version umgestellt. Danach das bestehende
Projekt im DSM Container Manager neu erstellen und starten, siehe
[NAS aktualisieren](BETRIEB.md#nas-aktualisieren).

1. Änderungen prüfen, committen und pushen. Keine `.env`, `player.json`,
   Betriebsdaten oder eigenen Logos aufnehmen. `git status --short` und
   `git diff --cached` vor dem Commit ansehen.
2. Den Workflow des gewünschten Commits abwarten.
3. **Releases → Draft a new release**: neuen Tag **vVERSION** anlegen und den
   geprüften Commit/Branch auswählen. Der Tag muss exakt `v` plus Projektversion sein.
4. Versionshinweise eintragen, nicht als Prerelease markieren, veröffentlichen.
5. Den erfolgreichen Abschluss einschließlich Veröffentlichung abwarten.

Veröffentlichte Tags nicht auf andere Commits verschieben. Jedes Release
enthält den Quellstand seines Tags. Es gibt keinen automatisch
wechselnden `latest`-Tag; die `.env` des NAS legt dessen Version fest.

## Dateien im Release

- `ghcr.io/aldevelope-code/kitafenster:VERSION`: NAS-Image.
- `kitafenster-VERSION.zip`: vollständiger Quellcode einschließlich Pi-Installer,
  KMS/DRM-Dienst und Anleitungen.
- `kitafenster-nas-VERSION.zip`: Compose, `.env.example`, `pruefe-nas.py`,
  Kurzanleitung und weitere Anleitungen unter `docs/`, Lizenzhinweise.
- `SHA256SUMS`: Prüfsummen der ZIP-Dateien.

Die fiktiven Testbilder/PDFs liegen separat unter `testdaten` im Repository;
Betriebsdaten werden nicht mit verpackt. Auf einem Fork setzt der Workflow die
Image-Adresse im NAS-Paket auf dessen Namensraum.

## GitHub einmalig einrichten

Actions müssen im Repository erlaubt sein. Der Release-Job nutzt `GITHUB_TOKEN`
mit `packages: write` und `contents: write`; NAS-Zugangsdaten benötigt GitHub nicht.
Die Workflow-Datei muss im Standardbranch liegen, damit **Run workflow** verfügbar ist.

Unter **Packages → kitafenster → Package settings → Change visibility** das Paket
auf **Public** stellen, wenn es ohne GitHub-Anmeldung heruntergeladen werden soll.
Die Veröffentlichung des Repositorys allein ändert die Paket-Sichtbarkeit nicht.

Bei **Queued / Waiting for a runner** hat noch kein Test begonnen: Runner-
Verfügbarkeit, [GitHub-Status](https://www.githubstatus.com/) und die Actions-
Einstellungen prüfen. Bei einem vorübergehenden Registry-/Netzwerkfehler den
fehlgeschlagenen Lauf wiederholen. Dabei denselben unveränderten Commit verwenden.

## Lokal prüfen und paketieren

```powershell
.\.venv\Scripts\python.exe -m tools.release_info
.\.venv\Scripts\python.exe -m tools.package_release
docker compose --env-file .env.example config --quiet
```

Die Projektprüfungen stehen unter [Tests](TESTS.md). Der Container-Test braucht
eine laufende Docker-Engine mit Linux-Containern:

```powershell
docker build --platform linux/amd64 -t kitafenster:checked .
.\.venv\Scripts\python.exe -m tools.smoke_container kitafenster:checked
```

Auf NAS/Pi anschließend die [Update-Anleitung](BETRIEB.md) verwenden. Bei reinen
Dokumentationsänderungen muss eine funktionierende Installation nicht neu aufgesetzt werden.
