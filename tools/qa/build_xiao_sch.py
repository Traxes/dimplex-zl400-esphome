import kc, json, os, shutil

ROOT = "<PROJEKT>"
SRC = ROOT + "/ESP24V_HA_Board"
D = ROOT + "/ESP24V_HA_Board_XIAO"
S = D + "/ESP24V_HA_XIAO.kicad_sch"
os.makedirs(D, exist_ok=True)
assert os.path.exists(D + "/ESP24V_HA_XIAO.kicad_pro")
if os.path.exists(S):
    os.remove(S)

R = "Resistor_SMD:R_0805_2012Metric"
LED = "LED_SMD:LED_0805_2012Metric"
OPTO = "Package_DIP:SMDIP-4_W9.53mm"
TB = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-%d-5.08_1x0%d_P5.08mm_Horizontal"
SOCK = "Connector_PinSocket_2.54mm:PinSocket_1x07_P2.54mm_Vertical"
comps = []


def C(lib, ref, val, x, y, fp=None, rot=0):
    d = {"lib_id": lib, "reference": ref, "value": val, "x": x, "y": y, "rotation": rot}
    if fp:
        d["footprint"] = fp
    comps.append(d)


# XIAO left header (top to bottom, USB up): D0 D1 D2 D3 D4 D5 D6 ; right header: 5V GND 3V3 D10 D9 D8 D7
GP = [("IN_FAULT_D0", 1), ("IN_L1_D1", 2), ("IN_L2_D4", 5), ("IN_L3_D5", 6), ("IN_AUTO_D6", 7)]
OUT = [("OUT_UP_D10", 4), ("OUT_DN_D7", 7)]
nets = {"+24V_IN": [("J1", "1"), ("D7", "2")], "+24V": [("D7", "1")], "GND24_IN": [("J1", "2"), ("D8", "1")], "GND24": [("D8", "2")], "+3V3": [("J5", "3")], "GND": [("J5", "2")]}


def N(net, ref, pin):
    nets.setdefault(net, []).append((ref, str(pin)))


C("Connector:Screw_Terminal_01x02", "J1", "24V_from_unit", 38.1, 38.1, TB % (2, 2))
C("Diode:1N4148W", "D7", "1N4148W", 63.5, 30.48, "Diode_SMD:D_SOD-123")
C("Diode:1N4148W", "D8", "1N4148W", 63.5, 45.72, "Diode_SMD:D_SOD-123")
C("Connector:Screw_Terminal_01x05", "J2", "AUS_0-4_unit_outputs", 38.1, 76.2, TB % (5, 5))
C("Connector:Screw_Terminal_01x02", "J3", "EIN_0-1_unit_inputs", 38.1, 114.3, TB % (2, 2))
for i in range(5):
    y = 50.8 + 30.48 * i
    C("Device:R", f"R{1 + i}", "10k", 88.9, y, R)
    C("Diode:1N4148W", f"D{1 + i}", "1N4148W", 109.22, y, "Diode_SMD:D_SOD-123")
    C("Isolator:PC817", f"U{1 + i}", "EL817S", 139.7, y, OPTO)
    C("Device:R", f"R{6 + i}", "10k", 170.18, y, R)
    N("+24V", f"R{1 + i}", 1); N(f"INA_{i}", f"R{1 + i}", 2); N(f"INA_{i}", f"D{1 + i}", 1); N(f"INA_{i}", f"U{1 + i}", 1)
    N(f"AUS_{i}", f"D{1 + i}", 2); N(f"AUS_{i}", f"U{1 + i}", 2); N(f"AUS_{i}", "J2", i + 1)
    N("+3V3", f"U{1 + i}", 4); N(GP[i][0], f"U{1 + i}", 3); N(GP[i][0], f"R{6 + i}", 1); N("GND", f"R{6 + i}", 2)
    N(GP[i][0], "J4", GP[i][1])
for j in range(2):
    y = 210.82 + 30.48 * j
    C("Device:R", f"R{11 + j}", "330", 88.9, y, R)
    C("Isolator:PC817", f"U{6 + j}", "EL817S", 119.38, y, OPTO)
    C("Device:R", f"R{13 + j}", "22k", 149.86, y, R)
    C("Device:R", f"R{15 + j}", "10k", 170.18, y, R)
    C("Transistor_BJT:MMBT3906", f"Q{1 + j}", "MMBT3906", 195.58, y, "Package_TO_SOT_SMD:SOT-23")
    C("Device:R", f"R{20 + j}", "1k", 215.9, y, R)
    N(OUT[j][0], f"R{11 + j}", 1); N(f"OUTA_{j}", f"R{11 + j}", 2); N(f"OUTA_{j}", f"U{6 + j}", 1); N("GND", f"U{6 + j}", 2)
    N(f"OUTC_{j}", f"U{6 + j}", 4); N(f"OUTC_{j}", f"R{13 + j}", 1); N("GND24", f"U{6 + j}", 3)
    N(f"BASE_{j}", f"R{13 + j}", 2); N(f"BASE_{j}", f"R{15 + j}", 2); N("+24V", f"R{15 + j}", 1)
    N(f"BASE_{j}", f"Q{1 + j}", 1); N("+24V", f"Q{1 + j}", 2); N(f"EOUT_{j}", f"Q{1 + j}", 3); N(f"EOUT_{j}", f"R{20 + j}", 2); N(f"EIN_{j}", f"R{20 + j}", 1); N(f"EIN_{j}", "J3", j + 1)
    N(OUT[j][0], "J5", OUT[j][1])
    C("Device:R", f"R{18 + j}", "10k", 68.58, y + 12.7, R)
    N(OUT[j][0], f"R{18 + j}", 1); N("GND", f"R{18 + j}", 2)
