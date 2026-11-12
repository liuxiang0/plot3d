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
import os

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


def _heightfield_quads(V, zscale, lo=-1.0, hi=1.0):
    """m×m 标量场 → (m−1)² 个四边形面片（高度场 z=V·zscale）"""
    m = V.shape[0]
    xs = np.linspace(lo, hi, m)
    quads = []
    for i in range(m - 1):
        for j in range(m - 1):
            quads.append([[float(xs[i]), float(xs[j]), float(V[i, j] * zscale)],
                          [float(xs[i + 1]), float(xs[j]), float(V[i + 1, j] * zscale)],
                          [float(xs[i + 1]), float(xs[j + 1]), float(V[i + 1, j + 1] * zscale)],
                          [float(xs[i]), float(xs[j + 1]), float(V[i, j + 1] * zscale)]])
    return quads


def gray_scott(m=96, iters=4000, F=0.035, k=0.065, Du=0.16, Dv=0.08,
               seed=7, zscale=3.0, cache='cache_grayscott.npy'):
    """Gray-Scott 反应扩散 Turing 斑图（spots/mitosis 参数）→ 高度场四边形面片。
    周期 Laplacian（5 点 stencil + roll）；结果磁盘缓存，首次模拟后导入零成本。"""
    import os
    cpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), cache)
    if os.path.exists(cpath):
        V = np.load(cpath)
        if V.shape == (m, m):
            return _heightfield_quads(V, zscale)
    rng = np.random.default_rng(seed)
    U = np.ones((m, m))
    V = np.zeros((m, m))
    for ci in (m // 4, m // 2, 3 * m // 4):          # 3×3 多种子: 斑图铺满周期胞
        for cj in (m // 4, m // 2, 3 * m // 4):
            U[ci - 2:ci + 3, cj - 2:cj + 3] = 0.5
            V[ci - 2:ci + 3, cj - 2:cj + 3] = 0.25
    V += 0.01 * rng.random((m, m))
    for _ in range(iters):
        Lu = np.roll(U, 1, 0) + np.roll(U, -1, 0) + np.roll(U, 1, 1) + np.roll(U, -1, 1) - 4 * U
        Lv = np.roll(V, 1, 0) + np.roll(V, -1, 0) + np.roll(V, 1, 1) + np.roll(V, -1, 1) - 4 * V
        uvv = U * V * V
        U += Du * Lu - uvv + F * (1 - U)
        V += Dv * Lv + uvv - (F + k) * V
    np.save(cpath, V)
    return _heightfield_quads(V, zscale)


def flow_cyl(n=120, lo=-2.5, hi=2.5, a=1.0, zscale=1.0):
    """圆柱绕流势流流函数高度场 ψ=U·y(1−a²/r²)（U=a=1）。
    ∇²ψ=0 的均匀流+偶极叠加解；仅在 r≥a 区域出面（圆柱体内部剔除），
    圆柱面 ψ=0 即无穿透边界条件。"""
    xs = np.linspace(lo, hi, n)
    quads = []
    a2 = a * a
    for i in range(n - 1):
        for j in range(n - 1):
            corners = [(xs[i], xs[j]), (xs[i + 1], xs[j]),
                       (xs[i + 1], xs[j + 1]), (xs[i], xs[j + 1])]
            if any(px * px + py * py < a2 for px, py in corners):
                continue                          # 含圆柱内点的格不出面
            quads.append([[px, py, float(py * (1 - a2 / (px * px + py * py)) * zscale)]
                          for px, py in corners])
    return quads


def blasius(nx=64, ny=64, x0=0.25, x1=4.0, y1=2.0, nu_U=0.04,
            cache='cache_blasius.npy'):
    """Blasius 层流平板边界层 u/U=f'(η), η=y/√(νx/U) 高度场。
    相似方程 f'''+½ff''=0 打靶 f''(0)=0.33206 数值解（磁盘缓存）。"""
    import os
    cpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), cache)
    if os.path.exists(cpath):
        eta, fp = np.load(cpath)
    else:
        from scipy.integrate import solve_ivp

        def rhs(e, w):
            f, fp_, fpp = w
            return [fp_, fpp, -0.5 * f * fpp]
        sol = solve_ivp(rhs, [0, 8], [0, 0, 0.33206], dense_output=True,
                        rtol=1e-10, atol=1e-12, max_step=0.01)
        eta = np.linspace(0, 8, 400)
        fp = sol.sol(eta)[1]
        np.save(cpath, np.array([eta, fp]))
    xs = np.linspace(x0, x1, nx)
    ys = np.linspace(0, y1, ny)
    quads = []
    for i in range(nx - 1):
        for j in range(ny - 1):
            pts = []
            for X, Y in ((xs[i], ys[j]), (xs[i + 1], ys[j]),
                         (xs[i + 1], ys[j + 1]), (xs[i], ys[j + 1])):
                e = Y / math.sqrt(nu_U * X)
                pts.append([float(X), float(Y), float(np.interp(e, eta, fp))])
            quads.append(pts)
    return quads


