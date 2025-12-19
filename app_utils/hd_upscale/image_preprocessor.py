# app_utils/hd_upscale/image_preprocessor.py
from PIL import Image
import io
import streamlit as st

class ImagePreprocessor:
    """图片预处理器，优化SUPIR模型的输入"""
    
    @staticmethod
    def optimize_for_supir(uploaded_file, max_size_mb=5, max_dimension=2048):
        """
        为SUPIR模型优化图片
        :param uploaded_file: Streamlit上传的文件
        :param max_size_mb: 最大文件大小(MB)
        :param max_dimension: 最大尺寸(像素)
        :return: 优化后的文件对象
        """
        try:
            # 读取图片
            image = Image.open(uploaded_file)
            original_format = image.format
            
            # 获取原始信息
            original_size = len(uploaded_file.getvalue()) / (1024 * 1024)  # MB
            original_width, original_height = image.size
            
            # 检查是否需要优化
            needs_resize = (original_width > max_dimension or 
                          original_height > max_dimension or 
                          original_size > max_size_mb)
            
            if not needs_resize:
                # 不需要优化，返回原文件
                uploaded_file.seek(0)
                return uploaded_file, False, {
                    'original_size': f"{original_size:.1f}MB",
                    'original_dimensions': f"{original_width}x{original_height}",
                    'optimized': False
                }
            
            # 需要优化
            # 1. 调整尺寸
            if original_width > max_dimension or original_height > max_dimension:
                # 保持宽高比
                ratio = min(max_dimension / original_width, max_dimension / original_height)
                new_width = int(original_width * ratio)
                new_height = int(original_height * ratio)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 2. 转换格式和压缩
            if image.mode in ('RGBA', 'P'):
                # 处理透明通道
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            # 3. 保存优化后的图片
            output_buffer = io.BytesIO()
            
            # 根据目标大小调整质量
            quality = 85
            while True:
                output_buffer.seek(0)
                output_buffer.truncate()
                image.save(output_buffer, format='JPEG', quality=quality, optimize=True)
                
                current_size = len(output_buffer.getvalue()) / (1024 * 1024)
                if current_size <= max_size_mb or quality <= 60:
                    break
                quality -= 5
            
            # 创建新的文件对象
            output_buffer.seek(0)
            optimized_file = io.BytesIO(output_buffer.getvalue())
            optimized_file.name = f"optimized_{uploaded_file.name}"
            
            return optimized_file, True, {
                'original_size': f"{original_size:.1f}MB",
                'original_dimensions': f"{original_width}x{original_height}",
                'optimized_size': f"{current_size:.1f}MB",
                'optimized_dimensions': f"{image.width}x{image.height}",
                'quality': quality,
                'optimized': True
            }
            
        except Exception as e:
            st.error(f"图片预处理失败: {str(e)}")
            uploaded_file.seek(0)
            return uploaded_file, False, {'error': str(e)}
    
    @staticmethod
    def show_optimization_info(info):
        """显示优化信息"""
        if info.get('error'):
            st.error(f"预处理错误: {info['error']}")
            return
            
        if info['optimized']:
            st.info(f"""
            📊 **图片已优化以提高处理成功率**
            
            **原始**: {info['original_size']} | {info['original_dimensions']}
            **优化后**: {info['optimized_size']} | {info['optimized_dimensions']}
            **压缩质量**: {info['quality']}%
            
            💡 优化有助于避免内存错误，提高SUPIR处理成功率
            """)
        else:
            st.success(f"""
            ✅ **图片无需优化**
            
            **大小**: {info['original_size']} | **尺寸**: {info['original_dimensions']}
            
            图片已符合SUPIR模型的最佳处理条件
            """)