C("Device:R", "R17", "22k", 218.44, 38.1, R)
C("Device:LED", "D6", "GREEN", 238.76, 38.1, LED)
N("+24V", "R17", 1); N("PWRLED", "R17", 2); N("PWRLED", "D6", 2); N("GND24", "D6", 1)
C("Connector_Generic:Conn_01x07", "J4", "XIAO_left_D0-D6", 259.08, 127.0, SOCK)
C("Connector_Generic:Conn_01x07", "J5", "XIAO_right_5V_GND_3V3_D10-D7", 320.04, 127.0, SOCK)
for i in range(4):
    C("Mechanical:MountingHole", f"H{1 + i}", "M3", 259.08 + 15.24 * i, 248.92, "MountingHole:MountingHole_3.2mm_M3")

TS = ("sch_hierarchy", "sch_batch", "sch_wiring", "sch_components", "sch_analysis", "sch_export")
calls = [("load_toolset", {"name": n}) for n in TS]
calls += [("create_schematic", {"path": S, "size": "A3"}), ("batch_place_components", {"schematic": S, "components": comps})]
for n, p in nets.items():
    calls.append(("batch_connect_to_net", {"schematic": S, "net": n, "stub_length": 2.54, "pins": [{"reference": a, "pin_number": b} for a, b in p]}))
calls.append(("batch_get_schematic_pin_locations", {"schematic": S, "references": ["J4", "J5"]}))
res = kc.run(calls)
ok = True
for (m, _), r in zip(calls, res):
    if m == "load_toolset":
        continue
    t = r.get('result', {}).get('content', [{}])[0].get('text', json.dumps(r))
    try:
        dd = json.loads(t)
        errs = dd.get('errors') or dd.get('failures')
    except Exception:
        errs = None
    if r.get('result', {}).get('isError') or errs:
        ok = False
        print("ERR", m, '|', t[:900])
print("build ok:", ok)
used = {(a, b) for p in nets.values() for a, b in p}
pl = json.loads(res[-1]['result']['content'][0]['text'])
nc = [{"x": round(p['x'], 2), "y": round(p['y'], 2)} for c in pl['components'] for p in c['pins'] if (c.get('reference'), p['number']) not in used]

edits = [{"reference": f"R{i}", "fields": {"LCSC": "C17414"}} for i in list(range(1, 11)) + [15, 16, 18, 19]]
edits += [{"reference": f"R{i}", "fields": {"LCSC": "C17630"}} for i in (11, 12)] + [{"reference": f"R{i}", "fields": {"LCSC": "C17513"}} for i in (20, 21)] + [{"reference": f"R{i}", "fields": {"LCSC": "C17560"}} for i in (13, 14, 17)]
edits += [{"reference": f"D{i}", "fields": {"LCSC": "C81598"}} for i in (1, 2, 3, 4, 5, 7, 8)] + [{"reference": "D6", "fields": {"LCSC": "C2297"}}]
edits += [{"reference": f"U{i}", "fields": {"LCSC": "C63268"}} for i in range(1, 8)] + [{"reference": f"Q{i}", "fields": {"LCSC": "C2143"}} for i in (1, 2)]
calls = [("load_toolset", {"name": n}) for n in TS]
calls += [("batch_add_no_connect", {"schematic": S, "positions": nc}), ("batch_edit_schematic_components", {"schematic": S, "create_missing": True, "edits": edits})]


def T(t, x, y, size=1.8, bold=False):
    calls.append(("add_schematic_text", {"schematic": S, "text": t, "x": x, "y": y, "size": size, "bold": bold, "justify": "left"}))


T("Trax HA - ZL 400 VF Board (XIAO) - Home Assistant controller for Dimplex ZL 300/400 VF (terminal board PCB3)", 25.4, 17.78, 3, True)
T("24 V SIDE (from the ventilation unit). Fully isolated from the ESP32 side: no shared ground. D7 and D8 protect against reversed 24 V.", 25.4, 22.86)
T("INPUTS: the unit pulls an AUS line to GND when active -> optocoupler LED lights (2.3 mA)\n-> GPIO goes HIGH (10k pull-down). Diode protects the optocoupler against reversed wiring.", 76.2, 36.83)
T("OUTPUTS: GPIO HIGH -> optocoupler -> PNP transistor puts +24 V on the EIN line (like pressing the panel button). R18/R19 hold the outputs off while the ESP32 boots or is unpowered. R20/R21 limit the current if an EIN line is shorted.", 76.2, 198.12)
T("Seeed XIAO ESP32-C6 (ESP32-C5 fits with other GPIO numbers), USB-C power only.\nLeft header: D0 D1 D2 D3 D4 D5 D6   Right header: 5V GND 3V3 D10 D9 D8 D7\nD2, D3, D8, D9 are left unused: they are boot strapping pins on some XIAO variants.", 246.38, 88.9)
T("AUS_0 fault -> D0   AUS_1 level 1 -> D1   AUS_2 level 2 -> D4   AUS_3 level 3 -> D5   AUS_4 auto -> D6\nEIN_0 up <- D10   EIN_1 down <- D7", 25.4, 271.78)
calls += [("validate_wire_connections", {"schematic": S}), ("validate_component_connections", {"schematic": S}), ("find_shorted_nets", {"schematic": S}), ("run_erc", {"schematic": S})]
for (m, _), r in zip(calls, kc.run(calls)):
    if m in ("load_toolset", "add_schematic_text"):
        continue
    print(("ERR " if r['result'].get('isError') else "ok  ") + m, '|', r['result']['content'][0]['text'][:260])
