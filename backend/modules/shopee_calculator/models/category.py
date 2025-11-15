"""
Category Model for Shopee Calculator.
Manages product categories with fee rates for mall and non-mall sellers.
"""

import sqlite3
from typing import Optional, Dict, Any, List


class Category:
    """Model for Shopee product categories."""

    def __init__(self, db_path: str = '/app/database/events.db'):
        """Initialize Category model.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path

    def get_by_code(self, category_code: str) -> Optional[Dict[str, Any]]:
        """Get category by code.

        Args:
            category_code: Category code (e.g., 'non_mall_electronics')

        Returns:
            Dictionary with category data or None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT *
                FROM shopee_categories
                WHERE category_code = ? AND is_active = 1
            """, (category_code,))

            row = cursor.fetchone()
            return dict(row) if row else None

        finally:
            conn.close()

    def get_by_seller_type(self, seller_type: str) -> List[Dict[str, Any]]:
        """Get all categories for a seller type.

        Args:
            seller_type: Either 'mall' or 'non_mall'

        Returns:
            List of category dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT *
                FROM shopee_categories
                WHERE seller_type = ? AND is_active = 1
                ORDER BY display_order, category_name
            """, (seller_type,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        finally:
            conn.close()

    def get_all(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Get all categories.

        Args:
            include_inactive: Whether to include inactive categories

        Returns:
            List of category dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            query = """
                SELECT *
                FROM shopee_categories
                WHERE 1=1
            """

            if not include_inactive:
                query += " AND is_active = 1"

            query += " ORDER BY seller_type, display_order, category_name"

            cursor.execute(query)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

        finally:
            conn.close()

    def get_fee_rate(self, category_code: str) -> Optional[float]:
        """Get fee rate for a category.

        Args:
            category_code: Category code

        Returns:
            Fee rate percentage or None
        """
        category = self.get_by_code(category_code)
        return category['fee_rate_percent'] if category else None

    def search(self, search_term: str, seller_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search categories by name.

        Args:
            search_term: Search term for category name
            seller_type: Optional filter by seller type

        Returns:
            List of matching categories
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            query = """
                SELECT *
                FROM shopee_categories
                WHERE is_active = 1
                  AND (category_name LIKE ? OR category_name_en LIKE ? OR category_code LIKE ?)
            """
            params = [f'%{search_term}%', f'%{search_term}%', f'%{search_term}%']

            if seller_type:
                query += " AND seller_type = ?"
                params.append(seller_type)

            query += " ORDER BY display_order, category_name"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

        finally:
            conn.close()

    def create(self, category_data: Dict[str, Any]) -> int:
        """Create a new category.

        Args:
            category_data: Dictionary with category fields

        Returns:
            ID of created category
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO shopee_categories (
                    category_code,
                    category_name,
                    category_name_en,
                    seller_type,
                    fee_rate_percent,
                    description,
                    display_order,
                    is_active,
                    effective_date,
                    source_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                category_data['category_code'],
                category_data['category_name'],
                category_data.get('category_name_en'),
                category_data['seller_type'],
                category_data['fee_rate_percent'],
                category_data.get('description'),
                category_data.get('display_order', 999),
                category_data.get('is_active', 1),
                category_data.get('effective_date'),
                category_data.get('source_url')
            ))

            conn.commit()
            return cursor.lastrowid

        finally:
            conn.close()

    def update(self, category_id: int, category_data: Dict[str, Any]) -> bool:
        """Update category.

        Args:
            category_id: Category ID
            category_data: Dictionary with fields to update

        Returns:
            True if updated successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Build dynamic update query
            fields = []
            values = []

            for key, value in category_data.items():
                if key not in ['category_id', 'created_at']:
                    fields.append(f"{key} = ?")
                    values.append(value)

            if not fields:
                return False

            fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(category_id)

            query = f"""
                UPDATE shopee_categories
                SET {', '.join(fields)}
                WHERE category_id = ?
            """

            cursor.execute(query, values)
            conn.commit()

            return cursor.rowcount > 0

        finally:
            conn.close()

    def update_fee_rate(self, category_code: str, new_fee_rate: float) -> bool:
        """Update fee rate for a category.

        Args:
            category_code: Category code
            new_fee_rate: New fee rate percentage

        Returns:
            True if updated successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE shopee_categories
                SET fee_rate_percent = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE category_code = ?
            """, (new_fee_rate, category_code))

            conn.commit()
            return cursor.rowcount > 0

        finally:
            conn.close()
