# plot3d · 3D 数学可视化平台

> 经典代数曲线 / 曲面的交互式可视化与教学工具。
> 桌面端（Tkinter）+ 手机端（Web/Three.js）双形态，数学全在 Python 服务端，前端零计算。

一个面向数学教学与研究的 3D 可视化平台：内置 **115 条**经典曲线/曲面（含 Barth 六次/十次、Kummer 等节点曲面世界纪录保持者），支持任意表达式实时绘图（兼容 LaTeX）、Bézier/NURBS 样条设计、曲率分析、OBJ/STL 3D 打印导出，以及单文件《曲线图鉴》HTML 生成。

---

## 功能特性

### 🖥 桌面端（Tkinter，双标签）

- **函数绘图器** `plotter_app.py`：表达式 → 自动识别 → 自动绘图
  - 八种形态：显式 `y=f(x)` / 隐式 `f(x,y)=g(x,y)` / 显式曲面 `z=f(x,y)` / 隐式曲面 `F(x,y,z)=0` / 参数曲线 `r(t)` / 参数曲面 `r(u,v)` / 不等式区域（2D/3D）
  - 兼容 LaTeX 输入（`\frac{}{}`、`\sqrt{}`、`\pi`、`\sin`…）
  - 转台投影 / 无极缩放 / 八叉树自适应 Marching Cubes / Lambert 着色
  - SVG · EPS 矢量导出（`export3d.py` 另支持 OBJ/STL 3D 打印 + 截面工具）
  - 曲面分析：角亏缺高斯曲率 K + 余切 Laplacian 平均曲率 H（`surf_analysis.py`）
- **样条设计器** `spline_app.py`：Bézier/NURBS 点列插值 + 控制点实时微调，内置 14 例样条库（含 ❤ 心形线、♣ 三叶结、✈ NACA 翼型、梅瓶旋转面）

### 📱 手机端（Web / Three.js）

- `web/server.py` 启动后，同一 WiFi 下手机浏览器打开 `http://<电脑IP>:8030`
- 服务端用 numpy + scikit-image 采样几何，前端 Three.js 只做渲染（手机无压力）
- 触摸旋转/缩放、图形库抽屉 + 搜索、资料卡、自定义表达式实时绘制
- three.js 已离线打包（`web/static/lib/`），无外网也能用

### 🖼 画廊与图鉴

- `gallery.py`：缩略图网格 + 搜索 + 一键载入绘图器 + 112 张资料卡（公式/性质/趣闻）
- `atlas_gen.py`：生成单文件自包含《曲线图鉴》HTML（KaTeX 全内联、分类目录、搜索、收藏、打印版式）→ `output/曲线图鉴.html`

### 🧮 表达式解析层 `mathparse.py`

- AST 白名单安全求值（builtins 全禁用）
- LaTeX 兼容、自动分类、定义域后缀（`; x=-3..3, t=0..2pi`）

---

## 内置图形库（115 条）

| 分类 | 代表条目 |
|------|---------|
| 平面代数曲线 | 心形线、双纽线、笛卡尔叶形线、星形线、椭圆曲线 |
| 极坐标曲线 | 阿基米德/对数/费马/双曲螺线、卡西尼卵形线、帕斯卡蜗线 |
| 空间曲线 | 环面纽结 (2,5)/(3,4)/(3,5)、三维 Lissajous、球面/圆锥螺线 |
| 经典曲面 | 鞍面、抛物面、高斯钟面、波纹面 |
| 隐式曲面 | **Barth 六次(50)/十次(300)、Kummer(16)、Cayley(4)、Clebsch、Dupin 圆环面、正三/四/六棱柱** |
| 极小曲面 | Enneper、悬链面、螺旋面、Schwarz P/D、Gyroid、Scherk |
| 参数曲面 | Boy、Klein 瓶、Kuen、贝壳面、Bohemian 穹顶、Möbius 带、圆柱/椭圆柱、二次曲面经纬网 |
| 三角剖分曲面 | 测地球 (Fuller)、三次三角 Bézier 片、散点采样地形 (2D Delaunay)、球面三角片 |
| 不等式区域 | 圆盘、椭圆域、环形域、线性规划可行域、球体 |

