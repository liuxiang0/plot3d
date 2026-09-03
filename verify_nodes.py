#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_nodes.py — 节点曲面奇异点数值验证（验证门禁）

方法: 多起点 scipy least_squares(LM) 解超定方程组 [f, fx, fy, fz] = 0，
      聚类后计数。节点 = f=0 且 ∇f=0 的孤立解。

已验证基准:
  - Kummer (mu²=2, lambda=5): 16 个实节点（四次曲面上限）
  - Barth sextic (w=1): 50 个仿射实节点 = 半径√3 正十二面体 20 + 半径 1 二十·十二面体 30
    （射影空间共 65 节点，为六次曲面世界纪录；其余在无穷远/复域）

教训:
  - Kummer 取 mu²=1 会退化为罗马曲面（整条奇异线），16 节点需 1<mu²<3
  - Barth 节点最远半径 √3≈1.732，搜索盒必须 ≥1.8，否则漏掉 12 个
  - L-BFGS-B 极小化 F=f²+|∇f|² 在退化 Hessian 处停滞，勿用；用 least_squares LM
  - **十次曲面节点验证必须用复步微分**: |f| 量级 ~1e5 时中心差分噪声可达 ~5e-6，
    会把真节点误判为正则点；复步梯度无相消误差，节点处精确给 0（实测 6e-8）
  - Barth 十次外壳层节点盆地极细（全空间/球壳随机命中率 <1%）：用 60 阶正二十面体
    对称群轨道补全（5 重轴 (−φ,1,0)，实测 12 条候选轴均为对称轴；3 重轴 (1,1,1)）
  - Hunt 曲面沿 A=B=0 交线奇异（非孤立节点）：判别式型 4A³+27B²=0 的通病
