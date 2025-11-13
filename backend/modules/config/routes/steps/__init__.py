"""
Step-based configuration routes for V.PACK.

This package contains modular route handlers for each configuration step,
providing clean separation of concerns and maintainable code structure.
"""

from .step1_brandname_routes import step1_bp
from .step2_location_time_routes import step2_bp
from .step3_video_source_routes import step3_bp
from .step4_packing_area_routes import step4_bp
from .step5_timing_routes import step5_bp

__all__ = ["step1_bp", "step2_bp", "step3_bp", "step4_bp", "step5_bp"]
