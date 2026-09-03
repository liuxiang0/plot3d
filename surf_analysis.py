#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""surf_analysis.py — 曲面分析工具（教学用途）

对任意多边形网格（引擎 mesh 格式）计算逐顶点微分量:
  法向量（面积加权）· 高斯曲率 K（角亏缺, 内蕴）· 平均曲率 |H|（余切 Laplacian）
并提供: 曲率→色图重着色 · 法向量箭头抽样 · 色图函数
"""
import math


def _angle(p, q, r):
    """顶点 p 处向量 pq 与 pr 的夹角"""
    ax, ay, az = q[0] - p[0], q[1] - p[1], q[2] - p[2]
    bx, by, bz = r[0] - p[0], r[1] - p[1], r[2] - p[2]
    dot = ax * bx + ay * by + az * bz
    cr = math.sqrt((ay * bz - az * by) ** 2 + (az * bx - ax * bz) ** 2
                   + (ax * by - ay * bx) ** 2)
    return math.atan2(cr, dot)


def _cot(ang):
    s = math.sin(ang)
    return math.cos(ang) / s if abs(s) > 1e-12 else 0.0


def _dist2(p, q):
    return (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2


def analyze(meshes):
    """meshes: 引擎网格列表 [[(顶点组, 颜色), ...]]（取首个非空网格）。
    返回 dict: pts 顶点 · normals 单位法向量 · K 高斯曲率 · H 平均曲率模长 ·
               faces 三角形(顶点下标) · span 包围盒对角线"""
    src = next((m for m in meshes if m), [])
    vmap, pts, faces = {}, [], []

    def vid(p):
        key = (round(p[0], 9), round(p[1], 9), round(p[2], 9))
        i = vmap.get(key)
        if i is None:
            i = len(pts)
            vmap[key] = i
            pts.append(p)
        return i

    for P, col in src:                                # 四边形剖分为三角形, 顶点去重
        idx = [vid(p) for p in P]
        if len(idx) == 3:
            faces.append((idx[0], idx[1], idx[2]))
        elif len(idx) == 4:                           # Delaunay 对角线（取短者）减小各向异性偏差
            if _dist2(pts[idx[1]], pts[idx[3]]) < _dist2(pts[idx[0]], pts[idx[2]]):
                faces.append((idx[0], idx[1], idx[3]))
                faces.append((idx[1], idx[2], idx[3]))
            else:
                faces.append((idx[0], idx[1], idx[2]))
                faces.append((idx[0], idx[2], idx[3]))
    n = len(pts)
    if n < 3:
        return None
    normals = [[0.0, 0.0, 0.0] for _ in range(n)]
    angle_sum = [0.0] * n
    varea = [0.0] * n
    HN = [[0.0, 0.0, 0.0] for _ in range(n)]
    edge_cnt = {}
    farea = [0.0] * len(faces)
    for fi, (a, b, c) in enumerate(faces):
        pa, pb, pc = pts[a], pts[b], pts[c]
        ux, uy, uz = pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2]
        vx, vy, vz = pc[0] - pa[0], pc[1] - pa[1], pc[2] - pa[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        area2 = math.sqrt(nx * nx + ny * ny + nz * nz)
        if area2 < 1e-15:                             # 退化三角形（极点收缩等）
            continue
        area = area2 / 2.0
        farea[fi] = area
        for vi, w in ((a, 1.0), (b, 1.0), (c, 1.0)):
            normals[vi][0] += nx
            normals[vi][1] += ny
            normals[vi][2] += nz
        Aa = _angle(pa, pb, pc)
        Ab = _angle(pb, pc, pa)
        Ac = _angle(pc, pa, pb)
        angle_sum[a] += Aa
        angle_sum[b] += Ab
        angle_sum[c] += Ac
        # Voronoi 混合面积 (Meyer 2003): 非钝角用 Voronoi 区域, 钝角用 area/2 与 area/4
        ab2, ac2, bc2 = _dist2(pa, pb), _dist2(pa, pc), _dist2(pb, pc)
        cA, cB, cC = _cot(Aa), _cot(Ab), _cot(Ac)
        # 余切 Laplacian: 每条无向边更新两个端点 HN[i] += cot(对角)·(p_j − p_i)
        for i, j, cot in ((a, b, cC), (a, c, cB), (b, a, cC),
                          (b, c, cA), (c, a, cB), (c, b, cA)):
            pi_, pj = pts[i], pts[j]
            HN[i][0] += cot * (pj[0] - pi_[0])
            HN[i][1] += cot * (pj[1] - pi_[1])
            HN[i][2] += cot * (pj[2] - pi_[2])
        half = math.pi / 2
        if Aa >= half:
            varea[a] += area / 2; varea[b] += area / 4; varea[c] += area / 4
        elif Ab >= half:
            varea[b] += area / 2; varea[a] += area / 4; varea[c] += area / 4
        elif Ac >= half:
            varea[c] += area / 2; varea[a] += area / 4; varea[b] += area / 4
        else:
            varea[a] += (ac2 * cB + ab2 * cC) / 8
            varea[b] += (ab2 * cC + bc2 * cA) / 8
            varea[c] += (bc2 * cA + ac2 * cB) / 8
        for i, j in ((a, b), (b, c), (c, a)):
            edge_cnt[tuple(sorted((i, j)))] = edge_cnt.get(tuple(sorted((i, j))), 0) + 1
    boundary = set()
    for (i, j), c in edge_cnt.items():
        if c == 1:
            boundary.add(i)
            boundary.add(j)
    # 单位法向量
    for i in range(n):
        nx, ny, nz = normals[i]
        nl = math.sqrt(nx * nx + ny * ny + nz * nz)
        normals[i] = (nx / nl, ny / nl, nz / nl) if nl > 1e-15 else (0.0, 0.0, 1.0)
    # 高斯曲率: 角亏缺 / 混合面积（边界点用 π）
    K = [0.0] * n
    for i in range(n):
        if varea[i] > 1e-15:
            target = math.pi if i in boundary else 2.0 * math.pi
            K[i] = (target - angle_sum[i]) / varea[i]
    # 平均曲率: |H| = |Δp|/2, Δp = HN/(2·Voronoi面积)（HN 已在面循环中累加）
    H = [0.0] * n
    for i in range(n):
        if varea[i] > 1e-15:
            hx, hy, hz = (HN[i][0] / (2 * varea[i]), HN[i][1] / (2 * varea[i]),
                          HN[i][2] / (2 * varea[i]))
            H[i] = 0.5 * math.sqrt(hx * hx + hy * hy + hz * hz)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    zs = [p[2] for p in pts]
    span = math.sqrt((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2
                     + (max(zs) - min(zs)) ** 2)
    return {'pts': pts, 'normals': normals, 'K': K, 'H': H,
            'faces': [f for f, a in zip(faces, farea) if a > 0], 'span': span}


# ====================== 可视化 ======================

def colormap(t, kind='diverge'):
    """t∈[0,1] → '#rrggbb'; diverge 蓝-白-红（有符号）, seq 深蓝-青-黄-红（模长）"""
    stops = ([(0.0, (59, 76, 192)), (0.5, (245, 245, 245)), (1.0, (180, 4, 38))]
             if kind == 'diverge' else
             [(0.0, (15, 28, 80)), (0.4, (60, 150, 200)),
              (0.7, (240, 220, 90)), (1.0, (190, 20, 40))])
    t = max(0.0, min(1.0, t))
    for k in range(len(stops) - 1):
        (t0, c0), (t1, c1) = stops[k], stops[k + 1]
        if t <= t1 or k == len(stops) - 2:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            f = max(0.0, min(1.0, f))
            return '#%02x%02x%02x' % tuple(int(c0[i] + (c1[i] - c0[i]) * f)
                                           for i in range(3))


def colorize(geo, field='K'):
    """按曲率场重着色为三角形片; K 对称值域(发散色图), H 取 [0,max]。
    返回 (三角形片列表, (值域下界, 上界))"""
    vals = geo[field]
    if field == 'K':
        m = max(abs(min(vals)), abs(max(vals)), 1e-12)
        lo, hi, kind = -m, m, 'diverge'
    else:
        lo, hi, kind = 0.0, max(max(vals), 1e-12), 'seq'
    tris = []
    for a, b, c in geo['faces']:
        v = (vals[a] + vals[b] + vals[c]) / 3.0
        tris.append(((geo['pts'][a], geo['pts'][b], geo['pts'][c]),
                     colormap((v - lo) / (hi - lo), kind)))
    return tris, (lo, hi)


def normal_arrows(geo, max_arrows=160):
    """抽样法向量箭头: [(起点, 终点)]"""
    pts, normals = geo['pts'], geo['normals']
    stride = max(1, len(pts) // max_arrows)
    L = geo['span'] * 0.08
    return [(pts[i], tuple(pts[i][k] + normals[i][k] * L for k in range(3)))
            for i in range(0, len(pts), stride)]


def _solve_lin(A, b):
    """解 n×n 线性方程组 A x = b（高斯消去选主元）; 奇异返回 None"""
    n = len(A)
    M = [A[i][:] + [b[i]] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-13:
            return None
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        for r in range(n):
            if r != col:
                f = M[r][col] / pv
                if f:
                    for c in range(col, n + 1):
                        M[r][c] -= f * M[col][c]
    return [M[i][n] / M[i][i] for i in range(n)]


def principal_dirs(geo, rings=2):
    """逐顶点主曲率与主方向: 局部二次曲面片拟合（5 参数最小二乘, 2-ring 邻域）。
    返回 dict: k1,k2（主曲率, k1≥k2）· d1,d2（三维单位方向, 无效处为 None）"""
    pts, normals, faces = geo['pts'], geo['normals'], geo['faces']
    n = len(pts)
    adj = [set() for _ in range(n)]
    for a, b, c in faces:
        adj[a].update((b, c))
        adj[b].update((a, c))
        adj[c].update((a, b))
    nbr = [set(adj[i]) for i in range(n)]
    if rings >= 2:
        for i in range(n):
            ext = set()
            for j in nbr[i]:
                ext.update(adj[j])
            ext.discard(i)
            nbr[i] = ext
    k1 = [0.0] * n
    k2 = [0.0] * n
    d1 = [None] * n
    d2 = [None] * n
    for i in range(n):
        ni = normals[i]
        ref = (1.0, 0.0, 0.0) if abs(ni[0]) < 0.9 else (0.0, 1.0, 0.0)
        ux = ni[1] * ref[2] - ni[2] * ref[1]          # u = ni × ref
        uy = ni[2] * ref[0] - ni[0] * ref[2]
        uz = ni[0] * ref[1] - ni[1] * ref[0]
        ul = math.sqrt(ux * ux + uy * uy + uz * uz) or 1.0
        ux, uy, uz = ux / ul, uy / ul, uz / ul
        vx = ni[1] * uz - ni[2] * uy                  # v = ni × u
        vy = ni[2] * ux - ni[0] * uz
        vz = ni[0] * uy - ni[1] * ux
        ATA = [[0.0] * 5 for _ in range(5)]           # 法方程 5×5
        ATb = [0.0] * 5
        cnt = 0
        pi = pts[i]
        for j in nbr[i]:
            dp = (pts[j][0] - pi[0], pts[j][1] - pi[1], pts[j][2] - pi[2])
            uu = dp[0] * ux + dp[1] * uy + dp[2] * uz
            vv = dp[0] * vx + dp[1] * vy + dp[2] * vz
            ww = dp[0] * ni[0] + dp[1] * ni[1] + dp[2] * ni[2]
            row = (uu, vv, uu * uu, uu * vv, vv * vv)
            for r in range(5):
                ATb[r] += row[r] * ww
                for c in range(5):
                    ATA[r][c] += row[r] * row[c]
            cnt += 1
        if cnt < 6:
            continue
        coef = _solve_lin(ATA, ATb)
        if coef is None:
            continue
        # Hessian [[2c, d], [d, 2e]] → 主曲率 = 特征值
        mA, mB, mD = 2.0 * coef[2], coef[3], 2.0 * coef[4]
        tr = mA + mD
        disc = math.sqrt(max(0.0, tr * tr / 4.0 - (mA * mD - mB * mB)))
        lam1, lam2 = tr / 2.0 + disc, tr / 2.0 - disc
        if abs(mB) > 1e-12:
            e1 = (mB, lam1 - mA)
        elif mA >= mD:
            e1 = (1.0, 0.0)
        else:
            e1 = (0.0, 1.0)
        el = math.hypot(e1[0], e1[1]) or 1.0
        e1 = (e1[0] / el, e1[1] / el)
        e2 = (-e1[1], e1[0])
        k1[i], k2[i] = lam1, lam2
        d1[i] = (e1[0] * ux + e1[1] * vx, e1[0] * uy + e1[1] * vy,
                 e1[0] * uz + e1[1] * vz)
        d2[i] = (e2[0] * ux + e2[1] * vx, e2[0] * uy + e2[1] * vy,
                 e2[0] * uz + e2[1] * vz)
    return {'k1': k1, 'k2': k2, 'd1': d1, 'd2': d2}
