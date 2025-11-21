"""
Damage Assessor Module

Assesses and calculates damages for arbitration cases.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DamageAssessor:
    """
    Assesses damages in arbitration cases
    """

    def __init__(self):
        """Initialize Damage Assessor"""
        self.logger = logger

    def assess_damage(
        self,
        case_data: Dict[str, Any],
        verdict: str,
        ai_damage_assessment: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Assess damage for a case

        Args:
            case_data: Case information
            verdict: AI verdict
            ai_damage_assessment: AI's damage assessment (optional)

        Returns:
            dict: Damage assessment
        """
        if verdict != 'platform_wrong':
            # No damage if platform is right
            return {
                'type': 'none',
                'estimated_amount': 0,
                'calculation_basis': 'Sàn không có lỗi',
                'breakdown': {}
            }

        # If AI provided assessment, use it
        if ai_damage_assessment:
            return ai_damage_assessment

        # Otherwise, calculate basic damage
        disputed_amount = case_data.get('amount_disputed', 0)
        dispute_type = case_data.get('dispute_type', '')

        # Basic damage calculation
        damage_type = 'direct_loss'
        estimated_amount = disputed_amount

        # Adjust based on dispute type
        if dispute_type in ['ban', 'account_suspension']:
            damage_type = 'opportunity_cost'
            # Estimate opportunity cost (e.g., 30 days of potential revenue)
            estimated_amount = disputed_amount * 30 if disputed_amount > 0 else 10000000  # 10M VND default

        elif dispute_type == 'fraud':
            damage_type = 'direct_loss'
            # Add compensation for stress (20% of amount)
            estimated_amount = disputed_amount * 1.2

        return {
            'type': damage_type,
            'estimated_amount': estimated_amount,
            'calculation_basis': f'Tính toán dựa trên loại tranh chấp: {dispute_type}',
            'breakdown': {
                'direct_loss': disputed_amount,
                'compensation': estimated_amount - disputed_amount
            }
        }

    def calculate_total_damages(self, cases: list) -> Dict[str, Any]:
        """
        Calculate total damages across multiple cases

        Args:
            cases: List of cases

        Returns:
            dict: Total damage statistics
        """
        total_direct = 0
        total_indirect = 0
        total_opportunity = 0

        for case in cases:
            damage = case.get('damage_assessment', {})

            if isinstance(damage, str):
                import json
                try:
                    damage = json.loads(damage)
                except:
                    damage = {}

            damage_type = damage.get('type', 'none')
            amount = damage.get('estimated_amount', 0)

            if damage_type == 'direct_loss':
                total_direct += amount
            elif damage_type == 'indirect_loss':
                total_indirect += amount
            elif damage_type == 'opportunity_cost':
                total_opportunity += amount

        return {
            'total_direct_loss': total_direct,
            'total_indirect_loss': total_indirect,
            'total_opportunity_cost': total_opportunity,
            'grand_total': total_direct + total_indirect + total_opportunity,
            'case_count': len(cases)
        }
