import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'web'))
import importlib.util
import math
import numpy as np
import curve_library as cl
import export3d
import simplify

spec = importlib.util.spec_from_file_location('geom', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'web', 'geometry.py'))
geom = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geom)

# 1) 真实 MC 网格: Kummer 16 节点四次曲面
e = cl.BUILTIN['kummer']
g = geom.sample(e['expr'], e['category'])
verts = [tuple(g['vertices'][i:i+3]) for i in range(0, len(g['vertices']), 3)]
faces = [tuple(g['faces'][i:i+3]) for i in range(0, len(g['faces']), 3)]
tris = [(verts[a], verts[b], verts[c]) for a, b, c in faces]
print('Kummer MC 原始三角形:', len(tris))

out = simplify.decimate_tris(tris, 3000)
print('抽稀后:', len(out))
assert len(out) <= 3000

# 质量门禁: 抽稀顶点到零集的一阶距离 |F|/|∇F|
F = geom.mathparse.parse_input(e['expr'])['F']
def dist(p):
    v = F(*p)
    h = 1e-5
    gx = (F(p[0]+h, p[1], p[2]) - F(p[0]-h, p[1], p[2])) / (2*h)
    gy = (F(p[0], p[1]+h, p[2]) - F(p[0], p[1]-h, p[2])) / (2*h)
    gz = (F(p[0], p[1], p[2]+h) - F(p[0], p[1], p[2]-h)) / (2*h)
    gn = math.sqrt(gx*gx + gy*gy + gz*gz) or 1.0
    return abs(v) / gn
vs = {p for t in out for p in t}
dmax = max(dist(p) for p in vs)
print('抽稀顶点到零集距离上限: %.4f' % dmax)
assert dmax < 0.15, '简化偏离零集过远'

# 2) 导出冒烟: OBJ/STL 带 target_tris
n1 = export3d.export_obj([[(t, '#89b4fa') for t in tris]], '/tmp/dec_test.obj', 'kummer', target_tris=2000)
n2 = export3d.export_stl([[(t, '#89b4fa') for t in tris]], '/tmp/dec_test.stl', 'kummer', target_tris=2000)
n3 = export3d.export_obj([[(t, '#89b4fa') for t in tris]], '/tmp/dec_full.obj', 'kummer')
print('export_obj 简化:', n1, '| export_stl 简化:', n2, '| 不简化:', n3)
assert n1 <= 2000 and n2 <= 2000 and n3 == len(tris)
print('✓ MC 网格抽稀 + 导出管线验证通过')
