# AI Arbitration System - UI Flow & User Journey

## 📱 Tổng quan luồng người dùng (User Journey)

```
1. Dashboard → 2. Tạo Case → 3. Upload Chứng Cứ → 4. AI Phân Tích → 5. Xem Kết Quả → 6. Download Vi Bằng → 7. Theo Dõi Case
```

---

## 🎯 User Persona

**Người bán hàng trên sàn TMĐT:**
- Tên: Nguyễn Văn A
- Tuổi: 30-45
- Nghề nghiệp: Chủ shop online
- Vấn đề: Bị sàn khóa tài khoản/không hoàn tiền/vi phạm không rõ lý do
- Mục tiêu: Hiểu được quyền lợi của mình, có căn cứ pháp lý để khiếu nại

---

## 📺 Màn hình 1: Dashboard / Trang Chủ

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ [Logo VPACK]           AI TRỌNG TÀI         [User] [Logout] │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         🏛️ HỆ THỐNG TRỌNG TÀI AI                    │   │
│  │      Giải quyết tranh chấp thương mại khách quan    │   │
│  │                                                       │   │
│  │     [➕ TẠO CASE MỚI]    [📋 XEM CASE CỦA TÔI]      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  📊 THỐNG KÊ CỦA BẠN                                         │
│  ┌──────────┬──────────┬──────────┬──────────┐             │
│  │  Tổng    │  Đang    │  Sàn     │  Sàn     │             │
│  │  Case    │  Xử Lý   │  Đúng    │  Sai     │             │
│  │   12     │    3     │    5     │    4     │             │
│  └──────────┴──────────┴──────────┴──────────┘             │
│                                                               │
│  📝 CASE GẦN ĐÂY                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🔴 ARB-2025-001 | Khóa tài khoản không lý do       │   │
│  │    Shopee • Đang phân tích • 50,000,000 VND        │   │
│  │    [Xem chi tiết →]                                  │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ 🟡 ARB-2025-002 | Không hoàn tiền đúng hạn         │   │
│  │    Lazada • Chờ chứng cứ • 5,000,000 VND           │   │
│  │    [Xem chi tiết →]                                  │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ 🟢 ARB-2025-003 | Sản phẩm bị trả về sai quy định  │   │
│  │    Tiki • Hoàn thành • 3,000,000 VND                │   │
│  │    [Xem chi tiết →]                                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  📚 TÀI NGUYÊN                                               │
│  • Thư viện luật thương mại điện tử                          │
│  • Quy định của các sàn TMĐT                                 │
│  • Hướng dẫn khiếu nại                                       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Chức năng
- **Nút "TẠO CASE MỚI"**: Mở form tạo case
- **"XEM CASE CỦA TÔI"**: Danh sách tất cả case
- **Thống kê**: Overview nhanh
- **Case gần đây**: Click để xem chi tiết
- **Tài nguyên**: Link đến knowledge base

---

## 📺 Màn hình 2: Tạo Case Mới (Wizard 5 Bước)

### Bước 1: Thông tin cơ bản

