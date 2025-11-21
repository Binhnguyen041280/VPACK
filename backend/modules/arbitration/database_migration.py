"""
AI Arbitration System - Database Migration

Creates all necessary tables, indexes, and triggers for the AI Arbitration System.
Integrates seamlessly with existing VPACK database structure.
"""

import sqlite3
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)


def migrate_arbitration_tables(conn):
    """
    Create all AI Arbitration System tables

    Args:
        conn: SQLite database connection

    Returns:
        bool: True if migration successful, False otherwise
    """
    try:
        cursor = conn.cursor()

        logger.info("🔧 Starting AI Arbitration System database migration...")

        # ==================== LEGAL KNOWLEDGE BASE TABLES ====================

        # 1. Legal Rules Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS legal_rules (
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
            )
        """)
        logger.info("✅ Created legal_rules table")

        # 2. Rule References Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rule_references (
                ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_rule_id INTEGER NOT NULL,
                to_rule_id INTEGER NOT NULL,
                relationship TEXT,                     -- 'supersedes', 'related', 'contradicts', etc.
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_rule_id) REFERENCES legal_rules(rule_id) ON DELETE CASCADE,
                FOREIGN KEY (to_rule_id) REFERENCES legal_rules(rule_id) ON DELETE CASCADE
            )
        """)
        logger.info("✅ Created rule_references table")

        # ==================== CASE MANAGEMENT TABLES ====================

        # 3. Arbitration Cases Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS arbitration_cases (
                case_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_number TEXT UNIQUE NOT NULL,      -- Auto-generated: ARB-2025-001
                title TEXT NOT NULL,
                description TEXT NOT NULL,

                -- Parties
                complainant_name TEXT NOT NULL,        -- Người khiếu nại (người bán)
                complainant_email TEXT,
                complainant_phone TEXT,
                complainant_id_number TEXT,            -- CCCD/CMND
                respondent_name TEXT NOT NULL,         -- Bên bị khiếu nại (sàn/platform)
                respondent_type TEXT,                  -- 'platform', 'buyer', 'supplier', etc.
                respondent_tax_id TEXT,                -- Mã số thuế

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
                platform_violations TEXT,              -- JSON array of violations

                -- Outcome
                recommended_action TEXT,               -- Gợi ý hành động
                damage_assessment TEXT,                -- JSON: { type, amount, evidence }
                evidence_generated BOOLEAN DEFAULT 0,
                evidence_document BLOB,                -- Generated evidence document
                evidence_document_path TEXT,           -- Path to evidence document

                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                analyzed_at TIMESTAMP,
                closed_at TIMESTAMP,

                -- Creator
                created_by TEXT NOT NULL               -- user_email
            )
        """)
        logger.info("✅ Created arbitration_cases table")

        # 4. Case Evidence Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS case_evidence (
                evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                evidence_type TEXT NOT NULL,           -- 'video', 'image', 'document', 'chat', 'email', 'screenshot'
                file_name TEXT,
                file_path TEXT,
                file_blob BLOB,                        -- Lưu file nhỏ trực tiếp
                file_size_bytes INTEGER,
                cloud_url TEXT,                        -- Google Drive URL
                description TEXT,
                uploaded_by TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES arbitration_cases(case_id) ON DELETE CASCADE
            )
        """)
        logger.info("✅ Created case_evidence table")

        # 5. Case Analysis History Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS case_analysis_history (
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
            )
        """)
        logger.info("✅ Created case_analysis_history table")

        # 6. Case Comments Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS case_comments (
                comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                comment_text TEXT NOT NULL,
                comment_type TEXT DEFAULT 'note',      -- 'note', 'update', 'decision'
                author TEXT NOT NULL,                  -- user_email
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES arbitration_cases(case_id) ON DELETE CASCADE
            )
        """)
        logger.info("✅ Created case_comments table")

        # ==================== REPORTING & CLASSIFICATION TABLES ====================

        # 7. Case Classifications Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS case_classifications (
                classification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                pattern_type TEXT NOT NULL,            -- 'systematic_fraud', 'policy_abuse', 'isolated_incident'
                severity TEXT,                         -- 'minor', 'moderate', 'severe', 'critical'
                fraud_indicators TEXT,                 -- JSON array of fraud signals
                similar_cases TEXT,                    -- JSON array of similar case_ids
                classified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                classified_by TEXT,                    -- 'system' or user_email
                FOREIGN KEY (case_id) REFERENCES arbitration_cases(case_id) ON DELETE CASCADE
            )
        """)
        logger.info("✅ Created case_classifications table")

        # 8. Platform Statistics Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS platform_statistics (
                stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform_name TEXT NOT NULL,
                period_start DATE,
                period_end DATE,
                total_cases INTEGER DEFAULT 0,
                platform_right_count INTEGER DEFAULT 0,
                platform_wrong_count INTEGER DEFAULT 0,
                unclear_count INTEGER DEFAULT 0,
                total_damage_amount REAL DEFAULT 0,
                fraud_case_count INTEGER DEFAULT 0,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("✅ Created platform_statistics table")

        # 9. Authority Reports Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS authority_reports (
                report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_number TEXT UNIQUE NOT NULL,    -- REP-2025-001
                platform_name TEXT NOT NULL,
                case_ids TEXT NOT NULL,                -- JSON array of case_ids
                report_type TEXT,                      -- 'fraud', 'systematic_abuse', 'consumer_protection'
                report_document BLOB,
                report_document_path TEXT,
                recipient_authority TEXT,              -- Tên cơ quan
                recipient_email TEXT,
                sent_at TIMESTAMP,
                status TEXT DEFAULT 'draft',           -- 'draft', 'sent', 'acknowledged', 'investigating', 'resolved'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT
            )
        """)
        logger.info("✅ Created authority_reports table")

        # 10. Public Cases Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public_cases (
                public_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                anonymized BOOLEAN DEFAULT 1,          -- Ẩn danh hay không
                public_url TEXT,
                published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                view_count INTEGER DEFAULT 0,
                last_viewed_at TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES arbitration_cases(case_id) ON DELETE CASCADE
            )
        """)
        logger.info("✅ Created public_cases table")

        # ==================== WORKFLOW & AUDIT TABLES ====================

        # 11. Case Workflow Log Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS case_workflow_log (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                from_status TEXT,
                to_status TEXT NOT NULL,
                action TEXT NOT NULL,                  -- 'created', 'analyzed', 'ruled', 'appealed', 'closed'
                actor TEXT NOT NULL,                   -- user_email or 'system'
                notes TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES arbitration_cases(case_id) ON DELETE CASCADE
            )
        """)
        logger.info("✅ Created case_workflow_log table")

        # 12. Arbitration Audit Log Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS arbitration_audit_log (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,             -- 'case', 'rule', 'evidence', 'report'
                entity_id INTEGER NOT NULL,
                action TEXT NOT NULL,                  -- 'create', 'update', 'delete', 'view'
                actor TEXT NOT NULL,                   -- user_email
                changes TEXT,                          -- JSON of changed fields
                ip_address TEXT,
                user_agent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("✅ Created arbitration_audit_log table")

        # ==================== CREATE INDEXES ====================

        logger.info("🔧 Creating indexes...")

        # Legal rules indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_legal_rules_type ON legal_rules(rule_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_legal_rules_category ON legal_rules(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_legal_rules_jurisdiction ON legal_rules(jurisdiction)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_legal_rules_created ON legal_rules(created_at)")

        # Case indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_status ON arbitration_cases(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_type ON arbitration_cases(dispute_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_creator ON arbitration_cases(created_by)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_verdict ON arbitration_cases(ai_verdict)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_number ON arbitration_cases(case_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_created ON arbitration_cases(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_respondent ON arbitration_cases(respondent_name)")

        # Evidence indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_case ON case_evidence(case_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_type ON case_evidence(evidence_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_uploaded ON case_evidence(uploaded_at)")

        # Analysis history indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_case ON case_analysis_history(case_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_provider ON case_analysis_history(ai_provider)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_date ON case_analysis_history(analyzed_at)")

        # Classification indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_classification_case ON case_classifications(case_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_classification_pattern ON case_classifications(pattern_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_classification_severity ON case_classifications(severity)")

        # Statistics indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stats_platform ON platform_statistics(platform_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stats_period ON platform_statistics(period_start, period_end)")

        # Public cases indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_public_case ON public_cases(case_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_public_published ON public_cases(published_at)")

        # Workflow indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflow_case ON case_workflow_log(case_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflow_timestamp ON case_workflow_log(timestamp)")

        # Audit indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_entity ON arbitration_audit_log(entity_type, entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_actor ON arbitration_audit_log(actor)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON arbitration_audit_log(timestamp)")

        logger.info("✅ Created all indexes")

        # ==================== CREATE TRIGGERS ====================

        logger.info("🔧 Creating triggers...")

        # Update timestamp trigger for legal_rules
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_legal_rules_timestamp
            AFTER UPDATE ON legal_rules
            FOR EACH ROW
            BEGIN
                UPDATE legal_rules SET updated_at = CURRENT_TIMESTAMP WHERE rule_id = NEW.rule_id;
            END
        """)

        # Update timestamp trigger for arbitration_cases
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_arbitration_cases_timestamp
            AFTER UPDATE ON arbitration_cases
            FOR EACH ROW
            BEGIN
                UPDATE arbitration_cases SET updated_at = CURRENT_TIMESTAMP WHERE case_id = NEW.case_id;
            END
        """)

        # Update timestamp trigger for platform_statistics
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_platform_statistics_timestamp
            AFTER UPDATE ON platform_statistics
            FOR EACH ROW
            BEGIN
                UPDATE platform_statistics SET updated_at = CURRENT_TIMESTAMP WHERE stat_id = NEW.stat_id;
            END
        """)

        # Auto-create workflow log when case status changes
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS log_case_status_change
            AFTER UPDATE OF status ON arbitration_cases
            WHEN OLD.status != NEW.status
            BEGIN
                INSERT INTO case_workflow_log (case_id, from_status, to_status, action, actor)
                VALUES (NEW.case_id, OLD.status, NEW.status, 'status_changed', 'system');
            END
        """)

        logger.info("✅ Created all triggers")

        # ==================== CREATE VIEWS ====================

        logger.info("🔧 Creating views...")

        # Active cases view
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS active_cases_view AS
            SELECT
                c.case_id,
                c.case_number,
                c.title,
                c.dispute_type,
                c.respondent_name,
                c.amount_disputed,
                c.currency,
                c.status,
                c.ai_verdict,
                c.ai_confidence,
                c.created_at,
                c.created_by,
                COUNT(DISTINCT e.evidence_id) as evidence_count,
                COUNT(DISTINCT cm.comment_id) as comment_count
            FROM arbitration_cases c
            LEFT JOIN case_evidence e ON c.case_id = e.case_id
            LEFT JOIN case_comments cm ON c.case_id = cm.case_id
            WHERE c.status != 'closed'
            GROUP BY c.case_id
        """)

        # Platform performance view
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS platform_performance_view AS
            SELECT
                respondent_name as platform_name,
                COUNT(*) as total_cases,
                SUM(CASE WHEN ai_verdict = 'platform_right' THEN 1 ELSE 0 END) as right_count,
                SUM(CASE WHEN ai_verdict = 'platform_wrong' THEN 1 ELSE 0 END) as wrong_count,
                SUM(CASE WHEN ai_verdict = 'unclear' THEN 1 ELSE 0 END) as unclear_count,
                ROUND(AVG(amount_disputed), 2) as avg_dispute_amount,
                SUM(amount_disputed) as total_disputed
            FROM arbitration_cases
            WHERE respondent_type = 'platform'
            GROUP BY respondent_name
        """)

        # Case summary view
        cursor.execute("""
            CREATE VIEW IF NOT EXISTS case_summary_view AS
            SELECT
                c.case_id,
                c.case_number,
                c.title,
                c.complainant_name,
                c.respondent_name,
                c.dispute_type,
                c.status,
                c.ai_verdict,
                c.ai_confidence,
                c.amount_disputed,
                c.currency,
                c.created_at,
                c.analyzed_at,
                CASE
                    WHEN c.evidence_generated = 1 THEN 'Yes'
                    ELSE 'No'
                END as has_evidence_doc,
                COUNT(DISTINCT e.evidence_id) as evidence_count,
                cla.severity as classification_severity,
                cla.pattern_type as classification_pattern
            FROM arbitration_cases c
            LEFT JOIN case_evidence e ON c.case_id = e.case_id
            LEFT JOIN case_classifications cla ON c.case_id = cla.case_id
            GROUP BY c.case_id
        """)

        logger.info("✅ Created all views")

        # ==================== COMMIT CHANGES ====================

        conn.commit()

        logger.info("✅ AI Arbitration System database migration completed successfully!")
        logger.info("   - Created 12 tables")
        logger.info("   - Created 25+ indexes")
        logger.info("   - Created 4 triggers")
        logger.info("   - Created 3 views")

        return True

    except Exception as e:
        logger.error(f"❌ Error during arbitration database migration: {e}")
        conn.rollback()
        return False


