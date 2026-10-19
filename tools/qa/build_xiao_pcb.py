import pcbnew, re, os, sys
D = r"<PROJEKT>\ESP24V_HA_Board_XIAO"
SCH = os.path.join(D, "ESP24V_HA_XIAO.kicad_sch")
PCB = os.path.join(D, "ESP24V_HA_XIAO.kicad_pcb")
NET = sys.argv[1]
FPDIR = r"C:\Program Files\KiCad\10.0\share\kicad\footprints"
OX, OY = 100.0, 60.0
W, H = 75.0, 64.0
mm = pcbnew.FromMM


def P(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def blocks(s, head):
    out = []
    i = 0
    while True:
        i = s.find(head, i)
        if i < 0:
            break
        d = 0
        j = i
        while True:
            c = s[j]
            if c == '(':
                d += 1
            elif c == ')':
                d -= 1
                if d == 0:
                    break
            j += 1
        out.append(s[i:j + 1])
        i = j
    return out


# --- schematic symbol uuids (for footprint <-> symbol links) ---
s = open(SCH, encoding='utf8').read()
ls = s.find('(lib_symbols')
le = ls + len(blocks(s[ls:], '(lib_symbols')[0])
body = s[:ls] + s[le:]
sym = {}
for b in blocks(body, '(symbol'):
    if '(lib_id' not in b:
        continue
    ref = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', b).group(1)
    val = re.search(r'\(property\s+"Value"\s+"([^"]*)"', b).group(1)
    fp = re.search(r'\(property\s+"Footprint"\s+"([^"]*)"', b).group(1)
    d = 0
    own = None
    for m in re.finditer(r'\(|\)|uuid\s+"?([0-9a-f\-]{36})', b):
        t = m.group(0)
        if t == '(':
            d += 1
        elif t == ')':
            d -= 1
        elif d == 2 and own is None:
            own = m.group(1)
    props = dict(re.findall(r'\(property\s+"([^"]+)"\s+"([^"]*)"', b))
    flags = {k: (re.search(r'\(' + k + r'\s+(yes|no)\)', b) or [None, 'x'])[1] for k in ('in_bom', 'on_board', 'dnp')}
    sym[ref] = (val, fp, own, props, flags)

# --- netlist ---
n = open(NET, encoding='utf8').read()
nets = {}
for blk in re.split(r'\(net\s+\(code', n[n.find('(nets'):])[1:]:
    name = re.search(r'\(name "([^"]*)"', blk).group(1)
    for r, p in re.findall(r'\(node\s+\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', blk):
        nets[(r, p)] = name

board = pcbnew.NewBoard(PCB)
ds = board.GetDesignSettings()
ds.m_TrackMinWidth = mm(0.15)
ds.m_MinClearance = mm(0.15)
ds.m_ViasMinSize = mm(0.5)
ds.m_MinThroughDrill = mm(0.3)
ds.m_CopperEdgeClearance = mm(0.3)
ds.m_HoleClearance = mm(0.25)
ds.m_HoleToHoleMin = mm(0.5)
ds.m_ViasMinAnnularWidth = mm(0.13)
try:
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetClearance(mm(0.2))
    nc.SetTrackWidth(mm(0.3))
    nc.SetViaDiameter(mm(0.7))
    nc.SetViaDrill(mm(0.3))
except Exception as e:
    print("netclass:", e)

NI = {}


def net(name):
    if name not in NI:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        NI[name] = ni
    return NI[name]


FP = {}


def place(ref, x, y, rot=0, hide_ref=True):
    val, fpid, uu, props, flags = sym[ref]
    lib, name = fpid.split(':')
    fp = pcbnew.FootprintLoad(os.path.join(FPDIR, lib + '.pretty'), name)
    fp.SetReference(ref)
    fp.SetValue(val)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    fp.SetPosition(P(x, y))
    fp.SetOrientationDegrees(rot)
    fp.SetPath(pcbnew.KIID_PATH("/" + uu))
    if hide_ref:
        fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    for k in ('Description', 'LCSC', 'Datasheet'):
        if props.get(k):
            fp.SetField(k, props[k])
            for f in fp.GetFields():
                if f.GetName() == k:
                    f.SetVisible(False)
    if flags.get('in_bom') == 'no':
        fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM)
    elif flags.get('in_bom') == 'yes':
        fp.SetAttributes(fp.GetAttributes() & ~pcbnew.FP_EXCLUDE_FROM_BOM)
    for pad_ in fp.Pads():
        k = (ref, pad_.GetNumber())
        if k in nets:
            pad_.SetNet(net(nets[k]))
    board.Add(fp)
    FP[ref] = fp