```
┌─────────────────────────────────────────────────────────────┐
│ ← Quay lại                TẠO CASE MỚI                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  BƯỚC 1/5: THÔNG TIN CƠ BẢN                                 │
│  ●────○────○────○────○                                       │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Tiêu đề case *                                       │   │
│  │ [_____________________________________________]       │   │
│  │ VD: "Sàn khóa tài khoản không lý do"                │   │
│  │                                                       │   │
│  │ Loại tranh chấp *                                    │   │
│  │ [▼ Chọn loại tranh chấp                      ▼]     │   │
│  │   • Khóa tài khoản / Ban                             │   │
│  │   • Không hoàn tiền                                  │   │
│  │   • Thanh toán sai                                   │   │
│  │   • Chất lượng sản phẩm                              │   │
│  │   • Gian lận / Lừa đảo                               │   │
│  │   • Giao hàng / Vận chuyển                           │   │
│  │   • Khác                                              │   │
│  │                                                       │   │
│  │ Mô tả chi tiết *                                     │   │
│  │ [___________________________________________]        │   │
│  │ [                                            ]        │   │
│  │ [                                            ]        │   │
│  │ [                                            ]        │   │
│  │                                                       │   │
│  │ Hãy mô tả chi tiết vấn đề bạn gặp phải:             │   │
│  │ - Điều gì đã xảy ra?                                 │   │
│  │ - Khi nào xảy ra?                                    │   │
│  │ - Bạn đã làm gì?                                     │   │
│  │ - Sàn đã phản hồi như thế nào?                       │   │
│  │                                                       │   │
│  │ Số tiền tranh chấp                                   │   │
│  │ [_______________] VND                                │   │
│  │                                                       │   │
│  │ Ngày xảy ra sự việc                                  │   │
│  │ [📅 __/__/____]                                      │   │
│  │                                                       │   │
│  │ Mức độ ưu tiên                                       │   │
│  │ ○ Thấp  ● Trung bình  ○ Cao  ○ Khẩn cấp            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│                        [Tiếp theo →]                          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Bước 2: Thông tin người khiếu nại

```
┌─────────────────────────────────────────────────────────────┐
│ ← Quay lại                TẠO CASE MỚI                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  BƯỚC 2/5: THÔNG TIN NGƯỜI KHIẾU NẠI                        │
│  ●────●────○────○────○                                       │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Họ và tên *                                          │   │
│  │ [_____________________________________________]       │   │
│  │                                                       │   │
│  │ Số điện thoại                                        │   │
│  │ [_____________________________________________]       │   │
│  │                                                       │   │
│  │ Email                                                │   │
│  │ [_____________________________________________]       │   │
│  │                                                       │   │
│  │ CCCD/CMND (optional - để làm vi bằng)               │   │
│  │ [_____________________________________________]       │   │
│  │                                                       │   │
│  │ ℹ️ Thông tin này được bảo mật và chỉ dùng để:       │   │
│  │   • Lập vi bằng gian lận (nếu sàn sai)              │   │
│  │   • Liên hệ khi cần thông tin bổ sung               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│               [← Quay lại]      [Tiếp theo →]                │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Bước 3: Thông tin bên bị khiếu nại

```
┌─────────────────────────────────────────────────────────────┐
│ ← Quay lại                TẠO CASE MỚI                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  BƯỚC 3/5: THÔNG TIN BÊN BỊ KHIẾU NẠI                       │
│  ●────●────●────○────○                                       │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Loại bên bị khiếu nại *                              │   │
│  │ ● Sàn TMĐT  ○ Người mua  ○ Nhà cung cấp  ○ Khác    │   │
│  │                                                       │   │
│  │ Tên sàn/công ty *                                    │   │
│  │ [▼ Chọn hoặc nhập tên                        ▼]     │   │
│  │   • Shopee                                            │   │
│  │   • Lazada                                            │   │
│  │   • Tiki                                              │   │
│  │   • Sendo                                             │   │
│  │   • TikTok Shop                                       │   │
│  │   • Khác (nhập tên)                                   │   │
│  │                                                       │   │
│  │ Mã số thuế (nếu biết)                                │   │
│  │ [_____________________________________________]       │   │
│  │                                                       │   │
│  │ 📊 Lịch sử vi phạm của sàn này:                      │   │
│  │ ┌─────────────────────────────────────────────┐     │   │
│  │ │ Shopee                                       │     │   │
│  │ │ • Tổng case: 45                              │     │   │
│  │ │ • Sàn sai: 28 (62%)                          │     │   │
│  │ │ • Sàn đúng: 17 (38%)                         │     │   │
│  │ │ • Loại vi phạm phổ biến: Khóa tài khoản     │     │   │
│  │ └─────────────────────────────────────────────┘     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│               [← Quay lại]      [Tiếp theo →]                │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Bước 4: Upload chứng cứ

```
┌─────────────────────────────────────────────────────────────┐
│ ← Quay lại                TẠO CASE MỚI                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  BƯỚC 4/5: UPLOAD CHỨNG CỨ                                  │
│  ●────●────●────●────○                                       │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ℹ️ Chứng cứ càng đầy đủ, AI càng phân tích chính xác │   │
│  │                                                       │   │
│  │ Các loại chứng cứ hữu ích:                           │   │
│  │ • 📹 Video giao dịch, trao đổi                        │   │
│  │ • 📷 Screenshot thông báo từ sàn                      │   │
│  │ • 💬 Chat logs với sàn/người mua                      │   │
│  │ • 📧 Email trao đổi                                   │   │
│  │ • 📄 Hợp đồng, chính sách                             │   │
│  │ • 🧾 Hóa đơn, chứng từ                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │        📤 DRAG & DROP FILE VÀO ĐÂY                   │   │
│  │             hoặc click để chọn file                   │   │
│  │                                                       │   │
│  │  Hỗ trợ: Video (MP4, AVI), Images (JPG, PNG),       │   │
│  │  Documents (PDF, DOCX), Max size: 50MB/file          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  📎 Chứng cứ đã upload (3):                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 📹 video_thong_bao_khoa_tk.mp4              [🗑️]    │   │
│  │    12.5 MB • Uploaded 2 mins ago                     │   │
│  │    Mô tả: Video thông báo khóa tài khoản từ sàn     │   │
│  │    [✏️ Sửa mô tả]                                    │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ 📷 screenshot_chat_support.png              [🗑️]    │   │
│  │    2.3 MB • Uploaded 5 mins ago                      │   │
│  │    Mô tả: Chat với support không giải quyết         │   │
│  │    [✏️ Sửa mô tả]                                    │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ 📧 email_khieu_nai.pdf                      [🗑️]    │   │
│  │    1.1 MB • Uploaded 8 mins ago                      │   │
│  │    Mô tả: Email khiếu nại gửi cho sàn                │   │
│  │    [✏️ Sửa mô tả]                                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  [+ Thêm chứng cứ]                                           │
│                                                               │
│               [← Quay lại]      [Tiếp theo →]                │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Bước 5: Xem lại và xác nhận

