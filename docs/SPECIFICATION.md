# FRITZ!Box Network Insight – Pflichtenheft und Architektur

**Dokumentstatus:** Entwurf zur Abnahme  
**Spezifikationsversion:** 0.1  
**Zielplattform:** Home Assistant  
**Repository:** https://github.com/arator68/fritzbox-network-insight  
**Entwicklungsbranch:** `develop`  
**Lizenz:** MIT

> Dieses Dokument beschreibt die vereinbarten Anforderungen und die geplante Architektur. Es ist noch keine Implementierungsfreigabe. Vor Beginn der Programmierung muss der Nutzer diese Spezifikation ausdrücklich freigeben. Änderungen an freigegebenen Anforderungen erfolgen nur nach ausdrücklicher Zustimmung.

---

## 1. Projektziel

FRITZ!Box Network Insight ist eine eigenständige Home-Assistant-Integration zur Erfassung, Identifizierung und Auswertung von Netzwerkgeräten und deren Verbindungen.

Die Integration soll Informationen aus mehreren Quellen zusammenführen, ohne die Herkunft einzelner Beobachtungen zu verlieren. Aus diesen Informationen soll eine nachvollziehbare Netzwerktopologie entstehen.

Die Integration muss bereits nach der Einrichtung mit einer FRITZ!Box sinnvoll nutzbar sein. Die zusätzliche Switch-Konfiguration ist optional und darf die grundlegende Geräteerkennung nicht blockieren.

## 2. Verbindliche Grundprinzipien

1. **MAC-Adresse als Geräteidentität:** Eine gültige MAC-Adresse ist der primäre Schlüssel eines Netzwerkgeräts. IP-Adresse, Hostname und Anzeigename sind veränderliche Eigenschaften und dürfen keine neuen Geräteidentitäten erzeugen.
2. **Eine zentrale Geräteverwaltung:** Alle Datenquellen liefern Informationen an dieselbe zentrale Geräteverwaltung. Es gibt keine voneinander unabhängigen Gerätelisten je Datenquelle.
3. **Beobachtungen bleiben nachvollziehbar:** Daten unterschiedlicher Quellen werden getrennt mit Quelle und Zeitbezug gespeichert. Neue Informationen überschreiben nicht stillschweigend andere Beobachtungen.
4. **Keine unbelegten Direktverbindungen:** Eine gelernte MAC-Adresse an einem Switch-Port beweist allein nicht, dass das Gerät physisch direkt an diesem Port angeschlossen ist.
5. **Fehlerisolation:** Der Ausfall einer Datenquelle darf die übrige Integration nicht stoppen.
6. **Dynamische Entitäten:** Home-Assistant-Entitäten werden nur angelegt, wenn dafür tatsächlich verwertbare Informationen existieren.
7. **Persistenz:** Gerätebestand, Historie und relevante Zeitstempel bleiben über Neustarts und Updates hinweg erhalten.
8. **Modulare Entwicklung:** Jede Komponente hat eine klar definierte Verantwortung und kommuniziert über festgelegte Schnittstellen.
9. **Keine stillen Zusatzänderungen:** Implementierungen dürfen nur den freigegebenen Umfang umsetzen. Nicht vereinbarte Verbesserungen oder Umbauten sind vorher abzustimmen.

## 3. Funktionsumfang

### 3.1 FRITZ!Box als primäre Datenquelle

Die Integration verbindet sich mit der vom Nutzer konfigurierten Haupt-FRITZ!Box und erfasst – soweit die jeweilige FRITZ!Box-Schnittstelle diese Informationen bereitstellt – unter anderem:

- erkannte Netzwerkgeräte;
- MAC-Adresse;
- aktuelle und bekannte IP-Adressen;
- Hostname bzw. Gerätename;
- Online-/Offline- bzw. Erreichbarkeitsstatus;
- verfügbare Verbindungs- und Mesh-Informationen;
- verfügbare Geräte- und Schnittstelleninformationen.

Nicht jedes FRITZ!Box-Modell und jede Firmware stellt alle Felder bereit. Nicht verfügbare Informationen müssen als nicht verfügbar behandelt werden und dürfen nicht erfunden werden.

### 3.2 Zentrale Geräteidentität und Herstellererkennung

