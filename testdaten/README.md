# Testdaten für Gruppe 1 bis Gruppe 3

Dieser Ordner enthält vollständig erfundene Elterninfos und beschriftete
Testbilder. Ihr könnt ihn zum Ausprobieren der NAS-Zentrale und der Pi-Anzeige
verwenden. Die Beispieldateien enthalten keine echten Personen oder Termine.

## Inhalt

Jede Gruppe hat einen **zweiseitigen Elternplan im Bildschirmformat 16:9**:
eine Wochenübersicht und eine Seite mit Elterninfos. Die Gruppen unterscheiden
sich in Farbe und Thema:

| Gruppenordner | Farbe | Thema | PDF-Datei relativ zum Gruppenordner |
|---|---|---|---|
| `Gruppe 1` | Grün | Wald & Farben | `Infos/Elternplan.pdf` |
| `Gruppe 2` | Blau | Bauen & Forschen | `Infos/Elternplan.pdf` |
| `Gruppe 3` | Orange | Musik & Bewegung | `Infos/Elternplan.pdf` |

Zusätzlich liegen in jedem Unterordner `Bilder` drei JPG-Testbilder:

| Datei | Auflösung | Testzweck |
|---|---|---|
| `01-Querformat.jpg` | 1920 × 1080 | Querformat und Gruppenzuordnung |
| `02-Hochformat.jpg` | 1080 × 1920 | Hochformat und Bildbeschnitt |
| `03-Quadrat.jpg` | 1200 × 1200 | Seitenverhältnis und Ränder |

Alle Bilder tragen eine Gruppennummer und Eckmarkierungen. Bei **Ganzes Bild**
müssen alle vier Ecken sichtbar sein; bei **Bildschirm füllen** dürfen je nach
Bildschirmformat Teile der Ränder abgeschnitten werden. Es sind Testgrafiken,
keine Fotografien.

```text
testdaten/
  .bilderrahmen-source
  README.md
  Gruppe 1/
    Bilder/
      01-Querformat.jpg
      02-Hochformat.jpg
      03-Quadrat.jpg
    Infos/
      Elternplan.pdf
  Gruppe 2/                 # gleicher Aufbau
  Gruppe 3/                 # gleicher Aufbau
```

## Auf dem NAS ausprobieren

1. Die drei Gruppenordner und die Datei `.bilderrahmen-source` mit **DSM File Station**
   direkt in die Bilderfreigabe hochladen, beispielsweise `/volume1/Kita-Bilderrahmen`.
   Keinen zusätzlichen Ordner `testdaten` dazwischenschieben. Vorhandene eigene
   Dateien gleichen Namens nicht ersetzen. Die [NAS-Anleitung](../docs/INSTALLATION-NAS.md)
   erklärt Projektordner, Dateirechte und Einrichtung im Container Manager.
2. Auf der KitaFenster-Webseite unter **Gruppen & NAS → Gruppe bearbeiten** den
   Fotoordner auf `Gruppe 1`, `Gruppe 2` beziehungsweise `Gruppe 3` setzen.
   `Bilder` wird als Unterordner mitgelesen. **NAS abgleichen** wählen;
   erwartet werden pro Gruppe **3 Fotos**.
3. Die jeweilige `Infos/Elternplan.pdf` unter **Inhalte → Dokument (PDF) hochladen**
   separat hochladen. Die Vorschau enthält zwei Seiten. Für diese fiktiven
   Elterninformationen **Dieses Dokument ist nur für interne Zwecke** ausgeschaltet
   lassen; **Interne Inhalte zulassen** am Elternrahmen bleibt ebenfalls aus.
4. Unter **Inhalte** das Dokument über **Dokumentenliste** für die gewünschte
   Gruppe oder alle Gruppen aufnehmen. Den Bilderrahmen einer Gruppe zuordnen.
5. Beim Rahmen unter **Verwalten → Hauptanzeige · Standardinhalt** den Modus
   **Gemischt** und Einträge für Fotos sowie die Dokumentenliste wählen.
   Alternativ ein Dokument direkt auswählen. Für diesen Test die Betriebszeiten
   freigeben, eine manuelle Umschaltung auf **Automatisch** zurücksetzen und
   übersteuernde Inhaltszeitfenster beachten.

Die Dokumentenliste kann auch für die zusätzliche Anzeige verwendet werden.
Die PDFs werden nicht automatisch durch den Foto-Abgleich in die Liste aufgenommen.

## Test abschließen

Die kopierten Testbilder und Test-PDFs gezielt mit File Station aus den
Gruppenordnern entfernen und erneut abgleichen. Hochgeladene Testdokumente zusätzlich
unter **Inhalte** entfernen und dabei gegebenenfalls das Lösen ihrer Zuordnungen
bestätigen. Die Datei `.bilderrahmen-source` bleibt im NAS-Stammordner.
Bei echten Dokumenten die Kennzeichnung für interne Inhalte bewusst wählen.

Die Beispieldaten gehören zum Repository. Der automatisch erzeugte
Quellcode-Download und die Installationspakete enthalten diesen separaten
Testdatenordner derzeit nicht.
