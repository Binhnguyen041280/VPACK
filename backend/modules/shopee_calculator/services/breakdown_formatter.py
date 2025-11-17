"""
Breakdown Formatter Service for Shopee Calculator.
Formats calculation results in a detailed step-by-step breakdown similar to Shopee's calculation display.
"""

from typing import Dict, Any, List


class BreakdownFormatter:
    """Service for formatting calculation breakdown in Shopee style."""

    @staticmethod
    def format_profit_breakdown(calc_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format profit calculation breakdown.

        Args:
            calc_result: Calculation result from ProfitCalculator

        Returns:
            Dictionary with formatted breakdown
        """
        sale_price = calc_result['sale_price']
        cost_price = calc_result['cost_price']

        # Build step-by-step breakdown
        breakdown = {
            'calculation_type': 'profit',
            'sections': []
        }

        # Section 1: Giá bán
        breakdown['sections'].append({
            'title': 'Giá bán',
            'items': [
                {
                    'label': 'Giá bán sản phẩm',
                    'value': sale_price,
                    'formatted': f'{sale_price:,.0f} VND',
                    'type': 'base',
                    'highlight': True
                }
            ],
            'subtotal': None
        })

        # Section 2: Phí Shopee
        shopee_fees_section = {
            'title': 'Phí Shopee',
            'items': [],
            'subtotal': {
                'label': 'Tổng phí Shopee',
                'value': -calc_result['total_shopee_fees'],
                'formatted': f'-{calc_result["total_shopee_fees"]:,.0f} VND',
                'type': 'negative'
            }
        }

        if calc_result.get('payment_fee', 0) > 0:
            percent = calc_result['payment_fee'] / sale_price * 100 if sale_price > 0 else 0
            shopee_fees_section['items'].append({
                'label': f'Phí thanh toán ({percent:.2f}%)',
                'value': -calc_result['payment_fee'],
                'formatted': f'-{calc_result["payment_fee"]:,.0f} VND',
                'type': 'fee',
                'calculation': f'{sale_price:,.0f} × {percent:.2f}% = {calc_result["payment_fee"]:,.0f}'
            })

        if calc_result.get('fixed_fee', 0) > 0:
            percent = calc_result['fixed_fee'] / sale_price * 100 if sale_price > 0 else 0
            shopee_fees_section['items'].append({
                'label': f'Phí cố định - Hoa hồng ({percent:.2f}%)',
                'value': -calc_result['fixed_fee'],
                'formatted': f'-{calc_result["fixed_fee"]:,.0f} VND',
                'type': 'fee',
                'calculation': f'{sale_price:,.0f} × {percent:.2f}% = {calc_result["fixed_fee"]:,.0f}'
            })

        if calc_result.get('infrastructure_fee', 0) > 0:
            shopee_fees_section['items'].append({
                'label': 'Phí hạ tầng',
                'value': -calc_result['infrastructure_fee'],
                'formatted': f'-{calc_result["infrastructure_fee"]:,.0f} VND',
                'type': 'fee',
                'calculation': f'{calc_result["infrastructure_fee"]:,.0f} VND cố định/đơn'
            })

        if calc_result.get('service_fee', 0) > 0:
            shopee_fees_section['items'].append({
                'label': 'Phí dịch vụ (Voucher Xtra, PiShop...)',
                'value': -calc_result['service_fee'],
                'formatted': f'-{calc_result["service_fee"]:,.0f} VND',
                'type': 'fee',
                'calculation': f'Tùy chọn dịch vụ'
            })

        breakdown['sections'].append(shopee_fees_section)

        # Section 3: Doanh thu ròng sau phí Shopee
        net_revenue = calc_result['net_revenue']
        breakdown['sections'].append({
            'title': 'Doanh thu ròng sau phí Shopee',
            'items': [
                {
                    'label': 'Giá bán - Phí Shopee',
                    'value': net_revenue,
                    'formatted': f'{net_revenue:,.0f} VND',
                    'type': 'subtotal',
                    'highlight': True,
                    'calculation': f'{sale_price:,.0f} - {calc_result["total_shopee_fees"]:,.0f} = {net_revenue:,.0f}'
                }
            ],
            'subtotal': None
        })

        # Section 4: Chi phí khác
        if calc_result.get('total_custom_costs', 0) > 0:
            custom_costs_section = {
                'title': 'Chi phí khác',
                'items': [],
                'subtotal': {
                    'label': 'Tổng chi phí khác',
                    'value': -calc_result['total_custom_costs'],
                    'formatted': f'-{calc_result["total_custom_costs"]:,.0f} VND',
                    'type': 'negative'
                }
            }

            # Add each custom cost
            for cost_name, cost_value in calc_result.get('custom_costs_breakdown', {}).items():
                if cost_value > 0:
                    custom_costs_section['items'].append({
                        'label': cost_name,
                        'value': -cost_value,
                        'formatted': f'-{cost_value:,.0f} VND',
                        'type': 'cost'
                    })

            breakdown['sections'].append(custom_costs_section)

        # Section 5: Giá vốn
        breakdown['sections'].append({
            'title': 'Giá vốn',
            'items': [
                {
                    'label': 'Giá vốn sản phẩm',
                    'value': -cost_price,
                    'formatted': f'-{cost_price:,.0f} VND',
                    'type': 'cost',
                    'highlight': True
                }
            ],
            'subtotal': None
        })

        # Section 6: Lợi nhuận ròng
        net_profit = calc_result['net_profit']
        is_profitable = net_profit > 0

        breakdown['sections'].append({
            'title': 'Lợi nhuận ròng',
            'items': [
                {
                    'label': 'Doanh thu ròng - Chi phí khác - Giá vốn',
                    'value': net_profit,
                    'formatted': f'{net_profit:,.0f} VND',
                    'type': 'profit' if is_profitable else 'loss',
                    'highlight': True,
                    'calculation': f'{net_revenue:,.0f} - {calc_result["total_custom_costs"]:,.0f} - {cost_price:,.0f} = {net_profit:,.0f}'
                }
            ],
            'subtotal': None
        })

        # Section 7: Chỉ số hiệu quả
        breakdown['sections'].append({
            'title': 'Chỉ số hiệu quả',
            'items': [
                {
                    'label': 'Tỷ suất lợi nhuận (Profit Margin)',
                    'value': calc_result['profit_margin_percent'],
                    'formatted': f'{calc_result["profit_margin_percent"]:.2f}%',
                    'type': 'metric',
                    'calculation': f'(Lợi nhuận / Giá bán) × 100 = ({net_profit:,.0f} / {sale_price:,.0f}) × 100'
                },
                {
                    'label': 'ROI (Return on Investment)',
                    'value': calc_result['roi_percent'],
                    'formatted': f'{calc_result["roi_percent"]:.2f}%',
                    'type': 'metric',
                    'calculation': f'(Lợi nhuận / Giá vốn) × 100 = ({net_profit:,.0f} / {cost_price:,.0f}) × 100'
                },
                {
                    'label': 'Giá hòa vốn (Breakeven)',
                    'value': calc_result['breakeven_price'],
                    'formatted': f'{calc_result["breakeven_price"]:,.0f} VND',
                    'type': 'metric',
                    'calculation': 'Giá bán tối thiểu để đạt lợi nhuận = 0'
                }
            ],
            'subtotal': None
        })

        # Summary
        breakdown['summary'] = {
            'sale_price': sale_price,
            'total_fees': calc_result['total_shopee_fees'],
            'total_custom_costs': calc_result['total_custom_costs'],
            'cost_price': cost_price,
            'total_costs': calc_result['total_costs'],
            'net_profit': net_profit,
            'profit_margin_percent': calc_result['profit_margin_percent'],
            'roi_percent': calc_result['roi_percent'],
            'is_profitable': is_profitable
        }

        return breakdown

    @staticmethod
    def format_pricing_breakdown(
        calc_result: Dict[str, Any],
        selected_price: float,
        selected_price_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format pricing calculation breakdown for a selected price option.

        Args:
            calc_result: Pricing calculation result
            selected_price: The selected price from options
            selected_price_data: Data for the selected price

        Returns:
            Dictionary with formatted breakdown
        """
        cost_price = calc_result.get('cost_price', selected_price_data.get('cost_price', 0))

        breakdown = {
            'calculation_type': 'pricing',
            'sections': []
        }

        # Section 1: Giá bán được đề xuất
        breakdown['sections'].append({
            'title': 'Giá bán được đề xuất',
            'items': [
                {
                    'label': 'Giá bán',
                    'value': selected_price,
                    'formatted': f'{selected_price:,.0f} VND',
                    'type': 'base',
                    'highlight': True
                }
            ],
            'subtotal': None
        })

        # Section 2: Phí Shopee
        total_fees = selected_price_data.get('total_fees', 0)
        shopee_fees_section = {
            'title': 'Phí Shopee',
            'items': [
                {
                    'label': 'Tổng phí Shopee (thanh toán + hoa hồng + hạ tầng)',
                    'value': -total_fees,
                    'formatted': f'-{total_fees:,.0f} VND',
                    'type': 'fee',
                    'calculation': f'Ước tính dựa trên giá bán {selected_price:,.0f} VND'
                }
            ],
            'subtotal': {
                'label': 'Tổng phí Shopee',
                'value': -total_fees,
                'formatted': f'-{total_fees:,.0f} VND',
                'type': 'negative'
            }
        }
        breakdown['sections'].append(shopee_fees_section)

        # Section 3: Chi phí khác
        total_custom_costs = selected_price_data.get('total_custom_costs', 0)
        if total_custom_costs > 0:
            breakdown['sections'].append({
                'title': 'Chi phí khác',
                'items': [
                    {
                        'label': 'Tổng chi phí khác',
                        'value': -total_custom_costs,
                        'formatted': f'-{total_custom_costs:,.0f} VND',
                        'type': 'cost'
                    }
                ],
                'subtotal': {
                    'label': 'Tổng chi phí khác',
                    'value': -total_custom_costs,
                    'formatted': f'-{total_custom_costs:,.0f} VND',
                    'type': 'negative'
                }
            })

        # Section 4: Giá vốn
        breakdown['sections'].append({
            'title': 'Giá vốn',
            'items': [
                {
                    'label': 'Giá vốn sản phẩm',
                    'value': -cost_price,
                    'formatted': f'-{cost_price:,.0f} VND',
                    'type': 'cost',
                    'highlight': True
                }
            ],
            'subtotal': None
        })

        # Section 5: Lợi nhuận dự kiến
        profit = selected_price_data.get('profit', 0)
        is_profitable = profit > 0

        breakdown['sections'].append({
            'title': 'Lợi nhuận dự kiến',
            'items': [
                {
                    'label': 'Giá bán - Tổng phí - Chi phí khác - Giá vốn',
                    'value': profit,
                    'formatted': f'{profit:,.0f} VND',
                    'type': 'profit' if is_profitable else 'loss',
                    'highlight': True,
                    'calculation': f'{selected_price:,.0f} - {total_fees:,.0f} - {total_custom_costs:,.0f} - {cost_price:,.0f} = {profit:,.0f}'
                }
            ],
            'subtotal': None
        })

        # Section 6: Chỉ số hiệu quả
        margin = selected_price_data.get('margin_percent', 0)
        roi = selected_price_data.get('roi_percent', 0)

        breakdown['sections'].append({
            'title': 'Chỉ số hiệu quả',
            'items': [
                {
                    'label': 'Tỷ suất lợi nhuận (Profit Margin)',
                    'value': margin,
                    'formatted': f'{margin:.2f}%',
                    'type': 'metric',
                    'calculation': f'(Lợi nhuận / Giá bán) × 100 = ({profit:,.0f} / {selected_price:,.0f}) × 100'
                },
                {
                    'label': 'ROI (Return on Investment)',
                    'value': roi,
                    'formatted': f'{roi:.2f}%',
                    'type': 'metric',
                    'calculation': f'(Lợi nhuận / Giá vốn) × 100 = ({profit:,.0f} / {cost_price:,.0f}) × 100'
                }
            ],
            'subtotal': None
        })

        # Summary
        breakdown['summary'] = {
            'selected_price': selected_price,
            'total_fees': total_fees,
            'total_custom_costs': total_custom_costs,
            'cost_price': cost_price,
            'profit': profit,
            'margin_percent': margin,
            'roi_percent': roi,
            'is_profitable': is_profitable,
            'breakeven_price': calc_result.get('breakeven_price', 0)
        }

        return breakdown

    @staticmethod
    def format_text_breakdown(breakdown: Dict[str, Any]) -> str:
        """Format breakdown as plain text for display.

        Args:
            breakdown: Formatted breakdown dictionary

        Returns:
            Formatted text string
        """
        lines = []
        separator = "─" * 50

        for section in breakdown['sections']:
            # Section title
            lines.append("")
            lines.append(f"📊 {section['title'].upper()}")
            lines.append(separator)

            # Section items
            for item in section['items']:
                label = item['label']
                formatted = item['formatted']
                lines.append(f"{label:.<45} {formatted:>20}")

                # Add calculation if available
                if 'calculation' in item:
                    lines.append(f"   💡 {item['calculation']}")

            # Subtotal if available
            if section.get('subtotal'):
                lines.append(separator)
                subtotal = section['subtotal']
                lines.append(f"{subtotal['label']:.<45} {subtotal['formatted']:>20}")

        # Final summary
        lines.append("")
        lines.append("=" * 50)
        summary = breakdown['summary']

        if breakdown['calculation_type'] == 'profit':
            lines.append(f"{'KẾT QUẢ CUỐI CÙNG':^50}")
            lines.append("=" * 50)
            lines.append(f"Lợi nhuận ròng: {summary['net_profit']:,.0f} VND")
            lines.append(f"Tỷ suất lợi nhuận: {summary['profit_margin_percent']:.2f}%")
            lines.append(f"ROI: {summary['roi_percent']:.2f}%")
            lines.append(f"Trạng thái: {'✅ CÓ LỜI' if summary['is_profitable'] else '❌ LỖ'}")
        else:
            lines.append(f"{'GIÁ ĐỀ XUẤT':^50}")
            lines.append("=" * 50)
            lines.append(f"Giá bán: {summary['selected_price']:,.0f} VND")
            lines.append(f"Lợi nhuận dự kiến: {summary['profit']:,.0f} VND")
            lines.append(f"Tỷ suất lợi nhuận: {summary['margin_percent']:.2f}%")
            lines.append(f"Giá hòa vốn: {summary['breakeven_price']:,.0f} VND")

        return "\n".join(lines)
