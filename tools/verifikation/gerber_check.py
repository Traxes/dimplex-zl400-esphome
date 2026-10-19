"""Independent connectivity and clearance check of the fabricated Gerbers (no KiCad code involved).

Copper geometry: gerbonara + shapely from the files that were uploaded to JLCPCB.
Expected connectivity: the schematic netlist (kicad-cli export of the .kicad_sch, XML).
Pad identity: the X2 '.P' attribute (ref, pin) carried by each pad flash in the Gerber itself.
usage: python -I gerber_check.py <gerber-dir> <prefix> <schematic-netlist.xml>
"""
import sys, os, math, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv_geo"))
import warnings
warnings.filterwarnings("ignore")
from gerbonara import GerberFile, ExcellonFile
from gerbonara.utils import MM
from gerbonara import graphic_primitives as gp
from shapely.geometry import Point, LineString, Polygon, box
from shapely import affinity
from shapely.ops import unary_union
from shapely.strtree import STRtree

gdir, prefix, netxml = sys.argv[1], sys.argv[2], sys.argv[3]


def arc_pts(x1, y1, x2, y2, cx, cy, cw, n=24):
    a1, a2 = math.atan2(y1 - cy, x1 - cx), math.atan2(y2 - cy, x2 - cx)
    r = math.hypot(x1 - cx, y1 - cy)
    if cw:
        while a2 > a1: a2 -= 2 * math.pi
    else:
        while a2 < a1: a2 += 2 * math.pi
    if abs(a2 - a1) < 1e-9: a2 = a1 + (-2 * math.pi if cw else 2 * math.pi)
    return [(cx + r * math.cos(a1 + (a2 - a1) * k / n), cy + r * math.sin(a1 + (a2 - a1) * k / n)) for k in range(n + 1)]


def prim_geom(p):
    if isinstance(p, gp.Circle):
        return Point(p.x, p.y).buffer(p.r, 32)
    if isinstance(p, gp.Line):
        return LineString([(p.x1, p.y1), (p.x2, p.y2)]).buffer(p.width / 2, 16)
    if isinstance(p, gp.Arc):
        return LineString(arc_pts(p.x1, p.y1, p.x2, p.y2, p.cx, p.cy, p.clockwise)).buffer(p.width / 2, 16)
    if isinstance(p, gp.Rectangle):
        g = box(p.x - p.w / 2, p.y - p.h / 2, p.x + p.w / 2, p.y + p.h / 2)
        return affinity.rotate(g, p.rotation, origin=(p.x, p.y), use_radians=True)
    if isinstance(p, gp.ArcPoly):
        pts = []
        out = list(p.outline)
        for k in range(len(out)):
            a, b = out[k], out[(k + 1) % len(out)]
            ac = p.arc_centers[k] if k < len(p.arc_centers) else None
            if ac:
                cw, (cx, cy) = ac
                pts += arc_pts(a[0], a[1], b[0], b[1], cx, cy, cw)[:-1]
            else:
                pts.append(a)
        g = Polygon(pts) if len(pts) >= 3 else Point(out[0]).buffer(1e-6)
        return g if g.is_valid else g.buffer(0)
    raise TypeError(type(p))


def layer(path):
    g = GerberFile.open(path)
    acc, pads = None, []
    batch, batch_dark = [], True
    def flush():
        nonlocal acc, batch
        if not batch: return
        u = unary_union(batch)
        acc = u if acc is None else (acc.union(u) if batch_dark else acc.difference(u))
        batch = []
    for o in g.objects:
        prims = list(o.to_primitives(MM))
        for pr in prims:
            dark = getattr(pr, "polarity_dark", True)
            if dark != batch_dark:
                flush(); batch_dark = dark
            batch.append(prim_geom(pr))
        attrs = getattr(o, "attrs", None)
        attrs = attrs if isinstance(attrs, dict) else {}
        if ".P" in attrs:
            pads.append((attrs[".P"][0], attrs[".P"][1], unary_union([prim_geom(pr) for pr in prims])))
    flush()
    polys = list(acc.geoms) if acc.geom_type == "MultiPolygon" else [acc]
    return polys, pads


