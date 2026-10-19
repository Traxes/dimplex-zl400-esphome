s = open('build_pcb.py', encoding='utf8').read()
head = s[:s.index("YC = 28.0")]
head = head.replace("VentilationBoard\\ESP24V_Ventilation_LAB\"", "VentilationBoard\\ESP24V_HA_Board_XIAO\"")
head = head.replace("ESP24V_Ventilation_LAB.kicad", "ESP24V_HA_XIAO.kicad")
head = head.replace("W, H = 68.0, 56.0", "W, H = 75.0, 64.0")
head = head.replace("def place(ref, x, y, rot=0, hide_ref=False):", "def place(ref, x, y, rot=0, hide_ref=True):")
assert "ESP24V_HA_Board_XIAO" in head and "75.0" in head
open('build_xiao_pcb.py', 'w', encoding='utf8').write(head + open('xiao_body.py', encoding='utf8').read())
print("written")
