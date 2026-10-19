import pcbnew, sys
b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.ToMM
bb=b.GetBoardEdgesBoundingBox(); ox,oy=mm(bb.GetX()),mm(bb.GetY())
hv=lambda n: any(n.startswith(p) for p in ('/+24V','/GND24','/AUS_','/INA_','/EIN_','/BASE_','/OUTC_','/PWRLED'))
hi=[];lo=[]
def add(n,x0,x1,what):
    (hi if hv(n) else lo).append((x0,x1,what,n))
for fp in b.GetFootprints():
    for p in fp.Pads():
        n=p.GetNetname()
        if not n: continue
        r=p.GetBoundingBox(); add(n,mm(r.GetX())-ox,mm(r.GetRight())-ox,f"pad {fp.GetReference()}.{p.GetNumber()}")
for t in b.GetTracks():
    r=t.GetBoundingBox(); add(t.GetNetname(),mm(r.GetX())-ox,mm(r.GetRight())-ox,t.GetClass())
for z in b.Zones():
    if z.GetIsRuleArea(): continue
    r=z.GetBoundingBox(); add(z.GetNetname(),mm(r.GetX())-ox,mm(r.GetRight())-ox,"zone")
mh=max(hi,key=lambda t:t[1]); ml=min(lo,key=lambda t:t[0])
print("24V-side copper ends at x=%.2f (%s %s)"%(mh[1],mh[2],mh[3])); print("ESP-side copper starts at x=%.2f (%s %s)"%(ml[0],ml[2],ml[3])); print("isolation gap = %.2f mm"%(ml[0]-mh[1]))
print("board size %.1f x %.1f mm"%(mm(bb.GetWidth()),mm(bb.GetHeight())))
w={}
for t in b.GetTracks():
    if t.GetClass()=="PCB_TRACK": w.setdefault(round(mm(t.GetWidth()),2),0); w[round(mm(t.GetWidth()),2)]+=1
print("track widths:",w, "vias:",sum(1 for t in b.GetTracks() if t.GetClass()=="PCB_VIA"))
for fp in b.GetFootprints():
    if fp.GetReference() in ("J1","J2","J3"):
        cy=fp.GetCourtyard(pcbnew.F_CrtYd).BBox(); px=mm(list(fp.Pads())[0].GetPosition().x)
        print(fp.GetReference(),"body left of pins %.2f mm, right of pins %.2f mm"%(px-mm(cy.GetX()),mm(cy.GetRight())-px))
