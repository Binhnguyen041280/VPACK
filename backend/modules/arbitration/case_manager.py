"""
Case Manager Module

Handles creation, retrieval, update, and management of arbitration cases.
"""

import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
from modules.db_utils.safe_connection import safe_db_connection

logger = logging.getLogger(__name__)


class CaseManager:
    """
    Manages arbitration cases lifecycle: create, read, update, delete
    """

    def __init__(self):
        """Initialize Case Manager"""
        self.logger = logger

    def generate_case_number(self, conn: sqlite3.Connection = None) -> str:
        """
        Generate unique case number in format: ARB-YYYY-NNN

        Args:
            conn: Database connection (optional)

        Returns:
            str: Generated case number (e.g., "ARB-2025-001")
        """
        try:
            year = datetime.now().year

            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM arbitration_cases
                    WHERE case_number LIKE ?
                """, (f"ARB-{year}-%",))
                count = cursor.fetchone()[0]
            else:
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT COUNT(*) FROM arbitration_cases
                        WHERE case_number LIKE ?
                    """, (f"ARB-{year}-%",))
                    count = cursor.fetchone()[0]

            # Next number (1-indexed)
            next_num = count + 1

            # Format: ARB-2025-001
            case_number = f"ARB-{year}-{next_num:03d}"

            return case_number

        except Exception as e:
            self.logger.error(f"Error generating case number: {e}")
            # Fallback to timestamp-based
            return f"ARB-{year}-{int(datetime.now().timestamp())}"

    def create_case(self, case_data: Dict[str, Any], created_by: str) -> Optional[int]:
        """
        Create a new arbitration case

        Args:
            case_data: Dictionary containing case information
                Required fields:
                    - title: str
                    - description: str
                    - complainant_name: str
                    - respondent_name: str
                    - dispute_type: str
                Optional fields:
                    - complainant_email, complainant_phone, complainant_id_number
                    - respondent_type, respondent_tax_id
                    - dispute_date, amount_disputed, currency
                    - priority
            created_by: Email of the user creating the case

        Returns:
            int: Case ID if successful, None otherwise
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                # Generate case number
                case_number = self.generate_case_number(conn)

                # Extract required fields
                title = case_data.get('title')
                description = case_data.get('description')
                complainant_name = case_data.get('complainant_name')
                respondent_name = case_data.get('respondent_name')
                dispute_type = case_data.get('dispute_type')

                # Validate required fields
                if not all([title, description, complainant_name, respondent_name, dispute_type]):
                    self.logger.error("Missing required fields for case creation")
                    return None

                # Extract optional fields
                complainant_email = case_data.get('complainant_email')
                complainant_phone = case_data.get('complainant_phone')
                complainant_id_number = case_data.get('complainant_id_number')
                respondent_type = case_data.get('respondent_type', 'platform')
                respondent_tax_id = case_data.get('respondent_tax_id')
                dispute_date = case_data.get('dispute_date')
                amount_disputed = case_data.get('amount_disputed', 0.0)
                currency = case_data.get('currency', 'VND')
                priority = case_data.get('priority', 'medium')

                # Insert case
                cursor.execute("""
                    INSERT INTO arbitration_cases (
                        case_number, title, description,
                        complainant_name, complainant_email, complainant_phone, complainant_id_number,
                        respondent_name, respondent_type, respondent_tax_id,
                        dispute_type, dispute_date, amount_disputed, currency,
                        priority, status, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    case_number, title, description,
                    complainant_name, complainant_email, complainant_phone, complainant_id_number,
                    respondent_name, respondent_type, respondent_tax_id,
                    dispute_type, dispute_date, amount_disputed, currency,
                    priority, 'new', created_by
                ))

                case_id = cursor.lastrowid
                conn.commit()

                # Log workflow
                self._log_workflow(conn, case_id, None, 'new', 'created', created_by)

                # Audit log
                self._log_audit(conn, 'case', case_id, 'create', created_by, case_data)

                self.logger.info(f"✅ Created case {case_number} (ID: {case_id})")

                return case_id

        except Exception as e:
            self.logger.error(f"Error creating case: {e}")
            return None

    def get_case(self, case_id: int) -> Optional[Dict[str, Any]]:
        """
        Get case by ID with all details

        Args:
            case_id: Case ID

        Returns:
            dict: Case data or None if not found
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM arbitration_cases WHERE case_id = ?
                """, (case_id,))

                row = cursor.fetchone()
                if not row:
                    return None

                columns = [description[0] for description in cursor.description]
                case_data = dict(zip(columns, row))

                # Parse JSON fields
                if case_data.get('applicable_rules'):
                    try:
                        case_data['applicable_rules'] = json.loads(case_data['applicable_rules'])
                    except:
                        pass

                if case_data.get('platform_violations'):
                    try:
                        case_data['platform_violations'] = json.loads(case_data['platform_violations'])
                    except:
                        pass

                if case_data.get('damage_assessment'):
                    try:
                        case_data['damage_assessment'] = json.loads(case_data['damage_assessment'])
                    except:
                        pass

                return case_data

        except Exception as e:
            self.logger.error(f"Error getting case {case_id}: {e}")
            return None

    def get_case_by_number(self, case_number: str) -> Optional[Dict[str, Any]]:
        """
        Get case by case number

        Args:
            case_number: Case number (e.g., ARB-2025-001)

        Returns:
            dict: Case data or None if not found
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT case_id FROM arbitration_cases WHERE case_number = ?
                """, (case_number,))

                row = cursor.fetchone()
                if row:
                    return self.get_case(row[0])

                return None

        except Exception as e:
            self.logger.error(f"Error getting case by number {case_number}: {e}")
            return None

    def list_cases(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = 'created_at',
        sort_order: str = 'DESC'
    ) -> List[Dict[str, Any]]:
        """
        List cases with optional filters

        Args:
            filters: Dictionary of filters (status, dispute_type, created_by, etc.)
            limit: Number of results to return
            offset: Offset for pagination
            sort_by: Column to sort by
            sort_order: 'ASC' or 'DESC'

        Returns:
            List of case dictionaries
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                # Build query
                query = "SELECT * FROM arbitration_cases WHERE 1=1"
                params = []

                if filters:
                    if 'status' in filters:
                        query += " AND status = ?"
                        params.append(filters['status'])

                    if 'dispute_type' in filters:
                        query += " AND dispute_type = ?"
                        params.append(filters['dispute_type'])

                    if 'created_by' in filters:
                        query += " AND created_by = ?"
                        params.append(filters['created_by'])

                    if 'respondent_name' in filters:
                        query += " AND respondent_name LIKE ?"
                        params.append(f"%{filters['respondent_name']}%")

                    if 'ai_verdict' in filters:
                        query += " AND ai_verdict = ?"
                        params.append(filters['ai_verdict'])

                    if 'priority' in filters:
                        query += " AND priority = ?"
                        params.append(filters['priority'])

                # Sort
                allowed_sort_columns = ['created_at', 'case_number', 'status', 'amount_disputed', 'ai_confidence']
                if sort_by in allowed_sort_columns:
                    query += f" ORDER BY {sort_by} {sort_order}"
                else:
                    query += " ORDER BY created_at DESC"

                # Limit/offset
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                cursor.execute(query, params)

                cases = []
                columns = [description[0] for description in cursor.description]

                for row in cursor.fetchall():
                    case_dict = dict(zip(columns, row))
                    cases.append(case_dict)

                return cases

        except Exception as e:
            self.logger.error(f"Error listing cases: {e}")
            return []

    def update_case(self, case_id: int, updates: Dict[str, Any], updated_by: str) -> bool:
        """
        Update case fields

        Args:
            case_id: Case ID
            updates: Dictionary of fields to update
            updated_by: Email of user making the update

        Returns:
            bool: True if successful
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                # Build update query
                allowed_fields = [
                    'title', 'description', 'status', 'priority',
                    'complainant_email', 'complainant_phone',
                    'amount_disputed', 'currency',
                    'ai_verdict', 'ai_confidence', 'ai_reasoning',
                    'applicable_rules', 'platform_violations',
                    'recommended_action', 'damage_assessment',
                    'evidence_generated', 'evidence_document_path'
                ]

                update_fields = []
                params = []

                for field, value in updates.items():
                    if field in allowed_fields:
                        update_fields.append(f"{field} = ?")
                        # Convert dict/list to JSON
                        if isinstance(value, (dict, list)):
                            value = json.dumps(value)
                        params.append(value)

                if not update_fields:
                    self.logger.warning("No valid fields to update")
                    return False

                query = f"UPDATE arbitration_cases SET {', '.join(update_fields)} WHERE case_id = ?"
                params.append(case_id)

                cursor.execute(query, params)
                conn.commit()

                # Audit log
                self._log_audit(conn, 'case', case_id, 'update', updated_by, updates)

                # Log status change
                if 'status' in updates:
                    old_case = self.get_case(case_id)
                    if old_case:
                        self._log_workflow(
                            conn, case_id,
                            old_case.get('status'),
                            updates['status'],
                            'status_changed',
                            updated_by
                        )

                self.logger.info(f"✅ Updated case {case_id}")

                return True

        except Exception as e:
            self.logger.error(f"Error updating case {case_id}: {e}")
            return False

    def delete_case(self, case_id: int, deleted_by: str) -> bool:
        """
        Delete a case (soft delete - set status to 'deleted')

        Args:
            case_id: Case ID
            deleted_by: Email of user deleting the case

        Returns:
            bool: True if successful
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                # Soft delete - change status
                cursor.execute("""
                    UPDATE arbitration_cases SET status = 'deleted', closed_at = CURRENT_TIMESTAMP
                    WHERE case_id = ?
                """, (case_id,))

                conn.commit()

                # Audit log
                self._log_audit(conn, 'case', case_id, 'delete', deleted_by, {})

                self.logger.info(f"✅ Deleted case {case_id}")

                return True

        except Exception as e:
            self.logger.error(f"Error deleting case {case_id}: {e}")
            return False

    def add_evidence(
        self,
        case_id: int,
        evidence_type: str,
        file_name: Optional[str] = None,
        file_path: Optional[str] = None,
        file_blob: Optional[bytes] = None,
        cloud_url: Optional[str] = None,
        description: Optional[str] = None,
        uploaded_by: str = None
    ) -> Optional[int]:
        """
        Add evidence to a case

        Args:
            case_id: Case ID
            evidence_type: Type of evidence (video, image, document, chat, email, screenshot)
            file_name: Name of file
            file_path: Local file path
            file_blob: File binary data
            cloud_url: Google Drive URL
            description: Description of evidence
            uploaded_by: Email of uploader

        Returns:
            int: Evidence ID if successful, None otherwise
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                file_size = len(file_blob) if file_blob else 0

                cursor.execute("""
                    INSERT INTO case_evidence (
                        case_id, evidence_type, file_name, file_path,
                        file_blob, file_size_bytes, cloud_url, description, uploaded_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    case_id, evidence_type, file_name, file_path,
                    file_blob, file_size, cloud_url, description, uploaded_by
                ))

                evidence_id = cursor.lastrowid
                conn.commit()

                # Audit log
                self._log_audit(conn, 'evidence', evidence_id, 'create', uploaded_by, {
                    'case_id': case_id,
                    'evidence_type': evidence_type,
                    'file_name': file_name
                })

                self.logger.info(f"✅ Added evidence to case {case_id}")

                return evidence_id

        except Exception as e:
            self.logger.error(f"Error adding evidence to case {case_id}: {e}")
            return None

    def get_case_evidence(self, case_id: int) -> List[Dict[str, Any]]:
        """
        Get all evidence for a case

        Args:
            case_id: Case ID

        Returns:
            List of evidence dictionaries
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT evidence_id, evidence_type, file_name, file_path,
                           file_size_bytes, cloud_url, description, uploaded_by, uploaded_at
                    FROM case_evidence
                    WHERE case_id = ?
                    ORDER BY uploaded_at DESC
                """, (case_id,))

                evidence_list = []
                columns = [description[0] for description in cursor.description]

                for row in cursor.fetchall():
                    evidence_dict = dict(zip(columns, row))
                    evidence_list.append(evidence_dict)

                return evidence_list

        except Exception as e:
            self.logger.error(f"Error getting evidence for case {case_id}: {e}")
            return []

    def add_comment(self, case_id: int, comment_text: str, author: str, comment_type: str = 'note') -> bool:
        """
        Add a comment to a case

        Args:
            case_id: Case ID
            comment_text: Comment text
            author: Email of comment author
            comment_type: Type (note, update, decision)

        Returns:
            bool: True if successful
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO case_comments (case_id, comment_text, comment_type, author)
                    VALUES (?, ?, ?, ?)
                """, (case_id, comment_text, comment_type, author))

                conn.commit()

                self.logger.info(f"✅ Added comment to case {case_id}")

                return True

        except Exception as e:
            self.logger.error(f"Error adding comment to case {case_id}: {e}")
            return False

    def get_case_comments(self, case_id: int) -> List[Dict[str, Any]]:
        """
        Get all comments for a case

        Args:
            case_id: Case ID

        Returns:
            List of comment dictionaries
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM case_comments
                    WHERE case_id = ?
                    ORDER BY created_at ASC
                """, (case_id,))

                comments = []
                columns = [description[0] for description in cursor.description]

                for row in cursor.fetchall():
                    comment_dict = dict(zip(columns, row))
                    comments.append(comment_dict)

                return comments

        except Exception as e:
            self.logger.error(f"Error getting comments for case {case_id}: {e}")
            return []

    def get_case_statistics(self, created_by: Optional[str] = None) -> Dict[str, Any]:
        """
        Get case statistics

        Args:
            created_by: Optional filter by user email

        Returns:
            dict: Statistics
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                where_clause = ""
                params = []

                if created_by:
                    where_clause = "WHERE created_by = ?"
                    params.append(created_by)

                # Total cases
                cursor.execute(f"SELECT COUNT(*) FROM arbitration_cases {where_clause}", params)
                total_cases = cursor.fetchone()[0]

                # By status
                cursor.execute(f"""
                    SELECT status, COUNT(*) FROM arbitration_cases {where_clause}
                    GROUP BY status
                """, params)
                by_status = {row[0]: row[1] for row in cursor.fetchall()}

                # By verdict
                cursor.execute(f"""
                    SELECT ai_verdict, COUNT(*) FROM arbitration_cases
                    {where_clause} {"AND" if where_clause else "WHERE"} ai_verdict IS NOT NULL
                    GROUP BY ai_verdict
                """, params)
                by_verdict = {row[0]: row[1] for row in cursor.fetchall()}

                # Total disputed amount
                cursor.execute(f"""
                    SELECT SUM(amount_disputed) FROM arbitration_cases {where_clause}
                """, params)
                total_amount = cursor.fetchone()[0] or 0

                return {
                    'total_cases': total_cases,
                    'by_status': by_status,
                    'by_verdict': by_verdict,
                    'total_disputed_amount': total_amount
                }

        except Exception as e:
            self.logger.error(f"Error getting case statistics: {e}")
            return {}

    # ==================== PRIVATE HELPER METHODS ====================

    def _log_workflow(
        self,
        conn: sqlite3.Connection,
        case_id: int,
        from_status: Optional[str],
        to_status: str,
        action: str,
        actor: str
    ):
        """Log workflow state change"""
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO case_workflow_log (case_id, from_status, to_status, action, actor)
                VALUES (?, ?, ?, ?, ?)
            """, (case_id, from_status, to_status, action, actor))
            conn.commit()
        except Exception as e:
            self.logger.error(f"Error logging workflow: {e}")

    def _log_audit(
        self,
        conn: sqlite3.Connection,
        entity_type: str,
        entity_id: int,
        action: str,
        actor: str,
        changes: Dict[str, Any]
    ):
        """Log audit trail"""
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO arbitration_audit_log (entity_type, entity_id, action, actor, changes)
                VALUES (?, ?, ?, ?, ?)
            """, (entity_type, entity_id, action, actor, json.dumps(changes)))
            conn.commit()
        except Exception as e:
            self.logger.error(f"Error logging audit: {e}")
