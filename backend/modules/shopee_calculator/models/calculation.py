"""
Calculation Model for Shopee Calculator.
Manages profit and pricing calculations with versioning.
"""

import sqlite3
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from ..database import get_db_path


class Calculation:
    """Model for Shopee calculations."""

    def __init__(self, db_path: str = None):
        """Initialize Calculation model.

        Args:
            db_path: Path to SQLite database (defaults to Shopee Calculator DB)
        """
        self.db_path = db_path or get_db_path()

    def create(self, calc_data: Dict[str, Any]) -> int:
        """Create a new calculation.

        Args:
            calc_data: Dictionary with calculation fields

        Returns:
            ID of created calculation
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Serialize JSON fields
            enabled_fees_json = json.dumps(calc_data.get('enabled_fees', {}))
            custom_costs_json = json.dumps(calc_data.get('custom_costs', []))
            price_options_json = json.dumps(calc_data.get('price_options', []))
            input_data_json = json.dumps(calc_data.get('input_data', {}))
            results_json = json.dumps(calc_data.get('results', {}))

            cursor.execute("""
                INSERT INTO shopee_calculations (
                    user_email,
                    product_name,
                    product_sku,
                    workflow_type,
                    calculation_status,
                    version,
                    parent_calc_id,
                    seller_type,
                    category_code,
                    sale_price,
                    cost_price,
                    expected_quantity_monthly,
                    enabled_fees_json,
                    custom_category_fee,
                    custom_costs_json,
                    payment_fee,
                    fixed_fee,
                    infrastructure_fee,
                    service_fee,
                    total_shopee_fees,
                    total_custom_costs,
                    net_revenue,
                    total_costs,
                    net_profit,
                    profit_margin_percent,
                    roi_percent,
                    breakeven_price,
                    recommended_price,
                    desired_profit,
                    desired_margin,
                    pricing_reference_point,
                    num_price_options,
                    price_options_json,
                    input_data_json,
                    results_json,
                    notes,
                    tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                calc_data['user_email'],
                calc_data['product_name'],
                calc_data['product_sku'],
                calc_data['workflow_type'],
                calc_data.get('calculation_status', 'draft'),
                calc_data.get('version', 1),
                calc_data.get('parent_calc_id'),
                calc_data['seller_type'],
                calc_data['category_code'],
                calc_data.get('sale_price'),
                calc_data['cost_price'],
                calc_data.get('expected_quantity_monthly'),
                enabled_fees_json,
                calc_data.get('custom_category_fee'),
                custom_costs_json,
                calc_data.get('payment_fee'),
                calc_data.get('fixed_fee'),
                calc_data.get('infrastructure_fee'),
                calc_data.get('service_fee'),
                calc_data.get('total_shopee_fees'),
                calc_data.get('total_custom_costs'),
                calc_data.get('net_revenue'),
                calc_data.get('total_costs'),
                calc_data.get('net_profit'),
                calc_data.get('profit_margin_percent'),
                calc_data.get('roi_percent'),
                calc_data.get('breakeven_price'),
                calc_data.get('recommended_price'),
                calc_data.get('desired_profit'),
                calc_data.get('desired_margin'),
                calc_data.get('pricing_reference_point'),
                calc_data.get('num_price_options', 5),
                price_options_json,
                input_data_json,
                results_json,
                calc_data.get('notes'),
                calc_data.get('tags')
            ))

            conn.commit()
            return cursor.lastrowid

        finally:
            conn.close()

    def get_by_id(self, calc_id: int, user_email: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get calculation by ID.

        Args:
            calc_id: Calculation ID
            user_email: Optional user email for permission check

        Returns:
            Dictionary with calculation data or None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            query = "SELECT * FROM shopee_calculations WHERE calc_id = ?"
            params = [calc_id]

            if user_email:
                query += " AND user_email = ?"
                params.append(user_email)

            cursor.execute(query, params)
            row = cursor.fetchone()

            if row:
                result = dict(row)
                # Parse JSON fields
                result['enabled_fees'] = json.loads(result.get('enabled_fees_json') or '{}')
                result['custom_costs'] = json.loads(result.get('custom_costs_json') or '[]')
                result['price_options'] = json.loads(result.get('price_options_json') or '[]')
                result['input_data'] = json.loads(result.get('input_data_json') or '{}')
                result['results'] = json.loads(result.get('results_json') or '{}')
                return result

            return None

        finally:
            conn.close()

    def get_user_calculations(
        self,
        user_email: str,
        workflow_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's calculations with filters.

        Args:
            user_email: User email
            workflow_type: Optional filter by workflow type
            status: Optional filter by status
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of calculation dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            query = "SELECT * FROM shopee_calculations WHERE user_email = ?"
            params = [user_email]

            if workflow_type:
                query += " AND workflow_type = ?"
                params.append(workflow_type)

            if status:
                query += " AND calculation_status = ?"
                params.append(status)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                result = dict(row)
                # Parse JSON fields
                result['enabled_fees'] = json.loads(result.get('enabled_fees_json') or '{}')
                result['custom_costs'] = json.loads(result.get('custom_costs_json') or '[]')
                result['price_options'] = json.loads(result.get('price_options_json') or '[]')
                result['input_data'] = json.loads(result.get('input_data_json') or '{}')
                result['results'] = json.loads(result.get('results_json') or '{}')
                results.append(result)

            return results

        finally:
            conn.close()

    def search_products(
        self,
        user_email: str,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search user's products by SKU or name.

        Args:
            user_email: User email
            search_term: Search term
            limit: Maximum results

        Returns:
            List of unique products
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT DISTINCT
                    product_sku,
                    product_name,
                    seller_type,
                    category_code,
                    MAX(created_at) as last_used
                FROM shopee_calculations
                WHERE user_email = ?
                  AND (product_sku LIKE ? OR product_name LIKE ?)
                GROUP BY product_sku, product_name
                ORDER BY last_used DESC
                LIMIT ?
            """, (user_email, f'%{search_term}%', f'%{search_term}%', limit))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        finally:
            conn.close()

    def get_calculation_history(self, product_sku: str, user_email: str) -> List[Dict[str, Any]]:
        """Get calculation history for a product.

        Args:
            product_sku: Product SKU
            user_email: User email

        Returns:
            List of calculations ordered by version
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT *
                FROM shopee_calculations
                WHERE product_sku = ? AND user_email = ?
                ORDER BY version DESC, created_at DESC
            """, (product_sku, user_email))

            rows = cursor.fetchall()

            results = []
            for row in rows:
                result = dict(row)
                result['enabled_fees'] = json.loads(result.get('enabled_fees_json') or '{}')
                result['custom_costs'] = json.loads(result.get('custom_costs_json') or '[]')
                result['price_options'] = json.loads(result.get('price_options_json') or '[]')
                result['input_data'] = json.loads(result.get('input_data_json') or '{}')
                result['results'] = json.loads(result.get('results_json') or '{}')
                results.append(result)

            return results

        finally:
            conn.close()

    def confirm_calculation(self, calc_id: int, user_email: str, confirmed_by: str) -> bool:
        """Confirm a draft calculation.

        Args:
            calc_id: Calculation ID
            user_email: User email (for permission check)
            confirmed_by: Email/username of confirming user

        Returns:
            True if confirmed successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE shopee_calculations
                SET calculation_status = 'confirmed',
                    confirmed_at = CURRENT_TIMESTAMP,
                    confirmed_by = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE calc_id = ? AND user_email = ? AND calculation_status = 'draft'
            """, (confirmed_by, calc_id, user_email))

            conn.commit()
            return cursor.rowcount > 0

        finally:
            conn.close()

    def create_version(self, parent_calc_id: int, calc_data: Dict[str, Any]) -> int:
        """Create a new version of a calculation.

        Args:
            parent_calc_id: Parent calculation ID
            calc_data: New calculation data

        Returns:
            ID of new version
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get parent's version
            cursor.execute("SELECT version FROM shopee_calculations WHERE calc_id = ?", (parent_calc_id,))
            row = cursor.fetchone()

            if not row:
                raise ValueError(f"Parent calculation {parent_calc_id} not found")

            new_version = row[0] + 1

            # Set parent and version
            calc_data['parent_calc_id'] = parent_calc_id
            calc_data['version'] = new_version

            # Create new calculation
            return self.create(calc_data)

        finally:
            conn.close()

    def update(self, calc_id: int, calc_data: Dict[str, Any], user_email: Optional[str] = None) -> bool:
        """Update calculation.

        Args:
            calc_id: Calculation ID
            calc_data: Dictionary with fields to update
            user_email: User email (for permission check)

        Returns:
            True if updated successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Build dynamic update query
            fields = []
            values = []

            for key, value in calc_data.items():
                if key in ['enabled_fees', 'custom_costs', 'price_options', 'input_data', 'results']:
                    # JSON fields
                    fields.append(f"{key}_json = ?")
                    values.append(json.dumps(value))
                elif key not in ['calc_id', 'created_at', 'user_email']:
                    fields.append(f"{key} = ?")
                    values.append(value)

            if not fields:
                return False

            fields.append("updated_at = CURRENT_TIMESTAMP")

            query = f"UPDATE shopee_calculations SET {', '.join(fields)} WHERE calc_id = ?"
            values.append(calc_id)

            if user_email:
                query += " AND user_email = ?"
                values.append(user_email)

            cursor.execute(query, values)
            conn.commit()

            return cursor.rowcount > 0

        finally:
            conn.close()

    def delete(self, calc_id: int, user_email: str) -> bool:
        """Delete a calculation.

        Args:
            calc_id: Calculation ID
            user_email: User email (for permission check)

        Returns:
            True if deleted successfully
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                DELETE FROM shopee_calculations
                WHERE calc_id = ? AND user_email = ?
            """, (calc_id, user_email))

            conn.commit()
            return cursor.rowcount > 0

        finally:
            conn.close()
