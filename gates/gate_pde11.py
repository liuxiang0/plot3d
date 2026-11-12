#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_pde11.py — PDE 族⑪ 门禁（激波极线 + KdV-Burgers 复合波 + GN undular bore）

1) shock_polar（M₁=2.5）：库式=门禁重算 + 三条 RH（采样 β）+ 端点（β→μ₁ 回来流 /
   β→π/2 正激波点）+ 极线最远偏转角=θ-β-M 的 θ_max + 声速点 |V₂|=a₂ + Mach 反射判据
2) kdv_burgers：符号残差 0 + 远场极限 + 参数恒等 k=ν/10δ, q=−12δk², p=−12νk/5
3) gn_bore：质量守恒 + 波列 crest 数/调制递减 + 领先孤波速=同宿打靶 c(±5%)
   + bore 展宽 + 生成器=缓存
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
GA, M1 = 1.4, 2.5


def check(name, cond, detail=''):
    global OK
    print(('  ✓ ' if cond else '  ✗ ') + name + ('  ' + detail if detail else ''))
    if not cond:
        OK = False


def downstream(beta, m1=M1, ga=GA):
    """正激波关系给下游状态（a₁=ρ₁=p₁=1 单位）"""
    u1 = m1
    m1n = m1 * math.sin(beta)
    r = (ga + 1) * m1n ** 2 / ((ga - 1) * m1n ** 2 + 2)
    p = 1 + 2 * ga / (ga + 1) * (m1n ** 2 - 1)
    vn1, vt = u1 * math.sin(beta), u1 * math.cos(beta)
    vn2 = vn1 / r
    n = np.array([math.sin(beta), -math.cos(beta)])
    tv = np.array([math.cos(beta), math.sin(beta)])
    V2 = vn2 * n + vt * tv
    t21 = p / r
    return r, p, V2, t21


def rh_res(beta):
    r, p, V2, t21 = downstream(beta)
    u1 = M1
    p1 = 1.0 / GA
    p2 = p1 * p
    n = np.array([math.sin(beta), -math.cos(beta)])
    tv = np.array([math.cos(beta), math.sin(beta)])
    V1 = np.array([u1, 0.0])
    vn1, vt1 = V1 @ n, V1 @ tv
    vn2, vt2 = V2 @ n, V2 @ tv
    h1 = GA * p1 / (GA - 1)
    h2 = GA * p2 / ((GA - 1) * r)
    return max(abs(vn1 - r * vn2), abs(vn1 ** 2 + p1 - (r * vn2 ** 2 + p2)),
               abs(vt1 - vt2),
               abs(h1 + 0.5 * u1 ** 2 - (h2 + 0.5 * float(V2 @ V2))))


# ---------- 1) 激波极线 ----------
print('[1] 激波极线（M₁=2.5 速端曲线）')
spec = mathparse.parse_input(cl.BUILTIN['shock_polar']['expr'])
comps = spec['comps']
tlo, thi = spec['t_range']


def polar(bt):
    return np.array([float(comps['x'](bt)), float(comps['y'](bt)), float(comps['z'](bt))])


errs = []
for bt in (0.5, 0.7, 0.9, 1.2, 1.5):
    r, p, V2, t21 = downstream(bt)
    errs.append(float(np.abs(polar(bt)[:2] - V2).max()))
check('库式 = 门禁重算下游速度（5 个 β）', max(errs) < 1e-9, '最大差 %.2e' % max(errs))
check('三条采样 β 的 RH 跳变 < 1e-9', max(rh_res(b) for b in (0.5, 0.9, 1.4)) < 1e-9,
      '最大 %.2e' % max(rh_res(b) for b in (0.5, 0.9, 1.4)))
mu1 = math.asin(1 / M1)
r, p, V2, t21 = downstream(mu1 + 1e-7)
check('β→μ₁ 退回来流 V₂→(M₁,0)', float(np.abs(V2 - np.array([M1, 0.0])).max()) < 1e-6,
      'V₂=(%.6f, %.2e)' % (V2[0], V2[1]))