```
┌─────────────────────────────────────────────────────────────┐
│ ← Quay lại                TẠO CASE MỚI                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  BƯỚC 5/5: XEM LẠI VÀ XÁC NHẬN                              │
│  ●────●────●────●────●                                       │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ THÔNG TIN CASE                              [✏️ Sửa] │   │
│  │ • Tiêu đề: Sàn khóa tài khoản không lý do            │   │
│  │ • Loại: Khóa tài khoản / Ban                         │   │
│  │ • Số tiền: 50,000,000 VND                            │   │
│  │ • Ngày xảy ra: 15/11/2025                            │   │
│  │ • Ưu tiên: Cao                                        │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ NGƯỜI KHIẾU NẠI                             [✏️ Sửa] │   │
│  │ • Tên: Nguyễn Văn A                                  │   │
│  │ • SĐT: 0912345678                                    │   │
│  │ • Email: nguyenvana@gmail.com                        │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ BÊN BỊ KHIẾU NẠI                            [✏️ Sửa] │   │
│  │ • Loại: Sàn TMĐT                                     │   │
│  │ • Tên: Shopee                                        │   │
│  │ • Lịch sử: 28/45 case sàn sai (62%)                 │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ CHỨNG CỨ                                    [✏️ Sửa] │   │
│  │ • 3 files đã upload                                  │   │
│  │ • Tổng dung lượng: 15.9 MB                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ⚠️ SAU KHI TẠO CASE                                         │
│  • Case sẽ được lưu với số: ARB-2025-XXX                    │
│  • Bạn có thể yêu cầu AI phân tích ngay                      │
│  • Hoặc bổ sung thêm chứng cứ sau                            │
│                                                               │
│  ☑️ Tôi xác nhận thông tin trên là chính xác                │
│                                                               │
│               [← Quay lại]      [✅ TẠO CASE]                │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📺 Màn hình 3: Chi tiết Case (Sau khi tạo)

```
┌─────────────────────────────────────────────────────────────┐
│ ← Danh sách case                                   [Chia sẻ]│
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  🔴 ARB-2025-001                              [⋯ Menu]       │
│  Sàn khóa tài khoản không lý do                              │
│                                                               │
│  Status: 🟡 Mới tạo • Ưu tiên: 🔴 Cao                        │
│  Tạo lúc: 21/11/2025 14:30                                   │
│  Người tạo: nguyenvana@gmail.com                             │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🤖 HÀNH ĐỘNG NHANH                                   │   │
│  │                                                       │   │
│  │  [🔍 PHÂN TÍCH BẰNG AI]  [📝 THÊM CHỨNG CỨ]        │   │
│  │  [💬 THÊM COMMENT]       [📊 XEM THỐNG KÊ]          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  📑 TAB NAVIGATION                                           │
│  [● Tổng quan]  [○ Chứng cứ]  [○ Phân tích AI]             │
│  [○ Comments]   [○ Timeline]   [○ Tài liệu]                 │
│                                                               │
│  ═══════════════════════════════════════════════════════    │
│                                                               │
│  📋 THÔNG TIN CASE                                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Loại tranh chấp:  Khóa tài khoản / Ban               │   │
│  │ Số tiền tranh chấp: 50,000,000 VND                   │   │
│  │ Ngày xảy ra:     15/11/2025                           │   │
│  │ Bên khiếu nại:   Nguyễn Văn A                        │   │
│  │ Bên bị khiếu nại: Shopee (Sàn TMĐT)                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  📝 MÔ TẢ CHI TIẾT                                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Tài khoản bán hàng của tôi trên Shopee bị khóa đột   │   │
│  │ ngột vào ngày 15/11/2025 mà không có thông báo trước.│   │
│  │ Khi liên hệ với support, họ chỉ nói "vi phạm chính   │   │
│  │ sách" nhưng không nói cụ thể vi phạm điều nào. Tôi   │   │
│  │ có 3 đơn hàng lớn đang chờ giao (tổng 50 triệu) và   │   │
│  │ giờ không thể xử lý...                                │   │
│  │                                               [Xem thêm] │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  📎 CHỨNG CỨ (3 files)                                       │
│  • 📹 video_thong_bao_khoa_tk.mp4 (12.5 MB)                 │
│  • 📷 screenshot_chat_support.png (2.3 MB)                   │
│  • 📧 email_khieu_nai.pdf (1.1 MB)                           │
│                                           [Xem tất cả →]     │
│                                                               │
│  💬 COMMENTS GẦN ĐÂY (0)                                     │
│  Chưa có comment nào. [Thêm comment đầu tiên]                │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📺 Màn hình 4: Phân tích AI (Loading)

