#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_pde5.py — PDE 族⑤ 门禁（弹性波×2 + 空气动力学×2）

1) rayleigh_wave : 自由面零牵引(σ_zz=σ_xz=0, c_R 由 Rayleigh 方程二分精解) + 库式一致 + 深度局域
2) beam_flexural : 符号残差 η_tt+η_xxxx=0（ω=k² 色散）+ 库式一致
3) blasius_bl    : 打靶 f''(0)=0.4696 → f'(∞)=1 + 敏感性 + 缓存一致 + 单调 + 高度场范围
4) mach_lines    : 符号残差 (1−M²)φ_xx+φ_yy=0 + 库式一致 + Mach 角恒等 sinμ=1/M
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


# ---------- 1) Rayleigh 面波 ----------
print('[1] Rayleigh 面波（弹性半空间, ν=0.25）')


def rayleigh_R(c):
    return (2 - c * c) ** 2 - 4 * math.sqrt(1 - c * c / 3) * math.sqrt(1 - c * c)


lo, hi = 0.80, 0.99
for _ in range(80):
    mid = (lo + hi) / 2
    if rayleigh_R(lo) * rayleigh_R(mid) <= 0:
        hi = mid
    else:
        lo = mid
cR = (lo + hi) / 2
q, s, k, A = math.sqrt(1 - cR ** 2 / 3), math.sqrt(1 - cR ** 2), 1.0, 1.0
B = 2 * A * q * k / (s * s + k * k)
lam, mu = 1.0, 1.0                                # ρ=1, β=1, α=√3
sig = []
for x in np.arange(0, 2 * math.pi, 0.25):
    co, si = math.cos(x), math.sin(x)
    ux = k * (-A * k + s * B) * co
    uz = (A * q * k - s * s * B) * si             # z=0
    wx = (A * q * k - B * k * k) * si
    wz = (A * q * q - B * k * s) * co
    e = ux + wz
    sig.append((abs(lam * e + 2 * mu * wz), abs(mu * (uz + wx))))
szz, sxz = max(a for a, _ in sig), max(b for _, b in sig)
check('c_R 解 Rayleigh 方程 ≈0.9194', abs(cR - 0.919402) < 1e-5, 'c_R=%.6f' % cR)
check('自由面 σ_zz=0', szz < 1e-8, '实测 %.2e' % szz)
check('自由面 σ_xz=0', sxz < 1e-8, '实测 %.2e' % sxz)
f = f_of('rayleigh_wave')
w0 = lambda y: (-A * q * math.exp(-q * y) + B * k * math.exp(-s * y))
dmax = max(abs(f(x, y) - w0(y) * math.cos(x))
           for x in (0.3, 1.0, 3.7) for y in (0.0, 1.0, 2.5))
check('库式与精确 w 一致 < 1e-4', dmax < 1e-4, '实测 %.2e' % dmax)
trap = abs(w0(3.0)) / abs(w0(0.0))
check('深度局域 w(3)/w(0) < 0.75', trap < 0.75, '实测 %.3f' % trap)

# ---------- 2) Euler-Bernoulli 梁弯曲波 ----------
print('[2] 梁弯曲波 η_tt+η_xxxx=0（ω=k²）')
import sympy as sp
X, Y = sp.symbols('x y')
eta = sp.cos(2 * X - 4 * Y) + sp.cos(3 * X - 9 * Y)
res_b = sp.diff(eta, Y, 2) + sp.diff(eta, X, 4)
fb = sp.lambdify((X, Y), res_b, 'math')
rmax = max(abs(fb(a, b)) for a, b in ((0.3, 0.7), (-2.1, 1.9), (4.4, 3.3)))
check('符号残差 η_tt+η_xxxx = 0', rmax < 1e-10, '实测 %.2e' % rmax)
f = f_of('beam_flexural')
dmax = max(abs(f(a, b) - float(eta.subs({X: a, Y: b})))
           for a, b in ((0.3, 0.7), (-2.1, 1.9), (4.4, 3.3)))
check('库式与符号式一致', dmax < 1e-12, '实测 %.2e' % dmax)

# ---------- 3) Blasius 边界层 ----------
print('[3] Blasius 层流边界层')
from scipy.integrate import solve_ivp


def shoot(s0):
    def rhs(e, w):
        ff, fp, fpp = w
        return [fp, fpp, -0.5 * ff * fpp]
    return solve_ivp(rhs, [0, 8], [0, 0, s0], dense_output=True,
                   rtol=1e-10, atol=1e-12, max_step=0.01)


sol = shoot(0.33206)
fp8 = float(sol.sol(8)[1])
check("打靶 f''(0)=0.33206 → f'(8)≈1", abs(fp8 - 1) < 2e-3, "f'(8)=%.5f" % fp8)
fp8p = float(shoot(0.33306).sol(8)[1])
check('打靶敏感性（+1e-3 偏移 > 1e-3）', abs(fp8p - fp8) > 1e-3,
      'Δ=%.2e' % abs(fp8p - fp8))
eta_c, fp_c = np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   '..', 'cache_blasius.npy'))
dmax = float(np.max(np.abs(fp_c - sol.sol(eta_c)[1])))
check('缓存剖面与重积分一致 < 1e-9', dmax < 1e-9, '实测 %.2e' % dmax)
check("f' 单调且 f'(0)=0", bool(np.all(np.diff(fp_c) >= -1e-12)) and abs(fp_c[0]) < 1e-12)
quads = trisurf.blasius()
zs = [p[2] for qd in quads for p in qd]
check('高度场 z∈[0,1]（渐近容差 2e-3）', min(zs) >= -1e-12 and max(zs) <= 1 + 2e-3,
      '[%.6f, %.6f]' % (min(zs), max(zs)))

# ---------- 4) 超音速小扰动 Mach 线 ----------
print('[4] 超音速小扰动 (M=1.2)')
M, beta = 1.2, math.sqrt(1.44 - 1)
phi = sp.cos(2 * (X - beta * Y)) + sp.Rational(6, 10) * sp.cos(3 * (X + beta * Y))
res_m = (1 - sp.Rational(144, 100)) * sp.diff(phi, X, 2) + sp.diff(phi, Y, 2)
fm = sp.lambdify((X, Y), sp.simplify(res_m), 'math')
rmax = max(abs(fm(a, b)) for a, b in ((0.3, 0.7), (-2.1, 1.9), (4.4, 3.3)))
check('符号残差 (1−M²)φ_xx+φ_yy = 0', rmax < 1e-10, '实测 %.2e' % rmax)
f = f_of('mach_lines')
dmax = max(abs(f(a, b) - float(phi.subs({X: a, Y: b})))
           for a, b in ((0.3, 0.7), (-2.1, 1.9), (4.4, 3.3)))
check('库式与符号式一致', dmax < 1e-10, '实测 %.2e' % dmax)
mu = math.atan(1 / beta)
check('Mach 角恒等 sinμ=1/M', abs(math.sin(mu) - 1 / M) < 1e-12,
      'μ=%.4f°' % math.degrees(mu))

print('门禁结果:', '全绿' if OK else '有 FAIL')
sys.exit(0 if OK else 1)
