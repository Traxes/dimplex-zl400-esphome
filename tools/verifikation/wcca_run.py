"""Worst-case circuit analysis of controller v3. Prints all results; JSON copy in wcca_results.json.

Fixed criteria (Phase 0, provisional until the user approves):
  derating NASA EEE-INST-002 (5/03) Table 4: transistor V 0.75 / I 0.75 / P 0.60, Tj <= 110 C;
  diode IF 0.50, PIV 0.70; chip resistor (RM) P 0.60, V 0.80; ambient -10..60 C; EOL CTR factor 0.5.
Assumed environment (to be replaced by measurements): Vdev 21.6..30 V, AUS saturation 0..1 V,
  ESP pull-up RPU 20..70 kOhm (datasheet gives only typ. 45 k), GPIO output resistance 16..50 Ohm.
"""
import json, random, board as B

CTR_MIN, CTR_MAX, EOL = 1.30, 2.60, 0.5
TLO, THI = -10.0, 60.0
res = {}


def p(**kw):
    return B.default(**kw)


def rt(sign):            # all resistors at the +1 % or -1 % edge
    return {k: sign * 0.01 for k in B.NOM_R}


# ---------------------------------------------------------------- 1. input channel HIGH margin
print("== 1. Input HIGH margin (AUS active): weakest corner, all five active (max D7 drop)")
rows = []
for T in (TLO, 25.0, THI):
    for V in (21.6, 24.0, 30.0):
        q = p(Vdev=V, T=T, ctr=[CTR_MIN * EOL] * 7, dv=0.15, diode="max", Vsat=1.0, active=[1] * 5, VDD=3.2,
              rtol={"R1": 0.01, "R6": -0.01}, tcr_sign=1)
        r = B.solve(q)
        vih = 0.75 * q["VDD"]
        rows.append((T, V, r["gpio0"], vih, r["IF0"] * 1e3))
        print(f"  T={T:5.1f} Vdev={V:4.1f}: GPIO={r['gpio0']:.3f} V (VIH {vih:.2f}), IF={r['IF0']*1e3:.2f} mA")
res["input_high"] = rows
# minimum device voltage at which the weakest corner still reads HIGH
for T in (TLO, THI):
    lo, hi = 2.0, 24.0
    for _ in range(25):
        mid = (lo + hi) / 2
        r = B.solve(p(Vdev=mid, T=T, ctr=[CTR_MIN * EOL] * 7, dv=0.15, diode="max", Vsat=1.0, active=[1] * 5,
                      VDD=3.2, rtol={"R1": 0.01, "R6": -0.01}))
        if r["gpio0"] >= 0.75 * 3.2:
            hi = mid
        else:
            lo = mid
    print(f"  -> weakest corner reads HIGH down to Vdev = {hi:.2f} V at {T} C")
    res[f"vmin_input_{T}"] = hi

# ---------------------------------------------------------------- 2. input LOW: tolerated AUS off-state leakage
print("== 2. Input LOW (AUS inactive): largest device off-state sink current that still reads LOW")
for T in (TLO, 25.0, THI):
    lo, hi = 0.0, 2e-3
    for _ in range(30):
        mid = (lo + hi) / 2
        r = B.solve(p(Vdev=30.0, T=T, ctr=[CTR_MAX] * 7, dv=-0.05, diode="typ", active=[0] * 5, Ileak=mid, VDD=3.4,
                      rtol={"R6": 0.01}))
        if r["gpio0"] <= 0.25 * 3.4:
            lo = mid
        else:
            hi = mid
    print(f"  T={T:5.1f}: reads LOW up to {lo*1e6:.1f} uA sink current per AUS line")
    res[f"ileak_max_{T}"] = lo

