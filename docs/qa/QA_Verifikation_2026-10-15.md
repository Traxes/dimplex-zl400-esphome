# Verifikation Controller v3 (Tiefe) – Trax HA ZL 400 VF

Stand 15.10.2026. Grundlage ist die verschärfte Übergabe (Phasen 0–3). Ich habe nichts an Platinen- oder Schaltplandateien geändert und nichts bestellt.

Skripte, Modelle und Rohausgaben liegen in [_qa_tools/verifikation_2026-10-15/](_qa_tools/verifikation_2026-10-15/LIESMICH.txt) und sind dort reproduzierbar.

Dieser Bericht ersetzt in folgenden Punkten den Bericht vom 14.10.:
- Antennenlage: belegt statt geschätzt
- GPIO3: Pflicht statt Empfehlung
- Derating: Pass/Fail nach Regelwerk statt „knapp“
- Boot-Verhalten: Pull-up-Annahme durch Datenblatt und Grenzwertsuche ersetzt
- neuer Fund F3 (R15/R16 offen)
- neuer Fund F4 (24-V-Ausfall nicht erkennbar)

**Legende Belegart:** **DB** = Herstellerdatenblatt (mit Seite) · **SIM** = eigene Simulation (Datei) · **GEO** = Geometrie aus Fertigungsdaten · **ANN** = Annahme, muss gemessen werden · **MESS** = Messung des Nutzers (steht noch aus)

---

## 0. Kriterien (Phase 0) – vom Nutzer freigegeben am 15.10.2026, ab jetzt fest

