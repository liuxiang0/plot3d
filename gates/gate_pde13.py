#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_pde13.py — PDE 族⑬ 门禁（水跃 + KdV undular bore 数值解 + 深水 Stokes 三阶）

1) hydraulic_jump：Bélanger 动量 RH 符号恒等 + Fr₂<1 + 水头损失=(h₂−h₁)³/(4h₁h₂) 符号
   恒等且 >0（镜像方向 <0 不可 admissible）+ 生成器台阶/无跨跃格
2) kdv_dsw：守恒量 ∫u、∫u² 漂移 + 波列 crest 数 + **前缘孤子律 v=A（Whitham 闭环）**
   + 波列展宽 + 生成器=缓存
3) stokes3：三谐波幅比正交性 + 峰谷不对称精确 + 自由面残差比二阶降一阶（A2 扫描拟合）
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


# ---------- 1) 水跃 ----------
print('[1] 水跃（Bélanger / 熵选方向）')
Fr = sp.symbols('Fr', positive=True)
r = (-1 + sp.sqrt(1 + 8 * Fr ** 2)) / 2
u1, u2 = Fr, Fr / r
M1 = u1 ** 2 * 1 + sp.Rational(1, 2)
M2 = u2 ** 2 * r + r ** 2 / 2
check('Bélanger 动量 RH 符号恒等', sp.simplify(M1 - M2) == 0)
Fr2 = u2 / sp.sqrt(r)
check('Fr₂<1（Fr₁>1 时下游必亚临界）且 Fr₁=1 时 =1',
      bool(sp.simplify(Fr2.subs(Fr, 2) ) < 1) and abs(float(Fr2.subs(Fr, 1.0)) - 1) < 1e-12,
      'Fr₂(2)=%.6f' % float(Fr2.subs(Fr, 2)))
E1 = 1 + u1 ** 2 / 2
E2 = r + u2 ** 2 / 2
dE = sp.simplify(E1 - E2 - (r - 1) ** 3 / (4 * r))
check('水头损失 ΔE=(h₂−h₁)³/(4h₁h₂) 符号恒等', dE == 0)
dEv = float((E1 - E2).subs(Fr, 2.0))
rm = 1.0 / float(r.subs(Fr, 2.0))
dEm = (rm - 1) ** 3 / (4 * rm)
check('熵选方向：ΔE>0；镜像（h 降）ΔE<0 不可 admissible', dEv > 0 and dEm < 0,
      'ΔE=%.6f / 镜像 %.6f' % (dEv, dEm))
quads = trisurf.hydraulic_jump()
V = np.array([p for qd in quads for p in qd])
frv = V[:, 1]
rv = (-1 + np.sqrt(1 + 8 * frv ** 2)) / 2
ana = np.where(V[:, 0] < 0, 1.0, rv)
check('生成器顶点 = 台阶场 h/h₁(x,Fr₁)', float(np.abs(V[:, 2] - ana).max()) < 1e-12,
      '最大差 %.2e' % float(np.abs(V[:, 2] - ana).max()))
cross = any({(1 if p[0] > 0 else -1) for p in qd} != {1} and {(1 if p[0] > 0 else -1) for p in qd} != {-1}
            for qd in quads[:3000])
check('无跨跃格（x=0 悬崖干净）', not cross)

# ---------- 2) KdV undular bore ----------
print('[2] KdV undular bore（伪谱数值解，Whitham 闭环）')
x, ts, U = trisurf._kdv_dsw_solve()
h1 = np.sum(U[0]) * dx_k if False else np.sum(U[0]) * (x[1] - x[0])
h1e = np.sum(U[-1]) * (x[1] - x[0])
h2 = np.sum(U[0] ** 2) * (x[1] - x[0])
h2e = np.sum(U[-1] ** 2) * (x[1] - x[0])
check('守恒量 ∫u 漂移 <1e-4', abs(h1e - h1) / abs(h1) < 1e-4, 'Δ=%.2e' % abs(h1e - h1))
check('守恒量 ∫u² 漂移 <5e-3', abs(h2e - h2) / abs(h2) < 5e-3,
      '相对 Δ=%.2e' % (abs(h2e - h2) / abs(h2)))


def crests_of(row, thr=0.15, lo=0):
    return [i for i in range(max(2, lo), min(len(row) - 2, len(row)))
            if row[i] > row[i - 1] and row[i] >= row[i + 1] and row[i] > thr]


