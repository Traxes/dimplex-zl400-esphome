"""Gehäuse Controller v3 (Trax HA – ZL 400 VF) als Fusion-360-Konstruktion (API-Skript).

Aufruf in Fusion (Skript oder MCP), in einem leeren Bauteil-Dokument mit Einheit mm:
    g = {'__file__': PFAD}; exec(compile(open(PFAD, encoding='utf8').read(), PFAD, 'exec'), g)
    g['main'](['reset', 'unterteil', 'deckel', 'beschriftung', 'referenz', 'pruefen', 'export'])
Stufen: reset, unterteil, deckel, beschriftung, referenz, pruefen, bilder, export
Ausgabe (STL, STEP, Bilder) landet im Ordner über diesem Skript (bzw. in $TRAX_CASE_OUT).

Befestigung ohne Kaufteile: Zentrierstifte auf den Domen halten die Platine seitlich, Niederhalter im Deckel
drücken sie auf die Dome. Der Deckel rastet mit 4 federnden Haken in Fenster der Unterteilwand ein; zum
Öffnen die Nase durchs Fenster mit einem kleinen Schraubendreher nach innen drücken und anheben.

Koordinaten (mm): x/y-Ursprung = Mitte Innenraum, z = 0 Unterseite Gehäuse (Druckbett).
x nach rechts (Klemmen links), y nach oben = USB-Seite.
Platinen-Koordinaten (bx, by) wie im Maßblatt: Ursprung linke obere Platinenecke, by nach unten.
Quellen: D1..D25 = Messwerte vom 19.10.2026 (Prüfplan Phase D), Bohrungen aus der Bohrdatei,
Bauteilpositionen aus KiCad (+0,05 mm, gleicher Versatz wie Bohrdatei).
"""
import adsk.core, adsk.fusion, math, os

MM = 0.1                                   # Fusion rechnet intern in cm
OUT_DIR = os.environ.get('TRAX_CASE_OUT') or os.path.dirname(os.path.dirname(os.path.abspath(globals().get('__file__', 'fusion/x.py'))))

# ---------------- Platine (gemessen) ----------------
PCB_X, PCB_Y, PCB_T = 74.93, 63.99, 1.67   # D1, D2, D15
HOLES = [(3.55, 3.35), (71.55, 3.55), (3.55, 60.55), (71.55, 60.55)]
PIN_BELOW = 3.2                            # D16
TERM_FRONT, TERM_DEPTH, TERM_H = 3.0, 8.0, 10.13   # D12, KiCad, D17
TERM_BLOCKS = [(7.2, 17.9), (18.7, 44.6), (45.4, 56.1)]
WIRE_Z = 2.98                              # D18
WIRE_Y = [10.05, 15.13, 21.55, 26.63, 31.71, 36.79, 41.87, 48.25, 53.33]
WIRE_LBL = ['+24V', 'GND', 'AUS0', 'AUS1', 'AUS2', 'AUS3', 'AUS4', 'EIN0', 'EIN1']
WIRE_D = 3.5                               # D25
USB_X, USB_FACE, USB_Z, USB_TOP = 57.54, 2.0, 5.66, 7.06   # D7, D8, D20, D21
PLUG_W, PLUG_H = 11.82, 6.44               # D23, D24
BTN = {'RST': (51.2, 4.38), 'BOOT': (63.68, 4.38)}        # D9, D10, D11
XIAO_Z, XIAO_X = 3.88, 57.67               # D19, Mitte der Stiftreihen
LED, LED_H = (16.05, 6.55), 0.8
OFF = 0.05                                 # KiCad -> Platinenkoordinaten

# ---------------- Gehäuse ----------------
GAP = 0.5
WALL, FLOOR, LID_T = 2.4, 2.4, 3.0
R_OUT, R_IN, R_TOP = 5.0, 1.5, 1.5
BOSS_H, BOSS_D = 5.0, 8.0                  # 1,8 mm Luft unter den Pins
PIN_D, PIN_UP, PIN_CH = 2.8, 0.8, 0.3      # Zentrierstift im Dom (Platinenloch Ø3,2), ragt 0,8 mm über die Platine
INNER_H = 12.0                             # Platinenoberseite bis Deckelunterseite (Klemmen 10,13 + 1,87 Luft)
CLAMP_OD, CLAMP_ID, CLAMP_GAP = 6.4, 3.6, 0.1   # Niederhalter über den Platinenlöchern, 0,1 mm Luft zur Platine
SNAP_W, SNAP_T, SNAP_ENG, SNAP_GAP = 8.0, 1.2, 0.45, 1.0   # Rasthaken: Breite, Dicke, Eingriff in die Wand, Luft zum Steg
SNAPS = [(1, 22.0), (1, 44.0), (-1, 22.0), (-1, 56.0)]     # (Seite 1 = USB-Wand, -1 = untere Wand; bx)
LIP_W, LIP_H, LIP_CLR, LIP_CORNER = 1.2, 2.0, 0.25, 9.0
WIRE_HOLE = WIRE_D + 0.4
USB_W, USB_H, USB_R = 12.6, 7.2, 1.0            # kantiger Stecker 11,82x6,44 passt noch durch die Ecken
PIN_HOLE, PIN_SINK, PIN_TUBE_OD = 1.6, 3.2, 3.6
LED_HOLE, LED_SINK, LED_TUBE_OD = 2.4, 3.4, 4.2
TAB_W, TAB_L, TAB_T, TAB_R = 16.0, 13.0, 3.5, 5.0
SLOT_W, SLOT_L = 4.4, 6.4
TABS = [(-20.0, 1), (20.0, -1)]            # (x, Seite): oben links, unten rechts
VENT_N, VENT_W, VENT_L, VENT_P, VENT_C = 7, 1.8, 22.0, 3.6, (34.0, 33.0)
ENGR = 0.4