def karman(n=160, x0=-4.0, x1=4.0, y0=-1.0, y1=1.0, a=1.0, b=0.28054,
           G=1.0, core=0.055, zscale=2.0):
    """Kármán 涡街流函数高度场：双排交错点涡阵列的精确解。

    上排 +Γ 位于 (na, +b/2)，下排 −Γ 位于 (na+a/2, −b/2)；由无穷乘积恒等式
    |sin(πz/a)|² = [cosh(2πy/a) − cos(2πx/a)]/2 得收敛闭式
        ψ = −(Γ/4π)[ln(cosh(2π(y−h)/a) − cos(2πx/a))
                   − ln(cosh(2π(y+h)/a) − cos(2π(x−a/2)/a))],  h = b/2
    整条街以 U=(Γ/2a)tanh(πb/a) 刚性平移；b/a=0.28054 为 von Kármán 中性稳定比。
    涡核 r<core 处 ψ~−(Γ/2π)ln r 对数奇异，该处格点不出面。
    """
    xs = np.linspace(x0, x1, n).tolist()
    ys = np.linspace(y0, y1, n).tolist()
    X, Y = np.meshgrid(np.asarray(xs), np.asarray(ys), indexing='ij')
    h = b / 2.0
    k = 2.0 * np.pi / a
    t1 = np.cosh(k * (Y - h)) - np.cos(k * X)
    t2 = np.cosh(k * (Y + h)) - np.cos(k * (X - a / 2.0))
    P = (-(G / (4.0 * np.pi)) * (np.log(t1) - np.log(t2)) * zscale).tolist()

    bad = np.zeros(X.shape, dtype=bool)
    nper = int(np.ceil((x1 - x0) / a)) + 2
    for m in range(-nper, nper + 1):
        bad |= (X - m * a) ** 2 + (Y - h) ** 2 < core * core
        bad |= (X - m * a - a / 2.0) ** 2 + (Y + h) ** 2 < core * core
    valid = ~(bad[:-1, :-1] | bad[1:, :-1] | bad[1:, 1:] | bad[:-1, 1:])
    ii, jj = np.nonzero(valid)
    return [[[xs[i], ys[j], P[i][j]],
             [xs[i + 1], ys[j], P[i + 1][j]],
             [xs[i + 1], ys[j + 1], P[i + 1][j + 1]],
             [xs[i], ys[j + 1], P[i][j + 1]]]
            for i, j in zip(ii.tolist(), jj.tolist())]


def love(nx=170, nz=120, x1=6.2832, z1=3.0, H=1.0, b1=1.0, b2=1.4,
         mu1=1.0, mu2=2.0, kH=4.0, zscale=1.0):
    """Love 波高度场：低速层覆盖半空间的 SH 面波（Love 1911）。

    传播沿 x，深度 z 向下；位移 u_y = v(z)·cos(kx)（水平横向极化）。
    层内 (0<z<H) v=cos(κ₁z)（应力自由面 v'(0)=0），半空间 v=cos(κ₁H)e^{−κ₂(z−H)}；
    频散方程 μ₁κ₁tan(κ₁H)=μ₂κ₂，κ₁=√(ω²/β₁²−k²)、κ₂=√(k²−ω²/β₂²)，基模 κ₁H∈(0,π/2)。
    相速度 c 由二分精解；界面处 v 连续、斜率按 μ₂/μ₁ 跳变（剪应力连续）。
    """
    k = kH / H

    def kappa(c):
        k1 = math.sqrt(max((c * k / b1) ** 2 - k * k, 0.0))
        k2 = math.sqrt(max(k * k - (c * k / b2) ** 2, 0.0))
        return k1, k2

    def disp(c):
        k1, k2 = kappa(c)
        return mu1 * k1 * math.tan(k1 * H) - mu2 * k2

    c_hi = b1 * math.sqrt(1.0 + (math.pi / (2.0 * kH)) ** 2)   # κ₁H=π/2 处 tan 发散
    lo, hi = b1 * (1.0 + 1e-12), c_hi * (1.0 - 1e-12)
    for _ in range(90):
        mid = 0.5 * (lo + hi)
        if disp(lo) * disp(mid) <= 0:
            hi = mid
        else:
            lo = mid
    c = 0.5 * (lo + hi)
    k1, k2 = kappa(c)
    cH = math.cos(k1 * H)

    def vprof(z):
        return np.where(z <= H, np.cos(k1 * z), cH * np.exp(-k2 * (z - H)))

    xs = np.linspace(0.0, x1, nx).tolist()
    zs = np.linspace(0.0, z1, nz).tolist()
    X, Z = np.meshgrid(np.asarray(xs), np.asarray(zs), indexing='ij')
    U = (vprof(Z) * np.cos(k * X) * zscale).tolist()
    return [[[xs[i], zs[j], U[i][j]],
             [xs[i + 1], zs[j], U[i + 1][j]],
             [xs[i + 1], zs[j + 1], U[i + 1][j + 1]],
             [xs[i], zs[j + 1], U[i][j + 1]]]
            for i in range(nx - 1) for j in range(nz - 1)]


