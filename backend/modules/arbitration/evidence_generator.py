"""
Evidence Generator Module

Auto-generates legal evidence documents (fraud reports, complaints) based on case analysis.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class EvidenceGenerator:
    """
    Generates legal evidence documents
    """

    def __init__(self):
        """Initialize Evidence Generator"""
        self.logger = logger

    def generate_fraud_report(
        self,
        case_data: Dict[str, Any],
        analysis_result: Dict[str, Any],
        jurisdiction: str = 'VN'
    ) -> str:
        """
        Generate fraud evidence document

        Args:
            case_data: Case information
            analysis_result: AI analysis result
            jurisdiction: Jurisdiction ('VN', 'US', 'International')

        Returns:
            str: Generated document text (Markdown format)
        """
        try:
            if jurisdiction == 'VN':
                return self._generate_vietnam_fraud_report(case_data, analysis_result)
            elif jurisdiction == 'US':
                return self._generate_us_complaint(case_data, analysis_result)
            else:
                return self._generate_international_complaint(case_data, analysis_result)

        except Exception as e:
            self.logger.error(f"Error generating fraud report: {e}")
            return ""

    def _generate_vietnam_fraud_report(
        self,
        case_data: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> str:
        """
        Generate Vietnamese fraud report (Biên bản vi phạm)

        Args:
            case_data: Case information
            analysis_result: AI analysis result

        Returns:
            str: Document text in Markdown
        """
        # Parse damage assessment
        damage_assessment = analysis_result.get('damage_assessment', {})
        if isinstance(damage_assessment, str):
            try:
                damage_assessment = json.loads(damage_assessment)
            except:
                damage_assessment = {}

        # Parse violations
        violations = analysis_result.get('platform_violations', [])
        if isinstance(violations, str):
            try:
                violations = json.loads(violations)
            except:
                violations = []

        violations_text = "\n".join([f"   - {v}" for v in violations]) if violations else "   - Chưa xác định cụ thể"

        document = f"""
# BIÊN BẢN VI PHẠM THƯƠNG MẠI ĐIỆN TỬ

**Số hồ sơ:** {case_data.get('case_number', 'N/A')}
**Ngày lập:** {datetime.now().strftime('%d/%m/%Y')}

---

## I. THÔNG TIN BÊN KHIẾU NẠI

- **Họ và tên:** {case_data.get('complainant_name', 'N/A')}
- **Email:** {case_data.get('complainant_email', 'N/A')}
- **Số điện thoại:** {case_data.get('complainant_phone', 'N/A')}
- **CCCD/CMND:** {case_data.get('complainant_id_number', 'N/A')}

---

## II. THÔNG TIN BÊN VI PHẠM

- **Tên sàn/Công ty:** {case_data.get('respondent_name', 'N/A')}
- **Loại:** {case_data.get('respondent_type', 'Platform')}
- **Mã số thuế:** {case_data.get('respondent_tax_id', 'N/A')}

---

## III. NỘI DUNG VI PHẠM

### 1. Thời gian xảy ra vi phạm
{case_data.get('dispute_date', 'Chưa xác định')}

### 2. Loại vi phạm
{case_data.get('dispute_type', 'N/A').upper()}

### 3. Mô tả chi tiết
{case_data.get('description', 'N/A')}

### 4. Các hành vi vi phạm cụ thể
{violations_text}

---

## IV. PHÂN TÍCH VÀ ĐÁNH GIÁ

### 1. Kết luận phân tích
**Phán quyết:** {analysis_result.get('verdict', 'unclear').upper()}
**Độ tin cậy:** {analysis_result.get('confidence', 0)*100:.0f}%

### 2. Lý do chi tiết
{analysis_result.get('reasoning', 'Chưa có phân tích chi tiết')}

---

## V. CĂN CỨ PHÁP LÝ

Các luật/quy định bị vi phạm:

{self._format_applicable_rules(analysis_result.get('applicable_rules', []))}

---

## VI. THIỆT HẠI

### 1. Loại thiệt hại
{damage_assessment.get('type', 'N/A')}

### 2. Số tiền thiệt hại ước tính
{damage_assessment.get('estimated_amount', 0):,.0f} VND

### 3. Căn cứ tính toán
{damage_assessment.get('calculation_basis', 'N/A')}

### 4. Số tiền tranh chấp ban đầu
{case_data.get('amount_disputed', 0):,.0f} {case_data.get('currency', 'VND')}

---

## VII. CHỨNG CỨ ĐÍNH KÈM

_Danh sách chứng cứ sẽ được bổ sung từ hệ thống_

- Video giao dịch (nếu có)
- Hình ảnh sản phẩm/dịch vụ
- Chat logs, email trao đổi
- Screenshot thông báo từ sàn
- Các tài liệu liên quan khác

---

## VIII. YÊU CẦU

### 1. Hành động khuyến nghị
{analysis_result.get('recommended_action', 'Chưa có khuyến nghị')}

