"""
AI Arbiter Module

Uses AI (Claude/OpenAI) to analyze arbitration cases and provide verdicts.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from modules.db_utils.safe_connection import safe_db_connection
from modules.config.services.ai_service import get_ai_config, call_ai_api

logger = logging.getLogger(__name__)


class AIArbiter:
    """
    AI-powered arbitration engine
    """

    # Verdict types
    VERDICT_PLATFORM_RIGHT = "platform_right"
    VERDICT_PLATFORM_WRONG = "platform_wrong"
    VERDICT_UNCLEAR = "unclear"

    def __init__(self):
        """Initialize AI Arbiter"""
        self.logger = logger

    def analyze_case(
        self,
        case_data: Dict[str, Any],
        applicable_rules: List[Dict[str, Any]],
        user_email: str
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a case using AI

        Args:
            case_data: Case information from database
            applicable_rules: List of applicable legal rules
            user_email: User's email for AI configuration

        Returns:
            dict: Analysis result with verdict, reasoning, recommendations
        """
        try:
            # Get AI configuration for user
            ai_config = get_ai_config(user_email)

            if not ai_config or not ai_config.get('ai_enabled'):
                self.logger.warning(f"AI not enabled for user {user_email}")
                return None

            # Build prompt
            prompt = self._build_arbiter_prompt(case_data, applicable_rules)

            # Call AI API
            response = call_ai_api(
                provider=ai_config.get('api_provider', 'claude'),
                encrypted_api_key=ai_config.get('encrypted_api_key'),
                prompt=prompt,
                user_email=user_email,
                max_tokens=4000
            )

            if not response or not response.get('success'):
                self.logger.error(f"AI API call failed: {response.get('error')}")
                return None

            # Parse AI response
            analysis_result = self._parse_ai_response(response['response'])

            # Save analysis to history
            self._save_analysis_history(
                case_id=case_data['case_id'],
                provider=ai_config.get('api_provider'),
                model_version=response.get('model'),
                prompt=prompt,
                response=response['response'],
                verdict=analysis_result.get('verdict'),
                confidence=analysis_result.get('confidence'),
                tokens_used=response.get('tokens_used', 0),
                cost_usd=response.get('cost', 0.0),
                analyzed_by=user_email
            )

            self.logger.info(f"✅ AI analysis completed for case {case_data['case_number']}")

            return analysis_result

        except Exception as e:
            self.logger.error(f"Error analyzing case: {e}")
            return None

    def _build_arbiter_prompt(
        self,
        case_data: Dict[str, Any],
        applicable_rules: List[Dict[str, Any]]
    ) -> str:
        """
        Build AI prompt for case analysis

        Args:
            case_data: Case information
            applicable_rules: Applicable legal rules

        Returns:
            str: Formatted prompt
        """
        # Format evidence list
        evidence_summary = "Không có chứng cứ được cung cấp"
        # TODO: Get actual evidence from database

        # Format rules
        rules_text = ""
        for i, rule in enumerate(applicable_rules, 1):
            rules_text += f"\n{i}. **{rule['title']}**\n"
            rules_text += f"   Loại: {rule['rule_type']}\n"
            rules_text += f"   Nội dung: {rule['content'][:500]}...\n"

        if not rules_text:
            rules_text = "Không tìm thấy luật/quy định liên quan"

        prompt = f"""
Bạn là một trọng tài AI chuyên nghiệp, giúp phân tích các tranh chấp thương mại một cách khách quan và công bằng.

**THÔNG TIN CASE:**
- Số case: {case_data.get('case_number')}
- Tiêu đề: {case_data.get('title')}
- Loại tranh chấp: {case_data.get('dispute_type')}
- Người khiếu nại: {case_data.get('complainant_name')}
- Bên bị khiếu nại: {case_data.get('respondent_name')} ({case_data.get('respondent_type', 'platform')})
- Số tiền tranh chấp: {case_data.get('amount_disputed', 0):,.0f} {case_data.get('currency', 'VND')}
- Ngày xảy ra: {case_data.get('dispute_date', 'N/A')}

**MÔ TẢ CHI TIẾT:**
{case_data.get('description')}

**CHỨNG CỨ ĐƯỢC CUNG CẤP:**
{evidence_summary}

**CÁC LUẬT/QUY ĐỊNH LIÊN QUAN:**
{rules_text}

**NHIỆM VỤ CỦA BẠN:**

1. **Phân tích case** dựa trên:
   - Mô tả của người khiếu nại
   - Các luật/quy định liên quan
   - Chứng cứ được cung cấp (nếu có)

2. **Đánh giá khách quan:**
   - Ai đúng, ai sai?
   - Bên nào vi phạm luật/quy định?
   - Mức độ vi phạm như thế nào?

3. **Đưa ra phán quyết:**
   - **platform_right**: Sàn/Platform làm đúng, người khiếu nại không có cơ sở
   - **platform_wrong**: Sàn/Platform vi phạm, người khiếu nại có lý
   - **unclear**: Không đủ thông tin để phán quyết

4. **Gợi ý hành động:**
   - Nếu platform đúng: Khuyến cáo người khiếu nại nên làm gì
   - Nếu platform sai: Người khiếu nại nên làm gì tiếp theo (khiếu nại, yêu cầu bồi thường, báo cơ quan chức năng, etc.)

5. **Đánh giá thiệt hại** (nếu platform sai):
   - Loại thiệt hại: direct_loss (mất tiền trực tiếp) / indirect_loss (mất khách hàng, uy tín) / opportunity_cost (cơ hội kinh doanh)
   - Ước tính số tiền thiệt hại
   - Căn cứ tính toán

**OUTPUT FORMAT (JSON):**

Trả về JSON hợp lệ với format sau:

{{
  "verdict": "platform_right | platform_wrong | unclear",
  "confidence": 0.85,
  "reasoning": "Phân tích chi tiết (ít nhất 200 từ):\\n- Điểm 1\\n- Điểm 2\\n...",
  "platform_violations": ["Tên vi phạm 1", "Tên vi phạm 2"],
  "complainant_violations": ["Vi phạm của người khiếu nại nếu có"],
  "applicable_rules": [{applicable_rules[0]['rule_id'] if applicable_rules else 'null'}, {applicable_rules[1]['rule_id'] if len(applicable_rules) > 1 else 'null'}],
  "recommended_action": "Hành động cụ thể người khiếu nại nên làm",
  "damage_assessment": {{
    "type": "direct_loss | indirect_loss | opportunity_cost | none",
    "estimated_amount": 0,
    "calculation_basis": "Giải thích cách tính"
  }},
  "evidence_quality": "strong | moderate | weak",
  "additional_evidence_needed": ["Chứng cứ gì cần bổ sung"]
}}

**LƯU Ý QUAN TRỌNG:**
- Phân tích KHÁCH QUAN, dựa trên sự thật và luật pháp
- KHÔNG thiên vị bất kỳ bên nào
- Nếu không đủ thông tin, hãy chọn "unclear" và yêu cầu thêm chứng cứ
- Reasoning phải chi tiết, có căn cứ pháp lý cụ thể

Hãy phân tích và trả về JSON:
"""

        return prompt

    def _parse_ai_response(self, ai_response: str) -> Dict[str, Any]:
        """
        Parse AI response into structured format

        Args:
            ai_response: Raw AI response text

        Returns:
            dict: Parsed analysis result
        """
        try:
            # Try to extract JSON from response
            # AI might wrap JSON in markdown code blocks
            response_clean = ai_response.strip()

            # Remove markdown code blocks if present
            if response_clean.startswith('```json'):
                response_clean = response_clean[7:]
            if response_clean.startswith('```'):
                response_clean = response_clean[3:]
            if response_clean.endswith('```'):
                response_clean = response_clean[:-3]

            response_clean = response_clean.strip()

            # Parse JSON
            result = json.loads(response_clean)

            # Validate required fields
            if 'verdict' not in result:
                result['verdict'] = self.VERDICT_UNCLEAR

            if 'confidence' not in result:
                result['confidence'] = 0.5

            if 'reasoning' not in result:
                result['reasoning'] = "AI không cung cấp lý do cụ thể"

            return result

        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing AI response as JSON: {e}")

            # Fallback: Return unclear verdict
            return {
                'verdict': self.VERDICT_UNCLEAR,
                'confidence': 0.3,
                'reasoning': f"Không thể phân tích được response từ AI. Raw response:\n{ai_response[:500]}",
                'platform_violations': [],
                'complainant_violations': [],
                'applicable_rules': [],
                'recommended_action': 'Vui lòng thử lại hoặc cung cấp thêm thông tin',
                'damage_assessment': {
                    'type': 'none',
                    'estimated_amount': 0,
                    'calculation_basis': 'N/A'
                },
                'evidence_quality': 'weak',
                'additional_evidence_needed': ['Thêm chứng cứ cụ thể']
            }

    def _save_analysis_history(
        self,
        case_id: int,
        provider: str,
        model_version: str,
        prompt: str,
        response: str,
        verdict: str,
        confidence: float,
        tokens_used: int,
        cost_usd: float,
        analyzed_by: str
    ):
        """
        Save analysis to history table

        Args:
            case_id: Case ID
            provider: AI provider (claude/openai)
            model_version: Model version
            prompt: Prompt used
            response: AI response
            verdict: Verdict result
            confidence: Confidence score
            tokens_used: Number of tokens used
            cost_usd: Cost in USD
            analyzed_by: User email
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO case_analysis_history (
                        case_id, ai_provider, model_version, prompt_used, response,
                        verdict, confidence, tokens_used, cost_usd, analyzed_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    case_id, provider, model_version, prompt, response,
                    verdict, confidence, tokens_used, cost_usd, analyzed_by
                ))

                conn.commit()

                self.logger.info(f"✅ Saved analysis history for case {case_id}")

        except Exception as e:
            self.logger.error(f"Error saving analysis history: {e}")

    def get_analysis_history(self, case_id: int) -> List[Dict[str, Any]]:
        """
        Get analysis history for a case

        Args:
            case_id: Case ID

        Returns:
            List of analysis history records
        """
        try:
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM case_analysis_history
                    WHERE case_id = ?
                    ORDER BY analyzed_at DESC
                """, (case_id,))

                history = []
                columns = [description[0] for description in cursor.description]

                for row in cursor.fetchall():
                    record = dict(zip(columns, row))
                    history.append(record)

                return history

        except Exception as e:
            self.logger.error(f"Error getting analysis history: {e}")
            return []

    def reanalyze_case(
        self,
        case_id: int,
        user_email: str,
        force: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Re-analyze a case (useful if rules changed or new evidence added)

        Args:
            case_id: Case ID
            user_email: User email
            force: Force re-analysis even if already analyzed

        Returns:
            dict: New analysis result
        """
        try:
            # Get case from database
            with safe_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM arbitration_cases WHERE case_id = ?", (case_id,))

                row = cursor.fetchone()
                if not row:
                    self.logger.error(f"Case {case_id} not found")
                    return None

                columns = [description[0] for description in cursor.description]
                case_data = dict(zip(columns, row))

            # Check if already analyzed
            if case_data.get('ai_verdict') and not force:
                self.logger.warning(f"Case {case_id} already analyzed. Use force=True to re-analyze")
                return None

            # Get applicable rules (TODO: implement rule matcher)
            from modules.legal.rule_matcher import RuleMatcher
            matcher = RuleMatcher()
            applicable_rules = matcher.find_applicable_rules(
                dispute_type=case_data['dispute_type'],
                description=case_data['description'],
                respondent_type=case_data.get('respondent_type', 'platform'),
                jurisdiction='VN'
            )

            # Analyze
            analysis_result = self.analyze_case(case_data, applicable_rules, user_email)

            if analysis_result:
                # Update case with analysis result
                from modules.arbitration.case_manager import CaseManager
                cm = CaseManager()
                cm.update_case(case_id, {
                    'ai_verdict': analysis_result['verdict'],
                    'ai_confidence': analysis_result['confidence'],
                    'ai_reasoning': analysis_result['reasoning'],
                    'applicable_rules': json.dumps(analysis_result.get('applicable_rules', [])),
                    'platform_violations': json.dumps(analysis_result.get('platform_violations', [])),
                    'recommended_action': analysis_result.get('recommended_action'),
                    'damage_assessment': json.dumps(analysis_result.get('damage_assessment', {})),
                    'status': 'analyzed'
                }, user_email)

            return analysis_result

        except Exception as e:
            self.logger.error(f"Error re-analyzing case {case_id}: {e}")
            return None