r, p, V2, t21 = downstream(math.pi / 2 - 1e-9)
u2n = M1 * ((GA - 1) * M1 ** 2 + 2) / ((GA + 1) * M1 ** 2)
check('β→π/2 为正激波点（v=0, u₂ 公式）', abs(V2[1]) < 1e-6 and abs(V2[0] - u2n) < 1e-6,
      'u₂=%.6f / 公式 %.6f' % (V2[0], u2n))
bs = np.linspace(mu1 + 1e-6, math.pi / 2 - 1e-6, 40001)
pol = np.array([polar(b)[:2] for b in bs[::40]])
thp = np.arctan2(pol[:, 1], pol[:, 0])
thmax_polar = float(thp.max())


def theta_of(b):
    return math.atan(2.0 / math.tan(b) * (M1 * M1 * math.sin(b) ** 2 - 1.0)
                     / (M1 * M1 * (GA + math.cos(2 * b)) + 2.0))


thmax_tbm = max(theta_of(b) for b in bs[::40])
check('极线最远偏转角 = θ-β-M 的 θ_max', abs(thmax_polar - thmax_tbm) < 1e-6,
      '极线 %.6f° / θ-β-M %.6f°' % (math.degrees(thmax_polar), math.degrees(thmax_tbm)))


def sonic_f(b):
    r, p, V2, t21 = downstream(b)
    return float(np.linalg.norm(V2)) - math.sqrt(GA * p / r)


lo, hi = mu1 + 1e-6, math.pi / 2 - 1e-6
for _ in range(80):
    mid = 0.5 * (lo + hi)
    if sonic_f(lo) * sonic_f(mid) <= 0:
        hi = mid
    else:
        lo = mid
check('声速点 |V₂|=a₂ 存在（极线跨声速）', abs(sonic_f(0.5 * (lo + hi))) < 1e-9,
      'β_s=%.4f°' % math.degrees(0.5 * (lo + hi)))
check('Mach 反射判据：θ_w=35°>θ_max 无附着解', math.radians(35.0) > thmax_tbm,
      'θ_max=%.3f°' % math.degrees(thmax_tbm))

# ---------- 2) KdV-Burgers 复合波 ----------
print('[2] KdV-Burgers 复合波（ν=0.6, δ=0.2, Galilean V=2）')
NU, DL = 0.6, 0.2
KK = NU / (10 * DL)
QQ = -12 * DL * KK ** 2
PP = -12 * NU * KK / 5
SS0, VV = -0.966, 2.0
x, y = sp.symbols('x y', real=True)
uk = (VV - 0.75) + PP * sp.tanh(KK * (x - (SS0 + VV) * y)) \
    + QQ * sp.tanh(KK * (x - (SS0 + VV) * y)) ** 2
resk = sp.simplify(sp.diff(uk, y) + uk * sp.diff(uk, x)
                   + DL * sp.diff(uk, x, 3) - NU * sp.diff(uk, x, 2))
fres = sp.lambdify((x, y), resk, 'numpy')
rk = float(np.abs(fres(np.linspace(-5, 8, 25), np.linspace(0.2, 5, 25))).max())
check('代回 u_t+uu_x+δu_xxx=νu_xx（符号残差采样）', rk < 1e-9,
      '最大残差 %.2e' % rk)
lm = float(sp.limit(uk.subs(y, 0), x, -sp.oo))
lp = float(sp.limit(uk.subs(y, 0), x, sp.oo))
check('远场极限（符号）', abs(lm - (VV - 0.75 - PP + QQ)) < 1e-12
      and abs(lp - (VV - 0.75 + PP + QQ)) < 1e-12, 'u(∓∞)=%.4f/%.4f' % (lm, lp))
check('参数恒等 k=ν/10δ, q=−12δk², p=−12νk/5',
      abs(KK - 0.3) < 1e-12 and abs(QQ + 0.216) < 1e-12 and abs(PP + 0.432) < 1e-12,
      'k=%.4f q=%.4f p=%.4f' % (KK, QQ, PP))
fk = mathparse.parse_input(cl.BUILTIN['kdv_burgers']['expr'])['f']
dmax = max(abs(fk(a, b) - float(uk.subs({x: a, y: b})))
           for a, b in ((-2.0, 1.0), (1.5, 2.5), (5.0, 4.0)))
