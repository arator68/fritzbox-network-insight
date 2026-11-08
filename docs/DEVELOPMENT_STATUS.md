# Entwicklungsstand – FRITZ!Box Network Insight

**Stand:** 2026-11-08 (rekonstruiert aus dem letzten Entwicklungsdialog und GitHub)  
**Status:** Laufende Entwicklung; keine Release- oder Merge-Freigabe  
**Verbindliche Anforderungen:** [SPECIFICATION.md](SPECIFICATION.md)  
**Repository:** https://github.com/arator68/fritzbox-network-insight  
**Aktueller Arbeitsbranch:** `feature/avm-mesh-topology`  
**Pull Request:** [#32 – Add automatic AVM Mesh observations to Network Insight](https://github.com/arator68/fritzbox-network-insight/pull/32) → `develop`

> **Zweck:** Diese Datei dokumentiert den tatsächlichen Arbeitsstand und die nächsten Schritte für die Fortsetzung in einem neuen Chat. Sie ergänzt die Spezifikation, ersetzt sie nicht. Angaben aus dem früheren Chat sind als solche gekennzeichnet; sie sind nicht automatisch durch CI oder Quellcode verifiziert.

## 1. Zuletzt bestätigter Stand

- PR #32 ist ein **offener Draft-PR** auf `develop` (GitHub-Prüfung vom 08.11.2026; zuletzt bekannter Head: `cc758affff79c89b67017813729d85b52013577b`).
- Der PR umfasst die AVM-Mesh-Erfassung sowie weitere Arbeiten an Topologie, FDB-Portgruppen, Geräteverbindungen, Port-Historie, manuellen Verbindungen, Sensoren und Tests.
- **Rückmeldung aus dem vorherigen Chat:** Tests waren grün; der Entwicklungsstand wurde in Home Assistant installiert und Home Assistant neu gestartet. Die konkreten Testergebnisse und der installierte Commit sollten bei Bedarf erneut mit CI/Installation abgeglichen werden.
- **Nicht bestätigt:** Dass die automatisch erzeugte Topologie die unten beschriebene reale Verkabelung bereits korrekt als Netzwerkzweig darstellt. **PR #32 nicht allein aufgrund grüner Tests mergen.**
- Die PR-Beschreibung enthält noch den älteren Hinweis „Not yet tested on actual FRITZ!Box“; dieser Text ist gegenüber den späteren Nutzertests nicht mehr aktuell und sollte vor dem Merge überprüft werden.

## 2. Reale Netzwerktopologie – bestätigte Testkonstellation

Vom Nutzer bestätigte physische Verkabelung:

```text
FRITZ!Box 7590 AX
    |
TP-Link Omada TL-SG3428 (verwaltbar, LLDP/FDB)
    | Port 2
TL-SG1024DE
    |
Server-3
```

**Gerätekennungen:**

| Gerät | MAC-Adresse | Hinweis |
| --- | --- | --- |
| TL-SG3428 | `D4:D6:DF:0E:1B:54` | FDB-Datenquelle |
| TL-SG1024DE | `EC:75:0C:C2:68:F7` | Laut Nutzer hinter SG3428-Port 2 |
| Server-3 | `2C:CF:67:EF:3B:60` | Laut Nutzer hinter TL-SG1024DE |

**Tatsächlich beobachtete FDB-Daten (HA-Sensor „FDB-Portzuordnung“):**

- `observation_count: 61`, `source_count: 1`
- `evidence: last_manual_fdb_observation`
- `connection: reachable_via_port`
- Quelle `D4:D6:DF:0E:1B:54`, Port `gigabitEthernet 1/0/2`: **zwei MAC-Adressen**, `2C:CF:67:EF:3B:60` und `EC:75:0C:C2:68:F7`.
- Weitere Portgruppen: Port 1 mit 28 MAC-Adressen, Port 8 mit 27 MAC-Adressen sowie einzelne MAC-Adressen an Ports 3, 7, 10 und 13.
- **Interpretation:** Beide MAC-Adressen sind laut gespeicherter FDB-Messung über SG3428-Port 2 erreichbar. **FDB allein beweist keine direkte Kabelverbindung** zwischen den Geräten; die konkrete Verkabelung wurde zusätzlich vom Nutzer bestätigt.
- Weil die Evidenz `last_manual_fdb_observation` lautet, ist dies eine **gespeicherte manuelle Beobachtung**, kein Nachweis einer laufend aktualisierten Live-Messung.

**Abweichende AVM-Mesh-Darstellung:**

- Die FRITZ!Box meldete TL-SG1024DE und Server-3 als direkt über `fritz.box` / `LAN:1` angebunden (Quelle `fritzbox_node_links`).
- Diese Mesh-Angabe beschreibt hier keinen verlässlich belegten physischen Direktanschluss und darf die FDB-/LLDP-Erkenntnisse nicht überschreiben.

## 3. Implementierte Grundlagen im Branch (Quellcodeprüfung aus dem bisherigen Arbeitsverlauf)

- `topology/internal_graph.py`: unterscheidet bestätigte physische Verbindungen (z. B. LLDP/manuell) von AVM-Mesh-Beobachtungen und FDB-Erreichbarkeit; verarbeitet u. a. `fdb_port_groups`, `lan_port_memberships`, `downstream_switch_candidates`, `downstream_branches` und `graph_branches`.
- `topology/device_connections.py`: führt Geräte-Verbindungsinformationen mit Typen wie `reachable_via_port`, `confirmed_lan` und `wlan` zusammen.
- `topology/combined.py`: kombinierte Topologiedaten.
- `sensor.py`: stellt unter anderem LLDP-Topologie, FDB-Portzuordnung und Netzwerktopologie bereit.
- Deutsche Sensor-Anzeigenamen aus `translations/de.json`: **LLDP-Topologie**, **FDB-Portzuordnung**, **Netzwerktopologie**.
- In Home Assistant wurde der Sensor `sensor.fritz_box_192_168_178_1_lldp_topologie` genannt. Die FDB-Portzuordnung wurde vom Nutzer mit den oben dokumentierten Attributen gefunden.
- Die Quellcode-Grundlage für nachgelagerte Zweige **existiert bereits**. Nicht ohne Befund erneut dieselbe Funktion implementieren.

## 4. Offener Punkt / nächste konkrete Aufgabe

**Ziel:** Herausfinden, warum die vorhandene automatische Topologielogik die bestätigte Testverkabelung noch nicht wie erwartet abbildet.

**Vorgehen:**

1. **Zuerst den aktuellen Branch/PR-Code lesen**, insbesondere `topology/internal_graph.py`, `topology/device_connections.py`, `topology/combined.py`, `coordinator.py` und relevante Tests. Nicht von einem fehlenden Feature ausgehen, das bereits implementiert wurde.
2. Den **tatsächlichen kombinierten Topologie-Output** für SG3428-Port 2, TL-SG1024DE und Server-3 untersuchen: Sind Portgruppe, Switch-Kandidat, Branch und Evidenz bereits vorhanden, gehen sie bei der Zusammenführung verloren oder fehlt nur die Anzeige?
3. **Gezielten Regressionstest** mit den bekannten MAC-Adressen und Port-2-FDB-Beobachtungen erstellen bzw. bestehende Tests prüfen. AVM-Mesh-`LAN:1` darf daraus keine falsche direkte physische Verbindung erzeugen.
4. Nur die **konkret nachgewiesene Lücke** ändern. Keine neue Erkennung auf Verdacht, keine unbelegten Kabelverbindungen und keine ungefragten Umbauten.
5. Gezielte Tests und vollständigen Diff prüfen, Ergebnis in Home Assistant validieren, dann erst über PR-Freigabe entscheiden.

**Noch zu verifizieren:** Ob die Daten schon korrekt im Backend ausgegeben werden und nur die Darstellung fehlt; ob die FDB-Messung im aktuellen Lauf frisch ist; ob der installierte Home-Assistant-Code exakt dem PR-Head entspricht.

## 5. Vereinbarte Arbeitsweise

- **MAC-Adresse** ist die stabile Geräteidentität; IP und Name können wechseln.
- **Keine FDB- oder AVM-Mesh-Erreichbarkeit als belegte physische Direktverbindung ausgeben.** Herkunft, Zeitbezug und Evidenz erhalten.
- Keine Wiederholung bereits abgeschlossener Diagnosen ohne neuen konkreten Anlass.
- Vor Änderungen **aktuellen GitHub-Stand und bestehende Tests prüfen**; keine Änderungen allein auf Vermutungen.
- Änderungen bleiben im passenden Feature-Branch; `main` und `develop` nicht ohne Freigabe verändern.
- Bei manueller Codeübergabe **vollständige, ersetzbare Dateien** liefern.
- Diese Statusdatei nach **jedem abgeschlossenen Arbeitsschritt** aktualisieren; bestätigte Ergebnisse und offene Hypothesen getrennt führen.

## 6. Einstieg für den nächsten Chat

> Setze **FRITZ!Box Network Insight** fort. Lies zuerst `docs/SPECIFICATION.md` und `docs/DEVELOPMENT_STATUS.md`, danach den aktuellen Stand von **PR #32**. Beginne bei Abschnitt 4 dieser Statusdatei. Wiederhole keine bereits bestätigten Verkabelungs- oder FDB-Tests, sofern kein neuer konkreter Grund besteht.

---
*Erstfassung nachträglich aus dem bisherigen Chat und dem GitHub-Stand vom 08.11.2026 erstellt. Sie ist eine Übergabe, kein Testprotokoll und keine Merge-Freigabe.*
