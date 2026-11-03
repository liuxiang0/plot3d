import math
import sys

import numpy as np
from skimage.measure import marching_cubes

TAU = 2 * math.pi

def P(x, y, z):
    return math.cos(x) + math.cos(y) + math.cos(z)

def G(x, y, z):
    return (math.sin(x) * math.cos(y) + math.sin(y) * math.cos(z)
            + math.sin(z) * math.cos(x))

def IWP_m(x, y, z):
    return (2 * (math.cos(x) * math.cos(y) + math.cos(y) * math.cos(z)
                 + math.cos(z) * math.cos(x))
            - (math.cos(2 * x) + math.cos(2 * y) + math.cos(2 * z)))

def IWP_p(x, y, z):
    return (2 * (math.cos(x) * math.cos(y) + math.cos(y) * math.cos(z)
                 + math.cos(z) * math.cos(x))
            + (math.cos(2 * x) + math.cos(2 * y) + math.cos(2 * z)))

def periodic_genus(f, level=0.0, n=56):
    xs = np.linspace(0, TAU, n + 1)
    X, Y, Z = np.meshgrid(xs, xs, xs, indexing='ij')
    vf = np.vectorize(f, otypes=[float])
    vol = vf(X, Y, Z)
    verts, faces, _, _ = marching_cubes(vol, level=level, spacing=(TAU / n,) * 3)
    # 周期归并: 2π 边界折回 0
    verts = np.where(verts > TAU - 1e-9, verts - TAU, verts)
    key = [tuple(np.round(v, 6)) for v in verts]
    idx = {}
    vid = []
    for k in key:
        if k not in idx:
            idx[k] = len(idx)
        vid.append(idx[k])
    V = len(idx)
    edges = set()
    F = 0
    comps = None
    good = 0
    for tri in faces:
        a, b, c = vid[tri[0]], vid[tri[1]], vid[tri[2]]
        if a == b or b == c or a == c:
            continue
        good += 1
        for e in ((a, b), (b, c), (a, c)):
            edges.add((min(e), max(e)))
    F = good
    E = len(edges)
    # 连通分量 (并查集)
    parent = list(range(V))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    comps = len({find(i) for i in range(V)})
    chi = V - E + F
    return chi, comps, F

for name, f in (('P', P), ('G', G), ('IWP_minus', IWP_m), ('IWP_plus', IWP_p)):
    chi, comps, F = periodic_genus(f)
    g = (2 - chi / comps) / 2 if comps else None
    print(f'{name}: chi={chi} comps={comps} faces={F} => 每胞亏格≈{(2 - chi) / 2 / comps if comps else -1:.2f}')
