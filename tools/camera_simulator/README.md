# 📹 Camera Simulator

Công cụ mô phỏng camera phát sinh video liên tục để test ứng dụng xử lý video trong điều kiện thực tế.

## 🎯 Mục đích

Trong quá trình phát triển, bạn chỉ có vài file video mẫu để test → batch xử lý nhanh xong. Nhưng trong thực tế:
- Camera hoạt động **24/7** liên tục
- Có **nhiều camera** đồng thời
- Camera có thể **bật/tắt** không đều
- Thời lượng video **thay đổi** (10 phút, 20 phút, ...)
- Camera chỉ ghi khi **có chuyển động/sự kiện**

**Camera Simulator** giúp bạn:
- ✅ Mô phỏng camera phát sinh video liên tục
- ✅ Test khả năng xử lý real-time của ứng dụng
- ✅ Đánh giá hiệu năng với nhiều camera
- ✅ Kiểm tra batch scheduler trong điều kiện thực tế
- ✅ Metadata timestamp chính xác (thời gian thực)

---

## 🏗️ Kiến trúc

```
┌─────────────────────────────────────────┐
│      SIMULATOR ORCHESTRATOR             │
│   (Quản lý nhiều cameras)               │
└────────────┬────────────────────────────┘
             │
    ┌────────┴────────┬──────────┐
    ▼                 ▼          ▼
[Camera 1]      [Camera 2]   [Camera N]
    │                │           │
    ▼                ▼           ▼
[Pattern]       [Pattern]   [Pattern]
    │                │           │
    ▼                ▼           ▼
Video Files     Video Files  Video Files
```

### Recording Patterns

1. **CONTINUOUS** - Liên tục (camera an ninh)
   - Tạo video định kỳ (ví dụ: mỗi 15 phút)
   - Không có khoảng idle

2. **MOTION_TRIGGERED** - Khi có chuyển động
   - Idle: 10-30 phút (không có video)
   - Recording: 5-20 phút (có video)

3. **EVENT_TRIGGERED** - Khi có sự kiện
   - Idle: 20-60 phút
   - Recording: 3-10 phút (ngắn hơn)

4. **RANDOM_ON_OFF** - Bật/tắt ngẫu nhiên
   - Online: 2-8 giờ (ghi video liên tục)
   - Offline: 1-4 giờ (không có video)

---

## 📦 Cài đặt

### Yêu cầu

- Python 3.7+
- FFmpeg (đã cài sẵn trong Docker container)
- PyYAML

### Cài đặt dependencies

```bash
pip install pyyaml
```

Hoặc nếu dùng requirements.txt:
```bash
pip install -r requirements.txt
```

---

## 🚀 Sử dụng

### 1. Chuẩn bị video nguồn

Đặt video mẫu vào thư mục `source_videos/`:

```bash
tools/camera_simulator/
├── source_videos/
│   ├── packing_line.mp4    # Video cho camera 1
│   ├── shipping.mp4        # Video cho camera 2
│   └── quality_check.mp4   # Video cho camera 3
```

### 2. Tạo file config

Copy từ example:
```bash
cd tools/camera_simulator
cp config.example.yaml config.yaml
```

Chỉnh sửa `config.yaml`:

```yaml
simulator:
  run_duration_hours: 24    # Chạy 24 giờ
  status_interval_seconds: 60
  cleanup_old_files: true
  retention_count: 100

cameras:
  - name: "PackingLine1"
    source_video: "source_videos/packing_line.mp4"
    output_folder: "output/PackingLine1"
    pattern: "continuous"
    config:
      video_duration_range: [15, 15]  # Video 15 phút
      schedule: "working_hours"
      use_real_time: false  # false = tạo nhanh, true = real-time
```

### 3. Chạy simulator

**Chạy cơ bản:**
```bash
python simulator.py
```

**Chạy với config tùy chỉnh:**
```bash
python simulator.py -c my_config.yaml
```

**Chạy từ thời điểm cụ thể:**
```bash
python simulator.py --start-time "2025-11-20 08:00:00"
```

**Enable debug logging:**
```bash
python simulator.py -v
```

**Cleanup files cũ trước khi chạy:**
```bash
python simulator.py --cleanup
```

### 4. Xem kết quả

Video sẽ được tạo trong thư mục output:

```
output/
├── PackingLine1/
│   ├── PackingLine1_20251120_080000.mp4
│   ├── PackingLine1_20251120_081500.mp4
│   └── ...
├── ShippingDock/
│   ├── ShippingDock_20251120_080500.mp4
│   └── ...
```

---

## ⚙️ Configuration Chi tiết

### Simulator Settings

```yaml
simulator:
  # Thời gian chạy (giờ). 0 = vô hạn
  run_duration_hours: 24

  # Hiển thị status mỗi X giây
  status_interval_seconds: 60

  # Tự động xóa file cũ
  cleanup_old_files: true

  # Giữ lại N files mới nhất
  retention_count: 100
```