**节点曲面均经数值验证**（`verify_nodes.py`）：Kummer 16 节点、Barth 六次 50 仿射实节点、Barth 十次 300 仿射实节点（壳层分布与文献完全吻合），验证方法为多起点 least-squares + 正二十面体对称群轨道补全 + 复步微分终验。

---

## 显示管线优先级（几何法 > 三角剖分 > MC）

1. **几何法（首选）**：精确多边形面（多面体/棱柱，`polytopes.py`）；闭式参数化 r(u,v) 网格（四边形片，顶点解析精确，线框 = u/v 等参线）；显式 z=f(x,y) 正则网格；旋转面/直纹面扫掠。
2. **三角剖分（Delaunay 类，次选）**：曲面以点云/散采样给出，或参数域非矩形（球面三角片、Bézier 三角片）——先对参数域 2D Delaunay 再经 r(u,v) 映射，或对点云做曲面重建；顶点仍精确，连接关系由 Delaunay 最优性给出。
3. **Marching Cubes（立方体巡游，最后手段）**：仅当只有隐式标量场 F=0、无参数化、无点集结构时（Kummer/Barth/TPMS 等）。
   **术语辨正**：MC 是等值面提取（逐胞查案例表 + 棱上插值制造新顶点），**不是三角剖分**——三角剖分通常意义指对给定点集的 Delaunay 类连接构建；两者在顶点来源、输入结构、最优性准则上本质不同。MC 输出恰为三角形网格仅是表示副产物，其线框无几何意义。

## 快速开始

### 依赖

- Python 3.10+，桌面端需 `tkinter`、`Pillow`
- 虚拟环境 `.venv/numina/`（含 `numpy`、`scipy`、`scikit-image`、`faiss-cpu`）

### 桌面端

```bash
python3 plot3d/main_app.py          # 双标签合并入口
python3 plot3d/plotter_app.py       # 仅函数绘图器
python3 plot3d/spline_app.py        # 仅样条设计器
```

### 手机端（Web）

```bash
.venv/numina/bin/python plot3d/web/server.py --port 8030
# 手机(同一 WiFi)打开:  http://<电脑IP>:8030
```

### 验证门禁

```bash
.venv/numina/bin/python plot3d/verify_nodes.py          # Kummer 16 + Barth 50
.venv/numina/bin/python plot3d/verify_nodes.py decic    # Barth 十次 300（约15分钟）
```

---

## 目录结构

```
plot3d/
├── main_app.py          # 合并入口（双标签）
├── plotter_app.py       # 三维函数绘图器
├── spline_app.py        # Bézier/NURBS 样条设计器
├── engine3d.py          # 3D 矢量引擎（转台投影/SVG·EPS 导出）
├── mathparse.py         # 表达式解析层（AST 白名单/LaTeX 兼容）
├── curve_library.py     # 内置图形库（115 条）
├── gallery.py           # 画廊（缩略图+搜索+112 资料卡）
├── atlas_gen.py         # 《曲线图鉴》单文件 HTML 生成器
├── nurbs.py             # NURBS 数学（含旋转面精确构造器）
├── surf_analysis.py     # 曲率分析（K + H）
├── export3d.py          # OBJ/STL 导出 + 截面工具
├── verify_nodes.py      # 节点曲面数值验证门禁
├── thumbs/              # 缩略图缓存（115 张）
├── web/                 # 手机版 Web 应用
│   ├── server.py        # 零依赖 HTTP 服务（几何采样 API）
│   ├── geometry.py      # 无头几何采样层（numpy+skimage）
│   └── static/          # 前端（index/app/style + 离线 three.js）
└── 代数曲线与曲面汇总.md  # 设计文档
```

---

## 发布到 GitHub

本目录为独立 Git 仓库（与上层 workspace 解耦，`output/` 等产物已忽略）。

```bash
cd plot3d
git init && git add . && git commit -m "plot3d: 3D 数学可视化平台（桌面+手机双形态）"
git branch -M main
git remote add origin https://github.com/<你的用户名>/plot3d.git
git push -u origin main
```

详见会话内的发布指引（含认证方式选择）。

---

## 许可与引用

- 数学内容来源：NuminaMath、Nordstrand 数学画廊、MathWorld、Schoen (1970, NASA TN D-5541)、Barth (1996)
- 节点曲面公式均经数值验证后入库，严禁未验证公式
