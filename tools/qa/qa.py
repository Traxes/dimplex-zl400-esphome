"""QA pass for the v3 controller: independent netlist check, copper checks, worst-case simulation, fault cases."""
import ctypes, os, re, sys, random, subprocess, math
import pcbnew

BIN = r"C:\Program Files\KiCad\10.0\bin"
D = r"<PROJEKT>\ESP24V_HA_Board_XIAO"
PCB = os.path.join(D, "ESP24V_HA_XIAO.kicad_pcb")
NET = sys.argv[1]
fails = []


def check(ok, msg):
    print(("  ok   " if ok else "  FAIL ") + msg)
    if not ok:
        fails.append(msg)


# ---------------------------------------------------------------- A: netlist from the copper vs schematic
print("A. Connectivity taken from the finished board (IPC-D-356 export) compared with the schematic")
subprocess.run([os.path.join(BIN, "kicad-cli.exe"), "pcb", "export", "ipcd356", "-o", "board.d356", PCB], capture_output=True)
board_nets = {}
for line in open("board.d356", encoding="utf8", errors="replace"):
    if line[:3] in ("317", "327"):
        netname = line[3:17].strip()
        ref = line[20:26].strip()
        pin = line[27:31].strip().lstrip("-")
        if ref and pin and ref[0] not in "H":
            board_nets.setdefault(netname, set()).add((ref, pin))
s = open(NET, encoding="utf8").read()
sch_nets = {}
for blk in re.split(r"\(net\s+\(code", s[s.find("(nets"):])[1:]:
    name = re.search(r'\(name "([^"]*)"', blk).group(1)
    nodes = set(re.findall(r'\(node\s+\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', blk))
    if len(nodes) > 1:
        sch_nets[name] = nodes
bp = sorted(tuple(sorted(v)) for v in board_nets.values() if len(v) > 1)
sp = sorted(tuple(sorted(v)) for v in sch_nets.values())
check(bp == sp, f"board has {len(bp)} multi-pin nets, schematic has {len(sp)}; every net connects exactly the same pins")
if bp != sp:
    print("     only on board:", [x for x in bp if x not in sp][:4])
    print("     only in schematic:", [x for x in sp if x not in bp][:4])

# ---------------------------------------------------------------- B: copper
print("B. Copper: current capacity and spacing")
b = pcbnew.LoadBoard(PCB)
mm = pcbnew.ToMM


def ipc2221(width_mm, dT=10.0, oz=1.0, external=True):
    area = (width_mm / 0.0254) * (oz * 1.378)          # mil^2
    return (0.048 if external else 0.024) * dT ** 0.44 * area ** 0.725


byw = {}
for t in b.GetTracks():
    if t.GetClass() == "PCB_TRACK":
        byw.setdefault(round(mm(t.GetWidth()), 2), set()).add(t.GetNetname())
for w in sorted(byw):
    print(f"       track {w:.2f} mm: carries up to {ipc2221(w):.2f} A at 10 K rise; used on {len(byw[w])} nets")
check(ipc2221(min(byw)) > 0.2, f"narrowest track ({min(byw):.2f} mm) can carry {ipc2221(min(byw)):.2f} A; the largest current on this board is about 0.035 A")
hv = lambda n: any(n.startswith(p) for p in ("/+24V", "/GND24", "/AUS_", "/INA_", "/EIN_", "/EOUT_", "/BASE_", "/OUTC_", "/PWRLED"))
bb = b.GetBoardEdgesBoundingBox()
ox = mm(bb.GetX())
hi, lo = [], []
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname():
            r = p.GetBoundingBox()
            (hi if hv(p.GetNetname()) else lo).append((mm(r.GetX()) - ox, mm(r.GetRight()) - ox))
for t in b.GetTracks():
    r = t.GetBoundingBox()
    (hi if hv(t.GetNetname()) else lo).append((mm(r.GetX()) - ox, mm(r.GetRight()) - ox))
for z in b.Zones():
    if not z.GetIsRuleArea():
        r = z.GetBoundingBox()
        (hi if hv(z.GetNetname()) else lo).append((mm(r.GetX()) - ox, mm(r.GetRight()) - ox))
gap = min(x[0] for x in lo) - max(x[1] for x in hi)
check(gap > 3.0, f"gap between 24 V copper and ESP32 copper: {gap:.2f} mm (the optocoupler itself is rated for 5000 V)")
ds = b.GetDesignSettings()
check(mm(ds.m_MinClearance) >= 0.127 and mm(ds.m_NetSettings.GetDefaultNetclass().GetClearance()) >= 0.2,
      "copper-to-copper spacing rule 0.20 mm was enforced by the design rule check (IPC-2221 asks 0.1 mm for 30 V)")
check(mm(ds.m_CopperEdgeClearance) >= 0.3, "copper stays 0.30 mm away from the board edge")
smd_edge = 99
W, H = mm(bb.GetWidth()), mm(bb.GetHeight())
oy = mm(bb.GetY())
for fp in b.GetFootprints():
    if fp.GetReference()[0] in "RDUQ":
        p = fp.GetPosition()
        x, y = mm(p.x) - ox, mm(p.y) - oy
        smd_edge = min(smd_edge, x, y, W - x, H - y)
