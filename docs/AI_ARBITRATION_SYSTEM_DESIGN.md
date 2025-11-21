# AI Arbitration System - Design Document

## 1. Tổng quan (Overview)

Hệ thống Trọng tài AI giúp người bán hàng xử lý các khiếu nại thương mại một cách khách quan, dựa trên luật pháp và quy định của sàn.

### 1.1 Vấn đề cần giải quyết
- Người bán không nắm rõ luật, hợp đồng, điều kiện của sàn
- Bị bức xúc khi xử lý khiếu nại
- Cần công cụ phân tích khách quan
- Cần lập vi bằng gian lận tự động

### 1.2 Giải pháp
Hệ thống AI 5 chức năng chính:
1. **Legal Knowledge Base**: Lưu trữ luật/rule/hợp đồng
2. **Case Management**: Thu thập và quản lý case khiếu nại
3. **AI Arbiter Engine**: Phân tích và đưa ra phán quyết
4. **Evidence Generator**: Tự động lập vi bằng gian lận
5. **Public Reporting**: Thống kê và báo cáo cơ quan chức năng

---

## 2. Kiến trúc hệ thống (System Architecture)

### 2.1 Tech Stack

#### Backend
- **Python Flask**: REST API
- **SQLite**: Database với WAL mode
- **AI Services**: Claude (Anthropic), OpenAI GPT
- **Document Processing**: PyPDF2, python-docx
- **NLP**: spaCy (optional for text analysis)

#### Frontend
- **Next.js 15 + React 19**: UI Framework
- **Chakra UI**: Component library
- **TypeScript**: Type safety
- **React Context**: State management

### 2.2 Module Structure

```
backend/
├── modules/
│   ├── arbitration/              # NEW MODULE
│   │   ├── __init__.py
│   │   ├── case_manager.py       # Quản lý case
│   │   ├── ai_arbiter.py         # AI phân tích
│   │   ├── evidence_generator.py # Tạo vi bằng
│   │   ├── damage_assessor.py    # Đánh giá thiệt hại
│   │   └── verdict_formatter.py  # Format phán quyết
│   │
│   ├── legal/                    # NEW MODULE
│   │   ├── __init__.py
│   │   ├── knowledge_base.py     # Lưu trữ luật
│   │   ├── rule_matcher.py       # Match luật với case
│   │   ├── document_parser.py    # Parse documents
│   │   └── reference_scraper.py  # Scrape trang luật (optional)
│   │
│   ├── reporting/                # NEW MODULE
│   │   ├── __init__.py
│   │   ├── case_classifier.py    # Phân loại case
│   │   ├── statistics.py         # Thống kê
│   │   ├── public_reporter.py    # Push lên web
│   │   └── authority_notifier.py # Gửi cơ quan chức năng
│   │
│   └── workflow/                 # NEW MODULE
│       ├── __init__.py
│       ├── state_machine.py      # Case workflow
│       └── notification.py       # Thông báo

frontend/
├── app/
│   ├── arbitration/              # NEW ROUTES
│   │   ├── page.tsx              # Dashboard
│   │   ├── cases/
│   │   │   ├── page.tsx          # Danh sách case
│   │   │   └── [id]/
│   │   │       └── page.tsx      # Chi tiết case
│   │   ├── knowledge-base/
│   │   │   └── page.tsx          # Quản lý luật/rule
│   │   └── reports/
│   │       └── page.tsx          # Báo cáo thống kê
│   │
├── src/
│   ├── components/
│   │   ├── arbitration/          # NEW COMPONENTS
│   │   │   ├── CaseForm.tsx
│   │   │   ├── CaseList.tsx
│   │   │   ├── CaseDetail.tsx
│   │   │   ├── VerdictView.tsx
│   │   │   ├── EvidenceUpload.tsx
│   │   │   ├── LegalRuleManager.tsx
│   │   │   └── DamageAssessment.tsx
```

---

## 3. Database Schema

### 3.1 Legal Knowledge Base Tables

