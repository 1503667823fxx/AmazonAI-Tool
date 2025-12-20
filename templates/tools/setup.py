"""
模板库管理系统安装配置
"""

from setuptools import setup, find_packages
import os

# 读取README文件
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), '..', 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "APlus Studio 模板库管理系统"

# 读取依赖
def read_requirements():
    req_path = os.path.join(os.path.dirname(__file__), '..', '..', 'requirements-template-system.txt')
    if os.path.exists(req_path):
        with open(req_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name="aplus-template-system",
    version="1.0.0",
    description="APlus Studio 开发者模板库管理系统",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="APlus Studio Team",
    author_email="dev@aplus-studio.com",
    url="https://github.com/aplus-studio/template-system",
    
    packages=find_packages(),
    include_package_data=True,
    
    install_requires=read_requirements(),
    
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.5.0',
            'pre-commit>=3.0.0'
        ],
        'docs': [
            'sphinx>=7.0.0',
            'sphinx-rtd-theme>=1.3.0'
        ]
    },
    
    entry_points={
        'console_scripts': [
            'template-cli=cli.template_cli:main',
            'template-validator=validators.structure_validator:main',
            'template-generator=generators.template_generator:main'
        ]
    },
    
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Text Processing :: Markup"
    ],
    
    python_requires=">=3.8",
    
    project_urls={
        "Bug Reports": "https://github.com/aplus-studio/template-system/issues",
        "Source": "https://github.com/aplus-studio/template-system",
        "Documentation": "https://aplus-studio.github.io/template-system/"
    }
)