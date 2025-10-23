Kế Hoạch Thực Hiện Backend API cho AI Usage

  📋 Tổng Quan

  Mục tiêu: Tạo backend API để quản lý AI configuration, test API keys, và tracking usage - tận dụng
  tối đa pattern có sẵn trong codebase.

  ---
  🏗️ Chi Tiết Từng Bước

  Bước 1: Install Dependencies

  pip install anthropic
  - Cài Anthropic SDK để gọi Claude API
  - OpenAI đã có sẵn (v1.102.0)

  Bước 2: Database Schema

  Tạo migration hoặc thêm vào database.py:

  -- AI Configuration table
  CREATE TABLE IF NOT EXISTS ai_config (
      user_email TEXT PRIMARY KEY,
      ai_enabled INTEGER DEFAULT 0,
      api_provider TEXT DEFAULT 'claude',
      encrypted_api_key TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  -- AI Recovery Logs (tracking usage & cost)
  CREATE TABLE IF NOT EXISTS ai_recovery_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_email TEXT NOT NULL,
      event_id TEXT,
      frame_path TEXT,
      success INTEGER DEFAULT 0,
      decoded_text TEXT,
      cost_usd REAL DEFAULT 0,
      input_tokens INTEGER,
      output_tokens INTEGER,
      error_message TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_email) REFERENCES ai_config(user_email)
  );

  -- Index cho performance
  CREATE INDEX IF NOT EXISTS idx_ai_logs_user ON ai_recovery_logs(user_email);
  CREATE INDEX IF NOT EXISTS idx_ai_logs_created ON ai_recovery_logs(created_at);

  Tái sử dụng: Pattern từ database_operations.py

  Bước 3: AI Service Layer

  Tạo file: backend/modules/config/services/ai_service.py

  Chức năng:
  - encrypt_api_key(): Sử dụng Fernet từ cloud_auth.py (line 170-179)
  - decrypt_api_key(): Giải mã API key
  - test_claude_key(): Test Claude API key
  - test_openai_key(): Test OpenAI API key
  - get_ai_config(): Lấy config từ DB
  - update_ai_config(): Cập nhật config
  - get_usage_stats(): Thống kê usage từ logs
  - recover_qr_with_claude(): Core recovery function (dùng sau)

  Tái sử dụng:
  - Encryption pattern từ cloud_auth.py (lines 170-190, 463-534)
  - Error handling từ shared/error_handlers.py
  - Database operations từ shared/db_operations.py

  Bước 4: AI Routes

  Tạo file: backend/modules/config/routes/ai_routes.py

  Endpoints:

  from flask import Blueprint, request, jsonify, session
  from flask_cors import cross_origin
  from ..services.ai_service import AIService
  from ..shared import (
      create_success_response,
      create_error_response,
      validate_request_data,
      handle_general_error
  )

  ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')

  @ai_bp.route('/config', methods=['GET'])
  @cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
  def get_ai_config():
      """Get AI configuration for current user"""
      # Pattern từ step1_brandname_routes.py (lines 27-60)

  @ai_bp.route('/config', methods=['POST'])
  @cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
  def update_ai_config():
      """Update AI configuration"""
      # Pattern từ step1_brandname_routes.py (lines 63-116)

  @ai_bp.route('/test', methods=['POST'])
  @cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
  def test_api_key():
      """Test API key validity with actual API call"""
      # New endpoint - test thực tế với provider API

  @ai_bp.route('/stats', methods=['GET'])
  @cross_origin(origins=['http://localhost:3000'], supports_credentials=True)
  def get_ai_stats():
      """Get AI usage statistics"""
      # Query từ ai_recovery_logs table

  Tái sử dụng:
  - Blueprint pattern từ step1_brandname_routes.py
  - CORS config có sẵn
  - Response format từ error_handlers.py
  - Session handling có sẵn

  Bước 5: Register Blueprint

  Trong backend/app.py:

  from modules.config.routes.ai_routes import ai_bp

  # Register blueprint
  app.register_blueprint(ai_bp)

  Tái sử dụng: Pattern từ các blueprint khác đã register

  Bước 6: Update Frontend

  Trong frontend/src/components/account/AIUsage.tsx:

  // Thay thế mock data bằng real API calls
  useEffect(() => {
    const loadData = async () => {
      try {
        const config = await AccountService.getAIConfig();
        setAiConfig(config.data);

        const stats = await AccountService.getAIStats();
        setStats(stats.data);

        setIsLoading(false);
      } catch (error) {
        setError(error.message);
      }
    };
    loadData();
  }, []);

  Tái sử dụng:
  - AccountService methods đã define sẵn (lines 207-328)
  - Chỉ cần uncomment các API calls

  Bước 7: Testing

  Test Cases:

  1. API Key Validation:
  - Valid Claude key → Success
  - Invalid Claude key → 401 error
  - Valid OpenAI key → Success
  - Invalid OpenAI key → 401 error
  2. Config CRUD:
  - GET /api/ai/config → Return current config
  - POST /api/ai/config → Save with encryption
  - Verify encrypted key in DB
  - Verify decrypted key matches original
  3. Stats:
  - GET /api/ai/stats → Return 0 for new user
  - After recovery → Stats updated
  4. End-to-End:
  - UI Enable → Backend saves
  - UI Test Key → Backend validates
  - UI Save → Backend encrypts & stores
  - Reload page → Config persists

  ---
  🔧 Tài Nguyên Tái Sử Dụng

  | Component       | Source File               | Lines            |
  |-----------------|---------------------------|------------------|
  | Encryption      | cloud_auth.py             | 170-190, 463-534 |
  | Error Handling  | shared/error_handlers.py  | All              |
  | DB Operations   | shared/db_operations.py   | All              |
  | Route Pattern   | step1_brandname_routes.py | 27-116           |
  | Response Format | error_handlers.py         | 33-60            |
  | Validation      | shared/validation.py      | All              |
  | Session         | cloud_auth.py             | 138-168          |

  ---
  📊 Ước Tính

  - Files mới: 2 files (ai_service.py, ai_routes.py)
  - Files sửa: 3 files (app.py, database.py, AIUsage.tsx)
  - Lines of code: ~600 lines total
  - Dependencies: 1 package (anthropic)
  - Testing time: ~30 phút
  - Tổng thời gian: ~2-3 giờ

  ---
  ⚠️ Lưu Ý Bảo Mật

  1. API Key Encryption: Dùng Fernet (AES-256)
  2. Key Storage: File permissions 0o600
  3. Session: Require authentication
  4. Logging: Audit log cho security events
  5. Environment: ENCRYPTION_KEY từ env variable

  ---
  🎯 Kết Quả Mong Đợi

  Sau khi hoàn thành:
  - ✅ User có thể nhập API key Claude/OpenAI
  - ✅ System test key trước khi lưu
  - ✅ API key được encrypt an toàn
  - ✅ UI hiển thị config từ backend thật
  - ✅ Ready để implement QR recovery sau
                                                                          
⏺User approved Claude's plan:
  ⎿  Backend API Implementation Plan for AI Usage

     Tasks (8 steps):

     1. Install Anthropic SDK - pip install anthropic
     2. Create Database Schema - Add ai_config & ai_recovery_logs tables  
     3. Create AI Service Layer - Reuse encryption from cloud_auth.py
     4. Create AI Routes - Following step1_brandname_routes.py pattern
     5. Register Blueprint - Add to app.py
     6. Update Frontend - Uncomment real API calls in AIUsage.tsx
     7. Test API Keys - Validate Claude & OpenAI keys
     8. End-to-end Test - Full flow from UI to backend

     Key Reuse:

     - Encryption: cloud_auth.py (Fernet)
     - Error handling: shared/error_handlers.py
     - Route pattern: step1_brandname_routes.py
     - DB ops: shared/db_operations.py

     Deliverables:

     - 2 new files (ai_service.py, ai_routes.py)
     - 3 modified files (app.py, database.py, AIUsage.tsx)
     - ~600 LOC total
     - Secure API key storage with AES-256 encryption