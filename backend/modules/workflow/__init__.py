"""
Workflow Management Module

Manages case workflow, state transitions, and notifications.
"""

__version__ = "1.0.0"
__author__ = "VPACK Team"

from .state_machine import CaseStateMachine
from .notification import NotificationService

__all__ = [
    'CaseStateMachine',
    'NotificationService'
]
