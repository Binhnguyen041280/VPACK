# AI Arbitration System - README

## Tổng quan (Overview)

**AI Arbitration System** là hệ thống trọng tài AI giúp người bán hàng xử lý các khiếu nại thương mại một cách khách quan, dựa trên luật pháp và quy định của sàn thương mại điện tử.

### Vấn đề giải quyết
- Người bán không nắm rõ luật, hợp đồng, điều kiện của sàn
- Bị bức xúc khi xử lý khiếu nại vì thiếu thông tin
- Cần công cụ phân tích khách quan
- Cần lập vi bằng gian lận tự động khi sàn sai

### Giải pháp
Hệ thống AI với 5 module chính:
1. **Legal Knowledge Base**: Lưu trữ và quản lý luật/quy định/hợp đồng
2. **Case Management**: Quản lý case khiếu nại (tạo, cập nhật, lưu trữ chứng cứ)
3. **AI Arbiter Engine**: Phân tích case bằng AI (Claude/OpenAI) và đưa ra phán quyết
4. **Evidence Generator**: Tự động tạo vi bằng gian lận theo mẫu pháp luật
5. **Public Reporting**: Thống kê, phân loại, báo cáo cơ quan chức năng

---

## Cài đặt (Installation)

### Yêu cầu
- Python 3.8+
- SQLite
- Flask
- Claude API key hoặc OpenAI API key

### Database Migration

Database sẽ tự động được migrate khi khởi động backend:

```bash
cd /home/user/VPACK/backend
python app.py
```

Hoặc chạy migration độc lập:

```bash
python -m modules.arbitration.database_migration
```

---

## Sử dụng (Usage)

### 1. API Endpoints

Base URL: `http://localhost:8080/api/arbitration`

#### Case Management

**Tạo case mới:**
```bash
POST /api/arbitration/cases
Content-Type: application/json

{
  "title": "Sàn khóa tài khoản không lý do",
  "description": "Tài khoản bị khóa đột ngột sau khi có đơn hàng lớn...",
  "complainant_name": "Nguyễn Văn A",
  "complainant_email": "nguyenvana@example.com",
  "complainant_phone": "0912345678",
  "respondent_name": "Shopee",
  "respondent_type": "platform",
  "dispute_type": "ban",
  "amount_disputed": 50000000,
  "currency": "VND",
  "created_by": "user@example.com"
}
```

Response:
```json
{
  "success": true,
  "case_id": 1,
  "case_number": "ARB-2025-001",
  "case": {...}
}
```

**Lấy danh sách cases:**
```bash
GET /api/arbitration/cases?status=new&limit=20
```

**Lấy chi tiết case:**
```bash
GET /api/arbitration/cases/1
```

**Cập nhật case:**
```bash
PUT /api/arbitration/cases/1
Content-Type: application/json

{
  "updates": {
    "status": "analyzing",
    "priority": "high"
  },
  "updated_by": "user@example.com"
}
```

#### Evidence Management

**Thêm chứng cứ (file upload):**
```bash
POST /api/arbitration/cases/1/evidence
Content-Type: multipart/form-data

file: [video/image/document file]
evidence_type: "video"
description: "Video ghi lại quá trình bị khóa tài khoản"
uploaded_by: "user@example.com"
```

**Thêm comment:**
```bash
POST /api/arbitration/cases/1/comments
Content-Type: application/json

{
  "comment_text": "Đã liên hệ với sàn nhưng không được phản hồi",
  "author": "user@example.com",
  "comment_type": "note"
}
```

#### AI Analysis

**Phân tích case bằng AI:**
```bash
POST /api/arbitration/cases/1/analyze
Content-Type: application/json

{
  "user_email": "user@example.com",
  "force": false
}
```

