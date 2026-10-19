"""Part models for the worst-case analysis, each traced to a primary source.

EL817  : Everlight DPC-0000046 Rev.15 (2016-07-20), Fig. 1 (IF-VF), Fig. 2 (CTR vs IF), Fig. 3 (CTR vs Ta),
         Fig. 4 (dark current), p.3 table (CTR rank B 130-260 %, ICEO <= 100 nA @ 20 V).
         Curves digitised by eye from a 300-dpi render; reading uncertainty about +-0.01 V / +-0.02 (normalised CTR).
MMBT3906: Fairchild 2N3906/MMBT3906 datasheet SPICE model, beta scaled so hFE(10 mA, 1 V, 25 C) equals the
         JSCJ minimum of 100 (JSCJ datasheet D, May 2012).
1N4148W: Semtech 1N4148W Rev.05 (2016-09-20): VF max 0.715 V @ 1 mA, 0.855 @ 10 mA, 1.0 @ 50 mA, 1.25 @ 150 mA.
         Typical corner: classic 1N4148 model (VF ~0.62 V @ 1 mA).
"""
import math

# ---------- EL817 LED: VF at fixed currents for three temperatures (Fig. 1) ----------
FIG1_I = [0.1e-3, 1e-3, 10e-3, 100e-3]
FIG1_V = {-55: [1.151, 1.195, 1.263, 1.563],
          25: [0.993, 1.086, 1.185, 1.446],
          110: [0.845, 0.940, 1.074, 1.341]}
N_LOW = 2.0          # ideality used below 0.1 mA (conservative: shallower slope -> more current at low voltage)


def _vf_points(T):
    """VF at the four Fig.1 currents, linear in T between the plotted temperatures."""
    if T <= 25:
        a, b, t0, t1 = FIG1_V[-55], FIG1_V[25], -55, 25
    else:
        a, b, t0, t1 = FIG1_V[25], FIG1_V[110], 25, 110
    f = (T - t0) / (t1 - t0)
    return [x + (y - x) * f for x, y in zip(a, b)]


def led_vf(i, T, dv=0.0):
    """EL817 LED forward voltage at current i [A], temperature T [C], plus a part-to-part shift dv [V]."""
    v = _vf_points(T)
    lg = math.log10(i)
    if lg <= -4:     # below 0.1 mA: exponential extrapolation with N_LOW
        vt = 8.617e-5 * (T + 273.15)
        return v[0] + N_LOW * vt * math.log(10) * (lg + 4) + dv
    for k in range(3):
        a, b = math.log10(FIG1_I[k]), math.log10(FIG1_I[k + 1])
        if lg <= b or k == 2:
            return v[k] + (v[k + 1] - v[k]) * (lg - a) / (b - a) + dv


def led_pwl(T, dv=0.0):
    """pwl() argument list (V, I) for a B-source LED, from 1 pA to 80 mA, plus a reverse point."""
    pts = [(-2.0, -1e-12), (0.0, 0.0)]
    for e in range(-120, -10):        # 10^-12 ... 10^-1.1 A in 0.1-decade steps
        i = 10 ** (e / 10)
        if i > 80e-3:
            break
        pts.append((led_vf(i, T, dv), i))
    pts.append((pts[-1][0] + 1.0, pts[-1][1] + 1.0 / 5.0))   # 5-ohm slope beyond the table
    out, last = [], -9
    for v, i in pts:
        if v > last + 1e-6:
            out.append((v, i))
            last = v
    return ", ".join(f"{v:.5f},{i:.4e}" for v, i in out)


# ---------- EL817 CTR, normalised to IF = 5 mA, Ta = 25 C (Fig. 3; Fig. 2 below 1 mA) ----------
FIG3_T = [-55, -40, -20, 0, 20, 40, 60, 80, 100, 110]
FIG3 = {1:  [0.70, 0.71, 0.70, 0.61, 0.54, 0.47, 0.39, 0.33, 0.28, 0.255],
        2:  [0.84, 0.86, 0.88, 0.82, 0.77, 0.71, 0.61, 0.49, 0.42, 0.39],
        5:  [0.97, 1.02, 1.06, 1.06, 1.03, 0.95, 0.86, 0.76, 0.67, 0.62],
        10: [1.02, 1.08, 1.14, 1.17, 1.15, 1.10, 1.02, 0.94, 0.84, 0.77],
        20: [1.05, 1.10, 1.17, 1.21, 1.19, 1.13, 1.06, 0.98, 0.89, 0.84]}
LOW_EXP = math.log(0.32 / 0.50) / math.log(0.5 / 1.0)    # Fig. 2: CTR ~ IF^0.644 between 0.5 and 1 mA


def _interp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    for k in range(len(xs) - 1):
        if x <= xs[k + 1]:
            return ys[k] + (ys[k + 1] - ys[k]) * (x - xs[k]) / (xs[k + 1] - xs[k])
    return ys[-1]


def ctr_norm(i_ma, T):
    keys = [1, 2, 5, 10, 20]
    at = {k: _interp(FIG3_T, FIG3[k], T) for k in keys}
    if i_ma <= 1:
        return at[1] * (max(i_ma, 1e-9) / 1.0) ** LOW_EXP
    if i_ma >= 20:
        return at[20]
    lx = math.log10(i_ma)
    return _interp([math.log10(k) for k in keys], [at[k] for k in keys], lx)


def photo_pwl(T, ctr5, bf):
    """pwl() list (IF [A], base photocurrent [A]) = CTR(IF,T) * IF / BF; ctr5 = CTR at 5 mA/25 C (e.g. 1.30)."""
    pts = [(-1.0, 0.0), (0.0, 0.0)]
    for e in range(-110, -10):
        i = 10 ** (e / 10)
        if i > 60e-3:
            break
        pts.append((i, ctr5 * ctr_norm(i * 1e3, T) * i / bf))
    return ", ".join(f"{x:.4e},{y:.4e}" for x, y in pts)


def dark_current(T):
    """Phototransistor dark current bound: datasheet max 100 nA @ 25 C, scaled with Fig. 4 slope (x58 from 25 to 60 C)."""
    return 100e-9 * 58 ** ((T - 25) / 35.0)


# ---------- discrete models ----------
QPH = ".model QPH NPN(IS=1e-14 BF=500 BR=2 VAF=150 XTB=0 XTI=0)"
FAIR3906 = ("Is=1.41f Xti=3 Eg=1.11 Vaf=18.7 Bf={bf} Ne=1.5 Ise=0 Ikf=80m Xtb=1.5 Br=4.977 Nc=2 Isc=0 Ikr=0 "
            "Rc=2.5 Cjc=9.728p Mjc=.5776 Vjc=.75 Fc=.5 Cje=8.063p Mje=.3677 Vje=.75 Tr=33.42n Tf=179.3p Itf=.4 "
            "Vtf=4 Xtf=6 Rb=10")


def q3906(bf=180.7):
    return ".model Q3906 PNP(" + FAIR3906.format(bf=bf) + ")"


D4148_TYP = ".model DSW D(IS=2.52n N=1.752 RS=0.568 BV=100 IBV=100u)"
D4148_MAX = ".model DSW D(IS=8n N=2.37 RS=1.0 BV=100 IBV=100u)"     # fitted to Semtech max VF, see fit_check
DGRN = ".model DGRN D(IS=1e-20 N=2.6 RS=10)"                            # KT-0805G: VF 2.6-3.1 V @ 5 mA
