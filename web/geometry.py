#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""geometry.py — 无头几何采样层（手机版 Web 渲染用）

把 mathparse 解析出的表达式采样成 Three.js 可直接消费的几何：
  - 曲线 (参数曲线/显式/隐式2D)  → type='lines'
  - 曲面 (参数曲面/显式 z=f/隐式3D) → type='mesh'
设计原则：数学全在本模块（复用 mathparse），前端零计算，手机也能跑。
依赖：numpy、scikit-image（marching_cubes / find_contours）。
"""
import math
import os
import sys

# 允许从 web/ 子目录导入上层 plot3d 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import mathparse

try:
    from skimage.measure import marching_cubes, find_contours
except Exception:                                   # pragma: no cover
    marching_cubes = None
    find_contours = None


def _safe(fn, nargs):
    """包装为异常/非有限安全的标量函数（返回 nan 而不是抛错）"""
    def g(*args):
        try:
            v = fn(*args[:nargs])
            return v if math.isfinite(v) else np.nan
        except Exception:
            return np.nan
    return g


def _flat(pts):
    return [round(float(c), 5) for p in pts for c in p]


def _bbox(pts):
    arr = np.asarray([p for p in pts if all(math.isfinite(c) for c in p)])
    if not len(arr):
        return [-1, 1, -1, 1, -1, 1]
    mn, mx = arr.min(axis=0), arr.max(axis=0)
    return [round(float(mn[i]), 4) for i in range(3)] + \
           [round(float(mx[i]), 4) for i in range(3)]


# ---------------- 曲线 ----------------

def _sample_param_curve(spec, n=700):
    comps = spec['comps']
    fx = comps.get('x'); fy = comps.get('y'); fz = comps.get('z')
    t0, t1 = spec['t_range']
    pts = []
    for i in range(n + 1):
        t = t0 + (t1 - t0) * i / n
        x = fx(t) if fx else 0.0
        y = fy(t) if fy else 0.0
        z = fz(t) if fz else 0.0
        if all(math.isfinite(c) for c in (x, y, z)):
            pts.append((x, y, z))
    return pts


def _sample_explicit2d(spec, n=600):
    f = _safe(spec['f'], 1)
    var = spec.get('var', 'x')
    xr = spec['x_range']
    pts = []
    xs = np.linspace(xr[0], xr[1], n + 1)
    for x in xs:
        y = f(x)
        if math.isfinite(y):
            pts.append((float(x), float(y), 0.0) if var == 'x'
                       else (float(y), float(x), 0.0))
    return pts


def _sample_implicit2d(spec, n=180):
    if find_contours is None:
        return []
    F = _safe(spec['F'], 2)
    xr, yr = spec['x_range'], spec['y_range']
    ys = np.linspace(yr[0], yr[1], n + 1)
    xs = np.linspace(xr[0], xr[1], n + 1)
    X, Y = np.meshgrid(xs, ys, indexing='xy')
    vF = np.vectorize(F, otypes=[float])
    Z = vF(X, Y)
    Z = np.nan_to_num(Z, nan=1e6, posinf=1e6, neginf=-1e6)
    lines = []
    for level in (0.0,):
        for c in find_contours(Z, level):
            pts = [(xr[0] + cc[1] * (xr[1] - xr[0]) / n,
                    yr[0] + cc[0] * (yr[1] - yr[0]) / n, 0.0) for cc in c]
            if len(pts) > 2:
                lines.append(pts)
    return lines


# ---------------- 曲面 ----------------

def _grid_mesh(pts2d, nu, nv):
    """(nu+1)*(nv+1) 顶点网格 → (vertices, faces)；剔除含 nan 的面"""
    verts = []
    idx = {}
    faces = []
    def vid(i, j):
        p = pts2d[i][j]
        if not all(math.isfinite(c) for c in p):
            return None
        key = (i, j)
        if key not in idx:
            idx[key] = len(verts)
            verts.append(p)
        return idx[key]
    for i in range(nu):
        for j in range(nv):
            a, b = vid(i, j), vid(i + 1, j)
            c, d = vid(i + 1, j + 1), vid(i, j + 1)
            if None not in (a, b, c):
                faces += [a, b, c]
            if None not in (a, c, d):
                faces += [a, c, d]
    return verts, faces


def _sample_param_surface(spec, nu=52, nv=52):
    comps = spec['comps']
    zero = lambda u, v: 0.0
    fx = comps.get('x', zero); fy = comps.get('y', zero); fz = comps.get('z', zero)
    u0, u1 = spec['u_range']; v0, v1 = spec['v_range']
    grid = []
    for i in range(nu + 1):
        u = u0 + (u1 - u0) * i / nu
        row = []
        for j in range(nv + 1):
            v = v0 + (v1 - v0) * j / nv
            try:
                row.append((fx(u, v), fy(u, v), fz(u, v)))
            except Exception:
                row.append((np.nan, np.nan, np.nan))
        grid.append(row)
    return _grid_mesh(grid, nu, nv)


def _sample_surface(spec, n=52):
    f = _safe(spec['f'], 2)
    xr, yr = spec['x_range'], spec['y_range']
    grid = []
    for i in range(n + 1):
        x = xr[0] + (xr[1] - xr[0]) * i / n
        row = []
        for j in range(n + 1):
            y = yr[0] + (yr[1] - yr[0]) * j / n
            z = f(x, y)
            row.append((x, y, z if math.isfinite(z) else np.nan))
        grid.append(row)
    return _grid_mesh(grid, n, n)


def _sample_implicit3d(spec, n=42):
    if marching_cubes is None:
        return [], []
    F = _safe(spec['F'], 3)
    xr, yr, zr = spec['x_range'], spec['y_range'], spec['z_range']
    xs = np.linspace(xr[0], xr[1], n + 1)
    ys = np.linspace(yr[0], yr[1], n + 1)
    zs = np.linspace(zr[0], zr[1], n + 1)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij')
    vF = np.vectorize(F, otypes=[float])
    vol = vF(X, Y, Z)
    vol = np.nan_to_num(vol, nan=1e6, posinf=1e6, neginf=-1e6)
    sp = ((xr[1] - xr[0]) / n, (yr[1] - yr[0]) / n, (zr[1] - zr[0]) / n)
    try:
        verts, faces, _, _ = marching_cubes(vol, level=0.0, spacing=sp)
    except Exception:
        return [], []
    verts = [(v[0] + xr[0], v[1] + yr[0], v[2] + zr[0]) for v in verts]
    flat_faces = [int(k) for tri in faces for k in tri]
    return verts, flat_faces


# ---------------- 入口 ----------------

CAT_COLORS = {
    '平面代数曲线': '#f9e2af', '极坐标曲线': '#74c7ec', '空间曲线': '#f38ba8',
    '经典曲面': '#89b4fa', '隐式曲面': '#89dceb', '极小曲面': '#a6e3a1',
    '参数曲面': '#fab387', '不等式区域': '#94e2d5', '未分类': '#cdd6f4',
}


def sample(expr, category='', faces=None):
    """表达式 → 几何 JSON。失败抛 mathparse.ParseError / ValueError。
    faces: 平直多面体的精确面数据（有则绕过 Marching Cubes, 边缘无锯齿）。"""
    spec = mathparse.parse_input(expr)
    kind = spec['kind']
    color = CAT_COLORS.get(category, '#cdd6f4')

    if faces:
        verts, idx = [], []
        for poly in faces:                          # 每面独立顶点 → 平板着色硬边
            b = len(verts)
            verts.extend([tuple(p) for p in poly])
            for i in range(1, len(poly) - 1):
                idx += [b, b + i, b + i + 1]
        return {'type': 'mesh', 'vertices': _flat(verts), 'faces': idx,
                'color': color, 'bbox': _bbox(verts), 'kind': 'polyhedron'}

    if kind == 'parametric':
        pts = _sample_param_curve(spec)
        if not pts:
            raise ValueError('参数曲线无有效采样点')
        return {'type': 'lines', 'lines': [_flat(pts)], 'color': color,
                'bbox': _bbox(pts), 'kind': kind}

    if kind in ('explicit2d',):
        pts = _sample_explicit2d(spec)
        if not pts:
            raise ValueError('显式曲线无有效采样点')
        return {'type': 'lines', 'lines': [_flat(pts)], 'color': color,
                'bbox': _bbox(pts), 'kind': kind}

    if kind == 'implicit2d':
        lines = _sample_implicit2d(spec)
        if not lines:
            raise ValueError('隐式曲线无有效采样点')
        return {'type': 'lines', 'lines': [_flat(p) for p in lines],
                'color': color,
                'bbox': _bbox([p for L in lines for p in L]), 'kind': kind}

    if kind == 'param_surface':
        verts, faces = _sample_param_surface(spec)
        if not faces:
            raise ValueError('参数曲面无有效面片')
        return {'type': 'mesh', 'vertices': _flat(verts), 'faces': faces,
                'color': color, 'bbox': _bbox(verts), 'kind': kind}

    if kind == 'surface':
        verts, faces = _sample_surface(spec)
        if not faces:
            raise ValueError('显式曲面无有效面片')
        return {'type': 'mesh', 'vertices': _flat(verts), 'faces': faces,
                'color': color, 'bbox': _bbox(verts), 'kind': kind}

    if kind == 'implicit3d':
        verts, faces = _sample_implicit3d(spec)
        if not faces:
            raise ValueError('隐式曲面无有效面片')
        return {'type': 'mesh', 'vertices': _flat(verts), 'faces': faces,
                'color': color, 'bbox': _bbox(verts), 'kind': kind}

    if kind in ('inequality2d', 'inequality3d'):
        raise ValueError('不等式区域暂不支持手机端渲染')

    raise ValueError(f'暂不支持的类型: {kind}')


if __name__ == '__main__':                    # 自检: 遍历内置库
    import curve_library
    grouped, warns = curve_library.load_all()
    entries = [e for _, v in grouped for e in v]
    ok, fail = 0, []
    for e in entries:
        try:
            g = sample(e['expr'], e['category'])
            ok += 1
        except Exception as ex:
            fail.append((e['key'], str(ex)[:50]))
    print(f'几何采样自检: {ok}/{len(entries)} 通过')
    for k, m in fail:
        print('  ✗', k, '-', m)