"""
import math
import os
import numpy as np
from scipy.optimize import least_squares

SQ5 = math.sqrt(5)
PHI = (1 + SQ5) / 2          # 黄金比
PHI2 = PHI + 1               # φ²

# Kummer 四次: (x²+y²+z²−μ²)² = λpqrs, p=1−z−√2x, q=1−z+√2x, r=1+z+√2y, s=1+z−√2y
# μ²=2 → λ=(3μ²−1)/(3−μ²)=5；pq=(1−z)²−2x², rs=(1+z)²−2y²
def kummer(p):
    x, y, z = p
    A = x*x + y*y + z*z - 2
    B = (1 - z)**2 - 2*x*x
    C = (1 + z)**2 - 2*y*y
    return A*A - 5*B*C

# Barth 六次 (w=1): 4(φ²x²−y²)(φ²y²−z²)(φ²z²−x²) = (2+√5)(x²+y²+z²−1)²
def barth(p):
    x, y, z = p
    return 4*(PHI2*x*x - y*y)*(PHI2*y*y - z*z)*(PHI2*z*z - x*x) \
           - (2 + SQ5)*(x*x + y*y + z*z - 1)**2

# Barth 十次 (Nordstrand 式, w=1, t=φ):
# 8(x²−φ⁴y²)(y²−φ⁴z²)(z²−φ⁴x²)(x⁴+y⁴+z⁴−2x²y²−2x²z²−2y²z²)
#   + (3+5φ)(x²+y²+z²−1)²(x²+y²+z²−(2−φ))² = 0
def barth_decic(p):
    x, y, z = p
    P4 = PHI**4
    t1 = 8*(x*x - P4*y*y)*(y*y - P4*z*z)*(z*z - P4*x*x) \
         * (x**4 + y**4 + z**4 - 2*x*x*y*y - 2*x*x*z*z - 2*y*y*z*z)
    s = x*x + y*y + z*z
    return t1 + (3 + 5*PHI)*(s - 1)**2 * (s - (2 - PHI))**2


def jac_grad(f, p, h=1e-6):
    g = np.empty(3)
    for i in range(3):
        q = p.copy(); q[i] += h
        r = p.copy(); r[i] -= h
        g[i] = (f(q) - f(r)) / (2*h)
    return g


def resid(p, f):
    return np.concatenate([[f(p)], jac_grad(f, p)])


def find_nodes(f, lo, hi, nstart=6000, seed=7, tol_cost=1e-20, tol_dist=0.05):
    """多起点求奇异点并聚类，返回节点坐标列表"""
    rng = np.random.default_rng(seed)
    pts = []
    for p0 in rng.uniform(lo, hi, (nstart, 3)):
        res = least_squares(resid, p0, args=(f,), method='lm',
                            xtol=1e-14, ftol=1e-14)
        if res.cost < tol_cost and all(lo-0.01 < v < hi+0.01 for v in res.x):
            q = res.x
            if all(np.linalg.norm(q - r) > tol_dist for r in pts):
                pts.append(q.copy())
    return pts


def grad_cs(f, q, h=1e-6):
    """复步微分：解析函数无相消误差，高阶多项式节点验证的可靠选择。
    （中心差分在 |f|~1e5 量级的十次曲面上，FD 噪声可达 ~5e-6，会把真节点误判为正则点）"""
    g = np.empty(3)
    qc = q.astype(complex)
    for i in range(3):
        z = qc.copy(); z[i] += 1j*h
        g[i] = f(z).imag / h
    return g


def verify_node(f, q, tol_f=1e-7, tol_g=1e-4):
    """节点终验: |f| 与 |∇f|(复步) 均须近零"""
    return abs(f(q)) < tol_f and float(np.linalg.norm(grad_cs(f, q))) < tol_g


def icosa_group():
    """Barth 十次的对称群（正二十面体旋转群 60 阶，与循环式对齐）:
    5 重轴 (−φ,1,0)（已实测 12 条候选轴均为对称轴）+ 3 重轴 (1,1,1)（循环置换）。"""
    def rot(axis, ang):
        a = axis/np.linalg.norm(axis)
        K = np.array([[0,-a[2],a[1]],[a[2],0,-a[0]],[-a[1],a[0],0]])
        return np.eye(3) + math.sin(ang)*K + (1-math.cos(ang))*(K@K)
    R5 = rot(np.array([-PHI, 1, 0]), 2*math.pi/5)
    R3 = rot(np.array([1, 1, 1]), 2*math.pi/3)
    G, front, seen = [np.eye(3)], [np.eye(3)], {tuple(np.round(np.eye(3).ravel(),6))}
    while front:
        nxt = []
        for g in front:
            for h in (R5, R3, R5.T, R3.T):
                m = h @ g
                key = tuple(np.round(m.ravel(), 6))
                if key not in seen:
                    seen.add(key); G.append(m); nxt.append(m)
        front = nxt
    assert len(G) == 60, f'群阶异常: {len(G)}'
    return G


if __name__ == '__main__':
    import sys
    if 'decic' in sys.argv:
        # 策略: 内三壳层球壳播种（盆地可命中）+ 外壳层轨道补全（盆地太细）。
        # 节点必在 4 个已知半径上（MathWorld/Barth 1996）。
        radii = [1/PHI, math.sqrt(5-2*SQ5), 1.0, math.sqrt((5+SQ5)/2)]
        seeds_per_shell = [12000, 12000, 12000, 40000]
        rng = np.random.default_rng(31)
        pts = []
        for r, n in zip(radii, seeds_per_shell):
            for d in rng.normal(size=(n, 3)):
                p0 = r * d / np.linalg.norm(d) + rng.normal(scale=0.015, size=3)
                res = least_squares(resid, p0, args=(barth_decic,), method='lm',
                                    xtol=1e-14, ftol=1e-14)
                if res.cost < 1e-12 and all(abs(v) < 2.2 for v in res.x):
                    q = res.x
                    if all(np.linalg.norm(q - s) > 0.05 for s in pts):
                        pts.append(q.copy())
        # 外壳层轨道补全: 已得外壳节点 → 60 阶对称群轨道 → 终验每个像
        outer_r = radii[3]
        outer = [q for q in pts if abs(np.linalg.norm(q) - outer_r) < 0.1]
        if outer:
            G = icosa_group()
            for q0 in outer:
                for R in G:
                    q = R @ q0
                    if (all(np.linalg.norm(q - s) > 0.05 for s in pts)
                            and verify_node(barth_decic, q)):
                        pts.append(q.copy())
        # 终验全部节点（h=1e-3 避免 FD 噪声）并计数
        pts = [q for q in pts if verify_node(barth_decic, q)]
        hist = {round(r, 3): 0 for r in radii}
        for q in pts:
            hist[round(float(np.linalg.norm(q)), 3)] += 1
        assert len(pts) == 300, f'Barth 十次期望 300 仿射实节点, 实得 {len(pts)}, 分布 {hist}'
        expect = {round(1/PHI,3): 90, round(math.sqrt(5-2*SQ5),3): 60,
                  1.0: 90, round(math.sqrt((5+SQ5)/2),3): 60}
        assert hist == expect, f'壳层分布异常: {hist}'
        np.save(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'barth_decic_nodes.npy'), np.array(pts))
        print(f'✓ Barth 十次曲面: {len(pts)} 个仿射实节点, 壳层分布 {hist}')
        sys.exit(0)

    k = find_nodes(kummer, -2.2, 2.2, nstart=4000, seed=3)
    assert len(k) == 16, f'Kummer 期望 16 节点, 实得 {len(k)}'
    print(f'✓ Kummer 四次曲面: {len(k)} 个实节点（上限 16 达到）')

    b = find_nodes(barth, -1.95, 1.95, nstart=6000, seed=7)
    assert len(b) == 50, f'Barth 期望 50 仿射实节点, 实得 {len(b)}'
    radii = {round(float(np.linalg.norm(q)), 3) for q in b}
    assert radii == {1.0, 1.732}, f'节点半径异常: {radii}'
    print(f'✓ Barth 六次曲面: {len(b)} 个仿射实节点（半径集合 {sorted(radii)}）')
    print('全部门禁通过')
