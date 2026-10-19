"""Measure the generated enclosure STL: parts, cavity, standoffs and wall openings."""
import struct, sys, collections

path = sys.argv[1]
data = open(path, "rb").read()
tris = []
if data[:5] == b"solid" and b"facet" in data[:400]:
    vs = []
    for line in data.decode(errors="replace").splitlines():
        p = line.split()
        if p[:1] == ["vertex"]:
            vs.append(tuple(round(float(v), 3) for v in p[1:4]))
    tris = [tuple(vs[i:i + 3]) for i in range(0, len(vs), 3)]
else:
    n = struct.unpack_from("<I", data, 80)[0]
    for i in range(n):
        f = struct.unpack_from("<12f", data, 84 + 50 * i)
        tris.append(tuple(tuple(round(v, 3) for v in f[3 + 3 * k:6 + 3 * k]) for k in range(3)))
print("triangles:", len(tris))

# connected components by shared vertices
parent = {}


def find(a):
    while parent.setdefault(a, a) != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a


for t in tris:
    a = find(t[0])
    for v in t[1:]:
        parent[find(v)] = a
comp = collections.defaultdict(list)
for t in tris:
    comp[find(t[0])].append(t)
parts = sorted(comp.values(), key=len, reverse=True)


def bbox(ts):
    xs = [v[0] for t in ts for v in t]; ys = [v[1] for t in ts for v in t]; zs = [v[2] for t in ts for v in t]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


for i, p in enumerate(parts[:6]):
    b = bbox(p)
    print("part %d: %d tris  x %.2f..%.2f (%.2f)  y %.2f..%.2f (%.2f)  z %.2f..%.2f (%.2f)" % (i, len(p), b[0], b[1], b[1] - b[0], b[2], b[3], b[3] - b[2], b[4], b[5], b[5] - b[4]))


def normal(t):
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
    ux, uy, uz, vx, vy, vz = bx - ax, by - ay, bz - az, cx - ax, cy - ay, cz - az
    n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
    l = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5 or 1
    return n[0] / l, n[1] / l, n[2] / l, l / 2


def planes(ts, axis, sign):
    """total area of axis-aligned faces per coordinate"""
    acc = collections.Counter()
    for t in ts:
        n = normal(t)
        if n[axis] * sign > 0.999:
            acc[round(t[0][axis], 2)] += n[3]
    return sorted(acc.items(), key=lambda kv: -kv[1])[:6]


box = max(parts, key=lambda p: bbox(p)[5] - bbox(p)[4])
b = bbox(box)
print("\nBOX outer: %.2f x %.2f x %.2f" % (b[1] - b[0], b[3] - b[2], b[5] - b[4]))
for axis, name in ((0, "x"), (1, "y"), (2, "z")):
    print(" faces looking +%s:" % name, planes(box, axis, 1))
    print(" faces looking -%s:" % name, planes(box, axis, -1))
import pickle
pickle.dump((box, [p for p in parts if p is not box]), open(path + ".pkl", "wb"))
