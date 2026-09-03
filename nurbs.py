#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nurbs.py — Bézier / B 样条 / NURBS 数学核心（第四阶段）

约定 (Piegl & Tiller): n+1 个控制点 P_0..P_n, 次数 p, 节点向量 U 长 n+p+2, 两端钳位;
有理式使用权重 W (默认 1)。Bézier = p=n 的单段特例, 统一管线。
含: 基函数 · 曲线/曲面求值 · 全局插值(自动拟合) · 精确有理圆 · 曲面预设 · 点列解析
"""
import copy
import math
import re

import mathparse

LIGHT = (-0.45, -0.55, 0.75)


# ====================== 基函数与节点 ======================

def find_span(n, p, u, U):
    """定位 u 所在的节点区间 (A2.1)"""
    if u >= U[n + 1]:
        return n
    if u <= U[p]:
        return p
    lo, hi = p, n + 1
    mid = (lo + hi) // 2
    while u < U[mid] or u >= U[mid + 1]:
        if u < U[mid]:
            hi = mid
        else:
            lo = mid
        mid = (lo + hi) // 2
    return mid


def basis_funs(i, u, p, U):
    """返回 N_{i-p,p}(u)..N_{i,p}(u) 共 p+1 个基函数值 (A2.2)"""
    N = [1.0] + [0.0] * p
    left = [0.0] * (p + 1)
    right = [0.0] * (p + 1)
    for j in range(1, p + 1):
        left[j] = u - U[i + 1 - j]
        right[j] = U[i + j] - u
        saved = 0.0
        for r in range(j):
            denom = right[r + 1] + left[j - r]
            temp = N[r] / denom if denom else 0.0
            N[r] = saved + right[r + 1] * temp
            saved = left[j - r] * temp
        N[j] = saved
    return N


def clamped_knots(n, p):
    """均匀钳位节点向量（n = 末控制点下标）"""
    if n < p:
        raise ValueError(f'控制点数 ({n + 1}) 不能少于 次数+1 ({p + 1})')
    inner = [k / (n - p + 1) for k in range(1, n - p + 1)]
    return [0.0] * (p + 1) + inner + [1.0] * (p + 1)


# ====================== 曲线 / 曲面 ======================

class Curve:
    def __init__(self, P, W=None, p=3, U=None):
        self.P = [list(map(float, pt)) for pt in P]
        n = len(self.P) - 1
        self.p = min(int(p), n)
        self.W = [float(w) for w in W] if W else [1.0] * len(self.P)
        self.U = ([float(x) for x in U] if U is not None
                  else clamped_knots(n, self.p))

    def point(self, u):
        n = len(self.P) - 1
        span = find_span(n, self.p, u, self.U)
        N = basis_funs(span, u, self.p, self.U)
        num = [0.0, 0.0, 0.0]
        den = 0.0
        for j in range(self.p + 1):
            idx = span - self.p + j
            ww = N[j] * self.W[idx]
            den += ww
            pt = self.P[idx]
            num[0] += ww * pt[0]
            num[1] += ww * pt[1]
            num[2] += ww * pt[2]
        if abs(den) < 1e-14:
            return (math.nan, math.nan, math.nan)
        return (num[0] / den, num[1] / den, num[2] / den)

    def sample(self, count=400):
        return [self.point(i / (count - 1)) for i in range(count)]

    @property
    def rational(self):
        return any(abs(w - 1.0) > 1e-12 for w in self.W)

    def copy(self):
        return copy.deepcopy(self)


class Surface:
    """张量积 NURBS 曲面: P[i][j], W[i][j], u 向次数 p, v 向次数 q"""

    def __init__(self, P, W=None, p=None, q=None, U=None, V=None):
        self.P = [[list(map(float, pt)) for pt in row] for row in P]
        ni, nj = len(self.P), len(self.P[0])
        self.p = min(int(p if p is not None else ni - 1), ni - 1)
        self.q = min(int(q if q is not None else nj - 1), nj - 1)
        self.W = ([[float(w) for w in row] for row in W] if W
                  else [[1.0] * nj for _ in range(ni)])
        self.U = [float(x) for x in U] if U is not None else clamped_knots(ni - 1, self.p)
        self.V = [float(x) for x in V] if V is not None else clamped_knots(nj - 1, self.q)

    def point(self, u, v):
        ni, nj = len(self.P) - 1, len(self.P[0]) - 1
        su = find_span(ni, self.p, u, self.U)
        sv = find_span(nj, self.q, v, self.V)
        Nu = basis_funs(su, u, self.p, self.U)
        Nv = basis_funs(sv, v, self.q, self.V)
        num = [0.0, 0.0, 0.0]
        den = 0.0
        for a in range(self.p + 1):
            i = su - self.p + a
            for b in range(self.q + 1):
                j = sv - self.q + b
                ww = Nu[a] * Nv[b] * self.W[i][j]
                den += ww
                pt = self.P[i][j]
                num[0] += ww * pt[0]
                num[1] += ww * pt[1]
                num[2] += ww * pt[2]
        if abs(den) < 1e-14:
            return (math.nan, math.nan, math.nan)
        return (num[0] / den, num[1] / den, num[2] / den)

    def mesh(self, nu=26, nv=18, base=(148, 210, 200)):
        pts = [[self.point(i / nu, j / nv) for j in range(nv + 1)]
               for i in range(nu + 1)]
        return shade_grid(pts, base)

    @property
    def rational(self):
        return any(abs(w - 1.0) > 1e-12 for row in self.W for w in row)

    def copy(self):
        return copy.deepcopy(self)


def _norm(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / n for c in v)


def shade_grid(pts, base=(148, 210, 200), max_edge=None):
    """网格点 → Lambert 着色四边形片 [((p0..p3), '#rrggbb')];
    max_edge: 边长超过该值的面片剔除（处理接缝/奇点跳跃）"""
    Lx, Ly, Lz = _norm(LIGHT)
    m2 = max_edge * max_edge if max_edge else None
    quads = []
    for i in range(len(pts) - 1):
        for j in range(len(pts[0]) - 1):
            P = (pts[i][j], pts[i + 1][j], pts[i + 1][j + 1], pts[i][j + 1])
            if any(not all(math.isfinite(c) for c in p) for p in P):
                continue
            if m2 and any((P[(k + 1) % 4][0] - P[k][0]) ** 2
                          + (P[(k + 1) % 4][1] - P[k][1]) ** 2
                          + (P[(k + 1) % 4][2] - P[k][2]) ** 2 > m2
                          for k in range(4)):
                continue
            ux, uy, uz = P[1][0] - P[0][0], P[1][1] - P[0][1], P[1][2] - P[0][2]
            vx, vy, vz = P[3][0] - P[0][0], P[3][1] - P[0][1], P[3][2] - P[0][2]
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            b = 0.32 + 0.68 * abs(nx * Lx + ny * Ly + nz * Lz) / nl
            quads.append((P, '#%02x%02x%02x' % (int(base[0] * b),
                                                int(base[1] * b),
                                                int(base[2] * b))))
    return quads


# ====================== 自动构造 ======================

def bezier_curve(points):
    """Bézier 曲线（次数 = 控制点数−1）"""
    return Curve(points, p=len(points) - 1)


def bezier_surface(grid):
    return Surface(grid)


def circle(r=1.0, z=0.0):
    """精确有理圆: 4 段 90° 二次有理弧, 权重 √2/2（多项式曲线无法精确表示圆）"""
    s = math.sqrt(2.0) / 2.0
    P = [(r, 0, z), (r, r, z), (0, r, z), (-r, r, z), (-r, 0, z),
         (-r, -r, z), (0, -r, z), (r, -r, z), (r, 0, z)]
    W = [1.0, s, 1.0, s, 1.0, s, 1.0, s, 1.0]
    U = [0, 0, 0, 0.25, 0.25, 0.5, 0.5, 0.75, 0.75, 1, 1, 1]
    return Curve(P, W, 2, U)


def cylinder_arch(r=1.4, length=2.0, z0=0.0):
    """精确有理半圆柱拱壳: 180° 圆弧(2 段有理弧) × 直线母线"""
    s = math.sqrt(2.0) / 2.0
    arc = [(r, 0), (r, r), (0, r), (-r, r), (-r, 0)]
    w = [1.0, s, 1.0, s, 1.0]
    zs = (z0, z0 + length / 2.0, z0 + length)
    P = [[(x, y, z) for z in zs] for (x, y) in arc]
    W = [[wi] * 3 for wi in w]
    srf = Surface(P, W, p=2, q=2)
    srf.U = [0, 0, 0, 0.5, 0.5, 1, 1, 1]     # 双节点 → 两段 Bézier 弧拼接
    return srf


# ====================== 著名案例（样条库扩充） ======================

def surface_of_revolution(profile_pts, profile_w, p, U=None):
    """把 (r,z) 平面母线控制多边形绕 z 轴旋转 → **精确有理旋转面**。
    周向用 4 段有理圆弧(外接正方形控制点, 权重 √2/2), 旋转精确无近似;
    球面/环面/高脚杯/花瓶等经典 NURBS 案例的统一构造器。
    profile_pts: [(r0,z0),...] (r=到轴距离, 允许 0); p=母线次数;
    U=母线节点向量(必须透传, 否则有理圆弧的双节点丢失 → 不再精确)"""
    s = math.sqrt(2.0) / 2.0
    # 单位圆 9 个控制点(外接正方形角点在 ±45° 半径 √2) + 权重, 与 circle() 一致
    cw = [(1.0, 0.0, 1.0), (1.0, 1.0, s), (0.0, 1.0, 1.0), (-1.0, 1.0, s),
          (-1.0, 0.0, 1.0), (-1.0, -1.0, s), (0.0, -1.0, 1.0), (1.0, -1.0, s),
          (1.0, 0.0, 1.0)]
    P, W = [], []
    for (r, z), wp in zip(profile_pts, profile_w):
        P.append([(r * cx, r * cy, z) for cx, cy, _wj in cw])
        W.append([wp * wj for _cx, _cy, wj in cw])
    srf = Surface(P, W, p=p, q=2)
    srf.U = ([float(x) for x in U] if U is not None
             else clamped_knots(len(profile_pts) - 1, p))
    srf.V = [0, 0, 0, 0.25, 0.25, 0.5, 0.5, 0.75, 0.75, 1, 1, 1]
    return srf


def revolve(profile_curve):
    """把 (r,0,z) 平面曲线的**控制多边形**绕 z 轴旋转成精确曲面（非采样, 保精确）"""
    return surface_of_revolution([(pt[0], pt[2]) for pt in profile_curve.P],
                                 profile_curve.W, profile_curve.p, profile_curve.U)


def sphere_surface(R=1.3):
    """精确有理球面: 半圆母线(2 段 90° 有理弧)绕 z 轴 —— NURBS 教科书第一例"""
    s = math.sqrt(2.0) / 2.0
    prof = Curve([(0, 0, R), (R, 0, R), (R, 0, 0), (R, 0, -R), (0, 0, -R)],
                 W=[1, s, 1, s, 1], p=2, U=[0, 0, 0, 0.5, 0.5, 1, 1, 1])
    return revolve(prof)


def torus_surface(R=1.6, a=0.6):
    """精确有理环面: 偏离轴心的整圆母线(4 段有理弧)旋转, 需 R>a"""
    s = math.sqrt(2.0) / 2.0
    pts = [(R + a, 0, 0), (R + a, 0, a), (R, 0, a), (R - a, 0, a), (R - a, 0, 0),
           (R - a, 0, -a), (R, 0, -a), (R + a, 0, -a), (R + a, 0, 0)]
    prof = Curve(pts, W=[1, s, 1, s, 1, s, 1, s, 1], p=2,
                 U=[0, 0, 0, 0.25, 0.25, 0.5, 0.5, 0.75, 0.75, 1, 1, 1])
    return revolve(prof)


def goblet_surface():
    """高脚杯: 杯脚轮廓全局插值后旋转 —— 样条教材经典演示件"""
    pts = [(0.02, 0, 0.00), (0.85, 0, 0.02), (0.95, 0, 0.18), (0.55, 0, 0.30),
           (0.17, 0, 0.55), (0.17, 0, 1.05), (0.30, 0, 1.20), (0.78, 0, 1.48),
           (0.96, 0, 1.98), (0.99, 0, 2.40)]
    return revolve(interpolate_curve(pts, p=3))


def vase_surface():
    """梅瓶: 丰肩收颈撇口, 轮廓插值旋转"""
    pts = [(0.02, 0, 0.00), (0.70, 0, 0.04), (0.98, 0, 0.55), (0.86, 0, 1.15),
           (0.42, 0, 1.65), (0.30, 0, 2.05), (0.36, 0, 2.35), (0.58, 0, 2.55)]
    return revolve(interpolate_curve(pts, p=3))


def _interp_closed(fn, t0, t1, n, scale=1.0):
    """参数曲线采样 n 点 + 首尾闭合 → 全局插值样条"""
    pts = []
    for i in range(n):
        x, y, z = fn(t0 + (t1 - t0) * i / n)
        pts.append((x * scale, y * scale, z * scale))
    pts.append(pts[0])
    return interpolate_curve(pts, p=3)


def heart_curve(n=24):
    """经典心形线 x=16sin³t, y=13cos t−5cos2t−2cos3t−cos4t（插值拟合）"""
    def f(t):
        return (16 * math.sin(t) ** 3,
                13 * math.cos(t) - 5 * math.cos(2 * t)
                - 2 * math.cos(3 * t) - math.cos(4 * t), 0.0)
    return _interp_closed(f, 0.0, 2 * math.pi, n, scale=1 / 9.0)


def trefoil_curve(n=28):
    """三叶结 (2,3) 环面纽结 —— 拓扑学最著名的纽结, 插值成空间样条"""
    def f(t):
        return (math.sin(t) + 2 * math.sin(2 * t),
                math.cos(t) - 2 * math.cos(2 * t),
                -math.sin(3 * t))
    return _interp_closed(f, 0.0, 2 * math.pi, n, scale=0.85)


def airfoil_curve(n=36, thickness=0.12, chord=3.2):
    """NACA 0012 翼型剖面 —— 航空航天最经典的样条工程案例"""
    def yt(x):
        return 5 * thickness * (0.2969 * math.sqrt(x) - 0.1260 * x
                                - 0.3516 * x * x + 0.2843 * x ** 3
                                - 0.1015 * x ** 4)
    m = n // 2
    pts = []
    for i in range(m):                      # 上表面: 尾缘 → 前缘(余弦加密)
        x = 0.5 * (1 + math.cos(math.pi * i / (m - 1)))
        pts.append(((x - 0.5) * chord, yt(x) * chord, 0.0))
    for i in range(1, m - 1):               # 下表面: 前缘 → 尾缘 
        x = 0.5 * (1 - math.cos(math.pi * i / (m - 1)))
        pts.append(((x - 0.5) * chord, -yt(x) * chord, 0.0))
    pts.append(pts[0])
    return interpolate_curve(pts, p=3)


def s_glyph_curve(n=30):
    """字体字母 S —— Bézier 的成名之地 (PostScript 字体即三次样条轮廓)"""
    def f(t):                                 # 双正弦错位拼出 S 笔势 
        return (1.15 * math.sin(math.pi * (t - 0.5)),
                2.3 * (t - 0.5) + 0.25 * math.sin(2 * math.pi * t), 0.0)
    pts = [f(i / (n - 1)) for i in range(n)]
    return interpolate_curve(pts, p=3)


def _solve3(A, B):
    """解 A·X=B（B 为三元向量列），高斯消去选主元"""
    n = len(A)
    M = [A[i][:] + [B[i][0], B[i][1], B[i][2]] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-13:
            raise ValueError('插值矩阵奇异（点列退化？）')
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        for r in range(n):
            if r == col:
                continue
            f = M[r][col] / pv
            if f:
                for c in range(col, n + 3):
                    M[r][c] -= f * M[col][c]
    return [(M[i][n] / M[i][i], M[i][n + 1] / M[i][i], M[i][n + 2] / M[i][i])
            for i in range(n)]


def interpolate_curve(Q, p=3):
    """全局插值: 曲线精确穿过给定点列（向心参数化 + 平均节点, A9.1）"""
    Q = [tuple(map(float, q)) for q in Q]
    n = len(Q) - 1
    if n < 1:
        raise ValueError('至少需要 2 个点')
    p = max(1, min(int(p), n))
    ds = [math.sqrt(sum((a - b) ** 2 for a, b in zip(Q[k], Q[k - 1])))
          for k in range(1, n + 1)]
    ds = [d if d > 1e-12 else 1e-9 for d in ds]
    total = sum(math.sqrt(d) for d in ds)
    ub = [0.0] * (n + 1)
    for k in range(1, n + 1):
        ub[k] = ub[k - 1] + math.sqrt(ds[k - 1]) / total
    U = [0.0] * (p + 1)
    for j in range(1, n - p + 1):
        U.append(sum(ub[j:j + p]) / p)
    U += [1.0] * (p + 1)
    A = [[0.0] * (n + 1) for _ in range(n + 1)]
    for k in range(n + 1):
        span = find_span(n, p, ub[k], U)
        N = basis_funs(span, ub[k], p, U)
        for a in range(p + 1):
            A[k][span - p + a] = N[a]
    P = _solve3(A, Q)
    return Curve(P, p=p, U=U)


def parse_point(s):
    """解析单个点 '(x,y,z)'; 坐标支持 pi 与四则运算"""
    m = re.search(r'\(([^()]*)\)', s)
    body = m.group(1) if m else s
    toks = [t.strip() for t in body.split(',') if t.strip()]
    if len(toks) != 3:
        raise ValueError('点需要 3 个坐标 (x,y,z)')
    return tuple(float(mathparse._parse_bound(t)) for t in toks)


def parse_points(s):
    """解析点列: '(0,0,0);(1,2,0.5);(3,1,1)' 或 '(0,0),(2,1)'（2D 自动补 z=0）;
    坐标支持 pi 与四则运算, 如 (pi/2, 2*pi, 0)"""
    groups = re.findall(r'\(([^()]*)\)', s)
    if not groups:
        groups = [g for g in re.split(r'[;；]', s) if g.strip()]
    pts = []
    for g in groups:
        toks = [t.strip() for t in g.split(',') if t.strip()]
        try:
            nums = [mathparse._parse_bound(t) for t in toks]
        except mathparse.ParseError as e:
            raise ValueError(f'坐标无法解析 "({g})": {e}')
        if len(nums) == 2:
            nums.append(0.0)
        if len(nums) != 3:
            raise ValueError(f'每个点需要 2 或 3 个坐标: ({g})')
        pts.append(tuple(nums))
    if len(pts) < 2:
        raise ValueError('至少需要 2 个点（用分号或括号分隔）')
    return pts
