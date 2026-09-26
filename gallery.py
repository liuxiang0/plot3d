#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gallery.py — 曲线画廊: 缩略图网格 + 搜索过滤, 点击一键载入绘图器

- 缩略图: 纯 PIL 离屏渲染（无 matplotlib 依赖）, 缓存至 thumbs/<key>.png
- 八形态全覆盖: explicit2d / surface / implicit2d / implicit3d /
  parametric / param_surface / inequality2d / inequality3d
- 平面图形自动俯视图, 立体图形用与主引擎一致的转台相机视角
"""
import json
import math
import os

import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageDraw, ImageTk

import curve_library
import engine3d
import mathparse
from plotter_app import marching_squares, marching_cubes_adaptive

DIR = os.path.dirname(os.path.abspath(__file__))
THUMB_DIR = os.path.join(DIR, 'thumbs')
FAV_FILE = os.path.join(DIR, 'gallery_favs.json')
SIZE = 200                     # 缩略图像素
FAV_CAT = '⭐ 收藏'
BG = engine3d.BG

CAT_COLORS = {
    '平面代数曲线': '#f9e2af', '极坐标曲线': '#74c7ec', '空间曲线': '#94e2d5',
    '经典曲面': '#b4befe', '隐式曲面': '#89b4fa',
    '参数曲面': '#f38ba8', '极小曲面': '#a6e3a1',
    '不等式区域': '#fab387',
}
DEFAULT_COLOR = '#cba6f7'

# 著名曲线/曲面资料卡: 公式 + 性质 + 典故（未收录条目回退 expr+desc）
CARDS = {
    'circle': {'formula': '$x^2+y^2=r^2$', 'props': ['次数 2 · 亏格 0', '曲率 κ=1/r 恒定'],
               'trivia': '到定点距离相等的点的轨迹，平面最对称的曲线。'},
    'ellipse': {'formula': '$\\frac{x^2}{a^2}+\\frac{y^2}{b^2}=1$',
                'props': ['焦点 (±c,0)，c²=a²−b²', '离心率 e=c/a ∈ (0,1)'],
                'trivia': '动点到两焦点距离之和恒为 2a——开普勒行星轨道。'},
    'hyperbola': {'formula': '$\\frac{x^2}{a^2}-\\frac{y^2}{b^2}=1$',
                  'props': ['渐近线 y=±(b/a)x', '离心率 e=c/a > 1'],
                  'trivia': '到两焦点距离之差恒定；彗星逃逸轨道的形状。'},
    'astroid': {'formula': '$x^{2/3}+y^{2/3}=a^{2/3}$',
                'props': ['代数次数 6 · 4 个尖点', '周长 6a · 面积 3πa²/8'],
                'trivia': '梯子靠墙下滑时中点的包络线（“梯子曲线”）。'},
    'cardioid': {'formula': '$r=a(1-\\cos\\theta)$',
                 'props': ['等径外摆线', '弧长 8a'],
                 'trivia': 'Mandelbrot 集主体成分的边界正是心脏线。'},
    'lemniscate': {'formula': '$(x^2+y^2)^2=2a^2(x^2-y^2)$',
                   'props': ['四次曲线 · 原点为二重点', '亏格 0'],
                   'trivia': '伯努利 1694 年命名，∞ 符号的数学原型。'},
    'folium': {'formula': '$x^3+y^3=3axy$',
               'props': ['三次曲线 · 原点为结点', '渐近线 x+y+a=0'],
               'trivia': '笛卡尔 1638；传说用来向费马的切线法挑战。'},
    'cycloid': {'formula': '$x=a(t-\\sin t),\\ y=a(1-\\cos t)$',
                'props': ['一拱弧长 8a', '拱下面积 = 3 倍滚圆面积'],
                'trivia': '最速降线与等时降线都是它——伯努利/牛顿/莱布尼茨的擂台题。'},
    'witch': {'formula': '$y=\\frac{8a^3}{x^2+4a^2}$',
              'props': ['三次相关曲线', '渐近线 y=0'],
              'trivia': '“巫婆”实为翻译误会（versoria→aggessina）；柯西分布密度曲线。'},
    'cissoid': {'formula': '$y^2=\\frac{x^3}{2a-x}$',
                'props': ['尖点在原点', 'x=2a 为垂直渐近线'],
                'trivia': '古希腊三大曲线之一，曾用于尝试倍立方问题。'},
    'elliptic_curve': {'formula': '$y^2=x^3+ax+b$（Δ≠0）',
                       'props': ['亏格 1', '点集构成阿贝尔群（弦切法）'],
                       'trivia': 'ECC 密码学的核心；怀尔斯证费马大定理的舞台。'},
    'butterfly': {'formula': '$r=e^{\\cos\\theta}-2\\cos4\\theta+\\sin^5\\frac{\\theta}{12}$',
                  'props': ['超越曲线（非代数）', '需 t∈[0,12π] 才完整'],
                  'trivia': 'Tempest 1989：“我确认它像一只蝴蝶。”'},
    'rose': {'formula': '$r=a\\cos(k\\theta)$',
             'props': ['k 奇 → k 瓣', 'k 偶 → 2k 瓣'],
             'trivia': '棣莫弗 18 世纪研究的极坐标花瓣曲线。'},
    'involute': {'formula': '$x=a(\\cos t+t\\sin t),\\ y=a(\\sin t-t\\cos t)$',
                 'props': ['法线恒切于基圆', '渐开线齿轮齿廓'],
                 'trivia': '惠更斯 1673 用于摆钟；今天所有齿轮都用它。'},
    'spirograph': {'formula': '$z=(R-r)e^{it}+d\\,e^{i(R-r)t/r}$',
                   'props': ['闭合条件: (R−r)/r 有理', 'R=5,r=3 周期 6π'],
                   'trivia': 'Spirograph 玩具 1965 年发明，2019 年数学界还为它发过论文。'},
    'helix': {'formula': '$r(t)=(a\\cos t, a\\sin t, bt)$',
              'props': ['κ=a/(a²+b²) 恒定', 'τ=b/(a²+b²) 恒定'],
              'trivia': 'DNA 双螺旋的形状；κ/τ 均为常数是它的刻画。'},
    'trefoil': {'formula': '$x=\\sin t+2\\sin2t,\\ y=\\cos t-2\\cos2t,\\ z=-\\sin3t$',
                'props': ['(2,3) 环面纽结', '交叉数 3（最少）'],
                'trivia': '最简单的非平凡纽结；三叶结与其镜像不等价（手性）。'},
    'viviani': {'formula': '球 $x^2+y^2+z^2=a^2$ ∩ 柱 $(x-a/2)^2+y^2=(a/2)^2$',
                'props': ['8 字形自交', 'Viviani 窗口'],
                'trivia': 'Viviani 1700 提给莱布尼茨的谜题：球面上开窗使剩余面积可“化圆为方”。'},
    'loxodrome': {'formula': '$r(t)=(\\mathrm{sech}\\,t\\cos kt,\\ \\mathrm{sech}\\,t\\sin kt,\\ \\tanh t)$',
                  'props': ['与所有经线等角相交', '墨卡托投影下为直线'],
                  'trivia': '大航海时代的等角航线；永远到不了极点却绕无穷圈。'},
    'torus': {'formula': '$(x^2+y^2+z^2+R^2-r^2)^2=4R^2(x^2+y^2)$',
              'props': ['亏格 1', '高斯曲率有正有负'],
              'trivia': '拓扑学的“甜甜圈”；与咖啡杯同胚是经典科普。'},
    'gyroid': {'formula': '$\\sin x\\cos y+\\sin y\\cos z+\\sin z\\cos x=0$',
               'props': ['三重周期极小曲面 (TPMS)', '无直线、无镜面对称'],
               'trivia': 'Schoen 1970；出现在蝴蝶翅膀鳞片与细胞膜里。'},
    'schwarz_p': {'formula': '$\\cos x+\\cos y+\\cos z=0$',
                  'props': ['TPMS · 立方对称', '界面面积局部最小'],
                  'trivia': 'Schwarz 1865；块体共聚物自组装的经典形态。'},
    'scherk': {'formula': '$e^z=\\frac{\\cos x}{\\cos y}$',
               'props': ['极小曲面', '无穷多翼片棋盘状交错'],
               'trivia': '1834，悬链面/螺旋面之后 90 年才发现的下一个极小曲面。'},
    'mobius': {'formula': '$r(u,v)=((R+v\\cos\\frac u2)\\cos u,\\dots,\\ v\\sin\\frac u2)$',
               'props': ['单侧 · 不可定向', '边界为一条闭曲线'],
               'trivia': 'Möbius 与 Listing 1858 独立发现；回收标志就是它。'},
    'klein': {'formula': 'figure-8 浸入（8 字形截面绕环）',
              'props': ['不可定向闭曲面', 'R³ 中必自交'],
              'trivia': '“装不满也倒不出水的瓶子”；在 R⁴ 中可无自交嵌入。'},
    'catenoid': {'formula': '$r(u,v)=(c\\cosh v\\cos u,\\ c\\cosh v\\sin u,\\ cv)$',
                 'props': ['极小曲面 · K≤0', '与螺旋面共轭'],
                 'trivia': '两个肥皂圈之间的自然形状；Euler 1744 证明其极小性。'},
    'enneper': {'formula': '$x=u-\\frac{u^3}{3}+uv^2$ 等三分量',
                'props': ['极小曲面', '自交三折'],
                'trivia': 'Enneper 1864；与悬链面并列为最早的非平凡极小曲面。'},
    'gabriel': {'formula': '$y=1/x$ 绕 x 轴旋转（x≥1）',
                'props': ['体积 = π（有限）', '表面积 = ∞'],
                'trivia': '托里拆利 1641：“装满油漆却永远刷不完内壁”。'},
    'pseudosphere': {'formula': '曳物线绕渐近线旋转',
                     'props': ['K=−1 恒定', '有奇缘（曳物线尖点）'],
                     'trivia': 'Beltrami 1868 用它给出双曲几何的第一个实体模型。'},
    'dini': {'formula': '$z=\\cos v+\\ln\\tan\\frac v2+bu$',
             'props': ['K=−1 恒定', '伪球面的螺旋变形'],
             'trivia': 'Dini 1865；负曲率曲面可以拧成麻花而不改变 K。'},
    'monkey_saddle': {'formula': '$z=x^3-3xy^2=\\mathrm{Re}(x+iy)^3$',
                     'props': ['三阶鞍点', '三个凹陷 + 三条平坦射线'],
                     'trivia': '“猴子鞍”：两个凹陷放腿，一个放尾巴。'},
    'heart_surface': {'formula': '$(x^2+\\frac94y^2+z^2-1)^3=x^2z^3+\\frac{9}{80}y^2z^3$',
                     'props': ['六次隐式曲面', '关于 y=0 对称'],
                     'trivia': '互联网上流传的“3D 爱心”方程。'},
    'roman': {'formula': '$x^2y^2+y^2z^2+z^2x^2=xyz$',
              'props': ['四次 · 三重自交线', '3 个 pinch point'],
              'trivia': 'Steiner 1844 罗马之行后命名；射影平面到 R³ 的浸入。'},
    'whitney': {'formula': '$x^2=y^2z$',
                'props': ['奇点集为一条直线（伞柄）', '不可整体参数化'],
                'trivia': 'Whitney 1944；奇点论的入门标本。'},
    'superellipsoid': {'formula': '$|x|^n+|y|^n+|z|^n=1$',
                       'props': ['n=2 球 · n→∞ 立方', '此处 n=4'],
                       'trivia': 'Piet Hein 的“超蛋”灵感来源；Barr 1981 用于计算机图形建模。'},
    'kummer': {'formula': '$(x^2+y^2+z^2-\\mu^2)^2=\\lambda\\,pqrs$',
               'props': ['四次曲面 · 16 节点（四次曲面的上限）', 'λ=(3μ²−1)/(3−μ²)，此处 μ²=2'],
               'trivia': 'Kummer 1864；亏格 2 曲线 Jacobian 的商曲面，16 节点与 16 tropes 构成 Kummer 16₆ 位形。'},
    'barth': {'formula': '$4(\\varphi^2x^2-y^2)(\\varphi^2y^2-z^2)(\\varphi^2z^2-x^2)=(1+2\\varphi)(x^2+y^2+z^2-1)^2$',
              'props': ['六次曲面 · 射影空间 65 节点（次数 6 的世界纪录）', '仿射实节点 50 = 十二面体顶点 20 + 二十·十二面体 30'],
              'trivia': 'Barth 1994；正二十面体对称，黄金比 φ 内嵌，登上 1999 年 AMS Notices 封面。'},
    'cayley': {'formula': '$x^2+y^2+z^2+2xyz=1$',
               'props': ['三次曲面 · 4 节点（三次曲面的上限）', '有理曲面 · 4 条直线'],
               'trivia': 'Cayley 1849；射影平面模 Klein 四元群的商，四个节点恰在正四面体顶点方向。'},
    'octahedron': {'formula': '$|x|+|y|+|z|=1$',
                   'props': ['ℓ¹ 球 · 6 顶点/8 面/12 棱', '立方体的对偶'],
                   'trivia': '正八面体即 d8 骰子；水平截面是正方形，竖直截面是菱形。'},
    'tetra': {'formula': '$\\max_i(n_i\\cdot r)=1$（4 半空间）',
              'props': ['4 面/4 顶点/6 棱 · 自对偶', '二面角 ≈70.53°'],
              'trivia': '四个顶点可取立方体的交错顶点——唯一顶点全在整格点上的正多面体。'},
    'cube': {'formula': '$\\max(|x|,|y|,|z|)=1$',
             'props': ['ℓ∞ 单位球 · 6 面/8 顶点/12 棱', '二面角 90°'],
             'trivia': '唯一能单独堆满空间的正多面体；晶体学里立方晶系的胞形。'},
    'dodeca': {'formula': '$\\max_i(n_i\\cdot r)=1$（12 半空间）',
               'props': ['12 个五边形面/20 顶点/30 棱', '半空间系数恰为 1/φ² 与 1/φ'],
               'trivia': '毕达哥拉斯学派视正十二面体为宇宙的象征；面法向指向正二十面体的 12 个顶点（对偶）。'},
    'icosa': {'formula': '$\\max_i(n_i\\cdot r)=1$（20 半空间）',
              'props': ['20 个三角形面/12 顶点/30 棱', '与正十二面体互对偶'],
              'trivia': '腺病毒、脊髓灰质炎病毒等衣壳取正二十面体——相同亚基包裹球壳的最省方案。'},
    'horn_torus': {'formula': '$(x^2+y^2+z^2+R^2-r^2)^2=4R^2(x^2+y^2),\\ R=r$',
                   'props': ['R=r 临界环面 · 内孔收缩为一点', '原点处锥点奇点'],
                   'trivia': '环面退化三部曲之中章：R>r 环面 → R=r 角环面 → R<r 纺锤环面。'},
    'spindle_torus': {'formula': '$(x^2+y^2+z^2+R^2-r^2)^2=4R^2(x^2+y^2),\\ R<r$',
                      'props': ['自交环面 · 内侧上下自穿', '截面呈双纽线形'],
                      'trivia': '“柠檬形”环面；机械上对应自交的回转面，车床上车不出来。'},
    'neovovius': {'formula': '$\\cos x+\\cos y+\\cos z+4\\cos x\\cos y\\cos z=0$',
                  'props': ['三重周期曲面', 'Schwarz P 的近亲，腔体互穿'],
                  'trivia': 'Newell 1970 年代计算机图形学经典测试曲面。'},
    'schwarz_d': {'formula': '$\\cos x\\cos y\\cos z+\\cos x+\\cos y+\\cos z=0$',
                  'props': ['三重周期极小曲面 (TPMS)', 'D = Diamond，金刚石结构'],
                  'trivia': 'Schwarz 1865 发现；晶体学里对应金刚石型骨架，材料学仿生热门。'},
    'boy': {'formula': 'Apéry 参数式（见表达式）',
            'props': ['射影平面到 R³ 的浸入', '1 个三重点 · 不可定向'],
            'trivia': 'Werner Boy 1901（Hilbert 悬赏的回应）；射影平面无法嵌入 R³，只能浸入。'},
    'kuen': {'formula': '参数式（见表达式）',
             'props': ['常数负曲率 K=−1', '波浪状伪球面'],
             'trivia': '19 世纪意大利学派（Beltrami 一脉）的负曲率模型，双曲几何的实物直觉。'},
    'seashell': {'formula': '$r(u)=a\\,e^{bu}$ 生长螺旋',
                 'props': ['中心线与管径同步增长', '对数螺线绕轴扫掠'],
                 'trivia': 'Raup 1966 贝壳形态学参数（展开率/距离/形状）的极简版——蜗牛壳数学。'},
    'crosscap': {'formula': '$(x,y,z)=(uv,u^2,v^2)$',
                 'props': ['射影平面的浸入', 'Whitney 伞的近亲'],
                 'trivia': '“交叉帽”：把 Möbius 带的边界粘上圆盘所得闭曲面的自交实现。'},
    'helicoid': {'formula': '$(v\\cos u,\\, v\\sin u,\\, u/6)$',
                 'props': ['极小曲面 · 直纹面', '与悬链面共轭'],
                 'trivia': '除平面外唯一的直纹极小曲面（Catalan 1842）；旋转楼梯的数学理想化。'},
    'semicircle': {'formula': '$y=\\sqrt{1-x^2}$', 'props': ['单位圆上半支', '显式函数 y=f(x) 示例'],
                   'trivia': '同一个圆：隐式、显式、参数三种写法的教学对比起点。'},
    'heart': {'formula': '$(x^2+y^2-1)^3=x^2y^3$',
              'props': ['六次隐式曲线', '原点为尖点型奇点'],
              'trivia': '“心形线”的网红公式（与极坐标心摆线不同族）。'},
    'cubic': {'formula': '$y=x^3-3x$', 'props': ['极值点 x=±1', '拐点 x=0，中心对称'],
              'trivia': '高中导数课的标配原型：单调性/极值/切线一网打尽。'},
    'epicycloid5': {'formula': '外摆线 $(R{=}5, r{=}1)$',
                    'props': ['5 个尖点', '周长与弧段可解析'],
                    'trivia': '小圆在大圆外无滑动滚动，圆上定点的轨迹。'},
    'parabola': {'formula': '$y^2=4x$', 'props': ['焦点 (1,0) · 准线 x=−1', '离心率 e=1'],
                 'trivia': '到焦点与准线等距的轨迹；抛体运动的轨道（无阻力时）。'},
    'sine_curve': {'formula': '$y=\\sin x$', 'props': ['周期 2π · 幅值 1', '弧长为椭圆积分（不可初等表示）'],
                   'trivia': '一切振动的基元；傅里叶分析的起点。'},
    'catenary': {'formula': '$y=\\cosh x$', 'props': ['均匀链条自由悬挂的形状', '绕 x 轴旋转 → 悬链面（极小曲面）'],
                 'trivia': '伽利略误以为是抛物线，惠更斯 1691 纠正。与抛物线的区别：均匀“链长”而非均匀“横向”。'},
    'tractrix': {'formula': '$x=t-\\tanh t,\\ y=1/\\cosh t$',
                 'props': ['切线段长恒为 1', '绕渐近线旋转 → 伪球面（K=−1）'],
                 'trivia': '“拖拽曲线”：重物被绳拖行时的轨迹；双曲几何的旋转模型。'},
    'superellipse2': {'formula': '$|x|^n+|y|^n=1,\\ n=4$',
                      'props': ['n=2 圆 · n→∞ 正方形', 'Lamé 曲线'],
                      'trivia': '瑞典首都斯德哥尔摩的 Sergel 广场就是超椭圆形的。'},
    'rose4': {'formula': '$r=\\cos 4\\theta$', 'props': ['8 瓣（n 偶 → 2n 瓣）', '每瓣面积 π/16'],
              'trivia': '玫瑰线家族：n 奇 → n 瓣，n 偶 → 2n 瓣（本例 n=4）。'},
    'deltoid': {'formula': '$x=2\\cos t+\\cos 2t,\\ y=2\\sin t-\\sin 2t$',
                'props': ['三尖内摆线（R=3r）', '周长 16r · 面积 2πr²'],
                'trivia': '圆内滚圆的定点轨迹；平行光射入圆镜的焦散线正是它。'},
    'nephroid': {'formula': '$x=3\\cos t-\\cos 3t,\\ y=3\\sin t-\\sin 3t$',
                 'props': ['二尖外摆线（R=2r）', '肾形，有 2 个尖点'],
                 'trivia': '咖啡杯里灯光照出的焦散亮纹就是肾形线。'},
    'archimedean': {'formula': '$r=\\theta$（此处缩放 /6）', 'props': ['相邻圈等距', '面积可初等计算'],
                    'trivia': '阿基米德用它三等分角（借助有刻度的尺）。'},
    'log_spiral': {'formula': '$r=e^{\\theta/6}$', 'props': ['等角螺线 · 自相似', '弧长有限/无限看端点'],
                   'trivia': '鹦鹉螺、台风眼、向日葵种子排列的几何模板。'},
    'fermat': {'formula': '$r^2=\\theta$', 'props': ['双值 ±√θ，两支对称', '向外间距递减'],
               'trivia': '向日葵种子分布的近似模型（与黄金角配合）。'},
    'hyperbolic_spiral': {'formula': '$r=1/\\theta$', 'props': ['θ→0 时无限远，渐近线 y=1', '阿基米德螺线的倒数'],
                     'trivia': '从原点出发的“反螺线”，绕无穷多圈才到达渐近高度。'},
    'cassini': {'formula': '$(x^2+y^2)^2=2(x^2-y^2)-0.6$',
                'props': ['到两焦点距离之积恒定', '此处 b<a：两个分离卵形'],
                'trivia': '卡西尼 1680 年为行星轨道提出；b=a 时退化为双纽线 ∞。'},
    'limacon': {'formula': '$r=1+2\\cos\\theta$', 'props': ['内环型（b>a）', 'θ=2π/3, 4π/3 过极点'],
                'trivia': '帕斯卡之父 Étienne 研究的心脏线近亲；b=a 即心脏线，b=2a 即三叉极坐标曲线。'},
    'torus_knot_34': {'formula': '$T(3,4)$ 环面纽结', 'props': ['绕轴 3 圈 · 绕管 4 圈', '交叉数 8'],
                      'trivia': '环面纽结 T(p,q)：p,q 互素时是真纽结。'},
    'torus_knot_25': {'formula': '$T(2,5)$ 环面纽结', 'props': ['交叉数 5，即 5₁ 纽结', '双桥纽结'],
                      'trivia': '纽结表里的明星：五角星形的纽结化。'},
    'lissajous3d': {'formula': '$(\\sin 3t,\\ \\sin 4t,\\ \\cos 5t)$',
                    'props': ['频率比 3:4:5', '闭合（频率比有理）'],
                    'trivia': '示波器双通道合成的李萨如图形的三维版。'},
    'torus_knot_35': {'formula': '$T(3,5)$ 环面纽结', 'props': ['交叉数 10', '(3,5) 与 (5,3) 同型'],
                      'trivia': '纽结群、Brieskorn 奇点 x³+y⁵+z²=0 的链接正是 T(3,5)。'},
    'sph_spiral': {'formula': '$(\\cos t\\cos 4t,\\ \\cos t\\sin 4t,\\ \\sin t)$',
                   'props': ['纬向等速爬升', '每圈等高间距'],
                   'trivia': '球面上的“弹簧线”，卫星扫描轨道的玩具模型。'},
    'cone_helix': {'formula': '$(0.18t\\cos t,\\ 0.18t\\sin t,\\ 0.25t)$',
                   'props': ['半径与高同步线性增长', '非定螺距的螺线'],
                   'trivia': '弹簧被拉伸成喇叭形时的样子。'},
    'saddle': {'formula': '$z=x^2-y^2$', 'props': ['双曲抛物面 · 马鞍点', '双重直纹面'],
               'trivia': '品客藠片的形状；两个方向的直线族都能铺在它上面。'},
    'paraboloid': {'formula': '$z=(x^2+y^2)/4$', 'props': ['旋转抛物面', '焦点在轴上 (0,0,1)'],
                   'trivia': '卫星天线/太阳灶的形状：平行光反射后汇聚到焦点。'},
    'hemisphere': {'formula': '$z=\\sqrt{16-x^2-y^2}$', 'props': ['半径 4 上半球', '显式写法示例'],
                   'trivia': 'LaTeX \\sqrt{} 输入的示例条目。'},
    'cone': {'formula': '$z=\\sqrt{x^2+y^2}$', 'props': ['45° 圆锥', '顶点为锥点奇点'],
             'trivia': '圆锥曲线之“圆锥”本体：不同角度的截面给出圆/椭圆/抛物/双曲线。'},
    'gaussian': {'formula': '$z=3e^{-(x^2+y^2)/2}$', 'props': ['二维正态密度的形状', '旋转对称'],
                 'trivia': '“钟形曲面”：概率论的山峰，中心极限定理的雕塑。'},
    'wave': {'formula': '$z=\\sin x\\cos y$', 'props': ['棋盘状波纹', '满足拉普拉斯方程（调和）'],
             'trivia': '驻波的瞬时快照；二维波动方程的基本模式。'},
    'ripple': {'formula': '$z=\\frac{\\sin r}{r}$', 'props': ['sinc 径向波', '原点取值 1（连续延拓）'],
               'trivia': '石子落水的理想化波纹；光学圆孔衍射（Airy 斑）的近亲。'},
    'sphere': {'formula': '$x^2+y^2+z^2=4$', 'props': ['半径 2 · 高斯曲率 1/4', '隐式写法示例'],
               'trivia': '给定表面积体积最大的曲面——肥皂泡的数学。'},
    'ellipsoid': {'formula': '$\\frac{x^2}{9}+\\frac{y^2}{4}+z^2=1$',
                  'props': ['半轴 3/2/1', '地球形状的零阶近似'],
                  'trivia': 'LaTeX \\frac 输入的示例；大地水准面是它的扰动。'},
    'hyperboloid': {'formula': '$x^2+y^2-z^2=1$', 'props': ['单叶双曲面 · 直纹面', '腰圆半径 1'],
                    'trivia': '冷却塔的形状：用直钢筋弯出曲面（广州塔同理）。'},
    'hyperboloid2': {'formula': '$x^2/a^2+y^2/b^2-z^2=-1$', 'props': ['双叶双曲面 · 两叶不连通', '参数 a=1,b=1.5'],
                     'trivia': '与单叶同族：z 从 ±1 开始开口，永远不碰 z=0 平面。'},
    'barth_decic': {'formula': '$8(x^2-\\varphi^4y^2)(y^2-\\varphi^4z^2)(z^2-\\varphi^4x^2)\\Pi_4+(3+5\\varphi)(s-1)^2(s+\\varphi-2)^2=0$',
                    'props': ['十次曲面 · 射影 345 节点（次数 10 的世界纪录）', '仿射 300 实节点：半径 1/φ, √(5−2√5), √((5+√5)/2), 1 四层同心多面体'],
                    'trivia': 'Barth 1994；节点落在两个 60 面体（截角二十面体变体）+ 两个 90 面体的顶点上，正二十面体对称。'},
    'clebsch': {'formula': '$81\\sum x^3-189\\sum_{sym}x^2y+54xyz+126\\sum xy-9\\sum x^2-9\\sum x+1=0$',
                'props': ['三次曲面 · 27 条直线全为实', '10 个 Eckardt 点（三切面三线共点）'],
                'trivia': '代数几何的明星：唯一 27 线全实的三次曲面（Clebsch 1861），Nordstrand 画廊藏品。'},
    'hunt': {'formula': '$4A^3+27B^2=0$', 'props': ['有界闭曲面（A≤0）', '沿 A=B=0 交线奇异（非孤立节点）'],
             'trivia': 'Nordstrand 画廊藏品；4A³+27B²=0 正是三次方程重根的判别式形状，奇异集为球面与二次曲面的一条交线。'},
    'dupin': {'formula': '环面反演的四次式', 'props': ['四次曲面 · 两族曲率线都是圆', '环面/圆锥曲线的反演像'],
              'trivia': 'Dupin 1822；机械/船体放样时代的宠儿，此处取“双月牙”参数。'},
    'bohemian': {'formula': '$x=a\\cos u,\\ y=b\\cos v+a\\sin u,\\ z=c\\sin v$',
                 'props': ['圆沿垂直圆扫掠的包络', 'a=0.5, b=1.5, c=1'],
                 'trivia': '“波希米亚穹顶”：把圆形窗口沿垂直方向的圆轨道扫一圈得到的壳体。'},
    'cylinder': {'formula': '$(\\cos u,\\ \\sin u,\\ v)$',
                 'props': ['直纹可展曲面 · 高斯曲率 K≡0', '可等距摊平为平面'],
                 'trivia': '与圆锥面、切线面并列空间仅有的三类可展曲面；易拉罐的侧壁就是它（不含上下盖）。'},
    'cyl_ellipse': {'formula': '$(2\\cos u,\\ \\sin u,\\ v)$',
                    'props': ['准线为椭圆 a=2, b=1', '同属可展曲面（K≡0）'],
                    'trivia': '圆管斜切一刀的切口是椭圆——工程制图里椭圆出现的原理。'},
    'prism3': {'formula': '$\\max_i(n_i\\cdot r)=\\frac{1}{2}$',
               'props': ['正三角形截面 · 外接圆半径 1', '三个半平面取 max 的零集'],
               'trivia': '棱柱面 = 多边形沿直线平移；max 形式即凸多面体半空间交的边界。'},
    'prism4': {'formula': '$\\max(|x|,|y|)=1$',
               'props': ['正方形截面 · ℓ∞ 单位球', '与菱形 |x|+|y|=1 差 45° 旋转'],
               'trivia': '切比雪夫距离的“单位球”拉伸到三维的样子。'},
    'prism6': {'formula': '$\\max_i(n_i\\cdot r)=\\frac{\\sqrt3}{2}$',
               'props': ['正六边形截面 · 内切圆半径 √3/2', '蜂巢结构单元'],
               'trivia': '六角铅笔的笔杆、蜂巢的单格——等面积分割中周长最省的形状。'},
    'psphere': {'formula': '$(2\\sin u\\cos v,\\ 2\\sin u\\sin v,\\ 2\\cos u)$',
                'props': ['参数式球面 · 无缝闭合', 'u∈[0,π], v∈[0,2π]'],
                'trivia': '与隐式球面同形：参数式比隐式重建更光滑（演示两种输入方式）。'},
    'ptorus': {'formula': '$((2+\\cos v)\\cos u,\\ (2+\\cos v)\\sin u,\\ \\sin v)$',
               'props': ['R=2, r=1 完整环面', '亏格 1'],
               'trivia': '甜甜圈的数学本体；拓扑学“咖啡杯=甜甜圈”的主角。'},
    'disk': {'formula': '$x^2+y^2<r^2$，参数 r', 'props': ['参数化半径', '开区域'],
             'trivia': '把分号后的 r=2 改成 r=3 试试——参数实时生效。'},
    'ellipse_region': {'formula': '$\\frac{x^2}{4}+\\frac{y^2}{9}\\le 1$',
                       'props': ['半轴 2/3 的闭椭圆域', 'LaTeX \\le 示例'],
                       'trivia': '高中解析几何“椭圆内部”的可视化教具。'},
    'annulus': {'formula': '$1<x^2+y^2<4$', 'props': ['不等式组取交集', '圆环域'],
                'trivia': '逗号联立：两个不等式的公共部分。'},
    'parabolic_region': {'formula': '$x^2<y<4-x^2$', 'props': ['两抛物线之间的有界域', '面积可积出'],
                         'trivia': '高考定积分面积题的标配图形。'},
    'lp_region': {'formula': '四个一次不等式联立', 'props': ['可行域为四边形', '目标函数在顶点取最值'],
                  'trivia': '高中线性规划：阴影区即可行域，最值在角点。'},
    'ball': {'formula': '$x^2+y^2+z^2<4$', 'props': ['3D 不等式示例', '半透明边界 + z=0 截面'],
             'trivia': '三维“区域”渲染的演示条目。'},
}


# ---------------- 几何采样: 表达式 → 三维折线集 ----------------

def _runs(pts, jump_frac=0.16):
    """按跳变断开折线（规避 tan/奇点等不连续）"""
    if not pts:
        return []
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; zs = [p[2] for p in pts]
    span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 1e-9)
    jump = span * jump_frac
    out, cur = [], [pts[0]]
    for p in pts[1:]:
        q = cur[-1]
        if ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2) ** 0.5 > jump:
            if len(cur) > 1:
                out.append(cur)
            cur = [p]
        else:
            cur.append(p)
    if len(cur) > 1:
        out.append(cur)
    return out


def _finite_pts(gen):
    return [p for p in gen
            if all(math.isfinite(c) for c in p)]


def entry_polylines(spec):
    """返回折线列表 [[(x,y,z)...], ...]"""
    kind = spec['kind']
    if kind == 'parametric':
        c = spec['comps']
        lo, hi = spec['t_range']
        N = 420
        pts = _finite_pts((c['x'](t) if 'x' in c else 0.0,
                           c['y'](t) if 'y' in c else 0.0,
                           c['z'](t) if 'z' in c else 0.0)
                          for t in (lo + (hi - lo) * i / N for i in range(N + 1)))
        return _runs(pts)
    if kind == 'param_surface':
        c = spec['comps']
        (u0, u1), (v0, v1) = spec['u_range'], spec['v_range']
        fx = c.get('x'); fy = c.get('y'); fz = c.get('z')

        def P(u, v):
            return (fx(u, v) if fx else 0.0, fy(u, v) if fy else 0.0,
                    fz(u, v) if fz else 0.0)
        lines = []
        NU, NV, NS = 13, 13, 26
        for i in range(NU):
            u = u0 + (u1 - u0) * i / (NU - 1)
            lines.append(_finite_pts(P(u, v0 + (v1 - v0) * j / NS)
                                     for j in range(NS + 1)))
        for j in range(NV):
            v = v0 + (v1 - v0) * j / (NV - 1)
            lines.append(_finite_pts(P(u0 + (u1 - u0) * i / NS, v)
                                     for i in range(NS + 1)))
        return [ln for ln in lines if len(ln) > 1]
    if kind == 'surface':
        f = spec['f']
        (x0, x1), (y0, y1) = spec['x_range'], spec['y_range']
        lines, NS = [], 26
        for i in range(15):
            x = x0 + (x1 - x0) * i / 14
            lines.append(_finite_pts((x, y0 + (y1 - y0) * j / NS,
                                      f(x, y0 + (y1 - y0) * j / NS))
                                     for j in range(NS + 1)))
        for j in range(15):
            y = y0 + (y1 - y0) * j / 14
            lines.append(_finite_pts((x0 + (x1 - x0) * i / NS, y,
                                      f(x0 + (x1 - x0) * i / NS, y))
                                     for i in range(NS + 1)))
        return [ln for ln in lines if len(ln) > 1]
    if kind == 'explicit2d':
        f = spec['f']
        if spec.get('var') == 'y':
            lo, hi = spec['y_range']
            pts = _finite_pts((f(v), v, 0.0) for v in
                              (lo + (hi - lo) * i / 320 for i in range(321)))
        else:
            lo, hi = spec['x_range']
            pts = _finite_pts((v, f(v), 0.0) for v in
                              (lo + (hi - lo) * i / 320 for i in range(321)))
        return _runs(pts)
    if kind == 'implicit2d':
        segs = marching_squares(spec['F'], spec['x_range'], spec['y_range'], n=110)
        return [[tuple(a), tuple(b)] for a, b in segs]
    if kind == 'implicit3d':
        tris, _ = marching_cubes_adaptive(spec['F'], spec['x_range'],
                                          spec['y_range'], spec['z_range'],
                                          n0=12, s=2)
        lines = []
        for i, (tri, _col) in enumerate(tris):
            if i % 2:                      # 抽稀一半, 缩略图够用
                continue
            a, b, c = tri
            lines.append([tuple(a), tuple(b), tuple(c), tuple(a)])
        return lines
    if kind == 'inequality2d':
        lines = []
        for F, _pos in spec['conds']:
            segs = marching_squares(F, spec['x_range'], spec['y_range'], n=110)
            lines.extend([[tuple(a), tuple(b)] for a, b in segs])
        return lines
    if kind == 'inequality3d':
        lines = []
        for F, _pos in spec['conds']:
            tris, _ = marching_cubes_adaptive(F, spec['x_range'], spec['y_range'],
                                              spec['z_range'], n0=12, s=2)
            for i, (tri, _col) in enumerate(tris):
                if i % 2:
                    continue
                a, b, c = tri
                lines.append([tuple(a), tuple(b), tuple(c), tuple(a)])
        return lines
    return []


# ---------------- 渲染 ----------------

def _render_faces_thumb(entry, path, size=SIZE):
    """平直多面体缩略图: 精确多边形面 + Lambert 着色 + 画家算法（无线框/无毛刺）"""
    img = Image.new('RGB', (size, size), BG)
    d = ImageDraw.Draw(img)
    color = CAT_COLORS.get(entry.get('category', ''), DEFAULT_COLOR)
    rgb = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
    pts_all = [p for f in entry['faces'] for p in f]
    xs = [p[0] for p in pts_all]; ys = [p[1] for p in pts_all]
    zs = [p[2] for p in pts_all]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    cz = (min(zs) + max(zs)) / 2
    span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 1e-9)
    k = 2.4 / span
    cam = engine3d.Camera()
    cam.zoom = size * 0.38
    L = (-0.45, -0.55, 0.75)
    ln = math.sqrt(sum(c * c for c in L))
    L = tuple(c / ln for c in L)
    items = []
    for poly in entry['faces']:
        nx = ny = nz = 0.0                          # Newell 法向
        for i in range(len(poly)):
            a, b = poly[i], poly[(i + 1) % len(poly)]
            nx += (a[1] - b[1]) * (a[2] + b[2])
            ny += (a[2] - b[2]) * (a[0] + b[0])
            nz += (a[0] - b[0]) * (a[1] + b[1])
        nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        bri = 0.32 + 0.68 * abs(nx * L[0] + ny * L[1] + nz * L[2]) / nl
        shade = tuple(min(255, int(c * bri)) for c in rgb)
        proj = [cam.project((p[0] - cx) * k, (p[1] - cy) * k,
                            (p[2] - cz) * k, size, size) for p in poly]
        depth = sum(q[2] for q in proj) / len(proj)
        items.append((depth, [(q[0], q[1]) for q in proj], shade))
    items.sort(key=lambda it: -it[0])               # 远→近
    for _, pts2, shade in items:
        d.polygon(pts2, fill=shade, outline=shade)
    img.save(path)
    return True


def render_thumb(entry, path, size=SIZE):
    if entry.get('faces'):
        return _render_faces_thumb(entry, path, size)
    spec = mathparse.parse_input(entry['expr'])
    lines = entry_polylines(spec)
    img = Image.new('RGB', (size, size), BG)
    d = ImageDraw.Draw(img)
    color = CAT_COLORS.get(entry.get('category', ''), DEFAULT_COLOR)
    if spec['kind'] == 'inequality2d':          # 不等式区域: 先填可行域再描边界
        rgb = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
        bg_rgb = Image.new('RGB', (1, 1), BG).getpixel((0, 0))
        (x0, x1), (y0, y1) = spec['x_range'], spec['y_range']
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        span = max(x1 - x0, y1 - y0, 1e-9)
        k = size * 0.82 / span
        pale = tuple(int(rgb[i] * 0.35 + bg_rgb[i] * 0.65) for i in range(3))
        mask = Image.new('1', (size, size), 0)
        md = ImageDraw.Draw(mask)
        N, cw = 150, size / 150 + 1
        conds = spec['conds']
        for i in range(N):
            x = x0 + (x1 - x0) * (i + 0.5) / N
            for j in range(N):
                y = y0 + (y1 - y0) * (j + 0.5) / N
                if all((F(x, y) > 0) == pos for F, pos in conds):
                    px = (x - cx) * k + size / 2
                    py = size / 2 - (y - cy) * k
                    md.rectangle([px, py, px + cw, py + cw], fill=1)
        img.paste(Image.new('RGB', img.size, pale), (0, 0), mask.convert('L'))
        d = ImageDraw.Draw(img)
        for ln in lines:
            d.line([((p[0] - cx) * k + size / 2, size / 2 - (p[1] - cy) * k)
                    for p in ln], fill=color, width=2)
        img.save(path)
        return True
    pts_all = [p for ln in lines for p in ln]
    if not pts_all:
        img.save(path)
        return False
    zs = [p[2] for p in pts_all]
    flat = (max(zs) - min(zs)) < 1e-9          # 平面图形 → 俯视图
    if flat:
        xs = [p[0] for p in pts_all]; ys = [p[1] for p in pts_all]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        span = max(max(xs) - min(xs), max(ys) - min(ys), 1e-9)
        k = size * 0.82 / span
        for ln in lines:
            d.line([((p[0] - cx) * k + size / 2, size / 2 - (p[1] - cy) * k)
                    for p in ln], fill=color, width=2)
    else:
        xs = [p[0] for p in pts_all]; ys = [p[1] for p in pts_all]
        cx = (min(xs) + max(xs)) / 2
        cy = (min(ys) + max(ys)) / 2
        cz = (min(zs) + max(zs)) / 2
        span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 1e-9)
        k = 2.4 / span
        cam = engine3d.Camera()                # 与主引擎一致视角
        cam.zoom = size * 0.38
        for ln in lines:
            proj = [cam.project((p[0] - cx) * k, (p[1] - cy) * k,
                                (p[2] - cz) * k, size, size)[:2] for p in ln]
            d.line(proj, fill=color, width=1 if len(pts_all) > 4000 else 2)
    img.save(path)
    return True


def ensure_thumbs(entries, status_cb=None):
    """补齐缺失缩略图（磁盘缓存）。返回 (成功数, 失败 key 列表)"""
    os.makedirs(THUMB_DIR, exist_ok=True)
    n = len(entries)
    ok, failed = 0, []
    for i, e in enumerate(entries):
        path = thumb_path(e['key'])
        if os.path.exists(path) and os.path.getsize(path) > 0:
            ok += 1
            continue
        if status_cb:
            status_cb(f'生成缩略图 {i + 1}/{n}: {e["name"]}')
        try:
            render_thumb(e, path)
            ok += 1
        except Exception as ex:
            failed.append(e['key'])
            print(f'[gallery] 缩略图失败 {e["key"]}: {ex}')
    return ok, failed


def thumb_path(key):
    return os.path.join(THUMB_DIR, f'{key}.png')


def load_favs():
    try:
        with open(FAV_FILE, encoding='utf-8') as f:
            v = json.load(f)
            return set(v) if isinstance(v, list) else set()
    except (OSError, ValueError):
        return set()


def save_favs(favs):
    try:
        with open(FAV_FILE, 'w', encoding='utf-8') as f:
            json.dump(sorted(favs), f, ensure_ascii=False)
    except OSError:
        pass


# ---------------- Tk 画廊窗口 ----------------

class GalleryWindow(tk.Toplevel):
    N_COLS = 5

    def __init__(self, master, on_pick):
        super().__init__(master)
        self.on_pick = on_pick
        self.title('曲线画廊 · 搜索 + 缩略图')
        self.geometry('1120x760')
        self.configure(bg=BG)
        self._photos = []
        self._grouped = curve_library.load_all()[0]
        self._entries = [e for _, v in self._grouped for e in v]
        self._by_key = {e['key']: e for e in self._entries}
        self.favs = load_favs()

        top = tk.Frame(self, bg=BG)
        top.pack(fill='x', padx=10, pady=(10, 4))
        tk.Label(top, text='搜索', bg=BG, fg='#cdd6f4').pack(side='left')
        self.q = tk.Entry(top, bg='#181825', fg='#cdd6f4',
                          insertbackground='#cdd6f4', relief='flat',
                          font=('Consolas', engine3d.font_size(11)))
        self.q.pack(side='left', fill='x', expand=True, padx=6, ipady=4)
        self.q.bind('<KeyRelease>', lambda e: self.rebuild())
        cats = [FAV_CAT, '全部'] + [c for c, _ in self._grouped]
        self.cat = ttk.Combobox(top, values=cats, state='readonly', width=14)
        self.cat.set('全部')
        self.cat.pack(side='left', padx=6)
        self.cat.bind('<<ComboboxSelected>>', lambda e: self.rebuild())
        tk.Button(top, text='↻ 重载', bg='#45475a', fg='#cdd6f4', relief='flat',
                  command=self.reload).pack(side='left', padx=6)
        self.count = tk.Label(top, text='', bg=BG, fg='#9aa0b4')
        self.count.pack(side='left', padx=6)
        self.fav_count = tk.Label(top, text='', bg=BG, fg='#f9e2af')
        self.fav_count.pack(side='left', padx=6)

        self.status = tk.Label(self, text='', bg=BG, fg='#a6e3a1', anchor='w')
        self.status.pack(fill='x', padx=12)

        body = tk.Frame(self, bg=BG)
        body.pack(fill='both', expand=True, padx=6, pady=6)
        left = tk.Frame(body, bg=BG)
        left.pack(side='left', fill='both', expand=True)
        self.canvas = tk.Canvas(left, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(left, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')
        self.inner = tk.Frame(self.canvas, bg=BG)
        self.canvas.create_window((0, 0), window=self.inner, anchor='nw')
        self.inner.bind('<Configure>',
                        lambda e: self.canvas.configure(
                            scrollregion=self.canvas.bbox('all')))
        # 右侧资料卡面板
        right = tk.Frame(body, bg=BG, width=320)
        right.pack(side='right', fill='y', padx=(8, 0))
        right.pack_propagate(False)
        tk.Label(right, text='📜 资料卡', bg=BG, fg='#cdd6f4',
                 font=('DejaVu Sans', engine3d.font_size(11), 'bold')).pack(anchor='w')
        self.card = tk.Text(right, bg='#181825', fg='#cdd6f4', relief='flat',
                            wrap='word', padx=8, pady=8,
                            font=('DejaVu Sans', engine3d.font_size(10)))
        self.card.pack(fill='both', expand=True)
        self.card.tag_config('title', foreground='#89b4fa',
                             font=('DejaVu Sans', engine3d.font_size(11), 'bold'))
        self.card.tag_config('key', foreground='#f9e2af')
        self.card.tag_config('dim', foreground='#9aa0b4')
        self.card.config(state='disabled')
        self._show_card_hint()

        ensure_thumbs(self._entries,
                      status_cb=lambda s: (self.status.config(text=s),
                                           self.update_idletasks()))
        self.status.config(text='')
        self.rebuild()

    def reload(self):
        self._grouped = curve_library.load_all()[0]
        self._entries = [e for _, v in self._grouped for e in v]
        self._by_key = {e['key']: e for e in self._entries}
        self.favs = load_favs()
        cats = [FAV_CAT, '全部'] + [c for c, _ in self._grouped]
        self.cat.configure(values=cats)
        if self.cat.get() not in cats:
            self.cat.set('全部')
        ensure_thumbs(self._entries,
                      status_cb=lambda s: (self.status.config(text=s),
                                           self.update_idletasks()))
        self.status.config(text='')
        self.rebuild()

    def _match(self, e, kw):
        if not kw:
            return True
        hay = f"{e['name']} {e['key']} {e.get('category', '')} {e.get('desc', '')}".lower()
        return all(w in hay for w in kw.lower().split())

    def rebuild(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self._photos.clear()
        kw = self.q.get().strip()
        cat = self.cat.get()
        shown = [e for e in self._entries
                 if (cat == '全部' or (cat == FAV_CAT and e['key'] in self.favs)
                     or e.get('category') == cat)
                 and self._match(e, kw)]
        self.count.config(text=f'{len(shown)} / {len(self._entries)} 条')
        self.fav_count.config(text=f'⭐ {len(self.favs)} 收藏')
        for i, e in enumerate(shown):
            r, c = divmod(i, self.N_COLS)
            self._tile(e, r, c)
        if not shown:
            tk.Label(self.inner, text='没有匹配的曲线/曲面',
                     bg=BG, fg='#9aa0b4',
                     font=('DejaVu Sans', engine3d.font_size(12))).grid(
                row=0, column=0, columnspan=self.N_COLS, pady=40)

    def _tile(self, e, r, c):
        try:
            img = Image.open(thumb_path(e['key']))
        except Exception:
            img = Image.new('RGB', (SIZE, SIZE), BG)
        self._photos.append(ImageTk.PhotoImage(img))
        name = e['name']
        if len(name) > 16:
            name = name[:15] + '…'
        star = '★ ' if e['key'] in self.favs else ''
        b = tk.Button(self.inner, image=self._photos[-1], text=star + name,
                      compound='top', bg='#181825', fg='#cdd6f4',
                      activebackground='#313244', activeforeground='#f5f5f5',
                      relief='flat', bd=0, padx=4, pady=4,
                      font=('DejaVu Sans', engine3d.font_size(9)),
                      command=lambda item=e: self._pick(item))
        b.grid(row=r, column=c, padx=6, pady=6, sticky='nsew')
        b.bind('<Button-3>', lambda ev, item=e: self._toggle_fav(item))
        tip = e.get('desc', '') + '（右键: 收藏/取消）'
        if tip:
            b.bind('<Enter>', lambda ev, t=tip: self.status.config(text=t, fg='#f9e2af'))
            b.bind('<Leave>', lambda ev: self.status.config(text=''))

    def _toggle_fav(self, e):
        k = e['key']
        if k in self.favs:
            self.favs.discard(k)
            self.status.config(text=f'☆ 已取消收藏: {e["name"]}', fg='#9aa0b4')
        else:
            self.favs.add(k)
            self.status.config(text=f'★ 已收藏: {e["name"]}', fg='#f9e2af')
        save_favs(self.favs)
        self.rebuild()

    def _pick(self, e):
        self._show_card(e)
        self.on_pick(e)
        self.status.config(text=f'✓ 已载入: {e["name"]}', fg='#a6e3a1')

    def _show_card_hint(self):
        self.card.config(state='normal')
        self.card.delete('1.0', 'end')
        self.card.insert('end', '点击任一缩略图查看资料卡:\n'
                                '· 表达式 / 分类 / 描述\n'
                                '· 著名曲线附 LaTeX 公式、性质与典故', 'dim')
        self.card.config(state='disabled')

    def _show_card(self, e):
        self.card.config(state='normal')
        self.card.delete('1.0', 'end')
        self.card.insert('end', e['name'] + '\n', 'title')
        star = '★ 已收藏\n' if e['key'] in self.favs else ''
        self.card.insert('end', star, 'key')
        self.card.insert('end', f"分类: {e.get('category', '未分类')}   ID: {e['key']}\n\n", 'dim')
        try:
            plain = mathparse.parse_input(e['expr'])['plain']
        except mathparse.ParseError:
            plain = e['expr']
        self.card.insert('end', '表达式\n', 'key')
        self.card.insert('end', plain + '\n\n')
        c = CARDS.get(e['key'])
        if c:
            self.card.insert('end', '公式\n', 'key')
            self.card.insert('end', c['formula'] + '\n\n')
            if c.get('props'):
                self.card.insert('end', '性质\n', 'key')
                for p in c['props']:
                    self.card.insert('end', '  • ' + p + '\n')
                self.card.insert('end', '\n')
            if c.get('trivia'):
                self.card.insert('end', '典故\n', 'key')
                self.card.insert('end', c['trivia'] + '\n\n')
        if e.get('desc'):
            self.card.insert('end', '说明\n', 'key')
            self.card.insert('end', e['desc'] + '\n')
        self.card.config(state='disabled')


if __name__ == '__main__':          # 独立测试: 生成全部缩略图
    grouped, warns = curve_library.load_all()
    entries = [e for _, v in grouped for e in v]
    ok, failed = ensure_thumbs(entries, status_cb=print)
    print(f'完成: {ok}/{len(entries)}, 失败: {failed or "无"}')