def prandtl_meyer(nx=180, ny=140, x0=-2.0, x1=4.0, y0=-1.5, y1=3.0,
                  M1=2.0, thw=None, gamma=1.4, rcore=0.15, zscale=2.0):
    """Prandtl-Meyer 膨胀波高度场：超音速流绕凸角偏转的中心简单波（M 场）。

    来流 M₁ 沿 +x，壁面在原点外折 θ_w（凸角）；膨胀扇自原点发出，
    前缘特征线 φ₁=μ₁=arcsin(1/M₁)，后缘 φ₂=μ₂−θ_w；扇内等熵无旋精确解：
        ν(M)=ν(M₁)−θ,  φ=θ+μ(M)  （θ 为流向偏转角，μ 为 Mach 角）
    对 M∈[M₁,M₂] 单调 ⇒ 逐点向量二分；扇外为均匀区 M₁/M₂。
    壁体（x<0,y<0 与 x>0,y<−x·tanθ_w）及角点 r<rcore 奇异域不出面。
    高度 z=(M−M₁)·zscale：上游平台→扇内斜坡→下游平台，等 M 线为过角点的射线。
    """
    if thw is None:
        thw = math.radians(20.0)
    g1 = (gamma - 1.0) / 2.0

    def nu(M):
        return (math.sqrt((gamma + 1.0) / (gamma - 1.0))
                * np.arctan(np.sqrt(g1 / (g1 + 1.0) * (M * M - 1.0)))
                - np.arctan(np.sqrt(M * M - 1.0)))

    nu1 = float(nu(np.array(M1)))
    lo, hi = M1, 12.0
    for _ in range(80):                       # ν(M₂)=ν₁+θ_w
        mid = 0.5 * (lo + hi)
        if float(nu(np.array(mid))) < nu1 + thw:
            lo = mid
        else:
            hi = mid
    M2 = 0.5 * (lo + hi)
    phi1 = math.asin(1.0 / M1)
    phi2 = math.asin(1.0 / M2) - thw

    def phi_of_M(M):
        return nu1 - nu(M) + np.arcsin(1.0 / M)

    xs = np.linspace(x0, x1, nx)
    ys = np.linspace(y0, y1, ny)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    R = np.sqrt(X * X + Y * Y)
    PHI = np.arctan2(Y, X)
    target = np.clip(PHI, phi2, phi1)
    blo, bhi = np.full(X.shape, M1), np.full(X.shape, M2)
    for _ in range(48):                       # 向量二分: phi_of_M 单调减 ⇒ cond 真则根在右
        mid = 0.5 * (blo + bhi)
        cond = phi_of_M(mid) > target
        blo = np.where(cond, mid, blo)
        bhi = np.where(cond, bhi, mid)
    M = 0.5 * (blo + bhi)
    M = np.where(PHI > phi1, M1, M)
    M = np.where(PHI < phi2, M2, M)

    body = ((X < 0) & (Y < 0)) | ((X >= 0) & (Y < -X * math.tan(thw)))
    bad = body | (R < rcore)
    Z = ((M - M1) * zscale).tolist()
    xl, yl = xs.tolist(), ys.tolist()
    valid = ~(bad[:-1, :-1] | bad[1:, :-1] | bad[1:, 1:] | bad[:-1, 1:])
    ii, jj = np.nonzero(valid)
    return [[[xl[i], yl[j], Z[i][j]],
             [xl[i + 1], yl[j], Z[i + 1][j]],
             [xl[i + 1], yl[j + 1], Z[i + 1][j + 1]],
             [xl[i], yl[j + 1], Z[i][j + 1]]]
            for i, j in zip(ii.tolist(), jj.tolist())]


