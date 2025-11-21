"""
Statistics Engine Module

Generates statistics and reports for arbitration cases.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from modules.db_utils.safe_connection import safe_db_connection
import json

logger = logging.getLogger(__name__)


class StatisticsEngine:
    """
    Generates statistics for arbitration system
    """

    def __init__(self):
        """Initialize Statistics Engine"""
        self.logger = logger

    def generate_platform_statistics(
        self,
        platform_name: str,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate statistics for a platform

        Args:
            platform_name: Platform name
            period_start: Start date (YYYY-MM-DD)
            period_end: End date (YYYY-MM-DD)

        Returns:
            dict: Statistics
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                # Build query
                where_clauses = ["respondent_name = ?"]
                params = [platform_name]

                if period_start:
                    where_clauses.append("created_at >= ?")
                    params.append(period_start)

                if period_end:
                    where_clauses.append("created_at <= ?")
                    params.append(period_end)

                where_sql = " AND ".join(where_clauses)

                # Total cases
                cursor.execute(f"""
                    SELECT COUNT(*) FROM arbitration_cases WHERE {where_sql}
                """, params)
                total_cases = cursor.fetchone()[0]

                # By verdict
                cursor.execute(f"""
                    SELECT ai_verdict, COUNT(*) FROM arbitration_cases
                    WHERE {where_sql} AND ai_verdict IS NOT NULL
                    GROUP BY ai_verdict
                """, params)

                verdict_counts = {}
                for row in cursor.fetchall():
                    verdict_counts[row[0]] = row[1]

                # Total damage
                cursor.execute(f"""
                    SELECT SUM(amount_disputed) FROM arbitration_cases WHERE {where_sql}
                """, params)
                total_damage = cursor.fetchone()[0] or 0

                # Fraud cases
                cursor.execute(f"""
                    SELECT COUNT(*) FROM arbitration_cases
                    WHERE {where_sql} AND dispute_type = 'fraud'
                """, params)
                fraud_count = cursor.fetchone()[0]

                stats = {
                    'platform_name': platform_name,
                    'period_start': period_start,
                    'period_end': period_end,
                    'total_cases': total_cases,
                    'platform_right_count': verdict_counts.get('platform_right', 0),
                    'platform_wrong_count': verdict_counts.get('platform_wrong', 0),
                    'unclear_count': verdict_counts.get('unclear', 0),
                    'total_damage_amount': total_damage,
                    'fraud_case_count': fraud_count
                }

                # Save to table
                self._save_platform_statistics(stats)

                return stats

        except Exception as e:
            self.logger.error(f"Error generating platform statistics: {e}")
            return {}

    def _save_platform_statistics(self, stats: Dict[str, Any]):
        """Save statistics to database"""
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO platform_statistics (
                        platform_name, period_start, period_end,
                        total_cases, platform_right_count, platform_wrong_count,
                        unclear_count, total_damage_amount, fraud_case_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    stats['platform_name'],
                    stats.get('period_start'),
                    stats.get('period_end'),
                    stats['total_cases'],
                    stats['platform_right_count'],
                    stats['platform_wrong_count'],
                    stats['unclear_count'],
                    stats['total_damage_amount'],
                    stats['fraud_case_count']
                ))

                conn.commit()

        except Exception as e:
            self.logger.error(f"Error saving platform statistics: {e}")

    def get_overall_statistics(self) -> Dict[str, Any]:
        """
        Get overall system statistics

        Returns:
            dict: Overall statistics
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                # Total cases
                cursor.execute("SELECT COUNT(*) FROM arbitration_cases")
                total_cases = cursor.fetchone()[0]

                # By status
                cursor.execute("""
                    SELECT status, COUNT(*) FROM arbitration_cases GROUP BY status
                """)
                by_status = {row[0]: row[1] for row in cursor.fetchall()}

                # By verdict
                cursor.execute("""
                    SELECT ai_verdict, COUNT(*) FROM arbitration_cases
                    WHERE ai_verdict IS NOT NULL
                    GROUP BY ai_verdict
                """)
                by_verdict = {row[0]: row[1] for row in cursor.fetchall()}

                # Total damage
                cursor.execute("SELECT SUM(amount_disputed) FROM arbitration_cases")
                total_damage = cursor.fetchone()[0] or 0

                # Top platforms
                cursor.execute("""
                    SELECT respondent_name, COUNT(*) as count
                    FROM arbitration_cases
                    WHERE respondent_type = 'platform'
                    GROUP BY respondent_name
                    ORDER BY count DESC
                    LIMIT 10
                """)
                top_platforms = [{'name': row[0], 'count': row[1]} for row in cursor.fetchall()]

                return {
                    'total_cases': total_cases,
                    'by_status': by_status,
                    'by_verdict': by_verdict,
                    'total_damage': total_damage,
                    'top_platforms': top_platforms
                }

        except Exception as e:
            self.logger.error(f"Error getting overall statistics: {e}")
            return {}