- Die MAC-Adresse ist der primäre Identifikator.
- Änderungen an IP-Adresse, Hostname oder Anzeigename aktualisieren das vorhandene Gerät.
- Hersteller werden anhand des MAC-Präfixes aus einer lokalen OUI-Datenbank ermittelt.
- Die OUI-Datenbank muss über die Integration manuell aktualisierbar sein.
- Die Aktualisierung darf nicht bei jedem Netzwerkscan automatisch erfolgen.
- Die Oberfläche zeigt Datenbankstand und Zeitpunkt der letzten erfolgreichen Aktualisierung.
- Nach einer Datenbankaktualisierung können Herstellerzuordnungen für bereits bekannte Geräte erneut ausgewertet werden.
- Lokal verwaltete bzw. randomisierte MAC-Adressen können keine verlässliche Herstellerzuordnung erlauben. In diesem Fall wird der Hersteller als unbekannt bzw. nicht zuverlässig bestimmbar geführt.
- Die konkrete Datenquelle, das Dateiformat, die Lizenz- und Aktualisierungsstrategie der OUI-Datenbank werden vor ihrer Implementierung festgelegt.

### 3.3 Switch-Erkennung und -Einrichtung

Es wird Variante C umgesetzt: automatische Erkennung, ergänzt durch manuelle Konfiguration.

- Die Integration versucht, Switches im Netzwerk zu erkennen und als Infrastrukturgeräte zu identifizieren.
- Erkannte Switches werden in der Integration angezeigt.
- Für verwaltbare Switches kann der Nutzer IP-Adresse, SNMP-Version und Zugangsdaten manuell konfigurieren.
- Mehrere Switches mit unterschiedlichen Zugangsdaten müssen unterstützt werden.
- SNMP- und LLDP-Fähigkeiten werden pro Switch getrennt bewertet.
- Unverwaltete oder nicht abfragbare Switches können als erkannte Netzwerkgeräte sichtbar sein; ohne geeignete Schnittstelle werden für sie keine nicht verfügbaren Portdaten behauptet.
- Fehlende Zugangsdaten für einen Switch dürfen die FRITZ!Box-Erfassung und die Erkennung anderer Geräte nicht verhindern.
- Die Konfiguration eines Switches darf nicht voraussetzen, dass alle anderen Switches dieselben Zugangsdaten verwenden.

### 3.4 Switch-Daten und LLDP

Soweit von Gerät und Protokoll unterstützt, sollen folgende Informationen erfasst werden:

- Switch-MAC-Adresse und Identifikation;
- Bridge-/FDB-MAC-Tabelle;
- VLAN-Informationen, sofern verfügbar;
- Portnummer und Portbeschreibung;
- LLDP-Nachbarn und lokale/entfernte Portinformationen;
- Abfragezeitpunkt und Ergebnisstatus.

Die Erfassung der Bridge-FDB und die Auswertung von LLDP sind getrennte Funktionen. Das Vorhandensein einer MAC-Adresse in einer FDB ist ein Indiz für den über diesen Port erreichbaren Pfad, aber für sich allein kein Beweis für ein direkt angeschlossenes Endgerät.

### 3.5 AVM-Geräte

- Weitere FRITZ!Boxen und AVM-Repeater sollen nach Möglichkeit über die Haupt-FRITZ!Box erkannt werden.
- Jedes erkannte AVM-Gerät wird in Home Assistant als eigenes Gerät dargestellt.
- Diese Geräte gehören standardmäßig zur Konfiguration der Hauptintegration; separate Config Entries und zusätzliche Zugangsdaten sind zunächst nicht erforderlich.
- Direkte Abfragen eines AVM-Geräts können später optionale zusätzliche Zugangsdaten erfordern. Dies ist kein Muss für die erste nutzbare Version.
- Es werden nur Informationen und Sensoren angeboten, die das jeweilige Gerät tatsächlich bereitstellt.

### 3.6 Quellenkonflikte und Verbindungsbewertung

Jede Beobachtung muss mindestens enthalten:

- Quelle bzw. Adapter;
- Beobachtungsart;
- beobachtetes Gerät bzw. MAC-Adresse, soweit vorhanden;
- beobachteter Wert oder Verbindungsendpunkte;
- Zeitstempel;
- Gültigkeits-/Aktualitätsinformation;
- zugrunde liegende Evidenz.

Beobachtungen aus FRITZ!Box-Mesh, Switch-FDB und LLDP dürfen sich widersprechen oder unterschiedliche Netzabschnitte beschreiben. Sie werden deshalb nicht durch eine starre, globale Quellenpriorität ersetzt.

