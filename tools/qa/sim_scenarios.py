"""Time-domain replay of situations taken from build_sim_data.py on the v3 controller circuit."""
import ctypes, os

BIN = r"C:\Program Files\KiCad\10.0\bin"
os.add_dll_directory(BIN)
os.environ["PATH"] = BIN + ";" + os.environ["PATH"]
ng = ctypes.CDLL(os.path.join(BIN, "ngspice.dll"))
CB = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
EX = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_bool, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
BG = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
LOG = []
c_out = CB(lambda s, i, p: LOG.append(s.decode(errors="replace")) or 0)
c_stat = CB(lambda s, i, p: 0)
c_exit, c_bg = EX(lambda a, b, c, d, e: 0), BG(lambda a, b, c: 0)
ng.ngSpice_Init(c_out, c_stat, c_exit, None, None, c_bg, None)


class VecInfo(ctypes.Structure):
    _fields_ = [("name", ctypes.c_char_p), ("type", ctypes.c_int), ("flags", ctypes.c_short),
                ("real", ctypes.POINTER(ctypes.c_double)), ("comp", ctypes.c_void_p), ("length", ctypes.c_int)]


ng.ngGet_Vec_Info.restype = ctypes.POINTER(VecInfo)
ng.ngGet_Vec_Info.argtypes = [ctypes.c_char_p]


def vec(name):
    v = ng.ngGet_Vec_Info(name.encode())
    if not v:
        raise RuntimeError("no vector " + name + " | " + " ".join(LOG[-5:]))
    return [v.contents.real[i] for i in range(v.contents.length)]


MODELS = """
.model DLED D(IS=1e-12 N=2 RS=3 CJO=30p)
.model D4148 D(IS=2.5e-9 N=1.75 RS=0.6 CJO=2p)
.model QOPT NPN(BF=100 IS=1e-14 VAF=100 CJC=20p CJE=10p TF=5n)
.model QP3906 PNP(IS=1.4e-15 BF=180 VAF=20 RB=10 RC=2 CJE=9p CJC=4.5p TF=0.4n)
.model SWU SW(VT=0.5 VH=0.05 RON=5 ROFF=100MEG)
"""


def tran(lines, tstep, tstop, names):
    LOG.clear()
    net = ["scenario"] + [l for l in (MODELS + lines).strip().splitlines() if l.strip()] + [".end"]
    arr = (ctypes.c_char_p * (len(net) + 1))(*[l.encode() for l in net], None)
    ng.ngSpice_Circ(arr)
    ng.ngSpice_Command(f"tran {tstep} {tstop}".encode())
    out = {n: vec(n) for n in ["time"] + names}
    ng.ngSpice_Command(b"destroy all")
    return out


def controller(ctr=130, v24="DC 24", pulldown=True, n_in=5):
    """v3 controller: inputs i driven by unit switches (control nodes c0..), outputs by nodes gp0/gp1"""
    k = ctr / 100.0 / 100.0
    n = [f"VSUP p24u 0 {v24}", "D7 p24u p24h D4148", "D8 g24 0 D4148", "RISO g 0 1G", "V3 v33 g 3.3"]
    for i in range(n_in):
        n += [f"SU{i} aus{i} 0 c{i} 0 SWU",                                   # unit output: switch to GND
              f"RIN{i} p24h ina{i} 10k", f"DP{i} aus{i} ina{i} D4148", f"VS{i} ina{i} a{i} 0", f"DL{i} a{i} aus{i} DLED",
              f"F{i} v33 b{i} VS{i} {k}", f"Q{i} v33 b{i} gpio{i} QOPT", f"RPD{i} gpio{i} g 10k", f"CG{i} gpio{i} g 10p"]
    for j in range(2):
        n += [f"RS{j} gp{j} oa{j} 330", f"VO{j} oa{j} ob{j} 0", f"DO{j} ob{j} g DLED",
              f"FO{j} oc{j} bb{j} VO{j} {k}", f"QO{j} oc{j} bb{j} g24 QOPT", f"RB{j} oc{j} base{j} 22k",
              f"RBE{j} p24h base{j} 10k", f"QP{j} ein{j} base{j} p24h QP3906", f"RLD{j} ein{j} 0 10k", f"CLD{j} ein{j} 0 100p"]
        if pulldown:
            n.append(f"RPO{j} gp{j} g 10k")
    return n


