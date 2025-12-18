"""
Model Adapters for Video Studio

This package contains implementations of model adapters for different AI video generation services.
"""

import warnings

# Try to import adapters with graceful fallback for missing dependencies
try:
    from .luma_adapter import LumaAdapter
    LUMA_AVAILABLE = True
except ImportError as e:
    warnings.warn(f"LumaAdapter not available: {e}. Please install missing dependencies: pip install aiohttp psutil")
    LumaAdapter = None
    LUMA_AVAILABLE = False

try:
    from .runway_adapter import RunwayAdapter
    RUNWAY_AVAILABLE = True
except ImportError as e:
    warnings.warn(f"RunwayAdapter not available: {e}. Please install missing dependencies: pip install aiohttp psutil")
    RunwayAdapter = None
    RUNWAY_AVAILABLE = False

try:
    from .pika_adapter import PikaAdapter
    PIKA_AVAILABLE = True
except ImportError as e:
    warnings.warn(f"PikaAdapter not available: {e}. Please install missing dependencies: pip install aiohttp psutil")
    PikaAdapter = None
    PIKA_AVAILABLE = False

__all__ = [
    'LumaAdapter',
    'RunwayAdapter', 
    'PikaAdapter',
    'LUMA_AVAILABLE',
    'RUNWAY_AVAILABLE',
    'PIKA_AVAILABLE'
]
