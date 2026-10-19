import json, sys
from collections import Counter
d = json.load(open(sys.argv[1], encoding='utf8'))
for k in ('violations', 'unconnected_items', 'schematic_parity'):
    v = d.get(k, [])
    print(k, len(v))
    for (t, sev), c in Counter((x['type'], x['severity']) for x in v).items():
        print('   ', c, sev, t)
    for x in v[:int(sys.argv[2]) if len(sys.argv) > 2 else 10]:
        print('     -', x['type'], '|', x['description'][:100], '|', [(i.get('description', '')[:70], i.get('pos')) for i in x.get('items', [])][:2])