| Kriterium | Wert | Quelle |
|---|---|---|
| Derating Transistor (von mir auch auf den Optokoppler-Ausgang angewandt; EEE-INST-002 hat keine eigene Optokoppler-Zeile) | U ≤ 0,75 × Nennwert, I ≤ 0,75, P ≤ 0,60, Tj ≤ 110 °C (125 °C bzw. 40 K unter Max.) | NASA EEE-INST-002 (5/03), Sect. S1, Table 4 „Transistor Derating Requirements“ |
| Derating Diode (Schaltdiode; von mir auch auf die Optokoppler-LED angewandt) | IF ≤ 0,50, PIV ≤ 0,70, P ≤ 0,50 | ebd., Table 4 „Diode Derating Requirements“ |
| Derating Chipwiderstand (RM) | P ≤ 0,60 × Nennwert bis 118 °C, U ≤ 0,80 | ebd., Sect. R, Table 4 (Style RM: 0,6 / 0,8 / 70 / 118 / 150 °C) |
| Umgebungstemperatur im Gehäuse | −10 … +60 °C | ANN |
| Lebensdauer-Abfall des Übertragungsverhältnisses (CTR) | Faktor 0,5 (konservativ); Herstellerdaten zeigen < 13 % in 25 Jahren (2σ) | MIT/Fairchild AN-3001 (50 % als Ausfallkriterium); [Würth ANO006](https://www.we-online.com/catalog/media/o303314v410%20ANO006a%20EN.pdf) |
| Gerätespannung | 21,6 … 30 V | ANN → MESS M1/M2 |
| Isolationsziel | Funktionsisolation (beide Seiten Schutzkleinspannung SELV). IEC 60664-1 ist kostenpflichtig und **nicht eingesehen** → Kriterium formal offen | – |

Das Regelwerk EEE-INST-002 ist ein Raumfahrtstandard und damit streng; es gilt so wie oben freigegeben. Gerätespannung 21,6–30 V gilt nur bis zur Messung M1/M2 und wird dann durch die Messwerte ersetzt (die Kriterien selbst bleiben unverändert).

## 1. Anforderungs-Rückverfolgbarkeit (RTM)

| # | Anforderung | Herkunft | Verifikation | Beleg / Stand | Status |
|---|---|---|---|---|---|
| A1 | ESP nur über USB versorgt | Nutzer | Inspektion | J5 Pin 1 (5V) unbeschaltet (Schaltplan-Netzliste) | ✅ erfüllt |
| A2 | Galvanische Trennung, nur über Optokoppler | Nutzer | Inspektion, GEO, Test | Gerber-Geometrie: kein Kupfer verbindet die Seiten; Mindestabstand Oberseite 7,39 mm (AUS_1↔GND), Unterseite > 10 mm. Optokoppler VISO 5000 Vrms (DB EL817 S. 2). Isolationsmessung T7 offen | ✅ Analyse / ⏳ Test |
| A3 | AUS-Ausgänge schalten nach GND; Panel-LED zwischen +24 V und AUS | **ANN** (nicht gemessen) | MESS M4/M5 | Schaltung erfüllt das bei 0–1 V Restspannung und ≤ 160 µA Leckstrom (SIM) | ⏳ Annahme |
| A4 | Taste = +24 V an EIN | **ANN** | MESS M3 | EIN-Pegel je Last in Abschnitt 3.3 | ⏳ Annahme |
| A5 | Pinbelegung Controller ↔ Emulator gleich | Nutzer | Inspektion | Controller J2.1 = AUS_0, J3.1 = EIN_0; Emulator J3.1 = AUS_0, J4.1 = EIN_0 (beide Netzlisten) | ✅ |
| A6 | Tastendruck nie dauerhaft | Nutzer | DFMEA, Test | **Nicht einzelfehlersicher:** Kurzschluss Q1 C-E oder U6 C-E sowie R15/R16 offen bei 60 °C erzeugen Dauerdruck (SIM, Abschnitt 4) | ⚠️ nur ohne Fehler erfüllt |
| A7 | Nie beide Tasten gleichzeitig | Nutzer | Firmware-Test | nur Firmware, keine Hardware-Sperre | ⏳ T10 |
| A8 | Kein Druck beim Booten / ohne USB | Nutzer | SIM, Test | Kein Druck, solange der interne Pull-up ≥ 15 kΩ ist (DB: typ. 45 kΩ, kein Mindestwert). Ohne USB fließt kein LED-Strom | ✅ SIM / ⏳ T5 |
| A9 | E05 wurde durch den Einschaltstrom ausgelöst | **Hypothese** | MESS M7, T3 | Keine Kondensatoren auf der 24-V-Seite. Vorhersage: kein Einschaltstrom über dem Dauerstrom (0,9–10 mA bei 24 V) | ⏳ |
| A10 | Schraubklemmen 5,08 mm, SMD bei JLCPCB, Rest von Hand | Nutzer | Inspektion | Footprints passen; AKSW125 mechanisch ungemessen | ⏳ M9 |
| A11 | Bestückungsorientierung korrekt | implizit | Inspektion | JLCPCB-Vorschau konnte ich nicht ansehen (in Chrome nicht eingeloggt) | ⏳ Nutzer |
| A12 | Gerät als „Bedienelement Typ 1“ registriert | Nutzer | Doku / Gerät | Wie das Gerät den Bedienteiltyp erkennt, ist unbekannt | ⏳ M8 |
| A13 | WLAN funktioniert (implizit) | implizit | DB, Test | RF-Schalter braucht GPIO3 = LOW (Seeed-Schaltplan); RSSI-Test offen | ⚠️ Firmware-Pflicht |

## 2. Grenzwerttabelle mit Derating (Worst Case 30 V, 60 °C)

Primärquellen (alle selbst geöffnet):
- EL817: Everlight DPC-0000046 Rev. 15. Die LCSC-Seite zu C63268 hat einen kaputten Datenblatt-Link; die Revision für genau EL817S1(B)(TU)-F ist deshalb **nicht bestätigt**.
- MMBT3906: JSCJ, „D, May 2012“, über LCSC C2143
- 1N4148W: Semtech Rev. 05, 20.09.2016, über C81598
- Widerstände: UNI-ROYAL Thick Film V.3, 12.02.2019, über C17414 (gilt für alle 0805-Werte)
- LED grün: Hubei KENTO KT-0805G A.0, über C2297
- ESP32-C6: Espressif-Datenblatt v1.5
- XIAO ESP32-C6: Seeed-Schaltplan v1.0 + PCB-Zip „260114“

| Bauteil | Grenzwert (DB, Seite) | Derated | Belastung 24 V | Belastung 30 V Worst | Auslastung derated | Ergebnis |
|---|---|---|---|---|---|---|
| **U6/U7 Transistor VCE (aus)** | VCEO 35 V (EL817 S. 2) | 26,25 V | 22,65 V | **28,62 V** | 86 % / **109 %** | **FAIL ab Vdev ≥ 27,5 V** |
| U6/U7 LED IF | 60 mA (S. 2) | 30 mA | 5,1–6,4 mA | 6,8 mA | 23 % | PASS |
| U1–U5 LED IF | 60 mA | 30 mA | 1,8–2,1 mA | 2,85 mA | 10 % | PASS |
| U1–U5 Transistor VCE | 35 V | 26,25 V | ≤ 3,4 V | ≤ 3,4 V | 13 % | PASS |
| Q1/Q2 VCE (aus) | VCEO 40 V (JSCJ S. 1) | 30 V | 23,3 V | 29,34 V | 98 % | PASS (knapp) |
| Q1/Q2 IC (EIN-Kurzschluss) | 200 mA | 150 mA | 23 mA | 29,3 mA | 20 % | PASS |
| Q1/Q2 Tj (Kurzschluss, 60 °C) | 150 °C, RthJA 625 K/W (JSCJ S. 1) | 110 °C | – | 62,6 °C | 57 % | PASS |
| **R1–R5 Leistung** | 125 mW bei 70 °C (UNI-ROYAL S. 6) | 75 mW | 50,0 mW | **80,7 mW** | 67 % / **108 %** | **FAIL ab Vdev ≈ 29 V** |
| R13/R14 | 125 mW | 75 mW | – | 35,5 mW | 47 % | PASS |
| R17 | 125 mW | 75 mW | 19 mW | 32 mW | 43 % | PASS |
| **R20/R21 bei EIN-Kurzschluss** | 125 mW; Kurzzeitüberlast 2,5 × RCWV für 5 s ≈ 0,78 W (UNI-ROYAL S. 6) | 75 mW | 0,53 W | **0,85 W** | **1138 %** | **FAIL** (nur Puls ≤ 300 ms; kein Impulsdiagramm im DB → Pulsfestigkeit **unbelegt**) |
| R20/R21 normal (10-k-Last) | 125 mW | 75 mW | 4 mW | 7 mW | 9 % | PASS |
| R11/R12 | 125 mW | 75 mW | 12 mW | 15 mW | 20 % | PASS |
| D7 IF | IF(AV) 150 mA (Semtech S. 1) | 75 mA | 10 mA | 46 mA (alle AUS an + EIN-Kurzschluss) | 61 % | PASS |
| D7/D8 Sperrspannung bei Verpolung | VR 75 V | 52,5 V | 24 V | 30 V | 57 % | PASS |
| D6 LED | IF 30 mA, Topr bis 85 °C (KT-0805G S. 3) | 15 mA | 0,9 mA | 1,24 mA | 8 % | PASS |
| Alle Widerstände, Spannung | 150 V (0805) | 120 V | ≤ 23 V | ≤ 29 V | 24 % | PASS |

Die Auslastung bei 30 V stammt aus `wcca_out.txt`, Abschnitt 5. Die Grenzwerte in der Vdev-Spalte stammen aus einer Bisektion im Modell.

## 3. Worst-Case-Analyse (SIM)

**Modelle** ([models.py](_qa_tools/verifikation_2026-10-15/models.py)):
- **EL817 LED:** Tabellen aus Fig. 1 (−55/25/110 °C). Unter 0,1 mA mit Idealitätsfaktor 2 extrapoliert; das ist konservativ, weil dabei bei kleiner Spannung mehr Strom fließt.
- **EL817 Übertragungsverhältnis:** aus Fig. 3 (IF 1–20 mA über −55…110 °C), unter 1 mA nach Fig. 2.
- **EL817 Dunkelstrom:** 100 nA max bei 25 °C, skaliert mit der Steigung aus Fig. 4. Das ergibt eine pessimistische Obergrenze von 5,8 µA bei 60 °C.
- **MMBT3906:** Fairchild-SPICE-Modell aus dem 2N3906/MMBT3906-Datenblatt, Stromverstärkung skaliert auf das JSCJ-Minimum (hFE 100 bei 10 mA). Ergebnis: 82,7 bei −10 °C, 68,7 bei 50 mA (JSCJ-Minimum 60).
- **1N4148W:** zwei Ecken, „typ“ und „max“. Das Max-Modell liegt ≤ 2 % über den Semtech-Maximalwerten.
- **Plausibilisierung:** [fit_check_out.txt](_qa_tools/verifikation_2026-10-15/fit_check_out.txt).
- **Unsicherheit:** Die Kennlinien sind von Hand digitalisiert (etwa ±0,01 V bzw. ±0,02 beim normierten Übertragungsverhältnis). Der Datenblattstand für die exakte LCSC-Variante ist nicht bestätigt.

### 3.1 Eingänge
- **HIGH-Reserve:** Selbst im schwächsten Fall bleibt der Pegel ≥ 3,049 V (Grenze VIH 2,40 V). Schwächster Fall heißt: CTR 130 % × 0,5 Lebensdauer, LED-Flussspannung +0,15 V, Dioden max, 1 V Restspannung im Gerät, alle 5 AUS aktiv, VDD 3,2 V.
- **Mindestspannung:** Die Eingänge lesen im schwächsten Fall noch bei **10,2 V (−10 °C) bzw. 12,6 V (60 °C)** Gerätespannung richtig.
- **LOW mit Leckstrom:** Das Gerät darf im ausgeschalteten Zustand bis **159 µA** (−10 °C) bzw. 208 µA (60 °C) pro AUS-Leitung ziehen, der Eingang liest trotzdem LOW. Prüfbar über die Spannung an R1: unter 1,6 V.

### 3.2 Ausgänge EIN
Im schwächsten Fall bleiben U6 und Q1 bei **jeder** Last bis zum Kurzschluss in Sättigung (U6 VCE ≤ 0,15 V, Q1 VCE ≤ 0,14 V). Schwächster Fall heißt hier: CTR-Minimum × Lebensdauer, VDD 3,2 V, GPIO-Innenwiderstand 50 Ω, VF +0,15 V.

EIN-Pegel bei 21,6 V / 30 V (unabhängig von der Temperatur, ±0,1 V):

| Gerätelast an EIN | offen | 47k | 10k | 4,7k | 3,3k | 2,2k | 1,5k | 1k | Kurzschluss |
|---|---|---|---|---|---|---|---|---|---|
| EIN-Spannung bei 21,6 V | 20,7 | 20,3 | 18,8 | 17,0 | 15,8 | 14,2 | 12,3 | 10,3 | 0 |
| EIN-Spannung bei 30 V | 29,1 | 28,5 | 26,4 | 23,9 | 22,2 | 19,9 | 17,3 | 14,4 | 0 |
| Strom [mA] bei 30 V | 0 | 0,6 | 2,6 | 5,1 | 6,7 | 9,0 | 11,6 | 14,4 | 28,7 |

→ Ob R20/R21 = 1 k reicht, entscheidet allein die Messung M3 (Eingangsstrom des Geräts und ab welcher Spannung es einen Druck erkennt).

### 3.3 Booten
- **Datenblatt ESP32-C6** (v1.5, Tab. 2-1, S. 17):
  - GPIO17 (U0RXD, Ausgang „runter“) hat **nach** dem Reset IE + WPU.
  - GPIO18 (SDIO_CMD, Ausgang „hoch“) hat **während** des Resets WPU.
  - GPIO16 (U0TXD, Eingang Auto) ist nach dem Reset ein Ausgang.
  - Der Pull-up ist mit **typ. 45 kΩ** angegeben, ohne Mindestwert (Tab. 5-4).
- **SIM** (stärkster Optokoppler, 30 V, 10-k-Last): kein Strom an EIN (< 0,002 µA) bei Pull-up ≥ 15 kΩ und allen Temperaturen. Ein Druck entsteht erst bei **≤ 10 kΩ**. Gegenüber dem Typwert ist die Reserve also etwa 3–4,5-fach.
- **GPIO16:** Der XIAO hat 499 Ω in Reihe (R14 im Seeed-Schaltplan). Der Gegentreiber-Strom beim Bootlog ist deshalb auf ≤ 6,6 mA begrenzt → unschädlich.

### 3.4 Monte Carlo
4000 Läufe über alle Annahme-Bereiche: Gerätespannung, Temperatur, Optokoppler-Rang, Lebensdauer-Abfall, Flussspannungen, Dioden-Ecke, VDD, GPIO-Innenwiderstand, Pull-up 20–70 k, ±1 % je Widerstand, Last.
- **0 Fehler** bei Eingang HIGH, Eingang LOW, Ausgangssättigung und Boot.
- **Schlechteste Werte:** HIGH-Reserve 0,661 V; Q1 VCE (an) 0,055 V; Boot-Strom an EIN 0,000 µA.

## 4. DFMEA – Einzelfehler

Die Werte sind simuliert ([faults_out.txt](_qa_tools/verifikation_2026-10-15/faults_out.txt)), mit stärkstem Optokoppler, 30 V und 10-k-Last.

| Fehler | Wirkung (SIM) | Schwere | Auftreten | Erkennung | Maßnahme |
|---|---|---|---|---|---|
| **Q1/Q2 C-E-Kurzschluss** | Dauerdruck, EIN 26,7 V | hoch (A6 verletzt) | gering | Gerät verstellt die Stufe ohne Befehl → Firmware kann das über AUS erkennen | Firmware-Plausibilität; Rev. 2 optional zweistufige Freigabe |
| **U6/U7 C-E-Kurzschluss** | Dauerdruck, EIN 26,7 V | hoch | gering | wie oben | wie oben |
| **R15/R16 offen (z. B. kalte Lötstelle)** | 60 °C: Dunkelstrom × hFE → **EIN 13,3 V = Dauerdruck**; 25 °C: 0,3 V (unauffällig!) | hoch | gering | **bei Raumtemperatur unsichtbar** → nur über VBE-Messung T2 | T2 bei der Inbetriebnahme; Firmware-Plausibilität |
| R18/R19 offen | Boot mit 45 k: VBE 156 mV, EIN 0 V; mit 20 k: VBE 410 mV, EIN 6 mV → noch kein Druck, aber Reserve weg | mittel | gering | T5 | T2 (Widerstand messen) |
| R13/R14 Kurzschluss | beim Druck U6 im aktiven Bereich, VCE 27,7 V bei ≈ 15 mA → ≈ 0,4 W ≫ 150 mW → U6 überlastet | mittel | sehr gering | Tastendruck funktioniert, U6 altert | keine |
| R11/R12 Kurzschluss | LED-Strom 59 mA (Grenzwert 60), GPIO überlastet (1,34 V) | mittel | sehr gering | – | keine |
| R6–R10 offen | Eingang schwebt (Emitter ohne Last) → Zufallswerte | mittel | gering | Firmware | **Firmware: interner Pull-down (45 k) zusätzlich** → definierter Zustand |
| D7 offen / 24 V fehlt / Kabel lose | alle AUS = 0 → **nicht von „Stufe aus“ zu unterscheiden** | mittel (falscher Status in HA) | mittel | keine | Rev. 2: „24 V OK“ über einen Optokoppler auf GPIO2 (frei, kein Strapping-Pin); Firmware: Zeitüberwachung nach Tastendruck |
| R20/R21 Kurzschluss + EIN-Kurzschluss (Doppelfehler) | D7 202 mA (> 150 mA), Q1 überlastet | hoch | sehr gering | – | keine |
| D7/D8 Kurzschluss | nur Verpolschutz verloren | gering | gering | – | keine |
| Durchschlag Optokoppler (Isolation) | 24 V auf der ESP-Seite und am USB | hoch | sehr gering (5 kV rms) | – | T7 Isolationsmessung |

## 5. Unabhängige Prüfung der Fertigungsdaten (GEO)

- **Werkzeug:** gerbonara 1.5 + shapely auf genau den hochgeladenen Dateien (`jlcpcb_Controller/gerbers.zip`), kein KiCad-Code. Der Sollzustand ist die Schaltplan-Netzliste; die Pads werden über ihr eigenes X2-Attribut `.P` im Gerber zugeordnet.
- **Ergebnis:** 60 + 25 Kupferinseln, 51 durchkontaktierte Bohrungen. **Alle 115 Pins der 39 Netze sind korrekt verbunden: 0 offene Verbindungen, 0 Kurzschlüsse.**
- **Abstände:** Kleinster Abstand zwischen verschiedenen Netzen 0,27 mm (Unterseite, +3V3 ↔ unbenutzter J4-Pin 3, beide auf der ESP-Seite). Isolationsabstand 24 V ↔ ESP 7,389 mm (Oberseite), auf der Unterseite > 10 mm.
- **Gegenprobe:** In der Soll-Netzliste habe ich absichtlich U6 C/E vertauscht. Der Prüfer meldet daraufhin 2 Unterbrechungen und 2 Kurzschlüsse, erkennt den Fehler also.
- **JLCPCB-Vorschau:** Nicht geprüft, weil du in Chrome bei JLCPCB nicht angemeldet bist und ich keine Passwörter eingebe. **Was du klicken musst:** jlcpcb.com → Order History → Bestellung vom 11.10. → „Production File“ / „Component Placement“. Dort für U1–U7 (Punkt am Gehäuse = Pin 1, auf der Seite der Eingangsklemmen bei U1–U5, gedreht bei U6/U7) und D1–D8 (Kathodenstrich) mit dem 3D-Render vergleichen. Kathode laut Semtech-Datenblatt = Pin 1.

## 6. XIAO ESP32-C6 – Befunde aus Seeeds eigenen Unterlagen

- **RF-Schalter-Versorgung (Pflicht):** Q3 (P-MOSFET LP0404N3T5G) mit R21 = 10 k Pull-up am Gate auf 3V3; R22 (Pull-down) ist **nicht bestückt**. Laut Schaltplanhinweis heißt das: „RF Switch Power 0: ON, 1: OFF“. GPIO3 hat nach dem Reset nur IE, also keinen Pull. → **Ohne Firmware, die GPIO3 aktiv auf LOW zieht, ist der Antennenschalter FM8625H unversorgt.**
- **Antennenwahl:** GPIO14 mit R24 = 5,1 k Pull-down → Standard ist die interne Keramikantenne (ANT1, KH5220-A36).
- **Antennenposition** (Seeed-PCB-Datei, mit `xiao_pos.py`): ANT1 sitzt 9,26 mm vom Modulmittelpunkt zum Ende gegenüber USB, 3,12 mm zur 5V/GND/3V3-Reihe. Umgerechnet auf deine Platine liegt die **Antennenmitte bei x ≈ 60,8 / y ≈ 22,9 mm**, Ausdehnung x 57,1–64,5 / y 22,4–23,9 mm. Darunter liegt Bottom-GND, der Abstand ist ≈ 11 mm. Wie stark das dämpft, ist **nicht quantifiziert** → RSSI-A/B-Test T9.
- **Versorgung:** SGM6029 (Abwärtswandler) mit 10 µF am 3V3-Ausgang (C4) → keine zusätzliche Entkopplung nötig (bestätigt die Einschätzung vom 14.10.).
- **GPIO0/1:** kein 32-kHz-Quarz bestückt, D0/D1 frei nutzbar.

## 7. Funde nach Schwere

Jeder Fund steht mit Beleg und dem Test, der ihn bestätigt oder widerlegt.

### F1 – Hoch (Firmware, Pflicht): GPIO3 muss LOW sein
- **Beleg:** Seeed-Schaltplan v1.0, Blatt 4/5 (Q3/R21/R22).
- **Firmware:**

  ```yaml
  esphome: { on_boot: { priority: 900, then: [ output.turn_off: rf_pwr ] } }
  output: [ { platform: gpio, id: rf_pwr, pin: GPIO3 } ]
  ```
- **Test T9:** RSSI mit GPIO3 = LOW gegen GPIO3 offen. Erwartung: deutlich besser mit LOW. Ist kein Unterschied messbar, war die Annahme „Schalter aus = schlechter Empfang“ falsch.

### F2 – Mittel: Derating bei hoher Gerätespannung verletzt (U6/U7, R1–R5)
- **Beleg:** Abschnitt 2. U6/U7 überschreiten die Derating-Grenze ab 27,5 V Gerätespannung, die absolute 35-V-Grenze ab ≈ 36,2 V; R1–R5 ab ≈ 29 V.
- **Rework:** Keins, wenn M1 ≤ 27 V ergibt und M2 keine Spitzen über 33 V zeigt.
- **Rev. 2:**
  - U6/U7 durch einen Optokoppler mit VCEO ≥ 70 V ersetzen (Kandidat PC817X, **Datenblatt noch nicht geprüft**).
  - R1–R5 auf 15 k erhöhen. IF sinkt dann auf ≈ 1,2 mA; die HIGH-Reserve muss neu simuliert werden.
  - Alternativ R1–R5 in 1206.
- **Test:** M1/M2; Wärmebild T8.

### F3 – Mittel (neu): R15/R16 offen → Dauerdruck nur bei Wärme
- **Beleg:** SIM (faults_out.txt), allerdings mit der pessimistischen Dunkelstrom-Obergrenze.
- **Konsequenz:** Der Fehler ist bei Raumtemperatur unsichtbar.
- **Test T2:** VBE von Q1/Q2 bei 24 V, Ausgang aus → Soll 1–2 mV, Fehler > 10 mV. Rev. 2: keine Schaltungsänderung nötig, aber T2 in die Abnahme aufnehmen.

### F4 – Mittel (neu): Ausfall der 24 V ist nicht von „Stufe aus“ zu unterscheiden
- **Beleg:** Netzliste – kein Signal meldet die 24-V-Versorgung an den ESP.
- **Firmware:** Nach jedem Tastendruck muss sich innerhalb von 2 s eine AUS-Änderung zeigen, sonst Status „unbekannt/gestört“ (die alte Retry-Logik macht das ähnlich).
- **Rev. 2:** 8. Optokoppler „24 V OK“ an GPIO2 (D2).

### F5 – Mittel: EIN-Pegel hängt vom unbekannten Eingangsstrom des Geräts ab
- **Beleg:** Tabelle 3.2.
- **Rework:** Entscheidet sich nach M3. R20/R21 nicht unter 470 Ω (dann wären es 29 V/470 Ω = 62 mA im Kurzschluss, Q1-Sättigung neu prüfen).
- **Rev. 2:** R20/R21 in 1206.

### F6 – Mittel: R20/R21 bei EIN-Kurzschluss 0,53–0,85 W, Pulsfestigkeit unbelegt
- **Beleg:** UNI-ROYAL S. 6 nennt nur 2,5 × Grenzspannung für 5 s (≈ 0,78 W bei 1 k).
- **Firmware:** maximal 300 ms pro Puls, niemals Wiederholung ohne Pause.
- **Rev. 2:** 1206 oder 2512.

### F7 – Niedrig: Booten
- **Beleg:** Reserve etwa 3-fach gegenüber dem Typwert; ein Mindestwert für den Pull-up existiert nicht.
- **Test T5:** Power-Cycle-Test mit Logic Analyzer (falsifiziert bei mindestens einem Puls).

### F8 – Niedrig: Antenne über GND-Fläche
- **Beleg:** Abschnitt 6. **Test T9.**
- **Rev. 2:** Kupfer-Sperrfläche auf beiden Lagen bei x 56–66 / y 21–26 mm, oder XIAO drehen bzw. an die Kante setzen.

### F9 – Niedrig: Eingänge ohne definierten Zustand bei offenem R6–R10
- **Firmware:** `pin: {number: GPIO0, mode: {input: true, pulldown: true}}` für alle 5 Eingänge. Unschädlich: + 0,07 mA, die HIGH-Reserve sinkt um < 0,01 V (SIM-Reserve 0,66 V).

### F10 – Info
- Isolationsabstand 7,39 mm; Kriterium nach IEC 60664-1 formal offen.
- Bestückungsorientierung → Abschnitt 5.

## 8. Messplan am echten Gerät (Phase 0.3) – das brauche ich von dir

| # | Messung | Wo / womit | Erwartung bzw. was es entscheidet |
|---|---|---|---|
| M1 | 24-V-Ruhespannung | PCB3-Klemme +24 V gegen GND, Multimeter DC | ≤ 27 V → F2 ohne Rework; > 27,5 V → Derating verletzt |
| M2 | Spitzen auf 24 V | Oszilloskop 10:1, DC-gekoppelt, Trigger 2 V über DC, 50 µs/div; Lüfter-Stufe wechseln, Gerät ein/aus | Spitze < 33 V (U6 absolut 35 V + 1,3 V Dioden) |
| M3 | EIN-Eingang des Geräts | zwischen +24 V und EIN statt der Taste: Multimeter im mA-Bereich in Reihe → Strom. Optional Labornetzteil 0→24 V an EIN: ab welcher Spannung zählt ein Druck? | entscheidet R20/R21 (F5) |
| M4 | AUS aus | Spannung AUS→GND bei dunkler Panel-LED; nach Lieferung Spannung an R1 | Leckstrom < 160 µA ⇔ Spannung an R1 < 1,6 V |
| M5 | AUS an | Spannung AUS→GND bei leuchtender LED | 0–1 V angenommen; höher → Eingang neu rechnen |
| M6 | Fehlerblinken | Oszilloskop an AUS_0 | Periode → Firmware-Filter |
| M7 | Strom am 24-V-Eingang | 10-Ω-Shunt im Minus von J1 + Oszilloskop, beim Einstecken | Vorhersage: kein Peak über dem Dauerstrom (0,9–10 mA bei 24 V); bestätigt oder widerlegt A9 |
| M8 | Bedienteil-Erkennung | Dimplex-Unterlagen, Servicemenü 21 | wie „Typ 1“ erkannt wird |
| M9 | Mechanik | Messschieber: AKSW125-Stift ⌀ und Tiefe, Buchsenleisten-Höhe, XIAO-Oberkante/USB-Mitte | Gehäuseöffnungen |
| – | Fotos PCB3 (beide Seiten) und Rohlogs hinter `build_sim_data.py` | – | Eingangs-/Ausgangsstufe des Geräts verstehen |

## 9. Inbetriebnahme- und Abnahmetests mit Sollbändern

Vorhersagen aus [bringup_out.txt](_qa_tools/verifikation_2026-10-15/bringup_out.txt): 600 Monte-Carlo-Läufe je Zustand, Labornetzteil 24,0 V, Emulator-Lasten (AUS über 2,2 k, EIN 10 k + rote LED), 20–30 °C, neue Teile. Spannungen sind gegen J1-Minus gemessen, ESP-Werte gegen XIAO-GND.

| Messpunkt | S0: alles aus | S1: AUS_0 aktiv + „hoch“ an | S2: alle 5 AUS aktiv |
|---|---|---|---|
| Strom J1 (Controller allein) | 0,91 mA | 5,58–5,70 mA | 9,83–10,07 mA |
| +24V-Schiene (R1 Pad 1) | 23,28–23,43 V | 23,16–23,34 V | 23,12–23,31 V |
| GND24 (D8 Anode) | 0,58–0,73 V | 0,61–0,77 V | 0,58–0,73 V |
| Spannung an R1 (aktiv) | 0 | 17,92–18,28 V (→ 1,79–1,83 mA) | 17,90–18,25 V |
| AUS-Klemme aktiv / inaktiv | 22,6–22,9 V | 3,92–4,05 V / 22,5–22,8 V | 3,92–4,04 V |
| GPIO-Eingang aktiv / inaktiv | ≤ 2 mV | 3,15–3,26 V / ≤ 2 mV | 3,15–3,26 V |
| GPIO-Ausgang D10 (an) | 0 | 2,97–3,23 V | 0 |
| Spannung an R11 | 0 | 1,69–2,10 V (→ 5,1–6,4 mA) | 0 |
| EIN_0 (Emulator-Last) | < 1 V (nur Leckstrom; mit 10-MΩ-Multimeter ≈ 0) | 21,20–21,40 V | < 1 V |
| Q1 VCE (an) / VBE (aus) | VBE 1–2 mV | VCE ≈ 19 mV | VBE 1–2 mV |
| U6 VCE (an) / (aus) | 22,5–22,8 V | 70–97 mV | 22,4–22,7 V |

| Test | Ablauf | Akzeptanz |
|---|---|---|
| T1 | Sichtprüfung: Polung U1–U7, D1–D8, D6; Lötstellen R15/R16/R18/R19 | Abgleich mit Render und Datenblatt |
| T2 | Ohne XIAO, 24,0 V, Strombegrenzung 50 mA: Werte S0 (24-V-Seite) und VBE Q1/Q2 | in den Bändern; VBE < 10 mV (F3) |
| T3 | Einschaltstrom J1 (Shunt + Oszilloskop) | kein Peak > 2 × Dauerstrom |
| T4 | Mit XIAO + Emulator: Zustände S0/S1/S2 | alle Werte in den Bändern |
| T5 | ≥ 500 USB-Power-Cycles + 100 langsame USB-Brownouts (5 → 3,5 V); Logic Analyzer über 100k/10k-Teiler an EIN_0/EIN_1 | **0** Pulse > 1 V |
| T6 | EIN-Kurzschluss gepulst (≤ 300 ms), Verpolung J1, USB-Abzug im Puls | Strom 20–29 mA; Verpolung < 1 µA; Puls endet |
| T7 | Isolation (XIAO gezogen): alle 24-V-Klemmen gebrückt gegen ESP-GND, 500 V DC | ≥ 100 MΩ |
| T8 | Gehäuse zu, Vdev nach M1 (ideal 30 V), alle AUS aktiv, 1 h, Wärmebild | R1–R5 und Umgebung < 70 °C bei 25 °C Raumtemperatur (ab 70 °C beginnt das Datenblatt-Derating) |
| T9 | RSSI am Einbauort: XIAO lose / eingebaut; GPIO3 LOW / offen | Differenzen dokumentieren; Ziel ≥ −75 dBm (Praxiswert, kein Standard) |
| T10 | Firmware mit Emulator: Interlock, Neustart im Puls, WLAN-Verlust, Schnellfeuer-Befehle, beide Richtungen | Logic Analyzer: Puls ≤ 300 ms (+10 %), nie beide gleichzeitig |
| T11 | Emulator gegen Gerät: EIN-Last ≈ 1,9 mA und AUS-Pegel ≈ 4 V mit M3/M5 vergleichen | bei Abweichung Emulator-Widerstände anpassen, **bevor** T10 zählt |
| T12 | Feldtest: ≥ 1000 automatische Drücke mit Rückmeldung über AUS | jeder Druck genau eine Stufe, kein E05 |

## 10. Offene Annahmen und Grenzen dieser Verifikation

- Alle Aussagen zur Geräteseite (A3, A4, A9, A12) sind **Annahmen**, bis M1–M8 vorliegen. Danach müssen die Abschnitte 2, 3 und 7 mit den Messwerten neu durchlaufen (`wcca_run.py`, Parameter Vdev/Vsat/Last).
- Datenblattstand EL817 für die exakte LCSC-Variante unbestätigt; Kennlinien von Hand digitalisiert.
- ESP-Pull-up hat keinen Mindestwert im Datenblatt; Bereich 20–70 k ist eine Annahme, die Grenzwertsuche zeigt die Reserve.
- IEC 60664-1 nicht eingesehen.
- Mechanik (Klemme, Buchsenleisten, XIAO-Höhe, Gehäuse-Kollisionsprüfung) erst nach M9 möglich.
- JLCPCB-Bestückungsvorschau: Nutzer.
