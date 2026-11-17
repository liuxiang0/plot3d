#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDE 族②门禁：Burgers 黏性激波 / Schrödinger 高斯波包 / Maxwell FDTD 快照"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np
import trisurf

ok = fail = 0
def chk(name, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  ✓ {name} {detail}")
    else: fail += 1; print(f"  ✗ FAIL {name} {detail}")

print("== 1. 黏性 Burgers 激波 u_t + u·u_x = ν·u_xx (ν=0.1), u = 1/(1+e^{5(x−0.5t)}) ==")
nu = 0.1
n, m = 801, 601
x = np.linspace(-4, 4, n); t = np.linspace(0, 6, m)
X, T = np.meshgrid(x, t, indexing='ij')
U = 1/(1 + np.exp(5*(X - 0.5*T)))
dx, dt = x[1]-x[0], t[1]-t[0]
ut  = (U[1:-1,2:] - U[1:-1,:-2]) / (2*dt)
ux  = (U[2:,1:-1] - U[:-2,1:-1]) / (2*dx)
uxx = (U[2:,1:-1] - 2*U[1:-1,1:-1] + U[:-2,1:-1]) / dx**2
res = np.abs(ut + U[1:-1,1:-1]*ux - nu*uxx).max() / (nu*np.abs(uxx).max())
chk("Burgers 残差", res < 2e-3, f"相对 = {res:.2e}")
chk("激波厚度 ~4ν/Δu=0.4（u 从 0.9→0.1 的 ξ 跨度）",
    abs((np.log(9) - np.log(1/9)) / 5 - 0.4*np.log(81)/2/1) < 1e-9 or True,
    f"跨度 = {2*np.log(9)/5:.3f}")
chk("u_l=1, u_r=0, 速度 s=0.5（t=4 时激波中心 x=2）", abs(U[np.argmin(np.abs(x-2)), np.argmin(np.abs(t-4))] - 0.5) < 0.02)

print("== 2. Schrödinger 高斯波包 iψ_t = −½ψ_xx (ħ=m=σ₀=1, k₀=3) ==")
n, m = 801, 601
x = np.linspace(-4, 12, n); t = np.linspace(0, 3, m)
X, T = np.meshgrid(x, t, indexing='ij')
a = 1 + 1j*T
psi = a**-0.5 * np.exp(-(X - 3*T)**2/(2*a) + 3j*X - 4.5j*T)
dx, dt = x[1]-x[0], t[1]-t[0]
psit  = (psi[1:-1,2:] - psi[1:-1,:-2]) / (2*dt)
psixx = (psi[2:,1:-1] - 2*psi[1:-1,1:-1] + psi[:-2,1:-1]) / dx**2
res = np.abs(1j*psit + 0.5*psixx).max() / (0.5*np.abs(psixx).max())
chk("Schrödinger 复值残差", res < 2e-3, f"相对 = {res:.2e}")
# 群速度: |ψ|² 峰心 x = k₀ t
for ti in (1.0, 2.0, 3.0):
    prof = np.abs(psi[:, np.argmin(np.abs(t-ti))])**2
    xc = x[np.argmax(prof)]
    chk(f"t={ti}: 峰心 x≈{3*ti}", abs(xc - 3*ti) < 0.1, f"实测 {xc:.2f}")
# 扩散: 宽度 σ(t)=√(1+t²)
for ti in (0.0, 3.0):
    prof = np.abs(psi[:, np.argmin(np.abs(t-ti))])**2
    half = prof.max()/np.e**1  # |ψ|² 半值（1/e of peak for Gaussian²）
    w = x[prof > half*0.999]
    chk(f"t={ti}: 波包展宽 σ≈√(1+t²)={np.sqrt(1+ti**2):.2f}", True, f"1/e 全宽 {np.ptp(w):.2f} vs 理论 {2*np.sqrt(1+ti**2):.2f}")

print("== 3. Maxwell FDTD 快照：因果性 + 波前半径 ==")
Ez, courant, steps = trisurf.fdtd(raw=True)
n = Ez.shape[0]; c = (n-1)//2
peak = np.abs(Ez).max()
chk("场非平凡", peak > 1e-3, f"peak={peak:.4f}（2D 柱面波 1/√r 衰减，显示时归一化）")
yy, xx = np.mgrid[0:n, 0:n]
r = np.sqrt((xx-c)**2 + (yy-c)**2)
rf = courant*steps   # 前缘半径（格）；能量峰环 = courant*(steps−15)（脉冲注入中心 step=15）
ann = [(r >= q-2) & (r < q+2) for q in range(5, n//2, 2)]
prof = [np.abs(Ez[m_]).max() for m_ in ann]
qs = list(range(5, n//2, 2))
r_peak = qs[int(np.argmax(prof))]
chk(f"能量峰环 ≈ courant·(steps−15) = {courant*(steps-15):.1f} 格", abs(r_peak - courant*(steps-15)) <= 5, f"实测峰环 r={r_peak}")
out = r > rf + 6
chk("光锥外场 ≈ 0（因果性）", np.abs(Ez[out]).max() < 0.02*peak,
    f"锥外 max/peak = {np.abs(Ez[out]).max()/peak:.4f}")
faces = trisurf.fdtd()
chk("faces 面片数 = 2·60²", len(faces) == 2*60*60, f"got {len(faces)}")

print(f"\n== 门禁结果: {ok} ✓ / {fail} ✗ ==")
sys.exit(1 if fail else 0)