Verbindungen werden in drei Aussageklassen dargestellt:

- **Nachgewiesen:** Die verfügbare Evidenz belegt die konkrete Verbindung hinreichend.
- **Wahrscheinlich:** Die Evidenz spricht für die Verbindung, beweist sie aber nicht.
- **Unbekannt / nur beobachtet:** Die Information zeigt eine Erreichbarkeit oder Beobachtung, erlaubt aber keine belastbare Aussage über die physische Verbindung.

Darstellungsvorgabe für eine spätere Topologieansicht:

- nachgewiesene Verbindungen: durchgezogene Linie;
- wahrscheinliche Verbindungen: gestrichelte Linie;
- unbekannte bzw. nicht zuordenbare Verbindungen: sichtbar als unklar gekennzeichnet.

Es werden keine willkürlichen numerischen Vertrauenswerte als gemessene Tatsachen ausgegeben. Eine spätere Bewertung muss ihre nachvollziehbare Evidenz offenlegen.

### 3.7 Gerätehistorie und Offline-Geräte

- Geräte, die nicht mehr gesehen werden, bleiben im gespeicherten Gerätebestand erhalten.
- Der Status wird entsprechend als nicht aktuell gesehen bzw. offline markiert.
- Letzter Beobachtungszeitpunkt und relevante Änderungen werden persistiert.
- Geräte werden nicht unmittelbar beim Verschwinden gelöscht.
- Eine automatische Lösch- oder Aufbewahrungsregel ist nicht Bestandteil der ersten Festlegung und müsste gesondert vereinbart werden.

### 3.8 Sensoren und Home-Assistant-Geräte

- Es gibt eine zentrale Netzwerkübersicht.
- Erkannte Geräte werden als eigenständige Home-Assistant-Geräte angelegt, soweit es für sie eine stabile Identität gibt.
- AVM-Router und -Repeater werden separat dargestellt.
- Sensoren entstehen dynamisch anhand tatsächlich vorhandener und sinnvoller Daten.
- Es werden keine dauerhaft leeren Sensoren nur vorsorglich angelegt.
- Entity-IDs und interne Schlüssel sind sprachunabhängig und stabil.
- Anzeigenamen, Einrichtungsdialoge, Optionen und Fehlermeldungen werden auf Deutsch und Englisch bereitgestellt.

### 3.9 Scanintervall

- Standardintervall: 60 Sekunden.
- Das Scanintervall soll konfigurierbar sein.
- Datenquellen werden unabhängig voneinander abgefragt und verwaltet, soweit es für Fehlerisolation und Aktualität erforderlich ist.
- Die Integration muss fehlgeschlagene Abfragen als solche kennzeichnen und darf Fehler nicht als leere Gerätelisten interpretieren.

### 3.10 Herstellerdatenbank aktualisieren

In der Integrationsoberfläche ist ein Bereich für die OUI-Datenbank vorgesehen:

- aktueller Datenbankstand bzw. Versions-/Quelleninformation;
- Datum der letzten erfolgreichen Aktualisierung;
- Aktion „Jetzt aktualisieren“;
- Ergebnis der letzten Aktualisierung;
- lokale Verwendung der zuletzt erfolgreich gespeicherten Datenbank.

Eine fehlgeschlagene Aktualisierung darf die bestehende lokale Datenbank nicht beschädigen oder durch eine unvollständige Datei ersetzen.

## 4. Nicht-funktionale Anforderungen

- Ziel ist eine Installation als Home-Assistant-Custom-Integration.
- Die Integration soll mit dem Home-Assistant-Konfigurations- und Optionsfluss arbeiten.
- Zugangsdaten werden getrennt von Gerätebeobachtungen gespeichert und nicht in Diagnoseausgaben offengelegt.
- Netzwerkabfragen erhalten nachvollziehbare Timeouts und Fehlerbehandlung.
- Die Integration soll mit fehlenden optionalen Datenquellen weiterhin funktionieren.
- Persistente Daten müssen Updates und Home-Assistant-Neustarts überstehen.
- Datenmodelländerungen benötigen eine nachvollziehbare Migration.
- Es werden deutsche und englische Übersetzungen von Anfang an berücksichtigt.
- Das Projekt wird unter MIT-Lizenz veröffentlicht.
- Die spätere Veröffentlichung soll die Anforderungen des Home-Assistant-Ökosystems und HACS berücksichtigen. Konkrete Veröffentlichungsprüfungen werden vor dem ersten Release anhand der dann aktuellen Vorgaben verifiziert.

