#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_pde6.py — PDE 族⑥ 门禁（Kármán 涡街：点涡阵列流函数）

karman_street 四组检查：
1) 闭式流函数结构性质：x 周期 a（a/2 非周期）+ 闭式=截断点涡求和 + ∇²ψ=0（二阶收敛自证）
   + 涡核对数奇异 ψ(2r)−ψ(r) = −(Γ/2π)ln2
2) 刚性平移：周期条带精确核（cot 恒等式）给出 U=(Γ/2a)tanh(πb/a)，v≡0；无扰动积分形变≈机器精度
3) von Kármán 中性稳定比 b/a=0.28054：扰动不增长；b/a=0.40/0.50 指数失稳
4) 生成器与库：quads 顶点=解析 ψ、涡核剔除、bbox、条目/资料卡登记
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import curve_library as cl                        # noqa: E402
import gallery                                    # noqa: E402
import trisurf                                    # noqa: E402

OK = True
TWO_PI = 2.0 * math.pi
A, B, GAM = 1.0, 0.28054, 1.0          # 涡距 a、排距 b（von Kármán 比）、环量 Γ
HH = B / 2.0


def check(name, cond, detail=''):
    global OK
    print(('  ✓ ' if cond else '  ✗ ') + name + ('  ' + detail if detail else ''))
    if not cond:
        OK = False


def psi(X, Y, a=A, b=B, G=GAM):
    """双排交错点涡街精确流函数（无穷乘积恒等式的收敛闭式）"""
    h = b / 2.0
    k = TWO_PI / a
    t1 = np.cosh(k * (Y - h)) - np.cos(k * X)
    t2 = np.cosh(k * (Y + h)) - np.cos(k * (X - a / 2.0))
    return -(G / (2.0 * TWO_PI)) * (np.log(t1) - np.log(t2))


def psi_trunc(X, Y, a=A, b=B, G=GAM, N=400):
    """对称截断的直接点涡求和（对照闭式）"""
    h = b / 2.0
    s = np.zeros_like(np.asarray(X, dtype=float))
    for n in range(-N, N + 1):
        s += 0.5 * np.log((X - n * a) ** 2 + (Y - h) ** 2)
        s -= 0.5 * np.log((X - n * a - a / 2.0) ** 2 + (Y + h) ** 2)
    return -(G / TWO_PI) * s


# ---------- 1) 闭式流函数的结构性质 ----------
print('[1] 闭式流函数 ψ（周期 a / 求和一致 / 调和 / 核对数奇异）')

xg = np.linspace(-3.0, 3.0, 11)
yg = np.linspace(-0.9, 0.9, 7)
XX, YY = np.meshgrid(xg, yg)
dp_a = float(np.abs(psi(XX + A, YY) - psi(XX, YY)).max())
check('x 方向周期为 a（ψ(x+a)=ψ(x)）', dp_a < 1e-12, '实测 %.2e' % dp_a)
dp_h = float(np.abs(psi(XX + A / 2, YY) - psi(XX, YY)).max())
check('a/2 不是周期（交错双排的最小周期确为 a）', dp_h > 1e-3, '实测 %.3f' % dp_h)

rng = np.random.default_rng(11)
pts = []
while len(pts) < 300:                       # 采样点避开涡核
    x, y = rng.uniform(-2.5, 2.5), rng.uniform(-0.8, 0.8)
    if (min((x - n * A) ** 2 + (y - HH) ** 2 for n in range(-3, 4)) < 0.05
            or min((x - n * A - A / 2) ** 2 + (y + HH) ** 2 for n in range(-3, 4)) < 0.05):
        continue
    pts.append((x, y))
PX, PY = np.array(pts)[:, 0], np.array(pts)[:, 1]
dsum = float(np.abs(psi(PX, PY) - psi_trunc(PX, PY, N=400)).max())
check('闭式 = 截断点涡求和 (N=400, 避核采样 300 点)', dsum < 3e-3, '实测 %.2e' % dsum)


def lap_max(n, xr, yr):
    x = np.linspace(*xr, n)
    y = np.linspace(*yr, n)
    dx, dy = x[1] - x[0], y[1] - y[0]
    Xg, Yg = np.meshgrid(x, y, indexing='ij')
    P = psi(Xg, Yg)
    lap = (P[2:, 1:-1] + P[:-2, 1:-1] - 2 * P[1:-1, 1:-1]) / dx ** 2 \
        + (P[1:-1, 2:] + P[1:-1, :-2] - 2 * P[1:-1, 1:-1]) / dy ** 2
    return float(np.abs(lap).max())