```sql
-- Lưu trữ các luật/rule/điều khoản
CREATE TABLE legal_rules (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_type TEXT NOT NULL,              -- 'platform', 'commercial_law', 'international', 'contract'
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    jurisdiction TEXT,                     -- 'VN', 'US', 'International', etc.
    source_url TEXT,
    source_document BLOB,                  -- PDF/DOCX file
    effective_date DATE,
    version TEXT,
    category TEXT,                         -- 'refund', 'shipping', 'quality', 'fraud', etc.
    keywords TEXT,                         -- JSON array for search
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT                        -- user_email
);

CREATE INDEX idx_legal_rules_type ON legal_rules(rule_type);
CREATE INDEX idx_legal_rules_category ON legal_rules(category);
CREATE INDEX idx_legal_rules_jurisdiction ON legal_rules(jurisdiction);

-- Lưu các tham chiếu giữa các rule
CREATE TABLE rule_references (
    ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_rule_id INTEGER,
    to_rule_id INTEGER,
    relationship TEXT,                     -- 'supersedes', 'related', 'contradicts', etc.
    notes TEXT,
    FOREIGN KEY (from_rule_id) REFERENCES legal_rules(rule_id),
    FOREIGN KEY (to_rule_id) REFERENCES legal_rules(rule_id)
);
```

### 3.2 Case Management Tables

```sql
-- Quản lý case khiếu nại
CREATE TABLE arbitration_cases (
    case_id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_number TEXT UNIQUE NOT NULL,      -- Auto-generated: ARB-2025-001
    title TEXT NOT NULL,
    description TEXT NOT NULL,

    -- Parties
    complainant_name TEXT NOT NULL,        -- Người khiếu nại (người bán)
    complainant_email TEXT,
    respondent_name TEXT NOT NULL,         -- Bên bị khiếu nại (sàn)
    respondent_type TEXT,                  -- 'platform', 'buyer', 'supplier', etc.

    -- Case details
    dispute_type TEXT NOT NULL,            -- 'refund', 'ban', 'payment', 'quality', 'fraud', etc.
    dispute_date DATE,
    amount_disputed REAL,                  -- Số tiền tranh chấp
    currency TEXT DEFAULT 'VND',

    -- Status
    status TEXT DEFAULT 'new',             -- 'new', 'analyzing', 'ruled', 'appealed', 'closed'
    priority TEXT DEFAULT 'medium',        -- 'low', 'medium', 'high', 'urgent'

    -- AI Analysis
    ai_verdict TEXT,                       -- 'platform_right', 'platform_wrong', 'unclear'
    ai_confidence REAL,                    -- 0.0 to 1.0
    ai_reasoning TEXT,                     -- AI's detailed reasoning
    applicable_rules TEXT,                 -- JSON array of rule_ids

    -- Outcome
    recommended_action TEXT,               -- Gợi ý hành động
    damage_assessment TEXT,                -- JSON: { type, amount, evidence }
    evidence_generated BOOLEAN DEFAULT 0,
    evidence_document BLOB,                -- Generated evidence document

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,

    -- Creator
    created_by TEXT NOT NULL               -- user_email
);

CREATE INDEX idx_cases_status ON arbitration_cases(status);
CREATE INDEX idx_cases_type ON arbitration_cases(dispute_type);
CREATE INDEX idx_cases_creator ON arbitration_cases(created_by);
CREATE INDEX idx_cases_verdict ON arbitration_cases(ai_verdict);

-- Lưu evidence (chứng cứ) của case
CREATE TABLE case_evidence (
    evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    evidence_type TEXT NOT NULL,           -- 'video', 'image', 'document', 'chat', 'email', 'screenshot'
    file_name TEXT,
    file_path TEXT,
    file_blob BLOB,                        -- Lưu file nhỏ trực tiếp
    cloud_url TEXT,                        -- Google Drive URL
    description TEXT,
    uploaded_by TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES arbitration_cases(case_id) ON DELETE CASCADE
);

CREATE INDEX idx_evidence_case ON case_evidence(case_id);

-- Lưu lịch sử phân tích của case
CREATE TABLE case_analysis_history (
    analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    ai_provider TEXT,                      -- 'claude', 'openai'
    model_version TEXT,
    prompt_used TEXT,
    response TEXT,
    verdict TEXT,
    confidence REAL,
    tokens_used INTEGER,
    cost_usd REAL,
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analyzed_by TEXT,
    FOREIGN KEY (case_id) REFERENCES arbitration_cases(case_id) ON DELETE CASCADE
);

CREATE INDEX idx_analysis_case ON case_analysis_history(case_id);

-- Lưu các comment/note trong case
CREATE TABLE case_comments (
    comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    comment_text TEXT NOT NULL,
    comment_type TEXT DEFAULT 'note',      -- 'note', 'update', 'decision'
    author TEXT NOT NULL,                  -- user_email
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES arbitration_cases(case_id) ON DELETE CASCADE
);
```

### 3.3 Reporting & Classification Tables