## 5. Geplante Modulstruktur

Die folgende Struktur ist die vereinbarte Zielgliederung. Dateinamen können vor Implementierungsbeginn noch angepasst werden, sofern Zuständigkeiten und Grenzen erhalten bleiben.

```text
custom_components/fritzbox_network_insight/
├── __init__.py
├── manifest.json
├── const.py
├── config_flow.py
├── coordinator.py
├── diagnostics.py
│
├── core/
│   ├── device_model.py
│   ├── device_registry.py
│   ├── observations.py
│   ├── connection_model.py
│   ├── connection_registry.py
│   ├── topology.py
│   └── device_history.py
│
├── routers/
│   ├── base.py
│   ├── fritzbox.py
│   └── discovery.py
│
├── switches/
│   ├── base.py
│   ├── discovery.py
│   ├── snmp.py
│   ├── bridge_fdb.py
│   ├── lldp.py
│   └── switch_registry.py
│
├── avm/
│   ├── discovery.py
│   ├── device.py
│   └── client.py
│
├── sensors/
│   ├── sensor.py
│   └── device.py
│
├── storage/
│   ├── store.py
│   └── migration.py
│
└── translations/
    ├── de.json
    └── en.json
```

Tests liegen im Projekt in einem separaten Testbereich, der nicht als Laufzeitmodul der Integration importiert wird.

### 5.1 Zentrale Integration

- `__init__.py`: Setup, Plattformweitergabe, Shutdown und Lebenszyklus der Integration.
- `manifest.json`: Home-Assistant-Metadaten, Abhängigkeiten und Integrationskennung.
- `const.py`: gemeinsame Konstanten und feste Kennungen; keine fachliche Geschäftslogik.
- `config_flow.py`: Einrichtungsdialog, Verbindungstest und Optionsfluss.
- `coordinator.py`: zeitliche Koordination und Zusammenführung der Ergebnisse; keine Implementierung von SNMP, FRITZ!Box-Protokollen oder Topologieregeln.
- `diagnostics.py`: sichere Diagnoseinformationen ohne Passwörter oder Geheimnisse.

### 5.2 Kernlogik

- `device_model.py`: kanonisches Datenmodell eines Geräts.
- `device_registry.py`: Zusammenführung und Verwaltung der Geräte nach MAC-Identität.
- `observations.py`: einheitliches Modell für quellenspezifische Beobachtungen.
- `connection_model.py`: Datenmodell für einen Verbindungsbefund einschließlich Aussageklasse und Evidenz.
- `connection_registry.py`: Verwaltung und Aktualisierung aller Verbindungsbeobachtungen.
- `topology.py`: Ableitung einer nachvollziehbaren Netzwerktopologie aus Geräten und Verbindungsbefunden.
- `device_history.py`: fachliche Verwaltung von Geräteänderungen und Zeitverlauf.

### 5.3 Router-Adapter

- `routers/base.py`: gemeinsamer Vertrag für Router-Datenquellen.
- `routers/fritzbox.py`: FRITZ!Box-spezifische Kommunikation und Datenübersetzung in interne Beobachtungen.
- `routers/discovery.py`: Erkennung weiterer Router, soweit über die verfügbaren Datenquellen möglich.

### 5.4 Switch-Adapter

- `switches/base.py`: gemeinsamer Vertrag für Switch-Adapter.
- `switches/discovery.py`: Erkennung möglicher Switches und ihrer Fähigkeiten.
- `switches/snmp.py`: SNMP-Verbindung, Authentifizierung und Abfrage.
- `switches/bridge_fdb.py`: Interpretation von Bridge-FDB-/MAC-Tabellen.
- `switches/lldp.py`: Verarbeitung von LLDP-Nachbarschaftsinformationen.
- `switches/switch_registry.py`: konfigurierte und erkannte Switches, einschließlich individueller Verbindungsparameter.

### 5.5 AVM-Module

- `avm/discovery.py`: Erkennung zusätzlicher AVM-Geräte.
- `avm/device.py`: kanonische AVM-Geräteinformationen.
- `avm/client.py`: optionale direkte Kommunikation mit AVM-Geräten.

### 5.6 Home-Assistant-Plattform

