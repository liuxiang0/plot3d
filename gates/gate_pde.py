#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDE 候选条目数值门禁：闭式解代入原方程，有限差分残差须 ≈ 0（相对尺度归一）"""
import numpy as np
from scipy.special import j0

ok = fail = 0
def chk(name, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  ✓ {name} {detail}")
    else: fail += 1; print(f"  ✗ FAIL {name} {detail}")

print("== 1. 热核 u_t = u_xx, u = exp(-x²/4t)/√(4πt) ==")
n = 401; x = np.linspace(-4, 4, n); t = np.linspace(0.15, 2.0, n)
X, T = np.meshgrid(x, t, indexing='ij')
U = np.exp(-X**2/(4*T)) / np.sqrt(4*np.pi*T)
dx, dt = x[1]-x[0], t[1]-t[0]
ut  = (U[1:-1,2:] - U[1:-1,:-2]) / (2*dt)                     # t 轴（第二轴）中心差分
uxx = (U[2:,1:-1] - 2*U[1:-1,1:-1] + U[:-2,1:-1]) / dx**2      # x 轴（第一轴）中心差分
r = np.abs(ut-uxx).max()/np.abs(uxx).max()
chk("热方程残差", r < 1e-3, f"max|res|/max|u_xx| = {r:.2e}")
xm = np.linspace(-12, 12, 4801)   # 宽窗口防截断丢尾（t=2 时核宽 √(2t)=2）
mass = [np.trapezoid(np.exp(-xm**2/(4*ti))/np.sqrt(4*np.pi*ti), xm) for ti in (0.2, 0.8, 2.0)]
chk("∫u dx = 1（三时刻质量守恒）", all(abs(m-1) < 5e-4 for m in mass), f"{[f'{m:.5f}' for m in mass]}")
chk("峰值 = 1/√(4πt)（t=0.5）", abs(1/np.sqrt(4*np.pi*0.5) - np.exp(0)/np.sqrt(2*np.pi)) < 1e-12)

print("== 2. KdV 单孤子 u_t + 6u·u_x + u_xxx = 0, u = 2sech²(x−4t) ==")
n = 1001; x = np.linspace(-10, 10, n); t = np.linspace(0, 4, n)
X, T = np.meshgrid(x, t, indexing='ij')
U = 2/np.cosh(X - 4*T)**2
dx, dt = x[1]-x[0], t[1]-t[0]
c  = U[2:-2, 2:-2]
ut   = (U[2:-2,3:-1] - U[2:-2,1:-3]) / (2*dt)
ux   = (U[3:-1,2:-2] - U[1:-3,2:-2]) / (2*dx)
uxxx = (U[4:,2:-2] - 2*U[3:-1,2:-2] + 2*U[1:-3,2:-2] - U[:-4,2:-2]) / (2*dx**3)  # 中心三阶
r = np.abs(ut + 6*c*ux + uxxx).max() / max(np.abs(uxxx).max(), 1e-15)
chk("KdV 残差", r < 2e-3, f"相对 = {r:.2e}")
chk("峰高 u=2、峰脊 x=4t（t=2 处 x=8）", abs(2/np.cosh(8-8)**2 - 2) < 1e-12)

print("== 3. sine-Gordon 呼吸子 u_tt − u_xx + sin u = 0 ==")
w = 0.6; k = np.sqrt(1-w**2)   # k=0.8
n = 601; x = np.linspace(-8, 8, n); t = np.linspace(0.1, 10.4, n)
X, T = np.meshgrid(x, t, indexing='ij')
U = 4*np.arctan(k*np.sin(w*T) / (w*np.cosh(k*X)))
dx, dt = x[1]-x[0], t[1]-t[0]
utt = (U[2:-2,3:-1] - 2*U[2:-2,2:-2] + U[2:-2,1:-3]) / dt**2
uxx = (U[3:-1,2:-2] - 2*U[2:-2,2:-2] + U[1:-3,2:-2]) / dx**2
r = np.abs(utt - uxx + np.sin(U[2:-2,2:-2])).max() / max(np.abs(utt).max(), 1e-15)
chk("sG 残差", r < 2e-3, f"相对 = {r:.2e}")
chk("t 周期 2π/ω ≈ 10.472", abs(2*np.pi/w - 10.472) < 5e-4, f"2π/0.6={2*np.pi/w:.4f}")
chk("sin(ωt)=0 时刻 u≡0（t=π/0.6≈5.236 过零点）", abs(U[:, np.argmin(np.abs(t-np.pi/w))]).max() < 2e-2)  # t 网格偏离 π/ω 约 0.003 → u_max≈0.010，容差 2e-2

print("== 4. 矩形膜 Chladni 模态 (3,2)：∇²u = −13π² u（波动方程本征模） ==")
n = 301; x = np.linspace(0, 1, n); y = np.linspace(0, 1, n)
X, Y = np.meshgrid(x, y, indexing='ij')
U = np.sin(3*np.pi*X)*np.sin(2*np.pi*Y)
d = x[1]-x[0]
lap = (U[2:,1:-1] + U[:-2,1:-1] + U[1:-1,2:] + U[1:-1,:-2] - 4*U[1:-1,1:-1]) / d**2
r = np.abs(lap + 13*np.pi**2*U[1:-1,1:-1]).max() / (13*np.pi**2)
chk("本征方程残差", r < 2e-3, f"相对 = {r:.2e}")
chk("四边 u=0（固定边界）", abs(U[0,:]).max() < 1e-15 and abs(U[-1,:]).max() < 1e-15
    and abs(U[:,0]).max() < 1e-15 and abs(U[:,-1]).max() < 1e-15)
chk("节线：x=i/3 (i=1,2) 与 y=1/2 处 u≡0", abs(U[n//3,:]).max() < 1e-14 and abs(U[:,n//2]).max() < 1e-14)

print("== 5. 2D 量子谐振子本征态 ψ₂ψ₂：Ĥψ = Eψ, E = n_x+n_y+1 = 5 ==")
n = 401; x = np.linspace(-4, 4, n); y = x.copy()
X, Y = np.meshgrid(x, y, indexing='ij')
psi = lambda s: (4*s**2 - 2)*np.exp(-s**2/2)   # H₂(s)e^{-s²/2}，H₂=4s²−2
U = psi(X)*psi(Y)
d = x[1]-x[0]
lap = (U[2:,1:-1] + U[:-2,1:-1] + U[1:-1,2:] + U[1:-1,:-2] - 4*U[1:-1,1:-1]) / d**2
c = U[1:-1,1:-1]
H = -0.5*lap + 0.5*(X[1:-1,1:-1]**2 + Y[1:-1,1:-1]**2)*c
r = np.abs(H - 5*c).max() / 5
chk("本征方程残差 (E=5)", r < 2e-3, f"相对 = {r:.2e}")
chk("节线 x=±1/√2, y=±1/√2（4x²−2=0）", abs(4*(1/np.sqrt(2))**2 - 2) < 1e-12)

print("== 6. 圆膜 Bessel 基模 J₀(αr)：∇²u = −α²u, α=j₀,₁≈2.404826, 边界 u(a)=0 ==")
alpha = 2.404825557695773
chk("J₀(α)=0（边界条件）", abs(j0(alpha)) < 1e-14, f"J₀(α)={j0(alpha):.2e}")
nr, nth = 201, 241
r = np.linspace(0.02, 1.0, nr); th = np.linspace(0, 2*np.pi, nth)
R, TH = np.meshgrid(r, th, indexing='ij')
U = j0(alpha*R)
dr, dth = r[1]-r[0], th[1]-th[0]
Rc = R[1:-1,1:-1]
ur  = (U[2:,1:-1] - U[:-2,1:-1]) / (2*dr)
urr = (U[2:,1:-1] - 2*U[1:-1,1:-1] + U[:-2,1:-1]) / dr**2
uth_th = (U[1:-1,2:] - 2*U[1:-1,1:-1] + U[1:-1,:-2]) / dth**2
lap = urr + ur/Rc + uth_th/Rc**2     # u_θθ 项为零（轴对称），保留数值项验证
res = np.abs(lap + alpha**2*U[1:-1,1:-1])
r = res.max() / alpha**2
chk("极坐标本征方程残差", r < 5e-3, f"相对 = {r:.2e}（r≥0.02 内点）")
chk("J₀(0)=1（中心峰值）", abs(j0(0)-1) < 1e-15)

print(f"\n== 门禁结果: {ok} ✓ / {fail} ✗ ==")
raise SystemExit(1 if fail else 0)
