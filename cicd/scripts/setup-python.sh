#!/bin/bash
# Python3 + pip + venv 安装脚本（幂等）
# 用法: bash cicd/scripts/setup-python.sh
# 被 Jenkinsfile.wow-dbc-tool 使用

set -euo pipefail

PYPI_MIRROR="${PYPI_MIRROR:-https://mirrors.cloud.tencent.com/pypi/simple}"
PYPI_HOST="${PYPI_HOST:-mirrors.cloud.tencent.com}"

# ============================
# 1. Python3（Jenkins agent 通常已预装，此处做兜底安装）
# ============================
if ! command -v python3 >/dev/null 2>&1; then
    echo ">>> 未检测到 Python3，尝试安装..."

    if [ "$(id -u)" -eq 0 ]; then
        # root 用户直接安装
        apt-get update -qq
        apt-get install -y -qq python3 python3-pip python3-venv
    elif command -v sudo >/dev/null 2>&1; then
        # 非 root 但拥有 sudo
        sudo apt-get update -qq
        sudo apt-get install -y -qq python3 python3-pip python3-venv
    else
        echo "ERROR: 当前系统未安装 Python3，且无 root/sudo 权限进行安装。"
        echo "       请在 Jenkins agent 镜像中预装 python3，或切换到 root 权限运行。"
        exit 1
    fi
fi
echo "Python3: $(python3 --version)"

# ============================
# 2. pip（升级到最新版，使用镜像源）
# ============================
python3 -m pip install --upgrade pip \
    -i "${PYPI_MIRROR}" --trusted-host "${PYPI_HOST}"
echo "pip: $(python3 -m pip --version)"

# ============================
# 3. 创建 Jenkins 构建专用 venv
# ============================
VENV_DIR="/tmp/jenkins-venv-wow-dbc-tool"

if [ ! -d "${VENV_DIR}" ]; then
    echo ">>> 创建 venv: ${VENV_DIR}"
    python3 -m venv "${VENV_DIR}"
fi

# 每次构建都升级 pip
"${VENV_DIR}/bin/pip" install --upgrade pip \
    -i "${PYPI_MIRROR}" --trusted-host "${PYPI_HOST}"

# 安装构建依赖（提前安装，加速后续 install）
"${VENV_DIR}/bin/pip" install setuptools wheel build \
    -i "${PYPI_MIRROR}" --trusted-host "${PYPI_HOST}"

echo "venv pip: $(${VENV_DIR}/bin/pip --version)"

# ============================
# 4. 设置环境变量（供 Jenkinsfile 使用）
# ============================
echo "PYTHON=${VENV_DIR}/bin/python" >> .env.pipeline
echo "PIP=${VENV_DIR}/bin/pip"       >> .env.pipeline

# ============================
# 5. 跨 shell 验证
# ============================
echo "=== 跨 shell 验证 ==="
/bin/sh -c "${VENV_DIR}/bin/python --version" \
    && echo "python 在 /bin/sh 可用" \
    || { echo "python 在 /bin/sh 不可用"; exit 1; }
