import pickle, sys, collections
box, others = pickle.load(open(sys.argv[1], "rb"))
def nrm(t):
    (ax,ay,az),(bx,by,bz),(cx,cy,cz)=t
    ux,uy,uz,vx,vy,vz=bx-ax,by-ay,bz-az,cx-ax,cy-ay,cz-az
    n=(uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx); l=(n[0]**2+n[1]**2+n[2]**2)**.5 or 1
    return n[0]/l,n[1]/l,n[2]/l,l/2
# standoffs: vertices on plane z=-9.3
pts=sorted({(v[0],v[1]) for t in box for v in t if abs(v[2]+9.3)<0.01})
cl=[]
for p in pts:
    for c in cl:
        if abs(c[0][0]-p[0])<8 and abs(c[0][1]-p[1])<8: c.append(p); break
    else: cl.append([p])
print("standoffs (centre x,y ; outer dia ; hole dia approx):")
for c in cl:
    xs=[p[0] for p in c]; ys=[p[1] for p in c]; cx=(min(xs)+max(xs))/2; cy=(min(ys)+max(ys))/2
    rs=sorted({round(((p[0]-cx)**2+(p[1]-cy)**2)**.5,2) for p in c})
    print("  %.2f %.2f  outer %.2f  radii %s"%(cx,cy,max(xs)-min(xs),rs[:1]+rs[-1:]))
# wall openings: axis-aligned faces inside wall thickness
def faces(axis,sign):
    acc=collections.defaultdict(lambda:[0,[],[],[]])
    for t in box:
        n=nrm(t)
        if n[axis]*sign>0.999:
            k=round(t[0][axis],2); a=acc[k]; a[0]+=n[3]
            for v in t: a[1].append(v[0]); a[2].append(v[1]); a[3].append(v[2])
    return {k:(round(a[0],1),round(min(a[1]),2),round(max(a[1]),2),round(min(a[2]),2),round(max(a[2]),2),round(min(a[3]),2),round(max(a[3]),2)) for k,a in acc.items() if 3<a[0]<200}
for axis,name in ((0,"x"),(1,"y"),(2,"z")):
    for s in (1,-1):
        print("faces normal %s%s (coord: area, xmin,xmax, ymin,ymax, zmin,zmax):"%("+" if s>0 else "-",name))
        for k,v in sorted(faces(axis,s).items()): print("   %7.2f: %s"%(k,v))
