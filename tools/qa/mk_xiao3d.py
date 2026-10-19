"""Write a simple VRML model of a Seeed XIAO ESP32-C6 and attach it (plus its pin headers) to socket J4 of the controller board.
3D models do not change any fabrication output."""
import os, sys, pcbnew

board_path = sys.argv[1]
proj = os.path.dirname(board_path)
os.makedirs(os.path.join(proj, "3d"), exist_ok=True)
S = 1 / 2.54          # KiCad reads VRML in units of 0.1 inch
parts = []


def mat(rgb, shiny=0.2, spec=0.3):
    return "appearance Appearance { material Material { diffuseColor %g %g %g specularColor %g %g %g shininess %g } }" % (*rgb, spec, spec, spec, shiny)


def box(cx, cy, cz, sx, sy, sz, rgb, shiny=0.2, spec=0.3):
    parts.append("Transform { translation %.4f %.4f %.4f children [ Shape { %s geometry Box { size %.4f %.4f %.4f } } ] }"
                 % (cx * S, cy * S, cz * S, mat(rgb, shiny, spec), sx * S, sy * S, sz * S))


def cyl(cx, cy, cz, r, h, rgb, shiny=0.6, spec=0.7):
    # VRML cylinders stand along Y; turn them to stand along Z
    parts.append("Transform { translation %.4f %.4f %.4f rotation 1 0 0 1.5708 children [ Shape { %s geometry Cylinder { radius %.4f height %.4f } } ] }"
                 % (cx * S, cy * S, cz * S, mat(rgb, shiny, spec), r * S, h * S))


BLACK, GOLD, STEEL, CAN = (0.06, 0.06, 0.08), (0.83, 0.68, 0.22), (0.72, 0.72, 0.74), (0.80, 0.80, 0.82)
T = 1.0                                                        # board thickness
box(0, 0, T / 2, 17.8, 21.0, T, BLACK, 0.1, 0.1)                # XIAO circuit board 21 x 17.8 mm
for i in range(7):                                              # castellated pads along both long edges
    for sx in (-1, 1):
        box(sx * 8.15, 7.62 - 2.54 * i, T / 2, 1.5, 1.7, T + 0.04, GOLD, 0.6, 0.7)
box(0, 8.1, T + 1.58, 8.94, 7.35, 3.16, STEEL, 0.7, 0.8)        # USB-C socket, overhangs the board edge
box(0, 11.76, T + 1.58, 7.6, 0.06, 1.9, (0.03, 0.03, 0.03), 0.0, 0.0)
box(0, 11.74, T + 1.58, 6.4, 0.08, 0.6, (0.15, 0.15, 0.15), 0.0, 0.0)
box(0, -1.2, T + 1.0, 9.6, 9.8, 2.0, CAN, 0.6, 0.7)             # shield can over the ESP32-C6
box(0, -1.2, T + 2.01, 8.6, 8.8, 0.02, (0.86, 0.86, 0.88), 0.7, 0.8)
for sx in (-1, 1):                                              # BOOT and RESET buttons
    box(sx * 6.9, 8.0, T + 0.5, 1.9, 2.9, 1.0, STEEL, 0.5, 0.6)
    box(sx * 6.9, 8.0, T + 1.1, 0.9, 1.3, 0.25, (0.1, 0.1, 0.1), 0.1, 0.1)
box(-6.0, -8.6, T + 0.2, 2.6, 2.6, 0.4, (0.9, 0.88, 0.8), 0.2, 0.2)   # U.FL antenna connector
cyl(-6.0, -8.6, T + 0.8, 1.0, 0.9, GOLD)
box(2.0, -9.3, T + 0.5, 5.2, 1.6, 1.0, (0.78, 0.63, 0.42), 0.2, 0.2)  # ceramic chip antenna
box(-5.6, 4.6, T + 0.25, 1.0, 0.5, 0.5, (0.95, 0.85, 0.3), 0.3, 0.3)  # user LED
box(5.6, 4.6, T + 0.25, 1.0, 0.5, 0.5, (0.85, 0.2, 0.15), 0.3, 0.3)   # charge LED
for x, y in ((-5.5, 1.5), (-5.5, -0.5), (5.5, 1.5), (5.5, -0.5), (-2.5, -7.3), (5.5, -6.6)):   # small passives
    box(x, y, T + 0.25, 1.0, 0.5, 0.5, (0.45, 0.33, 0.22), 0.1, 0.1)

wrl = os.path.join(proj, "3d", "XIAO_ESP32C6.wrl")
open(wrl, "w").write("#VRML V2.0 utf8\n# Simplified Seeed XIAO ESP32-C6, 21 x 17.8 mm, origin = board centre, bottom face at z=0\n" + "\n".join(parts) + "\n")

b = pcbnew.LoadBoard(board_path)
j4, j5 = b.FindFootprintByReference("J4"), b.FindFootprintByReference("J5")
mm = pcbnew.ToMM
dx, dy = mm(j5.GetPosition().x - j4.GetPosition().x), mm(j5.GetPosition().y - j4.GetPosition().y)
print("J4 at", mm(j4.GetPosition().x), mm(j4.GetPosition().y), "rot", j4.GetOrientationDegrees(), "| J5 offset", dx, dy, "rot", j5.GetOrientationDegrees())
assert abs(dx - 15.24) < 0.01 and abs(dy) < 0.01 and j4.GetOrientationDegrees() == 0 and j5.GetOrientationDegrees() == 0
Z = 8.5 + 2.54                                                  # socket height + plastic body of the XIAO's pin header
HDR = "${KICAD10_3DMODEL_DIR}/Connector_PinHeader_2.54mm.3dshapes/PinHeader_1x07_P2.54mm_Vertical.step"
for fp in (j4, j5):
    ms = fp.Models()
    keep = [m for m in ms if "PinSocket" in m.m_Filename]
    ms.clear()
    for m in keep:
        ms.push_back(m)
    h = pcbnew.FP_3DMODEL()                                     # the XIAO's own pin header, plugged in upside down
    h.m_Filename = HDR
    h.m_Rotation = pcbnew.VECTOR3D(0, 180, 0)
    h.m_Offset = pcbnew.VECTOR3D(0, 0, Z)
    ms.push_back(h)
x = pcbnew.FP_3DMODEL()
x.m_Filename = "${KIPRJMOD}/3d/XIAO_ESP32C6.wrl"
x.m_Offset = pcbnew.VECTOR3D(7.62, -7.62, Z)
j4.Models().push_back(x)
print("J4 models:", [m.m_Filename.split("/")[-1] for m in j4.Models()], "| J5 models:", [m.m_Filename.split("/")[-1] for m in j5.Models()])
b.Save(board_path)
