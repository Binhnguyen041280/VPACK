"""
API Routes for Shopee Calculator module.
Flask blueprint with endpoints for profit/pricing calculations and data management.
"""

from flask import Blueprint, request, jsonify
from .services import CalculatorService
from .services.breakdown_formatter import BreakdownFormatter
from .models import CustomCostPreset, FeeConfig
import traceback

# Create blueprint
shopee_calculator_bp = Blueprint('shopee_calculator', __name__, url_prefix='/api/shopee-calculator')

# Initialize service
calculator_service = CalculatorService()


# ==================== CALCULATION ENDPOINTS ====================

@shopee_calculator_bp.route('/calculate/profit', methods=['POST'])
def calculate_profit():
    """Calculate profit from selling price and costs.

    Request body:
    {
        "user_email": "user@example.com",
        "product_name": "Product Name",
        "product_sku": "SKU-123",
        "seller_type": "non_mall",
        "category_code": "non_mall_electronics",
        "sale_price": 500000,
        "cost_price": 300000,
        "enabled_fees": {"payment_fee": true, "fixed_fee": true, ...},
        "custom_costs": [...],
        "custom_category_fee": null,
        "is_voucher_xtra_special": false,
        "expected_quantity_monthly": 100,
        "save_calculation": false,
        "notes": "",
        "tags": ""
    }

    Returns:
        JSON with calculation results
    """
    try:
        data = request.json

        result = calculator_service.calculate_profit(
            user_email=data['user_email'],
            product_name=data['product_name'],
            product_sku=data['product_sku'],
            seller_type=data['seller_type'],
            category_code=data['category_code'],
            sale_price=data['sale_price'],
            cost_price=data['cost_price'],
            enabled_fees=data.get('enabled_fees', {}),
            custom_costs=data.get('custom_costs', []),
            custom_category_fee=data.get('custom_category_fee'),
            is_voucher_xtra_special=data.get('is_voucher_xtra_special', False),
            expected_quantity_monthly=data.get('expected_quantity_monthly'),
            notes=data.get('notes'),
            tags=data.get('tags'),
            save_calculation=data.get('save_calculation', False)
        )

        return jsonify({
            'success': True,
            'data': result
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 400


@shopee_calculator_bp.route('/calculate/pricing', methods=['POST'])
def calculate_pricing():
    """Calculate recommended selling prices from cost and desired profit/margin.

    Request body:
    {
        "user_email": "user@example.com",
        "product_name": "Product Name",
        "product_sku": "SKU-123",
        "seller_type": "non_mall",
        "category_code": "non_mall_electronics",
        "cost_price": 300000,
        "enabled_fees": {...},
        "custom_costs": [...],
        "desired_profit": 100000,
        "desired_margin": null,
        "pricing_reference_point": "target_profit",
        "num_price_options": 5,
        "custom_category_fee": null,
        "is_voucher_xtra_special": false,
        "expected_quantity_monthly": 100,
        "save_calculation": false,
        "notes": "",
        "tags": ""
    }

    Returns:
        JSON with pricing options
    """
    try:
        data = request.json

        result = calculator_service.calculate_pricing(
            user_email=data['user_email'],
            product_name=data['product_name'],
            product_sku=data['product_sku'],
            seller_type=data['seller_type'],
            category_code=data['category_code'],
            cost_price=data['cost_price'],
            enabled_fees=data.get('enabled_fees', {}),
            custom_costs=data.get('custom_costs', []),
            desired_profit=data.get('desired_profit'),
            desired_margin=data.get('desired_margin'),
            pricing_reference_point=data.get('pricing_reference_point', 'breakeven'),
            num_price_options=data.get('num_price_options', 5),
            custom_category_fee=data.get('custom_category_fee'),
            is_voucher_xtra_special=data.get('is_voucher_xtra_special', False),
            expected_quantity_monthly=data.get('expected_quantity_monthly'),
            notes=data.get('notes'),
            tags=data.get('tags'),
            save_calculation=data.get('save_calculation', False)
        )

        return jsonify({
            'success': True,
            'data': result
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 400


@shopee_calculator_bp.route('/calculate/breakdown', methods=['POST'])
def get_price_breakdown():
    """Get detailed breakdown for a specific price option.

    Request body:
    {
        "calculation_type": "profit" or "pricing",
        "price_data": {...},  # Price option data
        "cost_price": 300000,
        "sale_price": 500000  # For profit type
    }

    Returns:
        JSON with detailed breakdown
    """
    try:
        data = request.json
        calc_type = data.get('calculation_type', 'profit')

        if calc_type == 'profit':
            # For profit calculation, use provided data
            breakdown = BreakdownFormatter.format_profit_breakdown(data['price_data'])
        else:
            # For pricing calculation
            calc_result = data.get('calc_result', {})
            selected_price = data.get('selected_price')
            price_option = data.get('price_option', {})

            breakdown = BreakdownFormatter.format_pricing_breakdown(
                calc_result,
                selected_price,
                price_option
            )

        breakdown_text = BreakdownFormatter.format_text_breakdown(breakdown)

        return jsonify({
            'success': True,
            'data': {
                'breakdown': breakdown,
                'breakdown_text': breakdown_text
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 400


# ==================== CALCULATION MANAGEMENT ====================

@shopee_calculator_bp.route('/calculations/<int:calc_id>', methods=['GET'])
def get_calculation(calc_id):
    """Get a saved calculation by ID.

    Query params:
        user_email: User email for permission check

    Returns:
        JSON with calculation data
    """
    try:
        user_email = request.args.get('user_email')
        if not user_email:
            return jsonify({
                'success': False,
                'error': 'user_email is required'
            }), 400

        result = calculator_service.get_calculation(calc_id, user_email)

        if not result:
            return jsonify({
                'success': False,
                'error': 'Calculation not found'
            }), 404

        return jsonify({
            'success': True,
            'data': result
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@shopee_calculator_bp.route('/calculations/<int:calc_id>/confirm', methods=['POST'])
def confirm_calculation(calc_id):
    """Confirm a draft calculation.

    Request body:
    {
        "user_email": "user@example.com"
    }

    Returns:
        JSON with success status
    """
    try:
        data = request.json
        user_email = data.get('user_email')

        if not user_email:
            return jsonify({
                'success': False,
                'error': 'user_email is required'
            }), 400

        success = calculator_service.confirm_calculation(calc_id, user_email)

        if success:
            return jsonify({
                'success': True,
                'message': 'Calculation confirmed'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to confirm calculation'
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


# ==================== PRODUCT SEARCH ====================

@shopee_calculator_bp.route('/products/search', methods=['GET'])
def search_products():
    """Search user's products by SKU or name.

    Query params:
        user_email: User email
        q: Search term

    Returns:
        JSON with matching products
    """
    try:
        user_email = request.args.get('user_email')
        search_term = request.args.get('q', '')

        if not user_email:
            return jsonify({
                'success': False,
                'error': 'user_email is required'
            }), 400

        results = calculator_service.search_products(user_email, search_term)

        return jsonify({
            'success': True,
            'data': results
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


# ==================== CATEGORIES ====================

@shopee_calculator_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get categories for a seller type.

    Query params:
        seller_type: 'mall' or 'non_mall'

    Returns:
        JSON with categories
    """
    try:
        seller_type = request.args.get('seller_type')

        if not seller_type:
            return jsonify({
                'success': False,
                'error': 'seller_type is required'
            }), 400

        results = calculator_service.get_categories(seller_type)

        return jsonify({
            'success': True,
            'data': results
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


# ==================== CUSTOM COST PRESETS ====================

@shopee_calculator_bp.route('/presets', methods=['GET'])
def get_custom_cost_presets():
    """Get all available custom cost presets for a user.

    Query params:
        user_email: User email (optional, shows only system presets if not provided)

    Returns:
        JSON with presets
    """
    try:
        user_email = request.args.get('user_email')
        preset_model = CustomCostPreset()

        if user_email:
            results = preset_model.get_all_for_user(user_email)
        else:
            results = preset_model.get_system_presets()

        return jsonify({
            'success': True,
            'data': results
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@shopee_calculator_bp.route('/presets', methods=['POST'])
def create_custom_cost_preset():
    """Create a new custom cost preset.

    Request body:
    {
        "user_email": "user@example.com",
        "cost_name": "Custom Cost",
        "default_value": 10000,
        "default_unit": "VND",
        "calculation_type": "fixed_per_order",
        "description": "...",
        "example_usage": "..."
    }

    Returns:
        JSON with created preset ID
    """
    try:
        data = request.json
        preset_model = CustomCostPreset()

        preset_id = preset_model.create(data)

        return jsonify({
            'success': True,
            'data': {
                'preset_id': preset_id
            }
        }), 201

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


# ==================== FEE CONFIGS ====================

@shopee_calculator_bp.route('/fee-config/active', methods=['GET'])
def get_active_fee_config():
    """Get currently active fee configuration.

    Returns:
        JSON with active fee config
    """
    try:
        fee_config_model = FeeConfig()
        result = fee_config_model.get_active_config()

        if not result:
            return jsonify({
                'success': False,
                'error': 'No active fee configuration found'
            }), 404

        return jsonify({
            'success': True,
            'data': result
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


# ==================== HEALTH CHECK ====================

@shopee_calculator_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint.

    Returns:
        JSON with status
    """
    return jsonify({
        'success': True,
        'message': 'Shopee Calculator API is running',
        'version': '1.0.0'
    }), 200
