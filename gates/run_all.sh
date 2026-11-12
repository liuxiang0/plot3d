#!/bin/bash
# gates/run_all.sh — 门禁一键跑（venv 解释器优先；任一 FAIL 即退出码 1）
# 用法: plot3d/gates/run_all.sh   （verify_nodes 的 Barth 十次 300 节点约 15 分钟, 不在此列, 手动: python verify_nodes.py decic）
cd "$(dirname "$0")" || exit 1
PY=/home/kumath/.openclaw/workspace/.venv/numina/bin/python
[ -x "$PY" ] || PY=python3
for g in gate_pde.py gate_pde2.py gate_pde3.py gate_pde4.py gate_pde5.py gate_pde6.py gate_pde7.py gate_pde8.py gate_pde9.py gate_pde10.py gate_simplify.py gate_genus.py; do
  echo "===== $g"
  "$PY" "$g" || exit 1
done
echo "===== 全部门禁绿"
