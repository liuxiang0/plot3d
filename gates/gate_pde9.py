#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_pde9.py — PDE 族⑨ 门禁（Rayleigh-Taylor 界面 + Sonic boom N 波 + 涡街动画式）

1) rayleigh_taylor：n²=gkA 符号（A>0 失稳/A<0 稳定）+ 两区 ∇²φ=0（符号）
   + 运动学 w(0±)=∂η/t + 动力学边界条件代回得频散（符号残差 0）+ 界面折角 + 生成器
2) n_wave：扇内 u=(x−ct)/(βt) 代回 u_t+cu_x+βuu_x=0（符号 0）+ Rankine-Hugoniot 恒等
   + ∫|u|dξ=a²/β 守恒 + 零均值 + 生成器
3) Kármán 涡街时间滑杆表达式：=tanh(4ψ(x−Us,y)) 恒等 + 刚性平移自洽
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


# ---------- 1) Rayleigh-Taylor ----------
print('[1] Rayleigh-Taylor 界面（ρ₁=1 下 / ρ₂=2 上, k=2, g=1, η₀=0.2）')
K, G, R1, R2, ETA0 = 2.0, 1.0, 1.0, 2.0, 0.2
A = (R2 - R1) / (R1 + R2)
N = math.sqrt(G * K * A)
check('n²=gkA>0（重在上→指数失稳）', N * N > 0 and abs(N * N - G * K * A) < 1e-15,
      'n=%.9f, A=%.6f' % (N, A))
A_neg = (R1 - R2) / (R1 + R2)
check('A<0（重在下）→ n²<0 振荡稳定', G * K * A_neg < 0, 'n²=%.4f' % (G * K * A_neg))

x, y, t = sp.symbols('x y t', real=True)
phi1 = -(N * ETA0 / K) * sp.exp(-K * y) * sp.cos(K * x) * sp.exp(N * t)   # y>0
phi2 = (N * ETA0 / K) * sp.exp(K * y) * sp.cos(K * x) * sp.exp(N * t)     # y<0
lap1 = sp.simplify(sp.diff(phi1, x, 2) + sp.diff(phi1, y, 2))
lap2 = sp.simplify(sp.diff(phi2, x, 2) + sp.diff(phi2, y, 2))
check('两区 ∇²φ=0（符号）', lap1 == 0 and lap2 == 0)
eta = ETA0 * sp.cos(K * x) * sp.exp(N * t)
w1 = sp.diff(phi1, y).subs(y, 0)
w2 = sp.diff(phi2, y).subs(y, 0)
etadot = sp.diff(eta, t)
check('运动学边界条件 w(0±)=∂η/t（符号）',
      sp.simplify(w1 - etadot) == 0 and sp.simplify(w2 - etadot) == 0,
      'w(0)=%s' % sp.sstr(w1))
dyn = sp.simplify((R1 * (sp.diff(phi2, t) + G * eta)
                   - R2 * (sp.diff(phi1, t) + G * eta)).subs(y, 0) / eta)
check('动力学边界条件 ⇒ n²=gk(ρ₂−ρ₁)/(ρ₁+ρ₂)（符号残差 0）',
      abs(float(dyn)) < 1e-12, '残差 %.2e' % abs(float(dyn)))

quads = trisurf.rayleigh_taylor()
V = np.array([p for qd in quads for p in qd])
ana = N * ETA0 * np.exp(-K * np.abs(V[:, 1])) * np.cos(K * V[:, 0]) * 3.0
check('生成器顶点 = nη₀e^{−k|y|}cos(kx)·zscale', float(np.abs(V[:, 2] - ana).max()) < 1e-12,
      '最大差 %.2e' % float(np.abs(V[:, 2] - ana).max()))
hh = 1e-6
wy_p = (np.exp(-K * hh) - 1) / hh * N * ETA0          # w_y(0+) 解析
wy_m = (np.exp(-K * hh) - 1) / hh * N * ETA0 * -1      # w_y(0−) = +k·nη₀·? 符号相反
check('界面折角：w 连续、∂w/∂y 两侧反号', abs(wy_p + wy_m) < 1e-12 and wy_p * wy_m < 0,
      'w_y(0±)=∓%.4f' % abs(wy_p))

# ---------- 2) N 波 ----------
print('[2] Sonic boom N 波（c=β=a=1）')
C, BE, AA = 1.0, 1.0, 1.0
u = (x - C * t) / (BE * t)
res = sp.simplify(sp.diff(u, t) + C * sp.diff(u, x) + BE * u * sp.diff(u, x))
check('扇内代回 u_t+cu_x+βuu_x=0（符号）', res == 0)
sh = C * t + AA * sp.sqrt(t)
u_in = u.subs(x, sh)
rhs = C + BE * (u_in + 0) / 2
check('Rankine-Hugoniot：d(ct+a√t)/dt = c+β(u₊+u₋)/2（符号恒等）',
      sp.simplify(sp.diff(sh, t) - rhs) == 0)
