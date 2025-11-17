"""
Fee Configuration Model for Shopee Calculator.
Manages Shopee seller fee configurations with effective dates.
"""

import sqlite3
from typing import Optional, Dict, Any
from datetime import datetime
from ..database import get_db_path


class FeeConfig:
    """Model for Shopee fee configurations."""

    def __init__(self, db_path: str = None):
        """Initialize FeeConfig model.

        Args:
            db_path: Path to SQLite database (defaults to Shopee Calculator DB)
        """
        self.db_path = db_path or get_db_path()

    def get_active_config(self) -> Optional[Dict[str, Any]]:
        """Get currently active fee configuration.

        Returns:
            Dictionary with active fee config or None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT *
                FROM shopee_fee_configs
                WHERE is_active = 1
                  AND effective_date <= DATE('now')
                  AND (end_date IS NULL OR end_date > DATE('now'))
                ORDER BY effective_date DESC
                LIMIT 1
            """)

            row = cursor.fetchone()
            return dict(row) if row else None

        finally:
            conn.close()

    def get_by_id(self, config_id: int) -> Optional[Dict[str, Any]]:
        """Get fee configuration by ID.

        Args:
            config_id: Configuration ID

        Returns:
            Dictionary with fee config or None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT *
                FROM shopee_fee_configs
                WHERE config_id = ?
            """, (config_id,))

            row = cursor.fetchone()
            return dict(row) if row else None

        finally:
            conn.close()

    def get_all(self, include_inactive: bool = False) -> list[Dict[str, Any]]:
        """Get all fee configurations.

        Args:
            include_inactive: Whether to include inactive configs

        Returns:
            List of fee configuration dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            query = """
                SELECT *
                FROM shopee_fee_configs
                WHERE 1=1
            """

            if not include_inactive:
                query += " AND is_active = 1"

            query += " ORDER BY effective_date DESC"

            cursor.execute(query)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

        finally:
            conn.close()

    def create(self, config_data: Dict[str, Any]) -> int:
        """Create a new fee configuration.

        Args:
            config_data: Dictionary with fee config fields

        Returns:
            ID of created config
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO shopee_fee_configs (
                    config_name,
                    payment_fee_percent,
                    infrastructure_fee,
                    voucher_xtra_percent,
                    voucher_xtra_percent_special,
                    voucher_xtra_cap,
                    pishop_fee,
                    effective_date,
                    end_date,
                    is_active,
                    created_by,
                    notes,
                    source_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                config_data['config_name'],
                config_data.get('payment_fee_percent', 5.0),
                config_data.get('infrastructure_fee', 3000),
                config_data.get('voucher_xtra_percent', 3.0),
                config_data.get('voucher_xtra_percent_special', 2.5),
                config_data.get('voucher_xtra_cap', 50000),
                config_data.get('pishop_fee', 1620),
                config_data['effective_date'],
                config_data.get('end_date'),
                config_data.get('is_active', 1),
                config_data.get('created_by'),
                config_data.get('notes'),
                config_data.get('source_url')
            ))

            conn.commit()
            return cursor.lastrowid

        finally:
            conn.close()

    def update(self, config_id: int, config_data: Dict[str, Any]) -> bool:
        """Update fee configuration.

        Args:
            config_id: Configuration ID
            config_data: Dictionary with fields to update

        Returns:
            True if updated successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Build dynamic update query
            fields = []
            values = []

            for key, value in config_data.items():
                if key not in ['config_id', 'created_at']:
                    fields.append(f"{key} = ?")
                    values.append(value)

            if not fields:
                return False

            fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(config_id)

            query = f"""
                UPDATE shopee_fee_configs
                SET {', '.join(fields)}
                WHERE config_id = ?
            """

            cursor.execute(query, values)
            conn.commit()

            return cursor.rowcount > 0

        finally:
            conn.close()

    def deactivate(self, config_id: int, end_date: Optional[str] = None) -> bool:
        """Deactivate a fee configuration.

        Args:
            config_id: Configuration ID
            end_date: Optional end date (defaults to today)

        Returns:
            True if deactivated successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            if end_date is None:
                end_date = datetime.now().date().isoformat()

            cursor.execute("""
                UPDATE shopee_fee_configs
                SET is_active = 0,
                    end_date = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE config_id = ?
            """, (end_date, config_id))

            conn.commit()
            return cursor.rowcount > 0

        finally:
            conn.close()
