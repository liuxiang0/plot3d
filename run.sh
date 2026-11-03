#!/bin/bash
# plot3d 桌面端启动器: 自动 cd 到脚本目录 + 优先 venv 解释器（超集：tkinter/PIL/numpy/scipy/skimage 全有）
# 用法: ./run.sh   或   bash run.sh   （等价于 cd plot3d && <解释器> main_app.py）
cd "$(dirname "$0")" || exit 1
PY=/home/kumath/.openclaw/workspace/.venv/numina/bin/python
[ -x "$PY" ] || PY=python3
exec "$PY" main_app.py "$@"