SUB = ((-1.5, 1.5), (0.45, 0.85))          # 子域离最近涡核 > 0.3
l1, l2 = lap_max(161, *SUB), lap_max(321, *SUB)
ratio = l1 / l2 if l2 > 0 else float('inf')
check('∇²ψ=0（离核子域，二阶收敛自证: 残差比≈4）',
      l2 < 5e-3 and 2.5 < ratio < 6.0,
      '粗 %.2e / 细 %.2e, 比 %.2f' % (l1, l2, ratio))

d_log = []
for r0 in (0.01, 0.02, 0.04):               # 上排核在 (0, h)；r→0 才能剥掉正则部分
    d_log.append(float(psi(2 * r0, HH) - psi(r0, HH)))
exp = -GAM / TWO_PI * math.log(2)
devs = [abs(v - exp) for v in d_log]
check('涡核对数奇异 ψ(2r)−ψ(r) → −(Γ/2π)ln2（r→0 收敛自证）',
      max(devs) < 1e-3 and devs[0] < devs[1] < devs[2],
      '偏差 %s（r=0.01/0.02/0.04, 期望 %.6f）'
      % (['%.1e' % d for d in devs], exp))

# ---------- 2) 刚性平移与 U=(Γ/2a)tanh(πb/a) ----------
print('[2] 刚性平移（周期条带精确核，Σcot 恒等式）')


def street(ratio, N=12, amp=0.0, mode=1, seed=5, a=A, G=GAM):
    h = ratio * a / 2.0
    X, Y, Gm = [], [], []
    for n in range(N):
        X.append(n * a); Y.append(h); Gm.append(G)
        X.append(n * a + a / 2.0); Y.append(-h); Gm.append(-G)
    X, Y, Gm = np.array(X), np.array(Y), np.array(Gm)
    if amp > 0:
        idx = np.arange(len(X)) // 2
        ph = mode * TWO_PI * idx / N
        r = np.random.default_rng(seed)
        X = X + amp * np.cos(ph) + amp * 0.3 * r.normal(size=len(X))
        Y = Y + amp * np.sin(ph) + amp * 0.3 * r.normal(size=len(Y))
    return X, Y, Gm, N * a


def rhs(X, Y, Gm, L):
    """u − iv = −i Σ_{j≠i} (γ_j/2L)·cot(π(z_i−z_j)/L)：周期条带精确 Green 函数"""
    Z = X + 1j * Y
    dZ = Z[:, None] - Z[None, :]
    np.fill_diagonal(dZ, 1.0)
    w = math.pi * dZ / L
    c = -1j * (Gm[None, :] / (2.0 * L)) * (np.cos(w) / np.sin(w))
    np.fill_diagonal(c, 0.0)
    S = c.sum(axis=1)
    return S.real, -S.imag


for rt in (0.28054, 0.40, 0.60):
    X, Y, Gm, L = street(rt)
    u, v = rhs(X, Y, Gm, L)
    Uf = (GAM / (2 * A)) * math.tanh(math.pi * rt)
    check('b/a=%.5f: 每涡 u=U 公式且 v≡0' % rt,
          float(u.max() - u.min()) < 1e-12 and float(np.abs(v).max()) < 1e-12
          and abs(float(u.mean()) - Uf) < 1e-12,
          'ū=%.9f 公式=%.9f |v|max=%.1e' % (u.mean(), Uf, np.abs(v).max()))


def integrate(ratio, T_conv, N=12, dt=5e-4, amp=0.0, mode=1, seed=5):
    """积分 T_conv 个对流时间（a/U），返回去刚性平移后的 RMS 形变"""
    X, Y, Gm, L = street(ratio, N, amp, mode, seed)
    X0, Y0 = X.copy(), Y.copy()
    U = (GAM / (2 * A)) * math.tanh(math.pi * ratio)
    T = T_conv / U
    nst = int(round(T / dt))
    for _ in range(nst):
        k1x, k1y = rhs(X, Y, Gm, L)
        k2x, k2y = rhs(X + dt / 2 * k1x, Y + dt / 2 * k1y, Gm, L)
        k3x, k3y = rhs(X + dt / 2 * k2x, Y + dt / 2 * k2y, Gm, L)
        k4x, k4y = rhs(X + dt * k3x, Y + dt * k3y, Gm, L)
        X = X + dt / 6 * (k1x + 2 * k2x + 2 * k3x + k4x)
        Y = Y + dt / 6 * (k1y + 2 * k2y + 2 * k3y + k4y)
    if not (np.all(np.isfinite(X)) and np.all(np.isfinite(Y))):
        return float('nan')
    sx = float(np.mean(X - X0)) - U * T
    sy = float(np.mean(Y - Y0))
    return float(np.sqrt(np.mean((X - X0 - U * T - sx) ** 2 + (Y - Y0 - sy) ** 2)))