def rayleigh_taylor(nx=160, ny=140, x1=6.283185307179586, y1=2.0, k=2.0, g=1.0,
                    rho1=1.0, rho2=2.0, eta0=0.2, zscale=3.0):
    """Rayleigh-Taylor 界面线性失稳模高度场：重流体在上（ρ₂>ρ₁）。

    界面 η=η₀cos(kx)e^{nt}，n²=gk(ρ₂−ρ₁)/(ρ₁+ρ₂)=gkA（A>0 指数失稳）；
    深流体极限下扰动流函数 φ=∓(nη₀/k)e^{∓ky}cos(kx)（两区调和），
    垂直速度 w=∂φ/∂y=nη₀e^{−k|y|}cos(kx)：界面连续、∂w/∂y 按 ±k 跳变（折角）。
    高度场=w(x,y)·zscale。
    """
    A = (rho2 - rho1) / (rho1 + rho2)
    n = math.sqrt(g * k * A)
    xs = np.linspace(0.0, x1, nx).tolist()
    ys = np.linspace(-y1, y1, ny).tolist()
    X, Y = np.meshgrid(np.asarray(xs), np.asarray(ys), indexing='ij')
    W = (n * eta0 * np.exp(-k * np.abs(Y)) * np.cos(k * X) * zscale).tolist()
    return [[[xs[i], ys[j], W[i][j]],
             [xs[i + 1], ys[j], W[i + 1][j]],
             [xs[i + 1], ys[j + 1], W[i + 1][j + 1]],
             [xs[i], ys[j + 1], W[i][j + 1]]]
            for i in range(nx - 1) for j in range(ny - 1)]


def n_wave(nx=200, nt=120, x0=-1.0, x1=7.0, t0=1.0, t1=4.0,
           c=1.0, beta=1.0, a=1.0, zscale=1.0):
    """Sonic boom N 波高度场：无黏 Burgers u_t+cu_x+βuu_x=0 的自相似弱解。

    u=(x−ct)/(βt)（|x−ct|<a√t），头尾激波在 x=ct±a√t（RH 速率为 c+a/(2√t)）；
    幅值 ∝t^{−1/2}、宽度 ∝t^{1/2}（∫|u|dξ=a²/β 守恒）、零均值。
    高度场=u(x,t)·zscale：N 形斜坡随时间展宽衰灭。
    """
    xs = np.linspace(x0, x1, nx).tolist()
    ts = np.linspace(t0, t1, nt).tolist()
    X, T = np.meshgrid(np.asarray(xs), np.asarray(ts), indexing='ij')
    XI = X - c * T
    U = np.where(np.abs(XI) < a * np.sqrt(T), XI / (beta * T), 0.0) * zscale
    Ul = U.tolist()
    return [[[xs[i], ts[j], Ul[i][j]],
             [xs[i + 1], ts[j], Ul[i + 1][j]],
             [xs[i + 1], ts[j + 1], Ul[i + 1][j + 1]],
             [xs[i], ts[j + 1], Ul[i][j + 1]]]
            for i in range(nx - 1) for j in range(nt - 1)]


