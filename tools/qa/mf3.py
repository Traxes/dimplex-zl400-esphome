import zipfile, sys, re, collections, pickle
z = zipfile.ZipFile(sys.argv[1])
print([ (i.filename, i.file_size) for i in z.infolist()])
tris = []
for n in z.namelist():
    if not n.endswith(".model"): continue
    s = z.read(n).decode("utf8", "replace")
    for obj in re.finditer(r"<mesh>(.*?)</mesh>", s, re.S):
        m = obj.group(1)
        V = [tuple(round(float(a), 3) for a in v) for v in re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', m)]
        T = re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', m)
        tris += [(V[int(a)], V[int(b)], V[int(c)]) for a, b, c in T]
        print(n, "mesh:", len(V), "vertices", len(T), "triangles")
parent = {}
def find(a):
    while parent.setdefault(a, a) != a:
        parent[a] = parent[parent[a]]; a = parent[a]
    return a
for t in tris:
    a = find(t[0])
    for v in t[1:]: parent[find(v)] = a
comp = collections.defaultdict(list)
for t in tris: comp[find(t[0])].append(t)
parts = sorted(comp.values(), key=len, reverse=True)
def bbox(ts):
    r = []
    for k in range(3):
        c = [v[k] for t in ts for v in t]; r += [min(c), max(c)]
    return r
for p in parts[:5]:
    b = bbox(p); print("part %d tris: x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f" % (len(p), *b))
box = max(parts, key=lambda p: bbox(p)[5] - bbox(p)[4])
pickle.dump((box, [p for p in parts if p is not box]), open("v2.pkl", "wb"))