- `sensors/sensor.py`: Sensorplattform und dynamische Sensorbereitstellung.
- `sensors/device.py`: stabile Home-Assistant-Gerätezuordnung und Geräteinformationen.

### 5.7 Speicherung

- `storage/store.py`: persistente Speicherung von Geräten, Beobachtungen, Verbindungen, Historie und OUI-Datenbank-Metadaten.
- `storage/migration.py`: kontrollierte Migration persistierter Datenmodelle.

## 6. Schnittstellen- und Datenmodellverträge

Die genauen Python-Typen werden bei der Implementierung festgelegt. Die folgenden fachlichen Felder und Grenzen sind verbindlich.

### 6.1 Device

Ein Geräteobjekt enthält mindestens:

- stabile interne Gerätekennung auf MAC-Basis;
- normalisierte MAC-Adresse, sofern vorhanden;
- IP-Adressen (eine oder mehrere);
- Hostname und Anzeigename, sofern bekannt;
- Hersteller und gegebenenfalls Modell;
- Gerätetyp/Kategorie, sofern ausreichend belegt;
- aktuelle Sichtbarkeit bzw. Erreichbarkeit;
- Zeitpunkt der ersten und letzten Beobachtung;
- Verweise auf zugehörige Beobachtungen.

Ein Gerät ohne verwertbare MAC-Adresse darf nicht durch eine erfundene MAC-Adresse identifiziert werden. Falls eine Quelle Geräte ohne MAC meldet, wird diese Information separat behandelt, bis eine belastbare Identität hergestellt werden kann.

### 6.2 Observation

Eine Beobachtung enthält mindestens:

- eindeutige Beobachtungskennung;
- Quellkennung (z. B. FRITZ!Box, SNMP-Switch mit Switch-ID, LLDP oder AVM-Direktabfrage);
- Beobachtungstyp;
- Gerätebezug oder MAC-Adresse, soweit vorhanden;
- beobachtete Daten;
- Beobachtungszeitpunkt;
- Zeitpunkt der letzten erfolgreichen Aktualisierung;
- Status (aktuell, veraltet, fehlgeschlagen oder ungültig);
- verfügbare Roh-/Evidenzdaten in einem für die Quelle geeigneten Umfang.

Die normalisierten Daten ersetzen nicht die Information darüber, woher sie stammen.

### 6.3 Connection Observation

Ein Verbindungsbefund enthält mindestens:

- Quelle;
- Endpunkte, soweit bekannt;
- lokale und entfernte Portkennung, soweit bekannt;
- Verbindungsmedium bzw. Segment, soweit bekannt;
- Zeitstempel;
- Evidenz und deren Herkunft;
- Aussageklasse: nachgewiesen, wahrscheinlich oder unbekannt/nur beobachtet;
- Aktualitätsstatus.

Mehrere Beobachtungen können dieselben Endpunkte betreffen. Sie bleiben unterscheidbar und können gemeinsam ausgewertet werden.

### 6.4 Switch-Konfiguration

Ein Switch-Eintrag enthält mindestens:

- interne Switch-Kennung;
- IP-Adresse bzw. Zieladresse;
- Hersteller/Modell, soweit bekannt;
- SNMP-Version;
- erforderliche Authentifizierungsdaten;
- aktivierte bzw. erkannte Fähigkeiten;
- letzten Abfragezeitpunkt und letzten Abfragestatus.

Zugangsdaten werden nicht in Gerätebeobachtungen, Sensorattribute oder Diagnoseexporte kopiert.

## 7. Abhängigkeitsrichtung und Modulgrenzen

Die Abhängigkeiten verlaufen grundsätzlich in eine Richtung:

1. Datenquellenadapter kommunizieren mit externen Geräten und liefern standardisierte Beobachtungen.
2. Core-Module verwalten Geräte, Beobachtungen und Verbindungsbefunde.
3. Die Topologie wertet Core-Daten aus, greift aber nicht direkt auf Router- oder SNMP-Verbindungen zu.
4. Der Coordinator orchestriert Adapter und Core-Verarbeitung.
5. Home-Assistant-Plattformen stellen aufbereitete Daten dar und führen keine eigene Netzwerkermittlung durch.
6. Storage speichert die dafür vorgesehenen Daten; fachliche Entscheidungen bleiben in den zuständigen Core-Modulen.