### 2. Yêu cầu cụ thể
- Yêu cầu sàn/công ty giải trình và khắc phục vi phạm
- Yêu cầu bồi thường thiệt hại theo quy định pháp luật
- Yêu cầu cơ quan chức năng can thiệp xử lý (nếu cần)

---

## IX. CAM KẾT

Tôi cam đoan rằng:
- Các thông tin trên là đúng sự thật
- Các chứng cứ đính kèm là xác thực
- Chịu hoàn toàn trách nhiệm trước pháp luật về nội dung khiếu nại

---

**Người lập biên bản**

_{case_data.get('complainant_name', 'N/A')}_

Ngày {datetime.now().strftime('%d')} tháng {datetime.now().strftime('%m')} năm {datetime.now().strftime('%Y')}

---

_Tài liệu này được tạo tự động bởi Hệ thống Trọng tài AI - VPACK_
_Số hồ sơ: {case_data.get('case_number', 'N/A')}_
"""

        return document

    def _generate_us_complaint(
        self,
        case_data: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> str:
        """
        Generate US FTC-style complaint

        Args:
            case_data: Case information
            analysis_result: AI analysis result

        Returns:
            str: Document text
        """
        document = f"""
# CONSUMER COMPLAINT FORM

**Case Number:** {case_data.get('case_number', 'N/A')}
**Date Filed:** {datetime.now().strftime('%m/%d/%Y')}

---

## COMPLAINANT INFORMATION

- **Name:** {case_data.get('complainant_name', 'N/A')}
- **Email:** {case_data.get('complainant_email', 'N/A')}
- **Phone:** {case_data.get('complainant_phone', 'N/A')}

---

## BUSINESS INFORMATION

- **Company Name:** {case_data.get('respondent_name', 'N/A')}
- **Type:** {case_data.get('respondent_type', 'Platform')}
- **Tax ID:** {case_data.get('respondent_tax_id', 'N/A')}

---

## COMPLAINT DETAILS

### Nature of Complaint
{case_data.get('dispute_type', 'N/A').upper()}

### Incident Date
{case_data.get('dispute_date', 'Not specified')}

### Amount in Dispute
${case_data.get('amount_disputed', 0):,.2f} {case_data.get('currency', 'USD')}

### Description
{case_data.get('description', 'N/A')}

---

## ANALYSIS

**Verdict:** {analysis_result.get('verdict', 'unclear').upper()}
**Confidence:** {analysis_result.get('confidence', 0)*100:.0f}%

**Reasoning:**
{analysis_result.get('reasoning', 'No detailed analysis available')}

---

## REQUESTED ACTION

{analysis_result.get('recommended_action', 'No specific action recommended')}

---

**Complainant Signature**

_{case_data.get('complainant_name', 'N/A')}_
Date: {datetime.now().strftime('%m/%d/%Y')}

---

_This document was automatically generated by AI Arbitration System - VPACK_
"""

        return document

    def _generate_international_complaint(
        self,
        case_data: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> str:
        """
        Generate international complaint format

        Args:
            case_data: Case information
            analysis_result: AI analysis result

        Returns:
            str: Document text
        """
        # Similar to US format but more general
        return self._generate_us_complaint(case_data, analysis_result)

    def _format_applicable_rules(self, rule_ids: list) -> str:
        """
        Format applicable rules for document

        Args:
            rule_ids: List of rule IDs

        Returns:
            str: Formatted rules text
        """
        if not rule_ids:
            return "Chưa xác định cụ thể các luật/quy định bị vi phạm"

        # TODO: Fetch actual rules from database
        # For now, return placeholder

        rules_text = ""
        for i, rule_id in enumerate(rule_ids, 1):
            rules_text += f"{i}. Quy định ID: {rule_id} (Chi tiết cần được tra cứu từ hệ thống)\n"

        return rules_text if rules_text else "Không có"

    def save_evidence_document(
        self,
        case_id: int,
        document_text: str,
        file_path: Optional[str] = None
    ) -> bool:
        """
        Save generated evidence document to database

        Args:
            case_id: Case ID
            document_text: Document text
            file_path: Optional file path

        Returns:
            bool: True if successful
        """
        try:
            from modules.db_utils.safe_connection import safe_db_connection

            with safe_db_connection() as conn:
                cursor = conn.cursor()

                # Convert text to bytes for BLOB storage
                document_blob = document_text.encode('utf-8')

                cursor.execute("""
                    UPDATE arbitration_cases
                    SET evidence_generated = 1,
                        evidence_document = ?,
                        evidence_document_path = ?
                    WHERE case_id = ?
                """, (document_blob, file_path, case_id))

                conn.commit()

                self.logger.info(f"✅ Saved evidence document for case {case_id}")

                return True

        except Exception as e:
            self.logger.error(f"Error saving evidence document: {e}")
            return False