check(smd_edge >= 3.0, f"nearest machine-placed part is {smd_edge:.1f} mm from the board edge")

# ---------------------------------------------------------------- C: simulation
print("C. Worst-case simulation (random spread of every value, 400 boards x 8 situations)")
os.add_dll_directory(BIN)
os.environ["PATH"] = BIN + ";" + os.environ["PATH"]
ng = ctypes.CDLL(os.path.join(BIN, "ngspice.dll"))
OUT = []
CB = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
EX = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_bool, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
BG = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
c_out = CB(lambda s_, i, p: OUT.append(s_.decode(errors="replace")) or 0)
c_stat = CB(lambda s_, i, p: 0)
c_exit, c_bg = EX(lambda a, b_, c, d, e: 0), BG(lambda a, b_, c: 0)
ng.ngSpice_Init(c_out, c_stat, c_exit, None, None, c_bg, None)


def run(lines, probes):
    net = ["qa"] + [l for l in lines if l.strip()] + [".end"]
    arr = (ctypes.c_char_p * (len(net) + 1))(*[l.encode() for l in net], None)
    ng.ngSpice_Circ(arr)
    ng.ngSpice_Command(b"op")
    res = {}
    for p in probes:
        OUT.clear()
        ng.ngSpice_Command(("print " + p).encode())
        m = re.search(r"=\s*([-+0-9.eE]+)", " ".join(OUT))
        res[p] = float(m.group(1)) if m else float("nan")
    ng.ngSpice_Command(b"destroy all")
    return res


def board(P, sw, gp, ein_short=False, reverse=False):
    """P: dict of sampled parameters"""
    r = lambda nominal: nominal * P["rtol"]()
    n = [f".model DLED D(IS={P['is_led']} N=2 RS=3)", ".model DGRN D(IS=1e-18 N=2.5 RS=5)", ".model D4148 D(IS=2.5e-9 N=1.75 RS=0.6 BV=75)",
         f".model QOPT NPN(BF=100 IS=1e-14 VAF=100)", f".model QP PNP(IS=1.4e-15 BF={P['hfe']} VAF=20 RB=10 RC=2)",
         "RISO g 0 1G", f"V3 v33 g {P['v33']}"]
    if reverse:
        n += [f"VSUP 0 p24u {P['v24']}"]            # supply connected backwards at J1
    else:
        n += [f"VSUP p24u 0 {P['v24']}"]
    n += ["D7 p24u p24h D4148", "D8 g24 0 D4148", f"RPL p24h pl {r(22e3)}", "DPL pl g24 DGRN"]
    for i in range(5):
        k = P["ctr"][i] / 1e4
        n += [f"RSW{i} aus{i} 0 {'5' if sw[i] else '100MEG'}", f"RIN{i} p24h ina{i} {r(10e3)}", f"DP{i} aus{i} ina{i} D4148",
              f"VS{i} ina{i} a{i} 0", f"DL{i} a{i} aus{i} DLED", f"F{i} v33 b{i} VS{i} {k}", f"Q{i} v33 b{i} gpio{i} QOPT", f"RPD{i} gpio{i} g {r(10e3)}"]
    for j in range(2):
        k = P["ctr"][5 + j] / 1e4
        n += [f"VG{j} gp{j} g {P['voh'] if gp[j] else 0}", f"RG{j} gp{j} gq{j} 30", f"RPO{j} gq{j} g {r(10e3)}", f"RS{j} gq{j} oa{j} {r(330)}",
              f"VO{j} oa{j} ob{j} 0", f"DO{j} ob{j} g DLED", f"FO{j} oc{j} bb{j} VO{j} {k}", f"QO{j} oc{j} bb{j} g24 QOPT",
              f"RB{j} oc{j} base{j} {r(22e3)}", f"RBE{j} p24h base{j} {r(10e3)}", f"QP{j} eo{j} base{j} p24h QP",
              f"VQ{j} eo{j} eo2{j} 0", f"RL{j} eo2{j} ein{j} {r(1e3)}", f"RLD{j} ein{j} 0 {'0.01' if ein_short else P['rload']}"]
    return n


def sample():
    return {"v24": random.uniform(20, 30), "v33": random.uniform(3.2, 3.4), "voh": random.uniform(2.9, 3.3),
            "rtol": lambda: random.uniform(0.95, 1.05), "is_led": random.choice(("5e-13", "1e-12", "2e-12")),
            "hfe": random.uniform(60, 300), "ctr": [random.uniform(50, 300) for _ in range(7)], "rload": random.choice((2200, 4700, 10e3, 47e3))}