Unzulässig ist insbesondere:
- Topologiecode mit SNMP-Abfragen;
- Sensorcode mit direkter FRITZ!Box-Kommunikation;
- Adapter, die eigenständig Home-Assistant-Entitäten anlegen;
- ein globaler Gerätebestand pro Datenquelle;
- die Vermischung von Zugangsdaten und Gerätehistorie.

## 8. Einrichtungs- und Betriebsablauf

1. Nutzer trägt Adresse und Zugangsdaten der Haupt-FRITZ!Box ein.
2. Die Integration testet die Verbindung und ermittelt verfügbare Geräteinformationen.
3. Die erste Geräteliste wird eingelesen und anhand von MAC-Adressen zentral registriert.
4. Weitere AVM-Router und Repeater werden – soweit erkennbar – als eigene Geräte erfasst.
5. Mögliche Managed Switches werden erkannt und angezeigt.
6. Der Nutzer kann Switches optional mit individuellen SNMP-Einstellungen ergänzen.
7. Switch-FDB, LLDP und Mesh liefern getrennte Beobachtungen.
8. Die Verbindungsverwaltung bewertet die Befunde und die Topologie leitet daraus die Netzwerkstruktur ab.
9. Home Assistant erhält nur die Entitäten, für die verwertbare Daten vorliegen.
10. Gerätebestand und Historie werden gespeichert und bei späteren Scans aktualisiert.

Die Integration muss bereits nach Schritt 3 sinnvoll nutzbar sein. Switch-Konfiguration und zusätzliche Protokolle sind optionale Erweiterungen.

## 9. Vorgesehene Konfigurationsbereiche

Die spätere Integrationsverwaltung soll mindestens folgende Bereiche vorsehen:

- Haupt-Router: Verbindung, Zugangsdaten und Verbindungsstatus;
- Geräte: erkannte Geräte und deren verfügbare Informationen;
- Switches: Erkennung, individuelle SNMP-Konfiguration und Status;
- AVM-Geräte: erkannte Router und Repeater;
- Topologie: Verbindungsbefunde, Quellen und Aussageklassen;
- System: Scanintervall, Speicher-/Historienstatus und Diagnose;
- Herstellerdatenbank: Versionsstand, letzte Aktualisierung und manuelle Aktualisierung.

Die genaue UI-Ausgestaltung wird gesondert spezifiziert, bevor die Oberfläche implementiert wird.

## 10. Scan- und Fehlerverhalten

- Standard-Scanintervall: 60 Sekunden.
- Das Intervall ist konfigurierbar.
- Jede Datenquelle meldet ihren eigenen Abrufstatus.
- Ein Fehler einer Quelle wird protokolliert und isoliert behandelt.
- Ein fehlgeschlagener Abruf darf nicht als erfolgreiche leere Antwort gespeichert werden.
- Vorhandene Daten bleiben erhalten, bis eine neue erfolgreiche Beobachtung oder eine explizite fachliche Regel ihre Aktualität verändert.
- Wiederholte Fehler dürfen keine unkontrollierte Geräte- oder Entitäten-Neuanlage verursachen.

## 11. Persistenz, Updates und Migration

Persistiert werden insbesondere:

- zentrale Geräteidentitäten und bekannte Eigenschaften;
- erste und letzte Beobachtungszeitpunkte;
- quellenspezifische Beobachtungen und deren Aktualitätsstatus;
- Verbindungsbefunde und Evidenz;
- konfigurierte Switches und notwendige Konfigurationsdaten;
- Historie;
- lokale OUI-Datenbank und deren Metadaten.

Passwörter und andere Geheimnisse werden ausschließlich über geeignete Home-Assistant-Konfigurationsmechanismen verwaltet und niemals in Klartext-Diagnosen ausgegeben.

Datenmodelländerungen erhalten eine Versionskennung und eine explizite Migration. Ein Integrationsupdate darf gespeicherte Nutzerdaten nicht stillschweigend löschen.

## 12. Sprache und stabile Kennungen

- Deutsch und Englisch ab der ersten Implementierung.
- Übersetzungen für Config Flow, Optionen, Sensoranzeigen und Fehlermeldungen.
- Interne Kennungen, Gerätekennungen und Entity-IDs bleiben unabhängig von der Sprache.
- Ein Wechsel der Home-Assistant-Sprache darf keine neuen Geräte oder Entitäten erzeugen.

## 13. Qualitätssicherung und Freigaberegeln