CAV_X, CAV_Y = PCB_X + 2 * GAP, PCB_Y + 2 * GAP
OUT_X, OUT_Y = CAV_X + 2 * WALL, CAV_Y + 2 * WALL
Z_FLOOR = FLOOR
Z_PCB_BOT = FLOOR + BOSS_H
Z_PCB_TOP = Z_PCB_BOT + PCB_T
Z_LID = Z_PCB_TOP + INNER_H                # Deckelunterseite = Oberkante Wand
Z_TOP = Z_LID + LID_T
Z_WIRE = Z_PCB_TOP + WIRE_Z
Z_USB = Z_PCB_TOP + USB_Z
Z_TUBE_BOT = Z_PCB_TOP + USB_TOP + 0.4     # Stifthülse endet 0,4 mm über der USB-Buchse
Z_LED_BOT = Z_PCB_TOP + LED_H + 1.0
Z_SNAP_BOT = Z_PCB_TOP + 1.55              # Hakenende 1,55 mm über der Platine (Randstreifen ohne Bauteile)
Z_LEAD = Z_SNAP_BOT + 1.2                  # Einführschräge der Nase
Z_CATCH = Z_SNAP_BOT + 2.0                 # Rastfläche der Nase (liegt am Fenster-Oberrand an)

NEW = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation
CUT = adsk.fusion.FeatureOperations.CutFeatureOperation


# ---------------- Hilfsfunktionen ----------------
def app():
    return adsk.core.Application.get()


def design():
    return adsk.fusion.Design.cast(app().activeProduct)


def V(mm):
    return adsk.core.ValueInput.createByReal(mm * MM)


def P(x, y, z=0.0):
    return adsk.core.Point3D.create(x * MM, y * MM, z * MM)


def B(bx, by):
    """Platinen-Koordinate -> Gehäuse-Koordinate (x, y)."""
    return (bx - PCB_X / 2, PCB_Y / 2 - by)


def near(a, b, tol=0.02):
    return abs(a - b) <= tol


def coll(items):
    oc = adsk.core.ObjectCollection.create()
    for i in items:
        oc.add(i)
    return oc


def root():
    """Bauteil-Dokument: nur eine Komponente erlaubt, Teile sind getrennte Körper."""
    return design().rootComponent


def body_of(name):
    return root().bRepBodies.itemByName(name)


def plane(c, d, name, base=None):
    pi = c.constructionPlanes.createInput()
    pi.setByOffset(base or c.xYConstructionPlane, V(d))
    pl = c.constructionPlanes.add(pi)
    pl.name = name
    pl.isLightBulbOn = False
    return pl


def sketch(c, pl, name):
    sk = c.sketches.add(pl)
    sk.name = name
    return sk


def sp(sk, x, y, z):
    return sk.modelToSketchSpace(P(x, y, z))


def rect(sk, a, b):
    sk.sketchCurves.sketchLines.addTwoPointRectangle(sp(sk, *a), sp(sk, *b))


def circle(sk, x, y, z, d):
    sk.sketchCurves.sketchCircles.addByCenterRadius(sp(sk, x, y, z), d / 2 * MM)


def slot_y(sk, cx, cy, length, width, z):
    """Langloch in y-Richtung (Gesamtlänge, Breite) aus zwei Halbkreisen und zwei Linien."""
    r, h = width / 2, length / 2 - width / 2
    A, L = sk.sketchCurves.sketchArcs, sk.sketchCurves.sketchLines
    A.addByThreePoints(sp(sk, cx - r, cy + h, z), sp(sk, cx, cy + h + r, z), sp(sk, cx + r, cy + h, z))
    A.addByThreePoints(sp(sk, cx + r, cy - h, z), sp(sk, cx, cy - h - r, z), sp(sk, cx - r, cy - h, z))
    L.addByTwoPoints(sp(sk, cx - r, cy - h, z), sp(sk, cx - r, cy + h, z))
    L.addByTwoPoints(sp(sk, cx + r, cy - h, z), sp(sk, cx + r, cy + h, z))


def profiles(sk):
    return coll([sk.profiles.item(i) for i in range(sk.profiles.count)])


def extrude(c, prof, dist, op, neg=False, name=None, sym=False, bodies=None):
    ex = c.features.extrudeFeatures
    ei = ex.createInput(prof, op)
    if sym:
        ei.setSymmetricExtent(V(dist), True)
    else:
        ei.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(V(dist)),
                            adsk.fusion.ExtentDirections.NegativeExtentDirection if neg
                            else adsk.fusion.ExtentDirections.PositiveExtentDirection)
    if bodies:
        ei.participantBodies = [body_of(n) for n in bodies]
    f = ex.add(ei)
    if name:
        f.name = name
    return f


def ebb(e):
    b = e.boundingBox
    return (b.minPoint.x / MM, b.minPoint.y / MM, b.minPoint.z / MM, b.maxPoint.x / MM, b.maxPoint.y / MM, b.maxPoint.z / MM)


def edges(body, pred):
    return [e for e in body.edges if pred(ebb(e), e)]


def is_line(e):
    return e.geometry.curveType == adsk.core.Curve3DTypes.Line3DCurveType


