# src/controllers/__init__.py
from .base_controller import BaseController
from .training_controller import TrainingController
from .consultation_controller import ConsultationController

__all__ = [
    "BaseController",
    "TrainingController",
    "ConsultationController"
]