d_rigid = integrate(0.28054, 2.0, amp=0.0)
check('无扰动涡街刚性平移（2 对流时间形变 < 1e-9）', d_rigid < 1e-9, '实测 %.2e' % d_rigid)

# ---------- 3) von Kármán 中性稳定比 ----------
print('[3] von Kármán 中性稳定比 b/a=0.28054（扰动放大：2→10 对流时间）')
for rt, kind in ((0.28054, 'neutral'), (0.40, 'unstable'), (0.50, 'unstable')):
    d2 = integrate(rt, 2.0, amp=1e-3)
    d10 = integrate(rt, 10.0, amp=1e-3)
    g = d10 / d2 if d2 > 0 else float('inf')
    if not math.isfinite(d10) or not math.isfinite(d2):
        g = float('inf')
    if kind == 'neutral':
        check('b/a=0.28054 中性：形变不增长（<2×）', math.isfinite(g) and g < 2.0,
              '形变 %.5f→%.5f, 放大 %.2f×' % (d2, d10 if math.isfinite(d10) else float('nan'), g))
    else:
        check('b/a=%.2f 失稳：形变指数增长（>50×）' % rt, g > 50.0,
              '形变 %.5f→%.5f, 放大 %.1f×' % (d2, d10 if math.isfinite(d10) else float('nan'), g))

# ---------- 4) 生成器与库登记 ----------
print('[4] 生成器 karman + 库/资料卡登记')
quads = trisurf.karman()
V = np.array([p for qd in quads for p in qd])
zs = V[:, 2]
check('quads 数量充足且 z 有限', len(quads) > 20000 and bool(np.all(np.isfinite(zs))),
      'quads=%d, z∈[%.4f, %.4f]' % (len(quads), zs.min(), zs.max()))
pa = psi(V[:, 0], V[:, 1]) * 2.0            # 生成器 zscale=2.0
check('生成器顶点 z = 解析 ψ（zscale=2）', float(np.abs(zs - pa).max()) < 1e-12,
      '最大差 %.2e' % float(np.abs(zs - pa).max()))
dcore = np.full(len(V), 9e9)
for m in range(-6, 7):
    dcore = np.minimum(dcore, np.sqrt((V[:, 0] - m * A) ** 2 + (V[:, 1] - HH) ** 2))
    dcore = np.minimum(dcore, np.sqrt((V[:, 0] - m * A - A / 2) ** 2 + (V[:, 1] + HH) ** 2))
check('涡核奇异域已剔除（顶点到最近核 ≥ core=0.055）', float(dcore.min()) >= 0.055 - 1e-9,
      '最小距离 %.4f' % float(dcore.min()))
check('bbox 与声明域一致 x∈[−4,4], y∈[−1,1]',
      abs(V[:, 0].min() + 4) < 1e-9 and abs(V[:, 0].max() - 4) < 1e-9
      and abs(V[:, 1].min() + 1) < 1e-9 and abs(V[:, 1].max() - 1) < 1e-9)

e = cl.BUILTIN.get('karman_street')
check('库条目 karman_street 已注册且 faces 非空',
      e is not None and e.get('gen') is True and bool(e.get('faces')),
      'faces=%d' % (len(e['faces']) if e and e.get('faces') else 0))
check('faces_kind=heightfield 且分类正确',
      e is not None and e.get('faces_kind') == 'heightfield'
      and e.get('category') == '偏微分方程解')
cards = getattr(gallery, 'CARDS', {})
check('资料卡已登记（formula/props/trivia）',
      'karman_street' in cards
      and all(k in cards['karman_street'] for k in ('formula', 'props', 'trivia')))

print('门禁结果:', '全绿' if OK else '有 FAIL')
sys.exit(0 if OK else 1)
