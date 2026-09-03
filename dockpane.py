#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dockpane.py — 可停靠/可脱离面板 (多窗口支持)

DockPane 将一块界面内容包装为"活动面板":
  dock()    嵌入宿主容器 (主窗口内, 右侧或底部)
  undock()  脱离为独立 Toplevel 窗口, 可拖动标题栏移动
  toggle()  两种状态互切
内容通过 build(parent) 回调重建; 面板状态(数据)由调用方模型持有,
切换停靠方式不丢数据 (重建后调用方自行刷新, 如重建列表/同步输入框)。
浮动窗口点"关闭"= 重新停靠, 面板不会丢失。
"""
import traceback

import tkinter as tk

import engine3d

BG = engine3d.BG
HDR_BG = '#313244'
HDR_FG = '#cdd6f4'
BTN_BG = '#45475a'
FONT = ('DejaVu Sans', engine3d.font_size(9), 'bold')


class DockPane:
    """可停靠/脱离面板

    app       所属 App Frame (tk.Frame), 用于定位主窗口
    title     面板标题
    build     build(parent) 回调: 在 parent 内构建面板内容
    side      停靠方位 'right' | 'bottom'
    width     右侧停靠时的固定宽度 (bottom 停靠忽略)
    float_size 浮动窗口建议尺寸 (w, h)
    """

    def __init__(self, app, title, build, side='right', width=330,
                 float_size=(400, 640)):
        self.app = app
        self.title = title
        self.build = build
        self.side = side
        self.width = width
        self.float_size = float_size
        self.docked = True
        self.box = None          # 停靠容器 Frame
        self.win = None          # 浮动 Toplevel
        self.content = None      # 当前内容 Frame
        self._drag = None

    # ---------- 对外接口 ----------
    def dock(self, host=None):
        """嵌入宿主容器; host 缺省使用上次的宿主"""
        if host is not None:
            self.host = host
        if self.win is not None:
            self.win.destroy()
            self.win = None
        if self.box is not None:
            self.box.destroy()
        self.app.winfo_toplevel().update_idletasks()   # 销毁先落盘再重建 (同 undock)
        box = tk.Frame(self.host, bg=BG)
        if self.side == 'right':
            box.pack(side='right', fill='y', padx=(4, 8), pady=(2, 4))
            if self.width:
                box.config(width=self.width)
                box.pack_propagate(False)
        else:
            box.pack(side='bottom', fill='x', padx=8, pady=(2, 6))
        self.box = box
        self._header(box, floating=False)
        self.content = tk.Frame(box, bg=BG)
        self.content.pack(fill='both', expand=True)
        try:
            self.build(self.content)
        except Exception:            # 构建失败不拖死应用: 留回溯, 面板保持可用
            traceback.print_exc()
        self.docked = True

    def undock(self):
        """脱离为独立窗口（时序对 WSLg 友好: 销毁先落盘、建窗与定位分批）"""
        root = self.app.winfo_toplevel()
        if self.box is not None:
            self.box.destroy()
            self.box = None
            root.update_idletasks()      # 销毁/重排先刷给 X, 避免与建窗挤在同一批请求 (WSLg 断连诱因)
        win = tk.Toplevel(root)
        win.title(self.title)
        win.configure(bg=BG)
        w, h = self.float_size
        win.geometry(f'{w}x{h}')         # 先只定尺寸, 初始位置交给窗口管理器
        win.protocol('WM_DELETE_WINDOW', self.dock)   # 关闭 = 回收停靠
        self.win = win
        self._header(win, floating=True)
        self.content = tk.Frame(win, bg=BG)
        self.content.pack(fill='both', expand=True)
        try:
            self.build(self.content)
        except Exception:            # 脱离时构建失败 → 关闭浮窗回落停靠, 避免崩溃退出
            traceback.print_exc()
            win.destroy()
            self.win = None
            self.docked = False      # 使 dock() 走完整重建路径
            self.dock()
            return
        self.docked = False

        def _place():                # 定位延后到独立事件批, 失败无害 (防 WSLg 合成器崩溃)
            if self.win is None or not self.win.winfo_exists():
                return
            try:
                x = root.winfo_rootx() + root.winfo_width() + 10
                y = root.winfo_rooty() + 40
                sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
                x = max(0, min(x, sw - w))
                y = max(0, min(y, sh - h))
                win.geometry(f'+{x}+{y}')
            except tk.TclError:
                pass

        win.after(80, _place)

    def toggle(self):
        if self.docked:
            self.undock()
        else:
            self.dock()

    # ---------- 内部 ----------
    def _header(self, parent, floating):
        bar = tk.Frame(parent, bg=HDR_BG)
        bar.pack(fill='x')
        tk.Label(bar, text='  ' + self.title, bg=HDR_BG, fg=HDR_FG,
                 font=FONT, anchor='w').pack(side='left', fill='x',
                                             expand=True, ipady=3)
        if floating:
            tk.Button(bar, text='✕ 收回', command=self.dock, bg=BTN_BG,
                      fg=HDR_FG, relief='flat', font=FONT,
                      padx=6).pack(side='right', padx=(0, 3))
            # 拖动标题栏移动浮动窗口
            for wd in (bar,):
                wd.bind('<Button-1>', self._drag_start)
                wd.bind('<B1-Motion>', self._drag_move)
        else:
            tk.Button(bar, text='⬈ 脱离', command=self.undock, bg=BTN_BG,
                      fg=HDR_FG, relief='flat', font=FONT,
                      padx=6).pack(side='right', padx=(0, 3))

    def _drag_start(self, e):
        if self.win is None:
            return
        self._drag = (e.x_root - self.win.winfo_x(),
                      e.y_root - self.win.winfo_y())

    def _drag_move(self, e):
        if self.win is None or self._drag is None:
            return
        x, y = e.x_root - self._drag[0], e.y_root - self._drag[1]
        self.win.geometry(f'+{max(0, x)}+{max(0, y)}')
