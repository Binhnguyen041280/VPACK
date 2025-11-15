"""
Pricing Calculator Service for Shopee Calculator.
Implements Workflow 2: Calculate selling price from cost and desired profit/margin.
"""

from typing import Dict, Any, List
from .fee_calculator import FeeCalculator
from .profit_calculator import ProfitCalculator


class PricingCalculator:
    """Service for calculating recommended selling prices."""

    def calculate(
        self,
        cost_price: float,
        fee_config: Dict[str, Any],
        category_fee_rate: float,
        enabled_fees: Dict[str, bool],
        custom_costs: list[Dict[str, Any]],
        desired_profit: float = None,
        desired_margin: float = None,
        pricing_reference_point: str = 'breakeven',
        num_price_options: int = 5,
        custom_category_fee: float = None,
        is_voucher_xtra_special: bool = False,
        expected_quantity_monthly: int = None
    ) -> Dict[str, Any]:
        """Calculate recommended selling prices.

        Args:
            cost_price: Cost of goods
            fee_config: Active fee configuration
            category_fee_rate: Category-specific fee rate
            enabled_fees: Dictionary of fee toggles
            custom_costs: List of custom cost items
            desired_profit: Optional desired profit amount
            desired_margin: Optional desired profit margin percentage
            pricing_reference_point: Reference point ('breakeven', 'target_profit', 'margin_range')
            num_price_options: Number of price options to generate (default 5)
            custom_category_fee: Optional custom category fee override
            is_voucher_xtra_special: Special Voucher Xtra rate eligibility
            expected_quantity_monthly: Expected monthly sales quantity

        Returns:
            Dictionary with recommended prices and options
        """
        profit_calc = ProfitCalculator()

        # Calculate breakeven price first
        breakeven_result = profit_calc.calculate(
            sale_price=cost_price * 2,  # Initial guess
            cost_price=cost_price,
            fee_config=fee_config,
            category_fee_rate=category_fee_rate,
            enabled_fees=enabled_fees,
            custom_costs=custom_costs,
            custom_category_fee=custom_category_fee,
            is_voucher_xtra_special=is_voucher_xtra_special,
            expected_quantity_monthly=expected_quantity_monthly
        )

        breakeven_price = breakeven_result['breakeven_price']

        # Calculate target price based on reference point
        if pricing_reference_point == 'target_profit' and desired_profit:
            # User wants specific profit amount
            target_price = self._calculate_price_for_profit(
                cost_price,
                desired_profit,
                fee_config,
                category_fee_rate,
                enabled_fees,
                custom_costs,
                custom_category_fee,
                is_voucher_xtra_special,
                expected_quantity_monthly
            )

        elif pricing_reference_point == 'target_margin' and desired_margin:
            # User wants specific profit margin
            target_price = self._calculate_price_for_margin(
                cost_price,
                desired_margin,
                fee_config,
                category_fee_rate,
                enabled_fees,
                custom_costs,
                custom_category_fee,
                is_voucher_xtra_special,
                expected_quantity_monthly
            )

        else:
            # Default to breakeven + some margin
            target_price = breakeven_price * 1.2

        # Generate price options around target
        price_options = self._generate_price_options(
            reference_price=target_price,
            breakeven_price=breakeven_price,
            num_options=num_price_options,
            cost_price=cost_price,
            fee_config=fee_config,
            category_fee_rate=category_fee_rate,
            enabled_fees=enabled_fees,
            custom_costs=custom_costs,
            custom_category_fee=custom_category_fee,
            is_voucher_xtra_special=is_voucher_xtra_special,
            expected_quantity_monthly=expected_quantity_monthly
        )

        return {
            'breakeven_price': breakeven_price,
            'recommended_price': target_price,
            'price_options': price_options,
            'num_options': len(price_options),
            'reference_point': pricing_reference_point
        }

    def _calculate_price_for_profit(
        self,
        cost_price: float,
        desired_profit: float,
        fee_config: Dict[str, Any],
        category_fee_rate: float,
        enabled_fees: Dict[str, bool],
        custom_costs: list[Dict[str, Any]],
        custom_category_fee: float = None,
        is_voucher_xtra_special: bool = False,
        expected_quantity_monthly: int = None,
        max_iterations: int = 100
    ) -> float:
        """Calculate price needed to achieve desired profit.

        Args:
            cost_price: Cost of goods
            desired_profit: Target profit amount
            Other args: Same as calculate()
            max_iterations: Maximum iterations

        Returns:
            Selling price that achieves desired profit
        """
        # Start with initial guess
        price = cost_price + desired_profit
        fee_calc = FeeCalculator(fee_config, category_fee_rate)
        profit_calc = ProfitCalculator()

        for _ in range(max_iterations):
            result = profit_calc.calculate(
                sale_price=price,
                cost_price=cost_price,
                fee_config=fee_config,
                category_fee_rate=category_fee_rate,
                enabled_fees=enabled_fees,
                custom_costs=custom_costs,
                custom_category_fee=custom_category_fee,
                is_voucher_xtra_special=is_voucher_xtra_special,
                expected_quantity_monthly=expected_quantity_monthly
            )

            actual_profit = result['net_profit']

            # If actual profit is close to desired, we're done
            if abs(actual_profit - desired_profit) < 10:
                return price

            # Adjust price
            profit_diff = desired_profit - actual_profit
            price += profit_diff * 1.1  # Overshoot slightly for faster convergence

        return price

    def _calculate_price_for_margin(
        self,
        cost_price: float,
        desired_margin: float,
        fee_config: Dict[str, Any],
        category_fee_rate: float,
        enabled_fees: Dict[str, bool],
        custom_costs: list[Dict[str, Any]],
        custom_category_fee: float = None,
        is_voucher_xtra_special: bool = False,
        expected_quantity_monthly: int = None,
        max_iterations: int = 100
    ) -> float:
        """Calculate price needed to achieve desired profit margin.

        Args:
            cost_price: Cost of goods
            desired_margin: Target profit margin percentage
            Other args: Same as calculate()
            max_iterations: Maximum iterations

        Returns:
            Selling price that achieves desired margin
        """
        # Start with initial guess based on margin
        price = cost_price / (1 - desired_margin / 100)
        profit_calc = ProfitCalculator()

        for _ in range(max_iterations):
            result = profit_calc.calculate(
                sale_price=price,
                cost_price=cost_price,
                fee_config=fee_config,
                category_fee_rate=category_fee_rate,
                enabled_fees=enabled_fees,
                custom_costs=custom_costs,
                custom_category_fee=custom_category_fee,
                is_voucher_xtra_special=is_voucher_xtra_special,
                expected_quantity_monthly=expected_quantity_monthly
            )

            actual_margin = result['profit_margin_percent']

            # If actual margin is close to desired, we're done
            if abs(actual_margin - desired_margin) < 0.1:
                return price

            # Adjust price
            margin_diff = desired_margin - actual_margin
            price *= (1 + margin_diff / 100)

        return price

    def _generate_price_options(
        self,
        reference_price: float,
        breakeven_price: float,
        num_options: int,
        cost_price: float,
        fee_config: Dict[str, Any],
        category_fee_rate: float,
        enabled_fees: Dict[str, bool],
        custom_costs: list[Dict[str, Any]],
        custom_category_fee: float = None,
        is_voucher_xtra_special: bool = False,
        expected_quantity_monthly: int = None
    ) -> List[Dict[str, Any]]:
        """Generate price options around reference price.

        Args:
            reference_price: Reference/target price
            breakeven_price: Calculated breakeven price
            num_options: Number of options to generate
            Other args: Same as calculate()

        Returns:
            List of price option dictionaries
        """
        profit_calc = ProfitCalculator()
        options = []

        # Generate prices: some below reference, some above
        # Range: breakeven to reference * 1.5
        min_price = breakeven_price
        max_price = reference_price * 1.5

        # Generate evenly spaced prices
        step = (max_price - min_price) / (num_options - 1) if num_options > 1 else 0

        for i in range(num_options):
            price = min_price + (i * step)

            # Round to nearest 1000
            price = round(price / 1000) * 1000

            # Calculate full metrics for this price
            result = profit_calc.calculate(
                sale_price=price,
                cost_price=cost_price,
                fee_config=fee_config,
                category_fee_rate=category_fee_rate,
                enabled_fees=enabled_fees,
                custom_costs=custom_costs,
                custom_category_fee=custom_category_fee,
                is_voucher_xtra_special=is_voucher_xtra_special,
                expected_quantity_monthly=expected_quantity_monthly
            )

            options.append({
                'price': price,
                'profit': result['net_profit'],
                'margin_percent': result['profit_margin_percent'],
                'roi_percent': result['roi_percent'],
                'total_fees': result['total_shopee_fees'],
                'total_custom_costs': result['total_custom_costs'],
                'is_profitable': result['is_profitable'],
                'is_breakeven': abs(result['net_profit']) < 100,
                'is_recommended': abs(price - reference_price) < 5000
            })

        return options
