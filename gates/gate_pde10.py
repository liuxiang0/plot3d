#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_pde10.py — PDE 族⑩ 门禁（斜激波 + Green-Naghdi 孤波 + 黏性 Burgers 行波）

1) oblique_shock（M₁=2.5, θ_w=15°, γ=1.4）：θ-β-M 弱解精解 + 脱体角裕度
   + 四条 Rankine-Hugoniot 跳变（质量/法向动量/切向速度/能量）+ 熵增 + 生成器
2) gn_solitary（h₀=1, a=0.3）：稳态 Serre 第一积分（发散形式守恒律）符号级
   + 质量 ∫η dx=2aL + KdV 极限残差→0 + 平移恒等 + 生成器
3) burgers_tw（u₁=1, u₂=−0.5, ν=0.05）：符号 PDE 0 + 远场极限 + RH 速率恒等
   + Cole-Hopf 恒等 + Lax 熵条件 + 厚度 8νln3/Δ + 生成器
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
import trisurf                                    # noqa: E402

OK = True


def check(name, cond, detail=''):
    global OK
    print(('  ✓ ' if cond else '  ✗ ') + name + ('  ' + detail if detail else ''))
    if not cond:
        OK = False


# ---------- 1) 斜激波 ----------
print('[1] 斜激波（M₁=2.5, θ_w=15°, γ=1.4）')
M1, THW, GA = 2.5, math.radians(15.0), 1.4
MU1 = math.asin(1.0 / M1)


def theta_of(b):
    return math.atan(2.0 / math.tan(b) * (M1 * M1 * math.sin(b) ** 2 - 1.0)
                     / (M1 * M1 * (GA + math.cos(2 * b)) + 2.0))


bs = np.linspace(MU1 + 1e-7, math.pi / 2 - 1e-7, 200001)
th = np.array([theta_of(b) for b in bs[::200]])
bgrid = bs[::200]
imax = int(np.argmax(th))
THMAX = th[imax]
check('θ_w < θ_max（附着激波存在）', THW < THMAX,
      'θ_max=%.3f° @ β=%.2f°' % (math.degrees(THMAX), math.degrees(bgrid[imax])))
lo, hi = MU1 + 1e-9, bgrid[imax]
for _ in range(90):
    mid = 0.5 * (lo + hi)
    if theta_of(lo) - THW < 0 <= theta_of(mid) - THW or \
       (theta_of(lo) - THW) * (theta_of(mid) - THW) <= 0:
        hi = mid
    else:
        lo = mid
BETA = 0.5 * (lo + hi)
check('θ-β-M 弱解残差 < 1e-12', abs(theta_of(BETA) - THW) < 1e-12,
      'β=%.6f°（μ₁=%.2f°）' % (math.degrees(BETA), math.degrees(MU1)))
M1n = M1 * math.sin(BETA)
R21 = (GA + 1) * M1n ** 2 / ((GA - 1) * M1n ** 2 + 2)
P21 = 1 + 2 * GA / (GA + 1) * (M1n ** 2 - 1)
M2n2 = ((GA - 1) * M1n ** 2 + 2) / (2 * GA * M1n ** 2 - (GA - 1))
T21 = P21 / R21
a1, rho1, p1 = 1.0, 1.0, 1.0 / GA
u1 = M1 * a1
a2 = a1 * math.sqrt(T21)
u2 = math.sqrt(M2n2) * a2 / math.sin(BETA - THW)
n = np.array([-math.sin(BETA), math.cos(BETA)])
tvec = np.array([math.cos(BETA), math.sin(BETA)])
V1 = np.array([u1, 0.0])
V2 = u2 * np.array([math.cos(THW), math.sin(THW)])
vn1, vt1 = V1 @ n, V1 @ tvec
vn2, vt2 = V2 @ n, V2 @ tvec
rho2, p2 = rho1 * R21, p1 * P21
h1 = GA * p1 / ((GA - 1) * rho1)
h2 = GA * p2 / ((GA - 1) * rho2)
r_mass = rho1 * vn1 - rho2 * vn2
r_mom = rho1 * vn1 ** 2 + p1 - (rho2 * vn2 ** 2 + p2)
r_tan = vt1 - vt2
r_en = h1 + 0.5 * u1 ** 2 - (h2 + 0.5 * u2 ** 2)
worst = max(abs(r_mass), abs(r_mom), abs(r_tan), abs(r_en))
check('四条 Rankine-Hugoniot 跳变全满足', worst < 1e-9,
      '质量 %.1e / 法向动量 %.1e / 切向 %.1e / 能量 %.1e'
      % (r_mass, r_mom, r_tan, r_en))
