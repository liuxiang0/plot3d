#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plotter_app.py — 三维函数绘图器 v2（第二阶段）

表达式输入 → 自动识别（兼容 LaTeX）→ 自动绘图:
  y=f(x) 显式曲线 · f(x,y)=g(x,y) 隐式曲线(Marching Squares)
  z=f(x,y) 显式曲面(画家算法+Lambert着色) · x=f(t),y=g(t),z=h(t) 参数曲线
运行: python3 plot3d/plotter_app.py
"""
import json
import math
import tkinter as tk
from tkinter import filedialog, ttk

import curve_library
import engine3d
import mathparse
import nurbs
import surf_analysis
from dockpane import DockPane
from mathparse import ParseError

BG = engine3d.BG
COLORS = {'explicit2d': '#f9e2af', 'implicit2d': '#a6e3a1',
          'parametric': '#f38ba8'}
SURF_BASE = (137, 180, 250)
# 平直多面体精确面查找表（plain 表达式 → faces）：渲染时绕过 Marching Cubes 格网锯齿
FACES_BY_PLAIN = {}
for _e in curve_library.BUILTIN.values():
    if _e.get('faces'):
        try:
            FACES_BY_PLAIN[mathparse.parse_input(_e['expr'])['plain']] = _e['faces']
        except Exception:
            pass
LIGHT = (-0.45, -0.55, 0.75)
FILL_STYLE = ('#89b4fa', 'gray50')                  # 不等式区域: 蓝色半透明(点纹)
BOUND_COLOR = '#f9e2af'                             # 区域边界线
PALETTE = ('#f9e2af', '#89b4fa', '#a6e3a1', '#f38ba8', '#cba6f7',
           '#fab387', '#94e2d5', '#f2cdcd', '#74c7ec', '#eba0ac')
SURFACE_KINDS = ('surface', 'param_surface', 'implicit3d', 'inequality3d',
                 'mesh')
KIND_ZH = {'explicit2d': '显式曲线', 'implicit2d': '隐式曲线',
           'implicit3d': '隐式曲面', 'surface': '显式曲面',
           'parametric': '参数曲线', 'param_surface': '参数曲面',
           'inequality2d': '不等式区域', 'inequality3d': '不等式体',
           'mesh': '旋转面'}

# 动画演示预设: 一键载入参数族表达式 → 自动设滑块范围 → 播放
ANIM_PRESETS = [
    {'name': '椭圆族 (半短轴 b)',
     'expr': 'x=2*cos(t), y=b*sin(t), z=0; t=0..2pi, b=1',
     'param': 'b', 'lo': 0.2, 'hi': 3.0, 'step': 0.2,
     'desc': 'b 从 0.2→3，看圆被拉成椭圆再压回去'},
    {'name': '抛物线族 (y=a·x²)', 'expr': 'y=a*x^2; a=0.5',
     'param': 'a', 'lo': -2.0, 'hi': 2.0, 'step': 0.25,
     'desc': 'a 的符号与大小决定开口方向与宽窄'},
    {'name': '双曲线族 (x²/a²−y²=1)',
     'expr': 'x^2/a^2-y^2=1; x=-4..4, y=-4..4, a=1',
     'param': 'a', 'lo': 0.4, 'hi': 3.0, 'step': 0.2,
     'desc': '半实轴 a 增大 → 开口变宽远离，渐近线转动'},
    {'name': '玫瑰线瓣数 k',
     'expr': 'x=cos(k*t)*cos(t), y=cos(k*t)*sin(t), z=0; t=0..2pi, k=3',
     'param': 'k', 'lo': 1, 'hi': 8, 'step': 1,
     'desc': '整数 k：奇数→k 瓣，偶数→2k 瓣'},
    {'name': '外摆线尖点数 k',
     'expr': 'x=(k+1)*cos(t)-cos((k+1)*t), y=(k+1)*sin(t)-sin((k+1)*t), z=0; t=0..2pi, k=4',
     'param': 'k', 'lo': 2, 'hi': 9, 'step': 1,
     'desc': 'R=k, r=1 的外摆线，k 个尖点依次登场'},
    {'name': '万花尺笔孔 h',
     'expr': 'x=2*cos(t)+h*cos(2*t/3), y=2*sin(t)-h*sin(2*t/3), z=0; t=0..6pi, h=5',
     'param': 'h', 'lo': 0.5, 'hi': 6.0, 'step': 0.5,
     'desc': 'R=5, r=3 内旋轮线：笔孔从滚圆内移到圆外'},
    {'name': 'Lissajous 相位 φ (3:4)',
     'expr': 'x=sin(3*t+p), y=sin(4*t), z=0; t=0..2pi, p=0',
     'param': 'p', 'lo': 0, 'hi': 6.24, 'step': 0.26,
     'desc': '相位差使曲线在矩形内翻转（示波器李萨如图形）'},
    {'name': '环面纽结族 q (2,q)',
     'expr': 'x=(2+cos(q*t))*cos(2*t), y=(2+cos(q*t))*sin(2*t), z=sin(q*t); t=0..2pi, q=3',
     'param': 'q', 'lo': 2, 'hi': 9, 'step': 1,
     'desc': '缠绕比 2:q 的环面纽结（三叶结 = q=3）'},
    {'name': '星形线族 (半径 a)',
     'expr': 'x=a*cos(t)^3, y=a*sin(t)^3, z=0; t=0..2pi, a=1',
     'param': 'a', 'lo': 0.3, 'hi': 3.0, 'step': 0.3,
     'desc': '梯子曲线的包络随 a 均匀长大'},
    {'name': '螺旋面节距 w',
     'expr': 'x=v*cos(u), y=v*sin(u), z=u/w; u=0..4pi, v=-1..1, w=6',
     'param': 'w', 'lo': 2, 'hi': 12, 'step': 1,
     'desc': 'w 越大螺旋坡道越平缓（极小曲面族）'},
]


def _norm3(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / n for c in v)


# ====================== 采样算法 ======================

def split_runs(pts, jump):
    """按 nan / 跳跃间断把采样点切成多条连续折线"""
    runs, cur, prev = [], [], None
    for p in pts:
        if not all(math.isfinite(c) for c in p):
            if len(cur) > 1:
                runs.append(cur)
            cur, prev = [], None
            continue
        if prev is not None and max(abs(p[k] - prev[k]) for k in range(3)) > jump:
            if len(cur) > 1:
                runs.append(cur)
            cur = []
        cur.append(p)
        prev = p
    if len(cur) > 1:
        runs.append(cur)
    return runs


def marching_squares(F, xr, yr, n=160):
    """隐式曲线 F(x,y)=0 → z=0 平面上的线段集"""
    x0, x1 = xr
    y0, y1 = yr
    dx, dy = (x1 - x0) / n, (y1 - y0) / n
    vals = [[F(x0 + i * dx, y0 + j * dy) for j in range(n + 1)]
            for i in range(n + 1)]

    def interp(pa, va, pb, vb):
        t = va / (va - vb)
        return (pa[0] + (pb[0] - pa[0]) * t,
                pa[1] + (pb[1] - pa[1]) * t, 0.0)

    segs = []
    for i in range(n):
        for j in range(n):
            v00, v10 = vals[i][j], vals[i + 1][j]
            v11, v01 = vals[i + 1][j + 1], vals[i][j + 1]
            if not all(math.isfinite(v) for v in (v00, v10, v11, v01)):
                continue
            p00 = (x0 + i * dx, y0 + j * dy)
            p10 = (x0 + (i + 1) * dx, y0 + j * dy)
            p11 = (x0 + (i + 1) * dx, y0 + (j + 1) * dy)
            p01 = (x0 + i * dx, y0 + (j + 1) * dy)
            pts = []                                  # 下/右/上/左 四边交点
            if (v00 > 0) != (v10 > 0):
                pts.append(interp(p00, v00, p10, v10))
            if (v10 > 0) != (v11 > 0):
                pts.append(interp(p10, v10, p11, v11))
            if (v01 > 0) != (v11 > 0):
                pts.append(interp(p01, v01, p11, v11))
            if (v00 > 0) != (v01 > 0):
                pts.append(interp(p00, v00, p01, v01))
            if len(pts) == 2:
                segs.append((pts[0], pts[1]))
            elif len(pts) == 4:                       # 鞍点: 切离与中心异号的角点
                c = (v00 + v10 + v11 + v01) / 4.0
                if (v00 > 0) == (c > 0):              # v10, v01 孤立 → 下右 + 上左
                    segs += [(pts[0], pts[1]), (pts[2], pts[3])]
                else:                                 # v00, v11 孤立 → 下左 + 右上
                    segs += [(pts[0], pts[3]), (pts[1], pts[2])]
    return segs


def chain_segments(segs):
    """无序线段集 (a,b) → 折线列表（端点匹配, 双向贪心延伸）"""
    if not segs:
        return []
    tol = 1e-7

    def key(p):
        return (round(p[0] / tol), round(p[1] / tol), round(p[2] / tol))

    endmap = {}
    for i, (a, b) in enumerate(segs):
        endmap.setdefault(key(a), []).append((i, a, b))
        endmap.setdefault(key(b), []).append((i, b, a))
    used = [False] * len(segs)
    chains = []
    for i, (a, b) in enumerate(segs):
        if used[i]:
            continue
        used[i] = True
        chain = [a, b]
        for tail in (True, False):            # 先延尾端, 再延首端 
            while True:
                cands = endmap.get(key(chain[-1] if tail else chain[0]), [])
                nxt = next(((j, p, q) for j, p, q in cands if not used[j]),
                           None)
                if nxt is None:
                    break
                j, _p, q = nxt
                used[j] = True
                if tail:
                    chain.append(q)
                else:
                    chain.insert(0, q)
        chains.append(chain)
    return chains


def revolve_curve(pts, p0, p1, n_seg=36, n_prof=64):
    """曲线点列 + 轴直线 (p0→p1) → 旋转面四边形片（世界坐标, 已着色）。
    管线: 点列→轴向 (r,z) 轮廓→全局插值样条→nurbs.surface_of_revolution
    精确有理旋转→网格采样→基变换回世界坐标。任意轴方向均适用。"""
    import nurbs
    lx, ly, lz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
    L = math.sqrt(lx * lx + ly * ly + lz * lz)
    if L < 1e-12:
        raise ValueError('轴线两端点重合, 无法确定轴方向')
    d = (lx / L, ly / L, lz / L)
    ref = (0.0, 0.0, 1.0) if abs(d[2]) < 0.9 else (1.0, 0.0, 0.0)
    cx, cy, cz = (d[1] * ref[2] - d[2] * ref[1],
                  d[2] * ref[0] - d[0] * ref[2],
                  d[0] * ref[1] - d[1] * ref[0])
    cl = math.sqrt(cx * cx + cy * cy + cz * cz) or 1.0
    e1 = (cx / cl, cy / cl, cz / cl)
    e2 = (d[1] * e1[2] - d[2] * e1[1],
          d[2] * e1[0] - d[0] * e1[2],
          d[0] * e1[1] - d[1] * e1[0])
    prof = []
    for P in pts:
        vx, vy, vz = P[0] - p0[0], P[1] - p0[1], P[2] - p0[2]
        z = vx * d[0] + vy * d[1] + vz * d[2]
        rx, ry, rz = vx - z * d[0], vy - z * d[1], vz - z * d[2]
        prof.append((math.sqrt(rx * rx + ry * ry + rz * rz), 0.0, z))
    if len(prof) < 2:
        raise ValueError('曲线有效点不足')
    if len(prof) > 120:                      # 插值矩阵过大降速 → 均匀降采样 
        m = 120
        prof = [prof[round(i * (len(prof) - 1) / (m - 1))] for i in range(m)]
    surf = nurbs.revolve(nurbs.interpolate_curve(prof, p=3))
    quads = surf.mesh(nu=n_prof, nv=n_seg)

    def to_world(P):
        x, y, z = P
        return (p0[0] + x * e1[0] + y * e2[0] + z * d[0],
                p0[1] + x * e1[1] + y * e2[1] + z * d[1],
                p0[2] + x * e1[2] + y * e2[2] + z * d[2])

    return [(tuple(map(to_world, Q)), col) for Q, col in quads]


# ---------- Marching Cubes 隐式曲面（无查找表: 面截线段成环 + 面心消歧） ----------
CUBE_VERTS = ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
              (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))
MC_EDGES = ((0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7))
MC_FACES = (                             # (面角点循环序, 面棱循环序)
    ((0, 1, 2, 3), (0, 1, 2, 3)),
    ((4, 5, 6, 7), (4, 5, 6, 7)),
    ((0, 1, 5, 4), (0, 9, 4, 8)),
    ((2, 3, 7, 6), (2, 11, 6, 10)),
    ((0, 3, 7, 4), (3, 11, 7, 8)),
    ((1, 2, 6, 5), (1, 10, 5, 9)),
)


def _mc_cell(cv, pts, tris):
    """单立方体 MC: cv 八角值, pts 八角坐标 → 截三角形追加至 tris"""
    pos = [v > 0 for v in cv]
    npos = sum(pos)
    if npos in (0, 8):
        return
    cross = {}                                       # 棱号 → 交点
    for ei, (a, b) in enumerate(MC_EDGES):
        if pos[a] != pos[b]:
            t = cv[a] / (cv[a] - cv[b])
            pa, pb = pts[a], pts[b]
            cross[ei] = (pa[0] + (pb[0] - pa[0]) * t,
                         pa[1] + (pb[1] - pa[1]) * t,
                         pa[2] + (pb[2] - pa[2]) * t)
    segs = []                                        # 面截线段（棱号对）
    for corners, edges in MC_FACES:
        ce = [e for e in edges if e in cross]
        if len(ce) == 2:
            segs.append((ce[0], ce[1]))
        elif len(ce) == 4:                           # 面鞍歧义: 面心符号判别
            fpos = sum(cv[c] for c in corners) / 4.0 > 0
            for k in range(4):
                if pos[corners[k]] != fpos:          # 孤立角点 → 连其两侧交点
                    segs.append((edges[(k - 1) % 4], edges[k]))
    if not segs:
        return
    adj = {}                                         # 交点图: 度数恒 2 → 闭环
    for a, b in segs:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    seen = set()
    for start in adj:
        if start in seen:
            continue
        loop = [start]
        seen.add(start)
        prev, cur = None, start
        while True:
            nxt = next((x for x in adj[cur] if x != prev and x not in seen),
                       None)
            if nxt is None:
                break
            seen.add(nxt)
            loop.append(nxt)
            prev, cur = cur, nxt
        lp = [cross[e] for e in loop]
        for k in range(1, len(lp) - 1):              # 扇形剖分
            tris.append((lp[0], lp[k], lp[k + 1]))


def marching_cubes(F, xr, yr, zr, base=(176, 196, 250)):
    """F(x,y,z)=0 → Lambert 着色三角形片; 返回 (面片列表, 网格分辨率)"""
    span = max(xr[1] - xr[0], yr[1] - yr[0], zr[1] - zr[0])
    n = 38 if span <= 5 else (32 if span <= 8 else 26)
    x0, x1 = xr
    y0, y1 = yr
    z0, z1 = zr
    dx, dy, dz = (x1 - x0) / n, (y1 - y0) / n, (z1 - z0) / n
    V = [[[F(x0 + i * dx, y0 + j * dy, z0 + k * dz) for k in range(n + 1)]
          for j in range(n + 1)] for i in range(n + 1)]
    tris = []
    for i in range(n):
        for j in range(n):
            for k in range(n):
                cv = [V[i + a][j + b][k + c] for a, b, c in CUBE_VERTS]
                if not all(math.isfinite(v) for v in cv):
                    continue
                pts = [(x0 + (i + a) * dx, y0 + (j + b) * dy,
                        z0 + (k + c) * dz) for a, b, c in CUBE_VERTS]
                _mc_cell(cv, pts, tris)
    return _shade_tris(tris, base), n


def marching_cubes_adaptive(F, xr, yr, zr, n0=18, s=3, ratio_limit=0.35,
                            base=(176, 196, 250)):
    """八叉树自适应: 粗网格 n0³ 分类空/曲面单元, 仅曲面单元做 2×2×2 细分 MC 提取
    （等效分辨率 N=n0*s, 跳过内部单元 → 生成加速 3-5×）。
    整数格点缓存 → 相邻单元共享顶点无缝隙; 活跃单元超 ratio_limit 回退均匀网格。
    返回 (面片列表, 说明字符串)"""
    x0, x1 = xr
    y0, y1 = yr
    z0, z1 = zr
    total = n0 ** 3
    dx0, dy0, dz0 = (x1 - x0) / n0, (y1 - y0) / n0, (z1 - z0) / n0
    V0 = [[[F(x0 + i * dx0, y0 + j * dy0, z0 + k * dz0) for k in range(n0 + 1)]
           for j in range(n0 + 1)] for i in range(n0 + 1)]
    active = []
    for i in range(n0):
        for j in range(n0):
            for k in range(n0):
                cs = (V0[i][j][k], V0[i + 1][j][k], V0[i + 1][j + 1][k],
                      V0[i][j + 1][k], V0[i][j][k + 1], V0[i + 1][j][k + 1],
                      V0[i + 1][j + 1][k + 1], V0[i][j + 1][k + 1])
                if not all(math.isfinite(v) for v in cs):
                    active.append((i, j, k))        # 非有限边界保守处理
                    continue
                if not (all(v > 0 for v in cs) or all(v <= 0 for v in cs)):
                    active.append((i, j, k))
    pct = len(active) * 100 // total
    if len(active) > ratio_limit * total:           # 密集曲面 → 均匀网格
        tris, n = marching_cubes(F, xr, yr, zr, base)
        return tris, f'均匀 {n}³（密集曲面, 活跃 {pct}%）'
    N = n0 * s                                      # 精细整数格点
    cache = {}

    def val(I, J, K):
        key = (I, J, K)
        v = cache.get(key)
        if v is None:
            v = F(x0 + (x1 - x0) * I / N, y0 + (y1 - y0) * J / N,
                  z0 + (z1 - z0) * K / N)
            cache[key] = v
        return v

    for i in range(n0 + 1):                         # 预填粗格点（与 V0 一致）
        for j in range(n0 + 1):
            for k in range(n0 + 1):
                cache[(i * s, j * s, k * s)] = V0[i][j][k]
    ddx = (x1 - x0) / N
    ddy = (y1 - y0) / N
    ddz = (z1 - z0) / N
    tris = []
    for i, j, k in active:
        I0, J0, K0 = i * s, j * s, k * s
        for a in range(s):
            for b in range(s):
                for c in range(s):
                    II, JJ, KK = I0 + a, J0 + b, K0 + c
                    cv = [val(II + u, JJ + v, KK + w)
                          for u, v, w in CUBE_VERTS]
                    if not all(math.isfinite(v) for v in cv):
                        continue
                    pts = [(x0 + (II + u) * ddx, y0 + (JJ + v) * ddy,
                            z0 + (KK + w) * ddz) for u, v, w in CUBE_VERTS]
                    _mc_cell(cv, pts, tris)
    return _shade_tris(tris, base), f'八叉树 {n0}³→{N}³（曲面单元 {pct}%）'


def refine_implicit(F, segs, cam, w, h, flat_px=0.5, min_px=1.5, max_depth=8):
    """隐式曲线段自适应平滑: 中点 Newton 投影到 F=0 + 屏幕平坦度判据。
    放大时弦中点偏差超阈 → 递归细分, 保证任意缩放下曲线光滑。"""
    out = []

    def proj2(p):
        f = F(p[0], p[1])
        if not math.isfinite(f):
            return p
        eps = 1e-7 * (1.0 + abs(p[0]) + abs(p[1]))
        gx = (F(p[0] + eps, p[1]) - F(p[0] - eps, p[1])) / (2.0 * eps)
        gy = (F(p[0], p[1] + eps) - F(p[0], p[1] - eps)) / (2.0 * eps)
        g2 = gx * gx + gy * gy
        if g2 < 1e-20:
            return p
        return (p[0] - f * gx / g2, p[1] - f * gy / g2)

    def rec(a, b, d):
        sa = cam.project(a[0], a[1], 0.0, w, h)
        sb = cam.project(b[0], b[1], 0.0, w, h)
        if ((sa[0] < -80 and sb[0] < -80) or (sa[0] > w + 80 and sb[0] > w + 80)
                or (sa[1] < -80 and sb[1] < -80)
                or (sa[1] > h + 80 and sb[1] > h + 80)):
            out.append((a, b))                      # 视口外: 不细分
            return
        m = proj2(((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0))
        m3 = (m[0], m[1], 0.0)
        sm = cam.project(m[0], m[1], 0.0, w, h)
        dev = math.hypot(sm[0] - (sa[0] + sb[0]) / 2.0,
                         sm[1] - (sa[1] + sb[1]) / 2.0)
        length = math.hypot(sa[0] - sb[0], sa[1] - sb[1])
        if d <= 0 or dev <= flat_px or length <= min_px:
            out.append((a, b))
        else:
            rec(a, m3, d - 1)
            rec(m3, b, d - 1)

    for a, b in segs:
        rec(a, b, max_depth)
    return out


def region_runs(conds, xr, yr, n=150):
    """conds=[(F(x,y), 正侧?)] → 行游程合并的填充矩形 [(x0,y0,x1,y1)]（中心采样）"""
    x0, x1 = xr
    y0, y1 = yr
    dx, dy = (x1 - x0) / n, (y1 - y0) / n

    def inside(xc, yc):
        for F, pos in conds:
            v = F(xc, yc)
            if not math.isfinite(v) or (v > 0) != pos:
                return False
        return True

    runs = []
    for j in range(n):
        yc = y0 + (j + 0.5) * dy
        i = 0
        while i < n:
            if inside(x0 + (i + 0.5) * dx, yc):
                i0 = i
                while i < n and inside(x0 + (i + 0.5) * dx, yc):
                    i += 1
                runs.append((x0 + i0 * dx, y0 + j * dy,
                             x0 + i * dx, y0 + (j + 1) * dy))
            else:
                i += 1
    return runs


def _shade_tris(tris, base=(176, 196, 250)):
    Lx, Ly, Lz = _norm3(LIGHT)
    out = []
    for a, b, c in tris:
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        nl = math.sqrt(nx * nx + ny * ny + nz * nz)
        if nl < 1e-15:
            continue
        bri = 0.32 + 0.68 * abs(nx * Lx + ny * Ly + nz * Lz) / nl
        out.append(((a, b, c), '#%02x%02x%02x' % (int(base[0] * bri),
                                                  int(base[1] * bri),
                                                  int(base[2] * bri))))
    return out


def _shade_polys(polys, base=(176, 196, 250)):
    """平直多边形面 → [(顶点元组, 色)] ：Newell 法向 + Lambert。
    面以 n 边形整面入管线：实体填充不变，线划模式只出现真棱（无扇形对角线）。"""
    Lx, Ly, Lz = _norm3(LIGHT)
    out = []
    for poly in polys:
        nx = ny = nz = 0.0
        for i in range(len(poly)):
            a, b = poly[i], poly[(i + 1) % len(poly)]
            nx += (a[1] - b[1]) * (a[2] + b[2])
            ny += (a[2] - b[2]) * (a[0] + b[0])
            nz += (a[0] - b[0]) * (a[1] + b[1])
        nl = math.sqrt(nx * nx + ny * ny + nz * nz)
        if nl < 1e-15:
            continue
        bri = 0.32 + 0.68 * abs(nx * Lx + ny * Ly + nz * Lz) / nl
        out.append((tuple(poly), '#%02x%02x%02x' % (int(base[0] * bri),
                                                    int(base[1] * bri),
                                                    int(base[2] * bri))))
    return out


def surface_quads(f, xr, yr, n=42, base=SURF_BASE):
    """显式曲面 → 带 Lambert 着色的四边形片列表"""
    x0, x1 = xr
    y0, y1 = yr
    xs = [x0 + (x1 - x0) * i / n for i in range(n + 1)]
    ys = [y0 + (y1 - y0) * j / n for j in range(n + 1)]
    Z = [[f(x, y) for y in ys] for x in xs]
    fin = [v for row in Z for v in row if math.isfinite(v)]
    if not fin:
        return []
    zspan = (max(fin) - min(fin)) or 1.0
    L = _norm3(LIGHT)
    quads = []
    for i in range(n):
        for j in range(n):
            P = [(xs[i], ys[j], Z[i][j]), (xs[i + 1], ys[j], Z[i + 1][j]),
                 (xs[i + 1], ys[j + 1], Z[i + 1][j + 1]),
                 (xs[i], ys[j + 1], Z[i][j + 1])]
            if any(not math.isfinite(p[2]) for p in P):
                continue
            if max(p[2] for p in P) - min(p[2] for p in P) > zspan * 0.25:
                continue                              # 间断面（如 1/x）剔除
            ux, uy, uz = P[1][0] - P[0][0], P[1][1] - P[0][1], P[1][2] - P[0][2]
            vx, vy, vz = P[3][0] - P[0][0], P[3][1] - P[0][1], P[3][2] - P[0][2]
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            b = 0.32 + 0.68 * abs(nx * L[0] + ny * L[1] + nz * L[2]) / nl
            col = '#%02x%02x%02x' % (int(base[0] * b),
                                     int(base[1] * b),
                                     int(base[2] * b))
            quads.append((P, col))
    return quads


# ====================== 应用界面 ======================

class PlotterApp(tk.Frame):
    HELP = ('回车/添加: 表达式加入场景（多对象同屏, ID 区分, 画家算法深度遮挡）· '
            'y=f(x) · f(x,y)=g(x,y) · z=f(x,y) · F(x,y,z)=0 · 不等式 · r(t) · r(u,v) · '
            '兼容 LaTeX 与参数 ; r=2 · 对象列表: 点选/双击编辑/点"显"列显隐/Del删除/颜色 · 景深: 远处淡出')
    def __init__(self, master):
        super().__init__(master, bg=BG)
        self.history = []
        self.hi = 0
        self._build_ui()

    def _build_ui(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill='x', padx=8, pady=(8, 2))
        tk.Label(top, text='f(x)', bg=BG, fg='#89b4fa',
                 font=('DejaVu Sans', engine3d.font_size(12), 'bold')).pack(side='left', padx=(0, 6))
        self.entry = tk.Entry(top, font=('Consolas', engine3d.font_size(13)), bg='#181825',
                              fg='#cdd6f4', insertbackground='#cdd6f4',
                              relief='flat')
        self.entry.pack(side='left', fill='x', expand=True, ipady=6)
        self.entry.bind('<Return>', lambda e: self.plot())
        self.entry.bind('<Up>', self._hist_prev)
        self.entry.bind('<Down>', self._hist_next)
        tk.Button(top, text='添加', command=self.plot, bg='#a6e3a1',
                  fg='#1e1e2e', relief='flat', font=('DejaVu Sans', engine3d.font_size(11), 'bold'),
                  padx=14).pack(side='left', padx=(6, 3))
        self.lib_btn = tk.Menubutton(top, text='函数库 ▾', bg='#45475a',
                                     fg='#cdd6f4', relief='flat')
        self.lib_btn.pack(side='left', padx=3)
        ex = tk.Menubutton(top, text='导出 ▾', bg='#45475a', fg='#cdd6f4',
                           relief='flat')
        exm = tk.Menu(ex, tearoff=0)
        exm.add_command(label='SVG 矢量图', command=lambda: self._export('svg'))
        exm.add_command(label='EPS 矢量图', command=lambda: self._export('eps'))
        exm.add_command(label='OBJ 3D 模型', command=lambda: self._export_model('obj'))
        exm.add_command(label='STL 3D 打印', command=lambda: self._export_model('stl'))
        exm.add_separator()
        exm.add_command(label='保存场景 JSON', command=self._save_scene_dialog)
        exm.add_command(label='打开场景 JSON', command=self._load_scene_dialog)
        exm.add_command(label='✂ 截面 z=h（隐式曲面）', command=self._add_slice)
        exm.add_command(label='🌀 曲线绕轴旋转成面…', command=self._revolve_dialog)
        exm.add_separator()
        exm.add_command(label='动画 GIF（参数扫描）', command=self._export_gif)
        exm.add_command(label='动画 SVG 序列（参数扫描）',
                        command=self._export_svg_seq)
        ex['menu'] = exm
        ex.pack(side='left', padx=3)
        self.status = tk.Label(self, anchor='w', justify='left', bg=BG,
                               fg='#9aa0b4', font=('DejaVu Sans', engine3d.font_size(10)),
                               wraplength=960)
        self.status.pack(fill='x', padx=10, pady=(0, 2))
        self.status.config(text=self.HELP)
        # 曲面分析工具栏
        abar = tk.Frame(self, bg=BG)
        abar.pack(fill='x', padx=10, pady=(0, 2))
        tk.Label(abar, text='曲面分析:', bg=BG, fg='#5b6178',
                 font=('DejaVu Sans', engine3d.font_size(9))).pack(side='left')
        self.an_btns = {}
        for key, label in (('normals', '法向量场'), ('K', '高斯曲率 K'),
                           ('H', '平均曲率 |H|'), ('PD', '主曲率方向'),
                           (None, '关闭')):
            b = tk.Button(abar, text=label, relief='flat', bg='#313244',
                          fg='#9aa0b4', font=('DejaVu Sans', engine3d.font_size(9)),
                          state='disabled', padx=8,
                          command=lambda k=key: self._set_analysis(k))
            b.pack(side='left', padx=2)
            self.an_btns[key] = b
        self.mode_btns = {}
        for key, label in (('both', '实体+线'), ('wire', '线框'),
                           ('solid', '实体')):
            b = tk.Button(abar, text=label, relief='flat', bg='#313244',
                          fg='#9aa0b4', font=('DejaVu Sans', engine3d.font_size(9)),
                          state='disabled', padx=6,
                          command=lambda k=key: self._set_surface_mode(k))
            b.pack(side='right', padx=2)
            self.mode_btns[key] = b
        tk.Label(abar, text='渲染:', bg=BG, fg='#5b6178',
                 font=('DejaVu Sans', engine3d.font_size(9))).pack(side='right')
        self.cue_btn = tk.Button(abar, text='景深', command=self._toggle_cue,
                                 bg='#313244', fg='#9aa0b4', relief='flat',
                                 font=('DejaVu Sans', engine3d.font_size(9)), padx=8)
        self.cue_btn.pack(side='right', padx=2)
        self.axes_btn = tk.Button(abar, text='坐标轴', command=self._toggle_axes,
                                  bg='#89b4fa', fg='#1e1e2e', relief='flat',
                                  font=('DejaVu Sans', engine3d.font_size(9)), padx=8)
        self.axes_btn.pack(side='right', padx=2)
        self.mode_btns['solid'].config(bg='#89b4fa', fg='#1e1e2e')
        self._geo = None
        self._base_meshes = None
        self._analysis = None
        self._arrows = []
        self._cbar = None
        self._cbar_title = ''
        self._pdirs = None
        self._pd_lines = []
        self._obj_color = None
        self._curve_srcs = []
        self._refine_pending = False
        self._slider_param = None
        self._play_id = None
        self._play_n = 0
        self.objects = []                    # 场景对象表（多对象同屏）
        self._next_id = 1
        self._sel_id = None
        self._palette_i = 0
        self._tree_tags = set()
        self._ana_mesh_idx = None
        self._in_render = False
        self._rebuild_lib_menu(init=True)
        # 中部: 画布(左) + 可停靠/可脱离的对象列表(右)
        mid = tk.Frame(self, bg=BG)
        mid.pack(fill='both', expand=True)
        self.eng = engine3d.Engine3D(mid)
        self.eng.pack(side='left', fill='both', expand=True)
        self.eng.on_view_change = self._schedule_refine
        self.layer_pane = DockPane(self, '对象列表 · 图层',
                                   self._build_layer_panel,
                                   side='right', width=330,
                                   float_size=(420, 680))
        self.layer_pane.dock(mid)

    def _build_layer_panel(self, parent):
        """构建对象列表(图层)面板内容; parent 为主窗口侧栏或脱离窗口"""
        tk.Label(parent, text='点“显”列切换显隐 · Del 删除 · 双击编辑',
                 bg=BG, fg='#5b6178', font=('DejaVu Sans', engine3d.font_size(9)),
                 anchor='w').pack(fill='x')
        tstyle = ttk.Style(parent)
        try:
            tstyle.theme_use('clam')
        except tk.TclError:
            pass
        tstyle.configure('Scene.Treeview', background='#181825',
                         foreground='#cdd6f4', fieldbackground='#181825',
                         font=('Consolas', engine3d.font_size(9)), rowheight=engine3d.font_size(22))
        tstyle.configure('Scene.Treeview.Heading', background='#313244',
                         foreground='#cdd6f4',
                         font=('DejaVu Sans', engine3d.font_size(9), 'bold'))
        tstyle.map('Scene.Treeview', background=[('selected', '#45475a')],
                   foreground=[('selected', '#f9e2af')])
        cols = ('id', 'vis', 'name', 'color', 'expr')
        self.tree = ttk.Treeview(parent, columns=cols, show='headings',
                                 style='Scene.Treeview', height=10)
        self.tree.tag_configure('hidden', foreground='#585e74')
        for c, label, wd in (('id', 'ID', 28), ('vis', '显', 26),
                             ('name', '名称', 92), ('color', '颜色', 58),
                             ('expr', '定义', 96)):
            self.tree.heading(c, text=label)
            self.tree.column(c, width=wd, anchor='w')
        tsb = ttk.Scrollbar(parent, orient='vertical', command=self.tree.yview)
        self.tree.config(yscrollcommand=tsb.set)
        self.tree.pack(side='left', fill='both', expand=True)
        tsb.pack(side='right', fill='y')
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        self.tree.bind('<Double-1>', self._on_tree_double)
        self.tree.bind('<Button-1>', self._on_tree_click)
        self.tree.bind('<Delete>', lambda e: self._delete_obj())
        tbtns = tk.Frame(parent, bg=BG)
        tbtns.pack(fill='x', pady=(4, 0))
        for label, cmd in (('删除', self._delete_obj),
                           ('显/隐', self._toggle_visible),
                           ('颜色', self._obj_color_btn),
                           ('清空全部', self._clear_objs)):
            tk.Button(tbtns, text=label, command=cmd, bg='#45475a',
                      fg='#cdd6f4', relief='flat',
                      font=('DejaVu Sans', engine3d.font_size(9))).pack(side='left', padx=2,
                                                   expand=True, fill='x')
        self._rebuild_tree()
        self.entry.focus_set()
        if getattr(self, '_sld_built', False):   # 滑块栏属主窗口非面板: 只建一次, 避免脱离/收回时重复叠加
            return
        self._sld_built = True
        # 参数滑块栏: [参数▾] [a] [b] [Δ] ═══●═══ 值标签 [▶播放]
        sld = tk.Frame(self, bg=BG)
        sld.pack(fill='x', padx=10, pady=(2, 6))
        tk.Label(sld, text='参数', bg=BG, fg='#5b6178',
                 font=('DejaVu Sans', engine3d.font_size(9))).pack(side='left')
        self.param_var = tk.StringVar(value='t')
        self.param_menu = tk.OptionMenu(sld, self.param_var, 't')
        self.param_menu.config(bg='#45475a', fg='#cdd6f4', relief='flat',
                               font=('DejaVu Sans', engine3d.font_size(9)), width=3)
        self.param_menu['menu'].config(bg='#313244', fg='#cdd6f4')
        self.param_menu.pack(side='left', padx=(2, 6))
        self.sld_vars = {}
        for label, key, default in (('a:', 'a', '-5'), ('b:', 'b', '5'),
                                    ('Δ:', 'd', '0.1')):
            tk.Label(sld, text=label, bg=BG, fg='#5b6178',
                     font=('DejaVu Sans', engine3d.font_size(9))).pack(side='left')
            var = tk.StringVar(value=default)
            var.trace_add('write', lambda *a: self._apply_slider_bounds())
            tk.Entry(sld, textvariable=var, width=5, font=('Consolas', engine3d.font_size(9)),
                     bg='#181825', fg='#cdd6f4', insertbackground='#cdd6f4',
                     relief='flat').pack(side='left', padx=(1, 4))
            self.sld_vars[key] = var
        style = ttk.Style(sld)
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass
        style.configure('Horizontal.TScale', background=BG,
                        troughcolor='#313244')
        self.slider = ttk.Scale(sld, from_=-5.0, to=5.0, orient='horizontal',
                                command=self._on_slider)
        self.slider.pack(side='left', fill='x', expand=True, padx=6)
        self.t_label = tk.Label(sld, text='t = —', bg=BG, fg='#f9e2af',
                                width=18, anchor='w', font=('Consolas', engine3d.font_size(10)))
        self.t_label.pack(side='left')
        self.play_btn = tk.Button(sld, text='▶ 播放', command=self._toggle_play,
                                  bg='#45475a', fg='#cdd6f4', relief='flat',
                                  font=('DejaVu Sans', engine3d.font_size(9)))
        self.play_btn.pack(side='left', padx=(4, 0))
        self._set_slider_enabled(False)

    # ---------- 主流程（多对象场景） ----------
    def plot(self):
        """输入框表达式 → 作为新对象加入场景"""
        self._add_object(self.entry.get())

    def _add_object(self, raw=None, color=None, name=None, visible=True,
                    render=True):
        raw = (raw if raw is not None else self.entry.get()).strip()
        if not raw:
            return None
        try:
            spec = mathparse.parse_input(raw)
        except ParseError as e:
            self._status(f'❌ 解析失败: {e}', '#f38ba8')
            return None
        oid = self._next_id
        self._next_id += 1
        col = color or self._next_color()
        nm = name or f'O{oid}·{KIND_ZH.get(spec["kind"], spec["kind"])}'
        obj = {'id': oid, 'name': nm, 'kind': spec['kind'], 'expr': raw,
               'spec': spec, 'color': col, 'visible': visible,
               'mesh_idx': None}
        self.objects.append(obj)
        self._sel_id = oid
        if raw not in self.history:
            self.history.append(raw)
        self.hi = len(self.history)
        self._rebuild_tree()
        if render:
            self._render_scene()
            self._status(f'✓ 已添加 {nm} · 颜色 {col} · 共 {len(self.objects)} 个对象',
                         '#a6e3a1')
        return obj

    def _next_color(self):
        col = PALETTE[self._palette_i % len(PALETTE)]
        self._palette_i += 1
        return col

    def _selected_obj(self):
        for o in self.objects:
            if o['id'] == self._sel_id:
                return o
        return None

    def _render_scene(self, status=True, keep_play=False):
        """重渲染整个场景: 全部可见对象（画家算法统一处理深度遮挡）
        keep_play=True 时不中断参数播放（滑块/播放步进路径专用）"""
        if self._in_render:
            return
        self._in_render = True
        try:
            eng = self.eng
            eng.clear_all()
            self._curve_srcs = []
            vis = 0
            for obj in self.objects:
                obj['mesh_idx'] = None
                if not obj['visible']:
                    continue
                vis += 1
                self._obj_color = obj['color']
                self._spec = obj['spec']
                mi = len(eng.meshes)
                try:
                    self._render(obj['spec'])
                except Exception as e:
                    self._status(f'❌ {obj["name"]} 渲染失败: {e}', '#f38ba8')
                    continue
                if len(eng.meshes) > mi:
                    obj['mesh_idx'] = mi
            self._refine_all()
            sel = self._selected_obj()
            if sel is None and self.objects:
                sel = self.objects[-1]
                self._sel_id = sel['id']
            if sel:
                self._spec = sel['spec']
                self._init_slider(sel['spec'], stop_play=not keep_play)
            else:
                self._spec = None
                self._init_slider({'params': {}})
            self._post_render_scene()
            if status:
                self._status(f'✓ 场景: {len(self.objects)} 个对象 · {vis} 可见'
                             + (f' · 选中 {sel["name"]}' if sel else ''),
                             '#a6e3a1')
        finally:
            self._in_render = False

    def _render(self, spec):
        kind = spec['kind']
        if kind == 'explicit2d':
            return self._plot_explicit(spec)
        if kind == 'implicit2d':
            return self._plot_implicit(spec)
        if kind == 'implicit3d':
            return self._plot_implicit3d(spec)
        if kind == 'surface':
            return self._plot_surface(spec)
        if kind == 'parametric':
            return self._plot_parametric(spec)
        if kind == 'param_surface':
            return self._plot_param_surface(spec)
        if kind == 'inequality2d':
            return self._plot_inequality2d(spec)
        if kind == 'inequality3d':
            return self._plot_inequality3d(spec)
        if kind == 'mesh':
            return self._plot_mesh(spec)
        raise ParseError(f'未知类型 {kind}')

    # ---------- 四类绘图 ----------
    def _plot_explicit(self, spec):
        var = spec['var']
        a, b = spec['x_range'] if var == 'x' else spec['y_range']
        col = self._obj_color or COLORS['explicit2d']
        self._curve_srcs.append(('explicit', spec['f'], var, (a, b), col))
        name = 'y=f(x)' if var == 'x' else 'x=g(y)'
        return f'显式曲线 {name}（自适应采样）'

    def _plot_implicit(self, spec):
        col = self._obj_color or COLORS['implicit2d']
        zl = spec.get('z_level', 0.0)
        self._curve_srcs.append(('implicit2d',
                                 [(spec['F'], spec['x_range'],
                                   spec['y_range'], zl)], col))
        return '隐式曲线 F(x,y)=0（自适应平滑）'

    def _plot_implicit3d(self, spec):
        faces = FACES_BY_PLAIN.get(spec['plain'])
        if faces:                                   # 精确多面体: n 边形整面入管线
            base = (engine3d.hex_to_rgb(self._obj_color) if self._obj_color
                    else (176, 196, 250))
            polys = [tuple(tuple(p) for p in poly) for poly in faces]
            self.eng.add_mesh(_shade_polys(polys, base=base))
            return (f'精确多面体 · {len(faces)} 个 n 边形面'
                    f'（线划模式仅真棱, 无三角剖分对角线）')
        base = (engine3d.hex_to_rgb(self._obj_color) if self._obj_color
                else (176, 196, 250))
        tris, info = marching_cubes_adaptive(
            spec['F'], spec['x_range'], spec['y_range'], spec['z_range'],
            base=base)
        if tris:
            self.eng.add_mesh(tris)
        return f'隐式曲面 F(x,y,z)=0 · {info} · {len(tris)} 三角形'

    def _plot_surface(self, spec):
        base = (engine3d.hex_to_rgb(self._obj_color) if self._obj_color
                else SURF_BASE)
        quads = surface_quads(spec['f'], spec['x_range'], spec['y_range'],
                              n=42, base=base)
        if quads:
            self.eng.add_mesh(quads)
        return f'显式曲面 z=f(x,y) · 42×42 网格 · {len(quads)} 面片'

    def _plot_parametric(self, spec):
        col = self._obj_color or COLORS['parametric']
        self._curve_srcs.append(('param', spec['comps'], spec['t_range'], col))
        t0, t1 = spec['t_range']
        return f'参数曲线 r(t) · t∈[{t0:g},{t1:g}]'

    def _plot_param_surface(self, spec):
        comps = spec['comps']
        zero = lambda u, v: 0.0
        fx = comps.get('x', zero)
        fy = comps.get('y', zero)
        fz = comps.get('z', zero)
        u0, u1 = spec['u_range']
        v0, v1 = spec['v_range']
        nu = nv = 42
        grid = []
        for i in range(nu + 1):
            u = u0 + (u1 - u0) * i / nu
            row = []
            for j in range(nv + 1):
                v = v0 + (v1 - v0) * j / nv
                row.append((fx(u, v), fy(u, v), fz(u, v)))
            grid.append(row)
        fin = [p for row in grid for p in row if all(math.isfinite(c) for c in p)]
        if not fin:
            raise ParseError('参数曲面无有效采样点')
        spans = [max(p[k] for p in fin) - min(p[k] for p in fin)
                 for k in range(3)]
        base = (engine3d.hex_to_rgb(self._obj_color) if self._obj_color
                else (250, 187, 130))
        quads = nurbs.shade_grid(grid, base=base,
                                 max_edge=max(spans) * 0.35 + 1e-9)
        if quads:
            self.eng.add_mesh(quads)
        return (f'参数曲面 r(u,v) · {nu}×{nv} 网格 · {len(quads)} 面片'
                f' · u∈[{u0:g},{u1:g}], v∈[{v0:g},{v1:g}]')

    def _plot_inequality2d(self, spec):
        conds = spec['conds']
        runs = region_runs(conds, spec['x_range'], spec['y_range'], n=150)
        quads = [(((a, c, 0.0), (b, c, 0.0), (b, d, 0.0), (a, d, 0.0)),
                  FILL_STYLE) for a, c, b, d in runs]
        if quads:
            self.eng.add_mesh(quads)
        col = self._obj_color or BOUND_COLOR
        pairs = [(F, spec['x_range'], spec['y_range'], 0.0)
                 for F, pos in conds]
        self._curve_srcs.append(('ineq_bounds', pairs, col))
        return (f'不等式区域（{len(conds)} 个条件取交集）· '
                f'{len(runs)} 填充块 + 自适应边界')

    def _plot_inequality3d(self, spec):
        F, pos = spec['conds'][0]
        xr, yr, zr = spec['x_range'], spec['y_range'], spec['z_range']
        base = (engine3d.hex_to_rgb(self._obj_color) if self._obj_color
                else (176, 196, 250))
        tris, info = marching_cubes_adaptive(F, xr, yr, zr, base=base)
        if tris:                                     # 半透明边界壳
            self.eng.add_mesh([(P, (col, 'gray50')) for P, col in tris])
        nrun = 0
        note = ''
        if zr[0] <= 0 <= zr[1]:                      # z=0 截面填充
            F2 = lambda x, y: F(x, y, 0.0)
            runs = region_runs([(F2, pos)], xr, yr, n=120)
            quads = [(((a, c, 0.0), (b, c, 0.0), (b, d, 0.0), (a, d, 0.0)),
                      FILL_STYLE) for a, c, b, d in runs]
            if quads:
                self.eng.add_mesh(quads)
            nrun = len(runs)
        else:
            note = ' · z=0 不在定义域, 截面省略'
        return (f'不等式体 · {info} · {len(tris)} 边界三角形(半透明) + '
                f'{nrun} z=0 截面块{note}')

    def _plot_mesh(self, spec):
        """预制网格对象（旋转成面等建模工具产出）直接入场景"""
        self.eng.add_mesh(spec['quads'])
        return f'网格曲面 · {len(spec["quads"])} 面片'

    # ---------- 函数库菜单 ----------
    def _rebuild_lib_menu(self, init=False):
        grouped, warns = curve_library.load_all()
        menu = tk.Menu(self.lib_btn, tearoff=0)
        total = n_user = 0
        for cat, entries in grouped:
            sub = tk.Menu(menu, tearoff=0)
            for e in entries:
                sub.add_command(label=e['name'],
                                command=lambda item=e: self.load_entry(item))
            menu.add_cascade(label=f'{cat} ({len(entries)})', menu=sub)
            total += len(entries)
            n_user += sum(1 for e in entries if e.get('user'))
        menu.add_separator()
        am = tk.Menu(menu, tearoff=0)
        for p in ANIM_PRESETS:
            am.add_command(label=p['name'],
                           command=lambda pp=p: self._load_anim_preset(pp))
        menu.add_cascade(label=f'▶ 动画演示 ({len(ANIM_PRESETS)})', menu=am)
        menu.add_command(label='🖼 曲线画廊（缩略图 + 搜索）',
                         command=self._open_gallery)
        menu.add_command(label='📖 生成《曲线图鉴》HTML',
                         command=self._make_atlas)
        menu.add_command(label='🎲 随机一曲', command=self._random_entry)
        menu.add_command(label='↻ 重载用户配置',
                         command=lambda: self._rebuild_lib_menu())
        self.lib_btn['menu'] = menu
        if warns:
            self._status(('⚠ ' if init else '↻ 重载完成 · ') + '；'.join(warns),
                         '#f9e2af')
        elif not init:
            self._status(f'↻ 函数库已加载: 共 {total} 条（自定义 {n_user}）', '#a6e3a1')

    def load_entry(self, e):
        """函数库一键调用: 载入表达式 + 绘制 + 状态行附注说明"""
        self.load(e['expr'])
        if e.get('desc') and self.status.cget('text').startswith('✓'):
            self.status.config(
                text=self.status.cget('text') + '  ·  ' + e['desc'])

    def _open_gallery(self):
        """曲线画廊: 缩略图网格 + 搜索, 点击一键载入"""
        import gallery
        win = getattr(self, '_gallery_win', None)
        if win is not None and win.winfo_exists():
            win.deiconify()
            win.lift()
            return
        self._gallery_win = gallery.GalleryWindow(self.winfo_toplevel(),
                                                  on_pick=self.load_entry)

    def _make_atlas(self):
        """生成《曲线图鉴》单文件 HTML（本地 KaTeX 内联）"""
        import atlas_gen
        try:
            path = atlas_gen.generate()
        except Exception as ex:
            self._status(f'⚠ 图鉴生成失败: {ex}', '#f38ba8')
            return
        self._status(f'📖 图鉴已生成: {path}', '#a6e3a1')
        try:
            import webbrowser
            webbrowser.open(path)          # WSL 下失败也无妨, 路径已提示
        except Exception:
            pass

    def _load_anim_preset(self, p):
        """动画演示预设: 载入参数族表达式 → 设滑块范围 → 自动播放"""
        if self._play_id is not None:
            self._toggle_play()
        self.load(p['expr'])
        self.sld_vars['a'].set(str(p['lo']))
        self.sld_vars['b'].set(str(p['hi']))
        self.sld_vars['d'].set(str(p['step']))
        self._apply_slider_bounds()
        if self._slider_param != p['param']:
            self._select_param(p['param'])
        if self._play_id is None:
            self._toggle_play()
        self._status(f'▶ 动画演示: {p["name"]} · {p["desc"]}', '#a6e3a1')

    def _random_entry(self):
        """随机一曲: 从全部库条目中随机载入"""
        import random
        entries = [e for _, v in curve_library.load_all()[0] for e in v]
        if entries:
            self.load_entry(random.choice(entries))

    def _export_model(self, fmt):
        """导出 OBJ/STL: 优先选中对象的网格, 否则全场景"""
        import export3d
        sel = self._selected_obj()
        if sel is not None and sel.get('mesh_idx') is not None:
            meshes = [self.eng.meshes[sel['mesh_idx']]]
            tag = f'O{sel["id"]}'
        else:
            meshes = [m for m in self.eng.meshes if m]
            tag = 'scene'
        if not meshes:
            self._status('❌ 无可导出网格（需曲面类对象: 显式/参数/隐式曲面）',
                         '#f38ba8')
            return
        path = filedialog.asksaveasfilename(
            defaultextension='.' + fmt, parent=self.winfo_toplevel(),
            filetypes=[('OBJ 模型', '*.obj') if fmt == 'obj'
                       else ('STL 模型', '*.stl')])
        if not path:
            return
        try:
            n = (export3d.export_obj(meshes, path, tag) if fmt == 'obj'
                 else export3d.export_stl(meshes, path, tag))
        except OSError as e:
            self._status(f'❌ 导出失败: {e}', '#f38ba8')
            return
        self._status(f'✓ 已导出 {n} 三角形 → {path}', '#a6e3a1')

    def _add_slice(self):
        """截面工具: 对选中隐式曲面 F(x,y,z)=0 截 z=h, 轮廓线加入场景"""
        from tkinter import simpledialog
        sel = self._selected_obj()
        if not sel or sel['kind'] not in ('implicit3d', 'inequality3d'):
            self._status('❌ 截面需先选中隐式曲面 F(x,y,z)=0 或不等式体',
                         '#f38ba8')
            return
        spec0 = sel['spec']
        F0 = spec0['F'] if sel['kind'] == 'implicit3d' else spec0['conds'][0][0]
        z0, z1 = spec0['z_range']
        h = simpledialog.askfloat(
            '截面', f'截面高度 z = ?（范围 {z0:g} … {z1:g}）',
            initialvalue=0.0, parent=self.winfo_toplevel())
        if h is None:
            return
        F2 = lambda x, y, _F=F0, _h=h: _F(x, y, _h)
        spec = {'kind': 'implicit2d', 'F': F2, 'params': {},
                'x_range': spec0['x_range'], 'y_range': spec0['y_range'],
                'z_level': h, 'plain': f'截面 z={h:g}', 'latex': False}
        oid = self._next_id
        self._next_id += 1
        col = self._next_color()
        obj = {'id': oid, 'name': f'O{oid}·截面 z={h:g}',
               'kind': 'implicit2d', 'expr': f'{sel["expr"]} @ z={h:g}',
               'spec': spec, 'color': col, 'visible': True, 'mesh_idx': None}
        self.objects.append(obj)
        self._sel_id = oid
        self._rebuild_tree()
        self._render_scene()
        self._status(f'✓ 已添加截面 z={h:g}（绿色轮廓, 可随场景缩放自适应）',
                     '#a6e3a1')

    # ---------- 辅助 ----------
    def _curve_polyline(self, spec):
        """曲线对象 spec → 采样点列（旋转成面等建模用）; 非曲线返回 None"""
        kind = spec['kind']
        N = 200
        if kind == 'parametric':
            c = spec['comps']
            lo, hi = spec['t_range']
            pts = [(c['x'](t) if 'x' in c else 0.0,
                    c['y'](t) if 'y' in c else 0.0,
                    c['z'](t) if 'z' in c else 0.0)
                   for t in (lo + (hi - lo) * i / N for i in range(N + 1))]
            return [p for p in pts if all(math.isfinite(v) for v in p)]
        if kind == 'explicit2d':
            f = spec['f']
            if spec.get('var') == 'y':
                lo, hi = spec['y_range']
                pts = [(f(v), v, 0.0)
                       for v in (lo + (hi - lo) * i / N for i in range(N + 1))]
            else:
                lo, hi = spec['x_range']
                pts = [(v, f(v), 0.0)
                       for v in (lo + (hi - lo) * i / N for i in range(N + 1))]
            return [p for p in pts if all(math.isfinite(v) for v in p)]
        if kind == 'implicit2d':
            zl = spec.get('z_level', 0.0)
            segs = marching_squares(spec['F'], spec['x_range'],
                                    spec['y_range'], n=160)
            chains = chain_segments(segs)
            if not chains:
                return None
            chain = max(chains, key=len)     # 多分支取最长链
            return [(p[0], p[1], p[2] + zl) for p in chain]
        return None

    def _revolve_dialog(self):
        """🌀 旋转成面: 选一条平面曲线 + 一条轴直线 → nurbs 旋转面入场景"""
        import nurbs
        curve_objs = [o for o in self.objects
                      if o['kind'] in ('parametric', 'explicit2d', 'implicit2d')]
        if not curve_objs:
            self._status('❌ 旋转成面需先添加平面曲线对象（显式/隐式/参数曲线）',
                         '#f38ba8')
            return
        win = tk.Toplevel(self.winfo_toplevel())
        win.title('🌀 曲线绕轴旋转成面')
        win.configure(bg=BG)
        win.geometry('470x250')
        win.transient(self.winfo_toplevel())
        F = ('DejaVu Sans', engine3d.font_size(10))

        def row(parent, text):
            r = tk.Frame(parent, bg=BG)
            r.pack(fill='x', padx=12, pady=3)
            tk.Label(r, text=text, bg=BG, fg='#cdd6f4', font=F,
                     width=10, anchor='w').pack(side='left')
            return r

        tk.Label(win, text='选中的平面曲线绕指定直线旋转一周生成曲面',
                 bg=BG, fg='#9aa0b4', font=F).pack(padx=12, pady=(10, 4))
        r1 = row(win, '平面曲线')
        names = [o['name'] for o in curve_objs]
        curve_box = ttk.Combobox(r1, values=names, state='readonly', width=34)
        sel = self._selected_obj()
        curve_box.current(names.index(sel['name'])
                          if sel and sel['name'] in names else 0)
        curve_box.pack(side='left')
        r2 = row(win, '轴点 P0')
        p0_ent = tk.Entry(r2, bg='#181825', fg='#cdd6f4', relief='flat',
                          insertbackground='#cdd6f4', font=('Consolas', F[1]))
        p0_ent.insert(0, '(0,0,0)'); p0_ent.pack(side='left', fill='x', expand=True)
        r3 = row(win, '轴点 P1')
        p1_ent = tk.Entry(r3, bg='#181825', fg='#cdd6f4', relief='flat',
                          insertbackground='#cdd6f4', font=('Consolas', F[1]))
        p1_ent.insert(0, '(0,0,1)'); p1_ent.pack(side='left', fill='x', expand=True)
        r4 = row(win, '周向分段')
        n_ent = tk.Entry(r4, bg='#181825', fg='#cdd6f4', relief='flat',
                         insertbackground='#cdd6f4', width=6,
                         font=('Consolas', F[1]))
        n_ent.insert(0, '36'); n_ent.pack(side='left')
        tk.Label(r4, text='（越大越圆滑, 建议 24–72）', bg=BG,
                 fg='#5b6178', font=F).pack(side='left', padx=8)

        def do():
            try:
                p0 = nurbs.parse_point(p0_ent.get())
                p1 = nurbs.parse_point(p1_ent.get())
                n_seg = max(6, int(n_ent.get()))
            except (ValueError, IndexError) as e:
                self._status(f'❌ 轴参数无法解析: {e}', '#f38ba8')
                return
            obj = curve_objs[curve_box.current()]
            pts = self._curve_polyline(obj['spec'])
            if not pts:
                self._status('❌ 未能从该曲线采样到点列', '#f38ba8')
                return
            try:
                quads = revolve_curve(pts, p0, p1, n_seg=n_seg)
            except Exception as e:
                self._status(f'❌ 旋转成面失败: {e}', '#f38ba8')
                return
            spec = {'kind': 'mesh', 'quads': quads, 'params': {},
                    'plain': f'{obj["name"]} ⤾ 轴', 'latex': False}
            oid = self._next_id
            self._next_id += 1
            col = self._next_color()
            new = {'id': oid, 'name': f'O{oid}·旋转面', 'kind': 'mesh',
                   'expr': f'{obj["expr"]} ⤾ ({p0}→{p1})', 'spec': spec,
                   'color': col, 'visible': True, 'mesh_idx': None}
            self.objects.append(new)
            self._sel_id = oid
            self._rebuild_tree()
            self._render_scene()
            self._status(f'✓ 旋转面已生成: {len(quads)} 面片 · 绕轴 '
                         f'{p0}→{p1} · 可导出 OBJ/STL', '#a6e3a1')
            win.destroy()

        bb = tk.Frame(win, bg=BG)
        bb.pack(fill='x', padx=12, pady=(8, 10))
        tk.Button(bb, text='生成旋转面', command=do, bg='#89b4fa',
                  fg='#1e1e2e', relief='flat', font=F,
                  padx=14).pack(side='left')
        tk.Button(bb, text='取消', command=win.destroy, bg='#45475a',
                  fg='#cdd6f4', relief='flat', font=F,
                  padx=14).pack(side='left', padx=8)

    # ---------- 其它辅助 ----------
    def load(self, expr):
        self.entry.delete(0, 'end')
        self.entry.insert(0, expr)
        self.plot()

    def clear(self):
        self.eng.clear_all()
        self._status(self.HELP, '#9aa0b4')

    def _status(self, text, color):
        self.status.config(text=text, fg=color)

    # ---------- 曲面分析 ----------
    def _set_analysis(self, mode):
        if not self._geo:
            return
        if mode == self._analysis:                   # 再点一次 = 关闭
            mode = None
        self._analysis = mode
        idx = self._ana_mesh_idx
        if idx is None or idx >= len(self.eng.meshes):
            return
        self.eng.meshes[idx] = list(self._base_meshes[0])
        self._arrows, self._cbar = [], None
        self._pd_lines = []
        for k, b in self.an_btns.items():
            on = (k == mode)
            b.config(bg='#89b4fa' if on else '#313244',
                     fg='#1e1e2e' if on else '#9aa0b4')
        if mode == 'normals':
            self._arrows = surf_analysis.normal_arrows(self._geo)
            self.eng.post_draw = self._draw_analysis_overlay
            self._status(f'法向量场 · 面积加权逐顶点法向量 · {len(self._arrows)} 支箭头'
                         f'（拖动旋转观察朝向）', '#cdd6f4')
        elif mode in ('K', 'H'):
            tris, (lo, hi) = surf_analysis.colorize(self._geo, mode)
            self.eng.meshes[idx] = tris
            self._cbar = (lo, hi, 'diverge' if mode == 'K' else 'seq')
            self._cbar_title = '高斯曲率 K' if mode == 'K' else '平均曲率 |H|'
            self.eng.post_draw = self._draw_analysis_overlay
            vals = self._geo[mode]
            if mode == 'K':
                self._status(f'高斯曲率 K（角亏缺, 内蕴量）∈ [{min(vals):.4g}, {max(vals):.4g}]'
                             f' · 蓝=负(鞍部) 白=0 红=正 · 球面理论值 1/r²', '#cdd6f4')
            else:
                self._status(f'平均曲率 |H|（余切 Laplacian）∈ [{min(vals):.4g}, {max(vals):.4g}]'
                             f' · 球面理论值 1/r · 极小曲面 H=0', '#cdd6f4')
        elif mode == 'PD':
            if self._pdirs is None:
                self._pdirs = surf_analysis.principal_dirs(self._geo)
            pd = self._pdirs
            pts = self._geo['pts']
            stride = max(1, len(pts) // 140)
            s1 = sorted(abs(v) for v in pd['k1'])
            med1 = s1[len(s1) // 2] or 1.0
            L0 = self._geo['span'] * 0.06
            lines = []
            for i in range(0, len(pts), stride):
                if pd['d1'][i] is None:
                    continue
                p = pts[i]
                for kval, dv, col in ((pd['k1'][i], pd['d1'][i], '#f38ba8'),
                                      (pd['k2'][i], pd['d2'][i], '#89b4fa')):
                    L = L0 * min(1.6, max(0.25, abs(kval) / med1))
                    lines.append(((p[0] - dv[0] * L, p[1] - dv[1] * L,
                                   p[2] - dv[2] * L),
                                  (p[0] + dv[0] * L, p[1] + dv[1] * L,
                                   p[2] + dv[2] * L), col, 2))
            self._pd_lines = lines
            self.eng.post_draw = self._draw_analysis_overlay
            self._status(f'主曲率方向 · k1 ∈ [{min(pd["k1"]):.4g},{max(pd["k1"]):.4g}]'
                         f'（红, 长度∝|k|）· k2 ∈ [{min(pd["k2"]):.4g},'
                         f'{max(pd["k2"]):.4g}]（蓝）· 2-ring 二次曲面片拟合', '#cdd6f4')
        else:
            self.eng.post_draw = None
            self._status('分析已关闭 · 恢复原始着色', '#9aa0b4')
        self.eng._redraw_soon()
    # ---------- 自适应采样（多对象曲线光滑） ----------
    def _refine_all(self):
        """按屏幕空间自适应采样重建场景全部曲线对象"""
        eng = self.eng
        curves, segments = [], []
        for src in self._curve_srcs:
            if src[0] == 'explicit':
                _, f, var, (a, b), col = src
                def pt(s, f=f, a=a, b=b, var=var):
                    v = a + (b - a) * s
                    fv = f(v)
                    return (v, fv, 0.0) if var == 'x' else (fv, v, 0.0)
                pts = eng.adaptive_polyline(pt)
                runs = split_runs(pts, jump=(b - a) * 2)
                curves.extend((r, col, 2) for r in runs)
            elif src[0] == 'param':
                _, comps, (t0, t1), col = src
                zero = lambda t: 0.0
                fx = comps.get('x', zero)
                fy = comps.get('y', zero)
                fz = comps.get('z', zero)
                def pt(s, fx=fx, fy=fy, fz=fz, t0=t0, t1=t1):
                    t = t0 + (t1 - t0) * s
                    return (fx(t), fy(t), fz(t))
                pts = eng.adaptive_polyline(pt)
                fins = [p for p in pts if all(math.isfinite(c) for c in p)]
                if not fins:
                    continue
                spans = [max(p[k] for p in fins) - min(p[k] for p in fins)
                         for k in range(3)]
                runs = split_runs(pts, jump=max(spans) * 0.6 + 1e-9)
                curves.extend((r, col, 2) for r in runs)
            elif src[0] in ('implicit2d', 'ineq_bounds'):
                _, pairs, col = src
                cam = eng.cam
                w, h = eng._size()
                n = int(160 * min(2.25, max(1.0, (cam.zoom / 90.0) ** 0.5)))
                all_segs = []
                for F, xr, yr, zl in pairs:
                    base = marching_squares(F, xr, yr, n=n)
                    segs = refine_implicit(F, base, cam, w, h)
                    if zl:                        # 截面抬升到 z=h
                        segs = [((a[0], a[1], zl), (b[0], b[1], zl))
                                for a, b in segs]
                    all_segs.extend(segs)
                if all_segs:
                    segments.append((all_segs, col, 2))
        eng.curves = curves
        eng.segments = segments
        return (sum(len(r) for r, c, wd in curves)
                + sum(len(s) for s, c, wd in segments))

    def _schedule_refine(self):
        """视图变化（缩放/平移）→ 防抖自适应重建曲线"""
        if not getattr(self, '_curve_srcs', None):
            return
        if not self._refine_pending:
            self._refine_pending = True
            self.after_idle(self._do_refine)

    def _do_refine(self):
        self._refine_pending = False
        try:
            self._refine_all()
        except Exception:
            return
        self.eng._redraw_soon()

    # ---------- 对象列表操作 ----------
    def _rebuild_tree(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for obj in self.objects:
            tag = f'c{obj["color"]}'
            if tag not in self._tree_tags:
                self.tree.tag_configure(tag, foreground=obj['color'])
                self._tree_tags.add(tag)
            tags = (tag,) if obj['visible'] else (tag, 'hidden')
            self.tree.insert('', 'end', iid=str(obj['id']),
                             values=(obj['id'], '✓' if obj['visible'] else '—',
                                     obj['name'], obj['color'],
                                     obj['expr'][:22]),
                             tags=tags)
        if self._sel_id is not None:
            s = str(self._sel_id)
            if s in self.tree.get_children():
                self.tree.selection_set(s)
                self.tree.see(s)

    def _on_tree_select(self, ev=None):
        s = self.tree.selection()
        if not s:
            return
        new_id = int(s[0])
        if new_id == self._sel_id:          # 程序性 selection_set 的回声事件
            return
        self._sel_id = new_id
        sel = self._selected_obj()
        if sel:
            self._spec = sel['spec']
            self._init_slider(sel['spec'])
            self._post_render_scene()
            self.eng._redraw_soon()

    def _on_tree_double(self, ev=None):
        """双击 → 定义载入输入框（可编辑后添加为新对象）"""
        sel = self._selected_obj()
        if sel:
            self.entry.delete(0, 'end')
            self.entry.insert(0, sel['expr'])
            self.entry.focus_set()

    def _on_tree_click(self, ev):
        """单击「显」列 → 直接切换该行显隐（不改变选中项）"""
        if self.tree.identify_column(ev.x) != '#2':
            return
        row = self.tree.identify_row(ev.y)
        obj = next((o for o in self.objects if str(o['id']) == row), None)
        if not obj:
            return
        obj['visible'] = not obj['visible']
        self._rebuild_tree()
        self._render_scene()
        self._status(f'✓ {obj["name"]} {"显示" if obj["visible"] else "隐藏"}',
                     '#a6e3a1')
        return 'break'

    def _delete_obj(self):
        sel = self._selected_obj()
        if not sel:
            return
        self.objects.remove(sel)
        self._sel_id = self.objects[-1]['id'] if self.objects else None
        self._rebuild_tree()
        self._render_scene()
        self._status(f'✓ 已删除 {sel["name"]} · 余 {len(self.objects)} 个对象',
                     '#a6e3a1')

    def _toggle_visible(self):
        sel = self._selected_obj()
        if not sel:
            return
        sel['visible'] = not sel['visible']
        self._rebuild_tree()
        self._render_scene()
        self._status(f'✓ {sel["name"]} {"显示" if sel["visible"] else "隐藏"}',
                     '#a6e3a1')

    def _clear_objs(self):
        self.objects = []
        self._sel_id = None
        self._rebuild_tree()
        self._render_scene()
        self._status('✓ 场景已清空', '#a6e3a1')

    def _obj_color_btn(self):
        from tkinter import colorchooser
        sel = self._selected_obj()
        if not sel:
            self._status('请先在对象列表点选一个对象', '#f9e2af')
            return
        rgb, hexcol = colorchooser.askcolor(parent=self.winfo_toplevel(),
                                           title=f'对象 {sel["name"]} 颜色')
        if not hexcol:
            return
        sel['color'] = hexcol
        self._rebuild_tree()
        self._render_scene(status=False)
        self._status(f'✓ {sel["name"]} 颜色 → {hexcol}', '#a6e3a1')

    def _toggle_axes(self):
        """坐标轴开关（与引擎快捷键 a 同步）"""
        on = not self.eng.show_axes
        self.eng.show_axes = on
        self.axes_btn.config(bg='#89b4fa' if on else '#313244',
                             fg='#1e1e2e' if on else '#cdd6f4')
        self.eng._redraw_soon()

    def _toggle_cue(self):
        on = self.eng.depth_cue <= 0
        self.eng.set_depth_cue(0.65 if on else 0.0)
        self.cue_btn.config(bg='#89b4fa' if on else '#313244',
                            fg='#1e1e2e' if on else '#9aa0b4')
        self._status(('✓ 景深开 — 远处对象向背景色淡出（纵深 cues 0.65）'
                      if on else '景深关'),
                     '#a6e3a1' if on else '#9aa0b4')

    def _post_render_scene(self):
        """渲染后处理: 分析态指向选中曲面对象"""
        self._analysis = None
        self._arrows, self._cbar = [], None
        self._pdirs, self._pd_lines = None, []
        self.eng.post_draw = None
        sel = self._selected_obj()
        can = (sel and sel['visible'] and sel['mesh_idx'] is not None
               and sel['kind'] in SURFACE_KINDS)
        if can:
            idx = sel['mesh_idx']
            self._ana_mesh_idx = idx
            self._base_meshes = [list(self.eng.meshes[idx])]
            self._geo = surf_analysis.analyze(self.eng.meshes[idx:idx + 1])
        else:
            self._ana_mesh_idx = None
            self._base_meshes, self._geo = None, None
        for b in self.an_btns.values():
            b.config(state='normal' if (can and self._geo) else 'disabled',
                     bg='#313244', fg='#9aa0b4')
        for b in self.mode_btns.values():
            b.config(state='normal' if bool(self.eng.meshes) else 'disabled')

    def _set_surface_mode(self, key):
        self.eng.set_surface_mode(key)
        for k, b in self.mode_btns.items():
            on = k == key
            b.config(bg='#89b4fa' if on else '#313244',
                     fg='#1e1e2e' if on else '#9aa0b4')
        names = {'solid': '实体着色', 'wire': '线框（线划图, 更快）',
                 'both': '实体 + 线框'}
        self._status(f'✓ 曲面渲染: {names[key]}', '#a6e3a1')

    # ---------- 参数滑块 ----------
    def _init_slider(self, spec, stop_play=True):
        """新表达式绘制后: 检测参数 → 启用滑块/下拉/播放
        stop_play=False 用于播放步进中的重渲染（不中断播放）"""
        if stop_play and self._play_id is not None:
            self._toggle_play()
        names = list(spec.get('params', {}).keys())
        if not names:
            self._slider_param = None
            self.t_label.config(text='t = —')
            self._set_slider_enabled(False)
            return
        menu = self.param_menu['menu']
        menu.delete(0, 'end')
        for nm in names:
            menu.add_command(label=nm,
                             command=lambda n=nm: self._select_param(n))
        self._set_slider_enabled(True)
        prefer = 't' if 't' in names else names[0]
        self._slider_param = prefer
        self.param_var.set(prefer)
        g = self._grid()
        if g:
            a, d, N = g
            hi = a + N * d
        else:
            try:
                a = float(self.sld_vars['a'].get())
                b = float(self.sld_vars['b'].get())
            except ValueError:
                a, b = -5.0, 5.0
            d, hi = None, b
        v = max(a, min(hi, spec['params'][prefer]))
        self._set_slider_silent(v)
        if v != spec['params'][prefer]:          # 被钳制 → 同步重渲染
            spec['params'][prefer] = v
            self._render_current()
        txt = f'{prefer} = {v:.4g}'
        if d:
            txt += f' (n={max(0, min(N, round((v - a) / d)))})'
        self.t_label.config(text=txt)

    def _set_slider_enabled(self, on):
        st = 'normal' if on else 'disabled'
        self.param_menu.config(state=st)
        self.slider.state(['!disabled'] if on else ['disabled'])
        self.play_btn.config(state=st)

    def _grid(self):
        """播放/吸附网格: t = a + n·d, n ∈ [0, N], N = ⌊(b−a)/d⌋。
        返回 (a, d, N); 输入非法返回 None。"""
        try:
            a = float(self.sld_vars['a'].get())
            b = float(self.sld_vars['b'].get())
            d = float(self.sld_vars['d'].get())
        except ValueError:
            return None
        if not (math.isfinite(a) and math.isfinite(b) and math.isfinite(d)
                and a < b and d > 0):
            return None
        # +1e-9 容差: 避免 1.0//0.1=9 这类浮点截断（数学上应为 10）
        return a, d, int(math.floor((b - a) / d + 1e-9))

    def _apply_slider_bounds(self, *_):
        """a/b/d 输入变化 → 滑块量程设为 [a, a+N·d] 并吸附当前值"""
        try:
            a = float(self.sld_vars['a'].get())
            b = float(self.sld_vars['b'].get())
        except ValueError:
            return
        if not (math.isfinite(a) and math.isfinite(b) and a < b):
            return
        g = self._grid()
        hi = (g[0] + g[2] * g[1]) if g else b
        self.slider.config(from_=a, to=hi)
        if self._slider_param:
            v = max(a, min(hi, self.slider.get()))
            self._set_slider_silent(v)
            self._on_slider(str(v))

    def _select_param(self, name):
        self._slider_param = name
        self.param_var.set(name)
        spec = getattr(self, '_spec', None)
        if spec and name in spec.get('params', {}):
            try:
                a = float(self.sld_vars['a'].get())
                b = float(self.sld_vars['b'].get())
            except ValueError:
                a, b = -5.0, 5.0
            v = max(a, min(b, spec['params'][name]))
            self._set_slider_silent(v)
            self._on_slider(str(v))

    def _on_slider(self, raw=None):
        """滑块事件: 吸附到网格 t = a + n·d → 更新参数 → 重渲染（保留相机）"""
        if getattr(self, '_slider_silent', False):
            return
        spec = getattr(self, '_spec', None)
        if not self._slider_param or not spec:
            return
        try:
            v = float(raw) if raw is not None else self.slider.get()
        except ValueError:
            return
        g = self._grid()
        if g:
            a, d, N = g
            n = max(0, min(N, round((v - a) / d)))
            v = a + n * d
        else:
            n = None
            v = max(float(self.slider.cget('from')),
                    min(float(self.slider.cget('to')), v))
        if abs(self.slider.get() - v) > 1e-9:      # 程序调用时同步滑块位置
            self._set_slider_silent(v)
        spec['params'][self._slider_param] = v
        txt = f'{self._slider_param} = {v:.4g}'
        if n is not None:
            txt += f' (n={n})'
        self.t_label.config(text=txt)
        self._render_current()

    def _set_slider_silent(self, v):
        """设置滑块位置但不触发回调（防重入/双重渲染）"""
        self._slider_silent = True
        self.slider.set(v)
        self._slider_silent = False

    def _render_current(self):
        """以当前参数重渲染整个场景（相机/对象表不变, 滑块/播放用）"""
        self._render_scene(status=False, keep_play=True)

    def _toggle_play(self):
        if self._play_id is not None:
            self.after_cancel(self._play_id)
            self._play_id = None
            self.play_btn.config(text='▶ 播放')
            return
        if not self._slider_param:
            return
        g = self._grid()
        if not g:
            self._status('❌ 播放需要 a < b 且增量 d > 0', '#f38ba8')
            return
        if g[2] < 1:
            self._status('❌ 步数 N=⌊(b−a)/d⌋ < 1，请调小 d 或加大 b−a',
                         '#f38ba8')
            return
        a, d, N = g
        self._play_n = max(0, min(N, round((self.slider.get() - a) / d)))
        self.play_btn.config(text='⏸ 暂停')
        self._play_id = self.after(80, self._play_step)

    def _play_step(self):
        """播放步进: n ← (n+1) mod (N+1), t = a + n·d（整数步进, 无浮点漂移）"""
        if self._play_id is None:
            return
        g = self._grid()
        if not g or g[2] < 1:
            self._toggle_play()
            return
        a, d, N = g
        self._play_n = (self._play_n + 1) % (N + 1)
        v = a + self._play_n * d
        self._set_slider_silent(v)
        self._on_slider(str(v))
        self._play_id = self.after(80, self._play_step)

    def _draw_analysis_overlay(self, w, h, emit):
        cam = self.eng.cam
        for a, b, col, wd in self._pd_lines:
            x1, y1, _ = cam.project(*a, w, h)
            x2, y2, _ = cam.project(*b, w, h)
            emit(('line', x1, y1, x2, y2, col, wd, None))
        for p, q in self._arrows:
            x1, y1, _ = cam.project(*p, w, h)
            x2, y2, _ = cam.project(*q, w, h)
            engine3d.emit_arrow(emit, x1, y1, x2, y2, '#94e2d5', 1.5, 7)
        if self._cbar:
            lo, hi, kind = self._cbar
            x0, y0, bw = w - 160, h - 36, 110
            nseg = 22
            for i in range(nseg):
                col = surf_analysis.colormap(i / (nseg - 1), kind)
                xa = x0 + i * bw / nseg
                xb = x0 + (i + 1) * bw / nseg
                emit(('poly', [(xa, y0), (xb, y0), (xb, y0 + 10),
                               (xa, y0 + 10)], col, col, None))
            emit(('text', x0, y0 + 22, f'{lo:.3g}', '#9aa0b4', 8, 'w', ''))
            emit(('text', x0 + bw, y0 + 22, f'{hi:.3g}', '#9aa0b4', 8,
                  'e', ''))
            emit(('text', x0 + bw / 2, y0 - 8, self._cbar_title, '#cdd6f4',
                  9, 'center', ''))

    # ---------- 导出与场景存档 ----------
    def _export(self, fmt):
        path = filedialog.asksaveasfilename(
            initialfile=f'plot3d.{fmt}', defaultextension=f'.{fmt}',
            filetypes=[(f'{fmt.upper()} 矢量', f'.{fmt}')])
        if not path:
            return
        try:
            if fmt == 'svg':
                self.eng.to_svg(path)
            else:
                self.eng.to_eps(path)
        except OSError as e:
            self._status(f'❌ 导出失败: {e}', '#f38ba8')
            return
        self._status(f'✓ 已导出 {path}', '#a6e3a1')

    def save_scene(self, path):
        data = {'app': 'plotter3d', 'version': 2,
                'camera': self.eng.camera_state(),
                'depth_cue': self.eng.depth_cue,
                'surface_mode': self.eng.surface_mode,
                'objects': [{'name': o['name'], 'expr': o['expr'],
                             'color': o['color'], 'visible': o['visible']}
                            for o in self.objects]}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_scene(self, path):
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        if data.get('app') != 'plotter3d':
            raise ValueError('不是 plotter3d 场景（样条场景请用样条设计器打开）')
        self.objects = []
        self._next_id = 1
        self._palette_i = 0
        if 'objects' in data:
            for o in data['objects']:
                self._add_object(o['expr'], o.get('color'), o.get('name'),
                                 o.get('visible', True), render=False)
        elif data.get('expr'):                     # v1 单表达式兼容
            self._add_object(data['expr'], render=False)
        self._rebuild_tree()
        self._render_scene()
        if 'camera' in data:
            self.eng.set_camera(data['camera'])
        if 'depth_cue' in data:
            self.eng.set_depth_cue(data['depth_cue'])
            on = data['depth_cue'] > 0
            self.cue_btn.config(bg='#89b4fa' if on else '#313244',
                                fg='#1e1e2e' if on else '#9aa0b4')
        if data.get('surface_mode'):
            self._set_surface_mode(data['surface_mode'])

    def _save_scene_dialog(self):
        path = filedialog.asksaveasfilename(
            initialfile='plot3d_scene.json', defaultextension='.json',
            filetypes=[('场景存档', '.json')])
        if not path:
            return
        try:
            self.save_scene(path)
        except OSError as e:
            self._status(f'❌ 保存失败: {e}', '#f38ba8')
            return
        self._status(f'✓ 场景已保存: {path}', '#a6e3a1')

    def _load_scene_dialog(self):
        path = filedialog.askopenfilename(filetypes=[('场景存档', '.json')])
        if not path:
            return
        try:
            self.load_scene(path)
        except (OSError, ValueError, json.JSONDecodeError) as e:
            self._status(f'❌ 载入失败: {e}', '#f38ba8')
            return
        self._status(f'✓ 场景已恢复: {path}', '#a6e3a1')

    # ---------- 动画导出 ----------
    def _anim_prims(self, nframes):
        """参数扫描帧生成器: r(t) 渐进描绘 / r(u,v) 沿 u 扫掠（临时替换引擎数据, 结束恢复）"""
        spec = getattr(self, '_spec', None)
        if not spec:
            raise ValueError('请先绘制一个图形')
        kind = spec['kind']
        if kind not in ('parametric', 'param_surface'):
            raise ValueError('动画导出仅支持参数曲线 r(t) 与参数曲面 r(u,v)')
        eng = self.eng
        saved = (eng.curves, eng.meshes, eng.segments, eng.post_draw)
        eng.post_draw = None
        w, h = eng._size()
        try:
            for k in range(nframes):
                prog = (k + 1) / nframes
                eng.curves, eng.meshes, eng.segments = [], [], []
                tip = None
                if kind == 'parametric':
                    comps = spec['comps']
                    t0, t1 = spec['t_range']
                    zero = lambda t: 0.0
                    fx = comps.get('x', zero)
                    fy = comps.get('y', zero)
                    fz = comps.get('z', zero)
                    te = t0 + (t1 - t0) * prog
                    n = max(8, int(1500 * prog))
                    pts = [(fx(t0 + (te - t0) * i / n),
                            fy(t0 + (te - t0) * i / n),
                            fz(t0 + (te - t0) * i / n)) for i in range(n + 1)]
                    eng.curves = [(pts, COLORS['parametric'], 2)]
                    tip = pts[-1]
                else:
                    comps = spec['comps']
                    zero = lambda u, v: 0.0
                    fx = comps.get('x', zero)
                    fy = comps.get('y', zero)
                    fz = comps.get('z', zero)
                    u0, u1 = spec['u_range']
                    v0, v1 = spec['v_range']
                    ue = u0 + (u1 - u0) * prog
                    nu, nv = max(2, int(42 * prog)), 42
                    grid = [[(fx(u0 + (ue - u0) * i / nu,
                                   v0 + (v1 - v0) * j / nv),
                             fy(u0 + (ue - u0) * i / nu,
                                v0 + (v1 - v0) * j / nv),
                             fz(u0 + (ue - u0) * i / nu,
                                v0 + (v1 - v0) * j / nv))
                             for j in range(nv + 1)] for i in range(nu + 1)]
                    fin = [p for row in grid for p in row
                           if all(math.isfinite(c) for c in p)]
                    if fin:
                        spans = [max(p[d] for p in fin) - min(p[d] for p in fin)
                                 for d in range(3)]
                        eng.meshes = [nurbs.shade_grid(
                            grid, base=(250, 187, 130),
                            max_edge=max(spans) * 0.35 + 1e-9)]
                prims = eng.build_prims(w, h, hud=False)
                if tip and all(math.isfinite(c) for c in tip):   # 笔尖标记
                    sx, sy, _ = eng.cam.project(*tip, w, h)
                    prims.append(('oval', sx - 5, sy - 5, sx + 5, sy + 5,
                                  '#f38ba8', '#f38ba8'))
                yield prims
        finally:
            eng.curves, eng.meshes, eng.segments, eng.post_draw = saved
            eng._redraw_soon()

    def _export_gif(self):
        from tkinter import simpledialog
        nframes = simpledialog.askinteger(
            '动画导出', '帧数（12 fps, 时长 = 帧数/12 秒）:',
            initialvalue=36, minvalue=6, maxvalue=120,
            parent=self.winfo_toplevel())
        if not nframes:
            return
        path = filedialog.asksaveasfilename(
            initialfile='anim.gif', defaultextension='.gif',
            filetypes=[('GIF 动画', '.gif')])
        if not path:
            return
        try:
            frames = list(self._anim_prims(nframes))
        except ValueError as e:
            self._status(f'❌ {e}', '#f38ba8')
            return
        try:
            import animate
            w, h = self.eng._size()
            imgs = [animate.prims_to_image(f, w, h) for f in frames]
            animate.save_gif(imgs, path)
        except Exception as e:
            self._status(f'❌ GIF 生成失败: {e}', '#f38ba8')
            return
        self._status(f'✓ 动画已导出 {path}（{nframes} 帧 · 12 fps）', '#a6e3a1')

    def _export_svg_seq(self):
        from tkinter import simpledialog
        nframes = simpledialog.askinteger(
            '动画导出', 'SVG 序列帧数:', initialvalue=24,
            minvalue=4, maxvalue=120, parent=self.winfo_toplevel())
        if not nframes:
            return
        d = filedialog.askdirectory()
        if not d:
            return
        try:
            frames = list(self._anim_prims(nframes))
        except ValueError as e:
            self._status(f'❌ {e}', '#f38ba8')
            return
        import animate
        w, h = self.eng._size()
        n = animate.write_svg_sequence(frames, d, w, h)
        self._status(f'✓ SVG 序列 frame_000…frame_{n - 1:03d}.svg → {d}',
                     '#a6e3a1')

    def _hist_prev(self, e):
        if not self.history:
            return 'break'
        self.hi = max(0, self.hi - 1)
        self.entry.delete(0, 'end')
        self.entry.insert(0, self.history[self.hi])
        return 'break'

    def _hist_next(self, e):
        if not self.history:
            return 'break'
        self.hi = min(len(self.history) - 1, self.hi + 1)
        self.entry.delete(0, 'end')
        self.entry.insert(0, self.history[self.hi])
        return 'break'


def main():
    root = tk.Tk()
    engine3d.apply_default_fonts(root)
    root.title('3D 函数绘图器 v2 · 表达式 → 图形（兼容 LaTeX）')
    root.geometry('1000x760')
    PlotterApp(root).pack(fill='both', expand=True)
    root.mainloop()


if __name__ == '__main__':
    main()