Jeder Entwicklungsabschnitt wird einzeln umgesetzt und geprüft.

Vor der Übergabe eines Entwicklungsstands sind mindestens erforderlich:

- Syntaxprüfung aller geänderten Python-Dateien;
- gezielte Tests der betroffenen Module;
- Regressionstests für bereits freigegebene Funktionen;
- Prüfung des vollständigen Diffs gegen den vorherigen freigegebenen Stand;
- Prüfung, dass keine nicht vereinbarten Dateien oder Funktionen geändert wurden;
- nachvollziehbare Commit-Nachricht und eindeutiger Versionsstand.

Es werden vollständige ersetzbare Dateien bzw. ein vollständiges ZIP bereitgestellt, wenn Dateien zur manuellen Installation übergeben werden.

Abgeschlossene und freigegebene Phasen werden nicht ohne ausdrückliche Zustimmung verändert.

## 14. Entwicklungs- und Branch-Strategie

- `main`: ausschließlich freigegebene, veröffentlichte Stände.
- `develop`: laufende Integration und zusammengeführte, geprüfte Entwicklungsarbeiten.
- `feature/<name>`: isolierte Arbeit an jeweils einem vereinbarten Funktionsumfang.
- Änderungen aus Feature-Branches werden nach Prüfung in `develop` übernommen.
- Eine Veröffentlichung erfolgt erst nach ausdrücklicher Freigabe und Prüfung des vollständigen Release-Stands.

Die bestehende frühere Integration wird nicht verändert. Sie dient ausschließlich als Erfahrungs- und Informationsquelle, soweit dies ausdrücklich vereinbart wurde.

## 15. Veröffentlichungsziel

Das Projekt soll öffentlich auf GitHub unter MIT-Lizenz entwickelt und später für die Verteilung über HACS bzw. das Home-Assistant-Ökosystem vorbereitet werden.

Vor dem ersten Release werden die dann aktuellen Anforderungen für:
- Integrationsmanifest;
- Repository-Metadaten;
- HACS-Validierung;
- Home-Assistant-Validierung;
- README und Installationsanleitung;
- Release-Tags und Versionsnummern;
- Lizenz und Urheberrechtsangaben

überprüft und umgesetzt.

## 16. Noch vor Implementierung festzulegende Detailentscheidungen

Die folgenden Punkte sind durch die bisherigen Architekturentscheidungen noch nicht vollständig bestimmt. Sie dürfen nicht stillschweigend durch Annahmen ersetzt werden:

1. **OUI-Datenquelle:** konkrete Datenquelle, Lizenz, Dateiformat, Updateprüfung und Fallback-Verhalten.
2. **FRITZ!Box-Schnittstellen:** konkrete unterstützte TR-064-/UPnP-/Mesh-Endpunkte und deren Modell-/Firmwareunterschiede.
3. **SNMP-Umfang:** unterstützte SNMP-Versionen und konkrete benötigte MIB-/OID-Abdeckung für erste Switchmodelle.
4. **LLDP-Erfassung:** welche Endpunkte bzw. Geräte tatsächlich LLDP-Daten liefern und wie deren Evidenz bewertet wird.
5. **Persistenzdetails:** konkrete Speicheraufteilung, Größenbegrenzung und Aufbewahrungsstrategie für historische Beobachtungen.
6. **Identitätsausnahmen:** Behandlung von Geräten ohne MAC-Adresse und von MAC-Adresswechseln.
7. **Topologie-Regeln:** konkrete Evidenzregeln für nachgewiesene, wahrscheinliche und unbekannte Links.
8. **Erste unterstützte Geräte/Testmatrix:** konkrete FRITZ!Box-, AVM-Repeater- und TP-Link-Switchmodelle für die erste Testphase.

Diese Detailpunkte werden vor der jeweiligen Implementierungsphase geklärt. Das Vorhandensein eines offenen Detailpunkts erlaubt keine automatische Erweiterung des Funktionsumfangs.

## 17. Abnahme

Dieses Dokument ist der Spezifikationsentwurf 0.1. Die Programmierung beginnt erst, wenn der Nutzer den Inhalt ausdrücklich freigegeben hat.

Änderungswünsche werden zuerst in diesem Dokument nachvollziehbar eingearbeitet. Erst nach Abnahme wird die Spezifikation als verbindliche Entwicklungsgrundlage markiert.
