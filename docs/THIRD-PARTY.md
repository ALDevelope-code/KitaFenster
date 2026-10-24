# Drittanbieter und Lizenzen

Die AGPL-Lizenz von KitaFenster ändert nicht die Lizenzen seiner Bibliotheken.
Der Quellcode-Download bündelt keine installierten Python-Bibliotheken oder
Betriebssystempakete. Diese werden durch pip bzw. apt installiert.

Die direkten Laufzeitabhängigkeiten sind unten aufgeführt. Die festgelegten
Paketversionen des Servers stehen in `requirements-server.txt`; die Pi-Installation nutzt
die Paketversionen der Betriebssystemquellen.

| Paket | Lizenz / Quelle |
|---|---|
| FastAPI | [MIT](https://github.com/fastapi/fastapi/blob/master/LICENSE) |
| Uvicorn | [BSD-3-Clause](https://github.com/Kludex/uvicorn/blob/main/LICENSE.md) |
| Pillow | [MIT-CMU](https://github.com/python-pillow/Pillow/blob/main/LICENSE) |
| pypdfium2 | [Apache-2.0 / BSD-3-Clause und Abhängigkeitslizenzen](https://github.com/pypdfium2-team/pypdfium2#licensing) |
| python-multipart | [Apache-2.0](https://github.com/Kludex/python-multipart/blob/master/LICENSE.txt) |
| tzdata | [Apache-2.0; IANA-Datenbank gesondert](https://github.com/python/tzdata/blob/master/LICENSE) |
| Pygame | [LGPL; mitgelieferte Komponenten gesondert](https://www.pygame.org/docs/) |

Das ist eine Übersicht der direkten Abhängigkeiten, kein vollständiges
Lizenzinventar eines fertigen Images. PDFium, SDL, Schriften, indirekte
Python-Abhängigkeiten und Betriebssystempakete bringen weitere Hinweise mit.
Bei Weitergabe eines Images die dort tatsächlich enthaltenen Lizenztexte,
Copyright-Hinweise und gegebenenfalls erforderlichen Quellcodeangebote
erhalten bzw. mitliefern. Für Pygame gilt insbesondere dessen LGPL; unverändert
eingesetztes Pygame erzwingt laut Projektdokumentation keine einheitliche Lizenz
für das gesamte aufrufende Programm. Die Pi-Installation nutzt die Pakete des
Betriebssystems, deren Versionen von der lokalen Testumgebung abweichen können.

Für die optionale Bewegungserkennung und HDMI-Abschaltung installiert der
Pi-Installer zusätzlich die OS-Pakete `python3-gpiozero`, `python3-lgpio` und
`libdrm2`. Diese werden ebenfalls nicht im Quellcode-ZIP gebündelt. Die zu den
installierten Versionen gehörenden Lizenzhinweise stehen auf dem Pi unter
`/usr/share/doc/` in den jeweiligen Paketverzeichnissen.
