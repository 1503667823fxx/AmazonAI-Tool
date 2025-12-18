"""
Logging Configuration for Video Studio

This module provides centralized logging configuration and utilities for the video studio system.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum


class LogLevel(Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class VideoStudioFormatter(logging.Formatter):
    """Custom formatter for Video Studio logs"""
    
    def __init__(self):
        super().__init__()
        self.formatters = {
            logging.DEBUG: logging.Formatter(
                '%(asctime)s - %(name)s - DEBUG - %(message)s - [%(filename)s:%(lineno)d]'
            ),
            logging.INFO: logging.Formatter(
                '%(asctime)s - %(name)s - INFO - %(message)s'
            ),
            logging.WARNING: logging.Formatter(
                '%(asctime)s - %(name)s - WARNING - %(message)s - [%(filename)s:%(lineno)d]'
            ),
            logging.ERROR: logging.Formatter(
                '%(asctime)s - %(name)s - ERROR - %(message)s - [%(filename)s:%(lineno)d]'
            ),
            logging.CRITICAL: logging.Formatter(
                '%(asctime)s - %(name)s - CRITICAL - %(message)s - [%(filename)s:%(lineno)d]'
            )
        }
    
    def format(self, record):
        formatter = self.formatters.get(record.levelno, self.formatters[logging.INFO])
        return formatter.format(record)


class VideoStudioLogger:
    """Centralized logger for Video Studio"""
    
    def __init__(self, name: str = "video_studio"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self._handlers_configured = False
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup logging handlers"""
        if self._handlers_configured:
            return
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(VideoStudioFormatter())
        self.logger.addHandler(console_handler)
        
        # File handler
        log_dir = Path("./logs")
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"video_studio_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(VideoStudioFormatter())
        self.logger.addHandler(file_handler)
        
        # Error file handler
        error_log_file = log_dir / f"video_studio_errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(VideoStudioFormatter())
        self.logger.addHandler(error_handler)
        
        self._handlers_configured = True
    
    def set_level(self, level: str):
        """Set logging level"""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        
        if level in level_map:
            self.logger.setLevel(level_map[level])
            # Also update console handler level
            for handler in self.logger.handlers:
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                    handler.setLevel(level_map[level])
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log debug message"""
        self.logger.debug(message, extra=extra or {})
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log info message"""
        self.logger.info(message, extra=extra or {})
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log warning message"""
        self.logger.warning(message, extra=extra or {})
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False):
        """Log error message"""
        self.logger.error(message, extra=extra or {}, exc_info=exc_info)
    
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False):
        """Log critical message"""
        self.logger.critical(message, extra=extra or {}, exc_info=exc_info)
    
    def log_task_start(self, task_id: str, task_type: str, details: Optional[Dict[str, Any]] = None):
        """Log task start"""
        extra = {"task_id": task_id, "task_type": task_type}
        if details:
            extra.update(details)
        self.info(f"Task started: {task_type} (ID: {task_id})", extra=extra)
    
    def log_task_progress(self, task_id: str, progress: float, message: Optional[str] = None):
        """Log task progress"""
        extra = {"task_id": task_id, "progress": progress}
        msg = f"Task progress: {progress:.1%} (ID: {task_id})"
        if message:
            msg += f" - {message}"
        self.info(msg, extra=extra)
    
    def log_task_complete(self, task_id: str, duration_seconds: float, result: Optional[Dict[str, Any]] = None):
        """Log task completion"""
        extra = {"task_id": task_id, "duration": duration_seconds}
        if result:
            extra.update(result)
        self.info(f"Task completed: {task_id} (Duration: {duration_seconds:.2f}s)", extra=extra)
    
    def log_task_error(self, task_id: str, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Log task error"""
        extra = {"task_id": task_id, "error_type": type(error).__name__}
        if context:
            extra.update(context)
        self.error(f"Task failed: {task_id} - {str(error)}", extra=extra, exc_info=True)
    
    def log_model_call(self, model_name: str, operation: str, duration_seconds: Optional[float] = None, 
                      success: bool = True, error: Optional[str] = None):
        """Log model API call"""
        extra = {
            "model_name": model_name,
            "operation": operation,
            "success": success
        }
        
        if duration_seconds is not None:
            extra["duration"] = duration_seconds
        
        if success:
            msg = f"Model call successful: {model_name}.{operation}"
            if duration_seconds:
                msg += f" (Duration: {duration_seconds:.2f}s)"
            self.info(msg, extra=extra)
        else:
            extra["error"] = error
            msg = f"Model call failed: {model_name}.{operation}"
            if error:
                msg += f" - {error}"
            self.error(msg, extra=extra)
    
    def log_asset_operation(self, operation: str, asset_id: Optional[str] = None, 
                           file_path: Optional[str] = None, success: bool = True, 
                           error: Optional[str] = None):
        """Log asset management operation"""
        extra = {
            "operation": operation,
            "success": success
        }
        
        if asset_id:
            extra["asset_id"] = asset_id
        if file_path:
            extra["file_path"] = file_path
        
        if success:
            msg = f"Asset operation successful: {operation}"
            if asset_id:
                msg += f" (Asset: {asset_id})"
            self.info(msg, extra=extra)
        else:
            extra["error"] = error
            msg = f"Asset operation failed: {operation}"
            if error:
                msg += f" - {error}"
            self.error(msg, extra=extra)
    
    def log_workflow_event(self, event: str, workflow_id: Optional[str] = None, 
                          details: Optional[Dict[str, Any]] = None):
        """Log workflow event"""
        extra = {"event": event}
        if workflow_id:
            extra["workflow_id"] = workflow_id
        if details:
            extra.update(details)
        
        msg = f"Workflow event: {event}"
        if workflow_id:
            msg += f" (Workflow: {workflow_id})"
        
        self.info(msg, extra=extra)
    
    def log_performance_metric(self, metric_name: str, value: float, unit: str = "", 
                              context: Optional[Dict[str, Any]] = None):
        """Log performance metric"""
        extra = {
            "metric_name": metric_name,
            "value": value,
            "unit": unit
        }
        if context:
            extra.update(context)
        
        msg = f"Performance metric: {metric_name} = {value}{unit}"
        self.info(msg, extra=extra)


