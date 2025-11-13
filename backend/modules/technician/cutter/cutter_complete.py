import subprocess


def cut_complete_event(event, video_buffer, video_length, output_file):
    """Cut video for complete event (has both ts and te)."""
    ts = event.get("ts")
    te = event.get("te")
    video_file = event.get("video_file")

    start_time = max(0, ts - video_buffer)  # Add buffer before ts
    end_time = min(te + video_buffer, video_length)  # Add buffer after te
    duration = end_time - start_time

    if duration <= 0:
        print(f"Skipped: Invalid duration ({duration}s) for event {event.get('event_id')}")
        return False

    try:
        cmd = [
            "ffmpeg",
            "-i",
            video_file,
            "-ss",
            str(start_time),
            "-t",
            str(duration),
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-y",
            output_file,
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Video cut: {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error cutting video {video_file}: {e}")
        return False
    except Exception as e:
        print(f"Unknown error: {e}")
        return False
