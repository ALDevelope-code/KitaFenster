# Freie Weiterentwicklung

KitaFenster steht unter der **GNU Affero General Public License, Version 3**
(`AGPL-3.0-only`). Maßgeblich ist der vollständige Text in [LICENSE](../LICENSE).
Der Projekthinweis steht in [NOTICE](../NOTICE).

Copyright (C) 2026 Andy Lungfiel (ALDevelope-code).

Die Anwendung darf genutzt, verändert und weitergegeben werden, auch kommerziell.
Bei Weitergabe abgeleiteter Programmversionen gelten die Copyleft- und
Quellcodepflichten der AGPL. Wer eine modifizierte Version über ein Netzwerk
nutzbar macht, muss den damit interagierenden Nutzern den zugehörigen Quellcode
unter dieser Lizenz anbieten (§ 13). Eine allgemeine Veröffentlichung jeder rein
privaten Änderung gegenüber der ganzen Welt verlangt die Lizenz nicht.

Die Weboberfläche verlinkt bereits vor der Anmeldung auf **Lizenz** und
**Quellcode**. `/api/source` erstellt ein ZIP aus dem aktuellen Quellbaum dieser
Installation. Es enthält Programmdateien, Lizenz, Installationsskripte und
Anleitungen; Datenbank, hochgeladene Logos, Fotos und Zugangsdaten sind nicht
Bestandteil. Der Server wird deshalb aus dem vollständigen Projektordner bzw.
dem mitgelieferten Dockerfile betrieben, nicht aus einem isolierten Python-Wheel.

Bei Erweiterungen neue Quellformate oder zusätzliche Build-Dateien in
`shared/source.py` aufnehmen. Betriebseinstellungen gehören in `.env` bzw.
`DATA_DIR`, niemals als Geheimnisse in Programmdateien. Der Quellcode-Download
ist absichtlich ohne Anmeldung verfügbar. Er ersetzt keine gegebenenfalls
zusätzlichen Pflichten beim Weitergeben von angepassten Abhängigkeiten,
fertigen Container-Images oder Raspberry-Pi-Systemabbildern.

Eigene Kita-Logos, Bilder, Pläne und Texte sind **Inhalte der jeweiligen
Einrichtung**. Der Upload legt keine Open-Source-Lizenz für diese Inhalte fest.
Das mitgelieferte neutrale SVG-Beispiel gehört dagegen zum AGPL-Projekt.
Das gilt ebenso für die von diesem Projekt erstellten Screenshots, synthetischen
Testdaten sowie CAD- und Druckdateien unter `hardware/gehaeuse/`. Diese
separaten Repository-Dateien gehören nicht zum Quellcode-ZIP des laufenden
Servers; sie stehen im Git-Repository bereit.
Die Lizenzen der Bibliotheken bleiben bestehen; siehe [Drittanbieter](THIRD-PARTY.md).

Quellen: [AGPLv3 bei SPDX](https://spdx.org/licenses/AGPL-3.0-only.html),
[Open Source Definition](https://opensource.org/osd).
