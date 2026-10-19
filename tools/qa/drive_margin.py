"""How much drive does an ESP32 pin really need for the up/down outputs of the v3 controller?"""
import ctypes, os, re

BIN = r"C:\Program Files\KiCad\10.0\bin"
os.add_dll_directory(BIN)
os.environ["PATH"] = BIN + ";" + os.environ["PATH"]
ng = ctypes.CDLL(os.path.join(BIN, "ngspice.dll"))
OUT = []
CB = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
EX = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_bool, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
BG = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
c_out = CB(lambda s, i, p: OUT.append(s.decode(errors="replace")) or 0)
c_stat = CB(lambda s, i, p: 0)
c_exit, c_bg = EX(lambda a, b, c, d, e: 0), BG(lambda a, b, c: 0)
ng.ngSpice_Init(c_out, c_stat, c_exit, None, None, c_bg, None)


def run(lines, probes):
    net = ["drive"] + lines + [".end"]
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


def out(vpin, rpin, ctr, hfe, rload, v24=24.0):
    """vpin: open-circuit pin voltage, rpin: internal resistance of the ESP32 pin driver"""
    k = ctr / 1e4
    n = [".model DLED D(IS=1e-12 N=2 RS=3)", ".model D4148 D(IS=2.5e-9 N=1.75 RS=0.6)", ".model QOPT NPN(BF=100 IS=1e-14 VAF=100)",
         f".model QP PNP(IS=1.4e-15 BF={hfe} VAF=20 RB=10 RC=2)", "RISO g 0 1G",
         f"VSUP p24u 0 {v24}", "D7 p24u p24h D4148", "D8 g24 0 D4148",
         f"VG gp g {vpin}", f"RG gp pin {rpin}", "RPO pin g 10k", "RS pin oa 330", "VO oa ob 0", "DO ob g DLED",
         f"FO oc bb VO {k}", "QO oc bb g24 QOPT", "RB oc base 22k", "RBE p24h base 10k", "QP eo base p24h QP",
         "RL eo ein 1k", f"RLD ein 0 {rload}"]
    r = run(n, ["v(ein)", "i(VO)", "v(pin)-v(g)", "v(p24h)"])
    ideal = r["v(p24h)"] * rload / (rload + 1000.0)
    return r["v(ein)"] / ideal, r["i(VO)"] * 1e3, r["v(pin)-v(g)"]


print("Normal operation (pin 3.3 V, typical 30 ohm driver):")
ratio, i, vp = out(3.3, 30, 130, 100, 4700)
print(f"  pin delivers {i:.2f} mA at {vp:.2f} V -> output reaches {100 * ratio:.0f} % of full level")
print()
print("How weak may the pin get before the output stops switching fully (>= 90 % of full level)?")
for ctr, hfe, rload, label in ((130, 100, 4700, "typical parts, 4.7k load"), (50, 60, 2200, "worst parts, heavy 2.2k load"), (50, 60, 10000, "worst parts, 10k load")):
    # weakest pin current
    lo, hi = 0.0, 3.3
    for _ in range(30):
        mid = (lo + hi) / 2
        if out(mid, 30, ctr, hfe, rload)[0] >= 0.9:
            hi = mid
        else:
            lo = mid
    r_, i_, vp_ = out(hi, 30, ctr, hfe, rload)
    # largest tolerable driver resistance at 3.3 V
    lo2, hi2 = 30.0, 20000.0
    for _ in range(30):
        mid = (lo2 + hi2) / 2
        if out(3.3, mid, ctr, hfe, rload)[0] >= 0.9:
            lo2 = mid
        else:
            hi2 = mid
    print(f"  {label:30s}: needs only {i_:.2f} mA ({vp_:.2f} V at the pin); still works with a pin resistance up to {lo2:.0f} ohm")
print()
ratio, i, vp = out(3.3, 30, 50, 60, 2200)
print(f"Design current is {i:.1f} mA. An ESP32-C6/C5 pin is specified for about 20 mA at its default drive strength.")
