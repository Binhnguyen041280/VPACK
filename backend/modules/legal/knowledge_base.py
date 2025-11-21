"""
Legal Knowledge Base Module

Manages legal rules, laws, contracts, and regulatory references.
"""

import sqlite3
import logging
from typing import Dict, List, Optional, Any
import json
from modules.db_utils.safe_connection import safe_db_connection

logger = logging.getLogger(__name__)


class LegalKnowledgeBase:
    """
    Manages legal rules and knowledge for arbitration
    """

    def __init__(self):
        """Initialize Legal Knowledge Base"""
        self.logger = logger

    def add_rule(self, rule_data: Dict[str, Any], created_by: str) -> Optional[int]:
        """
        Add a legal rule to the knowledge base

        Args:
            rule_data: Dictionary containing rule information
                Required:
                    - rule_type: 'platform', 'commercial_law', 'international', 'contract'
                    - title: str
                    - content: str
                Optional:
                    - jurisdiction: 'VN', 'US', 'International', etc.
                    - source_url: str
                    - source_document: bytes (PDF/DOCX)
                    - effective_date: str (YYYY-MM-DD)
                    - version: str
                    - category: str
                    - keywords: List[str]
            created_by: Email of creator

        Returns:
            int: Rule ID if successful, None otherwise
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                # Extract required fields
                rule_type = rule_data.get('rule_type')
                title = rule_data.get('title')
                content = rule_data.get('content')

                if not all([rule_type, title, content]):
                    self.logger.error("Missing required fields for rule creation")
                    return None

                # Extract optional fields
                jurisdiction = rule_data.get('jurisdiction')
                source_url = rule_data.get('source_url')
                source_document = rule_data.get('source_document')  # bytes
                effective_date = rule_data.get('effective_date')
                version = rule_data.get('version')
                category = rule_data.get('category')
                keywords = rule_data.get('keywords', [])

                # Convert keywords to JSON
                keywords_json = json.dumps(keywords) if isinstance(keywords, list) else keywords

                cursor.execute("""
                    INSERT INTO legal_rules (
                        rule_type, title, content, jurisdiction, source_url,
                        source_document, effective_date, version, category, keywords, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rule_type, title, content, jurisdiction, source_url,
                    source_document, effective_date, version, category, keywords_json, created_by
                ))

                rule_id = cursor.lastrowid
                conn.commit()

                self.logger.info(f"✅ Added legal rule: {title} (ID: {rule_id})")

                return rule_id

        except Exception as e:
            self.logger.error(f"Error adding legal rule: {e}")
            return None

    def get_rule(self, rule_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a legal rule by ID

        Args:
            rule_id: Rule ID

        Returns:
            dict: Rule data or None if not found
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM legal_rules WHERE rule_id = ?
                """, (rule_id,))

                row = cursor.fetchone()
                if not row:
                    return None

                columns = [description[0] for description in cursor.description]
                rule_data = dict(zip(columns, row))

                # Parse JSON keywords
                if rule_data.get('keywords'):
                    try:
                        rule_data['keywords'] = json.loads(rule_data['keywords'])
                    except:
                        pass

                return rule_data

        except Exception as e:
            self.logger.error(f"Error getting rule {rule_id}: {e}")
            return None

    def search_rules(
        self,
        query: Optional[str] = None,
        rule_type: Optional[str] = None,
        category: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search legal rules

        Args:
            query: Text search query (searches in title and content)
            rule_type: Filter by rule type
            category: Filter by category
            jurisdiction: Filter by jurisdiction
            limit: Maximum number of results

        Returns:
            List of rule dictionaries
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                sql = "SELECT * FROM legal_rules WHERE 1=1"
                params = []

                if query:
                    sql += " AND (title LIKE ? OR content LIKE ?)"
                    search_term = f"%{query}%"
                    params.extend([search_term, search_term])

                if rule_type:
                    sql += " AND rule_type = ?"
                    params.append(rule_type)

                if category:
                    sql += " AND category = ?"
                    params.append(category)

                if jurisdiction:
                    sql += " AND jurisdiction = ?"
                    params.append(jurisdiction)

                sql += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)

                cursor.execute(sql, params)

                rules = []
                columns = [description[0] for description in cursor.description]

                for row in cursor.fetchall():
                    rule_dict = dict(zip(columns, row))

                    # Parse JSON keywords
                    if rule_dict.get('keywords'):
                        try:
                            rule_dict['keywords'] = json.loads(rule_dict['keywords'])
                        except:
                            pass

                    rules.append(rule_dict)

                return rules

        except Exception as e:
            self.logger.error(f"Error searching rules: {e}")
            return []

    def update_rule(self, rule_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update a legal rule

        Args:
            rule_id: Rule ID
            updates: Dictionary of fields to update

        Returns:
            bool: True if successful
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                allowed_fields = [
                    'title', 'content', 'jurisdiction', 'source_url',
                    'source_document', 'effective_date', 'version', 'category', 'keywords'
                ]

                update_fields = []
                params = []

                for field, value in updates.items():
                    if field in allowed_fields:
                        update_fields.append(f"{field} = ?")
                        # Convert list to JSON
                        if field == 'keywords' and isinstance(value, list):
                            value = json.dumps(value)
                        params.append(value)

                if not update_fields:
                    return False

                sql = f"UPDATE legal_rules SET {', '.join(update_fields)} WHERE rule_id = ?"
                params.append(rule_id)

                cursor.execute(sql, params)
                conn.commit()

                self.logger.info(f"✅ Updated rule {rule_id}")

                return True

        except Exception as e:
            self.logger.error(f"Error updating rule {rule_id}: {e}")
            return False

    def delete_rule(self, rule_id: int) -> bool:
        """
        Delete a legal rule

        Args:
            rule_id: Rule ID

        Returns:
            bool: True if successful
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM legal_rules WHERE rule_id = ?", (rule_id,))
                conn.commit()

                self.logger.info(f"✅ Deleted rule {rule_id}")

                return True

        except Exception as e:
            self.logger.error(f"Error deleting rule {rule_id}: {e}")
            return False

    def add_rule_reference(
        self,
        from_rule_id: int,
        to_rule_id: int,
        relationship: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Add a reference between two rules

        Args:
            from_rule_id: Source rule ID
            to_rule_id: Target rule ID
            relationship: Type of relationship ('supersedes', 'related', 'contradicts', etc.)
            notes: Optional notes

        Returns:
            bool: True if successful
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO rule_references (from_rule_id, to_rule_id, relationship, notes)
                    VALUES (?, ?, ?, ?)
                """, (from_rule_id, to_rule_id, relationship, notes))

                conn.commit()

                self.logger.info(f"✅ Added reference: {from_rule_id} -> {to_rule_id}")

                return True

        except Exception as e:
            self.logger.error(f"Error adding rule reference: {e}")
            return False

    def get_rule_references(self, rule_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all references for a rule (both incoming and outgoing)

        Args:
            rule_id: Rule ID

        Returns:
            dict: {'outgoing': [...], 'incoming': [...]}
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()

                # Outgoing references
                cursor.execute("""
                    SELECT rr.*, lr.title as to_rule_title
                    FROM rule_references rr
                    JOIN legal_rules lr ON rr.to_rule_id = lr.rule_id
                    WHERE rr.from_rule_id = ?
                """, (rule_id,))

                outgoing = []
                for row in cursor.fetchall():
                    columns = [description[0] for description in cursor.description]
                    outgoing.append(dict(zip(columns, row)))

                # Incoming references
                cursor.execute("""
                    SELECT rr.*, lr.title as from_rule_title
                    FROM rule_references rr
                    JOIN legal_rules lr ON rr.from_rule_id = lr.rule_id
                    WHERE rr.to_rule_id = ?
                """, (rule_id,))

                incoming = []
                for row in cursor.fetchall():
                    columns = [description[0] for description in cursor.description]
                    incoming.append(dict(zip(columns, row)))

                return {
                    'outgoing': outgoing,
                    'incoming': incoming
                }

        except Exception as e:
            self.logger.error(f"Error getting rule references: {e}")
            return {'outgoing': [], 'incoming': []}

    def get_categories(self) -> List[str]:
        """
        Get list of all unique categories

        Returns:
            List of category names
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT category FROM legal_rules
                    WHERE category IS NOT NULL
                    ORDER BY category
                """)

                categories = [row[0] for row in cursor.fetchall()]

                return categories

        except Exception as e:
            self.logger.error(f"Error getting categories: {e}")
            return []

    def get_jurisdictions(self) -> List[str]:
        """
        Get list of all unique jurisdictions

        Returns:
            List of jurisdiction codes
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT jurisdiction FROM legal_rules
                    WHERE jurisdiction IS NOT NULL
                    ORDER BY jurisdiction
                """)

                jurisdictions = [row[0] for row in cursor.fetchall()]

                return jurisdictions

        except Exception as e:
            self.logger.error(f"Error getting jurisdictions: {e}")
            return []