def oblique_shock(nx=170, ny=140, x0=0.3, x1=4.0, y1=2.6, M1=2.5,
                  thw=0.2617993877991494, gamma=1.4, zscale=1.0):
    """斜激波高度场：超音速流遇凹角（楔角 θ_w）产生的附着斜激波（弱解）。

    θ-β-M 关系 tanθ=2cotβ(M₁²sin²β−1)/(M₁²(γ+cos2β)+2) 扫描+二分精解弱解 β；
    压强比 p₂/p₁=1+2γ/(γ+1)(M₁²sin²β−1)；高度场=(p/p₁−1)·zscale：
    激波线 y=x·tanβ 上游 0、下游台阶（悬崖即激波）；楔体 y<x·tanθ_w 与跨激波格不出面。
    """
    mu1 = math.asin(1.0 / M1)

    def tbm(b):
        return (2.0 / math.tan(b) * (M1 * M1 * math.sin(b) ** 2 - 1.0)
                / (M1 * M1 * (gamma + math.cos(2 * b)) + 2.0) - math.tan(thw))

    nb = 4000
    bs = [mu1 + 1e-9 + k * (math.pi / 2 - 1e-9 - mu1 - 1e-9) / nb for k in range(nb + 1)]
    vs = [tbm(b) for b in bs]
    beta = None
    for k in range(nb):
        if vs[k] < 0 < vs[k + 1]:
            lo, hi = bs[k], bs[k + 1]
            for _ in range(80):
                mid = 0.5 * (lo + hi)
                if tbm(lo) * tbm(mid) <= 0:
                    hi = mid
                else:
                    lo = mid
            beta = 0.5 * (lo + hi)
            break
    if beta is None:
        raise ValueError('θ 超脱体角，无附着斜激波')
    P21 = 1.0 + 2 * gamma / (gamma + 1) * (M1 * M1 * math.sin(beta) ** 2 - 1)
    tb, tw = math.tan(beta), math.tan(thw)
    xs = np.linspace(x0, x1, nx)
    ys = np.linspace(0.0, y1, ny)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    Z = np.where(Y < X * tb, P21 - 1.0, 0.0) * zscale
    body = Y < X * tw
    cross = (Y - X * tb)
    sgn = np.sign(cross)
    bad = (body[:-1, :-1] | body[1:, :-1] | body[1:, 1:] | body[:-1, 1:]) \
        | (sgn[:-1, :-1] != sgn[1:, :-1]) | (sgn[:-1, :-1] != sgn[1:, 1:]) \
        | (sgn[:-1, :-1] != sgn[:-1, 1:])
    Zl = Z.tolist()
    xl, yl = xs.tolist(), ys.tolist()
    ii, jj = np.nonzero(~bad)
    return [[[xl[i], yl[j], Zl[i][j]],
             [xl[i + 1], yl[j], Zl[i + 1][j]],
             [xl[i + 1], yl[j + 1], Zl[i + 1][j + 1]],
             [xl[i], yl[j + 1], Zl[i][j + 1]]]
            for i, j in zip(ii.tolist(), jj.tolist())]


def _gn_acc(h, hx, h0, g, c):
    """稳态 Serre 第一积分解出 h_xx（关于 (h,h_x) 的自治 ODE）"""
    return (3.0 * (h - h0) / (h0 * h)
            - 3.0 * g * (h * h - h0 * h0) / (2.0 * c * c * h0 * h0)
            + 1.5 * hx * hx / h)


def _gn_shoot(h0, a, g, c, xmax=25.0, dx=2e-3):
    """从波峰 (h=h0+a, h_x=0) RK4 积分到 xmax，返回 h(xmax)−h0（同宿轨道打靶）"""
    h, hx = h0 + a, 0.0
    n = int(xmax / dx)
    tmin = 0.0
    for i in range(n):
        k1h, k1v = hx, _gn_acc(h, hx, h0, g, c)
        k2h, k2v = hx + dx / 2 * k1v, _gn_acc(h + dx / 2 * k1h, hx + dx / 2 * k1v, h0, g, c)
        k3h, k3v = hx + dx / 2 * k2v, _gn_acc(h + dx / 2 * k2h, hx + dx / 2 * k2v, h0, g, c)
        k4h, k4v = hx + dx * k3v, _gn_acc(h + dx * k3h, hx + dx * k3v, h0, g, c)
        h += dx / 6 * (k1h + 2 * k2h + 2 * k3h + k4h)
        hx += dx / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)
        if h < h0 * 0.5 or h > h0 + 5 * a:
            return -1.0
        if i > n // 2:
            tmin = min(tmin, h - h0)
    return tmin