def pad(ref, num):
    for p in FP[ref].Pads():
        if p.GetNumber() == num:
            v = p.GetPosition()
            return (pcbnew.ToMM(v.x) - OX, pcbnew.ToMM(v.y) - OY)




def place_oriented(ref, x, y, rots, cond):
    """try rotations until cond(pad positions) holds"""
    for r in rots:
        place(ref, x, y, r)
        if cond():
            return r
        board.Remove(FP[ref])
    raise SystemExit("no orientation for " + ref)


def track(pts, netname, w=0.3, layer=pcbnew.F_Cu):
    for a, b in zip(pts, pts[1:]):
        if abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6:
            continue
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(P(*a))
        t.SetEnd(P(*b))
        t.SetWidth(mm(w))
        t.SetLayer(layer)
        t.SetNet(net(netname))
        board.Add(t)


def via(x, y, netname):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(P(x, y))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    try:
        v.SetWidth(pcbnew.F_Cu, mm(0.7))
    except TypeError:
        v.SetWidth(mm(0.7))
    v.SetDrill(mm(0.3))
    v.SetNet(net(netname))
    board.Add(v)


B = pcbnew.B_Cu
XT = 6.0               # terminal column
XP, XGB = 21.4, 24.9   # +24V and GND24 buses (bottom layer)
XO = 34.0              # optocoupler column (straddles the isolation gap)
XL = 50.0              # XIAO left header (D0..D6)
XR = XL + 15.24        # XIAO right header (5V GND 3V3 D10 D9 D8 D7)
YS = 6.0               # header pin 1, USB end towards the top edge
y0 = [14 + 6.35 * i for i in range(7)]

# terminals: wire entry to the left edge, pin 1 on top
for ref, y in (("J1", 10.0), ("J2", 21.5), ("J3", 48.2)):
    place_oriented(ref, XT, y, (90, 270), lambda ref=ref: pad(ref, "2")[1] > pad(ref, "1")[1] + 1)
place("J4", XL, YS, 0)
place("J5", XR, YS, 0)

GP = [("/IN_FAULT_D0", 1), ("/IN_L1_D1", 2), ("/IN_L2_D4", 5), ("/IN_L3_D5", 6), ("/IN_AUTO_D6", 7)]
XK = [45.5, 46.2, 46.9, 47.6, 48.3]
place("D7", 14.3, 10.0, 180)
track([pad("J1", "1"), pad("D7", "2")], "/+24V_IN", 0.5)
track([pad("D7", "1"), (XP, 10.0)], "/+24V", 0.5)
via(XP, 10.0, "/+24V")
track([(XP, 10.0), (XP, y0[6] - 0.63)], "/+24V", 0.6, B)
place("D8", 14.3, 15.08, 0)
track([pad("J1", "2"), pad("D8", "1")], "/GND24_IN", 0.5)
track([pad("D8", "2"), (17.3, 15.08)], "/GND24", 0.4)
via(17.3, 15.08, "/GND24")
track([(17.3, 15.08), (17.3, 6.5)], "/GND24", 0.6, B)
track([(13.6, 6.5), (XGB, 6.5), (XGB, y0[6] - 1.27)], "/GND24", 0.6, B)
p3 = pad("J5", "3")
ymid = (pad("J4", "3")[1] + pad("J4", "4")[1]) / 2
track([p3, (p3[0] - 2.2, p3[1]), (p3[0] - 2.2 - abs(ymid - p3[1]), ymid), (41.0, ymid), (41.0, y0[4] - 1.27)], "/+3V3", 0.3, B)