VIH, VIL = 0.75 * 3.3, 0.25 * 3.3


def edges(t, v, thr_hi=VIH, thr_lo=VIL):
    """state changes of a logic input with hysteresis thresholds"""
    st = v[0] > thr_hi
    ev = []
    for a, b in zip(t, v):
        if not st and b > thr_hi:
            st = True; ev.append((a, 1))
        elif st and b < thr_lo:
            st = False; ev.append((a, 0))
    return ev


def esphome_filter(ev, t_end, delay=0.2, start=0):
    """binary_sensor with delayed_on/delayed_off: a new state must hold for `delay` before it is published"""
    pub = []
    cur = start
    for idx, (t, s) in enumerate(ev):
        nxt = ev[idx + 1][0] if idx + 1 < len(ev) else t_end
        if s != cur and nxt - t >= delay:
            cur = s; pub.append((t + delay, s))
    return pub


print("=== 1. Fault line blinking (your event E12: 151,264 toggles, half-cycle 0.45-0.6 s) ===")
n = controller() + ["VC0 c0 0 PULSE(0 1 0.2 1u 1u 0.5 1.0)"] + [f"VC{i} c{i} 0 0" for i in range(1, 5)] + ["VG0 gp0 g 0", "VG1 gp1 g 0"]
r = tran("\n".join(n), "50u", "5.2", ["gpio0", "gpio1", "g"])
g0 = [a - b for a, b in zip(r["gpio0"], r["g"])]
g1 = [a - b for a, b in zip(r["gpio1"], r["g"])]
ev = edges(r["time"], g0)
print(f"  unit toggles in 5 s: 10   -> GPIO edges seen: {len(ev)}   (high {max(g0):.2f} V, low {min(g0):.3f} V)")
print(f"  delay switch->GPIO: on {1e6 * (ev[0][0] - 0.2):.0f} us, off {1e6 * (ev[1][0] - 0.7):.0f} us")
print(f"  neighbour input (level 1) stays at {max(g1):.3f} V  -> no crosstalk")
pub = esphome_filter(ev, 5.2)
print(f"  after your ESPHome filter (delayed_on/off 200 ms): {len(pub)} state changes reach Home Assistant")
pub2 = esphome_filter(ev, 5.2 + 3, delay=0.2)
onoff = []
cur = 0
for idx, (t, s) in enumerate(ev):      # delayed_on 200 ms, delayed_off 2 s
    nxt = ev[idx + 1][0] if idx + 1 < len(ev) else 99
    d = 0.2 if s else 2.0
    if s != cur and nxt - t >= d:
        cur = s; onoff.append((t + d, s))
print(f"  with delayed_off raised to 2 s: {len(onoff)} state changes (blinking is reported as one steady fault)")

print()
print("=== 2. Level stepping 0->1->2->3 and back (your data: steps 0.4 s apart) ===")
pw = ["VC1 c1 0 PWL(0 0 0.2 0 0.2001 1 3.0 1 3.0001 0)",        # level outputs as the unit drives them one after another
      "VC2 c2 0 PWL(0 0 0.6 0 0.6001 1 2.6 1 2.6001 0)",
      "VC3 c3 0 PWL(0 0 1.0 0 1.0001 1 2.2 1 2.2001 0)"]
