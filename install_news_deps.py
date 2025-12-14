#!/usr/bin/env python3
"""
Amazon AI Hub - 依赖安装和检查脚本
"""

import subprocess
import sys

def install_package(package):
    """安装Python包"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def check_and_install():
    """检查并安装依赖"""
    print("🔍 Amazon AI Hub - 依赖检查与安装")
    print("=" * 50)
    
    # 基础依赖
    required_packages = [
        "streamlit",
        "google-generativeai", 
        "pillow",
        "requests"
    ]
    
    # 可选依赖
    optional_packages = [
        "feedparser"  # RSS资讯功能
    ]
    
    print("📦 检查基础依赖...")
    missing_basic = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - 未安装")
            missing_basic.append(package)
    
    print("\n📦 检查可选依赖...")
    missing_optional = []
    
    for package in optional_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package} - RSS资讯功能可用")
        except ImportError:
            print(f"⚠️  {package} - 未安装 (RSS资讯功能不可用)")
            missing_optional.append(package)
    
    print("\n" + "=" * 50)
    
    # 安装缺失的依赖
    if missing_basic:
        print("🚨 发现缺失的基础依赖，正在安装...")
        for package in missing_basic:
            print(f"📦 正在安装 {package}...")
            if install_package(package):
                print(f"✅ {package} 安装成功")
            else:
                print(f"❌ {package} 安装失败")
    
    if missing_optional:
        print("💡 发现缺失的可选依赖，正在安装...")
        for package in missing_optional:
            print(f"📦 正在安装 {package}...")
            if install_package(package):
                print(f"✅ {package} 安装成功 - RSS资讯功能已启用")
            else:
                print(f"⚠️  {package} 安装失败 - RSS资讯功能将使用备用方案")
    
    if not missing_basic and not missing_optional:
        print("🎉 所有依赖都已安装！")
    
    print("\n💡 启动应用：streamlit run Home.py")

if __name__ == "__main__":
    check_and_install()