for i in range(5):
    y = y0[i]
    R1, D, U, R2 = f"R{1 + i}", f"D{1 + i}", f"U{1 + i}", f"R{6 + i}"
    place(U, XO, y, 0)
    place(R1, 23.5, y - 1.27, 0)
    place_oriented(D, 26.7, y, (90, 270), lambda D=D: pad(D, "1")[1] < pad(D, "2")[1])
    place_oriented(R2, 43.5, y + 1.27 + 0.9125, (90, 270), lambda R2=R2: pad(R2, "1")[1] < pad(R2, "2")[1])
    A, INA, G = f"/AUS_{i}", f"/INA_{i}", GP[i][0]
    via(XP, y - 1.27, "/+24V")
    track([(XP, y - 1.27), pad(R1, "1")], "/+24V", 0.4)
    track([pad(R1, "2"), pad(D, "1"), pad(U, "1")], INA)
    t = pad("J2", str(i + 1))
    a = pad(D, "2")
    dy = a[1] - t[1]
    track([t, (12.5, t[1]), (12.5 + abs(dy), a[1]), a, pad(U, "2")], A)
    u4 = pad(U, "4")
    track([u4, (41.0, u4[1])], "/+3V3", 0.4)
    via(41.0, u4[1], "/+3V3")
    u3 = pad(U, "3")
    g2 = pad(R2, "2")
    track([g2, (42.2, g2[1])], "/GND", 0.4)
    via(42.2, g2[1], "/GND")
    s = pad("J4", str(GP[i][1]))
    track([u3, (XK[i], u3[1]), (XK[i], s[1]), s], G)

OUT = [("/OUT_UP_D10", 4, 58.0), ("/OUT_DN_D7", 7, 60.0)]
for j in range(2):
    y = y0[5 + j]
    U, RS, RB, RBE, Q = f"U{6 + j}", f"R{11 + j}", f"R{13 + j}", f"R{15 + j}", f"Q{1 + j}"
    place(U, XO, y, 180)
    place(RS, 43.5, y + 1.27, 180)
    place(RB, 26.2, y + 1.27, 180)
    place_oriented(RBE, 23.0, y + 0.3125, (90, 270), lambda RBE=RBE: pad(RBE, "1")[1] < pad(RBE, "2")[1])
    place(Q, 19.5, y + 0.32, 180)
    G = OUT[j][0]
    track([pad(U, "1"), pad(RS, "2")], f"/OUTA_{j}")
    u2 = pad(U, "2")
    track([u2, (40.6, u2[1])], "/GND", 0.4)
    via(40.6, u2[1], "/GND")
    u3 = pad(U, "3")
    track([u3, (XGB, u3[1])], "/GND24", 0.4)
    via(XGB, u3[1], "/GND24")
    track([pad(U, "4"), pad(RB, "1")], f"/OUTC_{j}")
    b = pad(Q, "1")
    e = pad(Q, "2")
    c = pad(Q, "3")
    track([pad(RB, "2"), (pad(RBE, "2")[0], b[1]), b], f"/BASE_{j}")
    via(XP, e[1], "/+24V")
    track([e, (XP, e[1]), pad(RBE, "1")], "/+24V", 0.4)
    t = pad("J3", str(j + 1))
    dy = c[1] - t[1]
    RL = f"R{20 + j}"
    place(RL, 15.6, c[1], 0)
    track([t, (12.5, t[1]), (12.5 + abs(dy), c[1]), pad(RL, "1")], f"/EIN_{j}", 0.4)
    track([pad(RL, "2"), c], f"/EOUT_{j}", 0.4)
    r1 = pad(RS, "1")
    s = pad("J5", str(OUT[j][1]))
    xv = OUT[j][2]
    # run under the XIAO on the bottom layer, so nothing on top can touch pads on the back of a flat-soldered XIAO
    RPD = f"R{18 + j}"
    place_oriented(RPD, 46.6, r1[1] + 0.9125, (90, 270), lambda RPD=RPD: pad(RPD, "1")[1] < pad(RPD, "2")[1])
    track([r1, (48.3, r1[1])], G)
    via(48.3, r1[1], G)
    track([(48.3, r1[1]), (xv, r1[1]), (xv, s[1]), s], G, 0.3, B)
    g2 = pad(RPD, "2")
    track([g2, (45.0, g2[1])], "/GND", 0.4)
    via(45.0, g2[1], "/GND")

