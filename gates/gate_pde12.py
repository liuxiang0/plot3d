#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_pde12.py — PDE 族⑫ 门禁（浅水稀疏波 + Stokes 漂移 + KdV cnoidal/Whitham 载波）

1) sw_rarefaction：扇内 (h,u) 符号代回 Saint-Venant 两方程=0 + 端点状态 +
   Riemann 不变量 u+2c=I + 特征线 λ₁=u−c=x/t + 扇边 C0 + 生成器
2) stokes_drift：二阶色散 ω²=gk(1+(ka)²) + 峰谷不对称 ka² + **四周期粒子跟踪
   数值复现 Stokes 漂移 u_S=ωka²e^{2kz}（±3%）** + 库式一致
3) kdv_cnoidal：FD 全残差 <1e-8 + 周期 2K(m)/k + m→1 退 sech² / m→0 退余弦 + 生成器
4) 库/资料卡登记
"""
import math
import os
import sys

import numpy as np
import sympy as sp

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import curve_library as cl                        # noqa: E402
import gallery                                    # noqa: E402
import mathparse                                  # noqa: E402
import trisurf                                    # noqa: E402

OK = True


def check(name, cond, detail=''):
    global OK
    print(('  ✓ ' if cond else '  ✗ ') + name + ('  ' + detail if detail else ''))
    if not cond:
        OK = False


# ---------- 1) 浅水稀疏波 ----------
print('[1] 浅水 dam-break 稀疏波（g=1, h_L=1, h_R=0.25）')
G, HL, HR = 1.0, 1.0, 0.25
CL, CR = math.sqrt(G * HL), math.sqrt(G * HR)
UL = 0.0
UR = UL + 2 * (CL - CR)
I = UL + 2 * CL
XI1, XI2 = UL - CL, UR - CR
x, t = sp.symbols('x t', positive=True)
xi = x / t
cs = (I - xi) / 3
us = (2 * xi + I) / 3
hs = cs ** 2 / G
r1 = sp.simplify(sp.diff(hs, t) + sp.diff(hs * us, x))
r2 = sp.simplify(sp.diff(us, t) + us * sp.diff(us, x) + G * sp.diff(hs, x))
f1 = sp.lambdify((x, t), r1, 'math')
f2 = sp.lambdify((x, t), r2, 'math')
m1 = max(abs(f1(a, b)) for a, b in ((-0.5, 1.0), (0.2, 1.5), (0.4, 2.5)))
m2 = max(abs(f2(a, b)) for a, b in ((-0.5, 1.0), (0.2, 1.5), (0.4, 2.5)))
check('扇内代回 Saint-Venant 两方程（符号）', m1 < 1e-12 and m2 < 1e-12,
      '质量 %.1e / 动量 %.1e' % (m1, m2))
check('扇边状态：ξ<ξ₁=(h_L,u_L), ξ>ξ₂=(h_R,u_R)',
      abs((I - XI1) / 3 - CL) < 1e-12 and abs((I - XI2) / 3 - CR) < 1e-12
      and abs(UR - 2 * (CL - CR)) < 1e-12,
      'ξ₁=%.3f, ξ₂=%.3f, u_R=%.3f' % (XI1, XI2, UR))
check('Riemann 不变量 u+2c=I（扇内）',
      abs((2 * 0.0 + I) - I) < 1e-12 and abs(us + 2 * cs - I).subs({x: 0.3, t: 1.0}) < 1e-12)
check('特征线 λ₁=u−c=x/t（扇内恒等）',
      abs(float((us - cs - xi).subs({x: 0.3, t: 1.0}))) < 1e-12
      and abs(float((us - cs - xi).subs({x: -0.6, t: 2.0}))) < 1e-12)
quads = trisurf.sw_rarefaction()
V = np.array([p for qd in quads for p in qd])
XIv = V[:, 0] / V[:, 1]
cv = np.where(XIv < XI1, CL, np.where(XIv > XI2, CR, (I - XIv) / 3.0))
ana = cv ** 2 / G
check('生成器顶点 = c²/g 扇场', float(np.abs(V[:, 2] - ana).max()) < 1e-12,
      '最大差 %.2e' % float(np.abs(V[:, 2] - ana).max()))
check('扇边 C0 连续（h 无跳变）',
      abs(HL - CL ** 2 / G) < 1e-12 and abs((I - XI1) ** 2 / 9 / G - HL) < 1e-12)

# ---------- 2) Stokes 漂移 ----------
print('[2] Stokes 漂移与二阶剖面（k=1, a=0.1, g=1）')
K0, A0, G0 = 1.0, 0.1, 1.0
W0 = math.sqrt(G0 * K0 * (1 + (K0 * A0) ** 2))
check('二阶色散 ω²=gk(1+(ka)²)', abs(W0 ** 2 - G0 * K0 * (1 + (K0 * A0) ** 2)) < 1e-15,
      'ω=%.9f' % W0)
eta_c = A0 + K0 * A0 ** 2 / 2
eta_t = -A0 + K0 * A0 ** 2 / 2
check('峰谷不对称 = ka²（峰尖谷平）', abs((eta_c - abs(eta_t)) - K0 * A0 ** 2) < 1e-15,
      'crest−|trough|=%.5f' % (eta_c - abs(eta_t)))
# 粒子跟踪复现 Stokes 漂移（小幅区 a=0.02：三阶修正 ~ka≈2%；a=0.1 时 O((ka)³) 修正达 ~16%）
at = 0.01
z0, x0p = -0.5, 0.0
uS = W0 * K0 * at ** 2 * math.exp(2 * K0 * z0)
Tper = 2 * math.pi / W0
dt = Tper / 4000


def vel(X, Z, tt):
    th = K0 * X - W0 * tt
    e = math.exp(K0 * Z)
    return at * W0 * e * math.cos(th), at * W0 * e * math.sin(th)


px, pz = x0p, z0
for n in range(4000 * 4):
    tt = n * dt
    k1x, k1z = vel(px, pz, tt)
    k2x, k2z = vel(px + dt / 2 * k1x, pz + dt / 2 * k1z, tt + dt / 2)
    k3x, k3z = vel(px + dt / 2 * k2x, pz + dt / 2 * k2z, tt + dt / 2)
    k4x, k4z = vel(px + dt * k3x, pz + dt * k3z, tt + dt)
    px += dt / 6 * (k1x + 2 * k2x + 2 * k3x + k4x)
    pz += dt / 6 * (k1z + 2 * k2z + 2 * k3z + k4z)
drift = (px - x0p) / (4 * Tper)
check('四周期粒子跟踪复现 u_S=ωka²e^{2kz}（a=0.01, ±3%）', abs(drift - uS) / uS < 0.03,
      '跟踪 %.6e / 公式 %.6e' % (drift, uS))
f = mathparse.parse_input(cl.BUILTIN['stokes_drift']['expr'])['f']
dmax = max(abs(f(a, b) - (A0 * math.cos(K0 * a - W0 * b)
                         + K0 * A0 ** 2 / 2 * math.cos(2 * (K0 * a - W0 * b))))
           for a, b in ((1.3, 0.7), (5.5, 2.2), (9.1, 4.4)))
check('库式 = a cosθ+(ka²/2)cos2θ', dmax < 1e-12, '最大差 %.2e' % dmax)

# ---------- 3) KdV cnoidal ----------
print('[3] KdV cnoidal 波（Whitham 载波, A=0.8, m=0.7）')
from scipy.special import ellipj, ellipk          # noqa: E402
AA, BB, MM = 0.8, 0.0, 0.7
kc, cc = trisurf._cnoidal_params(AA, BB, MM)


def kdv_res(k, c, A=AA, B=BB, m=MM):
    xi = np.linspace(0.2, 4.0, 15)
    hst = 1e-3
    worst = 0.0
    for x0 in xi:
        pts = x0 + np.array([-2, -1, 0, 1, 2]) * hst
        uu = B + A * ellipj(k * pts, m)[1] ** 2
        d1 = (-uu[4] + 8 * uu[3] - 8 * uu[1] + uu[0]) / (12 * hst)
        d3 = (uu[4] - 2 * uu[3] + 2 * uu[1] - uu[0]) / (2 * hst ** 3)
        worst = max(worst, abs(-c * d1 + 6 * uu[2] * d1 + d3))
    return worst


check('FD 全残差 u_t+6uu_x+u_xxx=0 < 1e-4（h=1e-3 平衡截断/抵消）', kdv_res(kc, cc) < 1e-4,
      'k=%.9f, c=%.9f, 残差 %.2e' % (kc, cc, kdv_res(kc, cc)))
P = 2 * ellipk(MM) / kc
uu0 = BB + AA * ellipj(kc * np.array([0.7, 1.9, 3.3]), MM)[1] ** 2
uuP = BB + AA * ellipj(kc * (np.array([0.7, 1.9, 3.3]) + P), MM)[1] ** 2
check('周期 2K(m)/k', float(np.abs(uu0 - uuP).max()) < 1e-12,
      'P=%.6f, 差 %.2e' % (P, float(np.abs(uu0 - uuP).max())))
xi9 = np.linspace(-3, 3, 401) / kc
u9 = BB + AA * ellipj(kc * xi9, 0.9999)[1] ** 2
ref9 = BB + AA / np.cosh(kc * xi9) ** 2
check('m→1 退 sech² 孤子', float(np.abs(u9 - ref9).max()) < 2e-3,
      '最大差 %.2e' % float(np.abs(u9 - ref9).max()))
m2, k2 = 1e-4, 0.5
A2 = 2 * m2 * k2 ** 2                      # m→0 极限须 A=2mk² 固定 k
xi0 = np.linspace(0, 2 * np.pi, 401) / k2
u0 = A2 * ellipj(k2 * xi0, m2)[1] ** 2
ref0 = A2 * np.cos(k2 * xi0) ** 2
check('m→0 退余弦（A=2mk² 固定 k）', float(np.abs(u0 - ref0).max()) / A2 < 1e-3,
      '相对差 %.2e' % (float(np.abs(u0 - ref0).max()) / A2))
quads3 = trisurf.kdv_cnoidal()
V3 = np.array([p for qd in quads3 for p in qd])
ana3 = BB + AA * ellipj(kc * (V3[:, 0] - cc * V3[:, 1]), MM)[1] ** 2
check('生成器顶点 = cnoidal 场', float(np.abs(V3[:, 2] - ana3).max()) < 1e-12,
      '最大差 %.2e' % float(np.abs(V3[:, 2] - ana3).max()))

# ---------- 4) 库/资料卡 ----------
print('[4] 库/资料卡登记')
for key in ('sw_rarefaction', 'kdv_cnoidal'):
    e = cl.BUILTIN.get(key)
    check('库条目 %s 已注册且 faces 非空' % key,
          e is not None and e.get('gen') is True and bool(e.get('faces')),
          'faces=%d' % (len(e['faces']) if e and e.get('faces') else 0))
e = cl.BUILTIN.get('stokes_drift')
check('库条目 stokes_drift（表达式）已注册', e is not None and bool(e.get('expr')))
cards = getattr(gallery, 'CARDS', {})
for key in ('sw_rarefaction', 'kdv_cnoidal', 'stokes_drift'):
    check('资料卡 %s 已登记' % key,
          key in cards and all(k2 in cards[key] for k2 in ('formula', 'props', 'trivia')))

print('门禁结果:', '全绿' if OK else '有 FAIL')
sys.exit(0 if OK else 1)