Response:
```json
{
  "success": true,
  "analysis": {
    "verdict": "platform_wrong",
    "confidence": 0.85,
    "reasoning": "Phân tích chi tiết...",
    "platform_violations": ["Vi phạm quy trình khóa tài khoản", "Không thông báo rõ lý do"],
    "recommended_action": "Khiếu nại lên cơ quan quản lý...",
    "damage_assessment": {
      "type": "direct_loss",
      "estimated_amount": 50000000,
      "calculation_basis": "..."
    }
  },
  "formatted_verdict": {
    "verdict_label": "Sàn Sai",
    "verdict_color": "red",
    "confidence_percent": "85%"
  }
}
```

**Download vi bằng gian lận:**
```bash
GET /api/arbitration/cases/1/evidence-document
```

#### Legal Knowledge Base

**Tìm kiếm luật/quy định:**
```bash
GET /api/arbitration/rules?query=hoàn tiền&jurisdiction=VN&category=refund
```

**Thêm luật/quy định mới:**
```bash
POST /api/arbitration/rules
Content-Type: application/json

{
  "rule_type": "platform",
  "title": "Quy định hoàn tiền của Shopee",
  "content": "Nội dung quy định...",
  "jurisdiction": "VN",
  "category": "refund",
  "keywords": ["hoàn tiền", "refund", "bảo hành"],
  "created_by": "admin@example.com"
}
```

#### Statistics

**Thống kê tổng quan:**
```bash
GET /api/arbitration/statistics
```

**Thống kê theo platform:**
```bash
GET /api/arbitration/statistics/platform/Shopee?period_start=2025-01-01&period_end=2025-12-31
```

Response:
```json
{
  "success": true,
  "statistics": {
    "platform_name": "Shopee",
    "total_cases": 150,
    "platform_right_count": 80,
    "platform_wrong_count": 50,
    "unclear_count": 20,
    "total_damage_amount": 500000000,
    "fraud_case_count": 10
  }
}
```

---

## Architecture

### Backend Modules

```
backend/
├── modules/
│   ├── arbitration/              # Core arbitration logic
│   │   ├── case_manager.py       # CRUD operations for cases
│   │   ├── ai_arbiter.py         # AI analysis engine
│   │   ├── evidence_generator.py # Auto-generate legal documents
│   │   ├── verdict_formatter.py  # Format verdict for display
│   │   └── damage_assessor.py    # Assess damages
│   │
│   ├── legal/                    # Legal knowledge management
│   │   ├── knowledge_base.py     # Store and retrieve legal rules
│   │   ├── rule_matcher.py       # Match rules to cases
│   │   └── document_parser.py    # Parse legal documents
│   │
│   ├── reporting/                # Reporting and analytics
│   │   ├── case_classifier.py    # Classify cases by pattern
│   │   ├── statistics.py         # Generate statistics
│   │   ├── public_reporter.py    # Publish to public website
│   │   └── authority_notifier.py # Notify authorities
│   │
│   └── workflow/                 # Workflow management
│       ├── state_machine.py      # Case state transitions
│       └── notification.py       # Notification service
│
└── api/
    └── arbitration_routes.py     # Flask REST API endpoints
```

### Database Schema

**Main Tables:**
1. `legal_rules` - Legal rules and regulations
2. `arbitration_cases` - Arbitration cases
3. `case_evidence` - Evidence files
4. `case_analysis_history` - AI analysis history
5. `case_comments` - Case comments
6. `case_classifications` - Pattern classification
7. `platform_statistics` - Platform statistics
8. `authority_reports` - Reports to authorities
9. `public_cases` - Public cases
10. `case_workflow_log` - Workflow state changes
11. `arbitration_audit_log` - Audit trail

---

## AI Configuration

### Setup AI API Key

1. Vào trang cấu hình AI trong ứng dụng
2. Chọn provider: Claude (Anthropic) hoặc OpenAI
3. Nhập API key
4. Enable AI analysis

### AI Prompt

Hệ thống sử dụng prompt được tối ưu để:
- Phân tích case dựa trên luật/quy định
- Đánh giá khách quan ai đúng, ai sai
- Đề xuất hành động cụ thể
- Ước tính thiệt hại
- Đánh giá chất lượng chứng cứ

### Cost Estimation

- Average cost per case: ~$0.03 - $0.05
- For 1000 cases/month: ~$30-50

