import os
import subprocess
from .cutter_utils import generate_merged_filename, generate_output_filename

def cut_incomplete_event(event, video_buffer, video_length, output_file):
    """Cắt video cho sự kiện dở dang (thiếu ts hoặc te)."""
    ts = event.get("ts")
    te = event.get("te")
    video_file = event.get("video_file")

    # Log độ dài video gốc
    print(f"Video gốc {video_file} có độ dài: {video_length} giây")

    # Log giá trị video_buffer
    print(f"Sử dụng video_buffer: {video_buffer} giây")

    if ts is not None and te is None:  # Chỉ có ts
        start_time = max(0, ts - video_buffer)
        duration = video_length - start_time
    elif ts is None and te is not None:  # Chỉ có te
        start_time = 0
        duration = min(te + video_buffer, video_length)
    else:
        print(f"Bỏ qua: Sự kiện {event.get('event_id')} không có ts hoặc te")
        return False

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

        # Log độ dài của file dở dang vừa tạo
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", output_file],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        duration = float(probe.stdout.strip())
        print(f"File dở dang {output_file} có độ dài: {duration} giây")

        event["cut_video_file"] = output_file
        return True
    except subprocess.CalledProcessError as e:
        print(f"Lỗi khi cắt video {video_file}: {e}")
        return False
    except Exception as e:
        print(f"Lỗi không xác định: {e}")
        return False

def merge_incomplete_events(event_a, event_b, video_buffer, video_length_a, video_length_b, output_dir, max_packing_time, brand_name="Alan"):
    """Ghép nối hai sự kiện dở dang (A có ts, B có te) và tạo file ghép với tên tối ưu."""
    video_file_a = event_a.get("video_file")
    video_file_b = event_b.get("video_file")

    # Kiểm tra nếu file đã được cắt sẵn
    temp_file_a = event_a.get("cut_video_file")
    temp_file_b = event_b.get("cut_video_file")
    files_to_cleanup = []

    # Tạo thư mục temp_clips để lưu file tạm
    temp_clips_dir = os.path.join(os.path.dirname(output_dir), "temp_clips")
    if not os.path.exists(temp_clips_dir):
        os.makedirs(temp_clips_dir)

    # Nếu không có file cắt sẵn, cắt ngay lập tức và lưu vào temp_clips_dir
    if not temp_file_a or not os.path.exists(temp_file_a):
        temp_file_a = os.path.join(temp_clips_dir, f"temp_a_{event_a.get('event_id')}_incomplete.mp4")
        if not cut_incomplete_event(event_a, video_buffer, video_length_a, temp_file_a):
            print(f"Lỗi: Không thể cắt file tạm cho sự kiện {event_a.get('event_id')}")
            return None
    if not temp_file_b or not os.path.exists(temp_file_b):
        temp_file_b = os.path.join(temp_clips_dir, f"temp_b_{event_b.get('event_id')}_incomplete.mp4")
        if not cut_incomplete_event(event_b, video_buffer, video_length_b, temp_file_b):
            print(f"Lỗi: Không thể cắt file tạm cho sự kiện {event_b.get('event_id')}")
            return None

    # Tạo tên file đầu ra tối ưu dựa trên temp_file_a và temp_file_b
    file_name_a = os.path.basename(temp_file_a)
    file_name_b = os.path.basename(temp_file_b)
    parts_a = file_name_a.split("_")
    parts_b = file_name_b.split("_")

    # Lấy Brand từ file đầu tiên
    brand_name = parts_a[0]

    # Lấy mã vận đơn từ cả hai file, loại bỏ "NoCode"
    tracking_codes = []
    if len(parts_a) >= 2 and parts_a[1] != "NoCode":
        tracking_codes.append(parts_a[1])
    if len(parts_b) >= 2 and parts_b[1] != "NoCode":
        tracking_codes.append(parts_b[1])

    # Lấy thời gian từ file đầu tiên
    date = parts_a[2] if len(parts_a) >= 3 else "unknown"
    hour = parts_a[3].split(".")[0] if len(parts_a) >= 4 else "0000"
    time_str = f"{date}_{hour}"

    # Tạo tên mã vận đơn: dùng một mã hoặc ghép nhiều mã bằng "-"
    tracking_str = "-".join(tracking_codes) if tracking_codes else "unknown"

    # Tạo tên file đầu ra
    output_file = os.path.join(output_dir, f"{brand_name}_{tracking_str}_{time_str}.mp4")

    # Ghép nối video A và B
    concat_list_file = os.path.join(output_dir, f"concat_list_{event_a.get('event_id')}.txt")
    try:
        with open(concat_list_file, 'w') as f:
            f.write(f"file '{temp_file_a}'\nfile '{temp_file_b}'\n")

        cmd_concat = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_file,
            "-c", "copy",
            "-y",
            output_file
        ]
        subprocess.run(cmd_concat, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        print(f"Đã ghép và cắt video: {output_file}")

        # Log độ dài của file ghép
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", output_file],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        duration = float(probe.stdout.strip())
        print(f"File ghép {output_file} có độ dài: {duration} giây")

        # Xóa các file tạm và file concat_list sau khi ghép thành công
        if os.path.exists(temp_file_a):
            os.remove(temp_file_a)
        if os.path.exists(temp_file_b):
            os.remove(temp_file_b)
        if os.path.exists(concat_list_file):
            os.remove(concat_list_file)

        return output_file

    except subprocess.CalledProcessError as e:
        print(f"Lỗi khi ghép video: {e}")
        # Xóa các file tạm và file concat_list trong trường hợp lỗi
        if os.path.exists(temp_file_a):
            os.remove(temp_file_a)
        if os.path.exists(temp_file_b):
            os.remove(temp_file_b)
        if os.path.exists(concat_list_file):
            os.remove(concat_list_file)
        return None
    except Exception as e:
        print(f"Lỗi không xác định khi ghép video: {e}")
        # Xóa các file tạm và file concat_list trong trường hợp lỗi
        if os.path.exists(temp_file_a):
            os.remove(temp_file_a)
        if os.path.exists(temp_file_b):
            os.remove(temp_file_b)
        if os.path.exists(concat_list_file):
            os.remove(concat_list_file)
        return None