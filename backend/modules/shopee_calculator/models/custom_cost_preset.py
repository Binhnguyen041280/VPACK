"""
Custom Cost Preset Model for Shopee Calculator.
Manages user-defined and system cost presets.
"""

import sqlite3
from typing import Optional, Dict, Any, List
from ..database import get_db_path


class CustomCostPreset:
    """Model for custom cost presets."""

    def __init__(self, db_path: str = None):
        """Initialize CustomCostPreset model.

        Args:
            db_path: Path to SQLite database (defaults to Shopee Calculator DB)
        """
        self.db_path = db_path or get_db_path()

    def get_system_presets(self) -> List[Dict[str, Any]]:
        """Get all system-defined cost presets.

        Returns:
            List of system preset dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT *
                FROM shopee_custom_cost_presets
                WHERE is_system = 1 AND is_active = 1
                ORDER BY preset_id
            """)

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        finally:
            conn.close()

    def get_user_presets(self, user_email: str) -> List[Dict[str, Any]]:
        """Get user's custom cost presets.

        Args:
            user_email: User email

        Returns:
            List of user preset dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT *
                FROM shopee_custom_cost_presets
                WHERE user_email = ? AND is_active = 1
                ORDER BY created_at DESC
            """, (user_email,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        finally:
            conn.close()

    def get_all_for_user(self, user_email: str) -> List[Dict[str, Any]]:
        """Get both system and user presets combined.

        Args:
            user_email: User email

        Returns:
            List of all available presets (system + user)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT *
                FROM shopee_custom_cost_presets
                WHERE (is_system = 1 OR user_email = ?) AND is_active = 1
                ORDER BY is_system DESC, created_at DESC
            """, (user_email,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        finally:
            conn.close()

    def get_by_id(self, preset_id: int) -> Optional[Dict[str, Any]]:
        """Get preset by ID.

        Args:
            preset_id: Preset ID

        Returns:
            Dictionary with preset data or None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT *
                FROM shopee_custom_cost_presets
                WHERE preset_id = ?
            """, (preset_id,))

            row = cursor.fetchone()
            return dict(row) if row else None

        finally:
            conn.close()

    def create(self, preset_data: Dict[str, Any]) -> int:
        """Create a new custom cost preset.

        Args:
            preset_data: Dictionary with preset fields

        Returns:
            ID of created preset
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO shopee_custom_cost_presets (
                    user_email,
                    cost_name,
                    default_value,
                    default_unit,
                    calculation_type,
                    min_value,
                    max_value,
                    description,
                    example_usage,
                    is_system,
                    is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                preset_data.get('user_email'),
                preset_data['cost_name'],
                preset_data.get('default_value'),
                preset_data.get('default_unit', 'VND'),
                preset_data.get('calculation_type', 'fixed_per_order'),
                preset_data.get('min_value'),
                preset_data.get('max_value'),
                preset_data.get('description'),
                preset_data.get('example_usage'),
                preset_data.get('is_system', 0),
                preset_data.get('is_active', 1)
            ))

            conn.commit()
            return cursor.lastrowid

        finally:
            conn.close()

    def update(self, preset_id: int, preset_data: Dict[str, Any], user_email: Optional[str] = None) -> bool:
        """Update custom cost preset.

        Args:
            preset_id: Preset ID
            preset_data: Dictionary with fields to update
            user_email: User email (for permission check)

        Returns:
            True if updated successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Check if user owns this preset (can't update system presets)
            if user_email:
                cursor.execute("""
                    SELECT is_system, user_email
                    FROM shopee_custom_cost_presets
                    WHERE preset_id = ?
                """, (preset_id,))

                row = cursor.fetchone()
                if not row:
                    return False

                is_system, owner_email = row
                if is_system or (owner_email and owner_email != user_email):
                    return False  # Can't update system presets or other users' presets

            # Build dynamic update query
            fields = []
            values = []

            for key, value in preset_data.items():
                if key not in ['preset_id', 'created_at', 'is_system', 'user_email']:
                    fields.append(f"{key} = ?")
                    values.append(value)

            if not fields:
                return False

            values.append(preset_id)

            query = f"""
                UPDATE shopee_custom_cost_presets
                SET {', '.join(fields)}
                WHERE preset_id = ?
            """

            cursor.execute(query, values)
            conn.commit()

            return cursor.rowcount > 0

        finally:
            conn.close()

    def delete(self, preset_id: int, user_email: Optional[str] = None) -> bool:
        """Soft delete a custom cost preset (set is_active = 0).

        Args:
            preset_id: Preset ID
            user_email: User email (for permission check)

        Returns:
            True if deleted successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Check if user owns this preset (can't delete system presets)
            if user_email:
                cursor.execute("""
                    SELECT is_system, user_email
                    FROM shopee_custom_cost_presets
                    WHERE preset_id = ?
                """, (preset_id,))

                row = cursor.fetchone()
                if not row:
                    return False

                is_system, owner_email = row
                if is_system or (owner_email and owner_email != user_email):
                    return False

            cursor.execute("""
                UPDATE shopee_custom_cost_presets
                SET is_active = 0
                WHERE preset_id = ?
            """, (preset_id,))

            conn.commit()
            return cursor.rowcount > 0

        finally:
            conn.close()

    def search(self, search_term: str, user_email: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search presets by name or description.

        Args:
            search_term: Search term
            user_email: Optional user email to filter user presets

        Returns:
            List of matching presets
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            query = """
                SELECT *
                FROM shopee_custom_cost_presets
                WHERE is_active = 1
                  AND (cost_name LIKE ? OR description LIKE ?)
            """
            params = [f'%{search_term}%', f'%{search_term}%']

            if user_email:
                query += " AND (is_system = 1 OR user_email = ?)"
                params.append(user_email)
            else:
                query += " AND is_system = 1"

            query += " ORDER BY is_system DESC, cost_name"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

        finally:
            conn.close()