```sql
-- Phân loại case theo pattern
CREATE TABLE case_classifications (
    classification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    pattern_type TEXT NOT NULL,            -- 'systematic_fraud', 'policy_abuse', 'isolated_incident'
    severity TEXT,                         -- 'minor', 'moderate', 'severe', 'critical'
    fraud_indicators TEXT,                 -- JSON array of fraud signals
    similar_cases TEXT,                    -- JSON array of similar case_ids
    classified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES arbitration_cases(case_id) ON DELETE CASCADE
);

-- Thống kê theo platform/respondent
CREATE TABLE platform_statistics (
    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform_name TEXT NOT NULL,
    period_start DATE,
    period_end DATE,
    total_cases INTEGER DEFAULT 0,
    platform_right_count INTEGER DEFAULT 0,
    platform_wrong_count INTEGER DEFAULT 0,
    total_damage_amount REAL DEFAULT 0,
    fraud_case_count INTEGER DEFAULT 0,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Lưu báo cáo đã gửi cơ quan chức năng
CREATE TABLE authority_reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_number TEXT UNIQUE NOT NULL,    -- REP-2025-001
    platform_name TEXT NOT NULL,
    case_ids TEXT NOT NULL,                -- JSON array of case_ids
    report_type TEXT,                      -- 'fraud', 'systematic_abuse', 'consumer_protection'
    report_document BLOB,
    recipient_authority TEXT,              -- Tên cơ quan
    sent_at TIMESTAMP,
    status TEXT DEFAULT 'draft',           -- 'draft', 'sent', 'acknowledged', 'investigating'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT
);

-- Lưu các case đã public lên website
CREATE TABLE public_cases (
    public_id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    anonymized BOOLEAN DEFAULT 1,          -- Ẩn danh hay không
    public_url TEXT,
    published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    view_count INTEGER DEFAULT 0,
    FOREIGN KEY (case_id) REFERENCES arbitration_cases(case_id) ON DELETE CASCADE
);
```

### 3.4 Workflow & Audit Tables

```sql
-- Workflow state transitions
CREATE TABLE case_workflow_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    action TEXT NOT NULL,                  -- 'created', 'analyzed', 'ruled', 'appealed', 'closed'
    actor TEXT NOT NULL,                   -- user_email or 'system'
    notes TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES arbitration_cases(case_id) ON DELETE CASCADE
);

-- Audit trail for all actions
CREATE TABLE arbitration_audit_log (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,             -- 'case', 'rule', 'evidence', 'report'
    entity_id INTEGER NOT NULL,
    action TEXT NOT NULL,                  -- 'create', 'update', 'delete', 'view'
    actor TEXT NOT NULL,                   -- user_email
    changes TEXT,                          -- JSON of changed fields
    ip_address TEXT,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_entity ON arbitration_audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_actor ON arbitration_audit_log(actor);
```

---

## 4. AI Arbiter Engine

### 4.1 Workflow

```
1. Case Input
   ↓
2. Evidence Collection (documents, videos, chats, etc.)
   ↓
3. Legal Rule Matching
   ↓
4. AI Analysis (Claude/OpenAI)
   ↓
5. Verdict Generation
   ↓
6. Action Recommendation
   ↓
7. Evidence Document Generation (if platform wrong)
```

### 4.2 AI Prompt Structure

```python
ARBITER_PROMPT_TEMPLATE = """
Bạn là một trọng tài AI chuyên nghiệp, giúp phân tích các tranh chấp thương mại.

**CASE INFORMATION:**
- Case Number: {case_number}
- Type: {dispute_type}
- Complainant: {complainant_name}
- Respondent: {respondent_name} ({respondent_type})
- Amount Disputed: {amount_disputed} {currency}
- Date of Dispute: {dispute_date}

**DESCRIPTION:**
{description}

**EVIDENCE PROVIDED:**
{evidence_list}

**APPLICABLE LEGAL RULES:**
{legal_rules}

**YOUR TASK:**
1. Phân tích case dựa trên evidence và legal rules
2. Đánh giá ai đúng, ai sai (khách quan)
3. Đưa ra phán quyết: 'platform_right', 'platform_wrong', hoặc 'unclear'
4. Giải thích reasoning chi tiết
5. Đề xuất hành động cụ thể

**OUTPUT FORMAT (JSON):**
{{
  "verdict": "platform_right | platform_wrong | unclear",
  "confidence": 0.0-1.0,
  "reasoning": "Chi tiết phân tích...",
  "platform_violations": ["Rule 1", "Rule 2", ...],
  "complainant_violations": ["Rule 3", ...],
  "applicable_rules": [rule_id1, rule_id2, ...],
  "recommended_action": "Mô tả hành động...",
  "damage_assessment": {{
    "type": "direct_loss | indirect_loss | opportunity_cost",
    "estimated_amount": number,
    "calculation_basis": "Giải thích..."
  }},
  "evidence_quality": "strong | moderate | weak",
  "additional_evidence_needed": ["What to collect..."]
}}
"""
```

