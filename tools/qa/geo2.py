import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.ToMM
e=b.GetBoardEdgesBoundingBox(); L,T=mm(e.GetLeft())+0.05,mm(e.GetTop())+0.05
print("board w,h",round(mm(e.GetWidth())-0.1,2),round(mm(e.GetHeight())-0.1,2))
for fp in b.GetFootprints():
    r=fp.GetReference()
    if r[0] in "HJ":
        bb=fp.GetBoundingBox(False)
        print(r,fp.GetValue(),"pos",round(mm(fp.GetPosition().x)-L,2),round(mm(fp.GetPosition().y)-T,2),"bbox x",round(mm(bb.GetLeft())-L,2),round(mm(bb.GetRight())-L,2),"y",round(mm(bb.GetTop())-T,2),round(mm(bb.GetBottom())-T,2),"pads",[(round(mm(p.GetPosition().x)-L,2),round(mm(p.GetPosition().y)-T,2),round(mm(p.GetDrillSize().x),2)) for p in fp.Pads()][:7])
