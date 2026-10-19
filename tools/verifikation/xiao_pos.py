import zipfile,sys,re
z=zipfile.ZipFile(sys.argv[1])
n=[i for i in z.namelist() if i.endswith('.kicad_pcb')][0]
s=z.read(n).decode('utf8','replace')
# footprints: find each "(footprint" block start and its (at ...) and Reference
for m in re.finditer(r'\(footprint "([^"]+)"(.*?)\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)',s,re.S):
    blk=s[m.start():m.start()+6000]
    ref=re.search(r'\(property "Reference" "([^"]+)"',blk)
    ref=ref.group(1) if ref else '?'
    if re.match(r'(ANT|J|U|Q|K|P|H|TP1$)',ref) or 'Pin' in m.group(1) or 'USB' in m.group(1).upper():
        layer=re.search(r'\(layer "([^"]+)"',blk).group(1)
        print(ref,m.group(1),m.group(3),m.group(4),m.group(5),layer)
# edge cuts
xs=[];ys=[]
for m in re.finditer(r'\(gr_(?:line|rect|arc)[^()]*?\(start ([-\d.]+) ([-\d.]+)\)\s*\((?:end|mid) ([-\d.]+) ([-\d.]+)\)(.*?)\(layer "Edge.Cuts"\)',s,re.S):
    xs+= [float(m.group(1)),float(m.group(3))]; ys+=[float(m.group(2)),float(m.group(4))]
print('edge x',min(xs),max(xs),'y',min(ys),max(ys))
for m in re.finditer(r'\(zone(.*?)\n\t\)',s,re.S):
    b=m.group(1)
    if 'keepout' in b:
        pts=re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)',b)[:8]
        print('KEEPOUT',re.search(r'\(layers? ([^)]*)\)',b).group(1),pts)
