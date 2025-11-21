"""
AI Arbitration System API Routes

Provides REST API endpoints for the arbitration system.
"""

from flask import Blueprint, request, jsonify, send_file
import logging
from typing import Dict, Any
import io

from modules.arbitration.case_manager import CaseManager
from modules.arbitration.ai_arbiter import AIArbiter
from modules.arbitration.evidence_generator import EvidenceGenerator
from modules.arbitration.verdict_formatter import VerdictFormatter
from modules.arbitration.damage_assessor import DamageAssessor

from modules.legal.knowledge_base import LegalKnowledgeBase
from modules.legal.rule_matcher import RuleMatcher

from modules.reporting.case_classifier import CaseClassifier
from modules.reporting.statistics import StatisticsEngine
from modules.reporting.public_reporter import PublicReporter
from modules.reporting.authority_notifier import AuthorityNotifier

logger = logging.getLogger(__name__)

# Create blueprint
arbitration_bp = Blueprint('arbitration', __name__, url_prefix='/api/arbitration')

# Initialize services
case_mgr = CaseManager()
ai_arbiter = AIArbiter()
evidence_gen = EvidenceGenerator()
verdict_fmt = VerdictFormatter()
damage_assessor = DamageAssessor()
legal_kb = LegalKnowledgeBase()
rule_matcher = RuleMatcher()
classifier = CaseClassifier()
stats_engine = StatisticsEngine()
public_reporter = PublicReporter()
authority_notifier = AuthorityNotifier()


# ==================== CASE MANAGEMENT ENDPOINTS ====================

