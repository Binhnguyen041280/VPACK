"""
AI Arbitration System Module

This module provides AI-powered arbitration for commercial disputes.
Helps sellers handle complaints objectively based on laws and platform rules.
"""

__version__ = "1.0.0"
__author__ = "VPACK Team"

from .case_manager import CaseManager
from .ai_arbiter import AIArbiter
from .evidence_generator import EvidenceGenerator
from .verdict_formatter import VerdictFormatter
from .damage_assessor import DamageAssessor

__all__ = [
    'CaseManager',
    'AIArbiter',
    'EvidenceGenerator',
    'VerdictFormatter',
    'DamageAssessor'
]
