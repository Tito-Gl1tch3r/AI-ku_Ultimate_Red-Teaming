#!/bin/bash

# JS Cookie Monitor Debugger Hook - 一键构建脚本
# 用于编译打包油猴插件
# 使用方式：chmod +x ./build.sh && ./build.sh

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_step() {
    echo -e "${BLUE}🔄 $1${NC}"
}

# 检查Node.js环境
check_node() {
    print_step "检查Node.js环境..."
    
    if ! command -v node &> /dev/null; then
        print_error "未检测到Node.js，请先安装Node.js"
        exit 1
    fi
    
    NODE_VERSION=$(node --version)
    print_success "Node.js版本: $NODE_VERSION"
}

# 检查包管理器并安装依赖
check_dependencies() {
    print_step "检查依赖..."
    
    # 检查node_modules是否存在
    if [ ! -d "node_modules" ]; then
        print_warning "未检测到node_modules目录，开始安装依赖..."
        install_dependencies
    else
        print_success "依赖已安装"
    fi
}

# 安装依赖
install_dependencies() {
    if command -v yarn &> /dev/null && [ -f "yarn.lock" ]; then
        print_step "使用yarn安装依赖..."
        yarn install --frozen-lockfile
    elif command -v npm &> /dev/null; then
        print_step "使用npm安装依赖..."
        npm ci
    else
        print_error "未检测到yarn或npm，请先安装Node.js包管理器"
        exit 1
    fi
    print_success "依赖安装完成"
}

# 清理旧的构建文件
clean_build() {
    print_step "清理旧的构建文件..."
    
    if [ -d "dist" ]; then
        rm -rf dist
        print_success "已清理dist目录"
    fi
}

# 执行构建
build_project() {
    print_step "开始构建项目..."
    
    # 检测使用哪个包管理器
    if command -v yarn &> /dev/null && [ -f "yarn.lock" ]; then
        BUILD_CMD="yarn build"
    else
        BUILD_CMD="npm run build"
    fi
    
    print_info "执行构建命令: $BUILD_CMD"
    
    if $BUILD_CMD; then
        print_success "项目构建成功"
    else
        print_error "项目构建失败"
        exit 1
    fi
}

# 检查构建结果
check_build_result() {
    print_step "检查构建结果..."
    
    if [ ! -f "dist/index.js" ]; then
        print_error "构建失败：未找到dist/index.js文件"
        exit 1
    fi
    
    FILE_SIZE=$(du -h "dist/index.js" | cut -f1)
    print_success "构建文件: dist/index.js (大小: $FILE_SIZE)"
    
    # 检查文件是否包含UserScript头部
    if grep -q "==UserScript==" "dist/index.js"; then
        print_success "UserScript头部检查通过"
    else
        print_warning "警告：未检测到UserScript头部，请检查配置"
    fi
}

# 显示使用说明
show_usage() {
    print_success "构建完成！"
    echo ""
    print_info "使用说明："
    echo "  1. 打开Tampermonkey扩展"
    echo "  2. 点击'添加新脚本'"
    echo "  3. 复制 dist/index.js 的内容到编辑器中"
    echo "  4. 保存并启用脚本"
    echo ""
    print_info "开发调试："
    echo "  运行 'npm run dev-headers' 生成开发调试头部文件"
    echo "  使用 dev-header.js 进行本地开发调试"
}

# 主函数
main() {
    echo "=================================================="
    print_info "JS Cookie Monitor Debugger Hook - 构建脚本"
    echo "=================================================="
    echo ""
    
    check_node
    check_dependencies
    clean_build
    build_project
    check_build_result
    show_usage
    
    echo ""
    print_success "🎉 构建流程完成！"
}

# 执行主函数
main "$@"
