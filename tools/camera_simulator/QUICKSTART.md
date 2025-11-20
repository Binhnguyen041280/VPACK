# 🚀 Quick Start Guide

Hướng dẫn nhanh để bắt đầu sử dụng Camera Simulator trong 5 phút.

## Bước 1: Chuẩn bị video nguồn

Đặt ít nhất 1 file video vào thư mục `source_videos/`:

```bash
cd tools/camera_simulator

# Tạo thư mục nếu chưa có
mkdir -p source_videos

# Copy video mẫu của bạn vào đây
# Ví dụ:
cp /path/to/your/video.mp4 source_videos/test.mp4
```

Hoặc nếu chưa có video, tạo một video test đơn giản bằng FFmpeg:

```bash
# Tạo video test 30 giây (màn hình đen với text)
ffmpeg -f lavfi -i testsrc=duration=30:size=1280x720:rate=30 \
       -pix_fmt yuv420p source_videos/test.mp4
```

## Bước 2: Tạo config file

Có 2 cách:

### Cách 1: Dùng quick test config (khuyến nghị)

```bash
# File quick_test.yaml đã có sẵn, chỉ cần chỉnh source_video
```

Mở `quick_test.yaml` và đảm bảo `source_video` đúng:

```yaml
cameras:
  - name: "TestCam1"
    source_video: "source_videos/test.mp4"  # ← Đảm bảo file này tồn tại
```

### Cách 2: Tạo config từ example

```bash
cp config.example.yaml config.yaml
# Chỉnh sửa config.yaml theo nhu cầu
```

## Bước 3: Cài đặt dependencies

```bash
# Nếu chưa cài PyYAML
pip install pyyaml
```

## Bước 4: Chạy simulator!

```bash
# Quick test (30 phút, 2 cameras, fast mode)
python simulator.py -c quick_test.yaml

# Hoặc với config tùy chỉnh
python simulator.py -c config.yaml

# Với debug logging
python simulator.py -c quick_test.yaml -v
```

## Bước 5: Kiểm tra kết quả

```bash
# Xem video đã tạo
ls -lh output/TestCam1/
ls -lh output/TestCam2/

# Xem metadata của video
ffprobe output/TestCam1/*.mp4
```

---

## 📝 Ví dụ Output

Khi chạy, bạn sẽ thấy:

```
2025-11-20 10:00:00 [INFO] Loaded configuration from quick_test.yaml
2025-11-20 10:00:00 [INFO] Setting up cameras...
2025-11-20 10:00:00 [INFO] FFmpeg is available
2025-11-20 10:00:00 [INFO] Camera 'TestCam1' initialized: source=source_videos/test.mp4 (30.0s), output=output/TestCam1, pattern=continuous
2025-11-20 10:00:00 [INFO] Camera 'TestCam2' initialized: source=source_videos/test.mp4 (30.0s), output=output/TestCam2, pattern=motion_triggered
2025-11-20 10:00:00 [INFO] ✓ Setup camera: TestCam1
2025-11-20 10:00:00 [INFO] ✓ Setup camera: TestCam2
2025-11-20 10:00:00 [INFO] Setup complete: 2 cameras ready
2025-11-20 10:00:00 [INFO] Starting simulation: start_time=2025-11-20 10:00:00, duration=0.5h
2025-11-20 10:00:00 [INFO] [TestCam1] Generating schedule: start=2025-11-20 10:00:00, duration=0.5h
2025-11-20 10:00:00 [INFO] Generating CONTINUOUS pattern: 2-3m videos
2025-11-20 10:00:00 [INFO] [TestCam1] Schedule generated: 12 events, 12 recordings, 30.5 minutes of video
...
2025-11-20 10:00:05 [INFO] [TestCam1] Creating video: TestCam1_20251120_100000.mp4 (2.5m)
2025-11-20 10:00:06 [INFO] [TestCam1] ✓ Created: TestCam1_20251120_100000.mp4 (total: 1 videos)
...
```

---

## ⚙️ Tùy chỉnh nhanh

### Thay đổi số lượng video tạo ra

Chỉnh `run_duration_hours` trong config:

```yaml
simulator:
  run_duration_hours: 1  # 1 giờ
```

### Thay đổi thời lượng video

Chỉnh `video_duration_range`:

```yaml
config:
  video_duration_range: [5, 10]  # Video 5-10 phút
```

### Thêm camera mới

Copy một camera config và đổi tên:

```yaml
cameras:
  - name: "Camera3"
    source_video: "source_videos/video3.mp4"
    output_folder: "output/Camera3"
    pattern: "continuous"
    config:
      video_duration_range: [15, 15]
      schedule: "24x7"
      use_real_time: false
```

### Chạy trong giờ làm việc

```yaml
config:
  schedule: "working_hours"
  working_hours_start: 8   # 8 AM
  working_hours_end: 18    # 6 PM
  working_days: [0, 1, 2, 3, 4]  # Mon-Fri
```

---

## 🔧 Troubleshooting

### Lỗi: Source video not found

```bash
# Kiểm tra file tồn tại
ls -la source_videos/

# Nếu không có, tạo video test
ffmpeg -f lavfi -i testsrc=duration=30:size=1280x720:rate=30 \
       -pix_fmt yuv420p source_videos/test.mp4
```

### Lỗi: FFmpeg not found

```bash
# Kiểm tra FFmpeg
ffmpeg -version

# Nếu không có, cài đặt
apt-get install ffmpeg  # Ubuntu/Debian
brew install ffmpeg     # macOS
```

### Simulator chạy nhưng không tạo video

- Kiểm tra `use_real_time: false` (để chạy nhanh)
- Kiểm tra `schedule` có phù hợp không (dùng "24x7" để chắc chắn)
- Kiểm tra logs có lỗi không

---

## 🎯 Các Scenarios Phổ Biến

### Scenario 1: Test batch processing với nhiều file

```yaml
simulator:
  run_duration_hours: 2  # 2 giờ

cameras:
  - name: "Cam1"
    source_video: "source_videos/video.mp4"
    output_folder: "output/Cam1"
    pattern: "continuous"
    config:
      video_duration_range: [5, 5]  # Mỗi video 5 phút → ~24 videos/2h
      schedule: "24x7"
      use_real_time: false
```

Kết quả: ~24 videos trong vài phút (fast mode).

### Scenario 2: Test với nhiều cameras

```yaml
cameras:
  - name: "Cam1"
    # ...
  - name: "Cam2"
    # ...
  - name: "Cam3"
    # ...
  - name: "Cam4"
    # ...
  - name: "Cam5"
    # ...
```

Mỗi camera có thể dùng cùng source video hoặc khác nhau.

### Scenario 3: Test real-time processing

```yaml
config:
  use_real_time: true  # Chế độ real-time
  video_duration_range: [15, 15]  # Mỗi 15 phút
```

Chạy overnight để test 24/7 processing.

---

## 📚 Xem thêm

- [README.md](README.md) - Tài liệu đầy đủ
- [config.example.yaml](config.example.yaml) - Tất cả config options

---

**Ready? Let's simulate! 🎬**

```bash
python simulator.py -c quick_test.yaml
```