# 24 V present LED (fed after the protection diode)
place("D6", 16.0, 6.5, 0)
place("R17", 20.0, 6.5, 180)
track([pad("R17", "1"), (XP, 6.5), (XP, 10.0)], "/+24V", 0.4)
track([pad("D6", "2"), pad("R17", "2")], "/PWRLED")
track([pad("D6", "1"), (13.6, 6.5)], "/GND24", 0.4)
via(13.6, 6.5, "/GND24")

for i, (x, y) in enumerate([(3.5, 3.3), (W - 3.5, 3.5), (3.5, H - 3.5), (W - 3.5, H - 3.5)]):
    place(f"H{1 + i}", x, y, 0)

sh = pcbnew.PCB_SHAPE(board)
sh.SetShape(pcbnew.SHAPE_T_RECT)
sh.SetStart(P(0, 0))
sh.SetEnd(P(W, H))
sh.SetLayer(pcbnew.Edge_Cuts)
sh.SetWidth(mm(0.1))
board.Add(sh)

# ground pour on the ESP32 side only
for layer in (pcbnew.F_Cu, B):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net("/GND"))
    z.SetLocalClearance(mm(0.3))
    z.SetMinThickness(mm(0.25))
    o = z.Outline()
    o.NewOutline()
    for x, y in ((37.6, 0.5), (W - 0.5, 0.5), (W - 0.5, H - 0.5), (37.6, H - 0.5)):
        o.Append(mm(OX + x), mm(OY + y))
    board.Add(z)


# no top copper under the XIAO body (it has exposed pads on its back when soldered flat)
try:
    k = pcbnew.ZONE(board)
    k.SetIsRuleArea(True)
    k.SetLayer(pcbnew.F_Cu)
    for fn in ("SetDoNotAllowZoneFills", "SetDoNotAllowCopperPour"):
        if hasattr(k, fn):
            getattr(k, fn)(True)
            break
    for fn, val in (("SetDoNotAllowTracks", False), ("SetDoNotAllowVias", False), ("SetDoNotAllowPads", False), ("SetDoNotAllowFootprints", False)):
        if hasattr(k, fn):
            getattr(k, fn)(val)
    ko = k.Outline()
    ko.NewOutline()
    for x, y in ((51.7, 2.9), (63.5, 2.9), (63.5, 24.4), (51.7, 24.4)):
        ko.Append(mm(OX + x), mm(OY + y))
    board.Add(k)
except Exception as ex:
    print("keepout not added:", ex)


def text(t, x, y, size=1.0, rot=0, left=False):
    T = pcbnew.PCB_TEXT(board)
    T.SetText(t)
    T.SetPosition(P(x, y))
    T.SetLayer(pcbnew.F_SilkS)
    T.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    T.SetTextThickness(mm(max(0.15, size * 0.15)))
    T.SetTextAngleDegrees(rot)
    if left:
        T.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    board.Add(T)


text("Trax HA - ZL 400 VF Board", 33.3, 2.6, 1.0)
text("24V OK", 18.5, 4.2, 0.8)
text("USB", 57.62, 1.8, 1.0)
text("XIAO ESP32-C6", 57.62, 26.5, 1.2)
text("Seeed Studio", 57.62, 29.0, 0.9)
text("D0", 46.6, 3.6, 0.8)
text("5V", 68.4, 6.0, 0.8)
text("ESP32 SIDE - USB POWER ONLY", 55.0, 60.5, 0.9)
text("24V SIDE", 22.0, 60.5, 1.2)
text("ISOLATED", 34.0, 57.6, 0.9)
labels = [("J1", "1", "+24V"), ("J1", "2", "GND"), ("J2", "1", "AUS0 FAULT"), ("J2", "2", "AUS1 LVL1"), ("J2", "3", "AUS2 LVL2"),
          ("J2", "4", "AUS3 LVL3"), ("J2", "5", "AUS4 AUTO"), ("J3", "1", "EIN0 UP"), ("J3", "2", "EIN1 DN")]
for ref, pin, l in labels:
    text(l, 12.2, pad(ref, pin)[1] + (2.3 if ref == "J1" else 1.6 if ref == "J3" else 0), 0.8, 0, True)

pcbnew.SaveBoard(PCB, board)
board = pcbnew.LoadBoard(PCB)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print("saved; footprints", len(board.GetFootprints()), "tracks", len(board.GetTracks()), "nets", board.GetNetCount())