# Global logger instances
main_logger = VideoStudioLogger("video_studio")
model_logger = VideoStudioLogger("video_studio.models")
workflow_logger = VideoStudioLogger("video_studio.workflow")
asset_logger = VideoStudioLogger("video_studio.assets")
render_logger = VideoStudioLogger("video_studio.render")


def setup_logging(level: str = "INFO", log_dir: Optional[str] = None):
    """Setup logging configuration"""
    if log_dir:
        # Update log directory for all loggers
        for logger_instance in [main_logger, model_logger, workflow_logger, asset_logger, render_logger]:
            # Clear existing file handlers
            for handler in logger_instance.logger.handlers[:]:
                if isinstance(handler, logging.FileHandler):
                    logger_instance.logger.removeHandler(handler)
            
            # Add new file handlers with custom directory
            log_path = Path(log_dir)
            log_path.mkdir(exist_ok=True)
            
            # Main log file
            log_file = log_path / f"{logger_instance.name}_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(VideoStudioFormatter())
            logger_instance.logger.addHandler(file_handler)
            
            # Error log file
            error_log_file = log_path / f"{logger_instance.name}_errors_{datetime.now().strftime('%Y%m%d')}.log"
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file,
                maxBytes=10*1024*1024,
                backupCount=5
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(VideoStudioFormatter())
            logger_instance.logger.addHandler(error_handler)
    
    # Set logging level for all loggers
    for logger_instance in [main_logger, model_logger, workflow_logger, asset_logger, render_logger]:
        logger_instance.set_level(level)


def get_logger(name: str = "video_studio") -> VideoStudioLogger:
    """Get logger instance by name"""
    logger_map = {
        "video_studio": main_logger,
        "video_studio.models": model_logger,
        "video_studio.workflow": workflow_logger,
        "video_studio.assets": asset_logger,
        "video_studio.render": render_logger
    }
    
    return logger_map.get(name, main_logger)


# Convenience functions
def log_info(message: str, logger_name: str = "video_studio", extra: Optional[Dict[str, Any]] = None):
    """Log info message"""
    get_logger(logger_name).info(message, extra)


def log_error(message: str, logger_name: str = "video_studio", extra: Optional[Dict[str, Any]] = None, 
              exc_info: bool = False):
    """Log error message"""
    get_logger(logger_name).error(message, extra, exc_info)


def log_warning(message: str, logger_name: str = "video_studio", extra: Optional[Dict[str, Any]] = None):
    """Log warning message"""
    get_logger(logger_name).warning(message, extra)


def log_debug(message: str, logger_name: str = "video_studio", extra: Optional[Dict[str, Any]] = None):
    """Log debug message"""
    get_logger(logger_name).debug(message, extra)