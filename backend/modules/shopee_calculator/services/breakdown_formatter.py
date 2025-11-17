"""
Breakdown Formatter Service for Shopee Calculator.
Formats calculation results matching Shopee's official calculation display format.

Based on Shopee's calculation structure from ShopeeAnalytics and official seller center.
"""

from typing import Dict, Any, List


class BreakdownFormatter:
    """Service for formatting calculation breakdown matching Shopee's format."""

    @staticmethod
    def format_profit_breakdown(calc_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format profit calculation breakdown matching Shopee's format.

        Args:
            calc_result: Calculation result from ProfitCalculator

        Returns:
            Dictionary with formatted breakdown matching Shopee's structure
        """
        sale_price = calc_result['sale_price']
        cost_price = calc_result['cost_price']

        # Build breakdown matching Shopee's format
        breakdown = {
            'calculation_type': 'profit',
            'sections': []
        }

        # Section 1: Giá niêm yết (Listed Price)
        breakdown['sections'].append({
            'title': 'Giá niêm yết',
            'title_en': 'Listed Price',
            'items': [
                {
                    'label': 'Giá bán sản phẩm',
                    'label_en': 'Product Price',
                    'value': sale_price,
                    'formatted': f'{sale_price:,.0f}đ',
                    'type': 'base',
                    'highlight': True
                }
            ],
            'subtotal': None
        })

        # Section 2: Phí phải trả cho Shopee (Fees payable to Shopee)
        shopee_fees_section = {
            'title': 'Phí phải trả cho Shopee',
            'title_en': 'Fees Payable to Shopee',
            'items': [],
            'subtotal': {
                'label': 'Tổng phí Shopee',
                'label_en': 'Total Shopee Fees',
                'value': -calc_result['total_shopee_fees'],
                'formatted': f'{calc_result["total_shopee_fees"]:,.0f}đ',
                'type': 'negative'
            }
        }

        # Payment Fee
        if calc_result.get('payment_fee', 0) > 0:
            percent = calc_result['payment_fee'] / sale_price * 100 if sale_price > 0 else 0
            shopee_fees_section['items'].append({
                'label': f'Phí thanh toán ({percent:.2f}%)',
                'label_en': f'Payment Fee ({percent:.2f}%)',
                'value': -calc_result['payment_fee'],
                'formatted': f'{calc_result["payment_fee"]:,.0f}đ',
                'type': 'fee',
                'formula': f'{sale_price:,.0f}đ × {percent:.2f}%',
                'detail': f'Áp dụng từ ngày 01/07/2025'
            })

        # Fixed Commission Fee
        if calc_result.get('fixed_fee', 0) > 0:
            percent = calc_result['fixed_fee'] / sale_price * 100 if sale_price > 0 else 0
            shopee_fees_section['items'].append({
                'label': f'Phí cố định ({percent:.2f}%)',
                'label_en': f'Fixed Commission ({percent:.2f}%)',
                'value': -calc_result['fixed_fee'],
                'formatted': f'{calc_result["fixed_fee"]:,.0f}đ',
                'type': 'fee',
                'formula': f'{sale_price:,.0f}đ × {percent:.2f}%',
                'detail': 'Theo ngành hàng'
            })

        # Infrastructure Fee
        if calc_result.get('infrastructure_fee', 0) > 0:
            shopee_fees_section['items'].append({
                'label': 'Phí hạ tầng',
                'label_en': 'Infrastructure Fee',
                'value': -calc_result['infrastructure_fee'],
                'formatted': f'{calc_result["infrastructure_fee"]:,.0f}đ',
                'type': 'fee',
                'formula': f'{calc_result["infrastructure_fee"]:,.0f}đ cố định/đơn',
                'detail': 'Áp dụng từ ngày 01/07/2025'
            })

        # Service Fees (Voucher Xtra, PiShop, etc.)
        if calc_result.get('service_fee', 0) > 0:
            service_fee_items = []

            # Try to breakdown service fee if we have details
            voucher_xtra_fee = calc_result.get('voucher_xtra_fee', 0)
            pishop_fee = calc_result.get('pishop_fee', 0)

            if voucher_xtra_fee > 0:
                voucher_percent = voucher_xtra_fee / sale_price * 100 if sale_price > 0 else 0
                service_fee_items.append({
                    'label': f'Voucher Xtra ({voucher_percent:.2f}%)',
                    'value': -voucher_xtra_fee,
                    'formatted': f'{voucher_xtra_fee:,.0f}đ',
                    'detail': 'Tối đa 50,000đ/sản phẩm'
                })

            if pishop_fee > 0:
                service_fee_items.append({
                    'label': 'PiShop',
                    'value': -pishop_fee,
                    'formatted': f'{pishop_fee:,.0f}đ',
                    'detail': 'Cố định/đơn'
                })

            # If no breakdown, show total service fee
            if not service_fee_items:
                shopee_fees_section['items'].append({
                    'label': 'Phí dịch vụ (Voucher Xtra, PiShop...)',
                    'label_en': 'Service Fees',
                    'value': -calc_result['service_fee'],
                    'formatted': f'{calc_result["service_fee"]:,.0f}đ',
                    'type': 'fee',
                    'formula': 'Tùy chọn dịch vụ',
                    'detail': 'Các dịch vụ tùy chọn'
                })
            else:
                # Add indented service fee items
                for item in service_fee_items:
                    item['type'] = 'fee'
                    item['indent'] = True
                    shopee_fees_section['items'].append(item)

        breakdown['sections'].append(shopee_fees_section)

        # Section 3: Chi phí khác (Other Costs) - only if exists
        if calc_result.get('total_custom_costs', 0) > 0:
            custom_costs_section = {
                'title': 'Chi phí khác',
                'title_en': 'Other Costs',
                'items': [],
                'subtotal': {
                    'label': 'Tổng chi phí khác',
                    'label_en': 'Total Other Costs',
                    'value': -calc_result['total_custom_costs'],
                    'formatted': f'{calc_result["total_custom_costs"]:,.0f}đ',
                    'type': 'negative'
                }
            }

            # Add each custom cost
            for cost_name, cost_value in calc_result.get('custom_costs_breakdown', {}).items():
                if cost_value > 0:
                    custom_costs_section['items'].append({
                        'label': cost_name,
                        'value': -cost_value,
                        'formatted': f'{cost_value:,.0f}đ',
                        'type': 'cost'
                    })

            breakdown['sections'].append(custom_costs_section)

        # Section 4: Bảng tính toán (Calculation Table) - Shopee style
        total_costs = calc_result['total_costs']
        net_profit = calc_result['net_profit']
        is_profitable = net_profit > 0

        calculation_table = {
            'title': 'Bảng tính toán',
            'title_en': 'Calculation Summary',
            'items': [
                {
                    'label': 'Giá vốn',
                    'label_en': 'Cost Price',
                    'value': cost_price,
                    'formatted': f'{cost_price:,.0f}đ',
                    'type': 'cost',
                    'highlight': True
                },
                {
                    'label': 'Giá bán',
                    'label_en': 'Sale Price',
                    'value': sale_price,
                    'formatted': f'{sale_price:,.0f}đ',
                    'type': 'base',
                    'highlight': True
                },
                {
                    'label': 'Tổng phí Shopee',
                    'label_en': 'Total Shopee Fees',
                    'value': calc_result['total_shopee_fees'],
                    'formatted': f'{calc_result["total_shopee_fees"]:,.0f}đ',
                    'type': 'fee_summary'
                }
            ],
            'subtotal': None
        }

        if calc_result.get('total_custom_costs', 0) > 0:
            calculation_table['items'].append({
                'label': 'Chi phí khác',
                'label_en': 'Other Costs',
                'value': calc_result['total_custom_costs'],
                'formatted': f'{calc_result["total_custom_costs"]:,.0f}đ',
                'type': 'cost_summary'
            })

        calculation_table['items'].append({
            'label': 'Lợi nhuận dự kiến',
            'label_en': 'Expected Profit',
            'value': net_profit,
            'formatted': f'{net_profit:,.0f}đ',
            'type': 'profit' if is_profitable else 'loss',
            'highlight': True,
            'formula': f'{sale_price:,.0f}đ - {cost_price:,.0f}đ - {calc_result["total_shopee_fees"]:,.0f}đ' +
                      (f' - {calc_result["total_custom_costs"]:,.0f}đ' if calc_result.get('total_custom_costs', 0) > 0 else '')
        })

        breakdown['sections'].append(calculation_table)

        # Section 5: Chỉ số hiệu quả (Performance Metrics)
        breakdown['sections'].append({
            'title': 'Chỉ số hiệu quả',
            'title_en': 'Performance Metrics',
            'items': [
                {
                    'label': 'Tỷ suất lợi nhuận (Margin)',
                    'label_en': 'Profit Margin',
                    'value': calc_result['profit_margin_percent'],
                    'formatted': f'{calc_result["profit_margin_percent"]:.2f}%',
                    'type': 'metric',
                    'formula': f'({net_profit:,.0f}đ / {sale_price:,.0f}đ) × 100'
                },
                {
                    'label': 'ROI (Lợi nhuận/Vốn)',
                    'label_en': 'Return on Investment',
                    'value': calc_result['roi_percent'],
                    'formatted': f'{calc_result["roi_percent"]:.2f}%',
                    'type': 'metric',
                    'formula': f'({net_profit:,.0f}đ / {cost_price:,.0f}đ) × 100'
                },
                {
                    'label': 'Giá hòa vốn',
                    'label_en': 'Breakeven Price',
                    'value': calc_result['breakeven_price'],
                    'formatted': f'{calc_result["breakeven_price"]:,.0f}đ',
                    'type': 'metric',
                    'detail': 'Giá bán tối thiểu để lợi nhuận = 0'
                }
            ],
            'subtotal': None
        })

        # Summary - Quick view
        breakdown['summary'] = {
            'sale_price': sale_price,
            'cost_price': cost_price,
            'total_shopee_fees': calc_result['total_shopee_fees'],
            'total_custom_costs': calc_result.get('total_custom_costs', 0),
            'total_costs': total_costs,
            'net_profit': net_profit,
            'profit_margin_percent': calc_result['profit_margin_percent'],
            'roi_percent': calc_result['roi_percent'],
            'breakeven_price': calc_result['breakeven_price'],
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
        total_fees = selected_price_data.get('total_fees', 0)
        total_custom_costs = selected_price_data.get('total_custom_costs', 0)
        profit = selected_price_data.get('profit', 0)
        is_profitable = profit > 0

        breakdown = {
            'calculation_type': 'pricing',
            'sections': []
        }

        # Section 1: Giá bán được đề xuất
        breakdown['sections'].append({
            'title': 'Giá bán được đề xuất',
            'title_en': 'Recommended Price',
            'items': [
                {
                    'label': 'Giá niêm yết',
                    'label_en': 'Listed Price',
                    'value': selected_price,
                    'formatted': f'{selected_price:,.0f}đ',
                    'type': 'base',
                    'highlight': True
                }
            ],
            'subtotal': None
        })

        # Section 2: Ước tính phí Shopee
        breakdown['sections'].append({
            'title': 'Phí phải trả cho Shopee (ước tính)',
            'title_en': 'Estimated Shopee Fees',
            'items': [
                {
                    'label': 'Tổng phí Shopee',
                    'label_en': 'Total Shopee Fees',
                    'value': total_fees,
                    'formatted': f'{total_fees:,.0f}đ',
                    'type': 'fee_summary',
                    'detail': f'Dựa trên giá bán {selected_price:,.0f}đ'
                }
            ],
            'subtotal': None
        })

        # Section 3: Chi phí khác (if any)
        if total_custom_costs > 0:
            breakdown['sections'].append({
                'title': 'Chi phí khác',
                'title_en': 'Other Costs',
                'items': [
                    {
                        'label': 'Tổng chi phí khác',
                        'label_en': 'Total Other Costs',
                        'value': total_custom_costs,
                        'formatted': f'{total_custom_costs:,.0f}đ',
                        'type': 'cost_summary'
                    }
                ],
                'subtotal': None
            })

        # Section 4: Bảng tính toán
        calculation_items = [
            {
                'label': 'Giá vốn',
                'label_en': 'Cost Price',
                'value': cost_price,
                'formatted': f'{cost_price:,.0f}đ',
                'type': 'cost',
                'highlight': True
            },
            {
                'label': 'Giá bán',
                'label_en': 'Sale Price',
                'value': selected_price,
                'formatted': f'{selected_price:,.0f}đ',
                'type': 'base',
                'highlight': True
            },
            {
                'label': 'Tổng phí Shopee',
                'label_en': 'Total Shopee Fees',
                'value': total_fees,
                'formatted': f'{total_fees:,.0f}đ',
                'type': 'fee_summary'
            }
        ]

        if total_custom_costs > 0:
            calculation_items.append({
                'label': 'Chi phí khác',
                'label_en': 'Other Costs',
                'value': total_custom_costs,
                'formatted': f'{total_custom_costs:,.0f}đ',
                'type': 'cost_summary'
            })

        calculation_items.append({
            'label': 'Lợi nhuận dự kiến',
            'label_en': 'Expected Profit',
            'value': profit,
            'formatted': f'{profit:,.0f}đ',
            'type': 'profit' if is_profitable else 'loss',
            'highlight': True,
            'formula': f'{selected_price:,.0f}đ - {cost_price:,.0f}đ - {total_fees:,.0f}đ' +
                      (f' - {total_custom_costs:,.0f}đ' if total_custom_costs > 0 else '')
        })

        breakdown['sections'].append({
            'title': 'Bảng tính toán',
            'title_en': 'Calculation Summary',
            'items': calculation_items,
            'subtotal': None
        })

        # Section 5: Chỉ số
        margin = selected_price_data.get('margin_percent', 0)
        roi = selected_price_data.get('roi_percent', 0)

        breakdown['sections'].append({
            'title': 'Chỉ số hiệu quả',
            'title_en': 'Performance Metrics',
            'items': [
                {
                    'label': 'Tỷ suất lợi nhuận (Margin)',
                    'label_en': 'Profit Margin',
                    'value': margin,
                    'formatted': f'{margin:.2f}%',
                    'type': 'metric'
                },
                {
                    'label': 'ROI (Lợi nhuận/Vốn)',
                    'label_en': 'Return on Investment',
                    'value': roi,
                    'formatted': f'{roi:.2f}%',
                    'type': 'metric'
                },
                {
                    'label': 'Giá hòa vốn',
                    'label_en': 'Breakeven Price',
                    'value': calc_result.get('breakeven_price', 0),
                    'formatted': f'{calc_result.get("breakeven_price", 0):,.0f}đ',
                    'type': 'metric'
                }
            ],
            'subtotal': None
        })

        # Summary
        breakdown['summary'] = {
            'selected_price': selected_price,
            'cost_price': cost_price,
            'total_fees': total_fees,
            'total_custom_costs': total_custom_costs,
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
            Formatted text string matching Shopee's style
        """
        lines = []
        separator = "━" * 60

        lines.append("")
        lines.append("╔" + "═" * 58 + "╗")
        lines.append("║" + "BẢNG TÍNH PHÍ SHOPEE".center(58) + "║")
        lines.append("╚" + "═" * 58 + "╝")

        for section in breakdown['sections']:
            # Section title
            lines.append("")
            lines.append(f"▸ {section['title'].upper()}")
            lines.append(separator)

            # Section items
            for item in section['items']:
                indent = "  " if item.get('indent') else ""
                label = item['label']
                formatted = item['formatted']

                lines.append(f"{indent}{label:.<50} {formatted:>10}")

                # Add formula/detail if available
                if 'formula' in item:
                    lines.append(f"{indent}  ➜ {item['formula']}")
                if 'detail' in item:
                    lines.append(f"{indent}  ℹ  {item['detail']}")

            # Subtotal if available
            if section.get('subtotal'):
                lines.append(separator)
                subtotal = section['subtotal']
                lines.append(f"{'TỔNG':.<50} {subtotal['formatted']:>10}")

        # Final summary
        lines.append("")
        lines.append("╔" + "═" * 58 + "╗")
        summary = breakdown['summary']

        if breakdown['calculation_type'] == 'profit':
            lines.append("║" + "KẾT QUẢ".center(58) + "║")
            lines.append("╠" + "═" * 58 + "╣")
            lines.append(f"║  Lợi nhuận ròng: {summary['net_profit']:>20,.0f}đ" + " " * (58 - len(f"  Lợi nhuận ròng: {summary['net_profit']:>20,.0f}đ") - 2) + "║")
            lines.append(f"║  Tỷ suất lợi nhuận: {summary['profit_margin_percent']:>16.2f}%" + " " * (58 - len(f"  Tỷ suất lợi nhuận: {summary['profit_margin_percent']:>16.2f}%") - 2) + "║")
            lines.append(f"║  ROI: {summary['roi_percent']:>31.2f}%" + " " * (58 - len(f"  ROI: {summary['roi_percent']:>31.2f}%") - 2) + "║")
            status = '✅ CÓ LỜI' if summary['is_profitable'] else '❌ LỖ'
            lines.append(f"║  Trạng thái: {status:>27}" + " " * (58 - len(f"  Trạng thái: {status:>27}") - 2) + "║")
        else:
            lines.append("║" + "GIÁ ĐỀ XUẤT".center(58) + "║")
            lines.append("╠" + "═" * 58 + "╣")
            lines.append(f"║  Giá bán: {summary['selected_price']:>24,.0f}đ" + " " * (58 - len(f"  Giá bán: {summary['selected_price']:>24,.0f}đ") - 2) + "║")
            lines.append(f"║  Lợi nhuận dự kiến: {summary['profit']:>17,.0f}đ" + " " * (58 - len(f"  Lợi nhuận dự kiến: {summary['profit']:>17,.0f}đ") - 2) + "║")
            lines.append(f"║  Margin: {summary['margin_percent']:>28.2f}%" + " " * (58 - len(f"  Margin: {summary['margin_percent']:>28.2f}%") - 2) + "║")
            lines.append(f"║  Giá hòa vốn: {summary['breakeven_price']:>21,.0f}đ" + " " * (58 - len(f"  Giá hòa vốn: {summary['breakeven_price']:>21,.0f}đ") - 2) + "║")

        lines.append("╚" + "═" * 58 + "╝")

        return "\n".join(lines)
