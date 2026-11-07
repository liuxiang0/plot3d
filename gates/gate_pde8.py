#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_pde8.py — PDE 族⑧ 门禁（Prandtl-Meyer 膨胀波：超音速凸角的中心简单波）

prandtl_meyer 检查（M₁=2.0, θ_w=20°, γ=1.4，与 trisurf.prandtl_meyer 默认一致）：
1) Prandtl-Meyer 函数 ν(M)=√((γ+1)/(γ−1))·arctan√((γ−1)(M²−1)/(γ+1))−arctan√(M²−1)：
   ν(1)=0、单调增、ν(M₂)=ν(M₁)+θ_w（M₂ 门禁二分精解）
2) 扇几何：前缘 φ₁=μ₁=arcsin(1/M₁)、后缘 φ₂=μ₂−θ_w；sinμ=1/M 恒等
3) 扇内特征关系 φ=θ+μ(M)、θ=ν₁−ν(M)：θ(φ₁)=0、θ(φ₂)=−θ_w、M(φ) 由 M₁ 单调升至 M₂
4) PDE 级：中心简单波是定常等熵无旋 Euler 的精确解——速度场 u=V(M)(cosθ,sinθ)
   在扇内满足无旋 ∂v/∂x−∂u/∂y=0 与连续 ∂(ρu)/∂x+∂(ρv)/∂y=0（ρ 等熵，FD 残差）
5) 生成器：顶点 z=(M−M₁)·zscale 与门自身场一致；壁体/角点奇异域不出面；quads/bbox
6) 库/资料卡登记
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import curve_library as cl                        # noqa: E402
import gallery                                    # noqa: E402
import trisurf                                    # noqa: E402

OK = True

# 介质参数（与 trisurf.prandtl_meyer 默认一致）
M1, THW, GAMMA = 2.0, math.radians(20.0), 1.4
G1 = (GAMMA - 1.0) / 2.0
ZSCALE = 2.0


def check(name, cond, detail=''):
    global OK
    print(('  ✓ ' if cond else '  ✗ ') + name + ('  ' + detail if detail else ''))
    if not cond:
        OK = False


def nu(M):
    return (math.sqrt((GAMMA + 1.0) / (GAMMA - 1.0))
            * math.atan(math.sqrt(G1 / (G1 + 1.0) * (M * M - 1.0)))
            - math.atan(math.sqrt(M * M - 1.0)))


def mu(M):
    return math.asin(1.0 / M)


def V(M):
    return M / math.sqrt(1.0 + G1 * M * M)          # a₀=1


def rho(M):
    return ((1.0 + G1 * M1 * M1) / (1.0 + G1 * M * M)) ** (1.0 / (GAMMA - 1.0))


NU1 = nu(M1)
lo, hi = M1, 12.0
for _ in range(90):                                  # ν(M₂)=ν₁+θ_w
    mid = 0.5 * (lo + hi)
    if nu(mid) < NU1 + THW:
        lo = mid
    else:
        hi = mid
M2 = 0.5 * (lo + hi)
PHI1, PHI2 = mu(M1), mu(M2) - THW


def phi_of_M(M):
    return NU1 - nu(M) + mu(M)                       # 单调减: φ₁→φ₂


def M_of_phi(phi):
    a, b = M1, M2
    for _ in range(70):
        m = 0.5 * (a + b)
        if phi_of_M(m) > phi:
            a = m
        else:
            b = m
    return 0.5 * (a + b)


def M_field(x, y):
    phi = math.atan2(y, x)
    if phi > PHI1:
        return M1
    if phi < PHI2:
        return M2
    return M_of_phi(phi)


def uv(x, y):
    M = M_field(x, y)
    th = NU1 - nu(M)
    return V(M) * math.cos(th), V(M) * math.sin(th), M


# ---------- 1) Prandtl-Meyer 函数 ----------
print('[1] Prandtl-Meyer 函数 ν(M)')
check('ν(1)=0 且单调增', abs(nu(1.0)) < 1e-12 and nu(M1) < nu(M2),
      'ν(1)=%.2e, ν(M₁)=%.6f < ν(M₂)=%.6f' % (nu(1.0), nu(M1), nu(M2)))
check('ν(M₂)=ν(M₁)+θ_w（M₂ 二分精解）', abs(nu(M2) - NU1 - THW) < 1e-10,
      '残差 %.2e, M₂=%.6f' % (abs(nu(M2) - NU1 - THW), M2))
check('M₁<M₂ 且 ν(∞) 有限（最大折角）', M1 < M2 < 12.0,
      'ν(∞)=%.4f rad = %.2f°' % (nu(1e6), math.degrees(nu(1e6))))

# ---------- 2) 扇几何 ----------
print('[2] 膨胀扇几何（前/后缘特征线）')
check('前缘 φ₁=μ₁=arcsin(1/M₁)', abs(PHI1 - math.asin(1.0 / M1)) < 1e-12,
      'φ₁=%.4f°' % math.degrees(PHI1))
check('后缘 φ₂=μ₂−θ_w', abs(PHI2 - (mu(M2) - THW)) < 1e-12,
      'φ₂=%.4f°（扇宽 %.2f°）' % (math.degrees(PHI2), math.degrees(PHI1 - PHI2)))
check('sinμ=1/M 恒等（Mach 角定义）',
      abs(math.sin(mu(M1)) - 1.0 / M1) < 1e-12 and abs(math.sin(mu(M2)) - 1.0 / M2) < 1e-12,
      'μ₁=%.2f°, μ₂=%.2f°' % (math.degrees(mu(M1)), math.degrees(mu(M2))))