F, padsF = layer(os.path.join(gdir, prefix + "-F_Cu.gtl"))
Bk, padsB = layer(os.path.join(gdir, prefix + "-B_Cu.gbl"))
holes = [(o.x, o.y, o.aperture.diameter) for o in ExcellonFile.open(os.path.join(gdir, prefix + "-PTH.drl")).objects]
print(f"copper islands: F={len(F)} B={len(Bk)}, plated holes={len(holes)}, pad flashes F={len(padsF)} B={len(padsB)}")

# union-find over islands; plated holes join F and B islands they touch
nodes = [("F", k) for k in range(len(F))] + [("B", k) for k in range(len(Bk))]
par = {n: n for n in nodes}
def find(a):
    while par[a] != a:
        par[a] = par[par[a]]; a = par[a]
    return a
def join(a, b): par[find(a)] = find(b)
for x, y, d in holes:
    ring = Point(x, y).buffer(d / 2 + 0.05)
    hit = [("F", k) for k, g in enumerate(F) if g.intersects(ring)] + [("B", k) for k, g in enumerate(Bk) if g.intersects(ring)]
    for h in hit[1:]:
        join(hit[0], h)

def island_of(lay, geom):
    polys = F if lay == "F" else Bk
    c = geom.representative_point()
    for k, g in enumerate(polys):
        if g.contains(c):
            return find((lay, k))
    return None

# expected nets from the schematic netlist
root = ET.parse(netxml).getroot()
expect = {}
for n in root.iter("net"):
    for x in n.iter("node"):
        expect[(x.get("ref"), x.get("pin"))] = n.get("name")

pad_island = {}
for lay, lst in (("F", padsF), ("B", padsB)):
    for ref, pin, geom in lst:
        isl = island_of(lay, geom)
        pad_island.setdefault((ref, pin), set()).add(isl)

problems = 0
for key, isls in pad_island.items():
    if len(isls) != 1 or None in isls:
        print("  pad on more than one island / no copper:", key, isls); problems += 1
net_islands, island_nets = {}, {}
for key, isls in pad_island.items():
    net = expect.get(key)
    if net is None:
        if key[0].startswith("H"): continue
        print("  pad not in schematic:", key); problems += 1; continue
    isl = next(iter(isls))
    net_islands.setdefault(net, set()).add(isl)
    island_nets.setdefault(isl, set()).add(net)
missing = [k for k in expect if k not in pad_island]
for k in missing:
    print("  schematic pin without pad in Gerber:", k, expect[k]); problems += 1
for net, isls in net_islands.items():
    if len(isls) > 1:
        print(f"  OPEN: net {net} split over {len(isls)} copper groups"); problems += 1
for isl, nets in island_nets.items():
    if len(nets) > 1:
        print(f"  SHORT: copper group joins nets {sorted(nets)}"); problems += 1
multi = sum(1 for n, s in net_islands.items() if len({k for k, v in expect.items() if v == n}) > 1)
print(f"nets checked: {len(net_islands)} ({multi} with 2+ pins); schematic pins: {len(expect)}; problems: {problems}")

# clearance between different nets, per layer; isolation barrier between 24 V side and ESP side
ESP = {"/GND", "/+3V3"} | {n for n in net_islands if n.startswith(("/IN_", "/OUT_", "/OUTA_"))} | \
      {n for n in net_islands if n.startswith("unconnected-(J4") or n.startswith("unconnected-(J5")}
side = {}
for isl, nets in island_nets.items():
    side[isl] = "ESP" if nets & ESP else "24V"
for lay, polys in (("F", F), ("B", Bk)):
    items = [(find((lay, k)), g) for k, g in enumerate(polys)]
    tree = STRtree([g for _, g in items])
    best, best_iso = (9e9, None), (9e9, None)
    for i, (ii, g) in enumerate(items):
        for j in tree.query(g.buffer(10.0)):
            if j <= i: continue
            jj, h = items[j]
            if ii == jj: continue
            d = g.distance(h)
            pair = (sorted(island_nets.get(ii, {"(no pad)"})), sorted(island_nets.get(jj, {"(no pad)"})))
            if d < best[0]: best = (d, pair)
            if side.get(ii) and side.get(jj) and side[ii] != side[jj] and d < best_iso[0]:
                best_iso = (d, pair)
    print(f"{lay}.Cu: smallest copper gap between different nets {best[0]:.3f} mm {best[1]}")
    print(f"{lay}.Cu: smallest gap 24V-side <-> ESP-side {best_iso[0]:.3f} mm {best_iso[1]}")
