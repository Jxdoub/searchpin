# ── Searchpin Docker Image ────────────────────────────────
# Multi-stage: build in context, ship a lean runtime.
# 修改说明：新增 supergateway（stdio → Streamable HTTP 桥接），
# 使容器能通过 HTTP 端口暴露 MCP 服务（云端 / Railway 可达）。
# 原 searchpin python 构建逻辑保持不变。

FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
COPY searchpin/ ./searchpin/
COPY search_server.py ./

# 嵌入模型下载端点：构建时预下载 ~470MB 模型并烘焙进镜像。
# 云端构建机通常在海外，默认官方 huggingface.co 可达；
# 国内本地构建可用 --build-arg HF_ENDPOINT=https://hf-mirror.com 覆盖。
# HF_HUB_DISABLE_XET=1：兼容 hf-mirror（不支持 xet 传输协议），对官方源也无害。
ARG HF_ENDPOINT=https://huggingface.co
ENV HF_ENDPOINT=${HF_ENDPOINT}
ENV HF_HUB_DISABLE_XET=1

# Install dependencies and pre-download the embedding model.
# Model is baked into the image — zero delay on first container start.
RUN pip install --no-cache-dir . && \
    HF_ENDPOINT=${HF_ENDPOINT} searchpin-setup

# ── Node builder: supergateway bridge (stdio → Streamable HTTP) ──
FROM node:20-slim AS bridge-builder

RUN npm install -g supergateway@3.4.3

# ── Runtime stage ─────────────────────────────────────────
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface

# Node runtime + supergateway 桥接
COPY --from=bridge-builder /usr/local/bin/node /usr/local/bin/node
COPY --from=bridge-builder /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf /usr/local/lib/node_modules/.bin/supergateway /usr/local/bin/supergateway

ENV SEARCHPIN_TIMING_LOG=""

# Streamable HTTP MCP 端点（默认 /mcp）；健康检查 /healthz
# 云端（Railway 等）需监听其注入的 $PORT 环境变量
EXPOSE 8000
CMD ["sh", "-c", "supergateway --stdio searchpin-server --outputTransport streamableHttp --port ${PORT:-8000} --streamableHttpPath /mcp --healthEndpoint /healthz"]