def circ_r(e):
    g = e.geometry
    return adsk.core.Circle3D.cast(g).radius / MM if g.curveType == adsk.core.Curve3DTypes.Circle3DCurveType else None


def vertical(b):
    return b[3] - b[0] < 0.01 and b[4] - b[1] < 0.01 and b[5] - b[2] > 0.1


def planar_faces(body, nz, z):
    out = []
    for f in body.faces:
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            continue
        ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
        if abs(n.z - nz) < 1e-3 and near(f.pointOnFace.z / MM, z):
            out.append(f)
    return out


def loop_edges(face, outer=True):
    out = []
    for lp in face.loops:
        if lp.isOuter == outer:
            out += [lp.edges.item(i) for i in range(lp.edges.count)]
    return out


def fillet(c, eds, r, chain, name):
    assert eds, 'keine Kanten gefunden für ' + name
    F = c.features.filletFeatures
    fi = F.createInput()
    fi.edgeSetInputs.addConstantRadiusEdgeSet(coll(eds), V(r), chain)
    f = F.add(fi)
    f.name = name
    return f


def chamfer(c, eds, d, chain, name):
    assert eds, 'keine Kanten gefunden für ' + name
    C = c.features.chamferFeatures
    ci = C.createInput2()
    ci.chamferEdgeSets.addEqualDistanceChamferEdgeSet(coll(eds), V(d), chain)
    f = C.add(ci)
    f.name = name
    return f


def csk_holes(c, body_name, pl, pts, z, d, dsink, depth, name):
    """Senkbohrungen (90°) von der Ebene pl aus nach unten; prüft die Bohrrichtung über das Volumen."""
    sk = sketch(c, pl, name)
    oc = coll([sk.sketchPoints.add(sp(sk, x, y, z)) for (x, y) in pts])
    H = c.features.holeFeatures
    v0 = c.bRepBodies.itemByName(body_name).volume
    for default_dir in (True, False):
        hi = H.createCountersinkInput(V(d), V(dsink), adsk.core.ValueInput.createByString('90 deg'))
        hi.setPositionBySketchPoints(oc)
        hi.setDistanceExtent(V(depth))
        hi.tipAngle = adsk.core.ValueInput.createByString('180 deg')
        hi.isDefaultDirection = default_dir
        f = H.add(hi)
        if c.bRepBodies.itemByName(body_name).volume < v0 - 1e-6:
            f.name = name
            sk.isVisible = False
            return f
        f.deleteMe()
    raise RuntimeError('Bohrung schneidet nicht: ' + name)


def appearance(name):
    des = design()
    a = des.appearances.itemByName(name)
    if a:
        return a
    lib = app().materialLibraries.itemByName('Fusion-Darstellungsbibliothek')
    la = lib.appearances.itemByName(name) if lib else None
    return des.appearances.addByCopy(la, name) if la else None


def paint(c, body_name, ap_name):
    b = c.bRepBodies.itemByName(body_name)
    a = appearance(ap_name)
    if b and a:
        b.appearance = a


def hide_sketches(c):
    for i in range(c.sketches.count):
        c.sketches.item(i).isVisible = False


def text(sk, s, x, y, z, h, align='L', w=40.0):
    T = sk.sketchTexts
    inp = T.createInput2(s, h * MM)
    HA = adsk.core.HorizontalAlignments
    if align == 'L':
        a, b, ha = (x, y - h), (x + w, y + h), HA.LeftHorizontalAlignment
    else:
        a, b, ha = (x - w / 2, y - h), (x + w / 2, y + h), HA.CenterHorizontalAlignment
    inp.setAsMultiLine(sp(sk, a[0], a[1], z), sp(sk, b[0], b[1], z), ha,
                       adsk.core.VerticalAlignments.MiddleVerticalAlignment, 0)
    inp.fontName = 'Arial'
    inp.textStyle = adsk.fusion.TextStyles.TextStyleBold
    return T.add(inp)


def info(c, body_name):
    b = c.bRepBodies.itemByName(body_name)
    bb = b.boundingBox
    s = [(bb.maxPoint.x - bb.minPoint.x) / MM, (bb.maxPoint.y - bb.minPoint.y) / MM, (bb.maxPoint.z - bb.minPoint.z) / MM]
    print(f'  {body_name}: {s[0]:.2f} x {s[1]:.2f} x {s[2]:.2f} mm, z {bb.minPoint.z / MM:.2f}..{bb.maxPoint.z / MM:.2f}, '
          f'Volumen {b.volume:.2f} cm³, Flächen {b.faces.count}, gültig {b.isValid}')


# ---------------- Stufen ----------------
def reset():
    """Leert das Design, aber nur wenn es leer ist oder von diesem Skript stammt (Attribut-Marke)."""
    des = design()
    r = des.rootComponent
    mine = des.attributes.itemByName('trax_case', 'erzeugt_von') is not None
    empty = r.bRepBodies.count == 0 and r.sketches.count == 0 and r.occurrences.count == 0
    assert mine or empty, 'Design enthält fremde Inhalte, Abbruch'
    tl = des.timeline
    if tl.count:
        tl.moveToBeginning()
        tl.deleteAllAfterMarker()
    des.attributes.add('trax_case', 'erzeugt_von', 'gehaeuse_fusion.py')
    print('Design geleert')


