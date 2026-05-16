#!/bin/bash
set -e

# 如果环境变量 MODE 为 gpu，且尚未安装相关的 nvidia 库，则进行安装
if [ "$MODE" == "gpu" ]; then
    echo "检测到 GPU 模式，正在检查/安装 NVIDIA 运行时库..."
    # 这些库是 ctranslate2 在 GPU 上运行所必须的
    pip install --no-cache-dir nvidia-cublas-cu12 nvidia-cudnn-cu12
    
    # 将安装好的库路径加入 LD_LIBRARY_PATH
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$(python3 -c 'import os; import nvidia.cublas.lib as lib; print(os.path.dirname(lib.__file__))')
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$(python3 -c 'import os; import nvidia.cudnn.lib as lib; print(os.path.dirname(lib.__file__))')
    echo "GPU 环境准备就绪。"
else
    echo "运行于 CPU 模式。"
fi

# 启动 API 服务器
exec python3 whisper_api.py "$@"