### 4.3 Verdict Logic

```python
class VerdictType(Enum):
    PLATFORM_RIGHT = "platform_right"      # Sàn đúng → Gợi ý, khuyến cáo
    PLATFORM_WRONG = "platform_wrong"      # Sàn sai → Lập vi bằng
    UNCLEAR = "unclear"                    # Không đủ evidence
```

---

## 5. Evidence Generator (Vi Bằng Gian Lận)

### 5.1 Document Types

```python
EVIDENCE_DOCUMENT_TYPES = {
    "VN": {
        "template": "bien_ban_vi_pham.docx",
        "format": "Biên bản vi phạm theo Luật BVQKDNTT Việt Nam"
    },
    "US": {
        "template": "complaint_form.docx",
        "format": "FTC Complaint Format"
    },
    "INTERNATIONAL": {
        "template": "international_complaint.docx",
        "format": "International Consumer Protection Format"
    }
}
```

### 5.2 Evidence Document Structure

```
BIÊN BẢN VI PHẠM THƯƠNG MẠI ĐIỆN TỬ

I. THÔNG TIN BÊN KHIẾU NẠI
- Họ tên: ...
- CCCD/CMND: ...
- Địa chỉ: ...
- Số điện thoại: ...

II. THÔNG TIN BÊN VI PHẠM
- Tên sàn/công ty: ...
- Mã số thuế: ...
- Địa chỉ: ...

III. NỘI DUNG VI PHẠM
- Thời gian xảy ra: ...
- Hình thức vi phạm: ...
- Mô tả chi tiết: ...

IV. CHỨNG CỨ
- Danh sách chứng cứ đính kèm
- Video/hình ảnh
- Chat logs
- Emails

V. CĂN CỨ PHÁP LÝ
- Điều khoản bị vi phạm: ...
- Luật liên quan: ...

VI. YÊU CẦU
- Yêu cầu của người khiếu nại
- Thiệt hại cần được bồi thường

VII. CHỮ KÝ XÁC NHẬN
```

### 5.3 Auto-generation Process

```python
def generate_evidence_document(case_id):
    """
    1. Load case data
    2. Load AI verdict
    3. Collect evidence files
    4. Select template based on jurisdiction
    5. Fill template with data
    6. Generate PDF
    7. Store in database
    8. Return document path
    """
```

---

## 6. Public Reporting System

### 6.1 Features

#### A. Case Classification
- Automatic pattern detection
- Fraud indicator analysis
- Similar case grouping

#### B. Statistics Dashboard
- Cases by platform
- Win/loss ratio
- Total damages
- Fraud trends

#### C. Public Website
- Anonymized case publishing
- Search by platform
- Statistics visualization
- Download evidence documents

#### D. Authority Notification
- Automatic report generation
- Email to authorities
- Tracking report status

### 6.2 API Endpoints

```python
# Statistics
GET  /api/arbitration/statistics
GET  /api/arbitration/statistics/platform/{platform_name}

# Public cases
GET  /api/arbitration/public/cases
GET  /api/arbitration/public/case/{case_id}

# Reports
POST /api/arbitration/reports/generate
POST /api/arbitration/reports/send
GET  /api/arbitration/reports/{report_id}
```

---

## 7. Frontend UI Design

### 7.1 Main Routes

```
/arbitration                    # Dashboard
/arbitration/cases              # Case list
/arbitration/cases/new          # Create new case
/arbitration/cases/{id}         # Case detail + AI analysis
/arbitration/knowledge-base     # Legal rules management
/arbitration/reports            # Statistics & reports
/arbitration/public             # Public cases view
```

### 7.2 Key Components

#### CaseForm.tsx
- Multi-step form (Wizard)
- Evidence upload (drag & drop)
- Party information
- Dispute details

#### CaseDetail.tsx
- Case information
- Evidence viewer (video, images, documents)
- AI verdict display
- Timeline of actions
- Comments section

#### VerdictView.tsx
- Visual verdict (green/red/yellow)
- Confidence meter
- Reasoning display
- Recommended actions
- Download evidence document

