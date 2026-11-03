#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""trisurf.py — 三角剖分层（显示管线②级）生成器

四条路线（顶点均解析精确落在目标曲面上，连接关系来自剖分）:
  geodesic      : 二十面体细分 freq² → 投影球面（Fuller 测地穹顶；等价于球面点集凸包/3D Delaunay）
  bezier_tri    : 三次三角 Bézier 片——参数域是三角形（非矩形），重心格点剖分
  terrain       : 散点采样 z=f(x,y) → scipy.spatial.Delaunay(2D) → 提升（点云路线，不新增顶点）
  drum          : 圆膜 Bessel 模态 J₀(αr) 极坐标结构化格点 → 中心扇形 + 环带 quad 两三角（顶点精确）
  fdtd          : 2D Maxwell FDTD（Yee 格）E_z 快照 → 抽稀结构化格点高度场三角剖分（波前半径≈courant·steps）
  sph_tri_patch : 球面三角片（大圆边）——平面三角域重心格点剖分 → 归一化到球

返回 faces = [ [[x,y,z]*3], ... ]（三角形多边形列表），与 polytopes.py 的 'faces' 机制同构，
三路渲染（桌面/缩略图/手机）直接复用。
"""
import math

import numpy as np


def _tris_from_lattice(rows):
    """rows = 逐行点列表（行 i 有 i+1 个点，三角形格点）→ 三角形面片"""
    faces = []
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        for j in range(len(a)):
            faces.append([a[j], b[j], b[j + 1]])
            if j + 1 < len(a):
                faces.append([a[j], b[j + 1], a[j + 1]])
    return faces


def geodesic(freq=3, R=2.0):
    """二十面体每面细分 freq² 个球面三角形"""
    t = (1 + math.sqrt(5)) / 2
    V = [np.array(v, float) for v in
         [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t),
          (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]]
    F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
         (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
         (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
         (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    faces = []
    for a, b, c in F:
        pa, pb, pc = V[a], V[b], V[c]
        rows = []
        for i in range(freq + 1):
            row = []
            for j in range(i + 1):
                u, v, w = 1 - i / freq, (i - j) / freq, j / freq
                p = u * pa + v * pb + w * pc
                p = R * p / np.linalg.norm(p)          # 投影到球面: 顶点精确
                row.append(p)
            rows.append(row)
        faces.extend(_tris_from_lattice(rows))
    return [[list(map(float, p)) for p in tri] for tri in faces]


def bezier_tri(m=22):
    """三次三角 Bézier 片: 三角参数域 → 重心格点剖分"""
    P = {  # 控制网 (i,j,k), i+j+k=3
        (3, 0, 0): (0, 0, 0), (0, 3, 0): (3, 0, 0), (0, 0, 3): (1.5, 2.6, 0),
        (2, 1, 0): (1, 0, 0.6), (1, 2, 0): (2, 0, 0.6), (2, 0, 1): (0.5, 0.9, 0.9),
        (1, 0, 2): (0.5, 1.7, 0.9), (0, 2, 1): (2.5, 0.9, 0.9), (0, 1, 2): (2, 1.7, 0.9),
        (1, 1, 1): (1.5, 0.9, 1.5),
    }
    coef = {(3, 0, 0): 1, (0, 3, 0): 1, (0, 0, 3): 1,
            (2, 1, 0): 3, (1, 2, 0): 3, (2, 0, 1): 3, (1, 0, 2): 3,
            (0, 2, 1): 3, (0, 1, 2): 3, (1, 1, 1): 6}
    rows = []
    for i in range(m + 1):
        row = []
        for j in range(i + 1):
            u, v, w = 1 - i / m, (i - j) / m, j / m
            p = np.zeros(3)
            for k3, c in coef.items():
                p += c * (u ** k3[0]) * (v ** k3[1]) * (w ** k3[2]) * np.array(P[k3])
            row.append(p)
        rows.append(row)
    return [[list(map(float, q)) for q in tri] for tri in _tris_from_lattice(rows)]


def terrain(n=1400, seed=7, lo=-3.0, hi=3.0):
    """散点采样高度场 → 2D Delaunay → 提升（点云路线: 顶点=原采样点）"""
    from scipy.spatial import Delaunay
    rng = np.random.default_rng(seed)
    pts = rng.uniform(lo, hi, (n, 2))
    b = np.linspace(lo, hi, 25)                     # 边界环: 保证凸包覆盖方域
    ring = np.concatenate([np.c_[b, np.full_like(b, lo)], np.c_[b, np.full_like(b, hi)],
                           np.c_[np.full_like(b, lo), b], np.c_[np.full_like(b, hi), b]])
    pts = np.vstack([pts, ring])
    f = lambda x, y: 1.2 * math.sin(x) * math.cos(y) + 0.4 * math.sin(2 * x + y)
    tri = Delaunay(pts)
    faces = []
    for a, b2, c in tri.simplices:
        pa, pb, pc = pts[a], pts[b2], pts[c]
        # 剔除过瘦长跨越边界的片(面积过大者)
        area = 0.5 * abs((pb[0]-pa[0])*(pc[1]-pa[1]) - (pc[0]-pa[0])*(pb[1]-pa[1]))
        if area > 1.2:
            continue
        faces.append([[pa[0], pa[1], f(pa[0], pa[1])],
                      [pb[0], pb[1], f(pb[0], pb[1])],
                      [pc[0], pc[1], f(pc[0], pc[1])]])
    return [[[float(c) for c in p] for p in tri_] for tri_ in faces]


def sph_tri_patch(m=20, R=2.0):
    """球面三角片: 平面三角域重心格点 → 归一化到球（边为大圆弧）"""
    A = np.array([1.0, 0, 0]); B = np.array([0, 1.0, 0]); C = np.array([0, 0, 1.0])
    rows = []
    for i in range(m + 1):
        row = []
        for j in range(i + 1):
            u, v, w = 1 - i / m, (i - j) / m, j / m
            p = u * A + v * B + w * C
            p = R * p / np.linalg.norm(p)
            row.append(p)
        rows.append(row)
    return [[list(map(float, q)) for q in tri] for tri in _tris_from_lattice(rows)]


def drum(nr=24, nth=64, alpha=2.404825557695773):
    """圆膜基模 J₀(αr)：波动方程圆域本征解，α=j₀,₁≈2.40483 使边界 u(1)=0。

    极坐标结构化格点，顶点解析精确落在 (r cosθ, r sinθ, J₀(αr))；
    中心 r=0 退化环用扇形三角，其余环带每 quad 切两三角。
    """
    from scipy.special import j0
    rs = np.linspace(0, 1, nr + 1)
    ths = np.linspace(0, 2 * np.pi, nth + 1)          # 末列与首列位置重合，接缝闭合
    P = np.empty((nr + 1, nth + 1, 3))
    for i, r in enumerate(rs):
        P[i, :, 0] = r * np.cos(ths)
        P[i, :, 1] = r * np.sin(ths)
        P[i, :, 2] = float(j0(alpha * r))
    v = lambda p: [float(c) for c in p]
    faces = []
    for j in range(nth):                              # 中心扇形（r=0 全行同点）
        faces.append([v(P[0, 0]), v(P[1, j]), v(P[1, j + 1])])
    for i in range(1, nr):                            # 环带 quad → 两三角
        for j in range(nth):
            a, b = P[i, j], P[i, j + 1]
            c, d = P[i + 1, j + 1], P[i + 1, j]
            faces.append([v(a), v(b), v(c)])
            faces.append([v(a), v(c), v(d)])
    return faces


def fdtd(n=121, steps=80, courant=0.7, display=61, raw=False, extent=3.0, zscale=1.2):
    """2D Maxwell FDTD（Yee 格，TMz：E_z/H_x/H_y）点源高斯脉冲软注入快照。

    因果性结构：波前半径 ≈ courant·steps 格（光锥外场≈0）——门禁据此校验。
    raw=True 返回 (Ez, courant, steps) 供验证；否则返回抽稀后高度场三角面。
    """
    Ez = np.zeros((n, n)); Hx = np.zeros((n, n)); Hy = np.zeros((n, n))
    c = (n - 1) // 2
    for step in range(steps):
        Hx[:, 1:] -= courant * (Ez[:, 1:] - Ez[:, :-1])
        Hy[1:, :] += courant * (Ez[1:, :] - Ez[:-1, :])
        Ez[1:-1, 1:-1] += courant * ((Hy[2:, 1:-1] - Hy[1:-1, 1:-1])
                                     - (Hx[1:-1, 2:] - Hx[1:-1, 1:-1]))
        if step < 40:                                   # 高斯脉冲软源
            Ez[c, c] += np.exp(-((step - 15) / 6.0) ** 2)
    if raw:
        return Ez, courant, steps
    stride = max(1, (n - 1) // (display - 1))
    g = Ez[::stride, ::stride]
    pk = np.abs(g).max() or 1.0
    g = g / pk * zscale
    nx, ny = g.shape
    xs = np.linspace(-extent, extent, nx); ys = np.linspace(-extent, extent, ny)
    v = lambda i, j: [float(xs[i]), float(ys[j]), float(g[i, j])]
    faces = []
    for i in range(nx - 1):
        for j in range(ny - 1):
            a, b = v(i, j), v(i, j + 1)
            cc, d = v(i + 1, j + 1), v(i + 1, j)
            faces.append([a, b, cc]); faces.append([a, cc, d])
    return faces


GENS = {'geodesic': geodesic, 'bezier_tri': bezier_tri,
        'terrain': terrain, 'sph_tri_patch': sph_tri_patch, 'drum': drum,
        'fdtd': fdtd}


_SKIP = {'gen', 'name', 'category', 'desc'}


def build(spec):
    """spec = {'gen': 名称, 其余为生成器关键字参数} → faces"""
    fn = GENS[spec['gen']]
    return fn(**{k: v for k, v in spec.items() if k not in _SKIP})