### Camera Settings

```yaml
cameras:
  - name: "CameraName"           # Tên camera (dùng trong filename)
    source_video: "path/to/video.mp4"  # Video nguồn
    output_folder: "output/CameraName"  # Thư mục output
    pattern: "continuous"        # Pattern type
    config:
      # ... pattern-specific config
```

### Pattern: CONTINUOUS

```yaml
pattern: "continuous"
config:
  video_duration_range: [15, 15]  # [min, max] phút
  schedule: "working_hours"       # 24x7 / working_hours / custom
  working_hours_start: 8          # 8:00 AM
  working_hours_end: 18           # 6:00 PM
  working_days: [0, 1, 2, 3, 4]   # 0=Mon, 6=Sun
  use_real_time: false
```

### Pattern: MOTION_TRIGGERED

```yaml
pattern: "motion_triggered"
config:
  video_duration_range: [5, 20]   # Khi có motion: 5-20 phút
  idle_duration_range: [10, 30]   # Khi idle: 10-30 phút
  schedule: "24x7"
  use_real_time: false
```

### Pattern: EVENT_TRIGGERED

```yaml
pattern: "event_triggered"
config:
  video_duration_range: [3, 10]   # Event ngắn: 3-10 phút
  idle_duration_range: [20, 60]   # Idle dài: 20-60 phút
  schedule: "working_hours"
  use_real_time: false
```

### Pattern: RANDOM_ON_OFF

```yaml
pattern: "random_on_off"
config:
  video_duration_range: [10, 20]       # Video khi online
  online_duration_range: [2, 8]        # Online 2-8 giờ
  offline_duration_range: [1, 4]       # Offline 1-4 giờ
  schedule: "24x7"
  use_real_time: false
```

### Schedule Types

- **`24x7`**: Luôn hoạt động
- **`working_hours`**: Chỉ trong giờ làm việc (config working_hours_*)
- **`custom`**: Tùy chỉnh (dùng custom_hours)

```yaml
schedule: "custom"
custom_hours: [[8, 12], [13, 18]]  # 8-12h và 13-18h
```

---

## 🎮 Use Cases

### Use Case 1: Test Continuous Processing (24/7)

Mô phỏng 3 camera chạy liên tục:

```yaml
cameras:
  - name: "Cam1"
    source_video: "source_videos/video.mp4"
    output_folder: "output/Cam1"
    pattern: "continuous"
    config:
      video_duration_range: [15, 15]
      schedule: "24x7"
      use_real_time: false

  - name: "Cam2"
    source_video: "source_videos/video.mp4"
    output_folder: "output/Cam2"
    pattern: "continuous"
    config:
      video_duration_range: [20, 20]
      schedule: "24x7"
      use_real_time: false

  - name: "Cam3"
    source_video: "source_videos/video.mp4"
    output_folder: "output/Cam3"
    pattern: "continuous"
    config:
      video_duration_range: [10, 10]
      schedule: "24x7"
      use_real_time: false
```

**Chạy:**
```bash
python simulator.py
```

Simulator sẽ tạo video liên tục cho 3 cameras (Cam1: 15m, Cam2: 20m, Cam3: 10m).

---

### Use Case 2: Test Motion Detection Scenario

Mô phỏng camera chỉ ghi khi có chuyển động:

```yaml
cameras:
  - name: "MotionCam"
    source_video: "source_videos/video.mp4"
    output_folder: "output/MotionCam"
    pattern: "motion_triggered"
    config:
      video_duration_range: [5, 20]   # Recording 5-20 phút
      idle_duration_range: [10, 30]   # Idle 10-30 phút
      schedule: "24x7"
      use_real_time: false
```

---

### Use Case 3: Test Working Hours Only

Mô phỏng camera chỉ hoạt động trong giờ làm việc:

```yaml
cameras:
  - name: "WorkCam"
    source_video: "source_videos/video.mp4"
    output_folder: "output/WorkCam"
    pattern: "continuous"
    config:
      video_duration_range: [15, 15]
      schedule: "working_hours"
      working_hours_start: 8   # 8 AM
      working_hours_end: 18    # 6 PM
      working_days: [0, 1, 2, 3, 4]  # Mon-Fri
      use_real_time: false
```

---

### Use Case 4: Test Unreliable Camera

Mô phỏng camera bật/tắt không đều:

```yaml
cameras:
  - name: "UnreliableCam"
    source_video: "source_videos/video.mp4"
    output_folder: "output/UnreliableCam"
    pattern: "random_on_off"
    config:
      video_duration_range: [10, 20]
      online_duration_range: [1, 4]    # Online 1-4 giờ
      offline_duration_range: [0.5, 2] # Offline 0.5-2 giờ
      schedule: "24x7"
      use_real_time: false
```

---

## 🔍 Monitoring

Trong khi chạy, simulator sẽ hiển thị status định kỳ:

