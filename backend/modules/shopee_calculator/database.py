"""
Shopee Calculator Database Initialization.
Creates and manages separate database for Shopee Calculator module.
"""

import sqlite3
import os
from pathlib import Path


# Database path
DB_DIR = Path('/app/database')
DB_PATH = DB_DIR / 'shopee_calculator.db'


def get_db_path():
    """Get database path."""
    return str(DB_PATH)


def initialize_database():
    """Initialize Shopee Calculator database with all tables."""

    # Ensure directory exists
    DB_DIR.mkdir(parents=True, exist_ok=True)

    print(f"🛍️ Initializing Shopee Calculator database at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    try:
        # Enable WAL mode for better concurrency
        cursor.execute("PRAGMA journal_mode=WAL")
        print("✅ WAL mode enabled")

        # ==================== SHOPEE CALCULATOR TABLES ====================

        # 1. Shopee Fee Configs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shopee_fee_configs (
                config_id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_name TEXT NOT NULL,
                payment_fee_percent REAL NOT NULL DEFAULT 5.0,
                infrastructure_fee INTEGER NOT NULL DEFAULT 3000,
                voucher_xtra_percent REAL NOT NULL DEFAULT 3.0,
                voucher_xtra_percent_special REAL DEFAULT 2.5,
                voucher_xtra_cap INTEGER DEFAULT 50000,
                pishop_fee INTEGER DEFAULT 1620,
                effective_date DATE NOT NULL,
                end_date DATE,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                updated_by TEXT,
                notes TEXT,
                source_url TEXT
            )
        """)
        print("✅ Created shopee_fee_configs table")

        # 2. Shopee Categories Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shopee_categories (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_code TEXT NOT NULL UNIQUE,
                category_name TEXT NOT NULL,
                category_name_en TEXT,
                seller_type TEXT NOT NULL CHECK(seller_type IN ('non_mall', 'mall')),
                fee_rate_percent REAL NOT NULL,
                description TEXT,
                icon TEXT,
                display_order INTEGER DEFAULT 999,
                is_customizable BOOLEAN DEFAULT 1,
                min_fee_percent REAL DEFAULT 0,
                max_fee_percent REAL DEFAULT 20,
                min_fee_amount REAL,
                max_fee_amount REAL,
                fee_unit TEXT DEFAULT 'percent',
                calculation_type TEXT DEFAULT 'percent_of_price',
                is_active BOOLEAN DEFAULT 1,
                effective_date DATE,
                end_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_url TEXT,
                notes TEXT
            )
        """)
        print("✅ Created shopee_categories table")

        # 3. Shopee Calculations Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shopee_calculations (
                calc_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                product_name TEXT NOT NULL,
                product_sku TEXT NOT NULL,
                workflow_type TEXT NOT NULL CHECK(workflow_type IN ('profit', 'pricing')),
                calculation_status TEXT DEFAULT 'draft' CHECK(calculation_status IN ('draft', 'confirmed')),
                version INTEGER DEFAULT 1,
                parent_calc_id INTEGER,
                seller_type TEXT NOT NULL,
                category_code TEXT NOT NULL,
                sale_price REAL,
                cost_price REAL NOT NULL,
                expected_quantity_monthly INTEGER,
                enabled_fees_json TEXT,
                custom_category_fee REAL,
                custom_costs_json TEXT,
                payment_fee REAL,
                fixed_fee REAL,
                infrastructure_fee REAL,
                service_fee REAL,
                total_shopee_fees REAL,
                total_custom_costs REAL,
                net_revenue REAL,
                total_costs REAL,
                net_profit REAL,
                profit_margin_percent REAL,
                roi_percent REAL,
                breakeven_price REAL,
                recommended_price REAL,
                desired_profit REAL,
                desired_margin REAL,
                pricing_reference_point TEXT,
                num_price_options INTEGER DEFAULT 5,
                price_options_json TEXT,
                input_data_json TEXT,
                results_json TEXT,
                notes TEXT,
                tags TEXT,
                confirmed_at TIMESTAMP,
                confirmed_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_calc_id) REFERENCES shopee_calculations(calc_id) ON DELETE SET NULL
            )
        """)
        print("✅ Created shopee_calculations table")

        # 4. Shopee Custom Cost Presets Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shopee_custom_cost_presets (
                preset_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT,
                cost_name TEXT NOT NULL,
                default_value REAL,
                default_unit TEXT CHECK(default_unit IN ('VND', '%')),
                calculation_type TEXT,
                min_value REAL,
                max_value REAL,
                description TEXT,
                example_usage TEXT,
                is_system BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Created shopee_custom_cost_presets table")

        # 5. Shopee Calculation History Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shopee_calculation_history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                calc_id INTEGER NOT NULL,
                change_type TEXT NOT NULL,
                old_value_json TEXT,
                new_value_json TEXT,
                changed_fields TEXT,
                change_summary TEXT,
                changed_by TEXT NOT NULL,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (calc_id) REFERENCES shopee_calculations(calc_id) ON DELETE CASCADE
            )
        """)
        print("✅ Created shopee_calculation_history table")

        # ==================== CREATE INDEXES ====================

        print("📑 Creating indexes...")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fee_config_active ON shopee_fee_configs(is_active, effective_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category_seller ON shopee_categories(seller_type, is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category_code ON shopee_categories(category_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calc_user_product ON shopee_calculations(user_email, product_sku)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calc_sku ON shopee_calculations(product_sku)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calc_name ON shopee_calculations(product_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calc_status ON shopee_calculations(calculation_status, confirmed_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calc_version ON shopee_calculations(parent_calc_id, version)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_preset_user ON shopee_custom_cost_presets(user_email, is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_preset_system ON shopee_custom_cost_presets(is_system, is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_calc ON shopee_calculation_history(calc_id, changed_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_type ON shopee_calculation_history(change_type)")

        print("✅ Created 12 indexes")

        conn.commit()
        print(f"✅ Shopee Calculator database initialized successfully at {DB_PATH}")

        return str(DB_PATH)

    except sqlite3.Error as e:
        print(f"❌ Database initialization error: {e}")
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == '__main__':
    initialize_database()
