#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_pde4.py — PDE 族④ 门禁（流体×3 + 热传导×1）

1) flow_cylinder : ∇²ψ=0（无旋不可压）/ 圆柱面 ψ=0 / 驻点 ∇ψ(±1,0)=0 / 生成器顶点=解析 ψ
2) stokes_first  : u_t=νu_yy 残差 / u(0,t)=1 / 相似变量 η=y/2√(νt) 坍缩
3) airy_dispersion: 各分量满足模态方程 c_tt=(g/k)c_xx / 库表达式=分量之和
4) heat_rod      : u_t=αu_xx 残差 / Dirichlet 端零 / 初值=Σbₙsin(nπx)
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import mathparse                                  # noqa: E402
import curve_library as cl                        # noqa: E402
import trisurf                                    # noqa: E402

OK = True


def check(name, cond, detail=''):
    global OK
    print(('  ✓ ' if cond else '  ✗ ') + name + ('  ' + detail if detail else ''))
    if not cond:
        OK = False


def f_of(key):
    return mathparse.parse_input(cl.BUILTIN[key]['expr'])['f']


# ---------- 1) 圆柱绕流势流 ----------
print('[1] 圆柱绕流势流 ψ=y(1−1/r²)')


def psi(x, y):
    r2 = x * x + y * y
    return y * (1 - 1 / r2) if r2 > 1e-12 else float('nan')


h = 0.025
worst_lap = 0.0
for x in np.arange(-2.4, 2.41, 0.1):
    for y in np.arange(-2.4, 2.41, 0.1):
        if math.hypot(x, y) < 1.2 + 2 * h:
            continue
        lap = (psi(x + h, y) + psi(x - h, y) + psi(x, y + h) + psi(x, y - h)
               - 4 * psi(x, y)) / h ** 2
        worst_lap = max(worst_lap, abs(lap))
check('∇²ψ=0 残差 (r>1.2) < 2e-2', worst_lap < 2e-2, '实测 %.2e' % worst_lap)
check('圆柱面 ψ=0 (r=1)', max(abs(psi(math.cos(t), math.sin(t)))
                          for t in np.linspace(0, 2 * math.pi, 37)) < 1e-12)


def dpsidx(x, y, hh=1e-5):
    return (psi(x + hh, y) - psi(x - hh, y)) / (2 * hh)


def dpsidy(x, y, hh=1e-5):
    return (psi(x, y + hh) - psi(x, y - hh)) / (2 * hh)


stag = max(max(abs(dpsidx(s, 0)), abs(dpsidy(s, 0))) for s in (1, -1))
check('驻点 ∇ψ(±1,0)=0', stag < 1e-6, '实测 %.2e' % stag)
quads = trisurf.flow_cyl(n=40)
vmin = min(min(math.hypot(p[0], p[1]) for p in q) for q in quads)
zerr = max(abs(q[i][2] - psi(q[i][0], q[i][1])) for q in quads for i in range(4))
check('生成器: 全部顶点 r≥1 且 z=ψ', vmin >= 1 - 1e-12 and zerr < 1e-12,
      'r_min=%.4f z_err=%.1e quads=%d' % (vmin, zerr, len(quads)))

# ---------- 2) Stokes 第一问题 ----------
print('[2] Stokes 第一问题 u=erfc(x/2√(0.2y))')
f = f_of('stokes_first')
nu = 0.2
hx, hy = 0.02, 0.01
worst = 0.0
for x in np.arange(0.5, 4.51, 0.25):
    for y in np.arange(0.3, 2.71, 0.3):
        u_t = (f(x, y + hy) - f(x, y - hy)) / (2 * hy)
        u_yy = (f(x + hx, y) - 2 * f(x, y) + f(x - hx, y)) / hx ** 2
        worst = max(worst, abs(u_t - nu * u_yy))
check('u_t=νu_yy 残差 < 2e-3', worst < 2e-3, '实测 %.2e' % worst)
check('板面 u(0,t)=1', max(abs(f(0.0, y) - 1) for y in (0.1, 1, 3)) < 1e-12)
sim = max(abs(f(x, y) - f(2 * x, 4 * y))
          for x, y in ((1.0, 0.5), (0.7, 1.3), (2.2, 0.9)))
check('相似性 u(x,y)=u(2x,4y)', sim < 1e-12, '实测 %.2e' % sim)

# ---------- 3) Airy 重力波色散 ----------
print('[3] Airy 重力波×2（ω²=gk）')
g = 9.81
w1, w2 = math.sqrt(g * 2), math.sqrt(g * 3)
f = f_of('airy_dispersion')


def c1(x, y):
    return math.cos(2 * x - w1 * y)


def c2(x, y):
    return math.cos(3 * x - w2 * y)


cons = max(abs(f(x, y) - (c1(x, y) + c2(x, y)))
           for x in (0.3, -1.7, 2.5) for y in (0.2, 1.1, 3.3))
check('库表达式=分量之和', cons < 1e-12, '实测 %.2e' % cons)
h = 0.005
for nm, comp, k in (('k=2', c1, 2.0), ('k=3', c2, 3.0)):
    worst = 0.0
    for x in (0.4, -2.1, 3.3):
        for y in (0.7, 2.2, 4.9):
            c_tt = (comp(x, y + h) - 2 * comp(x, y) + comp(x, y - h)) / h ** 2
            c_xx = (comp(x + h, y) - 2 * comp(x, y) + comp(x - h, y)) / h ** 2
            worst = max(worst, abs(c_tt - (g / k) * c_xx))
    check(f'模态方程 c_tt=(g/{k})c_xx 残差 < 3e-3 ({nm})', worst < 3e-3,
          '实测 %.2e' % worst)

# ---------- 4) 有限杆热传导 ----------
print('[4] 有限杆热传导 u_t=αu_xx')
f = f_of('heat_rod')
alpha = 0.05
hx, ht = 0.005, 0.01
worst = 0.0
for x in np.arange(0.05, 0.951, 0.15):
    for y in np.arange(0.2, 2.81, 0.6):
        u_t = (f(x, y + ht) - f(x, y - ht)) / (2 * ht)
        u_xx = (f(x + hx, y) - 2 * f(x, y) + f(x - hx, y)) / hx ** 2
        worst = max(worst, abs(u_t - alpha * u_xx))
check('u_t=αu_xx 残差 < 1e-3', worst < 1e-3, '实测 %.2e' % worst)
bnd = max(max(abs(f(0.0, y)), abs(f(1.0, y))) for y in (0.5, 1.5, 3.0))
check('Dirichlet 端零 u(0,t)=u(1,t)=0', bnd < 1e-12, '实测 %.2e' % bnd)
init = max(abs(f(x, 0.0) - (math.sin(math.pi * x) + 0.5 * math.sin(2 * math.pi * x)
                            + 0.333 * math.sin(3 * math.pi * x)))
           for x in (0.13, 0.37, 0.61, 0.88))
check('初值=Σbₙsin(nπx)', init < 1e-12, '实测 %.2e' % init)

print('门禁结果:', '全绿' if OK else '有 FAIL')
sys.exit(0 if OK else 1)
