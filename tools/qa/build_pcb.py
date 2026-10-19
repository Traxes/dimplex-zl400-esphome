import pcbnew, re, os, sys
D = r"<PROJEKT>\ESP24V_Ventilation_LAB"
SCH = os.path.join(D, "ESP24V_Ventilation_LAB.kicad_sch")
PCB = os.path.join(D, "ESP24V_Ventilation_LAB.kicad_pcb")
NET = sys.argv[1]
FPDIR = r"C:\Program Files\KiCad\10.0\share\kicad\footprints"
OX, OY = 100.0, 60.0
W, H = 68.0, 56.0
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


def place(ref, x, y, rot=0, hide_ref=False):
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


YC = 28.0
yrow = [YC + (i - 2) * 5.08 for i in range(5)]
ya = [y - 1.27 for y in yrow]
yb = [y + 1.27 for y in yrow]
place("J1", 17, 6, 180)
place("J2", 17, 50, 0)
place("J3", 8, YC - 5.08, 0, True)
place("SW1", 40, YC - 5.08, 0)
place("J4", 62, YC - 1.27, 0, True)
for i in range(5):
    place(f"R{1 + i}", 25, ya[i], 0, True)
    place(f"R{6 + i}", 21, yb[i], 0, True)
    place(f"D{1 + i}", 26, yb[i], 180, True)
for i in range(2):
    y = YC - 1.27 + 2.54 * i
    place(f"R{11 + i}", 57, y, 180, True)
    place(f"D{6 + i}", 52.5, y, 0, True)
for i, (x, y) in enumerate([(3.5, 3.5), (W - 3.5, 3.5), (3.5, H - 3.5), (W - 3.5, H - 3.5)]):
    place(f"H{1 + i}", x, y, 0, True)


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


for i in range(5):
    A = f"/AUS_{i}"
    S = f"/SW_{i}"
    jx, jy = pad("J3", str(i + 1))
    r1 = pad(f"R{1 + i}", "1")
    r2 = pad(f"R{1 + i}", "2")
    dy = r1[1] - jy
    track([(jx, jy), (9.6, jy), (9.6 + abs(dy), r1[1]), r1], A)
    sx, sy = pad("SW1", str(i + 1))
    dy = sy - r2[1]
    track([r2, (31, r2[1]), (31 + abs(dy), sy), (sx, sy)], S)
    k = pad(f"D{1 + i}", "1")
    track([k, (28.5, k[1]), (28.5, r2[1])], S)
    a = pad(f"D{1 + i}", "2")
    q2 = pad(f"R{6 + i}", "2")
    track([q2, a], f"Net-(D{1 + i}-A)")
    q1 = pad(f"R{6 + i}", "1")
    via(17, q1[1], "/+24V")
    track([(17, q1[1]), q1], "/+24V", 0.4)
for i in range(2):
    j = pad("J4", str(i + 1))
    r1 = pad(f"R{11 + i}", "1")
    r2 = pad(f"R{11 + i}", "2")
    a = pad(f"D{6 + i}", "2")
    track([j, r1], f"/EIN_{i}")
    track([r2, a], f"Net-(D{6 + i}-A)")
track([pad("J1", "1"), pad("J2", "1")], "/+24V", 0.8, pcbnew.B_Cu)

# board outline
sh = pcbnew.PCB_SHAPE(board)
sh.SetShape(pcbnew.SHAPE_T_RECT)
sh.SetStart(P(0, 0))
sh.SetEnd(P(W, H))
sh.SetLayer(pcbnew.Edge_Cuts)
sh.SetWidth(mm(0.1))
board.Add(sh)

# ground pours on both layers
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net("/GND"))
    z.SetLocalClearance(mm(0.3))
    z.SetMinThickness(mm(0.25))
    o = z.Outline()
    o.NewOutline()
    for x, y in ((0.5, 0.5), (W - 0.5, 0.5), (W - 0.5, H - 0.5), (0.5, H - 0.5)):
        o.Append(mm(OX + x), mm(OY + y))
    board.Add(z)


def text(t, x, y, size=1.0, rot=0):
    T = pcbnew.PCB_TEXT(board)
    T.SetText(t)
    T.SetPosition(P(x, y))
    T.SetLayer(pcbnew.F_SilkS)
    T.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    T.SetTextThickness(mm(size * 0.15))
    T.SetTextAngleDegrees(rot)
    board.Add(T)


text("PCB3 Ventilation Lab v2", 44.5, 3.6, 1.4)
text("Dimplex ZL 300/400 VF emulator", 44.5, 6.4, 1.0)
text("+24V", 17.6, 13.0)
text("GND", 11.6, 13.0)
text("24V IN", 25.2, 9.6, 1.1)
text("+24V", 16.4, 42.6)
text("GND", 22.3, 42.6)
text("24V OUT > ESP", 35, 50.0, 1.2)
for i, l in enumerate(["0 FAULT", "1 LVL1", "2 LVL2", "3 LVL3", "4 AUTO"]):
    text(l, 33.2, yb[i] + 0.9, 0.9)
text("J3 AUS", 8.6, YC - 7.7, 0.9)
text("0", 5.6, YC - 5.08)
text("4", 5.6, YC + 5.08)
text("J4 EIN", 61.6, YC - 4.0, 0.9)
text("0 UP", 54.8, YC - 3.3, 0.9)
text("1 DN", 54.8, YC + 3.3, 0.9)
text("ON = OUTPUT ACTIVE", 44, YC + 9.6, 0.9)

pcbnew.SaveBoard(PCB, board)
board = pcbnew.LoadBoard(PCB)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print("saved; footprints", len(board.GetFootprints()), "tracks", len(board.GetTracks()), "nets", board.GetNetCount())
