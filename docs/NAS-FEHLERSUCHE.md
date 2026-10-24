# NAS-Fehlersuche: DSM zuerst, SSH bei Bedarf

Installation, Start, Sicherung und Imagewechsel erfolgen über DSM; siehe
[NAS-Installation](INSTALLATION-NAS.md) und [Betrieb](BETRIEB.md).
Diese Anleitung ist für die gezielte Fehlersuche gedacht. Sie startet kein
zweites Compose-Projekt und ersetzt nicht die Projektverwaltung im Container Manager.

## Zuerst im DSM prüfen

1. **Container Manager → Projekt** öffnen: Ist das vorhandene KitaFenster-Projekt
   gestartet oder ist die Erstellung fehlgeschlagen? Die Ausgabe des fehlgeschlagenen
   Vorgangs lesen.
2. Den zugehörigen Container unter **Container** beziehungsweise den Projektdetails
   öffnen und **Protokoll** ansehen. Image-Adresse und Versions-Tag mit `.env` abgleichen.
3. In **File Station** prüfen, ob `.env` im richtigen Projektpfad liegt, `DATA_PATH`
   und `NAS_PATH` existieren und die Markerdatei direkt in der Bilderquelle liegt.
4. Auf der KitaFenster-Webseite **Gruppen & NAS → NAS abgleichen** ausführen und
   den dort gemeldeten Fehler lesen. Unter **Einrichtung → Softwareversion**
   den tatsächlich laufenden Serverstand prüfen.

| Problem | Nächster Schritt |
|---|---|
| Container beendet sich oder startet wiederholt | Containerprotokoll lesen; häufig sind Datenpfad oder Schreibrechte die Ursache. |
| `Permission denied` unter `/nas` | UID/GID, benötigte Zusatzgruppe und DSM-Leserechte bis zur betroffenen Datei prüfen. |
| `Permission denied` unter `/data` | Besitzer und Schreibrechte des Datenordners einschließlich vorhandener Dateien prüfen. |
| Marker oder Gruppenordner fehlt | Den eingebundenen Stammordner prüfen; `.bilderrahmen-source` liegt direkt darin. |
| `.env`-Änderung hat keine Wirkung | Projektpfad prüfen und [Konfiguration neu übernehmen](BETRIEB.md#konfiguration-übernehmen); Neustart allein genügt nicht. |
| Nach Update wird dieselbe Version angezeigt | Tag in `.env`, aktive YAML und Image des Containers vergleichen; Projekt neu erstellen, Browser mit Strg+F5 laden. |
| `unauthorized` beim Image-Download | Zugriff auf das GitHub-Paket prüfen; ein öffentliches Repository macht dessen Container-Paket nicht automatisch öffentlich. |
| `manifest unknown` / `no matching manifest` | Veröffentlichte Version ohne `v`, korrekte Image-Adresse und AMD64-NAS prüfen. |
| Lesetest erfolgreich, NAS-Abgleich fehlerhaft | Gruppenpfad, Format, Größe und beschädigte Bilddateien prüfen. |
| Port 8088 belegt | Andere Container/DSM-Dienste mit dieser Portbelegung prüfen; keinen zweiten KitaFenster-Container starten. |

## Optional per SSH untersuchen

Falls die DSM-Protokolle nicht ausreichen, SSH vorübergehend unter
**Systemsteuerung → Terminal & SNMP → Terminal** aktivieren und vom PC verbinden:

```powershell
ssh admin@NAS-IP
```

`admin` ist ein Beispielname für euer NAS-Administrationskonto; diesen Namen
und `NAS-IP` durch die eigenen Werte ersetzen. Danach auf dem NAS die Containernamen ablesen:

```bash
sudo docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
```

Den Namen des zum DSM-Projekt gehörenden Containers einsetzen, nicht den
Projektnamen oder einen geratenen Namen. Die folgenden Befehle ändern weder
Projektdefinition noch laufende Image-Version:

```bash
CONTAINER='Name-des-KitaFenster-Containers'
sudo docker logs --tail=100 "$CONTAINER"
sudo docker inspect --format '{{.Config.Image}}' "$CONTAINER"
sudo docker inspect --format '{{range .Mounts}}{{.Source}} -> {{.Destination}} (RW={{.RW}}){{println}}{{end}}' "$CONTAINER"
```

Bei einem **laufenden Container** zusätzlich:

```bash
sudo docker exec "$CONTAINER" id
sudo docker exec "$CONTAINER" python -m tools.check_nas
```

Der Test liest Marker und Bild-/PDF-Dateien in `Gruppe 1` bis `Gruppe 3` und
prüft `/data` mit einer automatisch entfernten Testdatei. Mit den Testdaten
sind je Gruppe vier Dateien lesbar. Das ist ein Dateirechtetest; der anschließende
NAS-Abgleich verarbeitet daraus je drei Fotos. Bei anderen Gruppenordnern:

```bash
sudo docker exec "$CONTAINER" python -m tools.check_nas 'Sterne' 'Sonne'
```

Die Benutzerkennung des gewählten NAS-Kontos lässt sich zusätzlich mit
`id admin` vergleichen; dabei den tatsächlichen Kontonamen verwenden.
Der Test läuft mit dem Containerbenutzer, nicht als Root im Container.

## Dateirechte korrigieren

Vor Änderungen an vorhandenen Anwendungsdaten das Projekt in DSM stoppen und
[sichern](BETRIEB.md#nas-sichern-und-wiederherstellen). In File Station den Besitzer
und Lese-/Schreibzugriff des Datenordners einschließlich Unterordnern und Dateien
auf das in `.env` gewählte NAS-Konto setzen. Für die Bilderquelle reicht Leserecht.
Abweichende Rechte vorhandener Dateien, Verweigern-Einträge und übergeordnete
Ordner berücksichtigen. Keine Datenordner löschen, um einen Rechtefehler zu umgehen.

Falls UID/GID oder Zusatzgruppe geändert wurden, das Projekt über DSM
[neu erstellen](BETRIEB.md#konfiguration-übernehmen). Danach den Test und den
NAS-Abgleich wiederholen. Die Zuordnungen und Pi-Kopplungen liegen weiterhin im
unverändert eingebundenen Datenordner.

## Docker-Netzadresspool erschöpft

Bei der entsprechenden Fehlermeldung vorhandene Netze und NAS-Routen ablesen:

```bash
sudo docker network inspect --format '{{.Name}}: {{range .IPAM.Config}}{{.Subnet}} {{end}}' $(sudo docker network ls -q)
ip -4 route
```

Nur ein nachweislich freies, nicht mit Docker, LAN oder VPN überlappendes Netz
verwenden. Falls beispielsweise `10.240.10.0/24` frei ist, im **YAML-Editor des
bestehenden DSM-Projekts** auf oberster Ebene ergänzen:

```yaml
networks:
  default:
    ipam:
      config:
        - subnet: 10.240.10.0/24
```

Netze anderer Projekte nicht löschen. Die Änderungen über DSM übernehmen und
bei späteren Updates beibehalten. Kann ein bereits vorhandenes Projektnetz nicht
angepasst werden, zuerst die Fehlermeldung und dessen Nutzung klären.

Nach Abschluss der Fehlersuche SSH wieder deaktivieren, wenn es sonst nicht
benötigt wird. Keine vollständige `.env`, Passwörter oder Gerätetokens als
Diagnose veröffentlichen.