n = controller() + pw + ["VC0 c0 0 0", "VC4 c4 0 0", "VG0 gp0 g 0", "VG1 gp1 g 0"]
r = tran("\n".join(n), "50u", "3.6", [f"gpio{i}" for i in range(5)] + ["g"])
exp = {1: (0.2, 3.0), 2: (0.6, 2.6), 3: (1.0, 2.2)}
ok = True
for i in (1, 2, 3):
    gi = [a - b for a, b in zip(r[f"gpio{i}"], r["g"])]
    e = edges(r["time"], gi)
    d_on, d_off = e[0][0] - exp[i][0], e[1][0] - exp[i][1]
    ok &= len(e) == 2 and 0 <= d_on < 0.005 and 0 <= d_off < 0.005
    print(f"  level {i}: on after {1e6 * d_on:.0f} us, off after {1e6 * d_off:.0f} us, edges {len(e)}")
quiet = max(max(a - b for a, b in zip(r[f"gpio{i}"], r["g"])) for i in (0, 4))
print(f"  fault and auto inputs stay at {quiet:.3f} V; sequence reproduced correctly: {ok}")

print()
print("=== 3. Boot (your pattern R02: fan started by itself on 8 of 8 boots) ===")
print("  ESP32 pins during the ~8 s boot are not driven; worst case is an internal pull-up (about 45 k to 3.3 V).")
for pd in (True, False):
    for ctr in (130, 260, 600):
        n = controller(ctr=ctr, pulldown=pd) + [f"VC{i} c{i} 0 0" for i in range(5)] + \
            ["VPU0 pu0 g 3.3", "RPU0 pu0 gp0 45k", "VPU1 pu1 g 3.3", "RPU1 pu1 gp1 45k"]
        r = tran("\n".join(n), "1m", "0.5", ["ein0", "ein1", "gp0", "g"])
        print(f"  pull-down R18/R19 {'fitted' if pd else 'absent'}, CTR {ctr:3d} %: pin sits at {r['gp0'][-1] - r['g'][-1]:.2f} V, EIN line = {max(r['ein0']):.2f} V"
              f"  -> {'no press' if max(r['ein0']) < 2 else 'FALSE PRESS'}")

print()
print("=== 4. One button press (your config: 300 ms pulse) ===")
n = controller() + [f"VC{i} c{i} 0 0" for i in range(5)] + ["VG0 gp0 g PULSE(0 3.3 0.1 1u 1u 0.3 2)", "VG1 gp1 g 0"]
r = tran("\n".join(n), "20u", "0.6", ["ein0", "ein1"])
t, v = r["time"], r["ein0"]
up = next(a for a, b in zip(t, v) if b > 12)
dn = next(a for a, b in zip(t, v) if a > up and b < 12)
print(f"  EIN0 reaches {max(v):.2f} V, pulse width {1e3 * (dn - up):.1f} ms, turn-on delay {1e6 * (up - 0.1):.0f} us, turn-off delay {1e6 * (dn - 0.4):.0f} us")
print(f"  the other line (EIN1) stays at {max(r['ein1']):.3f} V")

print()
print("=== 5. Unit loses power while the ESP32 stays on USB (your data: hold-up >= 0.34 s) ===")
n = controller(v24="PWL(0 24 0.2 24 0.54 0)") + ["VC1 c1 0 1"] + [f"VC{i} c{i} 0 0" for i in (0, 2, 3, 4)] + ["VG0 gp0 g 0", "VG1 gp1 g 0"]
r = tran("\n".join(n), "100u", "0.8", ["gpio1", "gpio0", "g", "ein0", "p24u"])
g1 = [a - b for a, b in zip(r["gpio1"], r["g"])]
e = edges(r["time"], g1)
v_at = next(p for tt, p in zip(r["time"], r["p24u"]) if tt >= e[0][0]) if e else float("nan")
print(f"  active level input drops out once at t={e[0][0]:.3f} s (supply at {v_at:.1f} V), edges: {len(e)}; idle inputs max {max(a - b for a, b in zip(r['gpio0'], r['g'])):.3f} V; EIN max {max(r['ein0']):.3f} V")
