#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""export3d.py — 网格导出: OBJ / STL（3D 打印）

引擎网格格式: [[(face_pts, color), ...]], face_pts 为 3 或 4 个世界坐标点。
四边面按 (0,1,2)+(0,2,3) 扇形三角化; 法向量按右手法则现场计算。
"""
import struct


def triangles(meshes):
    """所有网格 → 三角形生成器 (a, b, c)，跳过退化/非有限面片
    面片格式: (点集, 颜色字符串) 或 裸点集"""
    for faces in meshes:
        for face in faces:
            if (isinstance(face, (tuple, list)) and len(face) == 2
                    and isinstance(face[1], str)):
                pts = face[0]
            else:
                pts = face
            if not isinstance(pts, (list, tuple)) or len(pts) < 3:
                continue
            if any(len(p) < 3 or not all(_fin(c) for c in p[:3]) for p in pts):
                continue
            if len(pts) == 3:
                yield tuple(pts[0]), tuple(pts[1]), tuple(pts[2])
            else:
                for i in range(1, len(pts) - 1):
                    yield tuple(pts[0]), tuple(pts[i]), tuple(pts[i + 1])


def _fin(v):
    import math
    return math.isfinite(v)


def _normal(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    nl = (nx * nx + ny * ny + nz * nz) ** 0.5 or 1.0
    return nx / nl, ny / nl, nz / nl


def export_obj(meshes, path, name='plot3d'):
    """导出 Wavefront OBJ（顶点去重按面序写入, 每网格一个 group）。返回三角形数"""
    ntri = 0
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f'# plot3d export · {name}\n')
        vi = 1
        for mi, quads in enumerate(meshes):
            f.write(f'o mesh_{mi}\n')
            for a, b, c in triangles([quads]):
                for p in (a, b, c):
                    f.write(f'v {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n')
                f.write(f'f {vi} {vi + 1} {vi + 2}\n')
                vi += 3
                ntri += 1
    return ntri


def export_stl(meshes, path, solid='plot3d'):
    """导出二进制 STL（3D 打印标准格式）。返回三角形数"""
    tris = list(triangles(meshes))
    with open(path, 'wb') as f:
        header = f'plot3d {solid}'.encode()[:80]
        f.write(header + b'\0' * (80 - len(header)))
        f.write(struct.pack('<I', len(tris)))
        for a, b, c in tris:
            n = _normal(a, b, c)
            f.write(struct.pack('<3f', *n))
            f.write(struct.pack('<3f', *a[:3]))
            f.write(struct.pack('<3f', *b[:3]))
            f.write(struct.pack('<3f', *c[:3]))
            f.write(struct.pack('<H', 0))
    return len(tris)
