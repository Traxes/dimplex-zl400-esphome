# QA-Bericht Trax HA – ZL 400 VF Board (Controller v3 + Emulator)

Stand 14.10.2026. Geprüft wurden die Dateien in diesem Ordner. Es wurde nichts geändert; alle Arbeitsdateien liegen im Session-Scratchpad.

## 0. Was in dieser Session neu geprüft wurde

| Prüfung | Ergebnis | Beleg |
|---|---|---|
| ERC Controller / Emulator | 0 / 0 | `kicad-cli sch erc --severity-all` |
| DRC + Schaltplan-Parität Controller / Emulator | 0 Verstöße, 0 unverbunden, 0 Paritätsfehler (beide) | `kicad-cli pcb drc --schematic-parity`. Ignoriert sind nur kosmetische Prüfungen (Courtyard, Footprint-Filter, Via-Mitte) |
| Netzliste Pin für Pin gegen die Soll-Schaltung (Optokoppler-Pinout 1 A / 2 K / 3 E / 4 C, SOT-23 1 B / 2 E / 3 C, Dioden-Polung, XIAO-Pinout) | stimmt vollständig | Export als XML, Einzelprüfung aller 40 Netze |
| XIAO-Pinout gegen Seeed | D0=GPIO0, D1=1, D4=22, D5=23, D6=16, D7=17, D10=18 → stimmt. J4 links (x = 50,05), J5 rechts (x = 65,29), Pin 1 jeweils oben beim USB | [Seeed Wiki XIAO ESP32C6](https://wiki.seeedstudio.com/xiao_esp32c6_getting_started/) |
| Fertigungsdaten ↔ Platine | `order_check.py`: alle Prüfungen bestanden. **Achtung:** `.kicad_pcb` ist jünger (11.10. 18:59) als `gerbers.zip` (17:39). Ich habe die Gerber neu erzeugt: Kupfer, Lötstopp, Bestückungsdruck, Kontur und Bohrdaten sind **bytegleich** (ohne Datumszeilen). Die spätere Änderung betrifft nur Nicht-Fertigungsdaten (XIAO-3D-Modell). Die Paste-Lage weicht ab, weil `post.py` sie bewusst angepasst hat | regen in Scratchpad, `diff` |
| EL817 Grenzwerte | VCEO 35 V, VECO 6 V, IF 60 mA, IC 50 mA, PC 150 mW, ICEO ≤ 100 nA @ 20 V, CTR Rang B 130–260 % @ IF 5 mA, VCE(sat) ≤ 0,2 V @ IF 20 mA / IC 1 mA | Everlight-Datenblatt EL817 Rev. 15, S. 2–3 ([Kopie](https://sklep.msalamon.pl/download/6725)) |
| EL817 S1 Pad-Layout ↔ Footprint `SMDIP-4_W9.53mm` | Datenblatt: Pad 1,68 × 1,71 mm, Innenabstand 7,71, Außen 11,06 (Mitte 9,39 mm). Footprint: 2,0 × 1,78 mm, Mitte 9,52 mm (innen 7,52 / außen 11,52). Der Lötfuß (Spannweite ≤ 10,3 mm, Fuß ≥ 0,6 mm) liegt vollständig auf dem Pad → **passt** | Datenblatt S. 8–9 |
| AKSW125 (BerryBase) | 5,08 mm, Höhe 10 mm, Tiefe 7,6 mm, 16 A / 250 V; **Stiftdurchmesser nicht angegeben** | [BerryBase AKSW125-3P](https://www.berrybase.de/es/anschlussklemme-schraubbar-900-gewinkelt-1-25mm2-rm-5-08mm-3-polig) |

## 1. Bauteiltabelle Controller

Annahmen: Gerätespannung V = 24 V nominal, Worst Case 30 V. Die Platinen-Schiene „+24V“ liegt eine Diodenflussspannung (D7) unter V, also bei V – 0,7 V. GND24 liegt eine Flussspannung (D8) über dem Geräte-GND. GPIO-High = 3,3 V. Bei Bauteilen, deren Datenblatt ich nicht selbst geöffnet habe, steht „typ.“ – das sind Werte aus gängigen Herstellerdatenblättern, nicht für genau diese LCSC-Nummer verifiziert.

| Ref | Funktion | Wert/Typ | Grenzwerte | Belastung 24 V | Worst Case 30 V | Bewertung |
|---|---|---|---|---|---|---|
| J1 | 24-V-Eingang | MKDS-FP, bestückt AKSW125 | 16 A / 250 V | < 50 mA | < 50 mA | ok |
| J2 | AUS_0–4 | 5-pol (2+3 AKSW125) | 16 A / 250 V | 2,2 mA/Kanal | 2,8 mA | ok, Mechanik siehe F8 |
| J3 | EIN_0/1 | 2-pol AKSW125 | 16 A / 250 V | ≤ 23 mA (Kurzschluss) | ≤ 29 mA | ok |
| D7 | Verpolschutz Plus | 1N4148W | typ. IO 150 mA, VRRM 75–100 V, Ptot 400 mW | ≈ 15 mA normal | ≈ 46 mA (alle 5 AUS an + Kurzschluss an einem EIN) / Sperrspannung 30 V bei Verpolung | ok |
| D8 | Verpolschutz GND | 1N4148W | wie D7 | ≈ 2,5 mA (nur D6 + Basisströme; AUS- und EIN-Ströme fließen im Gerät zurück) | ≈ 3 mA | ok |
| D6 / R17 | LED „24V OK“ | grün 0805 / 22k | LED typ. 20 mA; 0805 125 mW | 0,97 mA / 21 mW | 1,24 mA / 34 mW | ok |
| R1–R5 | Vorwiderstand Eingangs-LED | 10k 0805 | 125 mW | 2,2 mA / 48 mW (38 %) | 2,8 mA / 78 mW (63 %) | ok (im geschlossenen Gehäuse knapp beobachten) |
| U1–U5 LED | Eingang | EL817S1(B) | IF 60 mA, VR 6 V | IF 2,2 mA | 2,8 mA | ok |
| D1–D5 | Verpolschutz LED | 1N4148W | VRRM ≥ 75 V | begrenzt VR der LED auf ≈ 0,7 V | – | ok |
| U1–U5 Transistor | Eingang ESP-Seite | EL817S1(B) | VCEO 35 V, IC 50 mA | VCE 3,3 V (aus); IC 0,33 mA (an) | – | ok. CTR-Bedarf ≥ 15 %, vorhanden ≥ 130 % (Rang B, bei kleinerem IF etwas weniger) |
| R6–R10 | Pull-down Eingang | 10k | 125 mW | 1 mW | – | ok |
| R11/R12 | LED-Strom Ausgang | 330 Ω | 125 mW | IF ≈ 6,5 mA / 14 mW | – | ok |
| R18/R19 | Pull-down Ausgang (Boot) | 10k | – | Boot: bei 45k interner Pull-up 0,6 V am GPIO → LED leitet nicht | – | ok |
| U6/U7 LED | Ausgang | EL817S1(B) | IF 60 mA | 6,5 mA | – | ok |
| **U6/U7 Transistor** | treibt Q-Basis | EL817S1(B) | **VCEO 35 V** | VCE(aus) ≈ V – 1,3 V = **22,7 V (65 %)**; IC ≈ 1,0 mA | **28,7 V (82 %)**; IC 1,3 mA | **knapp** → F1 |
| R13/R14 | Basisstrom Q1/Q2 | 22k | 125 mW | 1,0 mA / 22 mW | 1,3 mA / 38 mW | ok |
| R15/R16 | Basis-Emitter-Ableitung | 10k | – | 0,07 mA | – | ok |
| Q1/Q2 | High-Side-Schalter | MMBT3906 | typ. VCEO 40 V, IC 200 mA, hFE ≥ 100 @ 10 mA | VCE(aus) bis 23,3 V (58 %); Kurzschluss 23 mA, erzwungene Stromverstärkung 23 → gesättigt | VCE(aus) 29,3 V (73 %); 29 mA | ok (siehe F1 für Spannungsspitzen) |
| R20/R21 | Strombegrenzung EIN | 1k 0805 | 125 mW; Kurzzeitüberlast typ. 2,5 × Grenzspannung für 5 s (≈ 0,78 W) | Last 7 mA: 49 mW; **Kurzschluss 0,53 W** | **0,85 W** | ok nur gepulst → F4 |
| J4/J5 | XIAO-Sockel | 1×7 (bestückt 1×3 + 1×4) | – | – | – | ok, Mechanik → F8 |
| H1–H4 | M3 | 3,2 mm NPTH | – | – | – | ok (H1 0,2 mm versetzt, bekannt) |

## 2. Funde, nach Schwere sortiert

### F1 – Mittel: U6/U7 (und Q1/Q2) haben wenig Reserve gegen Spannungsspitzen auf der 24-V-Leitung
- **Beleg:** Laut EL817-Datenblatt ist VCEO = 35 V. Der Ausgangs-Fototransistor sieht im ausgeschalteten Zustand fast die volle Platinenspannung: 22,7 V bei 24 V, 28,7 V bei 30 V. Auf der 24-V-Seite gibt es weder Kondensator noch Begrenzer (bewusst, wegen des Einschaltstroms). Im Gerät laufen Lüftermotoren, Spitzen auf der 24-V-Leitung sind also plausibel – **nicht gemessen**.
- **Konsequenz:** Bei einer Spitze über ≈ 35,7 V bricht der Fototransistor durch. Dann leitet Q1 und erzeugt einen Tastendruck, der so kurz ist wie die Spitze selbst. Wiederholte Durchbrüche können den Optokoppler schädigen. Q1 (VCEO typ. 40 V) liegt nur knapp darüber.
- Eine TVS-Diode hilft hier **nicht**: Eine 30-V-TVS klemmt erst bei ≈ 48 V.
- **Rework:** Keins nötig, wenn die gemessene Gerätespannung (Multimeter, besser Oszilloskop beim Anlaufen des Lüfters) ≤ 26 V ist und keine Spitzen über 33 V zeigt.
- **Rev. 2:** U6/U7 durch einen Optokoppler mit VCEO ≥ 70 V ersetzen. Kandidat: PC817X…CSP9F (C66405). Dessen 80 V habe ich noch **nicht** im Datenblatt geprüft, und die Footprint-Passung ist offen. Q1/Q2 durch einen PNP mit VCEO ≥ 60 V ersetzen, z. B. MMBT5401 (150 V); dann Basisstrom und hFE neu rechnen. U1–U5 sehen nur 3,3 V und bleiben unverändert.

### F2 – Mittel: EIN-Pegel hängt vom unbekannten Eingangsstrom des Geräts ab (bekannt, weiter offen)
- **Beleg:** Durch R20 = 1 k fallen pro mA Laststrom 1 V ab: 22,3 V bei 1 mA, 16 V bei 7 mA, 11,6 V bei 12 mA.
- **Rework:** Erst den Strom messen. Liegt er über ≈ 8 mA, R20/R21 auf 470 Ω tauschen, **nicht kleiner**. Bei 330 Ω wären es im Kurzschluss ≈ 70 mA; dann reicht die Basis-Ansteuerung (≈ 1 mA) nicht mehr zur Sättigung, Q1 wird heiß.
- **Rev. 2:** Wert nach der Messung festlegen, Bauform 1206 (250 mW), Basisstrom passend erhöhen.

### F3 – Mittel: WLAN – Antenne über GND-Fläche, RF-Schalter nicht konfiguriert
- **Beleg:** Die Keramikantenne des XIAO C6 sitzt am Ende gegenüber dem USB-Anschluss. Das entnehme ich Produktfotos und dem Modell der Vorsession (`mk_xiao3d.py` Z. 43); Seeed gibt es nicht in Textform an → **unsicher**. Auf der Platine liegt dort Bottom-GND, durchgehend von x = 37,65 bis 74,55 mm. Laut Seeed muss GPIO3 auf LOW gesetzt werden, damit die RF-Schalter-Steuerung aktiv ist. GPIO14 = LOW wählt die interne Antenne.
- **Konsequenz:** Reichweite eventuell reduziert; die 11 mm Abstand mildern das. Unbewertet.
- **Firmware:** GPIO3 und GPIO14 früh im Boot auf LOW setzen (Snippet unten). Danach den RSSI-Sensor am Einbauort ablesen.
- **Rework:** keins.
- **Rev. 2:** Kupfer-Sperrfläche auf **beiden** Lagen unter dem Antennenende (≈ 8 × 6 mm). Besser noch: den XIAO so platzieren, dass das Antennenende über der Platinenkante oder einer Aussparung liegt.

### F4 – Niedrig/Mittel: „Nie dauerhaft / nie beide gleichzeitig“ sichert nur die Firmware
- **Beleg:** Die Schaltung ist DC-gekoppelt. Bleibt ein GPIO hängen, entsteht ein Dauerdruck. Steht dabei EIN im Kurzschluss, wird R20 mit 0,53–0,85 W überlastet (siehe Tabelle).
- **Firmware:** Interlock, `restore_mode: ALWAYS_OFF`, 300-ms-Pulse über `button: platform: output` (endet hardwareunabhängig über einen Timer). Den Task-Watchdog nicht abschalten.
- **Rev. 2 (optional):** Sicherheit in Hardware, z. B. R20/R21 in 1206 oder eine selbstrückstellende Sicherung; die beiden Ausgänge können sich über U6/U7 gegenseitig sperren.

### F5 – Niedrig: GPIO16 (D6, Eingang Auto) ist U0TXD
- **Beleg:** Der ROM-Bootloader gibt das Bootlog auf GPIO16 aus. Ist die Auto-LED aktiv, treibt der GPIO beim LOW-Pegel gegen den Fototransistor. Den Strom begrenzt CTR × IF ≤ 2,6 × 2,8 mA ≈ 7 mA, und das nur für wenige ms → unschädlich.
- **Firmware:** Eingänge erst nach dem Boot auswerten (das alte `on_boot`-Delay von 2 s beibehalten). GPIO17 (D7, runter) ist durch R19 sicher, siehe Tabelle.

### F6 – Niedrig: Fehlerleitung blinkt (bekannt)
- **Firmware:** `delayed_off: 2s` am Fehlereingang (Halbperiode ≈ 0,5 s laut Messdaten).

### F7 – Niedrig: Bestückungsorientierung U1–U7, D1–D8, D6 nicht dokumentiert geprüft
- **Beleg:** Laut Übergabe wurde nur Q1/Q2 in der JLCPCB-Vorschau kontrolliert. Die CPL-Rotationen sind U1–U5 0°, U6/U7 180°, D1–D5 270°, D7 180°, D8 0°.
- **Maßnahme:** In der JLCPCB-Bestellung die Bauteilvorschau ansehen (nur lesen) oder auf die DFM-Rückfrage von JLCPCB achten. Nach Lieferung die Pin-1-Markierungen per Lupe prüfen.

### F8 – Niedrig: Mechanik der Handbestückungsteile nicht verifiziert
- **AKSW125:** Stiftdurchmesser nicht angegeben; für die 1,3-mm-Bohrung brauchen die Stifte ≤ 1,1 mm. Tiefe 7,6 mm statt MKDS ≈ 9,8 mm (FP-Courtyard 0,91–11,8 mm), deshalb sitzt die Kabeleinführung vermutlich ≈ 1 mm weiter von der Kante entfernt. Höhe 10 mm. → Mit dem Messschieber prüfen, bevor die Gehäuseöffnungen gedruckt werden.
- **Buchsenleisten 1×3 + 1×4:** passen im Raster, wenn jede Leiste genau n × 2,54 mm lang ist; die Stirnseiten dürfen keinen Grat haben. Höhe nachmessen (angenommen 8,5 mm).
- **XIAO:** Gesamthöhe und USB-Lage sind aus Datenblattwerten gerechnet. Nach dem Stecken Höhe Oberkante und Mitte USB über der Platinenunterseite messen und mit der Gehäuseöffnung (Mitte 18,9 mm über Boden) vergleichen.

### F9 – Info: Entkopplung ESP-Seite
- Keine Kondensatoren auf der ESP-Seite. Die Lasten sind 5 × 0,33 mA + 2 × 6,5 mA, statisch geschaltet und direkt neben dem XIAO, der eigene Regler-Kondensatoren hat → **ok**, keine Änderung nötig. Für Rev. 2 optional 100 nF an J5 (3V3–GND), ohne Nachteil.

### F10 – Info: JLCPCB-Hinweise (Linienbreite 0,12 mm Bestückungsdruck, Lötstopp–Kupfer 0,04 mm an GND-Thermals)
- Die Lötstopp-Meldungen betreffen dasselbe Netz → elektrisch harmlos. Ich habe sie nicht selbst bei JLCPCB gesehen, die Einstufung ist plausibel, aber **nicht verifiziert**.

## 3. Emulator (nicht bestellt)

| Punkt | Bewertung |
|---|---|
| Netzliste | stimmt: AUS_i über R 2,2k und DIP-Schalter nach GND; grüne LED + 10k von +24V an derselben Schalterseite; rote LED + 10k von EIN nach GND |
| DIP-Strom | geschlossen: 2,2 mA grüne LED + 1,8 mA Controller ≈ **4 mA** (Übergabe sagte 16 mA). Worst Case AUS direkt an +24V: 11 mA. Grenzwert NT 05 25 mA → ok |
| EIN-Last | ≈ 1,9 mA → bildet ein Gerät mit kleinem Eingangsstrom nach; nach der EIN-Messung (F2) R11/R12 eventuell an den Messwert anpassen |
| Steckverbinder | J3/J4 sind 2,54-mm-Buchsenleisten, der Controller hat Schraubklemmen → Verbindung nur über Adapterkabel (Dupont-Stift → Aderendhülse) |
| Beschriftung | 0,135 mm < 0,15 mm → vor der Bestellung auf 0,15 mm setzen |
| LED-Polung JLCPCB | ungeprüft (D1–D5 180°, D6/D7 0°) → in der Vorschau prüfen |
| Schutz | kein Verpolschutz; für ein Labornetzteil mit Strombegrenzung akzeptabel, sonst eine Diode wie beim Controller |

## 4. Firmware-Vorschlag (Ausschnitt, ohne Zugangsdaten)

```yaml
esp32:
  variant: esp32c6
  framework: { type: esp-idf }
logger:
  hardware_uart: USB_SERIAL_JTAG
esphome:
  on_boot:
    - priority: 900          # vor WLAN-Start
      then:
        - output.turn_off: rf_switch_en   # GPIO3 LOW = RF-Schalter aktiv (Seeed)
        - output.turn_off: ant_select     # GPIO14 LOW = interne Antenne
output:
  - { platform: gpio, id: rf_switch_en, pin: GPIO3 }
  - { platform: gpio, id: ant_select,  pin: GPIO14 }
  - { platform: gpio, id: out_up,   pin: GPIO18 }   # D10, ohne inverted
  - { platform: gpio, id: out_down, pin: GPIO17 }   # D7
binary_sensor:
  - platform: gpio
    pin: GPIO0          # D0 Fehler
    name: "Fehler/Filter"
    filters: [ delayed_off: 2s ]
sensor:
  - platform: wifi_signal
    name: "WLAN RSSI"
```
Die Bedingung „nie beide gleichzeitig“ sichert das Skript ab: Vor jedem Druck auf die eine Taste wird die andere ausgeschaltet. Das bestehende `vent_step` ruft immer nur eine Taste auf.

## 5. Nächste Schritte

1. **Messen** (Nutzer): Gerätespannung (am besten mit Oszilloskop beim Lüfteranlauf), EIN-Eingangsstrom, Stiftdurchmesser und Tiefe der AKSW125, Höhe der Buchsenleisten.
2. **Rework** nach Messung: höchstens R20/R21 auf ≥ 470 Ω.
3. **Firmware:** GPIO3/14, Fehlerfilter, Interlock, RSSI.
4. **Rev. 2** (nach Freigabe, als Kopie `ESP24V_HA_Board_XIAO_rev2\`): Optokoppler/PNP mit höherer Spannungsfestigkeit, Antennen-Sperrfläche, R20/R21 in 1206 mit gemessenem Wert, optional 100 nF ESP-Seite. Danach komplette Neuprüfung.