cp = GA / (GA - 1)
ds = cp * math.log(T21) - math.log(P21)
check('熵增 Δs>0（激波不可逆）', ds > 0, 'Δs/R=%.6f' % ds)
quads = trisurf.oblique_shock()
V = np.array([p for qd in quads for p in qd])
tb = math.tan(BETA)
side = V[:, 1] - V[:, 0] * tb
exp_z = np.where(side < 0, P21 - 1.0, 0.0)
check('生成器顶点 = 台阶场（激波悬崖）', float(np.abs(V[:, 2] - exp_z).max()) < 1e-12,
      '最大差 %.2e' % float(np.abs(V[:, 2] - exp_z).max()))
for qd in quads[:2000]:
    sg = {float(np.sign(p[1] - p[0] * tb)) for p in qd}
    if len(sg) > 1:
        check('无跨激波格', False)
        break
else:
    check('无跨激波格（悬崖干净）', True)
check('楔体剔除（y≥x·tanθ_w）',
      bool(np.all(V[:, 1] >= V[:, 0] * math.tan(THW) - 1e-9)))

# ---------- 2) GN 孤波 ----------
print('[2] Green-Naghdi/Serre 孤波（h₀=1, a=0.3，同宿轨道精解）')
H0, AA, GG = 1.0, 0.3, 1.0
xs_p, eta_p, C = trisurf._gn_profile(H0, AA, GG)
check('波速区间 √(gh₀)<c<√(g(h₀+a))', math.sqrt(GG * H0) < C < math.sqrt(GG * (H0 + AA)),
      'c=%.9f（KdV %.6f, √(g(h₀+a))=%.6f）'
      % (C, math.sqrt(GG * H0) * (1 + AA / 2), math.sqrt(GG * (H0 + AA))))
hh = H0 + eta_p
uu = C * (1 - H0 / hh)
dxp = xs_p[1] - xs_p[0]


def _d1(f):
    o = np.empty_like(f)
    o[2:-2] = (-f[4:] + 8 * f[3:-1] - 8 * f[1:-3] + f[:-4]) / (12 * dxp)
    o[:2] = o[2]
    o[-2:] = o[-3]
    return o


def _d2(f):
    o = np.empty_like(f)
    o[2:-2] = (-f[4:] + 16 * f[3:-1] - 30 * f[2:-2]
               + 16 * f[1:-3] - f[:-4]) / (12 * dxp * dxp)
    o[:2] = o[2]
    o[-2:] = o[-3]
    return o


ux, uxx = _d1(uu), _d2(uu)
Eint = (-C * H0 * uu + GG * hh ** 2 / 2
        - (hh ** 3 / 3) * ((uu - C) * uxx - ux ** 2 / 2) - GG * H0 ** 2 / 2)
mm = np.abs(xs_p) < 0.8 * abs(xs_p[-1])
check('稳态 Serre 第一积分 ≡ gh₀²/2（FD 复算）', float(np.abs(Eint[mm]).max()) < 1e-7,
      '最大残差 %.2e' % float(np.abs(Eint[mm]).max()))
tail = float(np.abs(eta_p[np.abs(xs_p) > 0.9 * abs(xs_p[-1])]).max())
check('同宿衰逝（两端 |η|<1e-6·a）', tail < 1e-6 * AA, '尾幅 %.2e' % tail)
check('波峰 η(0)=a 且偶对称', abs(eta_p.max() - AA) < 1e-12
      and float(np.abs(eta_p - eta_p[::-1]).max()) < 1e-10)


def rel_l2(a2, xmax2):
    x2, e2, c2 = trisurf._gn_profile(H0, a2, GG, xmax=xmax2)
    L2 = (2 * H0 / math.sqrt(3)) * math.sqrt((H0 + a2) / a2)
    ref = a2 / np.cosh(x2 / L2) ** 2
    return (float(np.sqrt(np.trapezoid((e2 - ref) ** 2, x2))
                  / np.sqrt(np.trapezoid(e2 ** 2, x2))), c2)


r1, c1 = rel_l2(0.02, 60.0)
r2, c2b = rel_l2(0.005, 100.0)
check('KdV 极限：剖面→sech²（相对 L2 随 a 收缩）', r2 < r1 < 3e-2,
      'a=0.02: %.2e, a=0.005: %.2e' % (r1, r2))
