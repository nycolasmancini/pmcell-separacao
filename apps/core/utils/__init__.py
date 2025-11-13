"""
Image utilities package for empty state configuration
"""
from .image_utils import (
    validate_image_file,
    optimize_empty_state_image,
    MAX_FILE_SIZE,
    MIN_WIDTH,
    MIN_HEIGHT,
    TARGET_SIZE,
    ALLOWED_EXTENSIONS
)

__all__ = [
    'validate_image_file',
    'optimize_empty_state_image',
    'MAX_FILE_SIZE',
    'MIN_WIDTH',
    'MIN_HEIGHT',
    'TARGET_SIZE',
    'ALLOWED_EXTENSIONS',
]
