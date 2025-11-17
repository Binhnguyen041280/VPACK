"""
Seed data script for Shopee Calculator module.
Populates initial fee configurations, product categories, and custom cost presets.

Based on official Shopee seller fee information as of January 2025.
Sources:
- https://banhang.shopee.vn/edu/article/13019
- https://banhang.shopee.vn/edu/article/11761
"""

import sqlite3
import os
from datetime import datetime

try:
    from .database import get_db_path
except ImportError:
    # When running standalone
    from database import get_db_path


def seed_shopee_data(db_path=None):
    """Seed Shopee Calculator tables with initial data."""

    if db_path is None:
        db_path = get_db_path()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("🌱 Seeding Shopee Calculator data...")

    try:
        # ==================== 1. FEE CONFIGS ====================
        print("  📊 Seeding fee configurations...")

        # Fee config effective from July 1, 2025
        cursor.execute("""
            INSERT OR REPLACE INTO shopee_fee_configs (
                config_id,
                config_name,
                payment_fee_percent,
                infrastructure_fee,
                voucher_xtra_percent,
                voucher_xtra_percent_special,
                voucher_xtra_cap,
                pishop_fee,
                effective_date,
                is_active,
                notes,
                source_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            1,
            'Shopee Fee Config 2025',
            5.0,  # Payment fee
            3000,  # Infrastructure fee
            3.0,  # Voucher Xtra normal
            2.5,  # Voucher Xtra special (for stores using ≥10 Shopee Live sessions/month)
            50000,  # Voucher Xtra cap
            1620,  # PiShop fee
            '2025-07-01',
            1,
            'Fee structure effective from July 1, 2025. Payment fee changed from 4.91% to 5%. Infrastructure fee from 2,300 VND to 3,000 VND.',
            'https://banhang.shopee.vn/edu/article/13019'
        ))

        # ==================== 2. CATEGORIES ====================
        print("  📦 Seeding product categories...")

        # Non-Mall categories with fee rates
        non_mall_categories = [
            ('electronics', 'Thiết bị điện tử', 'Electronics', 1.47, 'https://banhang.shopee.vn/edu/article/11761'),
            ('home_appliances', 'Thiết bị gia dụng', 'Home Appliances', 1.47, 'https://banhang.shopee.vn/edu/article/11761'),
            ('computers_laptops', 'Máy tính & Laptop', 'Computers & Laptops', 1.47, 'https://banhang.shopee.vn/edu/article/11761'),
            ('cameras', 'Máy ảnh & Máy quay', 'Cameras & Camcorders', 1.47, 'https://banhang.shopee.vn/edu/article/11761'),
            ('health_beauty', 'Sức khỏe & Làm đẹp', 'Health & Beauty', 11.78, 'https://banhang.shopee.vn/edu/article/11761'),
            ('watches', 'Đồng hồ', 'Watches', 2.94, 'https://banhang.shopee.vn/edu/article/11761'),
            ('fashion_women', 'Thời trang nữ', 'Women\'s Fashion', 9.82, 'https://banhang.shopee.vn/edu/article/11761'),
            ('fashion_men', 'Thời trang nam', 'Men\'s Fashion', 9.82, 'https://banhang.shopee.vn/edu/article/11761'),
            ('bags_luggage', 'Túi xách & Vali', 'Bags & Luggage', 9.82, 'https://banhang.shopee.vn/edu/article/11761'),
            ('shoes', 'Giày dép', 'Shoes', 9.82, 'https://banhang.shopee.vn/edu/article/11761'),
            ('accessories', 'Phụ kiện thời trang', 'Fashion Accessories', 9.82, 'https://banhang.shopee.vn/edu/article/11761'),
            ('baby_kids', 'Mẹ & Bé', 'Baby & Kids', 9.82, 'https://banhang.shopee.vn/edu/article/11761'),
            ('home_living', 'Nhà cửa & Đời sống', 'Home & Living', 4.9, 'https://banhang.shopee.vn/edu/article/11761'),
            ('sports_outdoors', 'Thể thao & Du lịch', 'Sports & Outdoors', 8.33, 'https://banhang.shopee.vn/edu/article/11761'),
            ('automotive', 'Ô tô & Xe máy', 'Automotive', 4.9, 'https://banhang.shopee.vn/edu/article/11761'),
            ('hobbies_books', 'Sách & Văn phòng phẩm', 'Books & Hobbies', 8.33, 'https://banhang.shopee.vn/edu/article/11761'),
            ('pet_care', 'Thú cưng', 'Pet Care', 9.82, 'https://banhang.shopee.vn/edu/article/11761'),
            ('groceries', 'Bách hóa Online', 'Groceries', 4.9, 'https://banhang.shopee.vn/edu/article/11761'),
        ]

        for idx, (code, name_vi, name_en, fee_rate, source_url) in enumerate(non_mall_categories, 1):
            cursor.execute("""
                INSERT OR REPLACE INTO shopee_categories (
                    category_code,
                    category_name,
                    category_name_en,
                    seller_type,
                    fee_rate_percent,
                    display_order,
                    is_active,
                    effective_date,
                    source_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f'non_mall_{code}',
                name_vi,
                name_en,
                'non_mall',
                fee_rate,
                idx,
                1,
                '2025-01-01',
                source_url
            ))

        # Mall categories with fee rates
        mall_categories = [
            ('electronics', 'Thiết bị điện tử', 'Electronics', 1.1, 'https://banhang.shopee.vn/edu/article/11761'),
            ('home_appliances', 'Thiết bị gia dụng', 'Home Appliances', 1.1, 'https://banhang.shopee.vn/edu/article/11761'),
            ('computers_laptops', 'Máy tính & Laptop', 'Computers & Laptops', 1.1, 'https://banhang.shopee.vn/edu/article/11761'),
            ('cameras', 'Máy ảnh & Máy quay', 'Cameras & Camcorders', 1.1, 'https://banhang.shopee.vn/edu/article/11761'),
            ('health_beauty', 'Sức khỏe & Làm đẹp', 'Health & Beauty', 7.7, 'https://banhang.shopee.vn/edu/article/11761'),
            ('watches', 'Đồng hồ', 'Watches', 2.2, 'https://banhang.shopee.vn/edu/article/11761'),
            ('fashion_women', 'Thời trang nữ', 'Women\'s Fashion', 5.5, 'https://banhang.shopee.vn/edu/article/11761'),
            ('fashion_men', 'Thời trang nam', 'Men\'s Fashion', 5.5, 'https://banhang.shopee.vn/edu/article/11761'),
            ('bags_luggage', 'Túi xách & Vali', 'Bags & Luggage', 5.5, 'https://banhang.shopee.vn/edu/article/11761'),
            ('shoes', 'Giày dép', 'Shoes', 5.5, 'https://banhang.shopee.vn/edu/article/11761'),
            ('accessories', 'Phụ kiện thời trang', 'Fashion Accessories', 5.5, 'https://banhang.shopee.vn/edu/article/11761'),
            ('baby_kids', 'Mẹ & Bé', 'Baby & Kids', 5.5, 'https://banhang.shopee.vn/edu/article/11761'),
            ('home_living', 'Nhà cửa & Đời sống', 'Home & Living', 3.3, 'https://banhang.shopee.vn/edu/article/11761'),
            ('sports_outdoors', 'Thể thao & Du lịch', 'Sports & Outdoors', 5.5, 'https://banhang.shopee.vn/edu/article/11761'),
            ('automotive', 'Ô tô & Xe máy', 'Automotive', 3.3, 'https://banhang.shopee.vn/edu/article/11761'),
            ('hobbies_books', 'Sách & Văn phòng phẩm', 'Books & Hobbies', 5.5, 'https://banhang.shopee.vn/edu/article/11761'),
            ('pet_care', 'Thú cưng', 'Pet Care', 5.5, 'https://banhang.shopee.vn/edu/article/11761'),
            ('groceries', 'Bách hóa Online', 'Groceries', 3.3, 'https://banhang.shopee.vn/edu/article/11761'),
        ]

        for idx, (code, name_vi, name_en, fee_rate, source_url) in enumerate(mall_categories, 100):
            cursor.execute("""
                INSERT OR REPLACE INTO shopee_categories (
                    category_code,
                    category_name,
                    category_name_en,
                    seller_type,
                    fee_rate_percent,
                    display_order,
                    is_active,
                    effective_date,
                    source_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f'mall_{code}',
                name_vi,
                name_en,
                'mall',
                fee_rate,
                idx,
                1,
                '2025-01-01',
                source_url
            ))

        # ==================== 3. CUSTOM COST PRESETS ====================
        print("  💰 Seeding custom cost presets...")

        # System-defined presets (is_system=1)
        system_presets = [
            (
                'Chi phí vận chuyển',
                25000,
                'VND',
                'fixed_per_order',
                'Chi phí vận chuyển hàng từ kho đến khách hàng',
                'VD: Ship COD 25,000đ/đơn'
            ),
            (
                'Chi phí đóng gói',
                5000,
                'VND',
                'fixed_per_order',
                'Chi phí bao bì, túi, hộp đóng gói sản phẩm',
                'VD: Hộp carton + túi nilon = 5,000đ/đơn'
            ),
            (
                'Chi phí quảng cáo',
                5.0,
                '%',
                'percent_of_price',
                'Chi phí chạy quảng cáo Shopee Ads, Google Ads, Facebook Ads',
                'VD: Chi 5% doanh thu cho quảng cáo'
            ),
            (
                'Hoa hồng',
                3.0,
                '%',
                'percent_of_price',
                'Hoa hồng cho người giới thiệu, affiliate',
                'VD: Hoa hồng 3% cho affiliate/sale'
            ),
            (
                'Chi phí tem nhãn',
                2000,
                'VND',
                'fixed_per_order',
                'Chi phí in tem, nhãn, sticker sản phẩm',
                'VD: Tem nhãn 2,000đ/đơn'
            ),
            (
                'Phí rút tiền',
                1650,
                'VND',
                'fixed_per_transaction',
                'Phí chuyển tiền từ Shopee về tài khoản ngân hàng',
                'VD: Phí rút về ngân hàng 1,650đ/lần'
            ),
        ]

        for preset_data in system_presets:
            (cost_name, default_value, default_unit, calc_type,
             description, example_usage) = preset_data

            cursor.execute("""
                INSERT OR REPLACE INTO shopee_custom_cost_presets (
                    user_email,
                    cost_name,
                    default_value,
                    default_unit,
                    calculation_type,
                    description,
                    example_usage,
                    is_system,
                    is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                None,  # user_email (NULL for system presets)
                cost_name,
                default_value,
                default_unit,
                calc_type,
                description,
                example_usage,
                1,  # is_system
                1   # is_active
            ))

        conn.commit()
        print("✅ Seed data inserted successfully!")
        print(f"  - 1 fee config")
        print(f"  - {len(non_mall_categories)} non-mall categories")
        print(f"  - {len(mall_categories)} mall categories")
        print(f"  - {len(system_presets)} custom cost presets")

    except sqlite3.Error as e:
        print(f"❌ Error seeding data: {e}")
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == '__main__':
    # Run seed script
    seed_shopee_data()