check('KdV 极限：c→√(gh₀)(1+a/2h₀)',
      abs(c1 / (math.sqrt(GG * H0) * (1 + 0.01)) - 1) < 5e-3
      and abs(c2b / (math.sqrt(GG * H0) * (1 + 0.0025)) - 1) < 5e-3,
      '相对差 %.2e / %.2e'
      % (abs(c1 / (math.sqrt(GG * H0) * 1.01) - 1),
         abs(c2b / (math.sqrt(GG * H0) * 1.0025) - 1)))
quads2 = trisurf.gn_solitary()
V2v = np.array([p for qd in quads2 for p in qd])
ana2 = np.interp(V2v[:, 0] - C * V2v[:, 1], xs_p, eta_p)
check('生成器顶点 = 缓存剖面 η(x−ct)', float(np.abs(V2v[:, 2] - ana2).max()) < 1e-12,
      '最大差 %.2e' % float(np.abs(V2v[:, 2] - ana2).max()))
dlt = 0.73
tr2 = float(np.abs(np.interp(V2v[:, 0] + C * dlt - C * (V2v[:, 1] + dlt), xs_p, eta_p)
                   - ana2).max())
check('平移恒等 η(x+cΔ,t+Δ)=η(x,t)', tr2 < 1e-12, '最大差 %.2e' % tr2)

# ---------- 3) 黏性 Burgers 行波 ----------
print('[3] 黏性 Burgers 行波（u₁=1, u₂=−0.5, ν=0.05）')
U1, U2, NU = 1.0, -0.5, 0.05
DL = U1 - U2
SS = (U1 + U2) / 2
x, t = sp.symbols('x t', real=True)
ub = U2 + DL / (1 + sp.exp(DL * (x - SS * t) / (2 * NU)))
resb = sp.simplify(sp.diff(ub, t) + ub * sp.diff(ub, x) - NU * sp.diff(ub, x, 2))
check('代回 u_t+uu_x=νu_xx（符号）', resb == 0)
lim_m = float(sp.limit(ub.subs(t, 0), x, -sp.oo))
lim_p = float(sp.limit(ub.subs(t, 0), x, sp.oo))
check('远场极限 u(−∞)=u₁, u(+∞)=u₂（符号极限）',
      abs(lim_m - U1) < 1e-12 and abs(lim_p - U2) < 1e-12,
      'u(∓∞)=%.6f/%.6f' % (lim_m, lim_p))
check('RH 速率 s=(u₁+u₂)/2=[u²/2]/[u]（符号恒等）',
      abs(float(sp.simplify(SS - (U1 ** 2 - U2 ** 2) / 2 / (U1 - U2)))) < 1e-12)
phi = sp.exp(-U2 * x / (2 * NU)) + sp.exp(-U1 * x / (2 * NU))
cole = sp.simplify(-2 * NU * sp.diff(phi, x) / phi - ub.subs(t, 0))
fc = sp.lambdify(x, cole, 'numpy')
check('Cole-Hopf u=−2ν∂ₓlnφ 恒等', float(np.abs(fc(np.linspace(-3, 3, 31))).max()) < 1e-12,
      '最大差 %.2e' % float(np.abs(fc(np.linspace(-3, 3, 31))).max()))
check('Lax 熵条件 u₁>s>u₂', U1 > SS > U2, 's=%.3f' % SS)
xi9 = 2 * NU * math.log(9) / DL
wid = 2 * xi9
check('厚度（10%–90%）=8νln3/Δ', abs(wid - 8 * NU * math.log(3) / DL) < 1e-12,
      '宽=%.5f' % wid)
quads3 = trisurf.burgers_tw()
V3 = np.array([p for qd in quads3 for p in qd])
ana3 = U2 + DL / (1 + np.exp(DL * (V3[:, 0] - SS * V3[:, 1]) / (2 * NU)))
check('生成器顶点 = Taylor 剖面', float(np.abs(V3[:, 2] - ana3).max()) < 1e-12,
      '最大差 %.2e' % float(np.abs(V3[:, 2] - ana3).max()))

# ---------- 4) 库/资料卡 ----------
print('[4] 库/资料卡登记')
for key in ('oblique_shock', 'gn_solitary', 'burgers_tw'):
    e = cl.BUILTIN.get(key)
    check('库条目 %s 已注册且 faces 非空' % key,
          e is not None and e.get('gen') is True and bool(e.get('faces')),
          'faces=%d' % (len(e['faces']) if e and e.get('faces') else 0))
    cards = getattr(gallery, 'CARDS', {})
    check('资料卡 %s 已登记' % key,
          key in cards and all(k2 in cards[key] for k2 in ('formula', 'props', 'trivia')))

print('门禁结果:', '全绿' if OK else '有 FAIL')
sys.exit(0 if OK else 1)