Click nút **"PHÂN TÍCH BẰNG AI"**:

```
┌─────────────────────────────────────────────────────────────┐
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                       │   │
│  │              🤖 ĐANG PHÂN TÍCH BẰNG AI                │   │
│  │                                                       │   │
│  │                 ⏳ Vui lòng đợi...                    │   │
│  │                                                       │   │
│  │  ●●●○○○  Đang tìm các luật/quy định liên quan...     │   │
│  │                                                       │   │
│  │  Hệ thống đang:                                      │   │
│  │  ✓ Phân tích nội dung case                           │   │
│  │  ✓ Tìm 12 luật/quy định liên quan                    │   │
│  │  ⏳ Gửi đến AI (Claude) để phân tích...              │   │
│  │  ○ Đánh giá chứng cứ                                 │   │
│  │  ○ Tạo phán quyết                                    │   │
│  │                                                       │   │
│  │  Ước tính: ~30-60 giây                               │   │
│  │  Chi phí: ~$0.04                                     │   │
│  │                                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📺 Màn hình 5: Kết quả phân tích AI

### Case 1: Sàn SAI (Platform Wrong)

```
┌─────────────────────────────────────────────────────────────┐
│ ← Quay lại case                                              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  🔴 ARB-2025-001 • Kết quả phân tích AI                      │
│                                                               │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│  ┃                                                       ┃  │
│  ┃        ❌ SÀN SAI / PLATFORM WRONG                    ┃  │
│  ┃                                                       ┃  │
│  ┃     Độ tin cậy: ████████░░ 85%                       ┃  │
│  ┃                                                       ┃  │
│  ┃  Shopee đã vi phạm quy định, bạn có cơ sở khiếu nại ┃  │
│  ┃                                                       ┃  │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│                                                               │
│  📊 PHÂN TÍCH CHI TIẾT                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🔍 LÝ DO PHÂN TÍCH                                   │   │
│  │                                                       │   │
│  │ Sau khi phân tích nội dung case, chứng cứ và các    │   │
│  │ quy định liên quan, AI kết luận:                     │   │
│  │                                                       │   │
│  │ 1. Vi phạm quy trình khóa tài khoản:                │   │
│  │    Theo Nghị định 52/2013 Điều 16, sàn phải thông   │   │
│  │    báo rõ ràng lý do cụ thể khi khóa tài khoản.     │   │
│  │    Shopee chỉ nói "vi phạm chính sách" là quá chung │   │
│  │    chung và không đủ căn cứ pháp lý.                │   │
│  │                                                       │   │
│  │ 2. Không cho quyền khiếu nại:                        │   │
│  │    Luật Thương mại 2005 Điều 10 quy định người bán  │   │
│  │    có quyền được bảo vệ quyền lợi hợp pháp. Việc    │   │
│  │    khóa tài khoản đột ngột mà không cho giải trình  │   │
│  │    là vi phạm quyền này.                             │   │
│  │                                                       │   │
│  │ 3. Gây thiệt hại kinh tế:                            │   │
│  │    3 đơn hàng trị giá 50 triệu không thể giao làm   │   │
│  │    bạn mất cả tiền hàng và uy tín với khách.        │   │
│  │                                                       │   │
│  │ 🎯 KẾT LUẬN: Shopee cần giải trình rõ ràng và bồi   │   │
│  │    thường thiệt hại nếu không có căn cứ chính đáng. │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ⚖️ VI PHẠM CỦA SÀN                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ❗ Vi phạm quy trình thông báo (Nghị định 52/2013)  │   │
│  │ ❗ Hạn chế quyền khiếu nại (Luật TM 2005 Điều 10)    │   │
│  │ ❗ Không giải trình cụ thể lý do khóa                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  📚 LUẬT/QUY ĐỊNH LIÊN QUAN (5)                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. Nghị định 52/2013/NĐ-CP - Điều 16               │   │
│  │    Trách nhiệm sàn TMĐT khi khóa tài khoản          │   │
│  │    [Xem chi tiết]                                    │   │
│  │                                                       │   │
│  │ 2. Luật Thương mại 2005 - Điều 10                   │   │
│  │    Quyền và nghĩa vụ của thương nhân                │   │
│  │    [Xem chi tiết]                                    │   │
│  │                                                       │   │
│  │ 3. Quy định của Shopee về khóa tài khoản            │   │
│  │    [Xem 2 quy định khác...]                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  💰 ĐÁNH GIÁ THIỆT HẠI                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Loại thiệt hại:       Thiệt hại trực tiếp            │   │
│  │ Số tiền ước tính:     50,000,000 VND                 │   │
│  │ Chi tiết:                                             │   │
│  │ • Mất 3 đơn hàng:     50,000,000 VND                 │   │
│  │ • Bồi thường stress:   5,000,000 VND (10%)          │   │
│  │ • Mất uy tín:          Không định lượng             │   │
│  │                       ─────────────────              │   │
│  │ TỔNG YÊU CẦU:         55,000,000 VND                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  🎯 HÀNH ĐỘNG ĐỀ NGHỊ                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ✓ Bước 1: Gửi email yêu cầu giải trình cụ thể       │   │
│  │   (trong 7 ngày theo quy định)                       │   │
│  │                                                       │   │
│  │ ✓ Bước 2: Download vi bằng gian lận (đã tự động tạo)│   │
│  │   để làm căn cứ khiếu nại                            │   │
│  │                                                       │   │
│  │ ✓ Bước 3: Nếu sàn không phản hồi, gửi khiếu nại lên:│   │
│  │   • Sở Công Thương                                   │   │
│  │   • Cục Quản lý Cạnh tranh                           │   │
│  │   • Hội Bảo vệ Quyền lợi Người tiêu dùng            │   │
│  │                                                       │   │
│  │ ✓ Bước 4: Có thể khởi kiện dân sự để đòi bồi thường│   │
│  │                                                       │   │
│  │   [📥 TẢI HƯỚNG DẪN CHI TIẾT]                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  📄 VI BẰNG GIAN LẬN                                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ✅ Đã tự động tạo vi bằng theo mẫu pháp luật VN      │   │
│  │                                                       │   │
│  │ 📋 Biên bản vi phạm thương mại điện tử               │   │
│  │    Số hồ sơ: ARB-2025-001                            │   │
│  │    Định dạng: Markdown / PDF                         │   │
│  │    Bao gồm: Thông tin đầy đủ, chứng cứ, căn cứ pháp │   │
│  │             lý, yêu cầu bồi thường                    │   │
│  │                                                       │   │
│  │    [📥 TẢI VI BẰNG (.md)]  [📥 TẢI VI BẰNG (.pdf)]  │   │
│  │    [📧 GỬI EMAIL]          [🖨️ IN]                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  📊 CHẤT LƯỢNG CHỨNG CỨ                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Mức độ: ⭐⭐⭐⭐☆ Tốt (4/5)                            │   │
│  │                                                       │   │
│  │ ✅ Có video thông báo khóa tài khoản                 │   │
│  │ ✅ Có screenshot chat với support                     │   │
│  │ ✅ Có email khiếu nại                                │   │
│  │ ⚠️ Thiếu: Ảnh chụp màn hình đơn hàng bị ảnh hưởng   │   │
│  │                                                       │   │
│  │ 💡 Gợi ý: Nên bổ sung thêm ảnh chụp các đơn hàng    │   │
│  │    trị giá 50 triệu để tăng sức thuyết phục.        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  [🔄 PHÂN TÍCH LẠI]  [💬 THÊM COMMENT]  [📤 CHIA SẺ]        │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Case 2: Sàn ĐÚNG (Platform Right)

