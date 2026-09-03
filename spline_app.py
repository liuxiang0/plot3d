#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""spline_app.py — Bézier / NURBS 曲线与曲面设计器（第四阶段）

自动生成: 预设形状一键调用 · 精确有理圆/圆柱 · 点列全局插值（曲线精确过点）
控制点微调:
  拖拽 = 屏幕平面移动 · Ctrl+拖拽 = 沿视线移动 · Shift+拖拽 = 调节权重
  方向键 = 微移 · +/− = 权重 · 点击选中 · 面板精确输入 x/y/z/w · 插入/删除点
运行: python3 plot3d/spline_app.py
"""
import json
import math
import tkinter as tk
from tkinter import filedialog

import engine3d
import mathparse
import nurbs
from dockpane import DockPane

BG = engine3d.BG
CP_COLOR, SEL_COLOR, NET_COLOR = '#cdd6f4', '#f9e2af', '#6c7294'
CURVE_COLOR = '#f9e2af'
DEC_LEVEL_COLORS = ('#89b4fa', '#a6e3a1', '#cba6f7', '#fab387',
                    '#94e2d5', '#f2cdcd')


class SplineApp(tk.Frame):
    HELP = ('样条菜单▾ 一键生成 · 或输入点列 (0,0,0);(2,1.5,1);(4,-1,0);(5,1.5,0) 自动拟合 NURBS 插值曲线\n'
            '微调: 拖控制点=屏幕面移动 · Ctrl+拖=沿视线 · Shift+拖=调权重 · 方向键微移 · +/−权重 · 面板精确编辑')

    def __init__(self, master):
        super().__init__(master, bg=BG)
        self.spline = None          # ('curve', Curve) | ('surface', Surface)
        self.name = ''
        self.original = None
        self.sel = None             # int（曲线）或 (i,j)（曲面）
        self._markers = []
        self._dragging = False
        self.snap = True
        self._smode = 'solid'     # 当前曲面渲染模式(面板重建时恢复高亮)
        self._obj_color = None
        self._refine_pending = False
        self._build_ui()
        self._build_menu()
        self._bind_edit()
        self.eng.on_view_change = self._schedule_refine

    # ---------- 界面 ----------
    def _build_ui(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill='x', padx=8, pady=(8, 2))
        tk.Label(top, text='点列', bg=BG, fg='#89b4fa',
                 font=('DejaVu Sans', engine3d.font_size(11), 'bold')).pack(side='left', padx=(0, 6))
        self.entry = tk.Entry(top, font=('Consolas', engine3d.font_size(12)), bg='#181825',
                              fg='#cdd6f4', insertbackground='#cdd6f4',
                              relief='flat')
        self.entry.pack(side='left', fill='x', expand=True, ipady=5)
        self.entry.bind('<Return>', lambda e: self._generate())
        tk.Button(top, text='自动拟合', command=self._generate, bg='#a6e3a1',
                  fg='#1e1e2e', relief='flat',
                  font=('DejaVu Sans', engine3d.font_size(11), 'bold'),
                  padx=12).pack(side='left', padx=(6, 3))
        self.menu_btn = tk.Menubutton(top, text='样条库 ▾', bg='#45475a',
                                      fg='#cdd6f4', relief='flat')
        self.menu_btn.pack(side='left', padx=3)
        ex = tk.Menubutton(top, text='导出 ▾', bg='#45475a', fg='#cdd6f4',
                           relief='flat')
        exm = tk.Menu(ex, tearoff=0)
        exm.add_command(label='SVG 矢量图', command=lambda: self._export('svg'))
        exm.add_command(label='EPS 矢量图', command=lambda: self._export('eps'))
        exm.add_separator()
        exm.add_command(label='保存场景 JSON', command=self._save_scene_dialog)
        exm.add_command(label='打开场景 JSON', command=self._load_scene_dialog)
        exm.add_separator()
        exm.add_command(label='动画 GIF（参数扫描）', command=self._export_gif)
        exm.add_command(label='动画 SVG 序列（参数扫描）',
                        command=self._export_svg_seq)
        exm.add_command(label='de Casteljau 构造 GIF（Bézier）',
                        command=self._export_decasteljau_gif)
        exm.add_command(label='de Casteljau 构造 SVG 序列（Bézier）',
                        command=self._export_decasteljau_svg)
        ex['menu'] = exm
        ex.pack(side='left', padx=3)
        tk.Button(top, text='颜色', command=self._change_color, bg='#45475a',
                  fg='#cdd6f4', relief='flat').pack(side='left', padx=3)
        self.status = tk.Label(self, anchor='w', justify='left', bg=BG,
                               fg='#9aa0b4', font=('DejaVu Sans', engine3d.font_size(10)),
                               wraplength=960)
        self.status.pack(fill='x', padx=10, pady=(0, 2))
        self.status.config(text=self.HELP)
        self.eng = engine3d.Engine3D(self)
        self.eng.pack(fill='both', expand=True)
        # 底部控制点编辑面板（可停靠/可脱离为独立窗口）
        self.edit_pane = DockPane(self, '控制点编辑', self._build_edit_panel,
                                  side='bottom', width=0,
                                  float_size=(900, 150))
        self.edit_pane.dock(self)

    def _build_edit_panel(self, parent):
        """构建控制点编辑面板内容; parent 为主窗口底栏或脱离窗口"""
        panel = parent
        self.pt_label = tk.Label(panel, text='控制点 —', bg=BG, fg='#89b4fa',
                                 width=16, anchor='w', font=('DejaVu Sans', engine3d.font_size(10)))
        self.pt_label.pack(side='left')
        self.entries = {}
        for name in ('x', 'y', 'z', 'w'):
            tk.Label(panel, text=name + ':', bg=BG,
                     fg='#9aa0b4').pack(side='left')
            en = tk.Entry(panel, width=8, font=('Consolas', engine3d.font_size(10)), bg='#181825',
                          fg='#cdd6f4', insertbackground='#cdd6f4',
                          relief='flat')
            en.pack(side='left', padx=(1, 6), ipady=2)
            self.entries[name] = en
        tk.Button(panel, text='应用', command=self._apply_panel, bg='#89b4fa',
                  fg='#1e1e2e', relief='flat').pack(side='left', padx=2)
        for text, cmd in (('插入点', self._insert_point),
                          ('删除点', self._delete_point),
                          ('重置', self._reset_shape)):
            tk.Button(panel, text=text, command=cmd, bg='#45475a',
                      fg='#cdd6f4', relief='flat').pack(side='left', padx=2)
        self.snap_btn = tk.Button(panel, text='⊞ 吸附', command=self._toggle_snap,
                                  bg='#89b4fa', fg='#1e1e2e', relief='flat',
                                  font=('DejaVu Sans', engine3d.font_size(9)))
        self.snap_btn.pack(side='left', padx=2)
        tk.Label(panel, text='渲染:', bg=BG, fg='#5b6178',
                 font=('DejaVu Sans', engine3d.font_size(9))).pack(side='left', padx=(8, 0))
        self.mode_btns = {}
        for key, label in (('solid', '实体'), ('wire', '线框'),
                           ('both', '实体+线')):
            b = tk.Button(panel, text=label, relief='flat', bg='#313244',
                          fg='#9aa0b4', font=('DejaVu Sans', engine3d.font_size(9)), padx=6,
                          command=lambda k=key: self._set_surface_mode(k))
            b.pack(side='left', padx=2)
            self.mode_btns[key] = b
        for k, b in self.mode_btns.items():
            on = k == self._smode
            b.config(bg='#89b4fa' if on else '#313244',
                     fg='#1e1e2e' if on else '#cdd6f4')
        self.axes_btn = tk.Button(panel, text='坐标轴', command=self._toggle_axes,
                                  relief='flat', font=('DejaVu Sans', engine3d.font_size(9)),
                                  padx=6)
        self.axes_btn.pack(side='left', padx=2)
        on = self.eng.show_axes
        self.axes_btn.config(bg='#89b4fa' if on else '#313244',
                             fg='#1e1e2e' if on else '#cdd6f4')
        self.info_label = tk.Label(panel, text='', bg=BG, fg='#5b6178')
        self.info_label.pack(side='right')
        if self.snap:
            self.snap_btn.config(bg='#89b4fa', fg='#1e1e2e')
        else:
            self.snap_btn.config(bg='#45475a', fg='#cdd6f4')
        self._update_panel()

    def _build_menu(self):
        menu = tk.Menu(self.menu_btn, tearoff=0)
        curves = [
            ('三次 Bézier · S 形', lambda: self.load_curve(
                '三次 Bézier', nurbs.bezier_curve(
                    [(-2, -1, 0), (-0.6, 1.6, 1.2), (0.6, -1.6, 1.2), (2, 1, 0)]))),
            ('五次 Bézier · 波浪', lambda: self.load_curve(
                '五次 Bézier', nurbs.bezier_curve(
                    [(-2.5, 0, 0), (-1.2, 1.5, 1), (0, 0, -1),
                     (1.2, 1.5, 1), (2.5, 0, 0)]))),
            ('NURBS · 精确圆（有理二次）', lambda: self.load_curve(
                'NURBS 精确圆', nurbs.circle(1.6))),
            ('NURBS · 自动插值演示', lambda: self.load_curve(
                '插值曲线', nurbs.interpolate_curve(
                    [(-2.5, 0, 0), (-1.5, 1.2, 0.8), (-0.5, -0.8, 1.2),
                     (0.5, 1.0, -0.6), (1.5, -0.5, 0.4), (2.5, 0.6, 0)]))),
            ('❤ 心形线（经典插值）', lambda: self.load_curve(
                '心形线', nurbs.heart_curve())),
            ('♣ 三叶结（拓扑纽结）', lambda: self.load_curve(
                '三叶结', nurbs.trefoil_curve())),
            ('✈ NACA 0012 翼型', lambda: self.load_curve(
                'NACA 翼型', nurbs.airfoil_curve())),
            ('S 字体字母（Bézier 成名作）', lambda: self.load_curve(
                '字体 S', nurbs.s_glyph_curve())),
        ]
        surfaces = [
            ('Bézier 曲面 · 波浪片 4×4', lambda: self.load_surface(
                'Bézier 曲面', nurbs.bezier_surface(self._wave_grid()))),
            ('NURBS · 圆柱拱壳（精确）', lambda: self.load_surface(
                '圆柱拱壳', nurbs.cylinder_arch(1.4, 2.0))),
            ('● 精确球面（有理旋转）', lambda: self.load_surface(
                '精确球面', nurbs.sphere_surface())),
            ('◎ 精确环面（有理旋转）', lambda: self.load_surface(
                '精确环面', nurbs.torus_surface())),
            ('🍷 高脚杯（轮廓插值旋转）', lambda: self.load_surface(
                '高脚杯', nurbs.goblet_surface())),
            ('🏺 梅瓶（轮廓插值旋转）', lambda: self.load_surface(
                '梅瓶', nurbs.vase_surface())),
        ]
        cm = tk.Menu(menu, tearoff=0)
        for label, fn in curves:
            cm.add_command(label=label, command=fn)
        sm = tk.Menu(menu, tearoff=0)
        for label, fn in surfaces:
            sm.add_command(label=label, command=fn)
        menu.add_cascade(label=f'曲线 ({len(curves)})', menu=cm)
        menu.add_cascade(label=f'曲面 ({len(surfaces)})', menu=sm)
        self.menu_btn['menu'] = menu

    @staticmethod
    def _wave_grid():
        g = []
        for i in range(4):
            row = []
            for j in range(4):
                z = 0.9 * math.sin(i * 1.1) * math.cos(j * 1.1)
                z += 0.5 if (i + j) % 2 else -0.5
                row.append((-1.5 + i, -1.5 + j, z))
            g.append(row)
        return g

    # ---------- 载入 ----------
    def load_curve(self, name, curve):
        self.spline = ('curve', curve)
        self.name = name
        self.original = curve.copy()
        self.sel = 0
        self._refresh()
        extra = ' · 有理（Shift+拖拽调权重）' if curve.rational else ''
        self._status(f'✓ {name} · 次数 p={curve.p} · {len(curve.P)} 个控制点'
                     f'{extra} · 拖拽控制点可微调', '#a6e3a1')

    def load_surface(self, name, srf):
        self.spline = ('surface', srf)
        self.name = name
        self.original = srf.copy()
        self.sel = (0, 0)
        self._refresh()
        extra = ' · 有理' if srf.rational else ''
        self._status(f'✓ {name} · p={srf.p}, q={srf.q} · '
                     f'{len(srf.P)}×{len(srf.P[0])} 控制网格{extra} · 拖拽控制点可微调',
                     '#a6e3a1')

    def _generate(self):
        raw = self.entry.get().strip()
        if not raw:
            return
        try:
            pts = nurbs.parse_points(raw)
            curve = nurbs.interpolate_curve(pts)
        except (ValueError, mathparse.ParseError) as e:
            self._status(f'❌ {e}', '#f38ba8')
            return
        self.load_curve(f'插值曲线（{len(pts)} 点精确穿过）', curve)

    # ---------- 渲染 ----------
    def _refresh(self):
        eng = self.eng
        eng.clear_all()
        if not self.spline:
            eng.post_draw = None
            self._update_panel()
            return
        kind, obj = self.spline
        if kind == 'curve':
            pts = eng.adaptive_polyline(lambda s: obj.point(s))
            eng.add_curve(pts, self._obj_color or CURVE_COLOR, 2)
        else:
            base = (engine3d.hex_to_rgb(self._obj_color) if self._obj_color
                    else (148, 210, 200))
            eng.add_mesh(obj.mesh(26, 18, base=base))
        eng.post_draw = self._overlay
        self._update_panel()
        eng._redraw_soon()

    def _resample(self, fast=False):
        """控制点变化后原位重算曲线/曲面采样数据 → 实时跟随（拖动中用低分辨率, 松手恢复）"""
        if not self.spline:
            return
        eng = self.eng
        kind, obj = self.spline
        if kind == 'curve':
            if eng.curves:
                eng.curves[0] = (obj.sample(200 if fast else 400),
                                 CURVE_COLOR, 2)
        else:
            if eng.meshes:
                nu, nv = (18, 12) if fast else (26, 18)
                eng.meshes[0] = obj.mesh(nu, nv)
        eng._redraw_soon()

    def _overlay(self, w, h, emit):
        """覆盖层: 控制多边形/控制网 + 控制点标记 + 选中高亮"""
        if not self.spline:
            return
        cam = self.eng.cam
        self._markers = []
        kind, obj = self.spline
        if kind == 'curve':
            proj = [cam.project(*p, w, h) for p in obj.P]
            for a, b in zip(proj, proj[1:]):
                emit(('line', a[0], a[1], b[0], b[1], NET_COLOR, 1, (3, 3)))
            for i, pr in enumerate(proj):
                self._dot(emit, pr[0], pr[1], i == self.sel,
                          f'P{i}' if i == self.sel else '')
                self._markers.append((pr[0], pr[1], i))
        else:
            P = obj.P
            ni, nj = len(P), len(P[0])
            proj = [[cam.project(*P[i][j], w, h) for j in range(nj)]
                    for i in range(ni)]
            for i in range(ni):
                for j in range(nj):
                    if i + 1 < ni:
                        emit(('line', proj[i][j][0], proj[i][j][1],
                              proj[i + 1][j][0], proj[i + 1][j][1],
                              NET_COLOR, 1, None))
                    if j + 1 < nj:
                        emit(('line', proj[i][j][0], proj[i][j][1],
                              proj[i][j + 1][0], proj[i][j + 1][1],
                              NET_COLOR, 1, None))
            for i in range(ni):
                for j in range(nj):
                    sx, sy = proj[i][j][0], proj[i][j][1]
                    sel = self.sel == (i, j)
                    self._dot(emit, sx, sy, sel,
                              f'P({i},{j})' if sel else '')
                    self._markers.append((sx, sy, (i, j)))
        if self._dragging and self.snap:            # 吸附十字准星 + 坐标读数
            P = self._sel_point_ref()
            sx, sy, _ = cam.project(*P, w, h)
            emit(('line', sx - 9, sy, sx + 9, sy, SEL_COLOR, 1.5, None))
            emit(('line', sx, sy - 9, sx, sy + 9, SEL_COLOR, 1.5, None))
            emit(('text', sx + 12, sy + 14,
                  f'({P[0]:g}, {P[1]:g}, {P[2]:g})', SEL_COLOR, 9, 'w', ''))

    @staticmethod
    def _dot(emit, sx, sy, selected, label):
        r = 6 if selected else 4
        emit(('oval', sx - r, sy - r, sx + r, sy + r,
              SEL_COLOR if selected else CP_COLOR, BG))
        if label:
            emit(('text', sx + 10, sy - 10, label, SEL_COLOR, 9, 'w', 'bold'))

    # ---------- 控制点交互 ----------
    def _bind_edit(self):
        cv = self.eng.cv
        cv.bind('<ButtonPress-1>', self._press, add='+')
        cv.bind('<B1-Motion>', self._drag, add='+')
        cv.bind('<ButtonRelease-1>', self._release, add='+')
        cv.bind('<Key>', self._key, add='+')

    def _press(self, e):
        self._dragging = False
        if not self.spline:
            return
        best, bd = None, 12.0
        for sx, sy, key in self._markers:
            d = math.hypot(e.x - sx, e.y - sy)
            if d < bd:
                bd, best = d, key
        if best is not None:
            self.sel = best
            self._dragging = True
            self._last = (e.x, e.y)
            self.eng.interact_lock = True     # 抢占: 禁用旋转
            self._update_panel()
            self.eng._redraw_soon()

    def _drag(self, e):
        if not self._dragging:
            return
        lx, ly = self._last
        dx, dy = e.x - lx, e.y - ly
        self._last = (e.x, e.y)
        if e.state & 0x1:                     # Shift → 调权重（不吸附）
            self._nudge_weight(dx * 0.01)
        else:
            if e.state & 0x4:                 # Ctrl → 沿视线
                self._move_depth(dy)
            else:
                self._move_screen(dx, dy)
            if self.snap:                     # 吸附主网格交点（随缩放自适应）
                self._snap_point(self._sel_point_ref())
        self._resample(fast=True)
        self._update_panel()

    def _release(self, e):
        was = self._dragging
        self._dragging = False
        self.eng.interact_lock = False
        if was and self.spline:
            if self.spline[0] == 'curve':
                self._do_refine()          # 松手 → 自适应全精度重建
            else:
                self._resample()

    def _schedule_refine(self):
        """视图变化 → 曲线自适应重建（曲面网格不受影响）"""
        if not self.spline or self.spline[0] != 'curve':
            return
        if not self._refine_pending:
            self._refine_pending = True
            self.after_idle(self._do_refine)

    def _do_refine(self):
        self._refine_pending = False
        if not self.spline or self.spline[0] != 'curve':
            return
        obj = self.spline[1]
        pts = self.eng.adaptive_polyline(lambda s: obj.point(s))
        self.eng.curves = [(pts, self._obj_color or CURVE_COLOR, 2)]
        self.eng._redraw_soon()

    def _change_color(self):
        from tkinter import colorchooser
        rgb, hexcol = colorchooser.askcolor(parent=self.winfo_toplevel(),
                                           title='选择对象颜色')
        if not hexcol:
            return
        self._obj_color = hexcol
        if self.spline:
            self._refresh()
            self._status(f'✓ 对象颜色已改为 {hexcol}', '#a6e3a1')

    def _snap_point(self, P):
        """吸附到主网格交点: 格点步长 = nice_step(80/zoom), 随缩放自动切换"""
        step = engine3d.nice_step(80.0 / self.eng.cam.zoom)
        for i in range(3):
            P[i] = round(P[i] / step) * step
        return step

    def _toggle_axes(self):
        """坐标轴开关（与引擎快捷键 a 同步）"""
        on = not self.eng.show_axes
        self.eng.show_axes = on
        self.axes_btn.config(bg='#89b4fa' if on else '#313244',
                             fg='#1e1e2e' if on else '#cdd6f4')
        self.eng._redraw_soon()

    def _toggle_snap(self):
        self.snap = not self.snap
        self.snap_btn.config(bg='#89b4fa' if self.snap else '#45475a',
                             fg='#1e1e2e' if self.snap else '#cdd6f4')
        if self.snap:
            step = engine3d.nice_step(80.0 / self.eng.cam.zoom)
            self._status(f'✓ 吸附开 · 捕捉主网格交点 · 当前格点步长 {step:g}'
                         f'（随缩放自适应）· 快捷键 S', '#a6e3a1')
        else:
            self._status('吸附关 · 自由移动 · 快捷键 S', '#9aa0b4')
        self.eng._redraw_soon()

    def _set_surface_mode(self, key):
        self._smode = key
        self.eng.set_surface_mode(key)
        for k, b in self.mode_btns.items():
            on = k == key
            b.config(bg='#89b4fa' if on else '#313244',
                     fg='#1e1e2e' if on else '#cdd6f4')
        names = {'solid': '实体着色', 'wire': '线框（线划图, 更快）',
                 'both': '实体 + 线框'}
        self._status(f'✓ 曲面渲染: {names[key]}', '#a6e3a1')

    def _cam_basis(self):
        c = self.eng.cam
        ca, sa = math.cos(c.az), math.sin(c.az)
        ce, se = math.cos(c.el), math.sin(c.el)
        R = (ca, sa, 0.0)                     # 屏幕右 → 世界
        U = (-sa * se, ca * se, ce)           # 屏幕上 → 世界
        D = (-sa * ce, ca * ce, -se)          # 远离观察者方向
        return R, U, D

    def _move_screen(self, dx, dy):
        R, U, _ = self._cam_basis()
        k = self.eng.cam.zoom or 1.0
        self._move_sel(tuple((dx / k) * R[i] - (dy / k) * U[i]
                             for i in range(3)))

    def _move_depth(self, dy):
        _, _, D = self._cam_basis()
        k = self.eng.cam.zoom or 1.0
        self._move_sel(tuple((dy / k) * D[i] for i in range(3)))

    def _move_sel(self, delta):
        P = self._sel_point_ref()
        for i in range(3):
            P[i] += delta[i]

    def _nudge_weight(self, dw):
        kind, obj = self.spline
        if kind == 'curve':
            obj.W[self.sel] = max(0.05, obj.W[self.sel] + dw)
        else:
            i, j = self.sel
            obj.W[i][j] = max(0.05, obj.W[i][j] + dw)

    def _key(self, e):
        if not self.spline or self.sel is None:
            return
        step = 3.0
        moves = {'Left': (-step, 0), 'Right': (step, 0),
                 'Up': (0, -step), 'Down': (0, step)}
        if e.keysym in moves:
            self._move_screen(*moves[e.keysym])
            if self.snap:
                self._snap_point(self._sel_point_ref())
            self._resample()
            self._update_panel()
            return 'break'
        if e.keysym == 's':
            self._toggle_snap()
            return 'break'
        if e.keysym in ('plus', 'equal', 'KP_Add'):
            self._nudge_weight(0.1)
            self._resample()
            self._update_panel()
            return 'break'
        if e.keysym in ('minus', 'KP_Subtract'):
            self._nudge_weight(-0.1)
            self._resample()
            self._update_panel()
            return 'break'

    # ---------- 面板 ----------
    def _sel_point_ref(self):
        kind, obj = self.spline
        if kind == 'curve':
            return obj.P[self.sel]
        i, j = self.sel
        return obj.P[i][j]

    def _sel_weight(self):
        kind, obj = self.spline
        if kind == 'curve':
            return obj.W[self.sel]
        i, j = self.sel
        return obj.W[i][j]

    def _set_weight(self, w):
        kind, obj = self.spline
        if kind == 'curve':
            obj.W[self.sel] = w
        else:
            i, j = self.sel
            obj.W[i][j] = w

    def _update_panel(self):
        if self.spline and self.sel is not None:
            kind, obj = self.spline
            P = self._sel_point_ref()
            self.pt_label.config(
                text=(f'控制点 P{self.sel}/{len(obj.P) - 1}' if kind == 'curve'
                      else f'控制点 ({self.sel[0]},{self.sel[1]})'))
            for en in self.entries.values():
                en.delete(0, 'end')
            self.entries['x'].insert(0, f'{P[0]:.4g}')
            self.entries['y'].insert(0, f'{P[1]:.4g}')
            self.entries['z'].insert(0, f'{P[2]:.4g}')
            self.entries['w'].insert(0, f'{self._sel_weight():.4g}')
            if kind == 'curve':
                fam = ('有理 NURBS' if obj.rational else
                       ('Bézier' if obj.p == len(obj.P) - 1 else 'B 样条'))
                self.info_label.config(
                    text=f'{fam} · p={obj.p} · {len(obj.P)} 点 · '
                         f'节点 {len(obj.U)}')
            else:
                fam = '有理 NURBS' if obj.rational else 'Bézier'
                self.info_label.config(
                    text=f'{fam} 曲面 · p={obj.p},q={obj.q} · '
                         f'{len(obj.P)}×{len(obj.P[0])} 网格')
        else:
            self.pt_label.config(text='控制点 —')
            for en in self.entries.values():
                en.delete(0, 'end')
            self.info_label.config(text='')

    def _apply_panel(self):
        if not self.spline or self.sel is None:
            self._status('请先点击选中一个控制点', '#f9e2af')
            return
        try:
            vals = [float(self.entries[k].get()) for k in ('x', 'y', 'z')]
            w = float(self.entries['w'].get())
        except ValueError:
            self._status('❌ 坐标/权重须为数字', '#f38ba8')
            return
        if w <= 0:
            self._status('❌ 权重须为正数', '#f38ba8')
            return
        P = self._sel_point_ref()
        P[:] = vals
        self._set_weight(w)
        self._resample()
        self._status('✓ 控制点已更新（曲线/曲面实时重算）', '#a6e3a1')

    # ---------- 编辑: 插入/删除/重置 ----------
    def _insert_point(self):
        if not self.spline:
            return
        kind, obj = self.spline
        if kind != 'curve':
            self._status('曲面暂不支持增删控制点（可直接拖动网格点）', '#f9e2af')
            return
        i = self.sel if isinstance(self.sel, int) else len(obj.P) - 1
        p = obj.P[i]
        obj.P.insert(i + 1, [p[0] + 0.25, p[1] + 0.25, p[2] + 0.25])
        obj.W.insert(i + 1, obj.W[i])
        obj.U = nurbs.clamped_knots(len(obj.P) - 1, obj.p)
        self.sel = i + 1
        self._refresh()
        self._status(f'✓ 已在 P{i} 后插入新控制点（节点向量已重算）', '#a6e3a1')

    def _delete_point(self):
        if not self.spline:
            return
        kind, obj = self.spline
        if kind != 'curve':
            self._status('曲面暂不支持增删控制点（可直接拖动网格点）', '#f9e2af')
            return
        if len(obj.P) <= obj.p + 1:
            self._status(f'❌ 次数 p={obj.p} 至少需要 {obj.p + 1} 个控制点',
                         '#f38ba8')
            return
        obj.P.pop(self.sel)
        obj.W.pop(self.sel)
        obj.U = nurbs.clamped_knots(len(obj.P) - 1, obj.p)
        self.sel = min(self.sel, len(obj.P) - 1)
        self._refresh()
        self._status('✓ 控制点已删除', '#a6e3a1')

    def _reset_shape(self):
        if not (self.spline and self.original):
            return
        kind = self.spline[0]
        self.spline = (kind, self.original.copy())
        self._refresh()
        self._status('✓ 已重置为初始形状', '#a6e3a1')

    def _status(self, text, color):
        self.status.config(text=text, fg=color)

    # ---------- 导出与场景存档 ----------
    def _export(self, fmt):
        path = filedialog.asksaveasfilename(
            initialfile=f'spline.{fmt}', defaultextension=f'.{fmt}',
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
        if not self.spline:
            raise ValueError('没有可保存的样条')
        kind, obj = self.spline
        sp = {'kind': kind, 'name': self.name, 'P': obj.P, 'W': obj.W,
              'p': obj.p, 'U': obj.U}
        if kind == 'surface':
            sp['q'] = obj.q
            sp['V'] = obj.V
        data = {'app': 'spline3d', 'version': 1,
                'camera': self.eng.camera_state(), 'spline': sp,
                'entry': self.entry.get().strip()}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_scene(self, path):
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        if data.get('app') != 'spline3d':
            raise ValueError('不是 spline3d 场景文件')
        sp = data['spline']
        if sp['kind'] == 'curve':
            self.load_curve(sp.get('name', '载入曲线'),
                            nurbs.Curve(sp['P'], sp['W'], sp['p'], sp['U']))
        else:
            self.load_surface(sp.get('name', '载入曲面'),
                              nurbs.Surface(sp['P'], sp['W'], sp['p'],
                                            sp['q'], sp['U'], sp['V']))
        if data.get('entry'):
            self.entry.delete(0, 'end')
            self.entry.insert(0, data['entry'])
        if 'camera' in data:
            self.eng.set_camera(data['camera'])

    def _save_scene_dialog(self):
        path = filedialog.asksaveasfilename(
            initialfile='spline_scene.json', defaultextension='.json',
            filetypes=[('场景存档', '.json')])
        if not path:
            return
        try:
            self.save_scene(path)
        except (OSError, ValueError) as e:
            self._status(f'❌ 保存失败: {e}', '#f38ba8')
            return
        self._status(f'✓ 场景已保存: {path}', '#a6e3a1')

    def _load_scene_dialog(self):
        path = filedialog.askopenfilename(filetypes=[('场景存档', '.json')])
        if not path:
            return
        try:
            self.load_scene(path)
        except (OSError, ValueError, KeyError,
                json.JSONDecodeError) as e:
            self._status(f'❌ 载入失败: {e}', '#f38ba8')
            return
        self._status(f'✓ 场景已恢复: {path}', '#a6e3a1')

    # ---------- 动画导出 ----------
    def _anim_prims(self, nframes):
        """样条参数扫描帧: 曲线 u∈[0,1] 渐进描绘 / 曲面沿 u 扫掠"""
        if not self.spline:
            raise ValueError('没有样条 — 请先载入曲线或曲面')
        kind, obj = self.spline
        eng = self.eng
        saved = (eng.curves, eng.meshes, eng.segments, eng.post_draw)
        eng.post_draw = None
        w, h = eng._size()
        try:
            for k in range(nframes):
                prog = (k + 1) / nframes
                eng.curves, eng.meshes, eng.segments = [], [], []
                tip = None
                if kind == 'curve':
                    n = max(8, int(400 * prog))
                    pts = [obj.point(prog * i / n) for i in range(n + 1)]
                    eng.curves = [(pts, self._obj_color or CURVE_COLOR, 2)]
                    tip = pts[-1]
                else:
                    nu, nv = max(2, int(26 * prog)), 18
                    grid = [[obj.point(prog * i / nu, j / nv)
                             for j in range(nv + 1)] for i in range(nu + 1)]
                    base = (engine3d.hex_to_rgb(self._obj_color)
                            if self._obj_color else (148, 210, 200))
                    eng.meshes = [nurbs.shade_grid(grid, base=base)]
                prims = eng.build_prims(w, h, hud=False)
                if tip and all(math.isfinite(c) for c in tip):   # 笔尖标记
                    sx, sy, _ = eng.cam.project(*tip, w, h)
                    prims.append(('oval', sx - 5, sy - 5, sx + 5, sy + 5,
                                  '#f38ba8', '#f38ba8'))
                yield prims
        finally:
            eng.curves, eng.meshes, eng.segments, eng.post_draw = saved
            eng._redraw_soon()

    def _anim_decasteljau(self, nframes):
        """de Casteljau 构造教学动画: 控制多边形 → 逐层线性插值点 → 曲线。
        齐次坐标递推 → 自动支持有理 Bézier（权重可见地拉动曲线）。"""
        if not self.spline or self.spline[0] != 'curve':
            raise ValueError('没有曲线 — 请先载入 Bézier 曲线')
        curve = self.spline[1]
        P, W = curve.P, curve.W
        n = len(P) - 1
        if curve.p != n:
            raise ValueError('de Casteljau 演示仅支持 Bézier 曲线（次数 = 控制点数−1）: '
                             '请先在样条库载入「三次/五次 Bézier」')
        H = [(P[i][0] * W[i], P[i][1] * W[i], P[i][2] * W[i], W[i])
             for i in range(n + 1)]                 # 齐次坐标
        eng = self.eng
        saved = (eng.curves, eng.meshes, eng.segments, eng.post_draw)
        eng.post_draw = None
        w_, h_ = eng._size()
        cam = eng.cam
        try:
            traced = []
            for k in range(nframes):
                t = k / (nframes - 1)
                levels = [H]                        # 逐层递推
                cur = H
                while len(cur) > 1:
                    cur = [tuple((1 - t) * cur[i][d] + t * cur[i + 1][d]
                                 for d in range(4))
                           for i in range(len(cur) - 1)]
                    levels.append(cur)
                fh = levels[-1][0]
                final = (fh[0] / fh[3], fh[1] / fh[3], fh[2] / fh[3])
                traced.append(final)
                eng.curves, eng.meshes, eng.segments = [], [], []
                prims = eng.build_prims(w_, h_, hud=False)   # 仅坐标系
                # 1) 控制多边形 + 控制点标号
                proj0 = [cam.project(*P[i], w_, h_) for i in range(n + 1)]
                for a, b in zip(proj0, proj0[1:]):
                    prims.append(('line', a[0], a[1], b[0], b[1],
                                  NET_COLOR, 1.5, (4, 3)))
                for i, pr in enumerate(proj0):
                    prims.append(('oval', pr[0] - 5, pr[1] - 5, pr[0] + 5,
                                  pr[1] + 5, CP_COLOR, BG))
                    prims.append(('text', pr[0] + 9, pr[1] - 9, f'P{i}',
                                  CP_COLOR, 9, 'w', 'bold'))
                # 2) 各层递推点（每层一色）
                for r in range(1, len(levels)):
                    col = DEC_LEVEL_COLORS[(r - 1) % len(DEC_LEVEL_COLORS)]
                    pts3 = [tuple(levels[r][i][d] / levels[r][i][3]
                                  for d in range(3))
                            for i in range(len(levels[r]))]
                    proj = [cam.project(*p, w_, h_) for p in pts3]
                    for a, b in zip(proj, proj[1:]):
                        prims.append(('line', a[0], a[1], b[0], b[1],
                                      col, 1.5, None))
                    for pr in proj:
                        prims.append(('oval', pr[0] - 4, pr[1] - 4,
                                      pr[0] + 4, pr[1] + 4, col, col))
                # 3) 已描绘曲线
                if len(traced) > 1:
                    proj = [cam.project(*p, w_, h_) for p in traced]
                    for a, b in zip(proj, proj[1:]):
                        prims.append(('line', a[0], a[1], b[0], b[1],
                                      CURVE_COLOR, 2.5, None))
                # 4) 笔尖 + 参数标注
                fp = cam.project(*final, w_, h_)
                prims.append(('oval', fp[0] - 6, fp[1] - 6, fp[0] + 6,
                              fp[1] + 6, '#f38ba8', '#f38ba8'))
                prims.append(('text', 12, h_ - 16,
                              f'de Casteljau   t = {t:.3f}', '#9aa0b4',
                              10, 'w', ''))
                yield prims
        finally:
            eng.curves, eng.meshes, eng.segments, eng.post_draw = saved
            eng._redraw_soon()

    def _export_gif(self):
        self._export_anim_dialog('gif', self._anim_prims, 'spline_anim.gif',
                                 'frame', 36)

    def _export_svg_seq(self):
        self._export_anim_dialog('svg', self._anim_prims, None, 'frame', 24)

    def _export_decasteljau_gif(self):
        self._export_anim_dialog('gif', self._anim_decasteljau,
                                 'decasteljau.gif', 'decasteljau', 48)

    def _export_decasteljau_svg(self):
        self._export_anim_dialog('svg', self._anim_decasteljau, None,
                                 'decasteljau', 48)

    def _export_anim_dialog(self, fmt, gen, initname, prefix, default_n):
        """通用动画导出对话框: gen(nframes) → 显示列表序列"""
        from tkinter import simpledialog
        nframes = simpledialog.askinteger(
            '动画导出', '帧数（12 fps, 时长 = 帧数/12 秒）:',
            initialvalue=default_n, minvalue=8, maxvalue=240,
            parent=self.winfo_toplevel())
        if not nframes:
            return
        try:
            frames = list(gen(nframes))
        except ValueError as e:
            self._status(f'❌ {e}', '#f38ba8')
            return
        w, h = self.eng._size()
        if fmt == 'gif':
            path = filedialog.asksaveasfilename(
                initialfile=initname, defaultextension='.gif',
                filetypes=[('GIF 动画', '.gif')])
            if not path:
                return
            try:
                import animate
                imgs = [animate.prims_to_image(f, w, h) for f in frames]
                animate.save_gif(imgs, path)
            except Exception as e:
                self._status(f'❌ GIF 生成失败: {e}', '#f38ba8')
                return
            self._status(f'✓ 动画已导出 {path}（{nframes} 帧 · 12 fps）',
                         '#a6e3a1')
        else:
            d = filedialog.askdirectory()
            if not d:
                return
            import animate
            n = animate.write_svg_sequence(frames, d, w, h, prefix=prefix)
            self._status(f'✓ SVG 序列 {prefix}_000…{prefix}_{n - 1:03d}.svg → {d}',
                         '#a6e3a1')


def main():
    root = tk.Tk()
    engine3d.apply_default_fonts(root)
    root.title('Bézier / NURBS 设计器 v4 · 控制点微调')
    root.geometry('1000x780')
    app = SplineApp(root)
    app.pack(fill='both', expand=True)
    root.update_idletasks()
    app.load_curve('插值演示', nurbs.interpolate_curve(
        [(-2.5, 0, 0), (-1.5, 1.2, 0.8), (-0.5, -0.8, 1.2),
         (0.5, 1.0, -0.6), (1.5, -0.5, 0.4), (2.5, 0.6, 0)]))
    root.mainloop()


if __name__ == '__main__':
    main()
