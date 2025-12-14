#!/usr/bin/env python3
"""
Amazon AI Hub - 简单依赖检查脚本
检查项目运行所需的基础依赖
"""

def check_dependencies():
    """检查基础依赖是否安装"""
    print("🔍 Amazon AI Hub - 依赖检查")
    print("=" * 40)
    
    required_packages = [
        "streamlit",
        "google-generativeai", 
        "pillow",
        "requests"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - 未安装")
            missing_packages.append(package)
    
    print("\n" + "=" * 40)
    
    if missing_packages:
        print("⚠️  发现缺失依赖，请运行以下命令安装：")
        print(f"pip install {' '.join(missing_packages)}")
    else:
        print("🎉 所有依赖都已安装！")
        print("💡 运行命令启动应用：streamlit run Home.py")

if __name__ == "__main__":
    check_dependencies()
