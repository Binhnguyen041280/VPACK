"""
Public Reporter Module

Publishes cases to public website and manages public visibility.
"""

import logging
from typing import Dict, Any, Optional
from modules.db_utils.safe_connection import safe_db_connection

logger = logging.getLogger(__name__)


class PublicReporter:
    """
    Manages public case reporting
    """

    def __init__(self):
        """Initialize Public Reporter"""
        self.logger = logger

    def publish_case(self, case_id: int, anonymized: bool = True) -> Optional[str]:
        """
        Publish a case to public website

        Args:
            case_id: Case ID
            anonymized: Whether to anonymize personal info

        Returns:
            str: Public URL if successful
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                # Generate public URL
                public_url = f"/public/cases/{case_id}"

                cursor.execute("""
                    INSERT INTO public_cases (case_id, anonymized, public_url)
                    VALUES (?, ?, ?)
                """, (case_id, 1 if anonymized else 0, public_url))

                conn.commit()

                self.logger.info(f"✅ Published case {case_id} to public")

                return public_url

        except Exception as e:
            self.logger.error(f"Error publishing case: {e}")
            return None

    def increment_view_count(self, public_id: int):
        """Increment view count for a public case"""
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE public_cases
                    SET view_count = view_count + 1, last_viewed_at = CURRENT_TIMESTAMP
                    WHERE public_id = ?
                """, (public_id,))

                conn.commit()

        except Exception as e:
            self.logger.error(f"Error incrementing view count: {e}")