@arbitration_bp.route('/cases', methods=['GET'])
def list_cases():
    """
    List arbitration cases with optional filters

    Query params:
        - status: Filter by status
        - dispute_type: Filter by dispute type
        - created_by: Filter by creator email
        - respondent_name: Filter by respondent name
        - limit: Number of results (default: 50)
        - offset: Offset for pagination (default: 0)
        - sort_by: Sort column (default: created_at)
        - sort_order: ASC or DESC (default: DESC)
    """
    try:
        # Extract query params
        filters = {}
        if request.args.get('status'):
            filters['status'] = request.args.get('status')
        if request.args.get('dispute_type'):
            filters['dispute_type'] = request.args.get('dispute_type')
        if request.args.get('created_by'):
            filters['created_by'] = request.args.get('created_by')
        if request.args.get('respondent_name'):
            filters['respondent_name'] = request.args.get('respondent_name')
        if request.args.get('ai_verdict'):
            filters['ai_verdict'] = request.args.get('ai_verdict')

        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'DESC')

        # Get cases
        cases = case_mgr.list_cases(
            filters=filters,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )

        return jsonify({
            'success': True,
            'cases': cases,
            'count': len(cases)
        })

    except Exception as e:
        logger.error(f"Error listing cases: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@arbitration_bp.route('/cases', methods=['POST'])
def create_case():
    """
    Create a new arbitration case

    JSON body:
        - title: str (required)
        - description: str (required)
        - complainant_name: str (required)
        - respondent_name: str (required)
        - dispute_type: str (required)
        - complainant_email: str (optional)
        - complainant_phone: str (optional)
        - complainant_id_number: str (optional)
        - respondent_type: str (optional, default: 'platform')
        - respondent_tax_id: str (optional)
        - dispute_date: str (optional, YYYY-MM-DD)
        - amount_disputed: float (optional)
        - currency: str (optional, default: 'VND')
        - priority: str (optional, default: 'medium')
        - created_by: str (required - user email)
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['title', 'description', 'complainant_name', 'respondent_name', 'dispute_type', 'created_by']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400

        # Create case
        case_id = case_mgr.create_case(data, data.get('created_by'))

        if case_id:
            # Get created case
            case_data = case_mgr.get_case(case_id)

            return jsonify({
                'success': True,
                'case_id': case_id,
                'case_number': case_data.get('case_number'),
                'case': case_data
            }), 201
        else:
            return jsonify({'success': False, 'error': 'Failed to create case'}), 500

    except Exception as e:
        logger.error(f"Error creating case: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@arbitration_bp.route('/cases/<int:case_id>', methods=['GET'])
def get_case(case_id):
    """Get case details by ID"""
    try:
        case_data = case_mgr.get_case(case_id)

        if case_data:
            # Get evidence
            evidence = case_mgr.get_case_evidence(case_id)

            # Get comments
            comments = case_mgr.get_case_comments(case_id)

            # Get analysis history
            analysis_history = ai_arbiter.get_analysis_history(case_id)

            return jsonify({
                'success': True,
                'case': case_data,
                'evidence': evidence,
                'comments': comments,
                'analysis_history': analysis_history
            })
        else:
            return jsonify({'success': False, 'error': 'Case not found'}), 404

    except Exception as e:
        logger.error(f"Error getting case: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@arbitration_bp.route('/cases/<int:case_id>', methods=['PUT'])
def update_case(case_id):
    """
    Update case fields

    JSON body:
        - updates: dict of fields to update
        - updated_by: str (user email)
    """
    try:
        data = request.get_json()
        updates = data.get('updates', {})
        updated_by = data.get('updated_by', 'unknown')

        success = case_mgr.update_case(case_id, updates, updated_by)

        if success:
            case_data = case_mgr.get_case(case_id)
            return jsonify({'success': True, 'case': case_data})
        else:
            return jsonify({'success': False, 'error': 'Failed to update case'}), 500

    except Exception as e:
        logger.error(f"Error updating case: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@arbitration_bp.route('/cases/<int:case_id>', methods=['DELETE'])
def delete_case(case_id):
    """
    Delete (soft delete) a case

    JSON body:
        - deleted_by: str (user email)
    """
    try:
        data = request.get_json()
        deleted_by = data.get('deleted_by', 'unknown')

        success = case_mgr.delete_case(case_id, deleted_by)

        return jsonify({'success': success})

    except Exception as e:
        logger.error(f"Error deleting case: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== EVIDENCE ENDPOINTS ====================

@arbitration_bp.route('/cases/<int:case_id>/evidence', methods=['POST'])
def add_evidence(case_id):
    """
    Add evidence to a case

    JSON body or form-data:
        - evidence_type: str (video, image, document, chat, email, screenshot)
        - file_name: str (optional)
        - file_path: str (optional)
        - cloud_url: str (optional)
        - description: str (optional)
        - uploaded_by: str (user email)

    File upload: Use multipart/form-data with 'file' field
    """
    try:
        # Check if file upload
        file_blob = None
        file_name = None

        if 'file' in request.files:
            file = request.files['file']
            file_blob = file.read()
            file_name = file.filename

        # Get other data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

        evidence_id = case_mgr.add_evidence(
            case_id=case_id,
            evidence_type=data.get('evidence_type'),
            file_name=file_name or data.get('file_name'),
            file_path=data.get('file_path'),
            file_blob=file_blob,
            cloud_url=data.get('cloud_url'),
            description=data.get('description'),
            uploaded_by=data.get('uploaded_by', 'unknown')
        )

        if evidence_id:
            return jsonify({'success': True, 'evidence_id': evidence_id}), 201
        else:
            return jsonify({'success': False, 'error': 'Failed to add evidence'}), 500

    except Exception as e:
        logger.error(f"Error adding evidence: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@arbitration_bp.route('/cases/<int:case_id>/comments', methods=['POST'])
def add_comment(case_id):
    """
    Add comment to a case

    JSON body:
        - comment_text: str
        - author: str (user email)
        - comment_type: str (note, update, decision)
    """
    try:
        data = request.get_json()

        success = case_mgr.add_comment(
            case_id=case_id,
            comment_text=data.get('comment_text'),
            author=data.get('author', 'unknown'),
            comment_type=data.get('comment_type', 'note')
        )

        return jsonify({'success': success})

    except Exception as e:
        logger.error(f"Error adding comment: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== AI ANALYSIS ENDPOINTS ====================

@arbitration_bp.route('/cases/<int:case_id>/analyze', methods=['POST'])
def analyze_case(case_id):
    """
    Analyze a case using AI

    JSON body:
        - user_email: str (for AI config)
        - force: bool (force re-analysis, default: false)
    """
    try:
        data = request.get_json()
        user_email = data.get('user_email')
        force = data.get('force', False)

        if not user_email:
            return jsonify({'success': False, 'error': 'user_email is required'}), 400

        # Analyze case
        analysis_result = ai_arbiter.reanalyze_case(case_id, user_email, force)

        if analysis_result:
            # Format verdict for display
            formatted_verdict = verdict_fmt.format_verdict(analysis_result)

            # Classify case
            case_data = case_mgr.get_case(case_id)
            if case_data:
                classifier.classify_case(case_data, analysis_result)

            # Generate evidence if platform wrong
            if analysis_result.get('verdict') == 'platform_wrong':
                doc_text = evidence_gen.generate_fraud_report(case_data, analysis_result, jurisdiction='VN')
                evidence_gen.save_evidence_document(case_id, doc_text)

            return jsonify({
                'success': True,
                'analysis': analysis_result,
                'formatted_verdict': formatted_verdict
            })
        else:
            return jsonify({'success': False, 'error': 'Analysis failed'}), 500

    except Exception as e:
        logger.error(f"Error analyzing case: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@arbitration_bp.route('/cases/<int:case_id>/evidence-document', methods=['GET'])
def download_evidence_document(case_id):
    """Download generated evidence document"""
    try:
        case_data = case_mgr.get_case(case_id)

        if not case_data or not case_data.get('evidence_document'):
            return jsonify({'success': False, 'error': 'Evidence document not found'}), 404

        # Get document blob
        doc_blob = case_data['evidence_document']

        # Convert bytes to file-like object
        file_obj = io.BytesIO(doc_blob)

        # Send as download
        return send_file(
            file_obj,
            mimetype='text/markdown',
            as_attachment=True,
            download_name=f"evidence_{case_data['case_number']}.md"
        )

    except Exception as e:
        logger.error(f"Error downloading evidence document: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== LEGAL KNOWLEDGE BASE ENDPOINTS ====================

@arbitration_bp.route('/rules', methods=['GET'])
def search_rules():
    """
    Search legal rules

    Query params:
        - query: Text search
        - rule_type: Filter by rule type
        - category: Filter by category
        - jurisdiction: Filter by jurisdiction
        - limit: Max results (default: 50)
    """
    try:
        query = request.args.get('query')
        rule_type = request.args.get('rule_type')
        category = request.args.get('category')
        jurisdiction = request.args.get('jurisdiction')
        limit = int(request.args.get('limit', 50))

        rules = legal_kb.search_rules(
            query=query,
            rule_type=rule_type,
            category=category,
            jurisdiction=jurisdiction,
            limit=limit
        )

        return jsonify({
            'success': True,
            'rules': rules,
            'count': len(rules)
        })

    except Exception as e:
        logger.error(f"Error searching rules: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@arbitration_bp.route('/rules', methods=['POST'])
def add_rule():
    """
    Add a legal rule

    JSON body:
        - rule_type: str (platform, commercial_law, international, contract)
        - title: str
        - content: str
        - jurisdiction: str (optional)
        - source_url: str (optional)
        - effective_date: str (optional, YYYY-MM-DD)
        - version: str (optional)
        - category: str (optional)
        - keywords: list (optional)
        - created_by: str (user email)
    """
    try:
        data = request.get_json()

        rule_id = legal_kb.add_rule(data, data.get('created_by', 'unknown'))

        if rule_id:
            rule_data = legal_kb.get_rule(rule_id)
            return jsonify({'success': True, 'rule_id': rule_id, 'rule': rule_data}), 201
        else:
            return jsonify({'success': False, 'error': 'Failed to add rule'}), 500

    except Exception as e:
        logger.error(f"Error adding rule: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== STATISTICS ENDPOINTS ====================

@arbitration_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """Get overall system statistics"""
    try:
        stats = stats_engine.get_overall_statistics()

        return jsonify({
            'success': True,
            'statistics': stats
        })

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@arbitration_bp.route('/statistics/platform/<platform_name>', methods=['GET'])
def get_platform_statistics(platform_name):
    """
    Get statistics for a specific platform

    Query params:
        - period_start: YYYY-MM-DD
        - period_end: YYYY-MM-DD
    """
    try:
        period_start = request.args.get('period_start')
        period_end = request.args.get('period_end')

        stats = stats_engine.generate_platform_statistics(
            platform_name=platform_name,
            period_start=period_start,
            period_end=period_end
        )

        return jsonify({
            'success': True,
            'statistics': stats
        })

    except Exception as e:
        logger.error(f"Error getting platform statistics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== HEALTH CHECK ====================

@arbitration_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'service': 'AI Arbitration System',
        'version': '1.0.0',
        'status': 'healthy'
    })


logger.info("✅ AI Arbitration API routes registered")