def unterteil():
    c = root()
    body = lambda: body_of('Unterteil')
    sk = sketch(c, c.xYConstructionPlane, 'Außenkontur')
    rect(sk, (-OUT_X / 2, -OUT_Y / 2, 0), (OUT_X / 2, OUT_Y / 2, 0))
    f = extrude(c, sk.profiles.item(0), Z_LID, NEW, name='Grundkörper')
    f.bodies.item(0).name = 'Unterteil'
    fillet(c, edges(body(), lambda b, e: is_line(e) and vertical(b) and near(abs(b[0]), OUT_X / 2) and near(abs(b[1]), OUT_Y / 2)),
           R_OUT, False, 'Außenecken R5')
    pl = plane(c, Z_FLOOR, 'Bodenoberseite')
    sk = sketch(c, pl, 'Innenraum')
    rect(sk, (-CAV_X / 2, -CAV_Y / 2, Z_FLOOR), (CAV_X / 2, CAV_Y / 2, Z_FLOOR))
    extrude(c, sk.profiles.item(0), Z_LID - Z_FLOOR + 1, CUT, name='Innenraum', bodies=['Unterteil'])
    fillet(c, edges(body(), lambda b, e: is_line(e) and vertical(b) and near(abs(b[0]), CAV_X / 2) and near(abs(b[1]), CAV_Y / 2)),
           R_IN, False, 'Innenecken R1,5')
    chamfer(c, loop_edges(planar_faces(body(), -1, 0)[0], True), 0.6, True, 'Fase Unterkante')
    top = planar_faces(body(), 1, Z_LID)[0]
    chamfer(c, loop_edges(top, True) + loop_edges(top, False), 0.5, True, 'Fasen Oberkante (Schattenfuge, Einführung)')

    # Dome mit Einschmelzmuttern
    sk = sketch(c, pl, 'Dome')
    for (bx, by) in HOLES:
        circle(sk, *B(bx, by), Z_FLOOR, BOSS_D)
    extrude(c, profiles(sk), BOSS_H, JOIN, name='Dome Ø8', bodies=['Unterteil'])
    pl2 = plane(c, Z_PCB_BOT, 'Auflage Platine')
    sk = sketch(c, pl2, 'Zentrierstifte')
    for (bx, by) in HOLES:
        circle(sk, *B(bx, by), Z_PCB_BOT, PIN_D)
    extrude(c, profiles(sk), PCB_T + PIN_UP, JOIN, name='Zentrierstifte Ø2,8', bodies=['Unterteil'])
    chamfer(c, edges(body(), lambda b, e: circ_r(e) is not None and near(circ_r(e), PIN_D / 2) and near(b[5], Z_PCB_BOT + PCB_T + PIN_UP)),
            PIN_CH, False, 'Fase Zentrierstifte')

    # Kabellöcher links
    yz = c.yZConstructionPlane
    xw = -(OUT_X / 2 - WALL / 2)
    plw = plane(c, xw * yz.geometry.normal.x, 'Wandmitte links', base=yz)
    sk = sketch(c, plw, 'Kabellöcher')
    for by in WIRE_Y:
        circle(sk, xw, B(0, by)[1], Z_WIRE, WIRE_HOLE)
    extrude(c, profiles(sk), WALL + 4, CUT, sym=True, name='Kabellöcher 9x Ø3,9', bodies=['Unterteil'])
    chamfer(c, edges(body(), lambda b, e: circ_r(e) is not None and near(circ_r(e), WIRE_HOLE / 2) and near(b[0], -OUT_X / 2) and near(b[3], -OUT_X / 2)),
            0.4, False, 'Fase Kabellöcher')

    # USB-Öffnung oben
    xz = c.xZConstructionPlane
    yw = OUT_Y / 2 - WALL / 2
    xu = B(USB_X, 0)[0]
    plu = plane(c, yw * xz.geometry.normal.y, 'Wandmitte oben', base=xz)
    sk = sketch(c, plu, 'USB-Öffnung')
    rect(sk, (xu - USB_W / 2, yw, Z_USB - USB_H / 2), (xu + USB_W / 2, yw, Z_USB + USB_H / 2))
    extrude(c, sk.profiles.item(0), WALL + 4, CUT, sym=True, name='USB-Öffnung 12,6x7,2', bodies=['Unterteil'])
    fillet(c, edges(body(), lambda b, e: is_line(e) and b[3] - b[0] < .01 and b[5] - b[2] < .01 and b[4] - b[1] > 1
                    and near(abs(b[0] - xu), USB_W / 2) and near(abs(b[2] - Z_USB), USB_H / 2)), USB_R, False, 'Rundung USB-Öffnung')

    # Rastfenster für die Deckelhaken (durchgehend, damit man die Nase von außen lösen kann)
    for s, wname in ((1, 'oben'), (-1, 'unten')):
        ys = s * yw
        plr = plane(c, ys * xz.geometry.normal.y, 'Wandmitte ' + wname + ' (Rastfenster)', base=xz)
        sk = sketch(c, plr, 'Rastfenster ' + wname)
        for side, bx in SNAPS:
            if side == s:
                x = B(bx, 0)[0]
                rect(sk, (x - SNAP_W / 2 - 0.3, ys, Z_SNAP_BOT - 0.1), (x + SNAP_W / 2 + 0.3, ys, Z_CATCH + 0.1))
        extrude(c, profiles(sk), WALL + 4, CUT, sym=True, name='Rastfenster ' + wname, bodies=['Unterteil'])

    # Montagelaschen
    sk = sketch(c, c.xYConstructionPlane, 'Montagelaschen')
    for tx, s in TABS:
        y0, y1 = s * (OUT_Y / 2 - 1), s * (OUT_Y / 2 + TAB_L)
        rect(sk, (tx - TAB_W / 2, min(y0, y1), 0), (tx + TAB_W / 2, max(y0, y1), 0))
    extrude(c, profiles(sk), TAB_T, JOIN, name='Montagelaschen', bodies=['Unterteil'])
    fillet(c, edges(body(), lambda b, e: is_line(e) and vertical(b) and near(abs(b[1]), OUT_Y / 2 + TAB_L)), TAB_R, False, 'Rundung Laschen')
    sk = sketch(c, c.xYConstructionPlane, 'Langlöcher')
    for tx, s in TABS:
        slot_y(sk, tx, s * (OUT_Y / 2 + TAB_L - 5.5), SLOT_L, SLOT_W, 0)
    extrude(c, profiles(sk), TAB_T + 1, CUT, name='Langlöcher Ø4', bodies=['Unterteil'])
    fillet(c, edges(body(), lambda b, e: is_line(e) and b[4] - b[1] < .01 and b[5] - b[2] < .01 and b[3] - b[0] > 1
                    and near(b[2], TAB_T) and near(abs(b[1]), OUT_Y / 2)), 2.0, False, 'Hohlkehle Laschen')
    paint(c, 'Unterteil', 'Kunststoff - matt (Weiß)')
    hide_sketches(c)
    info(c, 'Unterteil')


