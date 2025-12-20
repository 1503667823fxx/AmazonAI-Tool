"""
AI处理状态界面组件
实现AI处理进度显示和状态更新功能
"""

import streamlit as st
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import time
import json

from ..interfaces import IGeminiAPIClient, IImageCompositor
from ..models.core_models import ProductData, Template


class AIProcessingTask:
    """AI处理任务数据类"""
    
    def __init__(self, task_id: str, task_type: str, description: str):
        self.task_id = task_id
        self.task_type = task_type
        self.description = description
        self.status = "pending"  # pending, processing, completed, failed
        self.progress = 0.0
        self.start_time = None
        self.end_time = None
        self.result_data = None
        self.error_message = None
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "description": self.description,
            "status": self.status,
            "progress": self.progress,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "result_data": self.result_data,
            "error_message": self.error_message
        }


class AIStatusUI:
    """AI处理状态界面组件"""
    
    def __init__(self, 
                 gemini_client: IGeminiAPIClient,
                 image_compositor: IImageCompositor):
        """
        初始化AI状态界面
        
        Args:
            gemini_client: Gemini API客户端
            image_compositor: 图片合成器
        """
        self.gemini_client = gemini_client
        self.image_compositor = image_compositor
        
    def render(self, 
               template: Template,
               product_data: ProductData,
               customization_options: Dict[str, Any]) -> Dict[str, Any]:
        """
        渲染AI处理状态界面
        
        Args:
            template: 选中的模板
            product_data: 产品数据
            customization_options: 自定义选项
            
        Returns:
            处理结果信息
        """
        st.markdown("### 🤖 AI智能处理")
        
        # 获取或创建处理任务
        tasks = self._get_or_create_tasks(template, product_data, customization_options)
        
        # 渲染任务列表
        self._render_task_list(tasks)
        
        # 渲染总体进度
        overall_progress = self._render_overall_progress(tasks)
        
        # 渲染控制按钮
        control_result = self._render_control_buttons(tasks)
        
        # 处理任务执行
        if control_result.get("start_processing"):
            self._start_processing(tasks)
        elif control_result.get("pause_processing"):
            self._pause_processing(tasks)
        elif control_result.get("retry_failed"):
            self._retry_failed_tasks(tasks)
        
        # 渲染结果预览
        results = self._render_results_preview(tasks)
        
        return {
            "overall_progress": overall_progress,
            "tasks": [task.to_dict() for task in tasks],
            "results": results,
            "is_completed": all(task.status == "completed" for task in tasks),
            "has_errors": any(task.status == "failed" for task in tasks)
        }
    
    def _get_or_create_tasks(self, 
                           template: Template,
                           product_data: ProductData,
                           customization_options: Dict[str, Any]) -> List[AIProcessingTask]:
        """获取或创建处理任务"""
        # 检查会话中是否已有任务
        if 'ai_processing_tasks' in st.session_state:
            # 从会话状态恢复任务
            tasks_data = st.session_state.ai_processing_tasks
            tasks = []
            for task_data in tasks_data:
                task = AIProcessingTask(
                    task_data["task_id"],
                    task_data["task_type"], 
                    task_data["description"]
                )
                task.status = task_data["status"]
                task.progress = task_data["progress"]
                task.start_time = datetime.fromisoformat(task_data["start_time"]) if task_data["start_time"] else None
                task.end_time = datetime.fromisoformat(task_data["end_time"]) if task_data["end_time"] else None
                task.result_data = task_data["result_data"]
                task.error_message = task_data["error_message"]
                tasks.append(task)
            return tasks
        
        # 创建新任务
        tasks = []
        
        # 任务1: 模板分析
        tasks.append(AIProcessingTask(
            "template_analysis",
            "analysis",
            "分析模板结构和可替换区域"
        ))
        
        # 任务2: 产品图片处理
        for i, image in enumerate(product_data.images):
            tasks.append(AIProcessingTask(
                f"image_processing_{i}",
                "image_processing",
                f"处理产品图片 {i+1}: {image.filename}"
            ))
        
        # 任务3: 文案优化
        if customization_options.get("ai_enhance_text"):
            tasks.append(AIProcessingTask(
                "text_enhancement",
                "text_processing",
                "AI优化产品文案和描述"
            ))
        
        # 任务4: 图片合成
        for section in template.sections:
            tasks.append(AIProcessingTask(
                f"composition_{section}",
                "image_composition",
                f"合成{section}模块"
            ))
        
        # 任务5: 背景生成（如果启用）
        if customization_options.get("ai_background_gen"):
            tasks.append(AIProcessingTask(
                "background_generation",
                "background_gen",
                "AI生成背景元素"
            ))
        
        # 任务6: 最终优化
        tasks.append(AIProcessingTask(
            "final_optimization",
            "optimization",
            "最终效果优化和质量检查"
        ))
        
        # 保存到会话状态
        st.session_state.ai_processing_tasks = [task.to_dict() for task in tasks]
        
        return tasks
    
    def _render_task_list(self, tasks: List[AIProcessingTask]):
        """渲染任务列表"""
        st.markdown("**处理任务:**")
        
        for task in tasks:
            with st.container():
                col_icon, col_desc, col_progress, col_status = st.columns([0.5, 3, 1.5, 1])
                
                with col_icon:
                    # 任务状态图标
                    if task.status == "completed":
                        st.markdown("✅")
                    elif task.status == "processing":
                        st.markdown("🔄")
                    elif task.status == "failed":
                        st.markdown("❌")
                    else:
                        st.markdown("⭕")
                
                with col_desc:
                    st.markdown(f"**{task.description}**")
                    if task.error_message:
                        st.error(f"错误: {task.error_message}")
                
                with col_progress:
                    if task.status == "processing":
                        st.progress(task.progress)
                        st.caption(f"{task.progress*100:.0f}%")
                    elif task.status == "completed":
                        st.progress(1.0)
                        st.caption("完成")
                    elif task.status == "failed":
                        st.progress(0.0)
                        st.caption("失败")
                    else:
                        st.progress(0.0)
                        st.caption("等待中")
                
                with col_status:
                    # 任务时间信息
                    if task.start_time:
                        if task.end_time:
                            duration = task.end_time - task.start_time
                            st.caption(f"用时: {duration.total_seconds():.1f}s")
                        else:
                            elapsed = datetime.now() - task.start_time
                            st.caption(f"已用: {elapsed.total_seconds():.1f}s")
    
    def _render_overall_progress(self, tasks: List[AIProcessingTask]) -> float:
        """渲染总体进度"""
        if not tasks:
            return 0.0
        
        # 计算总体进度
        total_progress = sum(task.progress for task in tasks if task.status != "failed")
        completed_tasks = sum(1 for task in tasks if task.status == "completed")
        failed_tasks = sum(1 for task in tasks if task.status == "failed")
        
        overall_progress = total_progress / len(tasks)
        
        # 显示总体进度条
        st.markdown("**总体进度:**")
        st.progress(overall_progress)
        
        # 进度统计
        col_stats1, col_stats2, col_stats3 = st.columns(3)
        
        with col_stats1:
            st.metric("完成任务", f"{completed_tasks}/{len(tasks)}")
        
        with col_stats2:
            st.metric("总体进度", f"{overall_progress*100:.1f}%")
        
        with col_stats3:
            if failed_tasks > 0:
                st.metric("失败任务", failed_tasks, delta=f"-{failed_tasks}")
            else:
                st.metric("状态", "正常" if overall_progress < 1.0 else "完成")
        
        return overall_progress
    
    def _render_control_buttons(self, tasks: List[AIProcessingTask]) -> Dict[str, bool]:
        """渲染控制按钮"""
        st.markdown("---")
        
        col_start, col_pause, col_retry, col_cancel = st.columns(4)
        
        result = {}
        
        with col_start:
            # 开始/继续处理按钮
            has_pending = any(task.status == "pending" for task in tasks)
            has_processing = any(task.status == "processing" for task in tasks)
            
            if has_pending and not has_processing:
                if st.button("🚀 开始处理", type="primary"):
                    result["start_processing"] = True
            elif has_processing:
                st.button("🔄 处理中...", disabled=True)
            else:
                st.button("✅ 已完成", disabled=True)
        
        with col_pause:
            # 暂停按钮
            if any(task.status == "processing" for task in tasks):
                if st.button("⏸️ 暂停"):
                    result["pause_processing"] = True
        
        with col_retry:
            # 重试失败任务按钮
            failed_tasks = [task for task in tasks if task.status == "failed"]
            if failed_tasks:
                if st.button(f"🔄 重试失败 ({len(failed_tasks)})"):
                    result["retry_failed"] = True
        
        with col_cancel:
            # 取消按钮
            if any(task.status in ["pending", "processing"] for task in tasks):
                if st.button("❌ 取消"):
                    result["cancel_processing"] = True
        
        return result
    
    def _render_results_preview(self, tasks: List[AIProcessingTask]) -> Dict[str, Any]:
        """渲染结果预览"""
        completed_tasks = [task for task in tasks if task.status == "completed" and task.result_data]
        
        if not completed_tasks:
            return {}
        
        st.markdown("### 🎨 处理结果预览")
        
        results = {}
        
        # 按任务类型组织结果
        for task in completed_tasks:
            if task.task_type == "image_composition":
                # 显示合成的图片模块
                with st.expander(f"📋 {task.description}", expanded=True):
                    # 模拟显示结果图片
                    result_url = f"https://via.placeholder.com/800x300/4CAF50/white?text={task.description.replace(' ', '+')}"
                    st.image(result_url, caption=task.description, use_container_width=True)
                    
                    # 下载按钮
                    if st.button(f"📥 下载", key=f"download_{task.task_id}"):
                        st.success("下载功能将在完整版本中实现")
                
                results[task.task_id] = {"type": "image", "url": result_url}
            
            elif task.task_type == "text_processing":
                # 显示优化后的文案
                with st.expander("📝 优化文案", expanded=False):
                    optimized_text = task.result_data.get("optimized_text", "优化后的产品文案...")
                    st.markdown(optimized_text)
                
                results[task.task_id] = {"type": "text", "content": optimized_text}
        
        # 显示下载选项
        if len(completed_tasks) > 1:
            st.markdown("**批量下载:**")
            
            col_download1, col_download2 = st.columns(2)
            
            with col_download1:
                if st.button("📦 下载所有图片"):
                    st.success("批量下载功能将在完整版本中实现")
            
            with col_download2:
                if st.button("📄 生成报告"):
                    self._generate_processing_report(tasks)
        
        return results
    
    def _start_processing(self, tasks: List[AIProcessingTask]):
        """开始处理任务"""
        # 找到第一个待处理的任务
        for task in tasks:
            if task.status == "pending":
                task.status = "processing"
                task.start_time = datetime.now()
                task.progress = 0.0
                
                # 模拟处理过程
                self._simulate_task_processing(task)
                break
        
        # 更新会话状态
        st.session_state.ai_processing_tasks = [task.to_dict() for task in tasks]
        st.rerun()
    
    def _simulate_task_processing(self, task: AIProcessingTask):
        """模拟任务处理过程"""
        # 这里应该调用实际的AI处理逻辑
        # 现在使用模拟处理
        
        try:
            if task.task_type == "analysis":
                # 模拟模板分析
                time.sleep(0.1)
                task.progress = 1.0
                task.status = "completed"
                task.end_time = datetime.now()
                task.result_data = {"analysis": "模板分析完成"}
            
            elif task.task_type == "image_processing":
                # 模拟图片处理
                time.sleep(0.1)
                task.progress = 1.0
                task.status = "completed"
                task.end_time = datetime.now()
                task.result_data = {"processed_image": "处理后的图片数据"}
            
            elif task.task_type == "text_processing":
                # 模拟文案优化
                time.sleep(0.1)
                task.progress = 1.0
                task.status = "completed"
                task.end_time = datetime.now()
                task.result_data = {
                    "optimized_text": "经过AI优化的产品文案，突出产品特色和优势..."
                }
            
            elif task.task_type == "image_composition":
                # 模拟图片合成
                time.sleep(0.1)
                task.progress = 1.0
                task.status = "completed"
                task.end_time = datetime.now()
                task.result_data = {"composed_image": "合成后的图片数据"}
            
            else:
                # 其他任务类型
                time.sleep(0.1)
                task.progress = 1.0
                task.status = "completed"
                task.end_time = datetime.now()
                task.result_data = {"result": "处理完成"}
                
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            task.end_time = datetime.now()
    
    def _pause_processing(self, tasks: List[AIProcessingTask]):
        """暂停处理"""
        for task in tasks:
            if task.status == "processing":
                task.status = "pending"
        
        st.session_state.ai_processing_tasks = [task.to_dict() for task in tasks]
        st.success("处理已暂停")
    
    def _retry_failed_tasks(self, tasks: List[AIProcessingTask]):
        """重试失败的任务"""
        for task in tasks:
            if task.status == "failed":
                task.status = "pending"
                task.progress = 0.0
                task.error_message = None
                task.start_time = None
                task.end_time = None
        
        st.session_state.ai_processing_tasks = [task.to_dict() for task in tasks]
        st.success("失败任务已重置，可以重新开始处理")
    
    def _generate_processing_report(self, tasks: List[AIProcessingTask]):
        """生成处理报告"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_tasks": len(tasks),
            "completed_tasks": len([t for t in tasks if t.status == "completed"]),
            "failed_tasks": len([t for t in tasks if t.status == "failed"]),
            "tasks": [task.to_dict() for task in tasks]
        }
        
        report_json = json.dumps(report, indent=2, ensure_ascii=False)
        
        st.download_button(
            "📊 下载处理报告",
            data=report_json,
            file_name=f"ai_processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    def render_compact(self, 
                      template: Template,
                      product_data: ProductData,
                      customization_options: Dict[str, Any]) -> Dict[str, Any]:
        """
        渲染紧凑版AI状态界面
        
        Returns:
            处理状态信息
        """
        tasks = self._get_or_create_tasks(template, product_data, customization_options)
        
        # 简化的进度显示
        completed = len([t for t in tasks if t.status == "completed"])
        total = len(tasks)
        progress = completed / total if total > 0 else 0
        
        st.progress(progress)
        st.caption(f"AI处理进度: {completed}/{total}")
        
        # 当前处理任务
        current_task = next((t for t in tasks if t.status == "processing"), None)
        if current_task:
            st.info(f"🔄 {current_task.description}")
        elif progress == 1.0:
            st.success("✅ AI处理完成")
        
        return {
            "progress": progress,
            "completed": completed,
            "total": total,
            "is_completed": progress == 1.0
        }