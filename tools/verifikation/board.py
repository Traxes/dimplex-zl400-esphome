"""Whole controller v3 as one ngspice netlist (24 V side + ESP side), parameterised for worst-case runs.

Topology taken from the KiCad netlist of ESP24V_HA_XIAO.kicad_sch (checked pin by pin on 2026-10-14).
Node names: dev = J1 '+' (device +24 V), 0 = device GND, rail = board +24V (after D7), g24 = GND24 (above D8),
eg = ESP ground (isolated, 1 GOhm to device GND), v33 = XIAO 3V3.
"""
import ngs, models as M

NOM_R = {"R1": 10e3, "R6": 10e3, "R11": 330.0, "R13": 22e3, "R15": 10e3, "R17": 22e3, "R18": 10e3, "R20": 1e3}
TCR = 100e-6           # UNI-ROYAL 0805 thick film, R > 10 ohm: +-100 ppm/K


def default(**kw):
    p = dict(Vdev=24.0, T=25.0, ctr=[1.95] * 7, dv=0.0, diode="typ", Vsat=0.2, active=[0, 1, 0, 0, 1],
             Ileak=0.0, VDD=3.3, out=["off", "off"], Rout=33.0, RPU=45e3, RL=[10e3, 10e3], rtol={}, tcr_sign=1)
    p.update(kw)
    return p


def R(p, name, k=None):
    tol = p["rtol"].get(f"{name}_{k}" if k is not None else name, p["rtol"].get(name, 0.0))
    return NOM_R[name] * (1 + tol) * (1 + p["tcr_sign"] * TCR * (p["T"] - 25))


def netlist(p):
    T = p["T"]
    led = M.led_pwl(T, p["dv"])
    BF = 500.0
    L = [M.QPH, M.q3906(112.3), M.D4148_TYP if p["diode"] == "typ" else M.D4148_MAX, M.DGRN, f".temp {T}",
         f"VDEV dev 0 {p['Vdev']}", "D7 dev rail DSW", "D8 g24 0 DSW",
         f"R17 rail pl {22e3 * (1 + p['rtol'].get('R17', 0))}", "D6 pl g24 DGRN",
         "RISO eg 0 1G", f"V33 v33 eg {p['VDD']}"]
    idk = M.dark_current(T)
    for i in range(5):
        L += [f"R1_{i} rail ina{i} {R(p, 'R1', i)}", f"D1_{i} aus{i} ina{i} DSW",
              f"VS{i} ina{i} la{i} 0", f"BL{i} la{i} aus{i} I = pwl(V(la{i},aus{i}), {led})"]
        if p["active"][i]:
            L.append(f"VA{i} aus{i} 0 {p['Vsat']}")
        else:
            L += [f"RA{i} aus{i} 0 1G", f"IA{i} aus{i} 0 {p['Ileak']}"]
        L += [f"BP{i} v33 pb{i} I = pwl(i(VS{i}), {M.photo_pwl(T, p['ctr'][i], BF)})",
              f"Q{i} v33 pb{i} gp{i} QPH", f"ID{i} v33 gp{i} {idk}", f"R6_{i} gp{i} eg {R(p, 'R6', i)}"]
    for j in range(2):
        k = 5 + j
        mode = p["out"][j]
        if mode == "on":
            L += [f"VG{j} gs{j} eg {p['VDD']}", f"RG{j} gs{j} go{j} {p['Rout']}"]
        elif mode == "boot":
            L += [f"VG{j} gs{j} eg {p['VDD']}", f"RG{j} gs{j} go{j} {p['RPU']}"]
        else:
            L += [f"RG{j} go{j} eg 1G"]
        rl = p["RL"][j]
        L += [f"R18_{j} go{j} eg {R(p, 'R18', j)}", f"R11_{j} go{j} oa{j} {R(p, 'R11', j)}",
              f"VSo{j} oa{j} ol{j} 0", f"BLo{j} ol{j} eg I = pwl(V(ol{j},eg), {led})",
              f"BPo{j} oc{j} ob{j} I = pwl(i(VSo{j}), {M.photo_pwl(T, p['ctr'][k], BF)})",
              f"Qo{j} oc{j} ob{j} g24 QPH", f"IDo{j} oc{j} g24 {idk}",
              f"R13_{j} oc{j} bq{j} {R(p, 'R13', j)}", f"R15_{j} rail bq{j} {R(p, 'R15', j)}",
              f"Q1_{j} cq{j} bq{j} rail Q3906", f"R20_{j} cq{j} ein{j} {R(p, 'R20', j)}",
              f"RL{j} ein{j} 0 {1e-3 if rl == 0 else (1e9 if rl is None else rl)}"]
    return L


def solve(p):
    probes = ["v(rail)", "v(g24)", "i(VDEV)", "v(v33)-v(eg)"]
    for i in range(5):
        probes += [f"v(gp{i})-v(eg)", f"i(VS{i})", f"v(rail)-v(ina{i})", f"v(aus{i})"]
    for j in range(2):
        probes += [f"v(ein{j})", f"i(VSo{j})", f"v(oc{j})-v(g24)", f"v(rail)-v(cq{j})", f"v(rail)-v(bq{j})",
                   f"v(cq{j})-v(ein{j})", f"v(oc{j})-v(bq{j})", f"v(go{j})-v(eg)"]
    r = ngs.run(netlist(p), probes)
    out = {"rail": r["v(rail)"], "g24": r["v(g24)"], "I_D7": -r["i(VDEV)"]}
    for i in range(5):
        out[f"gpio{i}"] = r[f"v(gp{i})-v(eg)"]
        out[f"IF{i}"] = r[f"i(VS{i})"]
        out[f"P_R1_{i}"] = r[f"v(rail)-v(ina{i})"] ** 2 / R(p, "R1", i)
    for j in range(2):
        vr20 = r[f"v(cq{j})-v(ein{j})"]
        out.update({f"ein{j}": r[f"v(ein{j})"], f"IFo{j}": r[f"i(VSo{j})"], f"vce_u{j}": r[f"v(oc{j})-v(g24)"],
                    f"vce_q{j}": r[f"v(rail)-v(cq{j})"], f"vbe_q{j}": r[f"v(rail)-v(bq{j})"],
                    f"I_ein{j}": vr20 / R(p, "R20", j), f"P_R20_{j}": vr20 ** 2 / R(p, "R20", j),
                    f"P_R13_{j}": r[f"v(oc{j})-v(bq{j})"] ** 2 / R(p, "R13", j), f"vgo{j}": r[f"v(go{j})-v(eg)"]})
        out[f"P_Q{j}"] = out[f"vce_q{j}"] * out[f"I_ein{j}"]
    out["P_R17"] = (out["rail"] - 2.7) ** 2 / 22e3  # approx (LED ~2.6-2.7 V @ 1 mA)
    if "_log" in r:
        out["_log"] = r["_log"]
    return out
