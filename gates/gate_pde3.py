#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_pde3.py — PDE 族③ 门禁: kdv_2soliton / ch_peakon / gray_scott

1) KdV 双孤子: u_t+6uu_x+u_xxx=0 FD 残差 + t=-10 双峰振幅 0.5/0.18
2) CH 峰孤子: 峰顶=1 / 离峰 |u_x|=u / 指数衰减率 1 / 离峰 CH 残差
3) Gray-Scott: 匀态 (1,0) 不动点 + 斑图统计 (std/max/覆盖率)
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'plot3d'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import mathparse                                  # noqa: E402
import curve_library as cl                        # noqa: E402

OK = True


def check(name, cond, detail=''):
    global OK
    print(('  ✓ ' if cond else '  ✗ ') + name + ('  ' + detail if detail else ''))
    if not cond:
        OK = False


def f_of(key):
    spec = mathparse.parse_input(cl.BUILTIN[key]['expr'])
    return spec['f']


# ---------- 1) KdV 双孤子 ----------
print('[1] KdV 双孤子 (Hirota τ)')
f = f_of('kdv_2soliton')
import sympy as sp                                 # 符号残差: 绕开 FD 截断误差
xs_, ts_ = sp.symbols('x t')
k1, k2 = sp.Integer(2), sp.Rational(6, 5)
A12 = ((k1 - k2) / (k1 + k2)) ** 2
e1 = sp.exp(k1 * (xs_ - k1 ** 2 * ts_))
e2 = sp.exp(k2 * (xs_ - k2 ** 2 * ts_))
tau = 1 + e1 + e2 + A12 * e1 * e2
u_sym = 2 * sp.diff(sp.log(tau), xs_, 2)
res_sym = (sp.diff(u_sym, ts_) + 6 * u_sym * sp.diff(u_sym, xs_)
           + sp.diff(u_sym, xs_, 3))
fu = sp.lambdify((xs_, ts_), u_sym, 'math')
fr = sp.lambdify((xs_, ts_), res_sym, 'math')
pts = [(0.3, -1.2), (2.0, 0.5), (-3.0, 2.0), (0.0, 0.0), (5.0, -2.0), (-7.0, 1.5)]
rmax = max(abs(fr(a, b)) for a, b in pts)
check('符号残差 max|u_t+6uu_x+u_xxx| < 1e-8', rmax < 1e-8, '实测 %.2e' % rmax)
dmax = max(abs(f(a, b) - fu(a, b)) for a, b in pts)
check('库表达式与 τ 式一致 < 1e-9', dmax < 1e-9, '实测 %.2e' % dmax)
h = 0.05
xs = np.arange(-10, 10 + h, h)
prof = np.array([f(x, -2.5) for x in xs])           # t = -2.5
i_fast = np.argmax(prof)
check('t=-2.5 快孤子振幅 ≈2', abs(prof[i_fast] - 2.0) < 0.03, '实测 %.4f' % prof[i_fast])
# 慢孤子峰: 在快孤子位置挖掉后再取最大
mask = np.abs(xs - xs[i_fast]) > 3
check('t=-2.5 慢孤子振幅 ≈0.72', abs(prof[mask].max() - 0.72) < 0.02,
      '实测 %.4f' % prof[mask].max())

# ---------- 2) CH 峰孤子 ----------
print('[2] Camassa-Holm 峰孤子')
g = f_of('ch_peakon')
check('峰顶 u(t,t)=1', max(abs(g(t, t) - 1) for t in (-3, 0, 2.5)) < 1e-12)
hh = 0.02
worst = 0.0
for xi in np.arange(0.35, 6, 0.25):
    for s in (1, -1):
        x = s * xi
        u = g(x, 0.0)
        ux = (g(x + hh, 0.0) - g(x - hh, 0.0)) / (2 * hh)
        worst = max(worst, abs(abs(ux) - u))
check('离峰恒等式 |u_x|=u (ξ>0.35)', worst < 2e-3, '实测 %.2e' % worst)
r1, r2 = g(1.0, 0.0), g(2.0, 0.0)
check('指数衰减率 = 1', abs((math.log(r2) - math.log(r1)) + 1) < 1e-12)
H = 0.05
worst_ch = 0.0
for xi in np.arange(0.5, 6, 0.5):
    for s in (1, -1):
        x = s * xi
        t = 0.0
        u = g(x, t)
        u_t = (g(x, t + H) - g(x, t - H)) / (2 * H)
        u_x = (g(x + H, t) - g(x - H, t)) / (2 * H)
        u_xx = (g(x + H, t) - 2 * u + g(x - H, t)) / H ** 2
        u_xxx = (g(x + 2 * H, t) - 2 * g(x + H, t) + 2 * g(x - H, t) - g(x - 2 * H, t)) / (2 * H ** 3)
        u_xx_t = (g(x + H, t + H) - 2 * g(x, t + H) + g(x - H, t + H)
                  - g(x + H, t - H) + 2 * g(x, t - H) - g(x - H, t - H)) / (2 * H ** 3)
        ch = u_t - u_xx_t + 3 * u * u_x - 2 * u_x * u_xx - u * u_xxx
        worst_ch = max(worst_ch, abs(ch))
check('离峰 CH 残差 < 5e-3', worst_ch < 5e-3, '实测 %.2e' % worst_ch)

# ---------- 3) Gray-Scott ----------
print('[3] Gray-Scott 反应扩散')
Du, Dv, F, k = 0.16, 0.08, 0.035, 0.065
m = 64
U0 = np.ones((m, m)); V0 = np.zeros((m, m))
for _ in range(100):
    Lu = np.roll(U0, 1, 0) + np.roll(U0, -1, 0) + np.roll(U0, 1, 1) + np.roll(U0, -1, 1) - 4 * U0
    Lv = np.roll(V0, 1, 0) + np.roll(V0, -1, 0) + np.roll(V0, 1, 1) + np.roll(V0, -1, 1) - 4 * V0
    uvv = U0 * V0 * V0
    U0 = U0 + Du * Lu - uvv + F * (1 - U0)
    V0 = V0 + Dv * Lv + uvv - (F + k) * V0
check('匀态 (1,0) 为不动点', abs(U0 - 1).max() < 1e-12 and abs(V0).max() < 1e-12)
import trisurf                                    # noqa: E402
trisurf.build(cl._GEN_SPECS['gray_scott'])        # 与条目同参构建, 确保缓存存在
V = np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'cache_grayscott.npy'))
check('斑图非平凡 std(V)>0.05', V.std() > 0.05, '实测 %.3f' % V.std())
check('V 有界 0≤V≤0.5', V.min() >= -1e-9 and V.max() <= 0.5,
      '实测 [%.3f, %.3f]' % (V.min(), V.max()))
cov = float((V > 0.1).mean())
check('spots 覆盖率 5%–70%', 0.05 < cov < 0.70, '实测 %.2f' % cov)

print('门禁结果:', '全绿' if OK else '有 FAIL')
sys.exit(0 if OK else 1)
