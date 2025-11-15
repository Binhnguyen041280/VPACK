"""
Fee Calculator Service for Shopee Calculator.
Handles calculation of all Shopee seller fees.
"""

from typing import Dict, Any, Optional


class FeeCalculator:
    """Service for calculating Shopee seller fees."""

    def __init__(self, fee_config: Dict[str, Any], category_fee_rate: float):
        """Initialize fee calculator.

        Args:
            fee_config: Active fee configuration
            category_fee_rate: Category-specific fee rate percentage
        """
        self.payment_fee_percent = fee_config.get('payment_fee_percent', 5.0)
        self.infrastructure_fee = fee_config.get('infrastructure_fee', 3000)
        self.voucher_xtra_percent = fee_config.get('voucher_xtra_percent', 3.0)
        self.voucher_xtra_percent_special = fee_config.get('voucher_xtra_percent_special', 2.5)
        self.voucher_xtra_cap = fee_config.get('voucher_xtra_cap', 50000)
        self.pishop_fee = fee_config.get('pishop_fee', 1620)
        self.category_fee_rate = category_fee_rate

    def calculate_payment_fee(self, sale_price: float) -> float:
        """Calculate payment processing fee.

        Args:
            sale_price: Selling price

        Returns:
            Payment fee amount
        """
        return sale_price * (self.payment_fee_percent / 100)

    def calculate_fixed_commission(
        self,
        sale_price: float,
        custom_category_fee: Optional[float] = None
    ) -> float:
        """Calculate fixed commission (category-based fee).

        Args:
            sale_price: Selling price
            custom_category_fee: Optional custom fee rate override

        Returns:
            Fixed commission amount
        """
        fee_rate = custom_category_fee if custom_category_fee is not None else self.category_fee_rate
        return sale_price * (fee_rate / 100)

    def calculate_infrastructure_fee(self) -> float:
        """Calculate infrastructure fee (fixed per order).

        Returns:
            Infrastructure fee amount
        """
        return self.infrastructure_fee

    def calculate_voucher_xtra(
        self,
        sale_price: float,
        is_special: bool = False
    ) -> float:
        """Calculate Voucher Xtra fee.

        Args:
            sale_price: Selling price
            is_special: Whether seller qualifies for special rate (≥10 Shopee Live sessions/month)

        Returns:
            Voucher Xtra fee amount (capped)
        """
        percent = self.voucher_xtra_percent_special if is_special else self.voucher_xtra_percent
        fee = sale_price * (percent / 100)

        # Apply cap
        return min(fee, self.voucher_xtra_cap)

    def calculate_pishop_fee(self) -> float:
        """Calculate PiShop fee (fixed per order).

        Returns:
            PiShop fee amount
        """
        return self.pishop_fee

    def calculate_all_fees(
        self,
        sale_price: float,
        enabled_fees: Dict[str, bool],
        custom_category_fee: Optional[float] = None,
        is_voucher_xtra_special: bool = False
    ) -> Dict[str, float]:
        """Calculate all enabled fees.

        Args:
            sale_price: Selling price
            enabled_fees: Dictionary of fee toggles (e.g., {'payment_fee': True, ...})
            custom_category_fee: Optional custom category fee rate
            is_voucher_xtra_special: Whether seller qualifies for special Voucher Xtra rate

        Returns:
            Dictionary with all fee amounts
        """
        fees = {}

        # Payment Fee
        if enabled_fees.get('payment_fee', True):
            fees['payment_fee'] = self.calculate_payment_fee(sale_price)
        else:
            fees['payment_fee'] = 0

        # Fixed Commission (Category Fee)
        if enabled_fees.get('fixed_fee', True):
            fees['fixed_fee'] = self.calculate_fixed_commission(sale_price, custom_category_fee)
        else:
            fees['fixed_fee'] = 0

        # Infrastructure Fee
        if enabled_fees.get('infrastructure_fee', True):
            fees['infrastructure_fee'] = self.calculate_infrastructure_fee()
        else:
            fees['infrastructure_fee'] = 0

        # Voucher Xtra
        if enabled_fees.get('voucher_xtra', False):
            fees['voucher_xtra'] = self.calculate_voucher_xtra(sale_price, is_voucher_xtra_special)
        else:
            fees['voucher_xtra'] = 0

        # PiShop Fee
        if enabled_fees.get('pishop_fee', False):
            fees['pishop_fee'] = self.calculate_pishop_fee()
        else:
            fees['pishop_fee'] = 0

        # Service Fee (sum of optional services)
        fees['service_fee'] = fees.get('voucher_xtra', 0) + fees.get('pishop_fee', 0)

        # Total Shopee Fees
        fees['total_shopee_fees'] = (
            fees['payment_fee'] +
            fees['fixed_fee'] +
            fees['infrastructure_fee'] +
            fees['service_fee']
        )

        return fees

    def calculate_custom_costs(
        self,
        custom_costs: list[Dict[str, Any]],
        sale_price: float,
        net_revenue: float,
        expected_quantity_monthly: Optional[int] = None
    ) -> Dict[str, float]:
        """Calculate custom costs based on their calculation types.

        Args:
            custom_costs: List of custom cost items
            sale_price: Selling price
            net_revenue: Net revenue after Shopee fees
            expected_quantity_monthly: Expected monthly sales quantity

        Returns:
            Dictionary with custom costs breakdown
        """
        total = 0
        breakdown = {}

        for cost in custom_costs:
            if not cost.get('enabled', True):
                continue

            cost_name = cost.get('cost_name', 'Unknown')
            calc_type = cost.get('calculation_type', 'fixed_per_order')
            value = cost.get('value', 0)

            amount = 0

            if calc_type == 'fixed_per_order':
                # Fixed amount per order (e.g., 25,000 VND)
                amount = value

            elif calc_type == 'fixed_per_month':
                # Monthly fixed cost divided by expected quantity
                if expected_quantity_monthly and expected_quantity_monthly > 0:
                    amount = value / expected_quantity_monthly
                else:
                    amount = 0

            elif calc_type == 'percent_of_price':
                # Percentage of selling price (e.g., 5% for ads)
                amount = sale_price * (value / 100)

            elif calc_type == 'percent_of_revenue':
                # Percentage of net revenue after fees
                amount = net_revenue * (value / 100)

            elif calc_type == 'fixed_per_transaction':
                # One-time transaction cost (e.g., withdrawal fee)
                # Divide by expected quantity to get per-order cost
                if expected_quantity_monthly and expected_quantity_monthly > 0:
                    amount = value / expected_quantity_monthly
                else:
                    amount = value

            breakdown[cost_name] = amount
            total += amount

        return {
            'total_custom_costs': total,
            'breakdown': breakdown
        }