#### LegalRuleManager.tsx
- Rule CRUD
- Category management
- Search & filter
- Version control

#### StatisticsBoard.tsx
- Charts (platform win/loss ratio)
- Damage totals
- Fraud trends
- Export reports

---

## 8. Security & Privacy

### 8.1 Data Protection
- Encrypt sensitive fields (CCCD, phone numbers)
- Anonymize public cases
- GDPR compliance (data deletion)

### 8.2 Access Control
- Role-based access (User, Admin, Auditor)
- Audit trail for all actions
- IP logging

### 8.3 File Storage
- Evidence files: encrypted at rest
- Virus scanning for uploads
- Size limits (e.g., 50MB per file)

---

## 9. Implementation Plan

### Phase 1: Core Infrastructure (Week 1)
- [ ] Create database tables
- [ ] Setup backend modules structure
- [ ] Create basic API routes
- [ ] Setup frontend routes

### Phase 2: Legal Knowledge Base (Week 1-2)
- [ ] Rule CRUD API
- [ ] Rule manager UI
- [ ] Document parser
- [ ] Search functionality

### Phase 3: Case Management (Week 2-3)
- [ ] Case CRUD API
- [ ] Evidence upload
- [ ] Case form UI
- [ ] Case detail UI

### Phase 4: AI Arbiter (Week 3-4)
- [ ] AI service integration
- [ ] Prompt engineering
- [ ] Verdict logic
- [ ] Confidence calculation

### Phase 5: Evidence Generator (Week 4)
- [ ] Document templates
- [ ] Auto-generation engine
- [ ] PDF export
- [ ] Download UI

### Phase 6: Classification & Reporting (Week 5)
- [ ] Pattern detection
- [ ] Statistics engine
- [ ] Dashboard UI
- [ ] Report generation

### Phase 7: Public Reporting (Week 5-6)
- [ ] Public website
- [ ] Anonymization
- [ ] Authority notification
- [ ] Email integration

### Phase 8: Testing & Polish (Week 6)
- [ ] Unit tests
- [ ] Integration tests
- [ ] UI/UX improvements
- [ ] Documentation

---

## 10. AI Models & Costs

### 10.1 Recommended Models

**Claude (Anthropic)** - Primary
- Model: Claude 3.5 Sonnet
- Strengths: Legal reasoning, Vietnamese support
- Cost: ~$3/1M input tokens, ~$15/1M output tokens

**OpenAI** - Backup
- Model: GPT-4o
- Strengths: Structured output, JSON mode
- Cost: ~$5/1M input tokens, ~$15/1M output tokens

### 10.2 Cost Estimation

Average case analysis:
- Input tokens: ~5,000 (case + rules + evidence)
- Output tokens: ~1,000 (verdict + reasoning)
- Cost per case: ~$0.03 - $0.05

For 1000 cases/month: ~$30-50

---

## 11. Future Enhancements

1. **Multi-language Support**
   - English, Vietnamese, Chinese
   - Auto-translation

2. **Advanced Analytics**
   - Predictive case outcomes
   - Risk scoring
   - Fraud detection ML models

3. **Integration with External Systems**
   - Court filing systems
   - Government portals
   - Payment processors

4. **Mobile App**
   - iOS/Android app
   - Push notifications
   - Quick case creation

5. **Blockchain Evidence**
   - Immutable evidence storage
   - Timestamping
   - Smart contracts for automated payouts

---

## 12. Technical Considerations

### 12.1 Performance
- Async AI calls (don't block UI)
- Caching frequent rules
- Pagination for large case lists
- Lazy loading evidence files

### 12.2 Scalability
- SQLite → PostgreSQL migration path
- Microservices architecture option
- CDN for public website

### 12.3 Reliability
- Retry logic for AI calls
- Fallback to alternative AI provider
- Background job processing
- Error logging (Sentry)

---

## 13. References

### Vietnamese Laws
- Luật Bảo vệ Quyền lợi Người tiêu dùng 2010
- Luật Thương mại 2005
- Nghị định 52/2013/NĐ-CP về TMĐT
- Luật Cạnh tranh 2018

### International
- UNCITRAL Model Law on Electronic Commerce
- EU Consumer Rights Directive
- US FTC Act

### Technical
- OpenAI API Documentation
- Anthropic Claude API Documentation
- Flask Documentation
- Next.js Documentation
- Chakra UI Documentation

---

**Document Version**: 1.0
**Created**: 2025-11-21
**Author**: AI Assistant (Claude)
**Status**: Design Phase