def deckel():
    c = root()
    body = lambda: body_of('Deckel')
    plb = plane(c, Z_LID, 'Deckelunterseite')
    plt = plane(c, Z_TOP, 'Deckeloberseite')
    sk = sketch(c, plb, 'Außenkontur')
    rect(sk, (-OUT_X / 2, -OUT_Y / 2, Z_LID), (OUT_X / 2, OUT_Y / 2, Z_LID))
    f = extrude(c, sk.profiles.item(0), LID_T, NEW, name='Deckelplatte')
    f.bodies.item(0).name = 'Deckel'
    fillet(c, edges(body(), lambda b, e: is_line(e) and vertical(b) and near(abs(b[0]), OUT_X / 2) and near(abs(b[1]), OUT_Y / 2)),
           R_OUT, False, 'Außenecken R5')
    fillet(c, loop_edges(planar_faces(body(), 1, Z_TOP)[0], True), R_TOP, True, 'Rundung Oberkante R1,5')
    chamfer(c, loop_edges(planar_faces(body(), -1, Z_LID)[0], True), 0.5, True, 'Fase Unterkante (Schattenfuge)')

    # Zentriersteg (4 gerade Stücke, Ecken frei für die Abstandsbolzen)
    sk = sketch(c, plb, 'Zentriersteg')
    xo, yo = CAV_X / 2 - LIP_CLR, CAV_Y / 2 - LIP_CLR
    xi, yi = xo - LIP_W, yo - LIP_W
    xc, yc = CAV_X / 2 - LIP_CORNER, CAV_Y / 2 - LIP_CORNER
    for s in (1, -1):
        x0 = -xc
        for xs in sorted(B(bx, 0)[0] for side, bx in SNAPS if side == s):
            rect(sk, (x0, s * yi, Z_LID), (xs - SNAP_W / 2 - SNAP_GAP, s * yo, Z_LID))
            x0 = xs + SNAP_W / 2 + SNAP_GAP
        rect(sk, (x0, s * yi, Z_LID), (xc, s * yo, Z_LID))
        rect(sk, (s * xi, -yc, Z_LID), (s * xo, yc, Z_LID))
    extrude(c, profiles(sk), LIP_H, JOIN, neg=True, name='Zentriersteg', bodies=['Deckel'])
    zl = Z_LID - LIP_H
    chamfer(c, edges(body(), lambda b, e: is_line(e) and near(b[2], zl) and near(b[5], zl) and
                     ((near(abs(b[1]), yo) and near(abs(b[4]), yo)) or (near(abs(b[0]), xo) and near(abs(b[3]), xo)))),
            0.4, False, 'Fase Zentriersteg')

    # Rasthaken: federnder Steg + Nase mit Einführschräge, rastet unter den Fenster-Oberrand
    sk = sketch(c, plb, 'Rasthaken')
    for s, bx in SNAPS:
        x = B(bx, 0)[0]
        rect(sk, (x - SNAP_W / 2, s * (yo - SNAP_T), Z_LID), (x + SNAP_W / 2, s * yo, Z_LID))
    extrude(c, profiles(sk), Z_LID - Z_SNAP_BOT, JOIN, neg=True, name='Rasthaken (4x)', bodies=['Deckel'])
    yzp = c.yZConstructionPlane
    yt = CAV_Y / 2 + SNAP_ENG
    for i, (s, bx) in enumerate(SNAPS, 1):
        x = B(bx, 0)[0]
        pln = plane(c, x * yzp.geometry.normal.x, f'Mitte Rasthaken {i}', base=yzp)
        sk = sketch(c, pln, f'Rastnase {i}')
        pts = [(yo - 0.3, Z_SNAP_BOT), (yo, Z_SNAP_BOT), (yt, Z_LEAD), (yt, Z_CATCH), (yo - 0.3, Z_CATCH)]
        for k in range(len(pts)):
            (y0, z0), (y1, z1) = pts[k], pts[(k + 1) % len(pts)]
            sk.sketchCurves.sketchLines.addByTwoPoints(sp(sk, x, s * y0, z0), sp(sk, x, s * y1, z1))
        extrude(c, sk.profiles.item(0), SNAP_W, JOIN, sym=True, name=f'Rastnase {i}', bodies=['Deckel'])
    yin = yo - SNAP_T
    eds = []
    for s, bx in SNAPS:
        x = B(bx, 0)[0]
        eds += edges(body(), lambda b, e, x=x, s=s: is_line(e) and near(b[2], Z_LID) and near(b[5], Z_LID)
                     and near(b[1], s * yin) and near(b[4], s * yin) and b[0] > x - SNAP_W / 2 - 0.05 and b[3] < x + SNAP_W / 2 + 0.05)
    fillet(c, eds, 0.8, False, 'Hohlkehle Rasthaken')

    # Niederhalter: drücken die Platine über den Löchern auf die Dome, Freistich für die Zentrierstifte
    sk = sketch(c, plb, 'Niederhalter')
    for h in HOLES:
        circle(sk, *B(*h), Z_LID, CLAMP_OD)
    extrude(c, profiles(sk), Z_LID - (Z_PCB_TOP + CLAMP_GAP), JOIN, neg=True, name='Niederhalter Platine (4x)', bodies=['Deckel'])
    plc = plane(c, Z_PCB_TOP + CLAMP_GAP, 'Unterkante Niederhalter')
    sk = sketch(c, plc, 'Freistich Zentrierstift')
    for h in HOLES:
        circle(sk, *B(*h), Z_PCB_TOP + CLAMP_GAP, CLAMP_ID)
    extrude(c, profiles(sk), 3.0, CUT, name='Freistich Zentrierstift', bodies=['Deckel'])

    # Stifthülsen RESET/BOOT
    sk = sketch(c, plb, 'Stifthülsen')
    for (bx, by) in BTN.values():
        circle(sk, *B(bx, by), Z_LID, PIN_TUBE_OD)
    extrude(c, profiles(sk), Z_LID - Z_TUBE_BOT, JOIN, neg=True, name='Stifthülsen RST/BOOT', bodies=['Deckel'])
    csk_holes(c, 'Deckel', plt, [B(*v) for v in BTN.values()], Z_TOP, PIN_HOLE, PIN_SINK, Z_TOP - Z_TUBE_BOT + 0.5, 'Stiftlöcher RST/BOOT')

    # Lichtleiter LED "24V OK"
    sk = sketch(c, plb, 'Lichtleiter')
    circle(sk, *B(*LED), Z_LID, LED_TUBE_OD)
    extrude(c, sk.profiles.item(0), Z_LID - Z_LED_BOT, JOIN, neg=True, name='Lichtleiter 24V OK', bodies=['Deckel'])
    csk_holes(c, 'Deckel', plt, [B(*LED)], Z_TOP, LED_HOLE, LED_SINK, Z_TOP - Z_LED_BOT + 0.5, 'LED-Fenster')

    # Lüftungsschlitze über den Optokopplern
    sk = sketch(c, plt, 'Lüftungsschlitze')
    vx, vy = B(*VENT_C)
    for i in range(VENT_N):
        slot_y(sk, vx + (i - (VENT_N - 1) / 2) * VENT_P, vy, VENT_L, VENT_W, Z_TOP)
    extrude(c, profiles(sk), LID_T + 0.5, CUT, neg=True, name='Lüftungsschlitze', bodies=['Deckel'])
    paint(c, 'Deckel', 'Kunststoff - matt (Grau)')
    hide_sketches(c)
    info(c, 'Deckel')


