#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""engine3d.py — 三维矢量渲染引擎 · 第一阶段: 坐标系

设计:
  数学层  Camera 转台投影 (az/el/zoom/target/pan), 纯双精度 → 无极缩放
  渲染层  Tkinter Canvas 矢量原语, 分辨率无关, 可导出 EPS 矢量文件
  场景层  add_curve() 折线对象, 画家算法按深度排序
  交互层  左键拖拽=旋转, 滚轮=定点缩放, Shift/中键拖拽=平移, 双击=复位
运行: python3 plot3d/engine3d.py
"""
import math
import tkinter as tk


# ====================== 全局字体缩放 ======================
FONT_SCALE = 1.4          # 界面字体缩放系数 (>1 调大, 1.0 恢复默认)


def font_size(pt):
    """按 FONT_SCALE 缩放字号; 统一控制界面控件与画布文字大小"""
    return max(1, round(pt * FONT_SCALE))


def apply_default_fonts(root=None):
    """放大 Tk 命名字体, 覆盖未显式指定字体的控件/菜单/弹窗"""
    from tkinter import font as tkfont
    base = {'TkDefaultFont': 10, 'TkTextFont': 10, 'TkFixedFont': 10,
            'TkMenuFont': 10, 'TkHeadingFont': 11, 'TkTooltipFont': 10}
    for name, pt in base.items():
        try:
            tkfont.nametofont(name).configure(size=font_size(pt))
        except tk.TclError:
            pass


# ====================== 数学层 ======================


def nice_step(raw: float) -> float:
    """自适应步长: 吸附到 {1,2,5}×10^k"""
    p = 10 ** math.floor(math.log10(raw))
    m = raw / p
    for k in (1.0, 2.0, 5.0, 10.0):
        if m <= k:
            return k * p
    return 10.0 * p


def fmt_tick(v: float, step: float) -> str:
    """刻度文字: 精度随步长, 过大/过小转科学计数"""
    if abs(v) < step * 1e-9:
        return '0'
    if abs(v) >= 1e6 or abs(v) < 1e-4:
        return f'{v:.1e}'
    dec = max(0, -int(math.floor(math.log10(step))))
    return f'{v:.{dec}f}'


class Camera:
    """转台相机: 世界 x右/y前/z上 → 屏幕坐标"""
    MIN_ZOOM, MAX_ZOOM = 1e-6, 1e8          # 像素/世界单位 → 无极缩放区间

    def __init__(self):
        self.reset()

    def reset(self):
        self.az = math.radians(-60.0)       # 方位角
        self.el = math.radians(28.0)        # 仰角
        self.zoom = 90.0
        self.tx = self.ty = self.tz = 0.0   # 注视目标
        self.panx = self.pany = 0.0         # 屏幕平移(像素)

    def clamp_el(self):
        lim = math.radians(89.4)
        self.el = max(-lim, min(lim, self.el))

    def project(self, x, y, z, w, h):
        """返回 (sx, sy, depth); depth 越大离观察者越远"""
        x -= self.tx
        y -= self.ty
        z -= self.tz
        ca, sa = math.cos(self.az), math.sin(self.az)
        X, Y = x * ca + y * sa, -x * sa + y * ca
        ce, se = math.cos(self.el), math.sin(self.el)
        depth = Y * ce - z * se
        up = Y * se + z * ce
        return (w / 2 + self.panx + X * self.zoom,
                h / 2 + self.pany - up * self.zoom, depth)


# ====================== 渲染 + 交互层 ======================

AXIS_COLORS = ('#f38ba8', '#a6e3a1', '#89b4fa')     # x红 y绿 z蓝
GRID_MAJOR, GRID_MINOR = '#2b3040', '#1c202c'
BG, FG = '#0f1117', '#9aa0b4'


def emit_arrow(emit, x1, y1, x2, y2, color, width=1.5, size=10):
    """线段 + 三角箭头（canvas/SVG/EPS 统一基元）; emit 为基元接收函数"""
    ang = math.atan2(y2 - y1, x2 - x1)
    pts = [(x2, y2)]
    for da in (math.radians(155), math.radians(-155)):
        pts.append((x2 + size * math.cos(ang + da),
                    y2 + size * math.sin(ang + da)))
    emit(('line', x1, y1, x2, y2, color, width, None))
    emit(('poly', pts, color, color, None))


def _hex_rgb(col):
    col = col.lstrip('#')
    return tuple(int(col[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def hex_to_rgb(col):
    """'#rrggbb' → (r, g, b) 0-255"""
    col = col.lstrip('#')
    return tuple(int(col[i:i + 2], 16) for i in (0, 2, 4))


def cue_color(col, t):
    """景深调色: 颜色按 t 比例向背景色淡出（支持 (颜色,stipple) 元组）"""
    if t <= 0:
        return col
    if isinstance(col, tuple):
        return (_cue_hex(col[0], t), col[1])
    return _cue_hex(col, t)


def _cue_hex(hexcol, t):
    r, g, b = hex_to_rgb(hexcol)
    br, bg_, bb_ = hex_to_rgb(BG)
    f = max(0.0, 1.0 - t)
    return '#%02x%02x%02x' % (int(br + (r - br) * f),
                              int(bg_ + (g - bg_) * f),
                              int(bb_ + (b - bb_) * f))


def prims_to_svg(prims, w, h, bg=BG):
    """基元显示列表 → SVG 文本（引擎视图与动画帧共用）"""
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" '
           f'height="{h}" viewBox="0 0 {w} {h}">',
           f'<rect width="{w}" height="{h}" fill="{bg}"/>']
    for p in prims:
        t = p[0]
        if t == 'line':
            _, x1, y1, x2, y2, col, wd, dash = p
            d = f' stroke-dasharray="{dash[0]},{dash[1]}"' if dash else ''
            out.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" '
                       f'y2="{y2:.2f}" stroke="{col}" stroke-width="{wd}"{d}/>')
        elif t == 'poly':
            _, pts, fill, outline, stipple = p
            pstr = ' '.join(f'{q[0]:.2f},{q[1]:.2f}' for q in pts)
            op = ' fill-opacity="0.5"' if stipple else ''
            out.append(f'<polygon points="{pstr}" fill="{fill}"{op} '
                       f'stroke="{outline}" stroke-width="0.4"/>')
        elif t == 'oval':
            _, x1, y1, x2, y2, fill, outline = p
            out.append(f'<circle cx="{(x1 + x2) / 2:.2f}" '
                       f'cy="{(y1 + y2) / 2:.2f}" r="{(x2 - x1) / 2:.2f}" '
                       f'fill="{fill}" stroke="{outline}" stroke-width="1"/>')
        elif t == 'text':
            _, x, y, s, col, size, anchor, style = p
            anch = {'w': 'start', 'e': 'end', 'nw': 'start',
                    'ne': 'end'}.get(anchor, 'middle')
            sty = ((' font-style="italic"' if 'italic' in style else '')
                   + (' font-weight="bold"' if 'bold' in style else ''))
            esc = (s.replace('&', '&amp;').replace('<', '&lt;')
                    .replace('>', '&gt;'))
            out.append(f'<text x="{x:.2f}" y="{y:.2f}" fill="{col}" '
                       f'font-size="{size}" font-family="DejaVu Sans, '
                       f'sans-serif" text-anchor="{anch}"{sty}>{esc}</text>')
    out.append('</svg>')
    return '\n'.join(out)


class Engine3D(tk.Frame):
    def __init__(self, master, width=920, height=680):
        super().__init__(master, bg=BG)
        self.cam = Camera()
        self.show_grid = True
        self.show_axes = True                       # 坐标轴开关 (快捷键 a)
        self.curves = []                            # [(points, color, width)]
        self.meshes = []                            # [[(quad4pts, color), ...]]
        self.segments = []                          # [(segs[(p1,p2)..], color, width)]
        self.cv = tk.Canvas(self, width=width, height=height,
                            bg=BG, highlightthickness=0)
        self.cv.pack(fill='both', expand=True)
        self._pending = False
        self.post_draw = None                       # 渲染后回调（控制点覆盖层等）
        self.interact_lock = False                  # True 时禁用旋转/平移（控制点拖拽模式）
        self.lod = 1                                # 交互 LOD: 1=全精度, 2=1/4 面片（旋转中）
        self.surface_mode = 'solid'                 # 曲面渲染: solid|wire|both
        self.on_view_change = None                  # 缩放/平移回调（曲线自适应重采样）
        self.depth_cue = 0.0                        # 景深强度: 0=关, 推荐 0.5~0.8
        self._bind()
        self._redraw_soon()

    # ---------- 对外场景 API ----------
    def add_curve(self, points, color='#f9e2af', width=2):
        """添加三维折线: points = [(x,y,z), ...]"""
        self.curves.append((list(points), color, width))
        self._redraw_soon()

    def add_mesh(self, quads):
        """quads = [((p0,p1,p2,p3), color), ...] 画家算法填充网格"""
        self.meshes.append(list(quads))
        self._redraw_soon()

    def add_segments(self, segs, color='#a6e3a1', width=2):
        """segs = [(p1, p2), ...] 批量短线段（Marching Squares 输出等）"""
        self.segments.append((list(segs), color, width))
        self._redraw_soon()

    def clear_all(self):
        self.curves.clear()
        self.meshes.clear()
        self.segments.clear()
        self._redraw_soon()

    def clear_curves(self):
        self.clear_all()

    def save_eps(self, path='plot3d.eps'):
        """导出 EPS 矢量文件"""
        self.to_eps(path)

    # ---------- 矢量导出 ----------
    def to_svg(self, path, w=None, h=None, hud=False):
        """导出当前视图为 SVG 矢量文件（stipple → fill-opacity 半透明）"""
        if w is None:
            w, h = self._size()
        with open(path, 'w', encoding='utf-8') as f:
            f.write(prims_to_svg(self.build_prims(w, h, hud=hud), w, h))

    def to_eps(self, path, w=None, h=None, hud=False):
        """导出当前视图为 EPS 矢量文件（原生 PostScript 写入, 无需显示环境）"""
        if w is None:
            w, h = self._size()
        L = ['%!PS-Adobe-3.0 EPSF-3.0',
             f'%%BoundingBox: 0 0 {int(math.ceil(w))} {int(math.ceil(h))}',
             '%%Creator: plot3d engine3d',
             f'0 {h:.2f} translate', '1 -1 scale', '1 setlinejoin']
        bg = _hex_rgb(BG)
        L.append(f'{bg[0]:.3f} {bg[1]:.3f} {bg[2]:.3f} setrgbcolor '
                 f'0 0 {w:.2f} {h:.2f} rectfill')
        for p in self.build_prims(w, h, hud=hud):
            t = p[0]
            if t == 'line':
                _, x1, y1, x2, y2, col, wd, dash = p
                c = _hex_rgb(col)
                ds = f'[{dash[0]} {dash[1]}] 0 setdash' if dash else '[] 0 setdash'
                L.append(f'{ds} {wd} setlinewidth {c[0]:.3f} {c[1]:.3f} '
                         f'{c[2]:.3f} setrgbcolor {x1:.2f} {y1:.2f} moveto '
                         f'{x2:.2f} {y2:.2f} lineto stroke')
            elif t == 'poly':
                _, pts, fill, outline, stipple = p
                c = _hex_rgb(fill)
                body = ' '.join(f'{q[0]:.2f} {q[1]:.2f} lineto'
                                for q in pts[1:])
                L.append(f'{c[0]:.3f} {c[1]:.3f} {c[2]:.3f} setrgbcolor '
                         f'{pts[0][0]:.2f} {pts[0][1]:.2f} moveto {body} '
                         f'closepath fill')
            elif t == 'oval':
                _, x1, y1, x2, y2, fill, outline = p
                c = _hex_rgb(fill)
                cx, cy, r = (x1 + x2) / 2, (y1 + y2) / 2, (x2 - x1) / 2
                L.append(f'{c[0]:.3f} {c[1]:.3f} {c[2]:.3f} setrgbcolor '
                         f'{cx:.2f} {cy:.2f} {r:.2f} 0 360 arc fill')
            elif t == 'text':
                _, x, y, s, col, size, anchor, style = p
                c = _hex_rgb(col)
                fname = ('Helvetica-Bold' if 'bold' in style else
                         ('Helvetica-Oblique' if 'italic' in style
                          else 'Helvetica'))
                esc = (s.replace('\\', '\\\\').replace('(', '\\(')
                        .replace(')', '\\)'))
                wx = 0.52 * size * len(s)                     # 近似字宽(锚点修正)
                xa = 0 if anchor in ('w', 'nw') else (-wx if anchor in ('e', 'ne')
                                                      else -wx / 2)
                ya = -0.8 * size if anchor in ('nw', 'ne') else -0.35 * size
                L.append(f'gsave {x:.2f} {y:.2f} translate 1 -1 scale '
                         f'{c[0]:.3f} {c[1]:.3f} {c[2]:.3f} setrgbcolor '
                         f'/{fname} findfont {size} scalefont setfont '
                         f'{xa:.2f} {ya:.2f} moveto ({esc}) show grestore')
        L.append('showpage')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(L) + '\n')

    # ---------- 相机状态（场景存档） ----------
    def camera_state(self):
        c = self.cam
        return {'az': c.az, 'el': c.el, 'zoom': c.zoom, 'panx': c.panx,
                'pany': c.pany, 'tx': c.tx, 'ty': c.ty, 'tz': c.tz}

    def set_camera(self, d):
        for k in ('az', 'el', 'zoom', 'panx', 'pany', 'tx', 'ty', 'tz'):
            if k in d:
                setattr(self.cam, k, float(d[k]))
        self.cam.clamp_el()
        self._redraw_soon()

    # ---------- 事件绑定 ----------
    def _bind(self):
        cv = self.cv
        cv.bind('<ButtonPress-1>', self._on_press)
        cv.bind('<B1-Motion>', self._on_rotate)
        cv.bind('<Shift-ButtonPress-1>', self._on_press)
        cv.bind('<Shift-B1-Motion>', self._on_pan)
        cv.bind('<ButtonPress-2>', self._on_press)
        cv.bind('<B2-Motion>', self._on_pan)
        cv.bind('<Double-Button-1>', lambda e: self._reset())
        cv.bind('<MouseWheel>', self._on_wheel)     # Windows / macOS
        cv.bind('<Button-4>', self._on_wheel)       # X11 / WSLg 滚轮上
        cv.bind('<Button-5>', self._on_wheel)       # 滚轮下
        cv.bind('<Configure>', lambda e: self._redraw_soon())
        cv.bind('<ButtonRelease-1>', self._on_release)
        cv.bind('<Key-r>', lambda e: self._reset())
        cv.bind('<Key-g>', self._toggle_grid)
        cv.bind('<Key-a>', self._toggle_axes)
        cv.focus_set()

    def _on_press(self, e):
        if self.interact_lock:
            return
        self._last = (e.x, e.y)
        self.lod = 2                                # 交互中: 粗 LOD 提升帧率
        self.cv.focus_set()

    def _on_release(self, e):
        if self.lod != 1:
            self.lod = 1                            # 松手恢复全精度
            self._redraw_soon()

    def _on_rotate(self, e):
        if self.interact_lock:
            return
        lx, ly = getattr(self, '_last', (e.x, e.y))
        self.cam.az += (e.x - lx) * 0.008
        self.cam.el -= (e.y - ly) * 0.008
        self.cam.clamp_el()
        self._last = (e.x, e.y)
        self._redraw_soon()

    def _on_pan(self, e):
        if self.interact_lock:
            return
        lx, ly = getattr(self, '_last', (e.x, e.y))
        self.cam.panx += e.x - lx
        self.cam.pany += e.y - ly
        self._last = (e.x, e.y)
        if self.on_view_change:
            self.on_view_change()
        self._redraw_soon()

    def _on_wheel(self, e):
        if getattr(e, 'num', 0) == 4:
            f = 1.15
        elif getattr(e, 'num', 0) == 5:
            f = 1 / 1.15
        else:
            f = 1.15 if getattr(e, 'delta', 120) > 0 else 1 / 1.15
        self._zoom_at(e.x, e.y, f)

    def _zoom_at(self, mx, my, f):
        """定点缩放: 保持光标下的世界点屏幕位置不变"""
        cam = self.cam
        w, h = self._size()
        X = (mx - w / 2 - cam.panx) / cam.zoom
        up = (h / 2 + cam.pany - my) / cam.zoom
        cam.zoom = min(cam.MAX_ZOOM, max(cam.MIN_ZOOM, cam.zoom * f))
        cam.panx = mx - w / 2 - X * cam.zoom
        cam.pany = my - h / 2 + up * cam.zoom
        if self.on_view_change:
            self.on_view_change()
        self._redraw_soon()

    def _reset(self):
        self.cam.reset()
        self._redraw_soon()

    def _toggle_grid(self, e=None):
        self.show_grid = not self.show_grid
        self._redraw_soon()

    def _toggle_axes(self, e=None):
        self.show_axes = not self.show_axes
        self._redraw_soon()

    # ---------- 绘制 ----------
    def _redraw_soon(self):
        """合并同一事件循环内的多次重绘请求"""
        if not self._pending:
            self._pending = True
            self.after_idle(self._do_draw)

    def _do_draw(self):
        self._pending = False
        self.draw()

    def _size(self):
        w, h = self.cv.winfo_width(), self.cv.winfo_height()
        if w < 2:
            w = int(self.cv['width'])
        if h < 2:
            h = int(self.cv['height'])
        return w, h

    def draw(self):
        w, h = self._size()
        self._render_canvas(self.build_prims(w, h))

    # ---------- 显示列表: 投影 → 基元 → canvas/SVG/EPS ----------
    def build_prims(self, w, h, hud=True):
        """构建基元显示列表（分辨率无关, 供屏幕绘制与矢量导出共用）"""
        prims = []
        step = nice_step(80.0 / self.cam.zoom)
        R = math.hypot(w, h) / 2 / self.cam.zoom + step * 2   # 可见半径(含余量)
        if self.show_grid:
            self._grid_prims(prims, w, h, R, step)
        if self.show_axes:
            self._axes_prims(prims, w, h, R, step)
        self._scene_prims(prims, w, h)
        self._triad_prims(prims, w, h)
        if hud:
            self._hud_prims(prims, w, h)
        if self.post_draw:
            self.post_draw(w, h, prims.append)
        return prims

    def _render_canvas(self, prims):
        cv = self.cv
        cv.delete('all')
        for p in prims:
            t = p[0]
            if t == 'line':
                _, x1, y1, x2, y2, col, wd, dash = p
                cv.create_line(x1, y1, x2, y2, fill=col, width=wd,
                               **({'dash': dash} if dash else {}))
            elif t == 'poly':
                _, pts, fill, outline, stipple = p
                flat = [c for q in pts for c in (q[0], q[1])]
                cv.create_polygon(flat, fill=fill, outline=outline,
                                  **({'stipple': stipple} if stipple else {}))
            elif t == 'oval':
                _, x1, y1, x2, y2, fill, outline = p
                cv.create_oval(x1, y1, x2, y2, fill=fill, outline=outline)
            elif t == 'text':
                _, x, y, s, col, size, anchor, style = p
                sz = font_size(size)
                font = (('DejaVu Sans', sz, style) if style
                        else ('DejaVu Sans', sz))
                cv.create_text(x, y, text=s, fill=col, font=font, anchor=anchor)

    def _seg(self, p1, p2, w, h):
        x1, y1, _ = self.cam.project(*p1, w, h)
        x2, y2, _ = self.cam.project(*p2, w, h)
        return x1, y1, x2, y2

    def set_surface_mode(self, mode):
        """曲面渲染模式: solid 实体 / wire 线框 / both 实体+线框"""
        if mode in ('solid', 'wire', 'both'):
            self.surface_mode = mode
            self._redraw_soon()

    def set_depth_cue(self, strength):
        """景深强度: 0=关, 推荐 0.5~0.8（远处对象向背景色淡出, 强化空间纵深）"""
        self.depth_cue = max(0.0, min(0.95, float(strength)))
        self._redraw_soon()

    def adaptive_polyline(self, pt_fn, t0=0.0, t1=1.0, w=None, h=None,
                          flat_px=0.6, min_px=1.5, max_depth=8, base=80):
        """屏幕空间自适应参数采样: 弦中点偏差距准则 → 任意缩放下曲线光滑。
        pt_fn(t) → (x,y,z); 平坦处稀疏、高曲率/放大处自动加密。"""
        if w is None:
            w, h = self._size()
        cam = self.cam
        pts = []

        def rec(a, ta, b, tb, d):
            tm = (ta + tb) / 2.0
            m = pt_fn(tm)
            if (all(math.isfinite(c) for c in a)
                    and all(math.isfinite(c) for c in b)
                    and all(math.isfinite(c) for c in m)):
                sa = cam.project(*a, w, h)
                sb = cam.project(*b, w, h)
                sm = cam.project(*m, w, h)
                dev = math.hypot(sm[0] - (sa[0] + sb[0]) / 2.0,
                                 sm[1] - (sa[1] + sb[1]) / 2.0)
                length = math.hypot(sa[0] - sb[0], sa[1] - sb[1])
                if d > 0 and dev > flat_px and length > min_px:
                    rec(a, ta, m, tm, d - 1)
                    rec(m, tm, b, tb, d - 1)
                    return
            pts.append(b)

        pts.append(pt_fn(t0))
        for i in range(base):
            ta = t0 + (t1 - t0) * i / base
            tb = t0 + (t1 - t0) * (i + 1) / base
            rec(pt_fn(ta), ta, pt_fn(tb), tb, max_depth)
        return pts

    def _grid_prims(self, prims, w, h, R, step):
        minor = step / 5.0
        if minor * self.cam.zoom >= 13:                       # 次网格自动显现
            nm = int(math.ceil(R / minor))
            for k in range(-nm, nm + 1):
                if k % 5 == 0:
                    continue
                v = k * minor
                prims.append(('line', *self._seg((v, -R, 0), (v, R, 0), w, h),
                              GRID_MINOR, 1, None))
                prims.append(('line', *self._seg((-R, v, 0), (R, v, 0), w, h),
                              GRID_MINOR, 1, None))
        n = int(math.ceil(R / step))
        for k in range(-n, n + 1):
            if k == 0:
                continue                                      # 0 位置留给坐标轴
            v = k * step
            prims.append(('line', *self._seg((v, -R, 0), (v, R, 0), w, h),
                          GRID_MAJOR, 1, None))
            prims.append(('line', *self._seg((-R, v, 0), (R, v, 0), w, h),
                          GRID_MAJOR, 1, None))

    def _axes_prims(self, prims, w, h, R, step):
        for i, color in enumerate(AXIS_COLORS):
            a, b = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
            a[i], b[i] = -R, R
            emit_arrow(prims.append, *self._seg(tuple(a), tuple(b), w, h),
                       color, 1.6, 11)
            lx, ly, _ = self.cam.project(*b, w, h)
            prims.append(('text', lx + 10, ly - 8, 'xyz'[i], color, 12,
                          'center', 'italic bold'))
        # 刻度线与刻度值
        nk = int(R // step)
        for i in range(3):
            for k in range(-nk, nk + 1):
                if k == 0:
                    continue
                v = k * step
                p = [0.0, 0.0, 0.0]
                p[i] = v
                sx, sy, _ = self.cam.project(*p, w, h)
                prims.append(('line', sx, sy - 3, sx, sy + 3,
                              AXIS_COLORS[i], 1.4, None))
                prims.append(('text', sx + 2, sy + 11, fmt_tick(v, step),
                              FG, 8, 'center', ''))
        ox, oy, _ = self.cam.project(0, 0, 0, w, h)
        prims.append(('text', ox - 9, oy + 10, 'O', FG, 9, 'center', ''))

    def _scene_prims(self, prims, w, h):
        """画家算法统一渲染: 曲面片(实体/线框/两者)+曲线/线段, 按深度远→近绘制"""
        items = []
        step = self.lod * self.lod
        mode = self.surface_mode
        for quads in self.meshes:
            if step > 1:
                quads = quads[::step]                         # LOD 抽稀
            if mode in ('solid', 'both'):
                for P, col in quads:
                    pr = [self.cam.project(*p, w, h) for p in P]
                    d = sum(q[2] for q in pr) / len(pr)
                    items.append((d, 0, 'q', pr, col, None))
            if mode in ('wire', 'both'):                      # 线划图: 共享棱去重
                seen = set()
                cache = {}
                for P, col in quads:
                    lc = col[0] if isinstance(col, tuple) else col
                    np_ = len(P)
                    for k in range(np_):
                        a, b = P[k], P[(k + 1) % np_]
                        ek = frozenset((a, b))
                        if len(ek) < 2 or ek in seen:
                            continue
                        seen.add(ek)
                        pa = cache.get(a)
                        if pa is None:
                            pa = cache[a] = self.cam.project(*a, w, h)
                        pb = cache.get(b)
                        if pb is None:
                            pb = cache[b] = self.cam.project(*b, w, h)
                        items.append(((pa[2] + pb[2]) / 2.0, 1, 'l', pa, pb,
                                      (lc, 1)))
        for pts, color, width in self.curves:
            proj = [self.cam.project(*p, w, h) for p in pts]
            for a, b in zip(proj, proj[1:]):
                items.append(((a[2] + b[2]) / 2.0, 1, 'l', a, b, (color, width)))
        for segs, color, width in self.segments:
            for p1, p2 in segs:
                a = self.cam.project(*p1, w, h)
                b = self.cam.project(*p2, w, h)
                items.append(((a[2] + b[2]) / 2.0, 1, 'l', a, b, (color, width)))
        items.sort(key=lambda it: (-it[0], it[1]))
        cue = self.depth_cue
        if cue > 0 and items:                        # 景深: 按深度向背景淡出
            ds = [it[0] for it in items]
            dmin, dmax = min(ds), max(ds)
            dspan = (dmax - dmin) or 1.0
        for it in items:
            if it[2] == 'q':
                pr, col = it[3], it[4]
                if cue > 0:
                    col = cue_color(col, cue * (it[0] - dmin) / dspan)
                pts2 = [(p[0], p[1]) for p in pr]             # 三角形/四边形通用
                if isinstance(col, tuple):                    # (颜色, stipple) 半透明
                    prims.append(('poly', pts2, col[0], col[0], col[1]))
                else:
                    prims.append(('poly', pts2, col, col, None))
            else:
                a, b, (color, width) = it[3], it[4], it[5]
                if cue > 0:
                    color = cue_color(color, cue * (it[0] - dmin) / dspan)
                prims.append(('line', a[0], a[1], b[0], b[1], color, width, None))

    def _triad_prims(self, prims, w, h):
        """左下角视角三轴指示器"""
        ox, oy, L = 46, h - 46, 26
        p0 = self.cam.project(0, 0, 0, w, h)
        for i, color in enumerate(AXIS_COLORS):
            v = [0.0, 0.0, 0.0]
            v[i] = 1.0
            p1 = self.cam.project(*v, w, h)
            dx, dy = p1[0] - p0[0], p1[1] - p0[1]
            nrm = math.hypot(dx, dy) or 1.0
            ux, uy = dx / nrm, dy / nrm
            emit_arrow(prims.append, ox, oy, ox + ux * L, oy + uy * L,
                       color, 2, 8)
            prims.append(('text', ox + ux * (L + 10), oy + uy * (L + 10),
                          'xyz'[i], color, 9, 'center', 'bold'))

    def _hud_prims(self, prims, w, h):
        c = self.cam
        info = (f"az={math.degrees(c.az):.0f}\u00b0  "
                f"el={math.degrees(c.el):.0f}\u00b0  "
                f"scale={c.zoom:.6g} px/u")
        prims.append(('text', 10, 10, info, FG, 9, 'nw', ''))
        prims.append(('text', w - 10, 10,
                      'drag=rotate · wheel=zoom · shift+drag=pan '
                      '· dblclick=reset · g=grid', '#5b6178', 9, 'ne', ''))


# ====================== 演示（测试对象, 后期由表达式输入替代） ======================

def _demo_curves(eng):
    helix, circle = [], []
    for i in range(629):                          # t: 0 → 4π
        t = i * 0.02
        helix.append((math.cos(t), math.sin(t), t / 6.0))
        circle.append((1.6 * math.cos(t), 1.6 * math.sin(t), 0.0))
    eng.add_curve(circle, '#89b4fa', 2)           # z=0 平面圆
    eng.add_curve(helix, '#f9e2af', 2)            # 螺旋线


def main():
    root = tk.Tk()
    root.title('3D 矢量引擎 v1 · 坐标系')
    root.geometry('920x680')
    eng = Engine3D(root)
    eng.pack(fill='both', expand=True)
    _demo_curves(eng)
    root.mainloop()


if __name__ == '__main__':
    main()