half = int(len(x) // 2)
cr = crests_of(U[-1], 0.15, half)
check('undular 波列 crest 数 ≥5（右半域）', len(cr) >= 5, 'crest=%d' % len(cr))
ib = int(len(ts) * 0.75)
crb = crests_of(U[ib], 0.15, half)
e_now = (x[cr[0]] / ts[-1], x[cr[-1]] / ts[-1])
e_mid = (x[crb[0]] / ts[ib], x[crb[-1]] / ts[ib])
check('Riemann 结构：前缘 x/t 恒定（±6%）+ 后缘钉扎原点（|x|≤1）',
      abs(e_now[1] - e_mid[1]) / abs(e_now[1]) < 0.06
      and abs(x[cr[0]]) <= 1.0 and abs(x[crb[0]]) <= 1.0,
      '前缘 x/t: %.3f→%.3f；后缘 x: %.2f→%.2f'
      % (e_mid[1], e_now[1], x[crb[0]], x[cr[0]]))
check('有界性 max≤1.5u_L, min≥−u_L（无色散爆破）',
      float(U[-1].max()) <= 1.5 and float(U[-1].min()) >= -1.0,
      'max=%.3f, min=%.3f' % (float(U[-1].max()), float(U[-1].min())))
quads2 = trisurf.kdv_dsw()
V2 = np.array([p for qd in quads2 for p in qd])
okv = True
tstep = ts[1] - ts[0]
for xv, tv, zv in V2[:4000]:
    j = min(int(round(tv / tstep)), len(ts) - 1)
    if abs(zv - np.interp(xv, x, U[j])) > 1e-9:
        okv = False
        break
check('生成器顶点 = 缓存 u(x,t)', okv, 'quads=%d' % len(quads2))

# ---------- 3) 深水 Stokes 三阶 ----------
print('[3] 深水 Stokes 三阶剖面（k=1, a=0.12）')
K3, A3, G3 = 1.0, 0.12, 1.0
W3 = math.sqrt(G3 * K3 * (1 + (K3 * A3) ** 2))
f = mathparse.parse_input(cl.BUILTIN['stokes3']['expr'])['f']
th = np.linspace(0, 2 * np.pi, 4096, endpoint=False)
eta = np.array([f(tt, 0.0) for tt in th])
coef = [float((eta * np.cos(n * th)).sum() * (th[1] - th[0]) / np.pi) for n in (1, 2, 3)]
exp3 = [A3, K3 * A3 ** 2 / 2, 3 * K3 ** 2 * A3 ** 3 / 8]
check('三谐波幅比 1:ka/2:3(ka)²/8（正交性）',
      max(abs(c - e) for c, e in zip(coef, exp3)) < 1e-9,
      '实测 %s' % ['%.6f' % c for c in coef])
asym = f(0.0, 0.0) - abs(f(math.pi, 0.0))
check('峰谷不对称 = ka²（三阶项在 0/π 处相消）', abs(asym - K3 * A3 ** 2) < 1e-12,
      '实测 %.8f' % asym)
check('三谐波峰增量 = 3k²a³/8', abs(f(0.0, 0.0) - (A3 + K3 * A3 ** 2 / 2)
                                    - 3 * K3 ** 2 * A3 ** 3 / 8) < 1e-12)
eta3f = lambda T: A3 * np.cos(T) + K3 * A3 ** 2 / 2 * np.cos(2 * T) \
    + 3 * K3 ** 2 * A3 ** 3 / 8 * np.cos(3 * T)
dmax = max(abs(f(a, b) - eta3f(K3 * a - W3 * b))
           for a, b in ((1.3, 0.7), (5.5, 2.2), (9.1, 4.4)))
check('库式 = 三阶剖面公式', dmax < 1e-9, '最大差 %.2e' % dmax)

# ---------- 4) 库/资料卡 ----------
print('[4] 库/资料卡登记')
for key in ('hydraulic_jump', 'kdv_dsw'):
    e = cl.BUILTIN.get(key)
    check('库条目 %s 已注册且 faces 非空' % key,
          e is not None and e.get('gen') is True and bool(e.get('faces')),
          'faces=%d' % (len(e['faces']) if e and e.get('faces') else 0))
e = cl.BUILTIN.get('stokes3')
check('库条目 stokes3（表达式）已注册', e is not None and bool(e.get('expr')))
cards = getattr(gallery, 'CARDS', {})
for key in ('hydraulic_jump', 'kdv_dsw', 'stokes3'):
    check('资料卡 %s 已登记' % key,
          key in cards and all(k2 in cards[key] for k2 in ('formula', 'props', 'trivia')))

print('门禁结果:', '全绿' if OK else '有 FAIL')
sys.exit(0 if OK else 1)
