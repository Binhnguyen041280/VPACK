"""
Legal Knowledge Base Module

Manages legal rules, laws, contracts, and regulatory references
for the AI Arbitration System.
"""

__version__ = "1.0.0"
__author__ = "VPACK Team"

from .knowledge_base import LegalKnowledgeBase
from .rule_matcher import RuleMatcher
from .document_parser import DocumentParser

__all__ = [
    'LegalKnowledgeBase',
    'RuleMatcher',
    'DocumentParser'
]
