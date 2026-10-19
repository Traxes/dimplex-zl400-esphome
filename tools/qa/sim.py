import ctypes, os, re, sys

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


c_out = CB(_out)
c_stat = CB(lambda s, i, p: 0)
c_exit = EX(lambda a, b, c, d, e: 0)
c_bg = BG(lambda a, b, c: 0)
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
    OUT.clear()
    net = ["sim"] + [l for l in (MODELS + lines).strip().splitlines() if l.strip()] + [".end"]
    arr = (ctypes.c_char_p * (len(net) + 1))(*[l.encode() for l in net], None)
    ng.ngSpice_Circ(arr)
    ng.ngSpice_Command(b"op")
    res = {}
    for p in probes:
        OUT.clear()
        ng.ngSpice_Command(("print " + p).encode())
        txt = " ".join(OUT)
        m = re.search(r"=\s*([-+0-9.eE]+)", txt)
        res[p] = float(m.group(1)) if m else float("nan")
    ng.ngSpice_Command(b"destroy all")
    return res


def input_channel(v24, ctr, case):
    k = ctr / 100.0 / 100.0   # photo current into the base = CTR/BF * I_led
    term = {
        "unit ON (line pulled to GND)": "RU aus 0 5",
        "unit OFF (line open)": "RU aus 0 100MEG",
        "emulator switch ON": "R22 aus sw 2.2k\nRSW sw 0 0.05\nRLE p24 le 10k\nDG le sw DGRN",
        "emulator switch OFF": "R22 aus sw 2.2k\nRSW sw 0 100MEG\nRLE p24 le 10k\nDG le sw DGRN",
    }[case]
    n = f"""
V24 p24 0 {v24}
RIN p24 ina 10k
DP aus ina D4148
VS ina a2 0
DL a2 aus DLED
{term}
RISO g 0 1G
V3 v33 g 3.3
F1 v33 b VS {k}
Q1 v33 b gpio QOPT
RPD gpio g 10k
"""
    r = run(n, ["v(gpio)-v(g)", "i(VS)"])
    return r["v(gpio)-v(g)"], r["i(VS)"] * 1e3


def output_channel(vgpio, ctr, load, v24=24.0):
    k = ctr / 100.0 / 100.0
    ld = {
        "10k input": "RL ein 0 10k",
        "4.7k input": "RL ein 0 4.7k",
        "1k input (heavy)": "RL ein 0 1k",
        "emulator (10k + red LED)": "RL ein le2 10k\nDR le2 0 DRED",
    }[load]
    n = f"""
RISO g 0 1G
VG gp g {vgpio}
RG gp g1 30
RS g1 oa 330
VS oa ob 0
DL ob g DLED
V24 p24 0 {v24}
F2 outc b2 VS {k}
Q2 outc b2 0 QOPT
RB outc base 22k
RBE p24 base 10k
QP ein base p24 QP3906
{ld}
"""
    r = run(n, ["v(ein)", "i(VS)", "v(p24)-v(base)", "v(outc)"])
    return r["v(ein)"], r["i(VS)"] * 1e3, r["v(p24)-v(base)"], r["v(outc)"]


VIH, VIL = 0.75 * 3.3, 0.25 * 3.3
print("=== INPUT CHANNEL: GPIO voltage (ESP32 reads HIGH above %.2f V, LOW below %.2f V) ===" % (VIH, VIL))
bad = 0
for case in ("unit ON (line pulled to GND)", "emulator switch ON", "unit OFF (line open)", "emulator switch OFF"):
    want_high = "ON" in case
    for v24 in (20.0, 24.0, 28.0):
        for ctr in (50, 130, 260):
            v, i = input_channel(v24, ctr, case)
            ok = (v > VIH) if want_high else (v < VIL)
            bad += not ok
            print(f"{case:30s} 24V={v24:4.0f}  CTR={ctr:3d}%  I_led={i:5.2f} mA  GPIO={v:5.2f} V  {'OK' if ok else 'FAIL'}")
print()
print("=== OUTPUT CHANNEL: voltage on the EIN line ===")
for vg, state in ((3.3, "GPIO HIGH"), (0.0, "GPIO LOW")):
    for load in ("10k input", "4.7k input", "1k input (heavy)", "emulator (10k + red LED)"):
        for ctr in (50, 130, 260):
            v, i, vbe, voc = output_channel(vg, ctr, load)
            ok = (v > 22.0) if vg > 1 else (v < 1.0)
            bad += not ok
            print(f"{state:9s} load={load:26s} CTR={ctr:3d}%  I_led={i:5.2f} mA  EIN={v:6.2f} V  Veb={vbe:5.2f} V  opto Vce={voc:5.2f} V  {'OK' if ok else 'FAIL'}")
print()
print("failures:", bad)
