"""Check a JLCPCB order folder (gerbers/, BOM csv, CPL csv) against the KiCad board it was made from."""
import sys, os, re, csv, glob, zipfile, math

folder, board_path = sys.argv[1], sys.argv[2]
G = os.path.join(folder, "gerbers")
problems = []


def need(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        problems.append(msg)


files = sorted(f for f in os.listdir(G) if not f.endswith(".gbrjob"))
ext = {os.path.splitext(f)[1].lower() for f in files}
print("Gerber files:", ", ".join(os.path.splitext(f)[0].split("-")[-1] + os.path.splitext(f)[1] for f in files))
for e, what in ((".gtl", "top copper"), (".gbl", "bottom copper"), (".gts", "top solder mask"), (".gbs", "bottom solder mask"),
                (".gto", "top silkscreen"), (".gbo", "bottom silkscreen"), (".gm1", "board outline"), (".gtp", "top paste")):
    need(e in ext, f"{what} layer present ({e})")
drl = [f for f in files if f.lower().endswith(".drl")]
need(len(drl) == 2, f"plated and non-plated drill files present ({len(drl)})")


def gerber_points(path):
    s = open(path, encoding="utf8", errors="replace").read()
    m = re.search(r"%FSLAX(\d)(\d)Y\d\d\*%", s)
    div = 10 ** int(m.group(2))
    unit = 25.4 if "%MOIN*%" in s else 1.0
    pts, flashes = [], []
    x = y = 0.0
    for mm in re.finditer(r"(?:X(-?\d+))?(?:Y(-?\d+))?D0([123])\*", s):
        if mm.group(1) is not None:
            x = int(mm.group(1)) / div * unit
        if mm.group(2) is not None:
            y = int(mm.group(2)) / div * unit
        pts.append((x, y))
        if mm.group(3) == "3":
            flashes.append((x, y))
    return pts, flashes


edge = [f for f in files if f.lower().endswith(".gm1")][0]
pts, _ = gerber_points(os.path.join(G, edge))
xs, ys = [p[0] for p in pts], [p[1] for p in pts]
W, H = max(xs) - min(xs), max(ys) - min(ys)
print(f"Board outline from Gerber: {W:.1f} x {H:.1f} mm")
need(5 <= W <= 400 and 5 <= H <= 500, "board size within JLCPCB limits")

holes = {}
for f in drl:
    s = open(os.path.join(G, f), encoding="utf8", errors="replace").read()
    need("METRIC" in s, f"{f.split('-')[-1]} uses metric units")
    tools = {m.group(1): float(m.group(2)) for m in re.finditer(r"^T(\d+)C([\d.]+)", s, re.M)}
    cur = None
    for line in s.splitlines():
        m = re.match(r"^T(\d+)$", line.strip())
        if m:
            cur = m.group(1)
        elif cur and re.match(r"^X-?[\d.]+Y-?[\d.]+", line.strip()):
            holes.setdefault((("NPTH" if "NPTH" in f else "PTH"), tools[cur]), 0)
            holes[(("NPTH" if "NPTH" in f else "PTH"), tools[cur])] += 1
print("Drill table:", ", ".join(f"{k[0]} {k[1]:.2f} mm x{v}" for k, v in sorted(holes.items())))
need(min(k[1] for k in holes) >= 0.3, "smallest hole >= 0.30 mm (JLCPCB standard minimum)")

# --- assembly files ---
bom = [f for f in os.listdir(folder) if f.startswith("BOM") and f.endswith(".csv")][0]
cpl = [f for f in os.listdir(folder) if f.startswith("CPL") and f.endswith(".csv")][0]
B = list(csv.DictReader(open(os.path.join(folder, bom), encoding="utf8")))
C = list(csv.DictReader(open(os.path.join(folder, cpl), encoding="utf8")))
need(list(B[0].keys()) == ["Comment", "Designator", "Footprint", "LCSC Part #"], "BOM columns are Comment, Designator, Footprint, LCSC Part #")
need(list(C[0].keys()) == ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"], "CPL columns are Designator, Mid X, Mid Y, Layer, Rotation")
bd = [d for r in B for d in r["Designator"].split(",")]
cd = [r["Designator"] for r in C]
need(len(bd) == len(set(bd)) and set(bd) == set(cd), f"BOM and CPL list the same {len(cd)} parts, none twice")
need(all(re.fullmatch(r"C\d+", r["LCSC Part #"]) for r in B), "every BOM line has an LCSC part number")
need(all(r["Layer"].lower() == "top" for r in C), "all assembled parts are on the top side")
_, flashes = gerber_points(os.path.join(G, [f for f in files if f.lower().endswith(".gtl")][0]))
far = []
for r in C:
    x, y = float(r["Mid X"]), float(r["Mid Y"])
    d = min(math.hypot(x - fx, y - fy) for fx, fy in flashes)
    if d > 5.0:
        far.append((r["Designator"], round(d, 2)))
need(not far, "every CPL position sits on copper pads in the top-copper Gerber (same coordinate origin)" + (f" {far}" if far else ""))
z = [f for f in os.listdir(folder) if f.endswith(".zip")]
if z:
    zn = sorted(i.filename for i in zipfile.ZipFile(os.path.join(folder, z[0])).infolist())
    need(zn == files, "gerbers.zip contains exactly the current Gerber and drill files")
print("BOM:")
for r in B:
    print(f"   {len(r['Designator'].split(',')):2d} x {r['Comment']:9s} {r['LCSC Part #']:9s} {r['Footprint'].split(':')[-1]}")

# --- board file ---
import pcbnew
b = pcbnew.LoadBoard(board_path)
mm = pcbnew.ToMM
tw = [mm(t.GetWidth()) for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"]
vias = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
print(f"Board file: {b.GetCopperLayerCount()} copper layers, thickness {mm(b.GetDesignSettings().GetBoardThickness()):.1f} mm, "
      f"{len(b.GetFootprints())} footprints, tracks {min(tw):.2f}-{max(tw):.2f} mm, {len(vias)} vias")
need(b.GetCopperLayerCount() == 2, "2 copper layers")
need(min(tw) >= 0.127, "narrowest track >= 0.127 mm")
if vias:
    vd = min(mm(v.GetDrillValue()) for v in vias)
    vw = min(mm(v.GetWidth(pcbnew.F_Cu)) for v in vias)
    need(vd >= 0.3 and (vw - vd) / 2 >= 0.13, f"vias {vw:.2f}/{vd:.2f} mm: hole >= 0.3, ring >= 0.13")
ring = 9
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
            ring = min(ring, (min(mm(p.GetSize(pcbnew.F_Cu).x), mm(p.GetSize(pcbnew.F_Cu).y)) - mm(p.GetDrillSize().x)) / 2)
need(ring >= 0.13, f"smallest through-hole pad ring {ring:.2f} mm >= 0.13")
th = [(mm(t.GetTextHeight()), mm(t.GetTextThickness())) for t in b.GetDrawings() if t.GetClass() == "PCB_TEXT" and t.GetLayer() == pcbnew.F_SilkS]
if th:
    need(min(h for h, _ in th) >= 0.8, f"smallest silkscreen text height {min(h for h, _ in th):.2f} mm >= 0.8")
    print(f"  {'ok  ' if min(w for _, w in th) >= 0.15 else 'note'} thinnest silkscreen stroke {min(w for _, w in th):.3f} mm (JLCPCB recommends >= 0.15)")
bot = [fp.GetReference() for fp in b.GetFootprints() if fp.GetLayer() == pcbnew.B_Cu]
need(not bot, "no parts on the bottom side")
print("RESULT:", "all checks passed" if not problems else f"{len(problems)} problem(s): " + "; ".join(problems))
