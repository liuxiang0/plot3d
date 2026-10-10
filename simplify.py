#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""simplify.py — 网格简化: Quadric Edge Collapse（Garland & Heckbert 1997）

设计文档 §34 所述"与八叉树正交的另一层优化": MC/参数网格提取后永久抽稀。
原理: 每顶点累积邻面平面二次型 Q=Σppᵀ(p=(a,b,c,d)); 边折叠代价 =
min_v̄ v̄ᵀ(Q_u+Q_v)v̄（最优收缩点解 3×3 线性系, 奇异时退端点/中点候选）。
堆驱动贪心折叠至目标三角形数。平面区域大幅合并、轮廓/特征保持。

入口:
  decimate(verts, faces, target_tris) -> (verts', faces')   索引式网格
  decimate_tris(tris, target_tris)    -> tris'              三角形元组列表(导出管线用)
"""
import heapq
import math

import numpy as np


def _plane_quadric(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    nl = math.sqrt(nx * nx + ny * ny + nz * nz)
    if nl < 1e-15:
        return None
    nx, ny, nz = nx / nl, ny / nl, nz / nl
    d = -(nx * a[0] + ny * a[1] + nz * a[2])
    p = np.array((nx, ny, nz, d))
    return np.outer(p, p)


def _cost(Qs, v):
    v4 = np.array((v[0], v[1], v[2], 1.0))
    return float(v4 @ Qs @ v4)


def _optimal(Qs, vu, vv):
    A, b = Qs[:3, :3], Qs[:3, 3]
    det = float(np.linalg.det(A))
    if abs(det) > 1e-10:                          # 病态时最优解会沿谷方向飞远
        try:
            vbar = np.linalg.solve(A, -b)
            if np.all(np.isfinite(vbar)):
                mid = (vu + vv) / 2
                reach = 3 * float(np.linalg.norm(vu - vv)) + 1e-9
                if float(np.linalg.norm(vbar - mid)) <= reach:
                    return _cost(Qs, vbar), vbar
        except np.linalg.LinAlgError:
            pass
    best, bp = None, None
    for cand in (vu, vv, (vu + vv) / 2):
        c = _cost(Qs, cand)
        if best is None or c < best:
            best, bp = c, cand
    return best, bp


def decimate(verts, faces, target_tris):
    """verts: [(x,y,z)...] faces: [(i,j,k)...] → 折叠至 ≤target_tris 面"""
    V = [np.array(v, float) for v in verts]
    F = [list(f) for f in faces]
    nf = len(F)
    if nf <= target_tris:
        return [tuple(v) for v in V], [tuple(f) for f in F]

    Q = [np.zeros((4, 4)) for _ in V]
    vfaces = [set() for _ in V]
    for fi, f in enumerate(F):
        q = _plane_quadric(V[f[0]], V[f[1]], V[f[2]])
        if q is None:
            continue
        for vi in f:
            Q[vi] = Q[vi] + q
            vfaces[vi].add(fi)
    edges = set()
    for f in F:
        for k in range(3):
            edges.add((min(f[k], f[k + 1 if k < 2 else 0]),
                       max(f[k], f[k + 1 if k < 2 else 0])))

    alive_v = [True] * len(V)
    alive_f = [True] * nf
    heap, tick = [], 0
    ver = [0] * len(V)

    def push(u, v):
        nonlocal tick
        Qs = Q[u] + Q[v]
        c, _ = _optimal(Qs, V[u], V[v])
        tick += 1
        heapq.heappush(heap, (c, tick, u, v, ver[u], ver[v]))

    for u, v in edges:
        push(u, v)

    while heap and nf > target_tris:
        c, _, u, v, vu_, vv_ = heapq.heappop(heap)
        if not (alive_v[u] and alive_v[v]) or ver[u] != vu_ or ver[v] != vv_:
            continue
        Qs = Q[u] + Q[v]
        _, vbar = _optimal(Qs, V[u], V[v])
        V[u] = vbar
        Q[u] = Qs
        # v 的邻面改挂 u; 含 u,v 的退化面删除
        for fi in list(vfaces[v]):
            f = F[fi]
            if u in f and v in f:
                alive_f[fi] = False
                nf -= 1
                for vi in f:
                    vfaces[vi].discard(fi)
            else:
                f[:] = [u if x == v else x for x in f]
                vfaces[u].add(fi)
        vfaces[v].clear()
        alive_v[v] = False
        ver[u] += 1
        nbrs = set()
        for fi in vfaces[u]:
            nbrs.update(F[fi])
        nbrs.discard(u)
        for w in nbrs:
            if alive_v[w]:
                push(u, w)

    out_v, idx = [], {}
    out_f = []
    for fi, f in enumerate(F):
        if not alive_f[fi]:
            continue
        ids = []
        for vi in f:
            if vi not in idx:
                idx[vi] = len(out_v)
                out_v.append(tuple(float(c) for c in V[vi]))
            ids.append(idx[vi])
        out_f.append(tuple(ids))
    return out_v, out_f


def decimate_tris(tris, target_tris):
    """三角形元组列表 [(a,b,c)...] → 去重索引化 → 折叠 → 三角形元组列表"""
    idx, verts, faces = {}, [], []
    for tri in tris:
        ids = []
        for p in tri:
            key = (round(p[0], 9), round(p[1], 9), round(p[2], 9))
            if key not in idx:
                idx[key] = len(verts)
                verts.append(key)
            ids.append(idx[key])
        if ids[0] != ids[1] and ids[1] != ids[2] and ids[0] != ids[2]:
            faces.append(tuple(ids))
    nv, nf = decimate(verts, faces, target_tris)
    return [(nv[a], nv[b], nv[c]) for a, b, c in nf]


if __name__ == '__main__':                     # 自检: UV 球 3200 → 800 面
    nu = nv = 40
    R = 2.0
    vs, fs = [], []
    for i in range(nu):
        for j in range(nv):
            u0, u1 = math.pi * i / nu, math.pi * (i + 1) / nu
            v0, v1 = 2 * math.pi * j / nv, 2 * math.pi * (j + 1) / nv
            a = len(vs); vs.append((R * math.sin(u0) * math.cos(v0),
                                    R * math.sin(u0) * math.sin(v0), R * math.cos(u0)))
            vs.append((R * math.sin(u1) * math.cos(v0),
                       R * math.sin(u1) * math.sin(v0), R * math.cos(u1)))
            vs.append((R * math.sin(u1) * math.cos(v1),
                       R * math.sin(u1) * math.sin(v1), R * math.cos(u1)))
            vs.append((R * math.sin(u0) * math.cos(v1),
                       R * math.sin(u0) * math.sin(v1), R * math.cos(u1)))
            fs.append((a, a + 1, a + 2)); fs.append((a, a + 2, a + 3))
    ov, of = decimate(vs, fs, 800)
    dev = max(abs(math.sqrt(x * x + y * y + z * z) - R) for x, y, z in ov)
    print(f'UV 球 {len(fs)} → {len(of)} 面 | 顶点径向偏差上限 {dev:.4f} (R={R})')
    assert len(of) <= 800 and dev < 0.12, '简化质量不达标'
    print('✓ Quadric Edge Collapse 自检通过')