```
2025-11-20 10:15:00 [INFO] ================================================================================
2025-11-20 10:15:00 [INFO] CAMERA STATUS:
2025-11-20 10:15:00 [INFO]   PackingLine1         | Status: Recording (12/48)       | Videos:  12 | Errors:  0 | Duration: 180.0m
2025-11-20 10:15:00 [INFO]   ShippingDock         | Status: Idle (8/35)             | Videos:   8 | Errors:  0 | Duration: 95.3m
2025-11-20 10:15:00 [INFO]   QualityCheck         | Status: Recording (5/20)        | Videos:   5 | Errors:  0 | Duration: 38.7m
2025-11-20 10:15:00 [INFO] TOTAL: 25 videos, 0 errors
2025-11-20 10:15:00 [INFO] ================================================================================
```

---

## 🛠️ Troubleshooting

### FFmpeg not found

**Lỗi:** `RuntimeError: FFmpeg not found or not working`

**Giải pháp:**
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows: Download từ https://ffmpeg.org/download.html
```

### Source video not found

**Lỗi:** `FileNotFoundError: Source video not found: ...`

**Giải pháp:**
- Kiểm tra đường dẫn trong config.yaml
- Đảm bảo file tồn tại trong `source_videos/`

### Permission denied

**Lỗi:** `PermissionError: [Errno 13] Permission denied: ...`

**Giải pháp:**
```bash
chmod +x simulator.py
chmod -R 755 output/
```

---

## 📊 Performance Tips

### Fast Mode (Generate nhanh)

```yaml
config:
  use_real_time: false  # Tạo video ngay lập tức
```

Dùng khi muốn:
- Tạo nhiều video nhanh để test batch processing
- Test với dataset lớn

### Real-Time Mode (Mô phỏng thực tế)

```yaml
config:
  use_real_time: true  # Chờ đúng thời gian thực
```

Dùng khi muốn:
- Test file watcher (scan mỗi 60s)
- Mô phỏng chính xác production
- Test real-time processing pipeline

---

## 🧪 Testing Workflow

### Bước 1: Quick Test (Fast Mode)

Tạo config đơn giản với 1 camera:

```yaml
simulator:
  run_duration_hours: 1  # Chỉ 1 giờ

cameras:
  - name: "TestCam"
    source_video: "source_videos/test.mp4"
    output_folder: "output/TestCam"
    pattern: "continuous"
    config:
      video_duration_range: [5, 5]
      schedule: "24x7"
      use_real_time: false
```

Chạy:
```bash
python simulator.py -c test_config.yaml
```

Sẽ tạo ~12 videos trong vài phút.

### Bước 2: Multi-Camera Test

Thêm nhiều cameras:

```yaml
cameras:
  - name: "Cam1"
    # ...
  - name: "Cam2"
    # ...
  - name: "Cam3"
    # ...
```

### Bước 3: Long-Running Test (Real-Time)

```yaml
simulator:
  run_duration_hours: 24  # 24 giờ

cameras:
  - name: "LongCam"
    config:
      use_real_time: true  # Real-time mode
```

---

## 📁 File Structure

```
tools/camera_simulator/
├── simulator.py           # Main orchestrator
├── camera.py             # Single camera simulator
├── patterns.py           # Recording patterns
├── video_generator.py    # FFmpeg wrapper
├── config.yaml           # Your config (gitignored)
├── config.example.yaml   # Example config
├── README.md             # This file
├── source_videos/        # Put your source videos here
│   ├── video1.mp4
│   └── video2.mp4
└── output/               # Generated videos (gitignored)
    ├── Camera1/
    ├── Camera2/
    └── Camera3/
```

---

## 🎓 Advanced Usage

### Custom Pattern Development

Bạn có thể tự tạo pattern mới trong `patterns.py`:

```python
class MyCustomPattern(RecordingPattern):
    def generate_events(self, start_time, duration_hours):
        # Your custom logic
        events = []
        # ...
        return events
```

### Integration với VPACK

Để integrate với VPACK backend:

1. Set output_folder trùng với input folder của VPACK:

```yaml
cameras:
  - name: "PackingLine1"
    output_folder: "/path/to/VPACK/input/PackingLine1"
```

2. Chạy simulator song song với VPACK backend
3. File watcher của VPACK sẽ tự động phát hiện video mới

---

## 📝 Notes

- Video metadata (creation_time) được set chính xác theo timestamp
- File system timestamps cũng được set phù hợp
- Simulator hỗ trợ graceful shutdown (Ctrl+C)
- Logs chi tiết giúp debug
- Thread-safe (có thể chạy nhiều cameras đồng thời)

---

## 🤝 Contributing

Nếu bạn muốn thêm features:
1. Thêm pattern mới trong `patterns.py`
2. Update `config.example.yaml` với ví dụ
3. Update README.md

---

## 📄 License

Internal tool for VPACK development.

---

**Happy Simulating! 🎬**
