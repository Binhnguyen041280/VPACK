"""
Profit Calculator Service for Shopee Calculator.
Implements Workflow 1: Calculate profit from selling price and costs.
"""

from typing import Dict, Any
from .fee_calculator import FeeCalculator


class ProfitCalculator:
    """Service for calculating profit from selling price."""

    def calculate(
        self,
        sale_price: float,
        cost_price: float,
        fee_config: Dict[str, Any],
        category_fee_rate: float,
        enabled_fees: Dict[str, bool],
        custom_costs: list[Dict[str, Any]],
        custom_category_fee: float = None,
        is_voucher_xtra_special: bool = False,
        expected_quantity_monthly: int = None
    ) -> Dict[str, Any]:
        """Calculate profit and all metrics.

        Args:
            sale_price: Selling price
            cost_price: Cost of goods
            fee_config: Active fee configuration
            category_fee_rate: Category-specific fee rate
            enabled_fees: Dictionary of fee toggles
            custom_costs: List of custom cost items
            custom_category_fee: Optional custom category fee override
            is_voucher_xtra_special: Special Voucher Xtra rate eligibility
            expected_quantity_monthly: Expected monthly sales quantity

        Returns:
            Dictionary with all calculation results
        """
        # Initialize fee calculator
        fee_calc = FeeCalculator(fee_config, category_fee_rate)

        # Calculate all Shopee fees
        fees = fee_calc.calculate_all_fees(
            sale_price,
            enabled_fees,
            custom_category_fee,
            is_voucher_xtra_special
        )

        # Calculate net revenue after Shopee fees
        net_revenue = sale_price - fees['total_shopee_fees']

        # Calculate custom costs
        custom_costs_result = fee_calc.calculate_custom_costs(
            custom_costs,
            sale_price,
            net_revenue,
            expected_quantity_monthly
        )

        # Calculate total costs
        total_costs = cost_price + fees['total_shopee_fees'] + custom_costs_result['total_custom_costs']

        # Calculate net profit
        net_profit = sale_price - total_costs

        # Calculate profit margin percentage
        profit_margin_percent = (net_profit / sale_price * 100) if sale_price > 0 else 0

        # Calculate ROI (Return on Investment)
        roi_percent = (net_profit / cost_price * 100) if cost_price > 0 else 0

        # Calculate breakeven price (price needed to achieve 0 profit)
        # Breakeven = Cost + Total Fees at breakeven price
        # This requires iterative calculation or formula
        breakeven_price = self._calculate_breakeven(
            cost_price,
            fee_config,
            category_fee_rate,
            enabled_fees,
            custom_costs,
            custom_category_fee,
            is_voucher_xtra_special,
            expected_quantity_monthly
        )

        return {
            # Input data
            'sale_price': sale_price,
            'cost_price': cost_price,

            # Shopee fees breakdown
            'payment_fee': fees['payment_fee'],
            'fixed_fee': fees['fixed_fee'],
            'infrastructure_fee': fees['infrastructure_fee'],
            'service_fee': fees['service_fee'],
            'total_shopee_fees': fees['total_shopee_fees'],

            # Custom costs
            'total_custom_costs': custom_costs_result['total_custom_costs'],
            'custom_costs_breakdown': custom_costs_result['breakdown'],

            # Revenue and profit
            'net_revenue': net_revenue,
            'total_costs': total_costs,
            'net_profit': net_profit,

            # Metrics
            'profit_margin_percent': round(profit_margin_percent, 2),
            'roi_percent': round(roi_percent, 2),
            'breakeven_price': round(breakeven_price, 0),

            # Additional info
            'is_profitable': net_profit > 0,
            'profit_per_unit': net_profit
        }

    def _calculate_breakeven(
        self,
        cost_price: float,
        fee_config: Dict[str, Any],
        category_fee_rate: float,
        enabled_fees: Dict[str, bool],
        custom_costs: list[Dict[str, Any]],
        custom_category_fee: float = None,
        is_voucher_xtra_special: bool = False,
        expected_quantity_monthly: int = None,
        max_iterations: int = 100
    ) -> float:
        """Calculate breakeven price using iterative approach.

        Args:
            cost_price: Cost of goods
            fee_config: Fee configuration
            category_fee_rate: Category fee rate
            enabled_fees: Enabled fees
            custom_costs: Custom costs
            custom_category_fee: Custom category fee override
            is_voucher_xtra_special: Special voucher rate
            expected_quantity_monthly: Expected monthly quantity
            max_iterations: Maximum iterations for convergence

        Returns:
            Breakeven selling price
        """
        # Start with initial guess
        price = cost_price * 1.5
        fee_calc = FeeCalculator(fee_config, category_fee_rate)

        for _ in range(max_iterations):
            # Calculate fees at this price
            fees = fee_calc.calculate_all_fees(
                price,
                enabled_fees,
                custom_category_fee,
                is_voucher_xtra_special
            )

            net_revenue = price - fees['total_shopee_fees']

            # Calculate custom costs at this price
            custom_costs_result = fee_calc.calculate_custom_costs(
                custom_costs,
                price,
                net_revenue,
                expected_quantity_monthly
            )

            # Total costs
            total_costs = cost_price + fees['total_shopee_fees'] + custom_costs_result['total_custom_costs']

            # Profit at this price
            profit = price - total_costs

            # If profit is close to 0, we found breakeven
            if abs(profit) < 1:
                return price

            # Adjust price for next iteration
            if profit < 0:
                price *= 1.01  # Increase price
            else:
                price *= 0.99  # Decrease price

        return price