# ---------------------------------------------------------------- 3. output ON: saturation and EIN level vs load
print("== 3. Output ON: weakest drive (CTR min x EOL, VDD 3.2, Rout 50, VF +0.15) at hottest/coldest, 21.6 and 30 V")
loads = [None, 47e3, 10e3, 4.7e3, 3.3e3, 2.2e3, 1.5e3, 1e3, 0]
tab = []
for T in (TLO, THI):
    for V in (21.6, 30.0):
        for rl in loads:
            q = p(Vdev=V, T=T, ctr=[CTR_MIN * EOL] * 7, dv=0.15, diode="max", VDD=3.2, Rout=50.0, out=["on", "off"],
                  RL=[rl, None], rtol={"R11": 0.01, "R13": 0.01, "R15": -0.01, "R20": 0.01})
            r = B.solve(q)
            tab.append(dict(T=T, V=V, RL=rl, ein=r["ein0"], I=r["I_ein0"] * 1e3, vce_u=r["vce_u0"],
                            vce_q=r["vce_q0"], IFo=r["IFo0"] * 1e3, P_R20=r["P_R20_0"], P_Q=r["P_Q0"]))
            print(f"  T={T:5.1f} V={V:4.1f} RL={'open' if rl is None else ('short' if rl == 0 else f'{rl/1e3:g}k'):>5}: "
                  f"EIN={r['ein0']:6.2f} V I={r['I_ein0']*1e3:6.2f} mA  U6 VCE={r['vce_u0']:.3f}  Q1 VCE={r['vce_q0']:.3f}  "
                  f"IF={r['IFo0']*1e3:.2f} mA  P_R20={r['P_R20_0']*1e3:.0f} mW")
res["output_on"] = tab

# ---------------------------------------------------------------- 4. boot / reset: no press from the weak pull-up
print("== 4. Boot: GPIO17/18 weak pull-up against R18/R19 (strong opto, hot/cold, VDD 3.4, 30 V, 10k load)")
boot = []
for T in (TLO, 25.0, THI):
    for rpu in (70e3, 45e3, 30e3, 20e3, 15e3, 10e3, 7e3, 5e3):
        q = p(Vdev=30.0, T=T, ctr=[CTR_MAX] * 7, dv=-0.05, diode="typ", VDD=3.4, out=["boot", "boot"], RPU=rpu,
              RL=[10e3, 10e3], rtol={"R18": 0.01, "R11": -0.01, "R13": -0.01, "R15": 0.01})
        r = B.solve(q)
        boot.append(dict(T=T, RPU=rpu, vgpio=r["vgo0"], IF=r["IFo0"], ein=r["ein0"], I=r["I_ein0"]))
        print(f"  T={T:5.1f} RPU={rpu/1e3:4.0f}k: GPIO={r['vgo0']:.3f} V IF={r['IFo0']*1e6:9.3f} uA "
              f"VBE(Q1)={r['vbe_q0']*1e3:6.1f} mV EIN={r['ein0']:7.4f} V I_EIN={r['I_ein0']*1e6:8.3f} uA")
res["boot"] = boot

# ---------------------------------------------------------------- 5. stresses vs EEE-INST-002 derated limits
print("== 5. Stress at Vdev 30 V vs derated limits (worst corners)")
st = {}
r = B.solve(p(Vdev=30.0, T=THI, diode="typ", active=[1] * 5, Vsat=0.0, rtol=rt(-1), ctr=[CTR_MAX] * 7, dv=-0.05,
              out=["off", "off"], RL=[0, 0]))
st["U6_VCE_off"] = (r["vce_u0"], 0.75 * 35)
st["Q1_VCE_off"] = (r["vce_q0"], 0.75 * 40)
st["R1_P"] = (max(r[f"P_R1_{i}"] for i in range(5)), 0.6 * 0.125)
st["IF_in"] = (max(r[f"IF{i}"] for i in range(5)), 0.5 * 60e-3)
st["R17_P"] = (r["P_R17"], 0.6 * 0.125)
r2 = B.solve(p(Vdev=30.0, T=THI, diode="typ", active=[1] * 5, Vsat=0.0, rtol=rt(-1), ctr=[CTR_MAX] * 7, dv=-0.05,
               VDD=3.4, Rout=16.0, out=["on", "off"], RL=[0, None]))
