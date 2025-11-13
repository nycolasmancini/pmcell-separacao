"""
Utilities package for core app
Combines image utilities and metrics/time utilities
"""

# Image utilities (from utils/image_utils.py)
from .image_utils import (
    validate_image_file,
    optimize_empty_state_image,
    MAX_FILE_SIZE,
    MIN_WIDTH,
    MIN_HEIGHT,
    TARGET_SIZE,
    ALLOWED_EXTENSIONS
)

# Metrics and time utilities (from parent utils.py module)
# Import from the parent-level utils.py file using .. notation
from .. import utils as parent_utils

# Re-export metrics functions
calcular_tempo_util = parent_utils.calcular_tempo_util
calcular_metricas_dia = parent_utils.calcular_metricas_dia
formatar_tempo = parent_utils.formatar_tempo
calcular_metricas_periodo = parent_utils.calcular_metricas_periodo

__all__ = [
    # Image utilities
    'validate_image_file',
    'optimize_empty_state_image',
    'MAX_FILE_SIZE',
    'MIN_WIDTH',
    'MIN_HEIGHT',
    'TARGET_SIZE',
    'ALLOWED_EXTENSIONS',
    # Metrics and time utilities
    'calcular_tempo_util',
    'calcular_metricas_dia',
    'formatar_tempo',
    'calcular_metricas_periodo',
]