def seed_sample_legal_rules(conn):
    """
    Seed database with sample legal rules for Vietnam

    Args:
        conn: SQLite database connection
    """
    try:
        cursor = conn.cursor()

        logger.info("🌱 Seeding sample legal rules...")

        sample_rules = [
            {
                'rule_type': 'commercial_law',
                'title': 'Luật Bảo vệ Quyền lợi Người tiêu dùng - Điều 8',
                'content': '''Người tiêu dùng có quyền được bồi thường thiệt hại khi quyền và lợi ích hợp pháp của mình bị xâm phạm.

Mức bồi thường thiệt hại được xác định theo quy định của pháp luật về dân sự.''',
                'jurisdiction': 'VN',
                'source_url': 'https://thuvienphapluat.vn/van-ban/Thuong-mai/Luat-Bao-ve-quyen-loi-nguoi-tieu-dung-2010-105266.aspx',
                'effective_date': '2010-07-01',
                'version': '2010',
                'category': 'consumer_protection',
                'keywords': json.dumps(['bồi thường', 'thiệt hại', 'người tiêu dùng', 'quyền lợi'])
            },
            {
                'rule_type': 'commercial_law',
                'title': 'Nghị định 52/2013/NĐ-CP - Điều 16: Trách nhiệm của sàn thương mại điện tử',
                'content': '''Sàn giao dịch thương mại điện tử có trách nhiệm:

1. Kiểm tra, xác thực thông tin của thương nhân, tổ chức, cá nhân khi đăng ký tham gia sàn
2. Cung cấp cơ chế để người tiêu dùng được cảnh báo về các giao dịch có dấu hiệu vi phạm
3. Loại bỏ thông tin kinh doanh vi phạm pháp luật khi có yêu cầu của cơ quan có thẩm quyền
4. Cung cấp thông tin về thương nhân khi có yêu cầu của cơ quan chức năng''',
                'jurisdiction': 'VN',
                'source_url': 'https://thuvienphapluat.vn/van-ban/Thuong-mai/Nghi-dinh-52-2013-ND-CP-thuong-mai-dien-tu-191794.aspx',
                'effective_date': '2013-07-16',
                'version': '2013',
                'category': 'platform_responsibility',
                'keywords': json.dumps(['sàn TMĐT', 'trách nhiệm', 'xác thực', 'vi phạm'])
            },
            {
                'rule_type': 'platform',
                'title': 'Quy định hoàn tiền của sàn thương mại điện tử',
                'content': '''Chính sách hoàn tiền tiêu chuẩn:

1. Sản phẩm lỗi do nhà sản xuất: hoàn 100% trong 7 ngày
2. Sản phẩm không đúng mô tả: hoàn 100% trong 7 ngày
3. Giao hàng muộn quá 3 ngày: hoàn 50% phí vận chuyển
4. Người mua thay đổi ý định: không hoàn tiền (trừ khi sản phẩm chưa giao)
5. Tranh chấp phải được giải quyết trong 15 ngày''',
                'jurisdiction': 'VN',
                'effective_date': '2024-01-01',
                'version': '1.0',
                'category': 'refund',
                'keywords': json.dumps(['hoàn tiền', 'hoàn trả', 'lỗi', 'tranh chấp'])
            },
            {
                'rule_type': 'platform',
                'title': 'Quy định về vi phạm và khóa tài khoản',
                'content': '''Sàn có quyền khóa tài khoản người bán trong các trường hợp:

1. Bán hàng giả, hàng nhái: khóa vĩnh viễn
2. Gian lận về giá, đánh giá sản phẩm: khóa 30 ngày (lần 1), vĩnh viễn (lần 2+)
3. Vi phạm chính sách giao hàng: cảnh cáo (lần 1), khóa 7 ngày (lần 2+)
4. Tỷ lệ đơn hàng hủy > 20%: cảnh cáo và giảm thứ hạng
5. Người bán có quyền khiếu nại trong 7 ngày kể từ khi bị khóa''',
                'jurisdiction': 'VN',
                'effective_date': '2024-01-01',
                'version': '1.0',
                'category': 'account_suspension',
                'keywords': json.dumps(['khóa tài khoản', 'vi phạm', 'gian lận', 'hàng giả'])
            },
            {
                'rule_type': 'commercial_law',
                'title': 'Luật Thương mại 2005 - Điều 10: Quyền và nghĩa vụ của thương nhân',
                'content': '''Thương nhân có các quyền và nghĩa vụ sau:

1. Được kinh doanh các ngành nghề không bị cấm
2. Được bảo vệ quyền và lợi ích hợp pháp
3. Thực hiện đúng cam kết với khách hàng
4. Chịu trách nhiệm về chất lượng hàng hóa, dịch vụ
5. Tuân thủ pháp luật về cạnh tranh, bảo vệ người tiêu dùng''',
                'jurisdiction': 'VN',
                'source_url': 'https://thuvienphapluat.vn/van-ban/Thuong-mai/Luat-Thuong-mai-2005-36-2005-QH11-18696.aspx',
                'effective_date': '2006-01-01',
                'version': '2005',
                'category': 'merchant_rights',
                'keywords': json.dumps(['thương nhân', 'quyền', 'nghĩa vụ', 'cam kết'])
            }
        ]

        for rule in sample_rules:
            cursor.execute("""
                INSERT OR IGNORE INTO legal_rules (
                    rule_type, title, content, jurisdiction, source_url,
                    effective_date, version, category, keywords, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule['rule_type'],
                rule['title'],
                rule['content'],
                rule['jurisdiction'],
                rule.get('source_url'),
                rule.get('effective_date'),
                rule.get('version'),
                rule['category'],
                rule['keywords'],
                'system'
            ))

        conn.commit()
        logger.info(f"✅ Seeded {len(sample_rules)} sample legal rules")

    except Exception as e:
        logger.error(f"❌ Error seeding sample rules: {e}")
        conn.rollback()


if __name__ == "__main__":
    """
    Standalone migration script
    Can be run independently: python -m backend.modules.arbitration.database_migration
    """
    import sys
    import os

    # Add parent directory to path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

    from backend.database import get_db_connection

    logging.basicConfig(level=logging.INFO)

    try:
        conn = get_db_connection()
        success = migrate_arbitration_tables(conn)

        if success:
            # Optionally seed sample data
            seed = input("\n🌱 Do you want to seed sample legal rules? (y/n): ")
            if seed.lower() == 'y':
                seed_sample_legal_rules(conn)

        conn.close()

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)