st["R20_P_short"] = (r2["P_R20_0"], 0.6 * 0.125)
st["R13_P"] = (r2["P_R13_0"], 0.6 * 0.125)
st["Q1_IC_short"] = (r2["I_ein0"], 0.75 * 0.2)
st["Q1_Tj_short"] = (THI + r2["P_Q0"] * 625, 110.0)
st["IF_out"] = (r2["IFo0"], 0.5 * 60e-3)
st["D7_IF"] = (r2["I_D7"], 0.5 * 0.150)
for k, (v, lim) in st.items():
    print(f"  {k:12s} {v:10.4g}  limit {lim:8.4g}  {100*v/lim:6.1f} %  {'PASS' if v <= lim else 'FAIL'}")
res["stress"] = st
# the same at 24 V for comparison
r = B.solve(p(Vdev=24.0, T=THI, diode="typ", active=[1] * 5, Vsat=0.0, rtol=rt(-1), ctr=[CTR_MAX] * 7))
print(f"  at 24 V: U6 VCE_off={r['vce_u0']:.2f} V ({100*r['vce_u0']/26.25:.0f} % of derated), "
      f"R1 P={max(r[f'P_R1_{i}'] for i in range(5))*1e3:.1f} mW ({100*max(r[f'P_R1_{i}'] for i in range(5))/0.075:.0f} %)")
# device voltage at which U6 hits the derated 26.25 V
lo, hi = 20.0, 34.0
for _ in range(25):
    mid = (lo + hi) / 2
    r = B.solve(p(Vdev=mid, T=THI, diode="typ", active=[0] * 5))
    lo, hi = (mid, hi) if r["vce_u0"] <= 26.25 else (lo, mid)
print(f"  U6/U7 reach the derated 26.25 V at Vdev = {lo:.2f} V; absolute 35 V at Vdev ~ {lo + 35 - 26.25:.1f} V")
res["vdev_u6_derated"] = lo

# ---------------------------------------------------------------- 6. Monte Carlo over all assumed ranges
print("== 6. Monte Carlo")
random.seed(20261015)
N = 4000
fails = {"in_high": 0, "in_low": 0, "out_sat": 0, "boot": 0, "conv": 0}
worst = {"in_high": 9, "boot": 0.0, "out_q": 0.0}
for n in range(N):
    T = random.uniform(TLO, THI)
    ctr = [random.uniform(CTR_MIN, CTR_MAX) * random.uniform(EOL, 1.0) for _ in range(7)]
    common = dict(Vdev=random.uniform(21.6, 30.0), T=T, ctr=ctr, dv=random.uniform(-0.05, 0.15),
                  diode=random.choice(["typ", "max"]), Vsat=random.uniform(0, 1.0), VDD=random.uniform(3.2, 3.4),
                  Rout=random.uniform(16, 50), RPU=random.uniform(20e3, 70e3),
                  rtol={f"{k}_{i}": random.uniform(-0.01, 0.01) for k in B.NOM_R for i in range(5)})
    act = [random.randint(0, 1) for _ in range(5)]
    rl = random.choice([None, 47e3, 10e3, 4.7e3, 2.2e3])
    r = B.solve(dict(B.default(), **common, active=act, out=["on", "boot"], RL=[rl, 10e3]))
    if "_log" in r:
        fails["conv"] += 1
        continue
    vdd = common["VDD"]
    for i in range(5):
        if act[i] and r[f"gpio{i}"] < 0.75 * vdd:
            fails["in_high"] += 1
        if act[i]:
            worst["in_high"] = min(worst["in_high"], r[f"gpio{i}"] - 0.75 * vdd)
        if not act[i] and r[f"gpio{i}"] > 0.25 * vdd:
            fails["in_low"] += 1
    if r["vce_q0"] > 0.3 or r["vce_u0"] > 0.4:
        fails["out_sat"] += 1
    worst["out_q"] = max(worst["out_q"], r["vce_q0"])
    if r["I_ein1"] > 10e-6:
        fails["boot"] += 1
    worst["boot"] = max(worst["boot"], r["I_ein1"])
print(f"  N={N}: failures {fails}")
print(f"  worst input HIGH margin {worst['in_high']:.3f} V above VIH; worst Q1 VCE(on) {worst['out_q']:.3f} V; "
      f"worst boot EIN current {worst['boot']*1e6:.3f} uA")
res["mc"] = dict(N=N, fails=fails, worst=worst)
json.dump(res, open("wcca_results.json", "w"), indent=1, default=str)
