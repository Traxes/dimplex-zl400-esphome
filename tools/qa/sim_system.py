import ctypes, os, re, itertools

BIN = r"C:\Program Files\KiCad\10.0\bin"
os.add_dll_directory(BIN)
os.environ["PATH"] = BIN + ";" + os.environ["PATH"]
ng = ctypes.CDLL(os.path.join(BIN, "ngspice.dll"))
OUT = []
CB = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
EX = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_bool, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
BG = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)


def _out(s, i, p):
    OUT.append(s.decode(errors="replace"))
    return 0


c_out, c_stat = CB(_out), CB(lambda s, i, p: 0)
c_exit, c_bg = EX(lambda a, b, c, d, e: 0), BG(lambda a, b, c: 0)
ng.ngSpice_Init(c_out, c_stat, c_exit, None, None, c_bg, None)

MODELS = """
.model DLED D(IS=1e-12 N=2 RS=3)
.model DGRN D(IS=1e-18 N=2.5 RS=5)
.model DRED D(IS=1e-16 N=2 RS=5)
.model D4148 D(IS=2.5e-9 N=1.75 RS=0.6)
.model QOPT NPN(BF=100 IS=1e-14 VAF=100)
.model QP3906 PNP(IS=1.4e-15 BF=180 VAF=20 RB=10 RC=2)
"""


def run(lines, probes):
    net = ["system"] + [l for l in (MODELS + lines).strip().splitlines() if l.strip()] + [".end"]
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


def system(sw, gp, ctr=130, v24=24.0, gnd_wire=True):
    """emulator board + controller board wired together.  sw: 5 DIP switches, gp: 2 GPIO outputs"""
    k = ctr / 100.0 / 100.0
    n = [f"VSUP p24e 0 {v24}",                       # bench supply -> emulator J1 -> J2 -> controller J1
         "D7 p24e p24h D4148",                       # controller: protection diode in +24V
         "D8 g24 g24in D4148",                       # controller: protection diode in GND
         f"RGW g24in 0 {'0.02' if gnd_wire else '100MEG'}",
         "RPL p24h pl 22k", "DPL pl g24 DGRN",       # controller: 24V OK LED
         "RISO g 0 1G", "V3 v33 g 3.3"]              # XIAO 3V3, isolated ground
    for i in range(5):
        n += [f"RE{i} aus{i} sw{i} 2.2k", f"RSW{i} sw{i} 0 {'0.05' if sw[i] else '100MEG'}",       # emulator
              f"RLE{i} p24e le{i} 10k", f"VLE{i} le{i} lf{i} 0", f"DGE{i} lf{i} sw{i} DGRN",
              f"RIN{i} p24h ina{i} 10k", f"DP{i} aus{i} ina{i} D4148", f"VS{i} ina{i} a{i} 0",     # controller input
              f"DL{i} a{i} aus{i} DLED", f"F{i} v33 b{i} VS{i} {k}", f"Q{i} v33 b{i} gpio{i} QOPT", f"RPD{i} gpio{i} g 10k"]
    for j in range(2):
        n += [f"VG{j} gp{j} g {3.3 if gp[j] else 0}", f"RG{j} gp{j} gq{j} 30", f"RS{j} gq{j} oa{j} 330",  # controller output
              f"VO{j} oa{j} ob{j} 0", f"DO{j} ob{j} g DLED", f"FO{j} oc{j} bb{j} VO{j} {k}", f"QO{j} oc{j} bb{j} g24 QOPT",
              f"RB{j} oc{j} base{j} 22k", f"RBE{j} p24h base{j} 10k", f"QP{j} ein{j} base{j} p24h QP3906",
              f"RLR{j} ein{j} lr{j} 10k", f"VLR{j} lr{j} ls{j} 0", f"DR{j} ls{j} 0 DRED"]              # emulator red LED
    probes = [f"v(gpio{i})-v(g)" for i in range(5)] + [f"i(VLE{i})" for i in range(5)] + \
             [f"v(ein{j})" for j in range(2)] + [f"i(VLR{j})" for j in range(2)] + ["i(VSUP)", "v(p24h)", "v(g24)"]
    r = run("\n".join(n), probes)
    return ([r[f"v(gpio{i})-v(g)"] for i in range(5)], [r[f"i(VLE{i})"] * 1e3 for i in range(5)],
            [r[f"v(ein{j})"] for j in range(2)], [r[f"i(VLR{j})"] * 1e3 for j in range(2)], -r["i(VSUP)"] * 1e3, r["v(p24h)"], r["v(g24)"])


VIH, VIL = 0.75 * 3.3, 0.25 * 3.3
fail = 0
worst_hi, worst_lo, max_i = 9, 0, 0
n = 0
for ctr in (50, 130, 260):
    for v24 in (20.0, 24.0, 28.0):
        for sw in itertools.product((0, 1), repeat=5):
            for gp in itertools.product((0, 1), repeat=2):
                g, le, ein, lr, isup, p24h, g24 = system(sw, gp, ctr, v24)
                n += 1
                for i in range(5):
                    if sw[i]:
                        worst_hi = min(worst_hi, g[i]); fail += g[i] < VIH
                    else:
                        worst_lo = max(worst_lo, g[i]); fail += g[i] > VIL
                    fail += (le[i] > 1.0) != bool(sw[i])
                for j in range(2):
                    fail += (ein[j] > 0.8 * v24) != bool(gp[j])
                    fail += (lr[j] > 1.0) != bool(gp[j])
                max_i = max(max_i, isup)
print(f"{n} combinations simulated (all 32 switch patterns x 4 output states x 3 supply voltages x 3 optocoupler gains)")
print(f"lowest GPIO voltage for an active input : {worst_hi:.2f} V (needs > {VIH:.2f})")
print(f"highest GPIO voltage for an inactive one: {worst_lo:.3f} V (needs < {VIL:.2f})")
print(f"largest 24 V supply current (both boards): {max_i:.1f} mA")
print("wrong states:", fail)
print()
g, le, ein, lr, isup, p24h, g24 = system((1, 0, 1, 0, 0), (1, 0))
print("example: switches FAULT+LVL2 on, UP pressed, 24 V, CTR 130 %")
print("  GPIO D0,D1,D4,D5,D6 =", " ".join(f"{x:.2f}" for x in g), "V")
print("  emulator green LED currents =", " ".join(f"{x:.2f}" for x in le), "mA")
print("  EIN0/EIN1 =", " ".join(f"{x:.2f}" for x in ein), "V ; emulator red LED currents =", " ".join(f"{x:.2f}" for x in lr), "mA")
print(f"  controller +24V rail after diode = {p24h:.2f} V, controller GND24 = {g24:.2f} V, total supply current = {isup:.1f} mA")
print()
g, le, ein, lr, isup, p24h, g24 = system((1, 1, 1, 1, 1), (1, 1), gnd_wire=False)
print("fault: GND wire to the controller missing -> EIN =", " ".join(f"{x:.2f}" for x in ein), "V, inputs =", " ".join(f"{x:.2f}" for x in g), "V")
g, le, ein, lr, isup, p24h, g24 = system((0, 0, 0, 0, 0), (0, 0))
print(f"idle (nothing active): total supply current = {isup:.2f} mA")