```
┌─────────────────────────────────────────────────────────────┐
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│  ┃                                                       ┃  │
│  ┃        ✅ SÀN ĐÚNG / PLATFORM RIGHT                   ┃  │
│  ┃                                                       ┃  │
│  ┃     Độ tin cậy: ██████████ 92%                       ┃  │
│  ┃                                                       ┃  │
│  ┃  Sàn tuân thủ đúng quy định, khiếu nại không có cơ sở┃  │
│  ┃                                                       ┃  │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│                                                               │
│  📊 PHÂN TÍCH CHI TIẾT                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Sau khi phân tích, AI kết luận sàn đã xử lý đúng:   │   │
│  │                                                       │   │
│  │ 1. Bạn đã vi phạm chính sách giao hàng:              │   │
│  │    - Tỷ lệ hủy đơn: 35% (quy định < 20%)             │   │
│  │    - Giao hàng muộn: 15/20 đơn gần nhất              │   │
│  │                                                       │   │
│  │ 2. Sàn đã thông báo cảnh cáo 2 lần trước:           │   │
│  │    - Email cảnh cáo: 01/11/2025                      │   │
│  │    - Thông báo trong app: 08/11/2025                 │   │
│  │                                                       │   │
│  │ 3. Việc khóa tài khoản tuân theo quy trình:         │   │
│  │    - Đã gửi thông báo trước 7 ngày                   │   │
│  │    - Đúng quy định trong Điều khoản sử dụng         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  🎯 KHUYẾN NGHỊ                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ✓ Chấp nhận quyết định của sàn                       │   │
│  │ ✓ Cải thiện tỷ lệ giao hàng để được mở khóa         │   │
│  │ ✓ Liên hệ support để hỏi về điều kiện khôi phục     │   │
│  │ ✓ Xem xét lại quy trình kinh doanh để tránh vi phạm │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  💡 HỌC HỎI TỪ CASE NÀY                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • Luôn đọc kỹ Điều khoản sử dụng của sàn            │   │
│  │ • Chú ý các email cảnh cáo từ sàn                    │   │
│  │ • Duy trì tỷ lệ giao hàng > 80%                      │   │
│  │ • Không hủy đơn > 20% tổng số đơn                    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Case 3: CHƯA RÕ (Unclear)

```
┌─────────────────────────────────────────────────────────────┐
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│  ┃                                                       ┃  │
│  ┃        ⚠️ CHƯA RÕ RÀNG / UNCLEAR                     ┃  │
│  ┃                                                       ┃  │
│  ┃     Độ tin cậy: ████░░░░░░ 45%                       ┃  │
│  ┃                                                       ┃  │
│  ┃  Cần thêm thông tin hoặc chứng cứ để kết luận        ┃  │
│  ┃                                                       ┃  │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│                                                               │
│  📊 PHÂN TÍCH                                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ AI chưa thể kết luận vì:                             │   │
│  │                                                       │   │
│  │ ❌ Thiếu chứng cứ quan trọng:                        │   │
│  │    - Không có email/thông báo từ sàn                 │   │
│  │    - Không có screenshot trước khi bị khóa           │   │
│  │    - Mô tả chưa đủ chi tiết                          │   │
│  │                                                       │   │
│  │ ⚠️ Thông tin mâu thuẫn:                              │   │
│  │    - Bạn nói "không vi phạm gì" nhưng sàn nói       │   │
│  │      "vi phạm giao hàng"                             │   │
│  │    - Cần xác minh ai đúng                            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  📋 CẦN BỔ SUNG                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. ⭐ Email thông báo từ sàn (nếu có)                │   │
│  │    → Upload file email hoặc screenshot               │   │
│  │                                                       │   │
│  │ 2. ⭐ Lịch sử giao dịch 30 ngày trước                │   │
│  │    → Screenshot từ dashboard bán hàng                │   │
│  │                                                       │   │
│  │ 3. ⭐ Điều khoản sử dụng của sàn                     │   │
│  │    → Link hoặc screenshot phần liên quan             │   │
│  │                                                       │   │
│  │ 4. Chat logs với support (nếu có)                    │   │
│  │                                                       │   │
│  │    [📤 UPLOAD THÊM CHỨNG CỨ]                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  🔄 SAU KHI BỔ SUNG                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Bạn có thể yêu cầu AI phân tích lại để nhận được    │   │
│  │ kết luận rõ ràng hơn.                                │   │
│  │                                                       │   │
│  │    [🔄 PHÂN TÍCH LẠI SAU KHI CÓ THÊM CHỨNG CỨ]      │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📺 Màn hình 6: Danh sách Case

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo] AI TRỌNG TÀI                     [User] [Logout]    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  DANH SÁCH CASE CỦA TÔI                    [+ Tạo case mới] │
│                                                               │
│  🔍 [Tìm kiếm case...                           ] [🔍]       │
│                                                               │
│  Lọc: [▼ Tất cả trạng thái] [▼ Tất cả loại] [▼ Tất cả sàn] │
│  Sắp xếp: [▼ Mới nhất]                                      │
│                                                               │
│  ═══════════════════════════════════════════════════════    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🔴 ARB-2025-001                    🟡 Đang phân tích │   │
│  │ Khóa tài khoản không lý do                           │   │
│  │ Shopee • 50,000,000 VND • 21/11/2025                 │   │
│  │ [Xem →]  [🤖 Phân tích]  [💬 2]  [📎 3]             │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ 🟡 ARB-2025-002                        ⭐ Cao       │   │
│  │ Không hoàn tiền đúng hạn                             │   │
│  │ Lazada • 5,000,000 VND • 20/11/2025                  │   │
│  │ [Xem →]  [📤 Upload]  [💬 0]  [📎 1]                │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ 🟢 ARB-2025-003                    ✅ Sàn sai (85%)  │   │
│  │ Sản phẩm bị trả về sai quy định                      │   │
│  │ Tiki • 3,000,000 VND • 19/11/2025                    │   │
│  │ [Xem →]  [📥 Vi bằng]  [💬 5]  [📎 4]               │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ 🟢 ARB-2025-004                    ✅ Sàn đúng (92%) │   │
│  │ Tài khoản bị cảnh cáo                                │   │
│  │ Shopee • 0 VND • 18/11/2025                          │   │
│  │ [Xem →]  [💬 1]  [📎 2]                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  Hiển thị 1-4 trong tổng 12 case     [1] [2] [3] [→]       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📺 Màn hình 7: Thống kê & Báo cáo

