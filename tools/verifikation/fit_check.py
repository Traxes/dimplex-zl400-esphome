import ngs, models as M
# 1N4148W max fit vs Semtech max VF
for name, mdl in (("typ", M.D4148_TYP), ("max", M.D4148_MAX)):
    row = []
    for i in (1e-3, 10e-3, 50e-3, 150e-3):
        r = ngs.run([mdl, f"I1 0 a {i}", "D1 a 0 DSW", ".temp 25"], ["v(a)"])
        row.append(f"{i*1e3:g}mA:{r['v(a)']:.3f}")
    print("1N4148", name, row, "(Semtech max: 0.715/0.855/1.0/1.25)")
# green LED
r = ngs.run([M.DGRN, "I1 0 a 5m", "D1 a 0 DGRN"], ["v(a)"]); print("KT-0805G VF@5mA", round(r["v(a)"], 3), "(DS 2.6-3.1)")
r = ngs.run([M.DGRN, "I1 0 a 1m", "D1 a 0 DGRN"], ["v(a)"]); print("KT-0805G VF@1mA", round(r["v(a)"], 3))
# EL817 LED table vs Fig.1 points
for T in (-55, 25, 110, 60, -10):
    out = []
    for i in (0.1e-3, 1e-3, 10e-3, 20e-3):
        r = ngs.run([f"I1 0 a {i}", f"B1 a 0 I = pwl(V(a), {M.led_pwl(T)})", f".temp {T}"], ["v(a)"])
        out.append(f"{i*1e3:g}mA:{r['v(a)']:.3f}")
    print("EL817 LED", T, out)
# CTR table sanity
for T in (-10, 25, 60):
    print("CTRn", T, [round(M.ctr_norm(i, T), 3) for i in (0.1, 0.5, 1, 2, 2.5, 5, 6.5, 10)])
print("dark current bound 25/60 C [nA]:", round(M.dark_current(25)*1e9), round(M.dark_current(60)*1e9))
# MMBT3906 hFE at IC=10 mA VCE=1 V
def hfe(bf, T=25, ic=10e-3):
    lo, hi = 1e-7, 1e-3
    for _ in range(40):
        ib = (lo*hi) ** 0.5
        r = ngs.run([M.q3906(bf), "VE e 0 1", f"IB b 0 {ib}", "VC c 0 0", "Q1 c b e Q3906", f".temp {T}"], ["i(VC)"])
        icr = r["i(VC)"]
        if icr < ic: lo = ib
        else: hi = ib
    return ic / ib
h = hfe(180.7); k = 100 / h
print("Fairchild model hFE(10mA,1V,25C)=", round(h, 1), " scale ->", round(180.7*k, 1))
print("scaled model hFE at 25/-10/60 C:", [round(hfe(180.7*k, T), 1) for T in (25, -10, 60)], " @50mA 25C:", round(hfe(180.7*k, 25, 50e-3), 1), "(JSCJ min 60)")
