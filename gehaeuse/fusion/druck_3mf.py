"""Baut aus den Fusion-STL-Exporten eine Druck-3MF für Bambu Studio.

Unterteil steht wie konstruiert (Boden aufs Bett), Deckel wird um die x-Achse um 180° gedreht
(Oberseite mit Gravur aufs Bett, Hülsen und Steg zeigen nach oben). Keine Stützen nötig.
Aufruf: python druck_3mf.py   (braucht numpy)
"""
import os, struct, zipfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)
OUT = os.path.join(SRC, 'CentralVentilationCase_Geometrie.3mf')   # nur Geometrie; Bambu-Projekt = CentralVentilationCase_Druck.3mf
BED = 256.0                                   # Bambu P2S / P1S / X1: 256 x 256 mm


def load_stl(p):
    d = open(p, 'rb').read()
    n = struct.unpack_from('<I', d, 80)[0]
    if 84 + 50 * n == len(d):
        a = np.frombuffer(d, dtype=np.uint8, count=n * 50, offset=84).reshape(n, 50)
        return np.frombuffer(a[:, 12:48].tobytes(), dtype='<f4').reshape(n, 3, 3).astype(float)
    vs = [list(map(float, l.split()[1:4])) for l in d.decode(errors='replace').splitlines() if l.strip().startswith('vertex')]
    return np.array(vs, dtype=float).reshape(-1, 3, 3)


def mesh(tris):
    v, inv = np.unique(np.round(tris.reshape(-1, 3), 4), axis=0, return_inverse=True)
    f = inv.reshape(-1, 3)
    f = f[(f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 0] != f[:, 2])]
    return v, f


def check_closed(f):
    e = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
    _, cnt = np.unique(e, axis=0, return_counts=True)
    return int((cnt != 2).sum())


def obj_xml(oid, name, v, f):
    vx = ''.join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in v)
    tx = ''.join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in f)
    return f'<object id="{oid}" type="model" name="{name}"><mesh><vertices>{vx}</vertices><triangles>{tx}</triangles></mesh></object>'


parts = []
base = load_stl(os.path.join(SRC, 'CentralVentilationCase_Unterteil.stl'))
lid = load_stl(os.path.join(SRC, 'CentralVentilationCase_Deckel.stl'))
lid = lid * np.array([1.0, -1.0, -1.0])       # 180° um x: (x, y, z) -> (x, -y, -z), keine Spiegelung
for name, t in (('Unterteil', base), ('Deckel', lid)):
    t = t - np.array([0, 0, t[:, :, 2].min()])
    v, f = mesh(t)
    lo, hi = v.min(0), v.max(0)
    parts.append((name, v, f, lo, hi))
    print(f'{name}: {hi[0] - lo[0]:.1f} x {hi[1] - lo[1]:.1f} x {hi[2] - lo[2]:.1f} mm, {len(f)} Dreiecke, offene Kanten {check_closed(f)}')

gap = 12.0
wsum = sum(p[4][0] - p[3][0] for p in parts) + gap
x = (BED - wsum) / 2
items, objs = [], []
for i, (name, v, f, lo, hi) in enumerate(parts, 1):
    tx = x - lo[0]
    ty = BED / 2 - (lo[1] + hi[1]) / 2
    objs.append(obj_xml(i, name, v, f))
    items.append(f'<item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 {tx:.3f} {ty:.3f} 0"/>')
    x += hi[0] - lo[0] + gap

model = ('<?xml version="1.0" encoding="UTF-8"?>'
         '<model unit="millimeter" xml:lang="de-DE" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
         '<metadata name="Title">CentralVentilationCase – Gehäuse Controller v3</metadata>'
         '<metadata name="Designer">Fusion 360 (gehaeuse_fusion.py)</metadata>'
         f'<resources>{"".join(objs)}</resources><build>{"".join(items)}</build></model>')
ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml', ct)
    z.writestr('_rels/.rels', rels)
    z.writestr('3D/3dmodel.model', model)
print('geschrieben:', OUT, os.path.getsize(OUT) // 1024, 'kB')
