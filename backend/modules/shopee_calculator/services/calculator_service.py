"""
Main Calculator Service for Shopee Calculator.
Coordinates all calculation workflows and database operations.
"""

from typing import Dict, Any, Optional
from ..models import Calculation, FeeConfig, Category
from ..database import get_db_path
from .profit_calculator import ProfitCalculator
from .pricing_calculator import PricingCalculator
from .breakdown_formatter import BreakdownFormatter


class CalculatorService:
    """Main service for Shopee Calculator operations."""

    def __init__(self, db_path: str = None):
        """Initialize calculator service.

        Args:
            db_path: Path to SQLite database (defaults to Shopee Calculator DB)
        """
        self.db_path = db_path or get_db_path()
        self.calculation_model = Calculation(self.db_path)
        self.fee_config_model = FeeConfig(self.db_path)
        self.category_model = Category(self.db_path)
        self.profit_calc = ProfitCalculator()
        self.pricing_calc = PricingCalculator()

    def calculate_profit(
        self,
        user_email: str,
        product_name: str,
        product_sku: str,
        seller_type: str,
        category_code: str,
        sale_price: float,
        cost_price: float,
        enabled_fees: Dict[str, bool],
        custom_costs: list[Dict[str, Any]],
        custom_category_fee: Optional[float] = None,
        is_voucher_xtra_special: bool = False,
        expected_quantity_monthly: Optional[int] = None,
        notes: Optional[str] = None,
        tags: Optional[str] = None,
        save_calculation: bool = False
    ) -> Dict[str, Any]:
        """Execute profit calculation workflow.

        Args:
            user_email: User email
            product_name: Product name
            product_sku: Product SKU
            seller_type: Seller type ('mall' or 'non_mall')
            category_code: Category code
            sale_price: Selling price
            cost_price: Cost of goods
            enabled_fees: Dictionary of fee toggles
            custom_costs: List of custom cost items
            custom_category_fee: Optional custom category fee override
            is_voucher_xtra_special: Special Voucher Xtra rate eligibility
            expected_quantity_monthly: Expected monthly sales quantity
            notes: Optional notes
            tags: Optional tags
            save_calculation: Whether to save to database

        Returns:
            Calculation results dictionary
        """
        # Get active fee config
        fee_config = self.fee_config_model.get_active_config()
        if not fee_config:
            raise ValueError("No active fee configuration found")

        # Get category fee rate
        category = self.category_model.get_by_code(category_code)
        if not category:
            raise ValueError(f"Category {category_code} not found")

        category_fee_rate = category['fee_rate_percent']

        # Perform calculation
        result = self.profit_calc.calculate(
            sale_price=sale_price,
            cost_price=cost_price,
            fee_config=fee_config,
            category_fee_rate=category_fee_rate,
            enabled_fees=enabled_fees,
            custom_costs=custom_costs,
            custom_category_fee=custom_category_fee,
            is_voucher_xtra_special=is_voucher_xtra_special,
            expected_quantity_monthly=expected_quantity_monthly
        )

        # Add detailed breakdown
        breakdown = BreakdownFormatter.format_profit_breakdown(result)
        result['breakdown'] = breakdown
        result['breakdown_text'] = BreakdownFormatter.format_text_breakdown(breakdown)

        # Save to database if requested
        if save_calculation:
            calc_data = {
                'user_email': user_email,
                'product_name': product_name,
                'product_sku': product_sku,
                'workflow_type': 'profit',
                'seller_type': seller_type,
                'category_code': category_code,
                'sale_price': sale_price,
                'cost_price': cost_price,
                'expected_quantity_monthly': expected_quantity_monthly,
                'enabled_fees': enabled_fees,
                'custom_category_fee': custom_category_fee,
                'custom_costs': custom_costs,
                'payment_fee': result['payment_fee'],
                'fixed_fee': result['fixed_fee'],
                'infrastructure_fee': result['infrastructure_fee'],
                'service_fee': result['service_fee'],
                'total_shopee_fees': result['total_shopee_fees'],
                'total_custom_costs': result['total_custom_costs'],
                'net_revenue': result['net_revenue'],
                'total_costs': result['total_costs'],
                'net_profit': result['net_profit'],
                'profit_margin_percent': result['profit_margin_percent'],
                'roi_percent': result['roi_percent'],
                'breakeven_price': result['breakeven_price'],
                'notes': notes,
                'tags': tags,
                'input_data': {
                    'sale_price': sale_price,
                    'cost_price': cost_price,
                    'seller_type': seller_type,
                    'category_code': category_code
                },
                'results': result
            }

            calc_id = self.calculation_model.create(calc_data)
            result['calc_id'] = calc_id
            result['saved'] = True
        else:
            result['saved'] = False

        return result

    def calculate_pricing(
        self,
        user_email: str,
        product_name: str,
        product_sku: str,
        seller_type: str,
        category_code: str,
        cost_price: float,
        enabled_fees: Dict[str, bool],
        custom_costs: list[Dict[str, Any]],
        desired_profit: Optional[float] = None,
        desired_margin: Optional[float] = None,
        pricing_reference_point: str = 'breakeven',
        num_price_options: int = 5,
        custom_category_fee: Optional[float] = None,
        is_voucher_xtra_special: bool = False,
        expected_quantity_monthly: Optional[int] = None,
        notes: Optional[str] = None,
        tags: Optional[str] = None,
        save_calculation: bool = False
    ) -> Dict[str, Any]:
        """Execute pricing calculation workflow.

        Args:
            user_email: User email
            product_name: Product name
            product_sku: Product SKU
            seller_type: Seller type ('mall' or 'non_mall')
            category_code: Category code
            cost_price: Cost of goods
            enabled_fees: Dictionary of fee toggles
            custom_costs: List of custom cost items
            desired_profit: Optional desired profit amount
            desired_margin: Optional desired profit margin percentage
            pricing_reference_point: Reference point for pricing
            num_price_options: Number of price options to generate
            custom_category_fee: Optional custom category fee override
            is_voucher_xtra_special: Special Voucher Xtra rate eligibility
            expected_quantity_monthly: Expected monthly sales quantity
            notes: Optional notes
            tags: Optional tags
            save_calculation: Whether to save to database

        Returns:
            Pricing results dictionary
        """
        # Get active fee config
        fee_config = self.fee_config_model.get_active_config()
        if not fee_config:
            raise ValueError("No active fee configuration found")

        # Get category fee rate
        category = self.category_model.get_by_code(category_code)
        if not category:
            raise ValueError(f"Category {category_code} not found")

        category_fee_rate = category['fee_rate_percent']

        # Perform calculation
        result = self.pricing_calc.calculate(
            cost_price=cost_price,
            fee_config=fee_config,
            category_fee_rate=category_fee_rate,
            enabled_fees=enabled_fees,
            custom_costs=custom_costs,
            desired_profit=desired_profit,
            desired_margin=desired_margin,
            pricing_reference_point=pricing_reference_point,
            num_price_options=num_price_options,
            custom_category_fee=custom_category_fee,
            is_voucher_xtra_special=is_voucher_xtra_special,
            expected_quantity_monthly=expected_quantity_monthly
        )

        # Add cost_price to result for breakdown
        result['cost_price'] = cost_price

        # Add detailed breakdown for recommended price
        recommended_price = result['recommended_price']
        # Find the price option closest to recommended
        selected_option = None
        for option in result['price_options']:
            if option.get('is_recommended') or abs(option['price'] - recommended_price) < 1000:
                selected_option = option
                break

        if not selected_option and result['price_options']:
            # Use first option if no recommended found
            selected_option = result['price_options'][0]

        if selected_option:
            breakdown = BreakdownFormatter.format_pricing_breakdown(
                result,
                selected_option['price'],
                selected_option
            )
            result['breakdown'] = breakdown
            result['breakdown_text'] = BreakdownFormatter.format_text_breakdown(breakdown)

        # Save to database if requested
        if save_calculation:
            calc_data = {
                'user_email': user_email,
                'product_name': product_name,
                'product_sku': product_sku,
                'workflow_type': 'pricing',
                'seller_type': seller_type,
                'category_code': category_code,
                'cost_price': cost_price,
                'expected_quantity_monthly': expected_quantity_monthly,
                'enabled_fees': enabled_fees,
                'custom_category_fee': custom_category_fee,
                'custom_costs': custom_costs,
                'breakeven_price': result['breakeven_price'],
                'recommended_price': result['recommended_price'],
                'desired_profit': desired_profit,
                'desired_margin': desired_margin,
                'pricing_reference_point': pricing_reference_point,
                'num_price_options': num_price_options,
                'price_options': result['price_options'],
                'notes': notes,
                'tags': tags,
                'input_data': {
                    'cost_price': cost_price,
                    'seller_type': seller_type,
                    'category_code': category_code,
                    'desired_profit': desired_profit,
                    'desired_margin': desired_margin
                },
                'results': result
            }

            calc_id = self.calculation_model.create(calc_data)
            result['calc_id'] = calc_id
            result['saved'] = True
        else:
            result['saved'] = False

        return result

    def get_calculation(self, calc_id: int, user_email: str) -> Optional[Dict[str, Any]]:
        """Retrieve a saved calculation.

        Args:
            calc_id: Calculation ID
            user_email: User email (for permission check)

        Returns:
            Calculation data or None
        """
        return self.calculation_model.get_by_id(calc_id, user_email)

    def search_products(self, user_email: str, search_term: str) -> list[Dict[str, Any]]:
        """Search user's products.

        Args:
            user_email: User email
            search_term: Search term

        Returns:
            List of matching products
        """
        return self.calculation_model.search_products(user_email, search_term)

    def get_categories(self, seller_type: str) -> list[Dict[str, Any]]:
        """Get categories for seller type.

        Args:
            seller_type: Seller type ('mall' or 'non_mall')

        Returns:
            List of categories
        """
        return self.category_model.get_by_seller_type(seller_type)

    def confirm_calculation(self, calc_id: int, user_email: str) -> bool:
        """Confirm a draft calculation.

        Args:
            calc_id: Calculation ID
            user_email: User email

        Returns:
            True if confirmed successfully
        """
        return self.calculation_model.confirm_calculation(calc_id, user_email, user_email)
