import subprocess

def cut_complete_event(event, video_buffer, video_length, output_file):
    """Cắt video cho sự kiện hoàn chỉnh (có cả ts và te)."""
    ts = event.get("ts")
    te = event.get("te")
    video_file = event.get("video_file")

    start_time = max(0, ts - video_buffer)  # Thêm buffer trước ts
    end_time = min(te + video_buffer, video_length)  # Thêm buffer sau te
    duration = end_time - start_time

    if duration <= 0:
        print(f"Bỏ qua: Duration không hợp lệ ({duration}s) cho sự kiện {event.get('event_id')}")
        return False

    try:
        cmd = [
            "ffmpeg",
            "-i", video_file,
            "-ss", str(start_time),
            "-t", str(duration),
            "-c:v", "copy",
            "-c:a", "copy",
            "-y",
            output_file
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Đã cắt video: {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Lỗi khi cắt video {video_file}: {e}")
        return False
    except Exception as e:
        print(f"Lỗi không xác định: {e}")
        return False