```
┌─────────────────────────────────────────────────────────────┐
│  THỐNG KÊ & BÁO CÁO                                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  📊 TỔNG QUAN                                                │
│  ┌──────────┬──────────┬──────────┬──────────┐             │
│  │  Tổng    │  Sàn     │  Sàn     │  Tổng    │             │
│  │  Case    │  Sai     │  Đúng    │  Thiệt Hại│             │
│  │   12     │   7      │   5      │  200M    │             │
│  │         │  58%     │  42%     │   VND    │             │
│  └──────────┴──────────┴──────────┴──────────┘             │
│                                                               │
│  📈 BIỂU ĐỒ THEO THỜI GIAN                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Case/tháng                                          │   │
│  │   10│         ┌─┐                                    │   │
│  │    8│    ┌─┐ │ │                                     │   │
│  │    6│    │ │ │ │ ┌─┐                                │   │
│  │    4│ ┌─┐│ │ │ │ │ │                                │   │
│  │    2│ │ ││ │ │ │ │ │                                │   │
│  │    0└─┴─┴┴─┴─┴─┴─┴─┴─                              │   │
│  │     T8 T9 T10T11T12 1  2                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  🏪 THỐNG KÊ THEO SÀN                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Shopee                                               │   │
│  │ • Case: 6 • Sàn sai: 4 (67%) • Thiệt hại: 120M     │   │
│  │ ████████████████████████████████░░░░ 67%             │   │
│  │ [Xem chi tiết]                                       │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ Lazada                                               │   │
│  │ • Case: 3 • Sàn sai: 2 (67%) • Thiệt hại: 50M      │   │
│  │ ████████████████████████████████░░░░ 67%             │   │
│  │ [Xem chi tiết]                                       │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ Tiki                                                 │   │
│  │ • Case: 3 • Sàn sai: 1 (33%) • Thiệt hại: 30M      │   │
│  │ ████████████░░░░░░░░░░░░░░░░░░░░░░░░ 33%             │   │
│  │ [Xem chi tiết]                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  🚨 VI PHẠM PHỔ BIẾN                                         │
│  1. Khóa tài khoản không lý do rõ ràng: 40%                 │
│  2. Không hoàn tiền đúng hạn: 25%                           │
│  3. Xử lý khiếu nại chậm: 20%                                │
│  4. Sai chính sách giao hàng: 15%                            │
│                                                               │
│  [📊 XEM BÁO CÁO ĐẦY ĐỦ]  [📤 XUẤT EXCEL]  [📧 GỬI EMAIL]  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📺 Màn hình 8: Thư viện Luật (Knowledge Base)

```
┌─────────────────────────────────────────────────────────────┐
│  THƯ VIỆN LUẬT & QUY ĐỊNH                   [+ Thêm luật mới]│
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  🔍 [Tìm kiếm luật, quy định...                    ] [🔍]   │
│                                                               │
│  Lọc: [▼ Tất cả loại] [▼ Vietnam] [▼ Tất cả category]      │
│                                                               │
│  ═══════════════════════════════════════════════════════    │
│                                                               │
│  📚 LUẬT THƯƠNG MẠI VIỆT NAM                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 📜 Luật Bảo vệ Quyền lợi Người tiêu dùng 2010       │   │
│  │    Điều 8: Quyền được bồi thường thiệt hại           │   │
│  │    Category: Consumer Protection • VN                │   │
│  │    [Xem chi tiết →]                                   │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ 📜 Nghị định 52/2013/NĐ-CP về TMĐT                   │   │
│  │    Điều 16: Trách nhiệm của sàn giao dịch TMĐT       │   │
│  │    Category: Platform Responsibility • VN             │   │
│  │    [Xem chi tiết →]                                   │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ 📜 Luật Thương mại 2005 - Điều 10                    │   │
│  │    Quyền và nghĩa vụ của thương nhân                 │   │
│  │    Category: Merchant Rights • VN                     │   │
│  │    [Xem chi tiết →]                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  📋 QUY ĐỊNH CỦA SÀN                                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 📄 Shopee - Quy định hoàn tiền                       │   │
│  │    Chính sách hoàn tiền tiêu chuẩn                   │   │
│  │    Category: Refund • Platform                        │   │
│  │    [Xem chi tiết →]                                   │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ 📄 Shopee - Quy định khóa tài khoản                  │   │
│  │    Các trường hợp bị khóa và quy trình               │   │
│  │    Category: Account Suspension • Platform            │   │
│  │    [Xem chi tiết →]                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  Hiển thị 1-5 trong tổng 47 luật/quy định  [1] [2] [→]     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎨 Color Scheme & Design System

