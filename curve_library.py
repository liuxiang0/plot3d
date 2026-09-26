#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""curve_library.py — 经典代数曲线/曲面库（第三阶段）

两个来源:
  1. BUILTIN 内置库（本文件，65 条经典曲线/曲面）
  2. user_define.json 用户配置（首次运行自动创建模板, 菜单「↻ 重载配置」热加载）
条目字段: name(显示名) · category(菜单分类) · expr(表达式, 同输入框语法, 兼容 LaTeX) · desc(可选)
"""
import json
import os

import mathparse

DIR = os.path.dirname(os.path.abspath(__file__))
USER_FILE = os.path.join(DIR, 'user_define.json')

BUILTIN = {
    # ---------- 平面代数曲线 ----------
    'semicircle': {'name': '半圆 y=√(1−x²)', 'category': '平面代数曲线',
                   'expr': 'y=sqrt(1-x^2)',
                   'desc': '单位圆上半支，显式函数 y=f(x)'},
    'circle': {'name': '圆 x²+y²=4', 'category': '平面代数曲线',
               'expr': 'x^2+y^2=4', 'desc': '半径 2 的圆，隐式方程'},
    'ellipse': {'name': '椭圆 (LaTeX \\frac)', 'category': '平面代数曲线',
                'expr': r'\frac{x^2}{4}+\frac{y^2}{9}=1',
                'desc': 'a=2, b=3；LaTeX 输入示例'},
    'astroid': {'name': '星形线 Astroid', 'category': '平面代数曲线',
                'expr': 'x=cos(t)^3, y=sin(t)^3, z=0; t=0..2pi',
                'desc': 'x^(2/3)+y^(2/3)=1，参数式规避负数分数幂'},
    'cardioid': {'name': '心摆线 Cardioid', 'category': '平面代数曲线',
                 'expr': 'x=2*cos(t)-cos(2t), y=2*sin(t)-sin(2t), z=0; t=0..2pi',
                 'desc': '心脏线（等径外摆线）'},
    'heart': {'name': '心形线 (六次隐式)', 'category': '平面代数曲线',
              'expr': '(x^2+y^2-1)^3=x^2*y^3; x=-1.6..1.6, y=-1.5..1.8',
              'desc': '(x²+y²−1)³=x²y³'},
    'lemniscate': {'name': '双纽线 Bernoulli', 'category': '平面代数曲线',
                   'expr': '(x^2+y^2)^2=2*(x^2-y^2); x=-1.8..1.8, y=-0.9..0.9',
                   'desc': '伯努利双纽线 ∞ 形'},
    'folium': {'name': '笛卡尔叶形线', 'category': '平面代数曲线',
               'expr': 'x^3+y^3=3*x*y; x=-1.6..3.2, y=-1.6..3.2',
               'desc': 'x³+y³=3axy (a=1)，含渐近线 x+y+1=0'},
    'cycloid': {'name': '摆线 Cycloid', 'category': '平面代数曲线',
                'expr': 'x=t-sin(t), y=1-cos(t), z=0; t=0..4pi',
                'desc': '滚圆上定点轨迹，2 拱'},
    'cubic': {'name': '三次函数 y=x³−3x', 'category': '平面代数曲线',
              'expr': 'y=x^3-3*x', 'desc': '含两个极值的三次曲线'},
    'hyperbola': {'name': '双曲线 x²−y²=1', 'category': '平面代数曲线',
                  'expr': 'x^2-y^2=1; x=-3..3, y=-3..3',
                  'desc': '等轴双曲线，渐近线 y=±x'},
    'witch': {'name': '箕舌线 (阿涅西)', 'category': '平面代数曲线',
              'expr': 'y=8/(x^2+4); x=-8..8',
              'desc': 'Witch of Agnesi（a=1），即柯西分布密度曲线'},
    'cissoid': {'name': '蔓叶线 (戴克利斯)', 'category': '平面代数曲线',
                'expr': 'y^2*(2-x)=x^3; x=-0.2..1.99, y=-9..9',
                'desc': '古希腊三大曲线之一，x=2 处有垂直渐近线'},
    'elliptic_curve': {'name': '椭圆曲线 y²=x³−3x+1', 'category': '平面代数曲线',
                       'expr': 'y^2=x^3-3*x+1; x=-2.5..2.5, y=-3.5..3.5',
                       'desc': '亏格 1 光滑三次曲线，RSA 之外现代密码学(ECC)核心'},
    'rose': {'name': '玫瑰线 r=cos3θ (三叶)', 'category': '平面代数曲线',
             'expr': 'x=cos(3*t)*cos(t), y=cos(3*t)*sin(t), z=0; t=0..pi',
             'desc': '极坐标玫瑰线，k 为奇数时 k 片花瓣'},
    'epicycloid5': {'name': '外摆线 (五尖)', 'category': '平面代数曲线',
                    'expr': 'x=6*cos(t)-cos(6*t), y=6*sin(t)-sin(6*t), z=0; t=0..2pi',
                    'desc': 'R=5, r=1 的外摆线，5 个尖点'},
    'involute': {'name': '圆的渐伸线', 'category': '平面代数曲线',
                 'expr': 'x=cos(t)+t*sin(t), y=sin(t)-t*cos(t), z=0; t=0..3pi',
                 'desc': '齿轮齿廓曲线：绷紧的线从圆上展开时端点的轨迹'},
    'spirograph': {'name': '万花尺 (内旋轮线)', 'category': '平面代数曲线',
                   'expr': 'x=2*cos(t)+5*cos(2*t/3), y=2*sin(t)-5*sin(2*t/3), z=0; t=0..6pi',
                   'desc': 'Spirograph 玩具: R=5, r=3, d=5 的内旋轮线'},
    'butterfly': {'name': '蝴蝶曲线 (Tempest)', 'category': '平面代数曲线',
                  'expr': 'x=sin(t)*(exp(cos(t))-2*cos(4*t)-sin(t/12)^5), y=cos(t)*(exp(cos(t))-2*cos(4*t)-sin(t/12)^5), z=0; t=0..12pi',
                  'desc': '1989 年 Tempest 发现，指数项织出蝶翼'},
    'parabola': {'name': '抛物线 y²=4x', 'category': '平面代数曲线',
                 'expr': 'y^2=4*x; x=-0.5..4, y=-4.2..4.2',
                 'desc': '圆锥曲线：到焦点(1,0)与准线 x=−1 等距的点的轨迹'},
    'sine_curve': {'name': '正弦曲线 y=sin x', 'category': '平面代数曲线',
                   'expr': 'y=sin(x); x=-2pi..2pi',
                   'desc': '周期 2π 的基本波动，三角函数图像的母本'},
    'catenary': {'name': '悬链线 y=cosh x', 'category': '平面代数曲线',
                 'expr': 'y=cosh(x); x=-3..3',
                 'desc': '均匀链条在重力下的自然形状；绕水平轴旋转即悬链面（极小曲面）'},
    'tractrix': {'name': '曳物线 Tractrix', 'category': '平面代数曲线',
                 'expr': 'x=t-tanh(t), y=1/cosh(t), z=0; t=0..4',
                 'desc': '拖拽问题的轨迹：重物被绳子拖行时的路径；旋转成伪球面（常负曲率）'},
    'superellipse2': {'name': '超椭圆 Lamé (n=4)', 'category': '平面代数曲线',
                      'expr': 'abs(x)^4+abs(y)^4=1; x=-1.3..1.3, y=-1.3..1.3',
                      'desc': '|x|ⁿ+|y|ⁿ=1：介于椭圆与矩形之间，App 图标圆角矩形即此形'},
    'rose4': {'name': '玫瑰线 r=cos4θ (八瓣)', 'category': '平面代数曲线',
              'expr': 'x=cos(4*t)*cos(t), y=cos(4*t)*sin(t), z=0; t=0..2pi',
              'desc': 'k 为偶数时玫瑰线开出 2k 瓣，与三叶版对照'},
    'deltoid': {'name': '三尖瓣线 Deltoid', 'category': '平面代数曲线',
                'expr': 'x=2*cos(t)+cos(2*t), y=2*sin(t)-sin(2*t), z=0; t=0..2pi',
                'desc': '半径 1 的圆在半径 3 的圆内滚动，圆上定点的轨迹（三尖内摆线）'},
    'nephroid': {'name': '肾形线 Nephroid', 'category': '平面代数曲线',
                 'expr': 'x=3*cos(t)-cos(3*t), y=3*sin(t)-sin(3*t), z=0; t=0..2pi',
                 'desc': '二尖外摆线；平行光照进圆杯，杯壁上的光纹（焦散）就是它'},
    # ---------- 极坐标曲线 ----------
    'archimedean': {'name': '阿基米德螺线 r=θ', 'category': '极坐标曲线',
                    'expr': 'x=(t/6)*cos(t), y=(t/6)*sin(t), z=0; t=0..6pi',
                    'desc': '等距螺线：相邻圈间距恒定（唱片纹路、蚊香、卷轴纸端面）'},
    'log_spiral': {'name': '对数螺线 (等角)', 'category': '极坐标曲线',
                   'expr': 'x=exp(t/6)*cos(t), y=exp(t/6)*sin(t), z=0; t=-2pi..3pi',
                   'desc': 'r=e^(θ/6)：半径与切线夹角恒定；鹦鹉螺、旋臂星系，笛卡尔称之为"永恒螺线"'},
    'fermat': {'name': '费马螺线 r²=θ', 'category': '极坐标曲线',
               'expr': 'x=sqrt(t)*cos(t)/2, y=sqrt(t)*sin(t)/2, z=0; t=0..8pi',
               'desc': '向日葵种子排列的数学模型（Vogel 模型的骨架）'},
    'hyperbolic_spiral': {'name': '双曲螺线 r=1/θ', 'category': '极坐标曲线',
                          'expr': 'x=cos(t)/t, y=sin(t)/t, z=0; t=pi/6..6pi',
                          'desc': '越绕越紧地逼近原点，θ→0 时有一条直线渐近线'},
    'cassini': {'name': '卡西尼卵形线 (双纽)', 'category': '极坐标曲线',
                'expr': '(x^2+y^2)^2=2*(x^2-y^2)-0.6; x=-1.7..1.7, y=-1.2..1.2',
                'desc': '到两定点距离之积为常数的轨迹；b=a 时退化为伯努利双纽线'},
    'limacon': {'name': '帕斯卡蜗线 (内环)', 'category': '极坐标曲线',
                'expr': 'x=(1+2*cos(t))*cos(t), y=(1+2*cos(t))*sin(t), z=0; t=0..2pi',
                'desc': 'r=1+2cosθ：b>a 时出现内环；b=a 正是心形线'},
    # ---------- 空间曲线 ----------
    'helix': {'name': '圆柱螺线', 'category': '空间曲线',
              'expr': 'x=cos(t), y=sin(t), z=t/6; t=0..4pi',
              'desc': '等距螺旋，曲率/挠率均为常数'},
    'trefoil': {'name': '三叶结 Trefoil', 'category': '空间曲线',
                'expr': 'x=sin(t)+2*sin(2t), y=cos(t)-2*cos(2t), z=-sin(3t); t=0..2pi',
                'desc': '最简单的非平凡纽结 (2,3)'},
    'torus_knot_34': {'name': '环面纽结 (3,4)', 'category': '空间曲线',
                      'expr': 'x=(2+cos(4t))*cos(3t), y=(2+cos(4t))*sin(3t), z=sin(4t); t=0..2pi',
                      'desc': '绕环面 3 圈+4 圈闭合'},
    'torus_knot_25': {'name': '环面纽结 (2,5)', 'category': '空间曲线',
                      'expr': 'x=(2+cos(5t))*cos(2t), y=(2+cos(5t))*sin(2t), z=sin(5t); t=0..2pi',
                      'desc': '所罗门结 (2,5)'},
    'viviani': {'name': 'Viviani 曲线', 'category': '空间曲线',
                'expr': 'x=1+cos(t), y=sin(t), z=2*sin(t/2); t=0..4pi',
                'desc': '球面与柱面相贯线，8 字形'},
    'lissajous3d': {'name': '三维 Lissajous', 'category': '空间曲线',
                    'expr': 'x=sin(3t), y=sin(4t), z=cos(5t); t=0..2pi',
                    'desc': '频率比 3:4:5 的空间李萨如'},
    'torus_knot_35': {'name': '环面纽结 (3,5)', 'category': '空间曲线',
                      'expr': 'x=(2+cos(5*t))*cos(3*t), y=(2+cos(5*t))*sin(3*t), z=sin(5*t); t=0..2pi',
                      'desc': '绕环面 3+5 圈闭合，五角星状纽结'},
    'loxodrome': {'name': '斜驶线 Loxodrome', 'category': '空间曲线',
                  'expr': 'x=cos(3*t)/cosh(t), y=sin(3*t)/cosh(t), z=tanh(t); t=-6..6',
                  'desc': '球面上与所有经线交于等角的航线，从南极盘旋飞向北极'},
    'sph_spiral': {'name': '球面螺线', 'category': '空间曲线',
                   'expr': 'x=cos(t)*cos(4*t), y=cos(t)*sin(4*t), z=sin(t); t=-pi/2..pi/2',
                   'desc': '纬度匀速、经度匀速的单位球面螺旋'},
    'cone_helix': {'name': '圆锥螺线', 'category': '空间曲线',
                   'expr': 'x=0.18*t*cos(t), y=0.18*t*sin(t), z=0.25*t; t=0..6pi',
                   'desc': '半径线性增长的螺旋（圣诞树/钻头形状）'},
    # ---------- 经典曲面 ----------
    'saddle': {'name': '鞍面 z=x²−y²', 'category': '经典曲面',
               'expr': 'z=x^2-y^2', 'desc': '双曲抛物面，原点为鞍点'},
    'paraboloid': {'name': '椭圆抛物面', 'category': '经典曲面',
                   'expr': 'z=(x^2+y^2)/4', 'desc': '旋转抛物面 z=(x²+y²)/4'},
    'monkey_saddle': {'name': '猴鞍面 z=x³−3xy²', 'category': '经典曲面',
                      'expr': 'z=x^3-3*x*y^2; x=-2.5..2.5, y=-2.5..2.5',
                      'desc': '三阶鞍点（Re(x+iy)³），猴子能放尾巴的鞍'},
    'hemisphere': {'name': '上半球面 (LaTeX \\sqrt)', 'category': '经典曲面',
                   'expr': r'z=\sqrt{16-x^2-y^2}; x=-4..4, y=-4..4',
                   'desc': '半径 4 上半球，域外自动裁切'},
    'cone': {'name': '圆锥面 z=√(x²+y²)', 'category': '经典曲面',
             'expr': 'z=sqrt(x^2+y^2); x=-4..4, y=-4..4', 'desc': '45° 圆锥'},
    'gaussian': {'name': '高斯钟面', 'category': '经典曲面',
                 'expr': 'z=3*exp(-(x^2+y^2)/2); x=-3..3, y=-3..3',
                 'desc': '二维正态密度形状'},
    'wave': {'name': '波面 z=sin(x)cos(y)', 'category': '经典曲面',
             'expr': 'z=sin(x)*cos(y); x=-6.28..6.28, y=-6.28..6.28',
             'desc': '双向驻波'},
    'ripple': {'name': '涟漪 \\frac{sin r}{r}', 'category': '经典曲面',
               'expr': r'z=\frac{\sin(\sqrt{x^2+y^2})}{\sqrt{x^2+y^2}+0.001}; x=-12..12, y=-12..12',
               'desc': 'sinc 径向波，LaTeX 分式示例'},
    # ---------- 隐式曲面 F(x,y,z)=0 ----------
    'sphere': {'name': '球面 x²+y²+z²=4', 'category': '隐式曲面',
               'expr': 'x^2+y^2+z^2=4; x=-2.5..2.5, y=-2.5..2.5, z=-2.5..2.5',
               'desc': '半径 2，Marching Tetrahedra 重建'},
    'ellipsoid': {'name': '椭球面 (LaTeX \\frac)', 'category': '隐式曲面',
                  'expr': r'\frac{x^2}{9}+\frac{y^2}{4}+z^2=1; x=-3.5..3.5, y=-2.5..2.5, z=-1.5..1.5',
                  'desc': 'a=3, b=2, c=1'},
    'hyperboloid': {'name': '单叶双曲面 x²+y²−z²=1', 'category': '隐式曲面',
                    'expr': 'x^2+y^2-z^2=1; x=-3..3, y=-3..3, z=-3..3',
                    'desc': '双重直纹曲面'},
    'hyperboloid2': {'name': '双叶双曲面 (参数 a,b)', 'category': '隐式曲面',
                     'expr': 'x^2/a^2+y^2/b^2-z^2=-1; x=-2.5..2.5, y=-2.5..2.5, z=-3..3',
                     'desc': '上下两叶分离，|z|≥c；a,b 默认 1，可 ; a=2, b=1 改形'},
    'torus': {'name': '环面 (R=2, r=1)', 'category': '隐式曲面',
              'expr': '(x^2+y^2+z^2+3)^2=16*(x^2+y^2); x=-3.5..3.5, y=-3.5..3.5, z=-1.5..1.5',
              'desc': '(x²+y²+z²+R²−r²)²=4R²(x²+y²)'},
    'gyroid': {'name': 'Gyroid 极小曲面', 'category': '极小曲面',
               'expr': 'sin(x)*cos(y)+sin(y)*cos(z)+sin(z)*cos(x)=0; x=-pi..pi, y=-pi..pi, z=-pi..pi',
               'desc': '三重周期极小曲面（八叉树自适应/密集回退均匀网格）'},
    'schwarz_p': {'name': 'Schwarz P 曲面', 'category': '极小曲面',
                  'expr': 'cos(x)+cos(y)+cos(z)=0; x=-pi..pi, y=-pi..pi, z=-pi..pi',
                  'desc': '三重周期极小曲面(TPMS)，立方对称，泡沫/骨骼结构原型'},
    'scherk': {'name': 'Scherk 极小曲面', 'category': '极小曲面',
               'expr': 'exp(z)*cos(y)=cos(x); x=-1.4..1.4, y=-1.4..1.4, z=-3..3',
               'desc': '1834 年发现的第一个新极小曲面，棋盘状无穷翼片'},
    'schwarz_d': {'name': 'Schwarz D 曲面', 'category': '极小曲面',
                  'expr': 'cos(x)*cos(y)*cos(z)+cos(x)+cos(y)+cos(z)=0; x=-pi..pi, y=-pi..pi, z=-pi..pi',
                  'desc': 'Schwarz Diamond：立方对称的三重周期极小曲面，与 P 曲面互补'},
    'heart_surface': {'name': '心形曲面 3D', 'category': '隐式曲面',
                      'expr': '(x^2+2.25*y^2+z^2-1)^3=x^2*z^3+0.1125*y^2*z^3; x=-1.5..1.5, y=-1.5..1.5, z=-1.5..1.5',
                      'desc': '(x²+9y²/4+z²−1)³=x²z³+9y²z³/80，六次隐式爱心'},
    'roman': {'name': 'Steiner 罗马曲面', 'category': '隐式曲面',
              'expr': 'x^2*y^2+y^2*z^2+z^2*x^2=x*y*z; x=-1.2..1.2, y=-1.2..1.2, z=-1.2..1.2',
              'desc': '射影平面到 R³ 的浸入，三条自交线+三个 pinch point'},
    'whitney': {'name': 'Whitney 伞', 'category': '隐式曲面',
                'expr': 'x^2=y^2*z; x=-1.5..1.5, y=-1.5..1.5, z=-0.5..2.5',
                'desc': 'x²=y²z，带一条自交"伞柄"的奇曲面，奇点在整条线上'},
    'superellipsoid': {'name': '超椭球 (圆角立方)', 'category': '隐式曲面',
                       'expr': 'abs(x)^4+abs(y)^4+abs(z)^4=1; x=-1.4..1.4, y=-1.4..1.4, z=-1.4..1.4',
                       'desc': '|x|⁴+|y|⁴+|z|⁴=1，介于球与立方体之间（Piet Hein 超蛋）'},
    'octahedron': {'name': '正八面体 |x|+|y|+|z|=1', 'category': '隐式曲面',
                   'expr': 'abs(x)+abs(y)+abs(z)=1; x=-1.4..1.4, y=-1.4..1.4, z=-1.4..1.4',
                   'desc': 'ℓ¹ 球面，正方体的对偶多面体；水平截面是正方形'},
    'tetra': {'name': '正四面体', 'category': '隐式曲面',
              'expr': 'max(x+y-z, x-y+z, -x+y+z, -x-y-z)=1; x=-1.3..1.3, y=-1.3..1.3, z=-1.3..1.3',
              'desc': '四个半空间交（max 式）：4 面/4 顶点/6 棱，顶点取立方体交错顶点，自对偶'},
    'cube': {'name': '正六面体 (立方体)', 'category': '隐式曲面',
             'expr': 'max(abs(x),abs(y),abs(z))=1; x=-1.3..1.3, y=-1.3..1.3, z=-1.3..1.3',
             'desc': 'ℓ∞ 单位球：6 面/8 顶点/12 棱；唯一能单独堆满空间的正多面体'},
    'dodeca': {'name': '正十二面体', 'category': '隐式曲面',
               'expr': 'max(-0.381966*x-0.618034*z-1, 0.618034*y-0.381966*z-1, -0.618034*x+0.381966*y-1, -0.381966*x+0.618034*z-1, -0.618034*y+0.381966*z-1, -0.618034*x-0.381966*y-1, 0.618034*x-0.381966*y-1, 0.381966*x-0.618034*z-1, -0.618034*y-0.381966*z-1, 0.618034*x+0.381966*y-1, 0.381966*x+0.618034*z-1, 0.618034*y+0.381966*z-1)=0; x=-2.1..2.1, y=-2.1..2.1, z=-2.1..2.1',
               'desc': '12 个五边形面半空间交（系数为 1/φ² 与 1/φ，凸包导出）：12 面/20 顶点/30 棱，与正二十面体互对偶'},
    'icosa': {'name': '正二十面体', 'category': '隐式曲面',
              'expr': 'max(0.381966*x-0.381966*y+0.381966*z-1, 0.618034*y-0.236068*z-1, 0.618034*x+0.236068*y-1, 0.618034*x-0.236068*y-1, 0.381966*x+0.381966*y-0.381966*z-1, 0.236068*x-0.618034*z-1, 0.381966*x-0.381966*y-0.381966*z-1, -0.381966*x-0.381966*y+0.381966*z-1, -0.618034*y-0.236068*z-1, -0.618034*y+0.236068*z-1, 0.381966*x+0.381966*y+0.381966*z-1, -0.236068*x+0.618034*z-1, 0.236068*x+0.618034*z-1, 0.618034*y+0.236068*z-1, -0.381966*x+0.381966*y+0.381966*z-1, -0.236068*x-0.618034*z-1, -0.381966*x+0.381966*y-0.381966*z-1, -0.618034*x+0.236068*y-1, -0.381966*x-0.381966*y-0.381966*z-1, -0.618034*x-0.236068*y-1)=0; x=-2.1..2.1, y=-2.1..2.1, z=-2.1..2.1',
              'desc': '20 个三角形面半空间交（凸包导出）：20 面/12 顶点/30 棱，与正十二面体互对偶'},
    'cayley': {'name': 'Cayley 三次曲面 (4 节点)', 'category': '隐式曲面',
               'expr': 'x^2+y^2+z^2+2*x*y*z=1; x=-1.6..1.6, y=-1.6..1.6, z=-1.6..1.6',
               'desc': 'x²+y²+z²+2xyz=1：带最多 4 个节点的三次曲面，有理曲面'},
    'kummer': {'name': 'Kummer 四次曲面 (16 节点)', 'category': '隐式曲面',
               'expr': '(x^2+y^2+z^2-2)^2=5*((1-z)^2-2*x^2)*((1+z)^2-2*y^2); x=-1.8..1.8, y=-1.8..1.8, z=-1.8..1.8',
               'desc': '(x²+y²+z²−μ²)²=λpqrs 取 μ²=2, λ=5：四次曲面节点数上限 16 全部达到，已数值验证'},
    'barth': {'name': 'Barth 六次曲面 (50 节点)', 'category': '隐式曲面',
              'expr': '4*((3+sqrt(5))/2*x^2-y^2)*((3+sqrt(5))/2*y^2-z^2)*((3+sqrt(5))/2*z^2-x^2)=(2+sqrt(5))*(x^2+y^2+z^2-1)^2; x=-1.9..1.9, y=-1.9..1.9, z=-1.9..1.9',
              'desc': '六次曲面节点数纪录 65（射影）的仿射实现：50 个实节点=正十二面体 20 + 三十·十二面体 30，黄金比 φ 内嵌，已数值验证'},
    'barth_decic': {'name': 'Barth 十次曲面 (300 节点)', 'category': '隐式曲面',
                    'expr': '8*(x^2-phi^4*y^2)*(y^2-phi^4*z^2)*(z^2-phi^4*x^2)*(x^4+y^4+z^4-2*x^2*y^2-2*x^2*z^2-2*y^2*z^2)+(3+5*phi)*(x^2+y^2+z^2-1)^2*(x^2+y^2+z^2-(2-phi))^2=0; x=-2.1..2.1, y=-2.1..2.1, z=-2.1..2.1, phi=1.618033988749895',
                    'desc': '十次曲面节点数世界纪录 345（射影）；仿射 w=1 保留 300 个实节点，分布于半径 1/φ, √(5−2√5), √((5+√5)/2), 1 四个同心多面体（Nordstrand 式，φ≈1.618…）'},
    'clebsch': {'name': 'Clebsch 对角三次曲面', 'category': '隐式曲面',
                'expr': '81*(x^3+y^3+z^3)-189*(x^2*y+x^2*z+y^2*x+y^2*z+z^2*x+z^2*y)+54*x*y*z+126*(x*y+x*z+y*z)-9*(x^2+y^2+z^2)-9*(x+y+z)+1=0; x=-2.5..2.5, y=-2.5..2.5, z=-2.5..2.5',
                'desc': 'Clebsch 对角三次：27 条直线全为实 + 10 个 Eckardt 点（三切面三线共点）的明星三次曲面'},
    'hunt': {'name': 'Hunt 曲面', 'category': '隐式曲面',
             'expr': '4*(x^2+y^2+z^2-13)^3+27*(3*x^2+y^2-4*z^2-12)^2=0; x=-3.7..3.7, y=-3.7..3.7, z=-3.7..3.7',
             'desc': '4A³+27B²=0 型（与心形曲面同族），有界闭曲面；沿球面 x²+y²+z²=13 与二次曲面 3x²+y²−4z²=12 的交线奇异（已数值验证），Nordstrand 画廊藏品'},
    'dupin': {'name': 'Dupin 圆环面 (双月牙)', 'category': '隐式曲面',
              'expr': '-375.0999*(x^2+y^2+z^2)^2+3240.72*x*(x^2+y^2+z^2)-7291.62*(x^2+y^2+z^2)+1296*x^2-5832*x+7779.24*y^2+6561=0; x=-6..6, y=-6..6, z=-6..6',
              'desc': 'Dupin 圆环面（环面的反演）：两族曲率线都是圆。取 Nordstrand 双月牙参数 r0=4.9,r1=5,dx=2,dy=0,ri=3，常数已代入展开'},
    'horn_torus': {'name': '角环面 (R=r)', 'category': '隐式曲面',
                   'expr': '(x^2+y^2+z^2)^2=4*(x^2+y^2); x=-2.3..2.3, y=-2.3..2.3, z=-1.3..1.3',
                   'desc': 'R=r 临界环面：剖面圆 (ρ−1)²+z²=1 切轴于原点（原点为锥奇点），环面→纺锤环面的临界情形；旧式误加常数 +1 致零集退化为圆环，已修'},
    'spindle_torus': {'name': '纺锤环面 (R<r)', 'category': '隐式曲面',
                      'expr': '(x^2+y^2+z^2-1)^2=2.25*(x^2+y^2); x=-2.2..2.2, y=-2.2..2.2, z=-1.4..1.4',
                      'desc': 'R=0.75<r=1.25：自交环面，内侧区域上下自我穿过'},
    'neovovius': {'name': 'Neovovius 曲面', 'category': '隐式曲面',
                  'expr': 'cos(x)+cos(y)+cos(z)+4*cos(x)*cos(y)*cos(z)=0; x=-pi..pi, y=-pi..pi, z=-pi..pi',
                  'desc': '三重周期经典曲面，Schwarz P 的近亲，腔体相互贯穿'},
    'prism3': {'name': '正三棱柱', 'category': '隐式曲面',
               'expr': 'max(sqrt(3)/2*x+y/2, -sqrt(3)/2*x+y/2, -y)+0*z=0.5; x=-1.1..1.1, y=-1.1..1.1, z=-1.5..1.5',
               'desc': 'max(三个半平面)=内切圆半径：正三角形沿 z 平移的柱面（+0*z 使分类器识别为 3D）'},
    'prism4': {'name': '正四棱柱 (方柱)', 'category': '隐式曲面',
               'expr': 'max(abs(x),abs(y))+0*z=1; x=-1.4..1.4, y=-1.4..1.4, z=-1.5..1.5',
               'desc': 'ℓ∞ 球面：max(|x|,|y|)=1，正方形截面沿 z 平移'},
    'prism6': {'name': '正六棱柱', 'category': '隐式曲面',
               'expr': 'max(sqrt(3)/2*x+y/2, y, -sqrt(3)/2*x+y/2, -sqrt(3)/2*x-y/2, -y, sqrt(3)/2*x-y/2)+0*z=sqrt(3)/2; x=-1.2..1.2, y=-1.2..1.2, z=-1.5..1.5',
               'desc': '六个半平面取 max = 内切圆半径 √3/2：蜂巢单元的形状'},
    # ---------- 参数曲面 r(u,v) ----------
    'psphere': {'name': '完整球面 r(u,v)', 'category': '参数曲面',
                'expr': 'x=2*sin(u)*cos(v), y=2*sin(u)*sin(v), z=2*cos(u); u=0..pi, v=0..2pi',
                'desc': '半径 2，解析精确（比隐式重建更光滑）'},
    'ptorus': {'name': '环面 r(u,v) (R=2,r=1)', 'category': '参数曲面',
               'expr': 'x=(2+cos(v))*cos(u), y=(2+cos(v))*sin(u), z=sin(v); u=0..2pi, v=0..2pi',
               'desc': '完整环面，无缝闭合'},
    'mobius': {'name': 'Möbius 带', 'category': '参数曲面',
               'expr': 'x=(1.5+0.5*v*cos(u/2))*cos(u), y=(1.5+0.5*v*cos(u/2))*sin(u), z=0.5*v*sin(u/2); u=0..2pi, v=-1..1',
               'desc': '单侧不可定向曲面，半扭转'},
    'helicoid': {'name': '螺旋面 Helicoid', 'category': '极小曲面',
                 'expr': 'x=v*cos(u), y=v*sin(u), z=u/6; u=0..4pi, v=-1..1',
                 'desc': '极小曲面，螺旋坡道'},
    'klein': {'name': 'Klein 瓶 (figure-8)', 'category': '参数曲面',
              'expr': 'x=(2+cos(u/2)*sin(v)-sin(u/2)*sin(2v))*cos(u), y=(2+cos(u/2)*sin(v)-sin(u/2)*sin(2v))*sin(u), z=sin(u/2)*sin(v)+cos(u/2)*sin(2v); u=0..2pi, v=0..2pi',
              'desc': '不可定向闭曲面，8 字形浸入'},
    'crosscap': {'name': 'Cross-cap 交叉帽', 'category': '参数曲面',
                 'expr': 'x=u*v, y=u^2, z=v^2; u=-1..1, v=-1..1',
                 'desc': '射影平面的另一种浸入，Whitney 伞的近亲'},
    'enneper': {'name': 'Enneper 极小曲面', 'category': '极小曲面',
                'expr': 'x=u-u^3/3+u*v^2, y=v-v^3/3+v*u^2, z=u^2-v^2; u=-2..2, v=-2..2',
                'desc': '自带三折纸感的极小曲面，与悬链面并列为最早的非平凡例子'},
    'catenoid': {'name': '悬链面 Catenoid', 'category': '极小曲面',
                 'expr': 'x=cosh(v)*cos(u), y=cosh(v)*sin(u), z=v; u=0..2pi, v=-1.5..1.5',
                 'desc': '悬链线旋转而成——两个肥皂圈之间的自然形状'},
    'gabriel': {'name': '托里拆利小号', 'category': '参数曲面',
                'expr': 'x=u, y=cos(v)/u, z=sin(v)/u; u=1..6, v=0..2pi',
                'desc': "Gabriel's horn: y=1/x 绕 x 轴旋转。体积有限 π，表面积无穷——'装满油漆却刷不完内壁'"},
    'pseudosphere': {'name': '伪球面 Tractricoid', 'category': '参数曲面',
                     'expr': 'x=cos(v)/cosh(u), y=sin(v)/cosh(u), z=u-tanh(u); u=0..3, v=0..2pi',
                     'desc': '曳物线旋转面，常数负曲率 K=−1，非欧几何的物理模型'},
    'dini': {'name': 'Dini 曲面', 'category': '参数曲面',
             'expr': 'x=cos(u)*sin(v), y=sin(u)*sin(v), z=cos(v)+ln(tan(v/2))+0.2*u; u=0..4pi, v=0.1..2',
             'desc': '扭转的伪球面，常数负曲率 K=−1，像一根螺旋意面'},
    'boy': {'name': 'Boy 曲面 (Apéry)', 'category': '参数曲面',
            'expr': 'x=(sqrt(2)*cos(v)^2*cos(2*u)+cos(u)*sin(2*v))/(2-sqrt(2)*sin(3*u)*sin(2*v)), y=(sqrt(2)*cos(v)^2*sin(2*u)-sin(u)*sin(2*v))/(2-sqrt(2)*sin(3*u)*sin(2*v)), z=3*cos(v)^2/(2-sqrt(2)*sin(3*u)*sin(2*v)); u=0..pi, v=0..pi',
            'desc': '射影平面到 R³ 的浸入，与 Klein 瓶、罗马曲面凑齐“不可定向三杰”'},
    'kuen': {'name': 'Kuen 曲面', 'category': '参数曲面',
             'expr': 'x=2*(cos(u)+u*sin(u))*sin(v)/(1+u^2*sin(v)^2), y=2*(sin(u)-u*cos(u))*sin(v)/(1+u^2*sin(v)^2), z=log(tan(v/2))+2*cos(v)/(1+u^2*sin(v)^2); u=0..4pi, v=0.15..3',
             'desc': '常数负曲率 K=−1 的波浪曲面，伪球面/ Dini 的兄弟'},
    'seashell': {'name': '贝壳面 (螺壳)', 'category': '参数曲面',
                 'expr': 'x=(0.12*u+0.08*u*cos(v))*cos(u), y=(0.12*u+0.08*u*cos(v))*sin(u), z=0.08*u*sin(v)-0.28*u; u=0..5pi, v=0..2pi',
                 'desc': '螺旋转角半径与管径同步增长的生长螺旋——蜗牛壳的参数化'},
    'bohemian': {'name': 'Bohemian 穹顶', 'category': '参数曲面',
                 'expr': 'x=0.5*cos(u), y=1.5*cos(v)+0.5*sin(u), z=1*sin(v); u=0..2pi, v=0..2pi',
                 'desc': '圆沿垂直方向的圆旋转扫出的包络（a=0.5,b=1.5,c=1）——像一颗薄荷糖的壳体'},
    'cylinder': {'name': '圆柱面 r(u,v)', 'category': '参数曲面',
                 'expr': 'x=cos(u), y=sin(u), z=v; u=0..2pi, v=-1.5..1.5',
                 'desc': '单位圆沿 z 平移：直纹可展曲面，高斯曲率 K≡0'},
    'cyl_ellipse': {'name': '椭圆柱面', 'category': '参数曲面',
                    'expr': 'x=2*cos(u), y=sin(u), z=v; u=0..2pi, v=-1.5..1.5',
                    'desc': '椭圆 (a=2,b=1) 沿 z 平移的柱面，同样可展（K≡0）'},
    # ---------- 不等式区域 ----------
    'disk': {'name': '圆盘 x²+y²<r²（参数）', 'category': '不等式区域',
             'expr': 'x^2+y^2<r^2; r=2',
             'desc': '参数 r=2，改为 ; r=3 试试'},
    'ellipse_region': {'name': '椭圆区域 (LaTeX \\le)', 'category': '不等式区域',
                       'expr': r'\frac{x^2}{4}+\frac{y^2}{9} \le 1',
                       'desc': '闭椭圆区域'},
    'annulus': {'name': '环形区域（不等式组）', 'category': '不等式区域',
                'expr': 'x^2+y^2>1, x^2+y^2<4; x=-2.5..2.5, y=-2.5..2.5',
                'desc': '1<x²+y²<4，逗号联立取交集'},
    'parabolic_region': {'name': '抛物线围成区域（组）', 'category': '不等式区域',
                         'expr': 'y>x^2, y<4-x^2; x=-2.5..2.5, y=-1..5',
                         'desc': '两抛物线之间的有界区域'},
    'lp_region': {'name': '线性规划可行域', 'category': '不等式区域',
                  'expr': 'y<x+2, y>-x+1, x<2, y>0; x=-1..2.5, y=-0.5..4.5',
                  'desc': '四个一次不等式联立的交集（高中线性规划）：阴影四边形即可行域'},
    'ball': {'name': '球体 x²+y²+z²<4（3D）', 'category': '不等式区域',
             'expr': 'x^2+y^2+z^2<4; x=-2.5..2.5, y=-2.5..2.5, z=-2.5..2.5',
             'desc': '半透明边界球面 + z=0 截面圆盘'},
}

_TEMPLATE = {
    "_readme": ("自定义曲线/曲面配置。键为唯一 ID；name=显示名；category=菜单分类；"
                "expr=表达式（与输入框语法相同，兼容 LaTeX，注意 JSON 中反斜杠须写双份，"
                "如 \"z=\\\\frac{x^2}{4}\"）；desc=描述（可选）。下划线开头的键被忽略。"
                "保存后点菜单「函数库 ▾ → ↻ 重载用户配置」即时生效。条目按 category 归入对应子菜单；"
                "未赋值的参数（如 a,b）自动取 1，可用 ; a=2, b=3 显式赋值。"),
    "my_lissajous": {
        "name": "李萨如曲线 (3:4)",
        "category": "我的自定义",
        "expr": "x=sin(3t+pi/2), y=sin(4t), z=0; t=0..2pi",
        "desc": "示例条目，可随意修改或删除"
    }
}


def load_user(path=USER_FILE):
    """读取用户配置; 文件不存在时自动创建模板。返回 (条目字典, 警告列表)"""
    if not os.path.exists(path):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(_TEMPLATE, f, ensure_ascii=False, indent=2)
                f.write('\n')
            return {}, [f'已创建配置文件: {path}（含示例模板）']
        except OSError as e:
            return {}, [f'无法创建配置文件: {e}']
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        return {}, [f'配置文件读取失败（{e}），仅加载内置库']
    if not isinstance(data, dict):
        return {}, ['配置顶层须为 JSON 对象（ID → 条目）']
    entries = {k: v for k, v in data.items() if not str(k).startswith('_')}
    return entries, []


def load_all(user_path=USER_FILE):
    """合并内置+用户库并预校验表达式。
    返回 ([(分类, [条目...]), ...], 警告列表)；坏条目进警告、不中断。"""
    grouped, warns = {}, []

    def add(key, e, user=False):
        if not isinstance(e, dict) or not e.get('name') or not e.get('expr'):
            warns.append(f'条目 {key} 忽略: 缺少 name/expr 字段')
            return
        try:
            mathparse.parse_input(e['expr'])
        except mathparse.ParseError as ex:
            warns.append(f'条目 {key} 表达式错误: {ex}')
            return
        cat = e.get('category') or '未分类'
        grouped.setdefault(cat, []).append(
            {'key': key, 'name': e['name'], 'expr': e['expr'],
             'category': cat, 'desc': e.get('desc', ''), 'user': user})

    for k, e in BUILTIN.items():
        add(k, e)
    user, warns2 = load_user(user_path)
    warns.extend(warns2)
    for k, e in user.items():
        add(k, e, user=True)
    return list(grouped.items()), warns
