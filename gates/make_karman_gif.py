"""导出 Kármán 涡街平移动画 GIF（与 ANIM_PRESETS 同表达式，s=0→5.66 共 24 帧）"""
import math
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import animate                                  # noqa: E402
import gallery                                  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, '..', 'plotter_app.py'), encoding='utf-8').read()
i = SRC.index('ANIM_PRESETS = [')
j = SRC.index('\n]\n', i)
PRE = [p for p in eval(SRC[i + len('ANIM_PRESETS = '):j + 2], {'math': math})  # noqa: S307
       if '涡街' in p['name']][0]

TMP = os.path.join(HERE, '..', 'output', '_gifframes')
os.makedirs(TMP, exist_ok=True)
imgs = []
for k, sv in enumerate(np.linspace(PRE['lo'], PRE['hi'], 24)):
    e2 = re.sub(r'([;,]\s*)s=[^,;]+', lambda m: m.group(1) + ('s=%.6f' % sv), PRE['expr'])
    p = os.path.join(TMP, 'f%02d.png' % k)
    gallery.render_thumb({'expr': e2, 'category': '偏微分方程解', 'name': 'karman anim'}, p)
    from PIL import Image
    imgs.append(Image.open(p).convert('RGB'))
out = os.path.join(HERE, '..', 'output', 'karman_street_anim.gif')
animate.save_gif(imgs, out, fps=12, width=480)
print('✓ GIF 已导出:', out, '(%.2f KB)' % (os.path.getsize(out) / 1024))