def _gn_profile(h0=1.0, a=0.3, g=1.0, xmax=25.0, dx=2e-3):
    """GN/Serre 精确孤波剖面（磁盘缓存）：对 c 二分打靶同宿轨道。
    返回 (xs, eta, c)；xs∈[−xmax, xmax] 对称格。"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'cache_gn_%g_%g.npy' % (h0, a))
    if os.path.exists(path):
        arr = np.load(path)
        return arr[0], arr[1], float(arr[2, 0])
    ck = math.sqrt(g * h0) * (1 + a / (2 * h0))          # KdV 速度（下界候选）
    lo, hi = ck * 0.98, math.sqrt(g * (h0 + a)) * 1.02
    flo, fhi = _gn_shoot(h0, a, g, lo, xmax, dx), _gn_shoot(h0, a, g, hi, xmax, dx)
    if flo * fhi > 0:                                     # 括号失败则外扩
        lo, hi = ck * 0.9, math.sqrt(g * (h0 + a)) * 1.1
        flo, fhi = _gn_shoot(h0, a, g, lo, xmax, dx), _gn_shoot(h0, a, g, hi, xmax, dx)
    for _ in range(48):
        mid = 0.5 * (lo + hi)
        fm = _gn_shoot(h0, a, g, mid, xmax, dx)
        if flo * fm <= 0:
            hi = mid
        else:
            lo, flo = mid, fm
    c = 0.5 * (lo + hi)
    # 存全剖面：自波峰积分右半，偶对称拼左半（孤波关于波峰偶）
    h, hx = h0 + a, 0.0
    n = int(xmax / dx)
    right = [a]
    for _ in range(n):
        k1h, k1v = hx, _gn_acc(h, hx, h0, g, c)
        k2h, k2v = hx + dx / 2 * k1v, _gn_acc(h + dx / 2 * k1h, hx + dx / 2 * k1v, h0, g, c)
        k3h, k3v = hx + dx / 2 * k2v, _gn_acc(h + dx / 2 * k2h, hx + dx / 2 * k2v, h0, g, c)
        k4h, k4v = hx + dx * k3v, _gn_acc(h + dx * k3h, hx + dx * k3v, h0, g, c)
        h += dx / 6 * (k1h + 2 * k2h + 2 * k3h + k4h)
        hx += dx / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)
        right.append(h - h0)
    right = np.array(right)
    eta = np.concatenate([right[:0:-1], right])      # x=−xmax..xmax, 2n+1 点
    xs = np.linspace(-xmax, xmax, 2 * n + 1)
    np.save(path, np.vstack([xs, eta, np.full_like(xs, c)]))
    return xs, eta, c


def gn_solitary(nx=200, nt=120, x0=-6.0, x1=10.0, t1=4.0,
                h0=1.0, a=0.3, g=1.0, zscale=1.0):
    """Green-Naghdi/Serre 浅水孤波高度场 η(x−ct)：稳态第一积分 ODE 的同宿轨道
    （对 c 二分打靶，磁盘缓存），非 sech² 近似；KdV 小幅极限→sech²。
    """
    xs_p, eta_p, c = _gn_profile(h0, a, g)
    xs = np.linspace(x0, x1, nx).tolist()
    ts = np.linspace(0.0, t1, nt).tolist()
    X, T = np.meshgrid(np.asarray(xs), np.asarray(ts), indexing='ij')
    E = (np.interp(X - c * T, xs_p, eta_p) * zscale).tolist()
    return [[[xs[i], ts[j], E[i][j]],
             [xs[i + 1], ts[j], E[i + 1][j]],
             [xs[i + 1], ts[j + 1], E[i + 1][j + 1]],
             [xs[i], ts[j + 1], E[i][j + 1]]]
            for i in range(nx - 1) for j in range(nt - 1)]


def burgers_tw(nx=200, nt=120, x0=-3.0, x1=5.0, t1=4.0,
               u1=1.0, u2=-0.5, nu=0.05, zscale=1.0):
    """黏性 Burgers 行波（Taylor 激波剖面）高度场 u(x,t)。

    u_t+uu_x=νu_xx 精确行波解：u=u₂+(u₁−u₂)/(1+e^{(u₁−u₂)(x−st)/(2ν)})，
    s=(u₁+u₂)/2 恰为无黏 RH 速率（黏性剖面选出熵满足激波）；厚度 ∝ν/(u₁−u₂)；
    Cole-Hopf u=−2ν∂ₓlnφ 恒等。高度场=u(x,t)：平移的扩散激波front。
    """
    s = (u1 + u2) / 2.0
    xs = np.linspace(x0, x1, nx).tolist()
    ts = np.linspace(0.0, t1, nt).tolist()
    X, T = np.meshgrid(np.asarray(xs), np.asarray(ts), indexing='ij')
    U = (u2 + (u1 - u2) / (1.0 + np.exp((u1 - u2) * (X - s * T) / (2 * nu)))
         ) * zscale
    Ul = U.tolist()
    return [[[xs[i], ts[j], Ul[i][j]],
             [xs[i + 1], ts[j], Ul[i + 1][j]],
             [xs[i + 1], ts[j + 1], Ul[i + 1][j + 1]],
             [xs[i], ts[j + 1], Ul[i][j + 1]]]
            for i in range(nx - 1) for j in range(nt - 1)]


def _serre_rhs(h, u, dx, g, lu_factor):
    """Serre/GN 右端：椭圆正则化 u_t + uu_x + gh_x = −(1/h)∂ₓ[(h³/3)(u_xt+uu_xx−u_x²)]。
    每步解 (I − (1/h)∂(h³/3 ₓ·))A = RHS_base 得 A=u_t（三对角）。"""
    from scipy.linalg import solve_banded
    n = h.size
    hx = np.gradient(h, dx)
    ux = np.gradient(u, dx)
    uxx = np.gradient(ux, dx)
    G = u * uxx - 0.5 * ux * ux
    K = (h ** 3) / 3.0
    Kh = 0.5 * (K[1:] + K[:-1])                       # 半节点
    rhs = -u * ux - g * hx - np.gradient(K * G, dx) / h
    ab = np.zeros((3, n))
    ab[1, 1:-1] = 1.0 + (Kh[:-1] + Kh[1:]) / (h[1:-1] * dx * dx)
    ab[0, 2:] = -Kh[1:] / (h[1:-1] * dx * dx)           # 上对角: 行 i 的 A_{i+1} 系数
    ab[2, :-2] = -Kh[:-1] / (h[1:-1] * dx * dx)          # 下对角: 行 i 的 A_{i-1} 系数
    ab[1, 0] = ab[1, -1] = 1.0                          # Dirichlet A=0 远场
    A = solve_banded((1, 1), ab, rhs)
    dh = -np.gradient(h * u, dx)
    return dh, A


def _gn_bore_solve(x0=-30.0, x1=60.0, N=1200, T=20.0, dt=0.01,
                   hL=1.3, hR=1.0, g=1.0, save_every=40):
    """Serre 方程台阶初值（左深右浅）→ undular bore；缓存 (xs, ts, H)。"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache_gnbore.npy')
    if os.path.exists(path):
        arr = np.load(path)
        N = int(arr[0])
        M = int(arr[1])
        return arr[2:2 + N], arr[2 + N:2 + N + M], arr[2 + N + M:].reshape(M, N)
    from scipy.linalg import solve_banded  # noqa: F401  (确保依赖存在)
    xs = np.linspace(x0, x1, N)
    dx = xs[1] - xs[0]
    h = np.where(xs < 0, hL, hR).copy()
    u = np.zeros_like(h)
    nsteps = int(T / dt)
    ts, frames = [], []
    for step in range(nsteps + 1):
        if step % save_every == 0:
            ts.append(step * dt)
            frames.append(h.copy())
        if step == nsteps:
            break
        d1h, d1u = _serre_rhs(h, u, dx, g, None)
        h1, u1 = h + dt * d1h, u + dt * d1u
        d2h, d2u = _serre_rhs(h1, u1, dx, g, None)
        h2, u2 = 0.75 * h + 0.25 * (h1 + dt * d2h), 0.75 * u + 0.25 * (u1 + dt * d2u)
        d3h, d3u = _serre_rhs(h2, u2, dx, g, None)
        h = h / 3 + 2 / 3 * (h2 + dt * d3h)
        u = u / 3 + 2 / 3 * (u2 + dt * d3u)
    H = np.array(frames)
    np.save(path, np.concatenate([np.array([h.size, len(ts)]), xs, np.array(ts),
                                  H.ravel()]))
    return xs, np.array(ts), H


