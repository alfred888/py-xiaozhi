#!/bin/bash

# 设置颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查操作系统类型
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo -e "${YELLOW}检测到 macOS 系统，正在安装系统依赖...${NC}"
    if ! command -v brew &> /dev/null; then
        echo -e "${RED}未找到 Homebrew，请先安装 Homebrew${NC}"
        echo -e "${YELLOW}安装命令：/bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"${NC}"
        exit 1
    fi
    brew install portaudio
    REQUIREMENTS_FILE="requirements_mac.txt"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    echo -e "${YELLOW}检测到 Linux 系统，正在安装系统依赖...${NC}"
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y portaudio19-dev python3-pyaudio
    elif command -v yum &> /dev/null; then
        sudo yum install -y portaudio-devel python3-pyaudio
    else
        echo -e "${RED}不支持的 Linux 发行版${NC}"
        exit 1
    fi
    REQUIREMENTS_FILE="requirements.txt"
fi

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}虚拟环境不存在，正在创建...${NC}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}创建虚拟环境失败，请确保已安装 python3-venv${NC}"
        exit 1
    fi
    echo -e "${GREEN}虚拟环境创建成功${NC}"
fi

# 激活虚拟环境
echo -e "${YELLOW}正在激活虚拟环境...${NC}"
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}激活虚拟环境失败${NC}"
    exit 1
fi

# 升级 pip
echo -e "${YELLOW}正在升级 pip...${NC}"
pip install --upgrade pip

# 安装依赖
echo -e "${YELLOW}正在安装依赖...${NC}"
pip install -r $REQUIREMENTS_FILE
if [ $? -ne 0 ]; then
    echo -e "${RED}安装依赖失败${NC}"
    exit 1
fi

# 启动程序
echo -e "${GREEN}正在启动程序...${NC}"
python main.py

# 程序结束后，退出虚拟环境
deactivate 