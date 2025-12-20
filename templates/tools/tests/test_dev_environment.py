"""
Streamlit环境测试
验证Streamlit环境配置是否正确
"""

import sys
from pathlib import Path


class TestStreamlitEnvironment:
    """Streamlit环境测试类"""
    
    def test_python_version(self):
        """测试Python版本要求"""
        version = sys.version_info
        assert version.major == 3, f"需要Python 3.x，当前版本: {version.major}"
        assert version.minor >= 8, f"需要Python 3.8+，当前版本: {version.major}.{version.minor}"
    
    def test_project_structure(self):
        """测试项目结构"""
        project_root = Path(__file__).parent.parent.parent
        
        # 检查关键目录
        required_dirs = [
            "templates",
            "templates/tools",
            "templates/tools/models",
            "templates/tools/validators", 
            "templates/tools/cli",
            "templates/tools/schemas",
            "templates/config",
            "templates/index",
            ".streamlit"
        ]
        
        for dir_path in required_dirs:
            full_path = project_root / dir_path
            assert full_path.exists(), f"缺少目录: {dir_path}"
            assert full_path.is_dir(), f"路径不是目录: {dir_path}"
    
    def test_streamlit_configuration_files(self):
        """测试Streamlit配置文件"""
        project_root = Path(__file__).parent.parent.parent
        
        # 检查Streamlit配置文件
        required_files = [
            ".streamlit/config.toml",
            ".streamlit/secrets.toml",
            "requirements.txt",
            "Makefile",
            "tools/config.py",
            "tools/streamlit_utils.py"
        ]
        
        for file_path in required_files:
            full_path = project_root / file_path
            assert full_path.exists(), f"缺少配置文件: {file_path}"
            assert full_path.is_file(), f"路径不是文件: {file_path}"
    
    def test_validator_imports(self):
        """测试验证器模块导入"""
        try:
            from tools.validators import ConfigValidator, StructureValidator, ImageValidator
            
            # 测试配置验证器
            validator = ConfigValidator()
            assert validator is not None
            
            # 测试结构验证器
            validator = StructureValidator()
            assert validator is not None
            
            # 测试图片验证器
            validator = ImageValidator()
            assert validator is not None
            
        except ImportError as e:
            assert False, f"验证器模块导入失败: {e}"
    
    def test_config_module(self):
        """测试配置模块"""
        try:
            from tools.config import get_config, Config
            
            config = get_config()
            assert config is not None
            assert isinstance(config, Config)
            
            # 测试基本配置获取
            debug_mode = config.is_debug_mode()
            assert isinstance(debug_mode, bool)
            
            max_size = config.get_max_file_size()
            assert isinstance(max_size, int)
            assert max_size > 0
            
        except ImportError as e:
            assert False, f"配置模块导入失败: {e}"
    
    def test_streamlit_utils(self):
        """测试Streamlit工具模块"""
        try:
            from tools.streamlit_utils import validate_environment, load_yaml_file, load_json_file
            
            # 测试环境验证函数
            results = validate_environment()
            assert isinstance(results, dict)
            
        except ImportError as e:
            assert False, f"Streamlit工具模块导入失败: {e}"
    
    def test_cli_tool_structure(self):
        """测试CLI工具结构"""
        cli_dir = Path(__file__).parent.parent / "cli"
        
        assert cli_dir.exists(), "CLI目录不存在"
        assert (cli_dir / "__init__.py").exists(), "CLI模块初始化文件不存在"
        assert (cli_dir / "template_cli.py").exists(), "CLI主文件不存在"
    
    def test_schema_files(self):
        """测试Schema文件"""
        schemas_dir = Path(__file__).parent.parent / "schemas"
        
        assert schemas_dir.exists(), "Schemas目录不存在"
        assert (schemas_dir / "template_config_schema.json").exists(), "模板配置Schema不存在"
    
    def test_template_config_structure(self):
        """测试模板配置结构"""
        config_dir = Path(__file__).parent.parent.parent / "templates" / "config"
        
        required_config_files = [
            "categories.yaml",
            "template_types.yaml", 
            "validation_rules.yaml",
            "global_settings.yaml"
        ]
        
        for config_file in required_config_files:
            full_path = config_dir / config_file
            assert full_path.exists(), f"缺少配置文件: {config_file}"


class TestStreamlitIntegration:
    """Streamlit集成测试"""
    
    def test_import_all_modules(self):
        """测试所有模块导入"""
        try:
            from tools.models import Template, TemplateConfig, FileStructure
            from tools.validators import ConfigValidator, StructureValidator, ImageValidator
            from tools.config import get_config
            from tools.streamlit_utils import validate_environment
        except ImportError as e:
            assert False, f"模块导入失败: {e}"
    
    def test_basic_functionality(self):
        """测试基本功能"""
        try:
            # 测试配置管理
            from tools.config import get_config
            config = get_config()
            
            # 测试图片尺寸配置
            desktop_size = config.get_image_size('desktop')
            assert len(desktop_size) == 2
            assert desktop_size[0] > 0 and desktop_size[1] > 0
            
            mobile_size = config.get_image_size('mobile')
            assert len(mobile_size) == 2
            assert mobile_size[0] > 0 and mobile_size[1] > 0
            
            # 测试路径配置
            templates_path = config.get_path('templates_root')
            assert isinstance(templates_path, Path)
            
        except Exception as e:
            assert False, f"基本功能测试失败: {e}"


def run_simple_test():
    """运行简单测试（不依赖pytest）"""
    print("🧪 运行Streamlit环境简单测试...")
    
    tests = [
        ("Python版本", lambda: sys.version_info.major == 3 and sys.version_info.minor >= 8),
        ("项目目录", lambda: Path("tools").exists() and Path("templates").exists()),
        ("Streamlit配置", lambda: Path(".streamlit/config.toml").exists()),
        ("配置模块", lambda: __import__("tools.config") is not None),
        ("验证器模块", lambda: __import__("tools.validators") is not None)
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {name}")
                passed += 1
            else:
                print(f"❌ {name}")
        except Exception as e:
            print(f"❌ {name}: {e}")
    
    print(f"\n测试结果: {passed}/{total} 通过")
    return passed == total


if __name__ == "__main__":
    # 如果pytest可用，使用pytest运行
    try:
        import pytest
        pytest.main([__file__, "-v"])
    except ImportError:
        # 否则运行简单测试
        success = run_simple_test()
        sys.exit(0 if success else 1)