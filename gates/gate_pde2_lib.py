import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'web'))
import curve_library, geometry

grouped, warns = curve_library.load_all()
print("load_all 警告:", warns if warns else "0 ✓")

NEW = {
 'burgers_shock':      ([-4, 0, -0.01], [4, 6, 1.01]),
 'schrodinger_packet': ([-4, 0, -1.05], [12, 3, 1.05]),
 'maxwell_fdtd':       ([-3, -3, -1.21], [3, 3, 1.21]),
}
index = {}
for cat, entries in grouped:
    for e in entries:
        index[e['key']] = e

ok = fail = 0
for key, (lo, hi) in NEW.items():
    e = index.get(key)
    if e is None:
        print(f"✗ {key} 未入库"); fail += 1; continue
    g = geometry.sample(e['expr'], e['category'], e.get('faces'))
    bb = g['bbox']
    good = all(bb[i] >= lo[i] - 0.05 and bb[3 + i] <= hi[i] + 0.05 for i in range(3))
    nv = len(g['vertices']) // 3 if g['type'] == 'mesh' else sum(len(L)//3 for L in g['lines'])
    nf = len(g['faces']) // 3 if g['type'] == 'mesh' else 0
    print(("✓" if good else "✗"), key, "| kind:", g.get('kind'),
          "| bbox:", [round(v, 3) for v in bb], "| 顶点:", nv, "| 面片:", nf)
    ok += good; fail += (not good)

print("BUILTIN 总数:", len(curve_library.BUILTIN))
print(f"== 几何门禁: {ok} ✓ / {fail} ✗ ; load_all 警告 {len(warns)} ==")
sys.exit(1 if fail or warns else 0)
