import csv, re, sys, os, zipfile, subprocess
folder, prefix, board = sys.argv[1], sys.argv[2], sys.argv[3]
smd = lambda d: re.match(r'^[RDUQ][0-9]+$', d)
b = os.path.join(folder, f'BOM-{prefix}.csv'); c = os.path.join(folder, f'CPL-{prefix}.csv')
rows = list(csv.reader(open(b, encoding='utf8')))
out = [rows[0]] + [r for r in rows[1:] if r[3] and all(smd(x) for x in r[1].split(','))]
csv.writer(open(b, 'w', encoding='utf8', newline='')).writerows(out)
rows = list(csv.reader(open(c, encoding='utf8')))
# JLCPCB's SOT-23 reel orientation is 180 degrees from KiCad's footprint (verified in JLCPCB's placement preview)
for r in rows[1:]:
    if re.match(r'^Q[0-9]+$', r[0]):
        r[4] = '%.6f' % ((float(r[4]) + 180) % 360)
csv.writer(open(c, 'w', encoding='utf8', newline='')).writerows([rows[0]] + [r for r in rows[1:] if smd(r[0])])
g = os.path.join(folder, 'gerbers')
subprocess.run([r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe", "pcb", "export", "gerbers", "--layers", "F.Paste,B.Paste", "--no-x2", "--no-netlist", "-o", g + os.sep, board], capture_output=True)
z = zipfile.ZipFile(os.path.join(folder, 'gerbers.zip'), 'w', zipfile.ZIP_DEFLATED)
for f in sorted(os.listdir(g)):
    if not f.endswith('.gbrjob'):
        z.write(os.path.join(g, f), f)
z.close()
print('post-processed', folder, [f for f in os.listdir(g) if 'Paste' in f])
