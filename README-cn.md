# Plot3D · 数学 3D 可视化平台

面向数学教学与研究的轻量 3D 可视化平台：任意表达式实时绘图、150 条内置经典曲线/曲面、样条设计、曲率分析、3D 打印导出，以及单文件《曲线图鉴》。纯本地运行，零外部网络依赖。

## 主要功能

- **表达式实时绘图**：显式/隐式/参数/不等式等八种形态，兼容 LaTeX 输入（如 `\frac{x^2}{9}+y^2=1`）
- **内置图形库 150 条**：代数曲线、节点曲面（Barth 六次/十次、Kummer）、极小曲面、PDE 精确解十三族 37 条（热方程、KdV、sine-Gordon、Kármán 涡街、Love 波、斜激波、undular bore……）
- **Bézier / NURBS 样条设计器**：点列插值 + 控制点实时微调，14 例样条库
- **曲面分析**：角亏缺曲率 K、余切 Laplacian 平均曲率 H
- **导出**：SVG/EPS 矢量图、OBJ/STL 3D 打印模型
- **画廊**：缩略图网格 + 搜索 + 150 张资料卡（公式/性质/趣闻）+ 收藏
- **《曲线图鉴》**：一键生成单文件自包含 HTML（本地 KaTeX 全内联，可离线分发/打印）
- **手机 Web 端**：本地服务 8030 端口，局域网直连

## 主要特点

- **数值门禁**：14 个门禁脚本、226 项 PDE 检查（符号残差/守恒律/Rankine-Hugoniot/频散关系/自收敛），`gates/run_all.sh` 一键全绿——库中每个精确解都经独立复算
- **纯本地**：Tk 桌面端 + 无头 Web 端；缩略图 PIL 离屏渲染；不联网、不调云 API
- **可复现**：数值解磁盘缓存（Blasius/Gray-Scott/GN 孤波/bore 等）、seed 可复现组卷式采样
- **教学友好**：资料卡含历史典故（Blasius 1908、von Kármán 1911、Russell 1834 孤波……）

## 如何开始

环境：Python 3.12 + numpy / Pillow / scipy（项目虚拟环境 `.venv/numina` 已备；系统 python3 亦可跑桌面端）。

```bash
# 桌面端（需 DISPLAY）
python3 plot3d/main_app.py          # 或 plot3d/run.sh（自动选解释器）

# 手机/浏览器端（无头）
.venv/numina/bin/python plot3d/web/server.py --port 8030
#   浏览器打开 http://<本机IP>:8030

# 生成《曲线图鉴》
.venv/numina/bin/python plot3d/atlas_gen.py     # → plot3d/output/曲线图鉴.html

# 数值回归门禁
plot3d/gates/run_all.sh
```

## 目录结构

```text
plot3d/
├── main_app.py          # 桌面合并入口（绘图器 + 样条设计器双标签）
├── plotter_app.py       # 绘图器主窗口（八形态解析/渲染/动画预设）
├── engine3d.py          # 3D 矢量引擎（转台投影/LOD/SVG·EPS 导出）
├── mathparse.py         # 表达式解析层（AST 白名单，兼容 LaTeX）
├── curve_library.py     # 内置图形库（150 条）
├── trisurf.py           # 三角剖分/高度场生成器（PDE 数值解）
├── gallery.py           # 画廊（缩略图 + 搜索 + 资料卡）
├── atlas_gen.py         # 《曲线图鉴》单文件 HTML 生成器
├── nurbs.py / spline_app.py / export3d.py / surf_analysis.py
├── web/server.py        # 手机 Web 服务（8030）
├── gates/               # 数值门禁（run_all.sh 一键）
├── thumbs/  output/     # 缩略图缓存 / 图鉴与动画产物
└── plot3d设计与实现.md   # 完整设计-实现-验证记录
```

## 许可证

MIT License © 2026 kumath。自由使用、修改、分发，保留版权声明即可。（仓库根附 `LICENSE` 文件。）

## 发布到 GitHub（含网站）

**仓库标题建议**：`Plot3D — 数学 3D 可视化平台（150 内置曲线/曲面 · 数值门禁 · 单文件曲线图鉴）`
**仓库名建议**：`plot3d-math`

```bash
cd plot3d                      # 或把 plot3d/ 作为仓库根
git remote add origin git@github.com:<你的用户名>/plot3d-math.git
git push -u origin main
```

**GitHub Pages 网站**（托管《曲线图鉴》）：

1. 图鉴为单文件自包含 HTML（KaTeX 与缩略图 base64 全内联），最适合 Pages：

   ```bash
   mkdir -p docs && cp output/曲线图鉴.html docs/index.html
   git add docs && git commit -m "docs: 曲线图鉴上线 Pages" && git push
   ```

2. 仓库 → **Settings → Pages** → Source 选 `Deploy from a branch` → Branch 选 `main`、目录 `/docs` → Save；
3. 数分钟后访问 `https://<你的用户名>.github.io/plot3d-math/` 即为图鉴网站。

**入库体积提示**：`thumbs/`（153 张 PNG，约数 MB）与 `*.npy` 缓存可直接入库；若嫌大，在 `.gitignore` 排除并附 `gallery.py` 一键重建说明即可。桌面 Tk 与 8030 Web 服务均为本地进程，不随 Pages 发布。
