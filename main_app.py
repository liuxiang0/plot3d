#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""main_app.py — 3D 数学可视化平台（合并单窗口入口）

双标签:
  函数绘图器 — 表达式→图形（显式/隐式/参数/不等式八形态, LaTeX, 函数库, 曲面分析, 导出）
  样条设计器 — Bézier/NURBS 自动生成 + 控制点实时微调 + 导出
两个标签页引擎与状态相互独立; 各 App 仍可单独运行。
运行: python3 plot3d/main_app.py
"""
import tkinter as tk
from tkinter import ttk

import engine3d
import nurbs
from plotter_app import PlotterApp
from spline_app import SplineApp

BG = engine3d.BG

ABOUT = """3D 数学可视化平台

【函数绘图器】
  y=f(x) · f(x,y)=g(x,y) · z=f(x,y) · F(x,y,z)=0
  不等式(组)/不等式体 · r(t) 曲线 · r(u,v) 参数曲面
  兼容 LaTeX (\\frac \\sqrt \\le …) 与参数 (; r=2)
  函数库 40 条 + user_define.json 自定义
  曲面分析: 法向量场 / 高斯曲率 K / 平均曲率 |H|

【样条设计器】
  Bézier / NURBS 曲线与曲面, 点列全局插值
  控制点实时微调: 拖拽 / Ctrl+拖(视线) / Shift+拖(权重)

【通用】
  无极缩放 · 八叉树自适应 + 交互 LOD
  导出 SVG / EPS 矢量图 + 场景 JSON 存档"""


def build(root):
    """构建主窗口; 返回 (notebook, plotter, spline)"""
    root.title('3D 数学可视化平台 · 函数绘图 / 样条设计')
    engine3d.apply_default_fonts(root)
    # 主窗口尺寸: 原 1060x820 的两倍, 不超过屏幕可视范围
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f'{min(2120, sw)}x{min(1640, sh)}')
    style = ttk.Style(root)
    try:
        style.theme_use('clam')
    except tk.TclError:
        pass
    style.configure('TNotebook', background=BG, borderwidth=0)
    style.configure('TNotebook.Tab', background='#313244',
                    foreground='#cdd6f4', padding=[16, 5],
                    font=('DejaVu Sans', engine3d.font_size(10), 'bold'))
    style.map('TNotebook.Tab',
              background=[('selected', '#89b4fa')],
              foreground=[('selected', '#1e1e2e')])
    nb = ttk.Notebook(root)
    plotter = PlotterApp(nb)
    spline = SplineApp(nb)
    nb.add(plotter, text='  函数绘图器  ')
    nb.add(spline, text='  样条设计器  ')
    nb.pack(fill='both', expand=True)
    # 根菜单
    menu = tk.Menu(root)
    fm = tk.Menu(menu, tearoff=0)
    fm.add_command(label='退出', command=root.destroy, accelerator='Ctrl+Q')
    menu.add_cascade(label='文件', menu=fm)
    hm = tk.Menu(menu, tearoff=0)
    hm.add_command(label='关于',
                   command=lambda: _about(root))
    menu.add_cascade(label='帮助', menu=hm)
    root.config(menu=menu)
    root.bind_all('<Control-q>', lambda e: root.destroy())
    # 样条页预载演示（与独立运行一致）
    root.update_idletasks()
    spline.load_curve('插值演示', nurbs.interpolate_curve(
        [(-2.5, 0, 0), (-1.5, 1.2, 0.8), (-0.5, -0.8, 1.2),
         (0.5, 1.0, -0.6), (1.5, -0.5, 0.4), (2.5, 0.6, 0)]))
    return nb, plotter, spline


def _about(root):
    from tkinter import messagebox
    messagebox.showinfo('关于', ABOUT, parent=root)


def main():
    root = tk.Tk()
    build(root)
    root.mainloop()


if __name__ == '__main__':
    main()