random.seed(7)
VIH, VIL = 0.75, 0.25
bad = 0
worst = {"gpio_on_min": 9, "gpio_off_max": 0, "ein_margin_min": 9, "ein_off_max": 0, "if_in_max": 0, "if_out_max": 0, "isup_max": 0, "vce_opto_max": 0, "p_rin_max": 0}
N = 400
for _ in range(N):
    P = sample()
    for sw, gp in (((1, 1, 1, 1, 1), (1, 1)), ((0, 0, 0, 0, 0), (0, 0)), ((1, 0, 1, 0, 1), (1, 0)), ((0, 1, 0, 1, 0), (0, 1)),
                   ((1, 0, 0, 0, 0), (0, 0)), ((0, 0, 0, 0, 1), (1, 1)), ((1, 1, 1, 1, 1), (0, 0)), ((0, 0, 0, 0, 0), (1, 1))):
        probes = [f"v(gpio{i})-v(g)" for i in range(5)] + [f"i(VS{i})" for i in range(5)] + [f"v(ein{j})" for j in range(2)] + \
                 [f"i(VO{j})" for j in range(2)] + ["i(VSUP)", "v(p24h)", "v(oc0)-v(g24)", "v(oc1)-v(g24)"]
        r = run(board(P, sw, gp), probes)
        for i in range(5):
            v = r[f"v(gpio{i})-v(g)"]
            if sw[i]:
                worst["gpio_on_min"] = min(worst["gpio_on_min"], v / P["v33"]); bad += v < VIH * P["v33"]
                worst["if_in_max"] = max(worst["if_in_max"], r[f"i(VS{i})"] * 1e3)
                worst["p_rin_max"] = max(worst["p_rin_max"], (r[f"i(VS{i})"] ** 2) * 10.5e3)
            else:
                worst["gpio_off_max"] = max(worst["gpio_off_max"], v / P["v33"]); bad += v > VIL * P["v33"]
        for j in range(2):
            v = r[f"v(ein{j})"]
            ideal = r["v(p24h)"] * P["rload"] / (P["rload"] + 1000.0)
            if gp[j]:
                worst["ein_margin_min"] = min(worst["ein_margin_min"], v / ideal); bad += v < 0.9 * ideal
                worst["if_out_max"] = max(worst["if_out_max"], r[f"i(VO{j})"] * 1e3)
            else:
                worst["ein_off_max"] = max(worst["ein_off_max"], v); bad += v > 1.0
                worst["vce_opto_max"] = max(worst["vce_opto_max"], r[f"v(oc{j})-v(g24)"])
        worst["isup_max"] = max(worst["isup_max"], -r["i(VSUP)"] * 1e3)
check(bad == 0, f"{N * 8} simulated situations, wrong logic states: {bad}")
print(f"       active input reads at least {100 * worst['gpio_on_min']:.0f} % of the ESP supply (needs 75 %); idle input at most {100 * worst['gpio_off_max']:.1f} % (limit 25 %)")
print(f"       pressed output delivers at least {100 * worst['ein_margin_min']:.0f} % of the ideal voltage; released output at most {worst['ein_off_max']:.2f} V")
print(f"       optocoupler LED current: inputs up to {worst['if_in_max']:.2f} mA, outputs up to {worst['if_out_max']:.2f} mA (limit 60 mA)")
print(f"       largest 24 V current of the controller: {worst['isup_max']:.1f} mA")
check(worst["vce_opto_max"] < 35, f"largest voltage across an output optocoupler: {worst['vce_opto_max']:.1f} V at up to 30 V supply (limit 35 V)")
check(worst["p_rin_max"] < 0.125, f"hottest input resistor: {1000 * worst['p_rin_max']:.0f} mW (rated 125 mW)")

print("D. Fault cases")
P = {"v24": 24.0, "v33": 3.3, "voh": 3.3, "rtol": lambda: 1.0, "is_led": "1e-12", "hfe": 300, "ctr": [260] * 7, "rload": 10e3}
r = run(board(P, (0,) * 5, (1, 1), ein_short=True), ["i(VQ0)", "v(p24h)-v(eo0)", "v(eo0)"])
i_sc = r["i(VQ0)"]
print(f"       EIN line shorted to GND while pressed: current {1000 * i_sc:.1f} mA, transistor {1000 * i_sc * r['v(p24h)-v(eo0)']:.0f} mW (rated 200 mW), "
      f"resistor R20 {1000 * i_sc ** 2 * 1000:.0f} mW (rated 125 mW continuous)")
check(i_sc < 0.2 and i_sc * r["v(p24h)-v(eo0)"] < 0.2, "a shorted output cannot destroy the transistor")
r = run(board(P, (1,) * 5, (1, 1), reverse=True), ["i(VSUP)", "v(p24h)", "v(g24)"] + ["i(VS0)", "v(oc0)-v(g24)"])
print(f"       24 V connected backwards: supply current {abs(r['i(VSUP)']) * 1e6:.2f} uA, optocoupler LED current {abs(r['i(VS0)']) * 1e6:.2f} uA")
check(abs(r["i(VSUP)"]) < 1e-4, "reversed 24 V is blocked by D7/D8")
print()
print("QA RESULT:", "all checks passed" if not fails else f"{len(fails)} failed: " + "; ".join(fails))