check('库式与符号式一致', dmax < 1e-9, '最大差 %.2e' % dmax)

# ---------- 3) GN undular bore ----------
print('[3] GN undular bore（h_L=1.3→h_R=1.0, Serre 数值解）')
xs, ts, H = trisurf._gn_bore_solve()
dx = xs[1] - xs[0]
m0 = np.trapezoid(H[0], xs)
m1 = np.trapezoid(H[-1], xs)
check('质量守恒（相对 <1e-6）', abs(m1 - m0) / abs(m0) < 1e-6,
      'Δm/m=%.2e' % (abs(m1 - m0) / abs(m0)))
HR = 1.0


def crests(hf):
    idx = [i for i in range(2, len(hf) - 2)
           if hf[i] > hf[i - 1] and hf[i] >= hf[i + 1] and hf[i] > HR + 0.05]
    return idx


cr = crests(H[-1])
check('undular 波列：crest 数 ≥4', len(cr) >= 4, 'crest=%d' % len(cr))
amps = [H[-1][i] - HR for i in cr[-3:][::-1]]
check('调制递减：领先三 crest 幅值递减', amps[0] > amps[1] > amps[2],
      '幅值 %s' % ['%.4f' % a for a in amps])
i_a, i_b = len(ts) - 1, max(0, len(ts) - 12)
lead_a = xs[cr[-1]]
crb = crests(H[i_b])
lead_b = xs[crb[-1]] if crb else xs[cr[-1]]
v_lead = (lead_a - lead_b) / (ts[i_a] - ts[i_b])
c_gn = trisurf._gn_profile(HR, amps[0], 1.0)[2]
check('领先孤波速 = 同宿打靶 c(a_lead)（±5%）', abs(v_lead - c_gn) / c_gn < 0.05,
      '实测 %.4f / 打靶 %.4f' % (v_lead, c_gn))


def width_at(hf):
    above = np.nonzero(hf > HR + 0.02)[0]
    step = np.nonzero(hf > (1.3 + HR) / 2)[0]
    return xs[above[-1]] - (xs[step[-1]] if len(step) else xs[above[0]])


w1, w2 = width_at(H[len(ts) // 2]), width_at(H[-1])
check('bore 展宽（前缘−后缘 随 t 增大）', w2 > w1, '宽 %.2f→%.2f' % (w1, w2))
quads = trisurf.gn_bore()
V = np.array([p for qd in quads for p in qd])
stride = max(1, len(xs) // 200)
X = xs[::stride]
Hs = H[::max(1, len(ts) // 50), ::stride]
Tsub = ts[::max(1, len(ts) // 50)]
okv = True
for xv, tv, zv in V[:3000]:
    j = int(round(tv / (Tsub[1] - Tsub[0]))) if len(Tsub) > 1 else 0
    j = min(j, len(Tsub) - 1)
    if abs(zv - (np.interp(xv, X, Hs[j]) - HR) * 2.0) > 1e-9:
        okv = False
        break
check('生成器顶点 = 缓存 h(x,t)', okv, 'quads=%d' % len(quads))

# ---------- 4) 库/资料卡 ----------
print('[4] 库/资料卡登记')
for key in ('shock_polar', 'kdv_burgers'):
    e = cl.BUILTIN.get(key)
    check('库条目 %s（表达式）已注册' % key, e is not None and bool(e.get('expr')))
e = cl.BUILTIN.get('gn_bore')
check('库条目 gn_bore 已注册且 faces 非空',
      e is not None and e.get('gen') is True and bool(e.get('faces')),
      'faces=%d' % (len(e['faces']) if e and e.get('faces') else 0))
cards = getattr(gallery, 'CARDS', {})
for key in ('shock_polar', 'kdv_burgers', 'gn_bore'):
    check('资料卡 %s 已登记' % key,
          key in cards and all(k2 in cards[key] for k2 in ('formula', 'props', 'trivia')))

print('门禁结果:', '全绿' if OK else '有 FAIL')
sys.exit(0 if OK else 1)
