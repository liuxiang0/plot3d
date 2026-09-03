#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""animate.py — 动画导出（参数扫描 → SVG 序列 / GIF）

- SVG 序列: 纯文本, 无额外依赖
- GIF: 显示列表 → PIL 软件光栅化 → 自适应调色板动画 GIF
"""
import os

import engine3d

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = ImageDraw = None


def prims_to_image(prims, w, h, bg=engine3d.BG):
    """基元显示列表 → PIL 图像（虚线/点纹按实线/实填充渲染）"""
    if Image is None:
        raise RuntimeError('未安装 Pillow: pip install Pillow')
    img = Image.new('RGB', (int(w), int(h)), bg)
    d = ImageDraw.Draw(img)
    for p in prims:
        t = p[0]
        try:
            if t == 'line':
                _, x1, y1, x2, y2, col, wd, dash = p
                d.line([(x1, y1), (x2, y2)], fill=col, width=max(1, int(wd)))
            elif t == 'poly':
                _, pts, fill, outline, stipple = p
                d.polygon([(q[0], q[1]) for q in pts], fill=fill)
            elif t == 'oval':
                _, x1, y1, x2, y2, fill, outline = p
                d.ellipse([x1, y1, x2, y2], fill=fill, outline=outline)
            elif t == 'text':
                _, x, y, s, col, size, anchor, style = p
                d.text((x, y), s, fill=col)
        except (ValueError, TypeError):
            continue
    return img


def save_gif(images, path, fps=12, width=640):
    """PIL 图像序列 → 动画 GIF（等比缩放至 width 宽, 自适应调色板）"""
    if not images:
        raise ValueError('没有动画帧')
    if Image is None:
        raise RuntimeError('未安装 Pillow: pip install Pillow')
    w0, h0 = images[0].size
    nh = max(2, int(h0 * width / w0))
    frames = [im.resize((width, nh), Image.LANCZOS)
                .convert('P', palette=Image.ADAPTIVE) for im in images]
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=max(20, int(1000 / fps)), loop=0, disposal=2)


def write_svg_sequence(frames, outdir, w, h, prefix='frame'):
    """显示列表序列 → frame_000.svg ... 返回文件数"""
    os.makedirs(outdir, exist_ok=True)
    for k, prims in enumerate(frames):
        path = os.path.join(outdir, f'{prefix}_{k:03d}.svg')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(engine3d.prims_to_svg(prims, w, h))
    return len(frames)
