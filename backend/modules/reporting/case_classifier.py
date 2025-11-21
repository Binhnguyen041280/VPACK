"""
Case Classifier Module

Classifies and categorizes arbitration cases based on patterns and severity.
"""

import logging
from typing import Dict, Any, List, Optional
from modules.db_utils.safe_connection import safe_db_connection
import json

logger = logging.getLogger(__name__)


class CaseClassifier:
    """
    Classifies cases by pattern and severity
    """

    def __init__(self):
        """Initialize Case Classifier"""
        self.logger = logger

    def classify_case(self, case_data: Dict[str, Any], analysis_result: Dict[str, Any]) -> Optional[int]:
        """
        Classify a case and save classification

        Args:
            case_data: Case information
            analysis_result: AI analysis result

        Returns:
            int: Classification ID if successful
        """
        try:
            # Determine pattern type
            pattern_type = self._determine_pattern(case_data, analysis_result)

            # Determine severity
            severity = self._determine_severity(case_data, analysis_result)

            # Extract fraud indicators
            fraud_indicators = self._extract_fraud_indicators(case_data, analysis_result)

            # Find similar cases
            similar_cases = self._find_similar_cases(case_data)

            # Save classification
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO case_classifications (
                        case_id, pattern_type, severity, fraud_indicators, similar_cases, classified_by
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    case_data['case_id'],
                    pattern_type,
                    severity,
                    json.dumps(fraud_indicators),
                    json.dumps(similar_cases),
                    'system'
                ))

                classification_id = cursor.lastrowid
                conn.commit()

                self.logger.info(f"✅ Classified case {case_data['case_id']}")

                return classification_id

        except Exception as e:
            self.logger.error(f"Error classifying case: {e}")
            return None

    def _determine_pattern(self, case_data: Dict[str, Any], analysis_result: Dict[str, Any]) -> str:
        """
        Determine pattern type

        Args:
            case_data: Case information
            analysis_result: AI analysis result

        Returns:
            str: Pattern type
        """
        verdict = analysis_result.get('verdict')
        violations = analysis_result.get('platform_violations', [])

        if verdict == 'platform_wrong' and len(violations) >= 3:
            return 'systematic_fraud'
        elif verdict == 'platform_wrong' and len(violations) >= 1:
            return 'policy_abuse'
        else:
            return 'isolated_incident'

    def _determine_severity(self, case_data: Dict[str, Any], analysis_result: Dict[str, Any]) -> str:
        """
        Determine severity level

        Args:
            case_data: Case information
            analysis_result: AI analysis result

        Returns:
            str: Severity level
        """
        amount = case_data.get('amount_disputed', 0)
        verdict = analysis_result.get('verdict')
        confidence = analysis_result.get('confidence', 0.5)

        # Critical: High amount + platform wrong + high confidence
        if amount > 50000000 and verdict == 'platform_wrong' and confidence > 0.8:  # > 50M VND
            return 'critical'

        # Severe: Medium-high amount + platform wrong
        elif amount > 10000000 and verdict == 'platform_wrong':  # > 10M VND
            return 'severe'

        # Moderate: Low amount or unclear verdict
        elif verdict == 'unclear' or amount > 1000000:  # > 1M VND
            return 'moderate'

        # Minor
        else:
            return 'minor'

    def _extract_fraud_indicators(self, case_data: Dict[str, Any], analysis_result: Dict[str, Any]) -> List[str]:
        """
        Extract fraud indicators

        Args:
            case_data: Case information
            analysis_result: AI analysis result

        Returns:
            List of fraud indicators
        """
        indicators = []

        # Check for fraud keywords in description
        fraud_keywords = ['gian lận', 'lừa đảo', 'hàng giả', 'fake', 'scam', 'cheat']
        description_lower = case_data.get('description', '').lower()

        for keyword in fraud_keywords:
            if keyword in description_lower:
                indicators.append(f"fraud_keyword:{keyword}")

        # High amount
        if case_data.get('amount_disputed', 0) > 20000000:  # > 20M VND
            indicators.append("high_amount")

        # Multiple violations
        violations = analysis_result.get('platform_violations', [])
        if len(violations) >= 2:
            indicators.append("multiple_violations")

        return indicators

    def _find_similar_cases(self, case_data: Dict[str, Any], limit: int = 5) -> List[int]:
        """
        Find similar cases

        Args:
            case_data: Case information
            limit: Maximum number of similar cases

        Returns:
            List of similar case IDs
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                # Find cases with same respondent and dispute type
                cursor.execute("""
                    SELECT case_id FROM arbitration_cases
                    WHERE respondent_name = ?
                      AND dispute_type = ?
                      AND case_id != ?
                      AND ai_verdict = 'platform_wrong'
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (
                    case_data.get('respondent_name'),
                    case_data.get('dispute_type'),
                    case_data.get('case_id'),
                    limit
                ))

                similar_cases = [row[0] for row in cursor.fetchall()]

                return similar_cases

        except Exception as e:
            self.logger.error(f"Error finding similar cases: {e}")
            return []