### Colors
```
Primary (Blue):      #3B82F6
Success (Green):     #10B981
Danger (Red):        #EF4444
Warning (Yellow):    #F59E0B
Neutral (Gray):      #6B7280

Background:          #F9FAFB
Card Background:     #FFFFFF
Border:              #E5E7EB
Text Primary:        #111827
Text Secondary:      #6B7280
```

### Typography
```
Heading 1:  32px, Bold
Heading 2:  24px, SemiBold
Heading 3:  18px, SemiBold
Body:       16px, Regular
Small:      14px, Regular
Tiny:       12px, Regular
```

### Components
- **Button Primary**: Blue background, white text
- **Button Secondary**: White background, blue border
- **Button Danger**: Red background, white text
- **Card**: White background, subtle shadow, rounded corners
- **Badge**: Small colored pill (status indicators)
- **Progress Bar**: Colored bar with percentage
- **Tab Navigation**: Underline active tab

---

## 📱 Responsive Design

### Desktop (>1024px)
- Sidebar navigation (left)
- 2-column layouts
- Full-width tables

### Tablet (768px - 1024px)
- Collapsible sidebar
- 1-2 column layouts
- Scrollable tables

### Mobile (<768px)
- Bottom navigation
- Single column
- Stack all sections
- Simplified wizard (full screen per step)

---

## 🎭 Interactive Elements

### Animations
- **Loading**: Spinner with "Đang phân tích..." text
- **Success**: Checkmark animation when case created
- **Verdict reveal**: Fade in + scale up animation
- **File upload**: Progress bar

### Tooltips
- Hover over icons for explanations
- "?" icon for help text
- Inline help for complex forms

### Notifications
- Toast notifications (top-right)
- Success, Error, Warning, Info types
- Auto-dismiss after 5 seconds

---

## 💡 Key UX Principles

1. **Progressive Disclosure**: Show basic info first, details on demand
2. **Clear Feedback**: Always show loading states and results
3. **Error Prevention**: Validation before submission
4. **Undo/Edit**: Allow editing before final submission
5. **Help & Guidance**: Inline help text, examples, tooltips
6. **Visual Hierarchy**: Use size, color, spacing to guide attention
7. **Consistency**: Same patterns across all screens

---

**Version**: 1.0
**Last Updated**: 2025-11-21
**Status**: Design Specification
