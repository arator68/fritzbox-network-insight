# Entwicklungsstand – FRITZ!Box Network Insight

**Stand:** 2026-11-09 (fortlaufend aktualisiert; ältere Abschnitte als historische Momentaufnahme erhalten)  
**Status:** Laufende Entwicklung; keine Release- oder Merge-Freigabe  
**Verbindliche Anforderungen:** [SPECIFICATION.md](SPECIFICATION.md)  
**Repository:** https://github.com/arator68/fritzbox-network-insight  
**Aktueller Arbeitsbranch:** `feature/wlan-device-details` (Ausgangsbasis `develop`)  
**Historischer Pull Request:** [#32 – Add automatic AVM Mesh observations to Network Insight](https://github.com/arator68/fritzbox-network-insight/pull/32) → `develop` (Status in Abschnitt 1 ist historisch und nicht der aktuelle Arbeitsauftrag)

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

## 7. 2026-11-09 – Karten-Datenmodell (implementiert, HA-Test ausstehend)

- Nutzer-Diagnose `topology_diagnostics` bestätigt eine manuell bestätigte SG3428-Port-2-Verbindung zum TL-SG1024DE (`consistent_with_fdb`) und einen FDB-basierten Zweig mit Server-3. Die tatsächliche Server-3-Direktverbindung bleibt nicht per FDB bewiesen.
- `topology/view_model.py` ergänzt: MAC-basierte, einmalige Knoten; bestätigte LAN-Kanten aus LLDP/manueller Bestätigung; WLAN-Kanten aus AVM Mesh; separate Mesh-LAN-Beobachtungen und FDB-Zweigzugehörigkeit. Ein Repeater ohne aufgelösten Uplink bleibt als Knoten sichtbar, ohne erfundene Kante.
- Neue read-only Aktion `fritzbox_network_insight.topology_view` liefert das Karten-Datenmodell. Bei mehreren konfigurierten FRITZ!Boxen ist `entry_id` erforderlich. Die Aktion ist in `services.yaml` dokumentiert.
- `tests/test_topology_view.py` enthält gezielte Regressionstests für unbekannte Repeater-Uplinks, bestätigte Switch-Kanten und FDB-Zweigmitgliedschaft.
- **Noch nicht abgeschlossen:** CI-Prüfung, Ausführung in Home Assistant und grafische Lovelace-Karte. Diese Änderung liefert zunächst die geprüfbare Backend-Schnittstelle, **noch keine fertige grafische HA-Karte**. PR #32 bleibt Draft und darf nicht allein aufgrund dieser Änderungen gemergt werden.

## 8. 2026-11-09 – Gezielte Mesh-Geräteklassifizierung

- Ursache: Die zentrale konservative Klassifizierung setzt ohne manuelle/protokollbasierte Erkennung `device_type: null`; das kombinierte Topologiemodell nutzte die bereits bekannte AVM-Mesh-Rolle bisher nicht als Fallback.
- `topology/combined.py`: Nur wenn noch kein `device_type` vorliegt, wird `mesh_role: master` zu `router` und `mesh_role: slave` zu `access_point`. Die Rolle `slave` unterscheidet eine zweite FRITZ!Box nicht zuverlässig von einem Repeater; daher keine unbelegte spezielle Repeater-Kategorie. Bereits vorhandene manuelle/SNMP-Klassifizierungen haben Vorrang. Quelle `avm_mesh_role` und Konfidenz `detected` werden ergänzt.
- Bestehende Klassifizierungsquelle und Konfidenz werden aus den Hostdaten übernommen; `topology/view_model.py` gibt diese Metadaten weiter.
- `tests/test_mesh_device_type.py` ergänzt drei Regressionstests (Mesh-Rollen, Vorrang bestehender Klassifizierung, Ausgabe in der Topologieansicht).
- **Offen:** GitHub-CI und anschließender Home-Assistant-Test der neuen `topology_view`-Ausgabe. Keine Änderung an Netzwerkkarte oder Verkabelungserkennung. PR #32 bleibt Draft.

## 9. 2026-11-09 – LAN-Gerätedetails abgeschlossen, WLAN-Gerätedetails in Entwicklung

### LAN-Gerätedetails (in `develop`)

- PR [#34 – LAN-Gerätedetails](https://github.com/arator68/fritzbox-network-insight/pull/34) wurde nach grünen Prüfungen nach `develop` übernommen.
- `lan_device_details.py` reichert MAC-bezogene Geräteinformationen mit IF-MIB-/FDB-Beobachtungen an; der vorhandene Statussensor zeigt `lan_switch_ports` **nur für explizit als Ethernet identifizierte Geräte**.
- `connection: reachable_via_port` ist eine FDB-Erreichbarkeitsaussage, **kein Nachweis eines direkten Kabels**. Geschwindigkeit und Betriebsstatus beziehen sich auf den gemeldeten Switch-Port.
- In Home Assistant wurde der Desktop-PC an `gigabitEthernet 1/0/13` mit 1000 Mbit/s geprüft; ein WLAN-Luftreiniger zeigte korrekt kein `lan_switch_ports`-Attribut.

### WLAN-Gerätedetails (aktueller Feature-Branch)

- Arbeitsbranch: `feature/wlan-device-details` von `develop`; **noch nicht nach `develop` gemergt**.
- Diagnose `fritzbox_network_insight.device_details_diagnostics` vom 09.11.2026: 72 Geräte; WLAN-Daten aus AVM Mesh und teilweise TR-064 vorhanden. Unterschiede zwischen Quellen sind real: z. B. Dreame-Saugroboter mit Mesh-Kanal 1 und TR-064-Kanal 11. RX-Raten können ausdrücklich 0 sein.
- Neue Datei `custom_components/fritzbox_network_insight/wlan_device_attributes.py` bereitet ausschließlich vorhandene WLAN-Beobachtungen für das Attribut `wlan_details` auf, einschließlich `field`, `value`, `source` und `observed_at`. Mesh-WLAN-Peer-MAC wird als gemeldete Beobachtung, nicht als bestätigte physische Verbindung ausgegeben.
- `sensor.py` ergänzt `wlan_details` am bestehenden Statussensor nur bei ausdrücklich als WLAN klassifizierten Hosts. Keine neuen Entitäten, keine Entity-ID- oder Anzeigenamenänderungen; bestehende LAN-Attribute bleiben erhalten.
- `tests/test_wlan_device_attributes.py` enthält Regressionstests für abweichende Quellen/Kanäle, Nullwerte, rohe Signalwerte, LAN-Abgrenzung und fehlende Messungen.
- **CI:** Nutzer meldete „test ok“; damit sind die GitHub-Prüfungen laut Nutzer grün. **Home-Assistant-Praxistest steht aus**; die Änderungen wurden noch nicht als installiert bestätigt.

### Vereinbarter Entwicklungs- und Testablauf

- Python-Änderungen an Custom Integrations benötigen für einen verlässlichen Test üblicherweise einen Home-Assistant-Neustart. Deshalb **Änderungen und GitHub-Tests bündeln**, statt nach jedem Commit neu zu starten.
- Erst nach Abschluss eines sinnvollen Entwicklungsabschnitts einmal auf der produktiven HA-Instanz installieren und prüfen; bis dahin produktives HA unangetastet lassen.
- `docs/DEVELOPMENT_STATUS.md` nach abgeschlossenen Schritten und wesentlichen Statuswechseln fortschreiben, dabei CI, HA-Praxistest und Merge-Status klar trennen.

### Nächster Schritt

1. WLAN-Attributmodell und Tests im Feature-Branch abschließend prüfen, insbesondere die Größe der HA-Statusattribute und die korrekte Quellzuordnung bei mehreren Mesh-Beobachtungen.
2. Weitere kleine Verbesserungen nach Möglichkeit vor dem nächsten gemeinsamen HA-Praxistest bündeln.
3. Nach einem einzigen HA-Neustart die WLAN-Statusattribute an einem konkreten Gerät (z. B. `sensor.fritzbox_network_insight_004b12694d2c_status`) prüfen.
4. Erst danach über PR/Merge nach `develop` entscheiden.

**Hinweis:** Abschnitte 1–8 dokumentieren frühere Zwischenstände und sind nicht als aktuelle PR-/CI-Aussagen zu lesen. Insbesondere die damaligen Aussagen zu PR #32 sind historische Momentaufnahmen.

## 10. 2026-11-09 – WLAN-Gerätedetails in Home Assistant praktisch bestätigt

- Nutzer hat Home Assistant nach Installation der aktuellen WLAN-Änderungen neu gestartet und die Statusattribute des WLAN-Luftreinigers im Arbeitszimmer übermittelt: `sensor.fritzbox_network_insight_004b12694d2c_status`, MAC `00:4B:12:69:4D:2C`, `interface_type: 802.11`.
- **Praxistest erfolgreich:** `wlan_details` ist vorhanden; RX 0 Mbit/s, TX 71 Mbit/s, RX/TX-Maximum je 150 Mbit/s, Mesh-Kanal 1. Die Messwerte sind mit `source: avm_mesh_radio` und `observed_at: 2026-11-09T11:39:05.474961+00:00` versehen.
- Rohe Signal-/RCPI-Felder bleiben unverändert: `wifi_mesh_signal_rx_raw: -31`, `mesh_rx_rcpi_raw: -31`, `mesh_tx_rcpi_raw: 255`. Diese Werte **nicht** ungeprüft als dBm oder Prozent interpretieren.
- `mesh_reported_wlan_peer_mac: E0:28:6D:C0:51:38` wird mit `source: avm_mesh` ausgegeben; dessen `observed_at` ist aktuell `null`. **Offener Qualitätsaspekt:** Zeitstempel dieser Peer-Beobachtung prüfen und nur bei belegter Quelle ergänzen.
- In der übermittelten Attributliste ist kein `lan_switch_ports` vorhanden; die LAN-/WLAN-Abgrenzung ist für dieses Gerät korrekt.
- **Keine weitere HA-Neustartschleife nötig** für diese Prüfung. Nächste Schritte: Qualitätsaspekt mit dem Peer-Zeitstempel bei Bedarf im Code prüfen, Änderung bündeln und den Feature-Branch für einen PR nach `develop` vorbereiten. Merge noch nicht bestätigt.

## 11. 2026-11-09 – Abgleich mit FRITZ!Box-Weboberfläche (Luftreiniger Arbeitszimmer)

- Nutzer lieferte Screenshots der AVM-Oberfläche: WLAN-Pfad `fritz.box → SG3428 → Fritz7560.koch.local → Luftreiniger`, letzter Abschnitt WLAN mit **2,4 GHz**, Anzeige **72 Mbit/s**.
- WLAN-Detailansicht der FRITZ!Box: Frequenzband 2,4 GHz; Standard Wi-Fi 4; WDS nein; aktuelle Datenrate **↓72 / ↑14 Mbit/s**; maximal **↓150 / ↑150 Mbit/s**; Kanalbandbreite 20 MHz; 1× Sende-/1× Empfangs-Stream; Signalstärke **−31 dBm**; STBC.
- HA-Sensor zum Vergleich: `wifi_rate_rx_mbps=0`, `wifi_rate_tx_mbps=71`, Maximalwerte 150/150, `mesh_wifi_channel=1`, `wifi_mesh_signal_rx_raw=-31`. **Maximalwerte stimmen überein, aktuelle Raten nicht**. Die Ursachen sind ungeklärt (z. B. Messzeitpunkt, Semantik/Richtung der Felder); Werte nicht auf Verdacht vertauschen.
- `-31` stimmt numerisch mit dem in AVM angezeigten `−31 dBm` überein; die allgemeine Einheit/Interpretation des Rohfelds ist im Code noch nicht verifiziert. Keine globale dBm-Umbenennung allein aufgrund eines Beispiels.
- Frequenzband, Standard, Kanalbandbreite, Streams, WDS und STBC erscheinen im bisher gezeigten `wlan_details`-Attribut nicht. Vor Ergänzung prüfen, ob die TR-064-/Mesh-Rohdaten diese Angaben zuverlässig liefern.
- **Nächster technischer Prüfschritt:** Quelle und Bedeutung der WLAN-Raten und Signal-/Bandbreitenfelder im bestehenden AVM-Parser nachvollziehen, gezielte Tests erstellen; produktive HA-Installation erst nach gebündelten Änderungen erneut aktualisieren.
