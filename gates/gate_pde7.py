#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_pde7.py — PDE 族⑦ 门禁（Love 波：低速层覆盖半空间的 SH 面波）

love_wave 检查：
1) 频散方程 μ₁κ₁tan(κ₁H)=μ₂κ₂ 二分精解：残差、β₁<c<β₂、基模 κ₁H∈(0,π/2)
2) 符号 PDE：SH 波方程 ρu_tt=μ(u_xx+u_zz) 在层内/半空间分别代回（ω 两区一致）
3) 深度本征函数 ODE + 边界条件：v'(0)=0（应力自由面）、v 连续、μv' 连续（斜率跳变=μ₂/μ₁）
4) 半空间衰逝 v(H+d)/v(H)=e^{−κ₂d}
5) 正常频散：dc/d(kH)<0 且群速度 U_g=c+k·dc/dk < c
6) 生成器顶点=解析场、bbox、库/资料卡登记
"""
import math
import os
import sys

import numpy as np
import sympy as sp

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import curve_library as cl                        # noqa: E402
import gallery                                    # noqa: E402
import trisurf                                    # noqa: E402

OK = True

# 介质参数（与 trisurf.love 默认一致）
H, B1, B2, MU1, MU2, KH = 1.0, 1.0, 1.4, 1.0, 2.0, 4.0
K = KH / H


def check(name, cond, detail=''):
    global OK
    print(('  ✓ ' if cond else '  ✗ ') + name + ('  ' + detail if detail else ''))
    if not cond:
        OK = False


def kappa(c):
    k1 = math.sqrt(max((c * K / B1) ** 2 - K * K, 0.0))
    k2 = math.sqrt(max(K * K - (c * K / B2) ** 2, 0.0))
    return k1, k2


def disp(c):
    k1, k2 = kappa(c)
    return MU1 * k1 * math.tan(k1 * H) - MU2 * k2


def solve_c(kh):
    """基模相速度：κ₁H∈(0,π/2) 支上二分"""
    kk = kh / H
    lo = B1 * (1.0 + 1e-12)
    hi = B1 * math.sqrt(1.0 + (math.pi / (2.0 * kh)) ** 2) * (1.0 - 1e-12)
    f = lambda c: MU1 * math.sqrt(max((c * kk / B1) ** 2 - kk * kk, 0.0)) \
        * math.tan(math.sqrt(max((c * kk / B1) ** 2 - kk * kk, 0.0)) * H) \
        - MU2 * math.sqrt(max(kk * kk - (c * kk / B2) ** 2, 0.0))
    for _ in range(90):
        mid = 0.5 * (lo + hi)
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


# ---------- 1) 频散方程精解 ----------
print('[1] Love 频散方程 μ₁κ₁tan(κ₁H)=μ₂κ₂（基模）')
C = solve_c(KH)
K1, K2 = kappa(C)
check('二分残差 < 1e-12', abs(disp(C)) < 1e-12, '实测 %.2e' % abs(disp(C)))
check('相速度夹在 β₁<c<β₂', B1 < C < B2, 'c=%.9f ∈ (%.1f, %.1f)' % (C, B1, B2))
check('基模 κ₁H∈(0,π/2) 且 κ₂H>0（层内振荡/半空间衰逝）',
      0 < K1 * H < math.pi / 2 and K2 * H > 0,
      'κ₁H=%.6f, κ₂H=%.6f' % (K1 * H, K2 * H))
W = B1 * math.sqrt(K1 ** 2 + K * K)
check('ω 两区一致 ω²=β₁²(κ₁²+k²)=β₂²(k²−κ₂²)',
      abs(W ** 2 - B2 ** 2 * (K * K - K2 ** 2)) < 1e-9 * W ** 2,
      'ω=%.9f, 相对差 %.2e' % (W, abs(W ** 2 - B2 ** 2 * (K * K - K2 ** 2)) / W ** 2))

# ---------- 2) 符号 PDE：SH 波方程 ----------
print('[2] SH 波方程 ρu_tt = μ(u_xx+u_zz)（层内 / 半空间）')
x, z, t = sp.symbols('x z t', real=True)
u1 = sp.cos(K1 * z) * sp.cos(K * x - W * t)
u2 = sp.cos(K1 * H) * sp.exp(-K2 * (z - H)) * sp.cos(K * x - W * t)
rho1, rho2 = MU1 / B1 ** 2, MU2 / B2 ** 2
r1 = sp.simplify(rho1 * sp.diff(u1, t, 2) - MU1 * (sp.diff(u1, x, 2) + sp.diff(u1, z, 2)))
r2 = sp.simplify(rho2 * sp.diff(u2, t, 2) - MU2 * (sp.diff(u2, x, 2) + sp.diff(u2, z, 2)))
f1 = sp.lambdify((x, z, t), r1, 'math')
f2 = sp.lambdify((x, z, t), r2, 'math')
m1 = max(abs(f1(a, b, c)) for a, b, c in ((0.7, 0.3, 1.1), (2.9, 0.8, 0.4), (5.5, 0.5, 2.2)))
m2 = max(abs(f2(a, b, c)) for a, b, c in ((0.7, 1.6, 1.1), (2.9, 2.4, 0.4), (5.5, 1.2, 2.2)))
check('层内残差 < 1e-9', m1 < 1e-9, '实测 %.2e' % m1)
check('半空间残差 < 1e-9', m2 < 1e-9, '实测 %.2e' % m2)

# ---------- 3) 深度本征函数 ODE 与边界条件 ----------
print('[3] v(z) 的 ODE 与界面条件')


def vprof(zz):
    zz = np.asarray(zz, dtype=float)
    return np.where(zz <= H, np.cos(K1 * zz), np.cos(K1 * H) * np.exp(-K2 * (zz - H)))


def ode_res(n, zlo, zhi, ksq, sign):
    """FD 残差 max|v''±k²v|（sign=+1 层内 / −1 半空间）"""
    zz = np.linspace(zlo, zhi, n)
    h = zz[1] - zz[0]
    vv = vprof(zz)
    r = (vv[2:] - 2 * vv[1:-1] + vv[:-2]) / h ** 2 + sign * ksq * vv[1:-1]
    return float(np.abs(r).max())


l1, l2 = ode_res(201, 0.05, H - 0.05, K1 ** 2, +1), ode_res(401, 0.05, H - 0.05, K1 ** 2, +1)
h1, h2 = ode_res(201, H + 0.05, 2.5, K2 ** 2, -1), ode_res(401, H + 0.05, 2.5, K2 ** 2, -1)
check("层内 v''+κ₁²v=0（二阶收敛自证）", l2 < 1e-5 and 2.5 < l1 / l2 < 6.0,
      '粗 %.2e / 细 %.2e, 比 %.2f' % (l1, l2, l1 / l2))
check("半空间 v''−κ₂²v=0（二阶收敛自证）", h2 < 1e-4 and 2.5 < h1 / h2 < 6.0,
      '粗 %.2e / 细 %.2e, 比 %.2f' % (h1, h2, h1 / h2))
hh = 1e-4
d0 = (-3 * vprof(0.0) + 4 * vprof(hh) - vprof(2 * hh)) / (2 * hh)   # 二阶单侧差商
check("应力自由面 v'(0)=0", abs(d0) < 1e-7, '实测 %.2e' % abs(d0))
jump = abs(vprof(H - 1e-7) - vprof(H + 1e-7))
check('界面 v 连续', jump < 1e-6, '实测 %.2e' % jump)
sl_l = (vprof(H) - vprof(H - 1e-6)) / 1e-6
sl_r = (vprof(H + 1e-6) - vprof(H)) / 1e-6
ratio = sl_l / sl_r
check('剪应力连续 ⇒ 斜率跳变 v′(H⁻)/v′(H⁺)=μ₂/μ₁',
      abs(ratio - MU2 / MU1) < 1e-4, '实测 %.6f（期望 %.1f）' % (ratio, MU2 / MU1))

# ---------- 4) 半空间衰逝 ----------
print('[4] 半空间指数衰逝')
errs = []
for d in (0.3, 0.8, 1.5):
    errs.append(abs(vprof(H + d) / vprof(H) - math.exp(-K2 * d)))
check('v(H+d)/v(H)=e^{−κ₂d}', max(errs) < 1e-12, '最大偏差 %.2e' % max(errs))

# ---------- 5) 正常频散 ----------
print('[5] 正常频散（dc/dk<0, 群速度<相速度）')
cm, cp = solve_c(KH - 0.4), solve_c(KH + 0.4)
dcdk = (cp - cm) / (0.8 / H)
Ug = C + K * dcdk
check('相速度随 kH 单调减', cp < C < cm,
      'c(kH−0.4)=%.6f > c=%.6f > c(kH+0.4)=%.6f' % (cm, C, cp))
check('群速度 U_g=c+k·dc/dk < c（正常频散）', Ug < C, 'U_g=%.6f < c=%.6f' % (Ug, C))

# ---------- 6) 生成器与库登记 ----------
print('[6] 生成器 love + 库/资料卡登记')
quads = trisurf.love()
V = np.array([p for qd in quads for p in qd])
ana = vprof(V[:, 1]) * np.cos(K * V[:, 0])
check('生成器顶点 = 解析场 v(z)cos(kx)', float(np.abs(V[:, 2] - ana).max()) < 1e-12,
      '最大差 %.2e' % float(np.abs(V[:, 2] - ana).max()))
check('quads 充足且 bbox 与声明域一致', len(quads) > 15000
      and abs(V[:, 0].max() - 6.2832) < 1e-3 and abs(V[:, 1].max() - 3.0) < 1e-9
      and abs(V[:, 2].max() - 1.0) < 1e-9,
      'quads=%d, z∈[%.4f, %.4f]' % (len(quads), V[:, 2].min(), V[:, 2].max()))
e = cl.BUILTIN.get('love_wave')
check('库条目 love_wave 已注册且 faces 非空',
      e is not None and e.get('gen') is True and bool(e.get('faces')),
      'faces=%d' % (len(e['faces']) if e and e.get('faces') else 0))
check('faces_kind=heightfield 且分类正确',
      e is not None and e.get('faces_kind') == 'heightfield'
      and e.get('category') == '偏微分方程解')
cards = getattr(gallery, 'CARDS', {})
check('资料卡已登记（formula/props/trivia）',
      'love_wave' in cards
      and all(k in cards['love_wave'] for k in ('formula', 'props', 'trivia')))

print('门禁结果:', '全绿' if OK else '有 FAIL')
sys.exit(0 if OK else 1)
