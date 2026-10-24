# Zu KitaFenster beitragen

Danke für das Interesse an KitaFenster. Besonders hilfreich sind reproduzierbare
Fehlerberichte, Rückmeldungen aus echten Testinstallationen, Verbesserungen der
Anleitungen und kleine, klar abgegrenzte Pull Requests.

## Vor einem Beitrag

- Für Fehler und überschaubare Wünsche eine passende Issue-Vorlage verwenden.
- Größere Funktionsänderungen zuerst als Issue beschreiben, damit Ziel,
  Datenschutzfolgen und Bedienkonzept abgestimmt werden können.
- Keine echten Kinderfotos, Namen, Zugangsdaten, Datenbanken, Sicherungen oder
  Protokolle mit personenbezogenen Angaben veröffentlichen. Für Beispiele stehen
  die neutralen Daten unter `testdaten/` zur Verfügung.
- Sicherheitsprobleme nicht öffentlich erläutern, sondern nach
  [SECURITY.md](SECURITY.md) melden.

## Entwicklungsumgebung

Vorausgesetzt werden Python 3.11 oder neuer und Node.js für die UI-Tests.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-server.txt
.\.venv\Scripts\python.exe -m pip install -e '.[player,test]'
.\tools\kitafenster-starten.bat
```

Die lokale Demo verwendet ausschließlich ignorierte Verzeichnisse. Änderungen an
produktiven Daten einer Einrichtung sind keine geeignete Testumgebung.

## Prüfungen

Vor einem Pull Request mindestens die zum geänderten Bereich passenden Tests
ausführen. Der vollständige Python-Prüflauf ist:

```powershell
.\.venv\Scripts\python.exe -m ruff check server player shared tests tools
.\.venv\Scripts\python.exe -m ruff format --check server player shared tests tools
.\.venv\Scripts\python.exe -m pytest -q
```

Zusätzliche JavaScript-, Shell-, Container- und Standortprüfungen beschreibt
[docs/TESTS.md](docs/TESTS.md). Dieselben zentralen Prüfungen laufen auch in
GitHub Actions.

## Pull Requests

- Änderungen klein und thematisch zusammengehörig halten.
- Verhalten und Motivation verständlich beschreiben.
- Tests und Anleitungen gemeinsam mit dem Verhalten aktualisieren.
- Neue Konfigurationswerte in `.env.example` und den Installationsanleitungen
  dokumentieren; niemals Geheimnisse einchecken.
- Abhängigkeiten nur hinzufügen, wenn ihr Nutzen den zusätzlichen Wartungs- und
  Sicherheitsaufwand rechtfertigt.
- Bestehende Lizenzhinweise und Drittanbieter-Lizenzen beachten.

Mit einem Beitrag erklärst du, dass du ihn unter der Projektlizenz
`AGPL-3.0-only` bereitstellen darfst.