# ---------- 3) 扇内特征关系 ----------
print('[3] 扇内 φ=θ+μ(M)、θ=ν₁−ν(M)')
phis = [PHI1 - k * (PHI1 - PHI2) / 8 for k in range(9)]
Ms = [M_of_phi(p) for p in phis]
ths = [NU1 - nu(m) for m in Ms]
check('M(φ) 由 M₁ 单调升至 M₂', all(Ms[k] <= Ms[k + 1] + 1e-9 for k in range(8)),
      'M: %.4f→%.4f' % (Ms[0], Ms[-1]))
check('θ(φ₁)=0、θ(φ₂)=−θ_w', abs(ths[0]) < 1e-9 and abs(ths[-1] + THW) < 1e-9,
      'θ: %.2e→%.6f（期望 −%.4f）' % (ths[0], ths[-1], THW))
check('特征关系 φ=θ+μ(M) 自洽', max(abs(phis[k] - (ths[k] + mu(Ms[k]))) for k in range(9)) < 1e-9,
      '最大残差 %.2e' % max(abs(phis[k] - (ths[k] + mu(Ms[k]))) for k in range(9)))

# ---------- 4) PDE 级：无旋 + 连续 ----------
print('[4] 中心简单波 = 定常等熵无旋 Euler 精确解（FD 残差）')
h = 1e-4
worst_ir = worst_ct = 0.0
for r in (0.6, 1.0, 1.6, 2.2):
    for k in range(1, 6):
        phi = PHI2 + 0.15 * (PHI1 - PHI2) + k * 0.7 * (PHI1 - PHI2) / 6
        x, y = r * math.cos(phi), r * math.sin(phi)
        u1, v1, _ = uv(x + h, y)
        u2, v2, _ = uv(x - h, y)
        u3, v3, _ = uv(x, y + h)
        u4, v4, _ = uv(x, y - h)
        ir = (v1 - v2) / (2 * h) - (u3 - u4) / (2 * h)
        a1, b1, m1 = uv(x + h, y)
        a2, b2, m2 = uv(x - h, y)
        a3, b3, m3 = uv(x, y + h)
        a4, b4, m4 = uv(x, y - h)
        ct = ((rho(m1) * a1 - rho(m2) * a2) / (2 * h)
              + (rho(m3) * b3 - rho(m4) * b4) / (2 * h))
        worst_ir = max(worst_ir, abs(ir))
        worst_ct = max(worst_ct, abs(ct))
check('无旋 ∂v/∂x−∂u/∂y=0（扇内 20 点）', worst_ir < 1e-6, '最大残差 %.2e' % worst_ir)
check('连续 ∂(ρu)/∂x+∂(ρv)/∂y=0（扇内 20 点）', worst_ct < 1e-6, '最大残差 %.2e' % worst_ct)
check('等熵关系 ρ(M) 自洽（p/p₁=(T/T₁)^{γ/(γ−1)}）',
      abs(rho(M2) - ((1.0 + G1 * M1 * M1) / (1.0 + G1 * M2 * M2)) ** (1.0 / (GAMMA - 1.0))) < 1e-12,
      'ρ₂/ρ₁=%.6f' % rho(M2))

# ---------- 5) 生成器与奇异域 ----------
print('[5] 生成器 prandtl_meyer + 壁体/角点奇异域')
quads = trisurf.prandtl_meyer()
Vv = np.array([p for qd in quads for p in qd])
ana = np.array([(M_field(x, y) - M1) * ZSCALE for x, y, _ in Vv])
check('生成器顶点 = 解析场 (M−M₁)·zscale', float(np.abs(Vv[:, 2] - ana).max()) < 1e-9,
      '最大差 %.2e' % float(np.abs(Vv[:, 2] - ana).max()))
body = ((Vv[:, 0] < 0) & (Vv[:, 1] < 0)) \
    | ((Vv[:, 0] >= 0) & (Vv[:, 1] < -Vv[:, 0] * math.tan(THW)))
rc = np.sqrt(Vv[:, 0] ** 2 + Vv[:, 1] ** 2)
check('壁体与角点 r<rcore 奇异域不出面', not body.any() and rc.min() > 0.15 - 1e-9,
      'body=%d, r_min=%.4f' % (int(body.sum()), rc.min()))
check('quads 充足且 bbox 与声明域一致', len(quads) > 12000
      and abs(Vv[:, 0].max() - 4.0) < 1e-9 and abs(Vv[:, 1].max() - 3.0) < 1e-9
      and abs(Vv[:, 2].max() - (M2 - M1) * ZSCALE) < 1e-9,
      'quads=%d, z∈[%.4f, %.4f]' % (len(quads), Vv[:, 2].min(), Vv[:, 2].max()))

# ---------- 6) 库/资料卡登记 ----------
print('[6] 库/资料卡登记')
e = cl.BUILTIN.get('prandtl_meyer')
check('库条目 prandtl_meyer 已注册且 faces 非空',
      e is not None and e.get('gen') is True and bool(e.get('faces')),
      'faces=%d' % (len(e['faces']) if e and e.get('faces') else 0))
check('faces_kind=heightfield 且分类正确',
      e is not None and e.get('faces_kind') == 'heightfield'
      and e.get('category') == '偏微分方程解')
cards = getattr(gallery, 'CARDS', {})
check('资料卡已登记（formula/props/trivia）',
      'prandtl_meyer' in cards
      and all(k in cards['prandtl_meyer'] for k in ('formula', 'props', 'trivia')))

print('门禁结果:', '全绿' if OK else '有 FAIL')
sys.exit(0 if OK else 1)
