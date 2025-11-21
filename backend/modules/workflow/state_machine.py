"""
Case State Machine Module

Manages case workflow and state transitions.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class CaseStateMachine:
    """
    Manages case state transitions
    """

    # Valid states
    STATE_NEW = 'new'
    STATE_ANALYZING = 'analyzing'
    STATE_ANALYZED = 'analyzed'
    STATE_RULED = 'ruled'
    STATE_APPEALED = 'appealed'
    STATE_CLOSED = 'closed'
    STATE_DELETED = 'deleted'

    # Valid transitions
    TRANSITIONS = {
        STATE_NEW: [STATE_ANALYZING, STATE_DELETED],
        STATE_ANALYZING: [STATE_ANALYZED, STATE_NEW],
        STATE_ANALYZED: [STATE_RULED, STATE_ANALYZING],
        STATE_RULED: [STATE_CLOSED, STATE_APPEALED],
        STATE_APPEALED: [STATE_ANALYZING, STATE_RULED],
        STATE_CLOSED: [],
        STATE_DELETED: []
    }

    def __init__(self):
        """Initialize State Machine"""
        self.logger = logging.getLogger(__name__)

    def can_transition(self, from_state: str, to_state: str) -> bool:
        """
        Check if state transition is valid

        Args:
            from_state: Current state
            to_state: Target state

        Returns:
            bool: True if transition is valid
        """
        return to_state in self.TRANSITIONS.get(from_state, [])

    def get_next_states(self, current_state: str) -> list:
        """
        Get list of valid next states

        Args:
            current_state: Current state

        Returns:
            list: List of valid next states
        """
        return self.TRANSITIONS.get(current_state, [])