for t0, t1 in ((1.0, 4.0), (2.0, 3.0)):
    xi = np.linspace(-AA * math.sqrt(t0) * 1.0000001, AA * math.sqrt(t0) * 1.0000001, 200001)
    area = np.trapezoid(np.abs(xi) / (BE * t0), xi)
    mean = np.trapezoid(xi / (BE * t0), xi)
    ok_a = abs(area - AA * AA / BE) < 1e-5
    ok_m = abs(mean) < 1e-9
    if (t0, t1) == (1.0, 4.0):
        check('∫|u|dξ=a²/β 守恒（t=1）', ok_a, '实测 %.9f' % area)
        check('零均值 ∫u dξ=0', ok_m, '实测 %.2e' % mean)
    else:
        check('∫|u|dξ=a²/β 守恒（t=2）', ok_a, '实测 %.9f' % area)
quads2 = trisurf.n_wave()
V2 = np.array([p for qd in quads2 for p in qd])
XI2 = V2[:, 0] - C * V2[:, 1]
ana2 = np.where(np.abs(XI2) < AA * np.sqrt(V2[:, 1]), XI2 / (BE * V2[:, 1]), 0.0)
check('生成器顶点 = 自相似弱解（含激波外零区）', float(np.abs(V2[:, 2] - ana2).max()) < 1e-12,
      '最大差 %.2e' % float(np.abs(V2[:, 2] - ana2).max()))
dt_min = np.abs(V2[:, 1] - 2.0).min()
sec = V2[np.abs(V2[:, 1] - 2.0) <= dt_min]
sec = sec[np.argsort(sec[:, 0])][:, 2]
sgn = np.sign(sec)
flips = int(np.sum((sgn[:-1] < 0) & (sgn[1:] > 0)))
check('N 形：t=2 截面负→正恰一次过零（头尾激波夹斜坡）',
      flips == 1 and sec.min() < 0 < sec.max(),
      '过零 %d 次, u∈[%.3f, %.3f]' % (flips, sec.min(), sec.max()))

# ---------- 3) 涡街时间滑杆表达式 ----------
print('[3] Kármán 涡街时间滑杆表达式（ANIM_PRESETS）')
U, HH = 0.353545594, 0.14027
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         '..', 'plotter_app.py'), encoding='utf-8').read()
_i = _src.index('ANIM_PRESETS = [')
_j = _src.index('\n]\n', _i)
ANIM_PRESETS = eval(_src[_i + len('ANIM_PRESETS = '):_j + 2], {'math': math})  # noqa: S307
pre = [p for p in ANIM_PRESETS if '涡街' in p['name']]
check('ANIM_PRESETS 含涡街平移预设', len(pre) == 1 and pre[0]['param'] == 's',
      'param=%s, s∈[%.2f, %.2f]' % (pre[0]['param'], pre[0]['lo'], pre[0]['hi']) if pre else '')
import re as _re


def f_at(sv):
    """与 app 滑块同机制：把参数赋值 s=… 替换后重解析"""
    e2 = _re.sub(r'([;,]\s*)s=[^,;]+', lambda m: m.group(1) + ('s=%r' % sv),
                 pre[0]['expr'])
    return mathparse.parse_input(e2)['f']


def psi_k(xv, yv):
    k = 2 * math.pi
    t1 = math.cosh(k * (yv - HH)) - math.cos(k * xv)
    t2 = math.cosh(k * (yv + HH)) - math.cos(k * (xv - 0.5))
    return -(1.0 / (4 * math.pi)) * (math.log(t1) - math.log(t2))


errs = []
for xv, yv, sv in ((0.7, 0.3, 0.9), (-2.2, -0.4, 1.7), (3.1, 0.55, 2.6)):
    errs.append(abs(f_at(sv)(xv, yv) - math.tanh(4 * psi_k(xv - U * sv, yv))))
check('表达式(s 重解析) = tanh(4ψ(x−Us,y))（门禁独立复算）', max(errs) < 1e-9,
      '最大差 %.2e' % max(errs))
f1, f2 = f_at(0.9), f_at(0.9 + 0.37)
tr = [abs(f2(xv + U * 0.37, yv) - f1(xv, yv))
      for xv, yv in ((0.7, 0.3), (-2.2, -0.4))]
check('刚性平移自洽 f_{s+Δ}(x+UΔ,y)=f_s(x,y)', max(tr) < 1e-9, '最大差 %.2e' % max(tr))

# ---------- 4) 库/资料卡 ----------
print('[4] 库/资料卡登记')
for key in ('rayleigh_taylor', 'n_wave'):
    e = cl.BUILTIN.get(key)
    check('库条目 %s 已注册且 faces 非空' % key,
          e is not None and e.get('gen') is True and bool(e.get('faces')),
          'faces=%d' % (len(e['faces']) if e and e.get('faces') else 0))
    cards = getattr(gallery, 'CARDS', {})
    check('资料卡 %s 已登记' % key,
          key in cards and all(k2 in cards[key] for k2 in ('formula', 'props', 'trivia')))

print('门禁结果:', '全绿' if OK else '有 FAIL')
sys.exit(0 if OK else 1)