def gn_bore(nx=200, nt=50, x0=-30.0, x1=60.0, T=20.0, hL=1.3, hR=1.0,
            g=1.0, zscale=2.0):
    """GN/Serre undular bore（色散冲击波）高度场 h(x,t)−h_R：台阶初值数值解本体。
    前缘为 GN 孤波列（领先孤波速=同宿打靶 c），后缘线性色散边；缓存 cache_gnbore.npy。"""
    xs, ts, H = _gn_bore_solve(x0, x1, 1200, T, 0.01, hL, hR, g, 40)
    stride = max(1, len(xs) // nx)
    X = xs[::stride]
    Hs = H[::max(1, len(ts) // nt), ::stride]
    Tsub = ts[::max(1, len(ts) // nt)]
    Z = ((Hs - hR) * zscale).tolist()
    xl, tl = X.tolist(), Tsub.tolist()
    ni, nj = len(xl), len(tl)
    return [[[xl[i], tl[j], Z[j][i]],
             [xl[i + 1], tl[j], Z[j][i + 1]],
             [xl[i + 1], tl[j + 1], Z[j + 1][i + 1]],
             [xl[i], tl[j + 1], Z[j + 1][i]]]
            for i in range(ni - 1) for j in range(nj - 1)]


def sw_rarefaction(nx=200, nt=120, x0=-3.0, x1=3.0, t0=0.5, t1=3.0,
                   g=1.0, hL=1.0, hR=0.25, zscale=1.0):
    """浅水 dam-break 稀疏波（中心简单波扇）高度场 h(x,t)。

    Riemann 初值在 1-族稀疏波曲线上（u_R=u_L+2(c_L−c_R)）⇒ 纯中心稀疏波：
    扇内 ξ=x/t=u−c 且 u+2c=I=u_L+2c_L ⇒ c=(I−ξ)/3, u=(2ξ+I)/3, h=c²/g；
    扇边 ξ₁=u_L−c_L、ξ₂=u_R−c_R 外为平台。与 bore 互为镜像：连续扇 vs 激波跳变。
    """
    cL, cR = math.sqrt(g * hL), math.sqrt(g * hR)
    uL = 0.0
    uR = uL + 2 * (cL - cR)
    I = uL + 2 * cL
    xi1, xi2 = uL - cL, uR - cR
    xs = np.linspace(x0, x1, nx).tolist()
    ts = np.linspace(t0, t1, nt).tolist()
    X, T = np.meshgrid(np.asarray(xs), np.asarray(ts), indexing='ij')
    XI = X / T
    c = np.where(XI < xi1, cL, np.where(XI > xi2, cR, (I - XI) / 3.0))
    H = (c * c / g * zscale).tolist()
    return [[[xs[i], ts[j], H[i][j]],
             [xs[i + 1], ts[j], H[i + 1][j]],
             [xs[i + 1], ts[j + 1], H[i + 1][j + 1]],
             [xs[i], ts[j + 1], H[i][j + 1]]]
            for i in range(nx - 1) for j in range(nt - 1)]


def _cnoidal_params(A=0.8, B=0.0, m=0.7):
    """KdV u_t+6uu_x+u_xxx=0 的 cnoidal 行波 u=B+A·cn²(k(x−ct),m) 闭式参数：
    C² 项平衡 ⇒ k²=A/(2m)；C¹ 项 ⇒ c=6B+4A−2A/m（m→1 退孤子 k²=A/2, c=6B+2A）。"""
    k = math.sqrt(A / (2.0 * m))
    c = 6.0 * B + 4.0 * A - 2.0 * A / m
    return float(k), float(c)


def kdv_cnoidal(nx=220, nt=120, x0=0.0, x1=12.0, t1=6.0,
                A=0.8, B=0.0, m=0.7, zscale=1.0):
    """KdV cnoidal 波高度场 u(x,t)=B+A·cn²(k(x−ct),m)——Whitham 调制理论的载波。
    (k,c) 由 _cnoidal_params 数值精解；m→1 退孤子 sech²、m→0 退余弦。
    """
    from scipy.special import ellipj
    k, c = _cnoidal_params(A, B, m)
    xs = np.linspace(x0, x1, nx).tolist()
    ts = np.linspace(0.0, t1, nt).tolist()
    X, T = np.meshgrid(np.asarray(xs), np.asarray(ts), indexing='ij')
    U = ((B + A * ellipj(k * (X - c * T), m)[1] ** 2) * zscale).tolist()
    return [[[xs[i], ts[j], U[i][j]],
             [xs[i + 1], ts[j], U[i + 1][j]],
             [xs[i + 1], ts[j + 1], U[i + 1][j + 1]],
             [xs[i], ts[j + 1], U[i][j + 1]]]
            for i in range(nx - 1) for j in range(nt - 1)]


GENS = {'geodesic': geodesic, 'bezier_tri': bezier_tri,
        'terrain': terrain, 'sph_tri_patch': sph_tri_patch, 'drum': drum,
        'fdtd': fdtd, 'gray_scott': gray_scott, 'flow_cyl': flow_cyl,
        'blasius': blasius, 'karman': karman, 'love': love,
        'prandtl_meyer': prandtl_meyer,
        'rayleigh_taylor': rayleigh_taylor, 'n_wave': n_wave,
        'oblique_shock': oblique_shock, 'gn_solitary': gn_solitary,
        'burgers_tw': burgers_tw, 'gn_bore': gn_bore,
        'sw_rarefaction': sw_rarefaction, 'kdv_cnoidal': kdv_cnoidal}


_SKIP = {'gen', 'name', 'category', 'desc', 'faces_kind'}


def build(spec):
    """spec = {'gen': 名称, 其余为生成器关键字参数} → faces"""
    fn = GENS[spec['gen']]
    return fn(**{k: v for k, v in spec.items() if k not in _SKIP})
