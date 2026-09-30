#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if command -v conda >/dev/null 2>&1; then
    conda_base="$(conda info --base)"
elif [[ -x "$HOME/miniconda3/bin/conda" ]]; then
    conda_base="$HOME/miniconda3"
else
    echo "错误：找不到 conda，请先安装 Miniconda 或将 conda 加入 PATH。" >&2
    exit 1
fi

# shellcheck source=/dev/null
source "$conda_base/etc/profile.d/conda.sh"
conda activate toolkit-camera

echo "摄像头拍照工具"
read -r -p "摄像头编号 [0]：" camera
camera="${camera:-0}"

while true; do
    read -r -p "模式：1=拍一张，2=按帧率拍多张 [1]：" mode
    mode="${mode:-1}"
    case "$mode" in
        1|2) break ;;
        *) echo "请输入 1 或 2。" ;;
    esac
done

count=1
fps=1
if [[ "$mode" == 2 ]]; then
    read -r -p "要保存多少张：" count
    read -r -p "目标帧率（每秒多少张）[1]：" fps
    fps="${fps:-1}"
fi

read -r -p "保存目录 [${script_dir}/output]：" output
args=(--camera "$camera" --count "$count" --fps "$fps")
if [[ -n "$output" ]]; then
    args+=(--output "$output")
fi

python3 "$script_dir/capture_camera.py" "${args[@]}"
