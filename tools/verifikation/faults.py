"""Single-fault injection on the board model: open = 1 GOhm, short = 1 mOhm (element lines replaced)."""
import ngs, board as B, re

def solve_fault(p, fault):
    L = B.netlist(p)
    out = []
    for l in L:
        name = l.split()[0] if l.strip() else ""
        if name in fault:
            kind = fault[name]
            parts = l.split()
            if kind == "open":
                l = f"{name} {parts[1]} {parts[2]} 1G" if name[0] in "RV" else "* removed " + l
            elif kind == "short":
                l = f"R{name}_sh {parts[1]} {parts[2]} 1m"
            elif kind.startswith("CE"):         # transistor collector-emitter short
                l = l + f"\nR{name}_ce {parts[1]} {parts[3]} 1m"
        out += l.split("\n")
    probes = ["v(ein0)", "v(ein1)", "v(rail)-v(bq0)", "v(rail)-v(cq0)", "v(oc0)-v(g24)", "v(gp0)-v(eg)", "v(go0)-v(eg)",
              "i(VSo0)", "i(VDEV)"]
    r = ngs.run(out, probes)
    return r

hot = dict(T=60.0, Vdev=30.0, ctr=[2.6] * 7, diode="typ", RL=[10e3, 10e3])
cases = [
  ("R15_0 offen, Ausgang AUS, 60 C", B.default(**hot, out=["off", "off"]), {"R15_0": "open"}),
  ("R15_0 offen, Ausgang AUS, 25 C", B.default(**dict(hot, T=25.0), out=["off", "off"]), {"R15_0": "open"}),
  ("R18_0 offen, Boot (RPU 45k), 60 C", B.default(**hot, out=["boot", "off"], RPU=45e3), {"R18_0": "open"}),
  ("R18_0 offen, Boot (RPU 20k), 60 C", B.default(**hot, out=["boot", "off"], RPU=20e3), {"R18_0": "open"}),
  ("Q1_0 C-E Kurzschluss, Ausgang AUS", B.default(**hot, out=["off", "off"]), {"Q1_0": "CE"}),
  ("Qo0 (U6) C-E Kurzschluss, Ausgang AUS", B.default(**hot, out=["off", "off"]), {"Qo0": "CE"}),
  ("R13_0 Kurzschluss, Ausgang EIN", B.default(**hot, out=["on", "off"]), {"R13_0": "short"}),
  ("R11_0 Kurzschluss, Ausgang EIN", B.default(**hot, out=["on", "off"]), {"R11_0": "short"}),
  ("R20_0 Kurzschluss + EIN-Kurzschluss, EIN", B.default(**dict(hot, RL=[0, 10e3]), out=["on", "off"]), {"R20_0": "short"}),
  ("D8 Kurzschluss (nur Schutzverlust)", B.default(**hot, out=["on", "off"]), {"D8": "short"}),
]
for name, p, f in cases:
    r = solve_fault(p, f)
    ie = (r["v(ein0)"]) / 10e3 if p["RL"][0] else float("nan")
    print(f"{name:42s} EIN0={r['v(ein0)']:7.3f} V  VBE_Q1={r['v(rail)-v(bq0)']*1e3:7.1f} mV  VCE_U6={r['v(oc0)-v(g24)']:6.2f} V  "
          f"IF_U6={r['i(VSo0)']*1e3:7.3f} mA  GPIO_out={r['v(go0)-v(eg)']:.2f} V  I_D7={-r['i(VDEV)']*1e3:6.1f} mA")
