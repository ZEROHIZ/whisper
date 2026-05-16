# 使用较小的基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖 (ffmpeg 是必须的)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# 拷贝代码和依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir .

# 暴露 API 端口
EXPOSE 8000

# 设置模型缓存目录
ENV WHISPER_MODEL_CACHE=/app/models
RUN mkdir -p $WHISPER_MODEL_CACHE

# 赋予执行权限
RUN chmod +x entrypoint.sh

# 使用 entrypoint 脚本来处理 GPU/CPU 依赖
ENTRYPOINT ["./entrypoint.sh"]