---

## Workflows

### Workflow 1: Tạo và phân tích case

```
1. User tạo case mới qua API
   ↓
2. Hệ thống generate case number (ARB-2025-001)
   ↓
3. User upload chứng cứ (video, images, documents)
   ↓
4. User trigger AI analysis
   ↓
5. AI Arbiter:
   - Tìm các luật/quy định liên quan
   - Phân tích case
   - Đưa ra phán quyết (platform_right/platform_wrong/unclear)
   ↓
6. Nếu platform_wrong:
   - Auto-generate vi bằng gian lận
   - Classify case (systematic_fraud/policy_abuse/isolated)
   - Save to database
   ↓
7. User download vi bằng và làm theo recommended actions
```

### Workflow 2: Báo cáo cơ quan chức năng

```
1. System phân loại các case có pattern vi phạm hệ thống
   ↓
2. Group các case theo platform + loại vi phạm
   ↓
3. Generate authority report (REP-2025-001)
   ↓
4. Admin review và gửi report đến cơ quan chức năng
   ↓
5. Track report status (sent/acknowledged/investigating/resolved)
```

---

## Sample Data

Hệ thống đi kèm 5 sample legal rules cho Vietnam:
1. Luật Bảo vệ Quyền lợi Người tiêu dùng - Điều 8
2. Nghị định 52/2013/NĐ-CP - Trách nhiệm sàn TMĐT
3. Quy định hoàn tiền của sàn
4. Quy định về vi phạm và khóa tài khoản
5. Luật Thương mại 2005 - Điều 10

Để seed sample data:

```bash
python -m modules.arbitration.database_migration
# Chọn 'y' khi được hỏi về seeding sample rules
```

---

## Troubleshooting

### Database Migration Issues

**Error: "table already exists"**
- Đây là warning bình thường, database migration sử dụng `CREATE TABLE IF NOT EXISTS`

**Error: "module not found"**
```bash
# Ensure you're in the backend directory
cd /home/user/VPACK/backend

# Check Python path
python -c "import sys; print(sys.path)"
```

### AI Analysis Issues

**Error: "AI not enabled for user"**
- User cần setup AI API key trước
- Check `ai_config` table trong database

**Error: "Failed to parse AI response"**
- AI response không đúng format JSON
- Check `case_analysis_history` table để debug

---

## Future Enhancements

### Phase 2 (Upcoming)
- [ ] Multi-language support (English, Chinese)
- [ ] Advanced NLP for automatic rule matching
- [ ] ML-based fraud detection
- [ ] Integration with court filing systems
- [ ] Mobile app (iOS/Android)
- [ ] Blockchain evidence storage

### Phase 3
- [ ] Predictive analytics (predict case outcomes)
- [ ] Automated negotiation with platforms
- [ ] Smart contracts for automated payouts

---

## API Documentation

Full API documentation available at:
- Swagger UI: `http://localhost:8080/api/docs` (TODO: implement)
- Postman Collection: See `/docs/postman/AI_Arbitration_API.json` (TODO: create)

---

## Testing

### Manual Testing

Use Postman or curl to test endpoints:

```bash
# Health check
curl http://localhost:8080/api/arbitration/health

# Create case
curl -X POST http://localhost:8080/api/arbitration/cases \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test case",
    "description": "Test description",
    "complainant_name": "Test User",
    "respondent_name": "Test Platform",
    "dispute_type": "refund",
    "created_by": "test@example.com"
  }'
```

### Unit Tests (TODO)

```bash
cd backend
pytest tests/test_arbitration/
```

---

## Contributors

- VPACK Team
- Developed with Claude AI (Anthropic)

---

## License

Copyright © 2025 VPACK. All rights reserved.

---

## Support

For issues or questions:
- GitHub Issues: [Create issue](https://github.com/your-repo/issues)
- Email: support@vpack.com
- Documentation: `/docs/AI_ARBITRATION_SYSTEM_DESIGN.md`

---

**Version**: 1.0.0
**Last Updated**: 2025-11-21
