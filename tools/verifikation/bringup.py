"""Predicted bring-up values (lab PSU 24.0 V, emulator loads, 20-30 C, new parts) as min/max bands from Monte Carlo."""
import random, ngs, board as B, models as M
DRED = ".model DRED D(IS=1e-19 N=2.0 RS=8)"   # C84256: VF 1.5-2.6 V @ 20 mA (Everlight-like red 0805)

def solve_emu(p, emu_aus=True, emu_ein=True):
    L = []
    for l in B.netlist(p):
        nm = l.split()[0] if l.strip() else ""
        if emu_aus and nm.startswith("VA"):
            i = nm[2:]; l = f"RA{i} aus{i} 0 2.2k"
        if emu_ein and nm.startswith("RL"):
            j = nm[2:]; l = f"RL{j} ein{j} xl{j} 10k\nDLR{j} xl{j} 0 DRED"
        L += l.split("\n")
    L.insert(0, DRED)
    pr = ["v(rail)", "v(g24)", "i(VDEV)", "v(rail)-v(ina0)", "v(rail)-v(ina1)", "v(gp0)-v(eg)", "v(gp1)-v(eg)",
          "v(aus0)", "v(aus1)", "v(go0)-v(eg)", "v(go0)-v(oa0)", "v(ein0)", "v(rail)-v(cq0)", "v(oc0)-v(g24)",
          "v(ein1)", "v(rail)-v(bq1)", "v(ol0)-v(eg)"]
    return ngs.run(L, pr)

random.seed(7)
states = {
  "S0 alles aus (DIP offen, Ausgaenge LOW)": dict(active=[0]*5, out=["off", "off"]),
  "S1 AUS_0 aktiv + Ausgang HOCH an": dict(active=[1,0,0,0,0], out=["on", "off"]),
  "S2 alle 5 AUS aktiv, Ausgaenge LOW": dict(active=[1]*5, out=["off", "off"]),
}
for name, st in states.items():
    agg = {}
    for n in range(600):
        p = B.default(Vdev=24.0, T=random.uniform(20, 30), ctr=[random.uniform(1.3, 2.6) for _ in range(7)],
                      dv=random.uniform(-0.05, 0.15), diode=random.choice(["typ", "max"]), VDD=random.uniform(3.25, 3.35),
                      Rout=random.uniform(16, 50), RL=[10e3, 10e3],
                      rtol={f"{k}_{i}": random.uniform(-0.01, 0.01) for k in B.NOM_R for i in range(5)}, **st)
        r = solve_emu(p)
        for k, v in r.items():
            if k == "_log": continue
            lo, hi = agg.get(k, (9e9, -9e9)); agg[k] = (min(lo, v), max(hi, v))
    print("==", name)
    for k, (lo, hi) in agg.items():
        if k == "i(VDEV)": k, lo, hi = "I(J1) [mA]", -hi*1e3, -lo*1e3
        print(f"   {k:22s} {lo:9.3f} .. {hi:9.3f}")