def beschriftung():
    c = root()
    plt = c.constructionPlanes.itemByName('Deckeloberseite')
    sk = sketch(c, plt, 'Beschriftung')
    z = Z_TOP
    items = [text(sk, lab, -OUT_X / 2 + 2.2, B(0, by)[1], z, 2.6) for by, lab in zip(WIRE_Y, WIRE_LBL)]
    lx, ly = B(*LED)
    items.append(text(sk, '24V OK', lx + 2.6, ly, z, 2.2))
    for name, (bx, by) in BTN.items():
        x, y = B(bx, by)
        items.append(text(sk, name, x, y - 3.8, z, 2.2, 'C', 14))
    items.append(text(sk, 'USB', B(USB_X, 0)[0], OUT_Y / 2 - 3.4, z, 2.0, 'C', 14))
    items.append(text(sk, 'Trax HA · ZL 400 VF', 0, -24.5, z, 3.4, 'C', 60))
    items.append(text(sk, 'Controller v3 · 24 V DC', 0, -29.5, z, 2.2, 'C', 60))
    for t in items:
        extrude(c, t, ENGR, CUT, neg=True, name='Gravur ' + t.text, bodies=['Deckel'])
    sk.isVisible = False
    info(c, 'Deckel')


def referenz():
    tbm = adsk.fusion.TemporaryBRepManager.get()
    BT = adsk.fusion.BooleanTypes

    def box(x0, y0, z0, x1, y1, z1):
        obb = adsk.core.OrientedBoundingBox3D.create(P((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2),
                                                     adsk.core.Vector3D.create(1, 0, 0), adsk.core.Vector3D.create(0, 1, 0),
                                                     abs(x1 - x0) * MM, abs(y1 - y0) * MM, abs(z1 - z0) * MM)
        return tbm.createBox(obb)

    def bbox(bx0, by0, bx1, by1, z0, z1):
        (x0, y0), (x1, y1) = B(bx0, by0), B(bx1, by1)
        return box(min(x0, x1), min(y0, y1), z0, max(x0, x1), max(y0, y1), z1)

    def cbox(bx, by, lx, ly, z0, z1):
        return bbox(bx - lx / 2, by - ly / 2, bx + lx / 2, by + ly / 2, z0, z1)

    def cyl(x, y, z0, z1, r0, r1=None):
        return tbm.createCylinderOrCone(P(x, y, z0), r0 * MM, P(x, y, z1), (r0 if r1 is None else r1) * MM)

    def union(lst):
        r = lst[0]
        for t in lst[1:]:
            tbm.booleanOperation(r, t, BT.UnionBooleanType)
        return r

    def minus(a, lst):
        for t in lst:
            tbm.booleanOperation(a, t, BT.DifferenceBooleanType)
        return a

    def hexprism(x, y, z0, z1, af):
        res = None
        for k in range(3):
            a = math.radians(60 * k)
            obb = adsk.core.OrientedBoundingBox3D.create(P(x, y, (z0 + z1) / 2),
                                                         adsk.core.Vector3D.create(math.cos(a), math.sin(a), 0),
                                                         adsk.core.Vector3D.create(-math.sin(a), math.cos(a), 0),
                                                         af * MM, 3 * af * MM, (z1 - z0) * MM)
            s = tbm.createBox(obb)
            if res is None:
                res = s
            else:
                tbm.booleanOperation(res, s, BT.IntersectionBooleanType)
        return res

    def add(c, feature_name, items):
        bf = c.features.baseFeatures.add()
        bf.name = feature_name
        bf.startEdit()
        for name, tb, ap in items:
            b = c.bRepBodies.add(tb, bf)
            b.name = name
        bf.finishEdit()
        for name, tb, ap in items:
            paint(c, name, ap)

    zt = Z_PCB_TOP
    k = lambda v: v + OFF
    # ---- Platine mit Bauteilen ----
    pcb = minus(bbox(0, 0, PCB_X, PCB_Y, Z_PCB_BOT, zt), [cyl(*B(*h), Z_PCB_BOT - 1, zt + 1, 1.6) for h in HOLES])
    term = union([bbox(TERM_FRONT, y0, TERM_FRONT + TERM_DEPTH, y1, zt, zt + TERM_H) for (y0, y1) in TERM_BLOCKS])
    term = minus(term, [cbox(TERM_FRONT + 1.0, by, 2.0, 3.0, zt + WIRE_Z - 1.5, zt + WIRE_Z + 1.5) for by in WIRE_Y])
    pins = union([cbox(6.05, by, 1.0, 1.0, Z_PCB_BOT - PIN_BELOW, Z_PCB_BOT) for by in WIRE_Y] +
                 [cbox(px, 6.05 + 2.54 * n, 0.64, 0.64, Z_PCB_BOT - PIN_BELOW, Z_PCB_BOT) for px in (50.05, 65.29) for n in range(7)])
    hdr = union([cbox(px, 13.67, 2.54, 17.78, zt, zt + 2.5) for px in (50.05, 65.29)])
    xiao = bbox(XIAO_X - 8.9, 3.0, XIAO_X + 8.9, 24.0, zt + XIAO_Z, zt + XIAO_Z + 1.0)
    usb = bbox(USB_X - 4.47, USB_FACE, USB_X + 4.47, USB_FACE + 7.35, zt + XIAO_Z + 1.0, zt + USB_TOP)
    btn = union([cbox(bx, by, 2.6, 1.6, zt + XIAO_Z + 1.0, zt + XIAO_Z + 1.5) for (bx, by) in BTN.values()])
    opto = union([cbox(k(34.0), k(y), 6.5, 4.6, zt, zt + 3.65) for y in (14.0, 20.35, 26.7, 33.05, 39.4, 45.75, 52.1)])
    led = cbox(LED[0], LED[1], 2.0, 1.25, zt, zt + LED_H)
    diodes = union([cbox(k(14.3), k(10.0), 2.7, 1.6, zt, zt + 1.1), cbox(k(14.3), k(15.08), 2.7, 1.6, zt, zt + 1.1)] +
                   [cbox(k(26.7), k(y), 1.6, 2.7, zt, zt + 1.1) for y in (14.0, 20.35, 26.7, 33.05, 39.4)] +
                   [cbox(k(19.5), k(y), 2.9, 1.3, zt, zt + 1.0) for y in (46.07, 52.42)])
    rx = [(23.5, 12.73), (23.5, 19.08), (23.5, 25.43), (23.5, 31.78), (23.5, 38.13), (43.5, 47.02), (43.5, 53.37),
          (26.2, 47.02), (26.2, 53.37), (20.0, 6.5), (15.6, 46.07), (15.6, 52.42)]
    ry = [(43.5, 16.18), (43.5, 22.53), (43.5, 28.88), (43.5, 35.23), (43.5, 41.58), (23.0, 46.06), (23.0, 52.41),
          (46.6, 47.93), (46.6, 54.28)]
    res = union([cbox(k(x), k(y), 2.0, 1.25, zt, zt + 0.5) for (x, y) in rx] + [cbox(k(x), k(y), 1.25, 2.0, zt, zt + 0.5) for (x, y) in ry])
    xu, yf = B(USB_X, USB_FACE - 0.3)
    plug = union([box(xu - PLUG_W / 2, yf, Z_USB - PLUG_H / 2, xu + PLUG_W / 2, yf + 22, Z_USB + PLUG_H / 2),
                  tbm.createCylinderOrCone(P(xu, yf + 22, Z_USB), 2.0 * MM, P(xu, yf + 45, Z_USB), 2.0 * MM)])
    xa = B(TERM_FRONT - 0.1, 0)[0]
    wires = union([tbm.createCylinderOrCone(P(xa, B(0, by)[1], Z_WIRE), WIRE_D / 2 * MM, P(xa - 30, B(0, by)[1], Z_WIRE), WIRE_D / 2 * MM)
                   for by in WIRE_Y])
    c = root()
    add(c, 'Referenz Platine Controller v3', [
        ('Ref Platine', pcb, 'Kunststoff - matt (Grün)'), ('Ref Klemmen J1–J3', term, 'Kunststoff - glänzend (Grün)'),
        ('Ref Pins unten', pins, 'Edelstahl - satiniert'), ('Ref Stiftleisten', hdr, 'Kunststoff - matt (Schwarz)'),
        ('Ref XIAO ESP32-C6', xiao, 'Kunststoff - matt (Blau)'), ('Ref USB-C-Buchse', usb, 'Edelstahl - satiniert'),
        ('Ref Taster RST/BOOT', btn, 'Kunststoff - matt (Weiß)'), ('Ref Optokoppler U1–U7', opto, 'Kunststoff - matt (Weiß)'),
        ('Ref LED 24V OK', led, 'LED (Grün)'), ('Ref Dioden und Transistoren', diodes, 'Kunststoff - matt (Schwarz)'),
        ('Ref Widerstände', res, 'Kunststoff - matt (Schwarz)'), ('Ref USB-Stecker (Kabel)', plug, 'Kunststoff - glänzend (Schwarz)'),
        ('Ref Adern 9x Ø3,5', wires, 'Kunststoff - glänzend (Rot)')])

    print('Referenz angelegt')


def pruefen():
    des = design()
    bodies = [root().bRepBodies.item(i) for i in range(root().bRepBodies.count)]
    ii = des.createInterferenceInput(coll(bodies))
    ii.areCoincidentFacesIncluded = False
    res = des.analyzeInterference(ii)
    print('Überschneidungen (ohne Berührflächen):', res.count)
    for i in range(res.count):
        r = res.item(i)
        print(f'  {r.entityOne.name} x {r.entityTwo.name}: {r.interferenceBody.volume * 1000:.4f} mm³')
    mm = app().measureManager
    refs = [b for b in bodies if b.name.startswith('Ref ')]
    for part in ('Deckel', 'Unterteil'):
        gaps = sorted((mm.measureMinimumDistance(body_of(part), rb).value / MM, rb.name) for rb in refs)
        print(f'  kleinster Abstand {part} zu: ' + ', '.join(f'{n} {d:.2f} mm' for d, n in gaps[:7]))
    for part in ('Unterteil', 'Deckel'):
        info(root(), part)


def bilder():
    vp = app().activeViewport
    vp.visualStyle = adsk.core.VisualStyles.ShadedWithVisibleEdgesOnlyVisualStyle
    bodies = [root().bRepBodies.item(i) for i in range(root().bRepBodies.count)]
    shots = [('Ansicht_gesamt', (-170, -210, 170), (0, 0, 1), ()),
             ('Ansicht_USB_Seite', (90, 240, 120), (0, 0, 1), ()),
             ('Ansicht_innen', (-120, -170, 210), (0, 0, 1), ('Deckel',)),
             ('Ansicht_oben', (0, 0, 320), (0, 1, 0), ()),
             ('Ansicht_Deckel_unten', (-90, -150, -120), (0, 0, 1), ('Unterteil', 'Ref '))]
    out = []
    for name, eye, up, hidden in shots:
        for b in bodies:
            b.isLightBulbOn = not any(b.name.startswith(h) for h in hidden)
        cam = vp.camera
        cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType if name == 'Ansicht_oben' else adsk.core.CameraTypes.PerspectiveCameraType
        cam.target = P(0, 0, 10)
        cam.eye = P(*eye)
        cam.upVector = adsk.core.Vector3D.create(*up)
        cam.isFitView = True
        vp.camera = cam
        vp.refresh()
        p = os.path.join(OUT_DIR, 'fusion', name + '.png')
        vp.saveAsImageFile(p, 1600, 1100)
        out.append(p)
    for b in bodies:
        b.isLightBulbOn = True
    cam = vp.camera
    cam.cameraType = adsk.core.CameraTypes.PerspectiveCameraType
    cam.target = P(0, 0, 10)
    cam.eye = P(-170, -210, 170)
    cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
    cam.isFitView = True
    vp.camera = cam
    vp.refresh()
    print('Bilder:', out)


def export():
    des = design()
    em = des.exportManager
    files = []
    for part in ('Unterteil', 'Deckel'):
        p = os.path.join(OUT_DIR, f'CentralVentilationCase_{part}.stl')
        o = em.createSTLExportOptions(body_of(part), p)
        o.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
        o.isBinaryFormat = True
        o.sendToPrintUtility = False
        if hasattr(o, 'unitType'):
            o.unitType = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        em.execute(o)
        files.append(p)
    p = os.path.join(OUT_DIR, 'CentralVentilationCase_Baugruppe.step')
    em.execute(em.createSTEPExportOptions(p, root()))
    files.append(p)
    p = os.path.join(OUT_DIR, 'fusion', 'CentralVentilationCase.f3d')
    em.execute(em.createFusionArchiveExportOptions(p, root()))
    files.append(p)
    print('Exportiert:', files)


def main(stages):
    for s in stages:
        globals()[s]()
        print('Stufe', s, 'fertig')
