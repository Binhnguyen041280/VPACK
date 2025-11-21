"""
Verdict Formatter Module

Formats AI verdict results into user-friendly displays.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class VerdictFormatter:
    """
    Formats verdict results for display
    """

    def __init__(self):
        """Initialize Verdict Formatter"""
        self.logger = logger

    def format_verdict(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format verdict for UI display

        Args:
            analysis_result: Raw AI analysis result

        Returns:
            dict: Formatted verdict
        """
        verdict = analysis_result.get('verdict', 'unclear')
        confidence = analysis_result.get('confidence', 0.5)

        # Determine verdict display properties
        verdict_display = {
            'platform_right': {
                'label': 'Sàn Đúng',
                'color': 'green',
                'icon': '✓',
                'message': 'Sàn/Platform tuân thủ đúng quy định'
            },
            'platform_wrong': {
                'label': 'Sàn Sai',
                'color': 'red',
                'icon': '✗',
                'message': 'Sàn/Platform có vi phạm, người khiếu nại có cơ sở'
            },
            'unclear': {
                'label': 'Chưa Rõ Ràng',
                'color': 'yellow',
                'icon': '?',
                'message': 'Cần thêm thông tin hoặc chứng cứ để kết luận'
            }
        }

        display_info = verdict_display.get(verdict, verdict_display['unclear'])

        # Confidence level
        confidence_level = 'Thấp'
        if confidence >= 0.8:
            confidence_level = 'Cao'
        elif confidence >= 0.6:
            confidence_level = 'Trung Bình'

        return {
            'verdict': verdict,
            'verdict_label': display_info['label'],
            'verdict_color': display_info['color'],
            'verdict_icon': display_info['icon'],
            'verdict_message': display_info['message'],
            'confidence': confidence,
            'confidence_percent': f"{confidence * 100:.0f}%",
            'confidence_level': confidence_level,
            'reasoning': analysis_result.get('reasoning', ''),
            'recommended_action': analysis_result.get('recommended_action', ''),
            'platform_violations': analysis_result.get('platform_violations', []),
            'damage_assessment': analysis_result.get('damage_assessment', {})
        }
