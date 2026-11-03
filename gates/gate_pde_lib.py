#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新增 PDE 条目解析+几何门禁：load_all 0 警告 + sample() mesh/lines 与 bbox 对账"""
import sys
sys.path.insert(0, '/home/kumath/.openclaw/workspace/plot3d')
sys.path.insert(0, '/home/kumath/.openclaw/workspace/plot3d/web')
import curve_library, geometry

grouped, warns = curve_library.load_all()
print("load_all 警告:", warns if warns else "0 ✓")

NEW = {  # key: (bbox 下界, bbox 上界)（容差 0.05）
 'heat_kernel':   ([-4, 0.12, -0.01], [4, 2, 0.87]),
 'kdv_soliton':   ([-10, 0, -0.01], [10, 4, 2.05]),
 'sg_breather':   ([-8, 0, -3.72], [8, 10.47, 3.72]),
 'membrane_rect': ([0, 0, -1.01], [1, 1, 1.01]),
 'qho_eigen':     ([-3, -3, -4.65], [3, 3, 5.35]),
 'drum_bessel':   ([-1.01, -1.01, -0.01], [1.01, 1.01, 1.01]),
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
          "| bbox:", [round(v, 3) for v in bb], "| 顶点/线点:", nv, "| 面片:", nf)
    ok += good; fail += (not good)

cat_names = [c for c, _ in grouped]
print("分类含『偏微分方程解』:", '偏微分方程解' in cat_names)
print(f"== 几何门禁: {ok} ✓ / {fail} ✗ ; load_all 警告 {len(warns)} ==")
sys.exit(1 if fail or warns else 0)
