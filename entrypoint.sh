#!/bin/bash
set -e

# 如果环境变量 MODE 为 gpu，且尚未安装相关的 nvidia 库，则进行安装
if [ "$MODE" == "gpu" ]; then
    echo "检测到 GPU 模式，正在检查/安装 NVIDIA 运行时库..."
    # 这些库是 ctranslate2 在 GPU 上运行所必须的
    pip install --no-cache-dir nvidia-cublas-cu12 nvidia-cudnn-cu12 nvidia-cuda-nvrtc-cu12
    
    # 获取 site-packages 路径
    SITE_PACKAGES=$(python3 -c 'import site; print(site.getsitepackages()[0])')
    
    # 动态查找并添加 LD_LIBRARY_PATH
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$SITE_PACKAGES/nvidia/cublas/lib
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$SITE_PACKAGES/nvidia/cudnn/lib
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$SITE_PACKAGES/nvidia/cuda_nvrtc/lib
    
    echo "LD_LIBRARY_PATH 已设置为: $LD_LIBRARY_PATH"
    echo "GPU 环境准备就绪。"
else
    echo "运行于 CPU 模式。"
fi

# 启动 API 服务器
exec python3 whisper_api.py "$@"
