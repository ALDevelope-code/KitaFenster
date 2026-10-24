# Sicherheit

## Unterstützte Versionen

Sicherheitskorrekturen werden für das jeweils aktuelle veröffentlichte Release
und den aktuellen Entwicklungsstand vorgenommen. Ältere Installationen sollten
vor einer Meldung anhand der [Betriebsanleitung](docs/BETRIEB.md) aktualisiert
werden, sofern dies ohne Verlust wichtiger Beweise möglich ist.

## Sicherheitsproblem melden

Bitte Schwachstellen nicht mit technischen Details, Zugangsdaten oder echten
Kita-Inhalten in einer öffentlichen Issue veröffentlichen.

1. Wenn im GitHub-Reiter **Security** die private Meldung einer Schwachstelle
   angeboten wird, diesen Weg verwenden.
2. Ist dort keine private Meldung möglich, eine öffentliche Issue nur mit dem
   Hinweis eröffnen, dass ein vertraulicher Kontaktweg benötigt wird. Noch keine
   Exploit-Details, Protokolle oder personenbezogenen Daten anhängen.
3. Betroffene Version, Komponente und mögliche Auswirkung möglichst genau nennen,
   sobald ein vertraulicher Kanal besteht.

Eine erste Eingangsbestätigung und Einschätzung erfolgt nach verfügbarer
Maintainer-Zeit. Es besteht kein Anspruch auf eine bestimmte Reaktionszeit.

## Betriebshinweise

- Die Webverwaltung nur in vertrauenswürdigen Netzen oder hinter einem korrekt
  eingerichteten HTTPS-Reverse-Proxy betreiben.
- Ein individuelles Administratorpasswort setzen und Demo-Zugangsdaten niemals
  in einer produktiven Installation verwenden.
- NAS-, DSM- und Raspberry-Pi-Systeme regelmäßig aktualisieren.
- Datenverzeichnis und aktive Container-Konfiguration nach der
  [Betriebsanleitung](docs/BETRIEB.md) sichern.
- Player nicht direkt aus dem Internet erreichbar machen.
- Vor dem Teilen von Diagnoseinformationen Namen, IP-Adressen, Gerätekennungen
  und Pfade prüfen und bei Bedarf anonymisieren.
