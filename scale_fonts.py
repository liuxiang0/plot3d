#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将 plot3d 三个界面文件中硬编码的字体字号替换为 engine3d.font_size(...)"""
import ast
import re

FILES = ['plotter_app.py', 'spline_app.py', 'main_app.py']

# font=('Family', N) 或 font=('Family', N, 'bold'/'italic')
pat = re.compile(r"font=\('([A-Za-z0-9 ]+)', (\d+)(, '[a-z]+')?\)")

total = 0
for fn in FILES:
    src = open(fn, encoding='utf-8').read()
    new, n = pat.subn(r"font=('\1', engine3d.font_size(\2)\3)", src)
    new, m = re.subn(r"rowheight=22\b", "rowheight=engine3d.font_size(22)", new)
    ast.parse(new)  # 语法预检, 防止写入损坏
    open(fn, 'w', encoding='utf-8').write(new)
    print(f'{fn}: font 替换 {n} 处, rowheight 替换 {m} 处')
    total += n + m
print('合计:', total)
