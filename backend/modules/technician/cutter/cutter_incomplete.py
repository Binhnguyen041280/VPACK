import os
import subprocess
from .cutter_utils import generate_merged_filename, generate_output_filename
from modules.path_utils import get_tmp_dir


def cut_incomplete_event(event, video_buffer, video_length, output_file):
    """Cut video for incomplete event (missing ts or te)."""
    ts = event.get("ts")
    te = event.get("te")
    video_file = event.get("video_file")

    # Log original video length
    print(f"Original video {video_file} length: {video_length} seconds")

    # Log video_buffer value
    print(f"Using video_buffer: {video_buffer} seconds")

    if ts is not None and te is None:  # Only has ts
        start_time = max(0, ts - video_buffer)
        duration = video_length - start_time
    elif ts is None and te is not None:  # Only has te
        start_time = 0
        duration = min(te + video_buffer, video_length)
    else:
        print(f"Skipped: Event {event.get('event_id')} has no ts or te")
        return False

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

        # Log length of incomplete file just created
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                output_file,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        duration = float(probe.stdout.strip())
        print(f"Incomplete file {output_file} length: {duration} seconds")

        event["cut_video_file"] = output_file
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error cutting video {video_file}: {e}")
        return False
    except Exception as e:
        print(f"Unknown error: {e}")
        return False


def merge_incomplete_events(
    event_a,
    event_b,
    video_buffer,
    video_length_a,
    video_length_b,
    output_dir,
    max_packing_time,
    brand_name="Alan",
):
    """Merge two incomplete events (A has ts, B has te) and create merged file with optimized name."""
    video_file_a = event_a.get("video_file")
    video_file_b = event_b.get("video_file")

    # Check if file already cut
    temp_file_a = event_a.get("cut_video_file")
    temp_file_b = event_b.get("cut_video_file")
    files_to_cleanup = []

    # Create temp_clips directory for temporary files in var/tmp
    temp_clips_dir = os.path.join(get_tmp_dir(), "temp_clips")
    if not os.path.exists(temp_clips_dir):
        os.makedirs(temp_clips_dir)

    # If no pre-cut file, cut immediately and save to temp_clips_dir
    if not temp_file_a or not os.path.exists(temp_file_a):
        temp_file_a = os.path.join(
            temp_clips_dir, f"temp_a_{event_a.get('event_id')}_incomplete.mp4"
        )
        if not cut_incomplete_event(event_a, video_buffer, video_length_a, temp_file_a):
            print(f"Error: Cannot cut temporary file for event {event_a.get('event_id')}")
            return None
    if not temp_file_b or not os.path.exists(temp_file_b):
        temp_file_b = os.path.join(
            temp_clips_dir, f"temp_b_{event_b.get('event_id')}_incomplete.mp4"
        )
        if not cut_incomplete_event(event_b, video_buffer, video_length_b, temp_file_b):
            print(f"Error: Cannot cut temporary file for event {event_b.get('event_id')}")
            return None

    # Create optimized output filename based on temp_file_a and temp_file_b
    file_name_a = os.path.basename(temp_file_a)
    file_name_b = os.path.basename(temp_file_b)
    parts_a = file_name_a.split("_")
    parts_b = file_name_b.split("_")

    # Get Brand from first file
    brand_name = parts_a[0]

    # Get tracking codes from both files, remove "NoCode"
    tracking_codes = []
    if len(parts_a) >= 2 and parts_a[1] != "NoCode":
        tracking_codes.append(parts_a[1])
    if len(parts_b) >= 2 and parts_b[1] != "NoCode":
        tracking_codes.append(parts_b[1])

    # Get time from first file
    date = parts_a[2] if len(parts_a) >= 3 else "unknown"
    hour = parts_a[3].split(".")[0] if len(parts_a) >= 4 else "0000"
    time_str = f"{date}_{hour}"

    # Create tracking code name: use one code or join multiple codes with "-"
    tracking_str = "-".join(tracking_codes) if tracking_codes else "unknown"

    # Create output filename
    output_file = os.path.join(output_dir, f"{brand_name}_{tracking_str}_{time_str}.mp4")

    # Concatenate videos A and B
    concat_list_file = os.path.join(get_tmp_dir(), f"concat_list_{event_a.get('event_id')}.txt")
    try:
        with open(concat_list_file, "w") as f:
            f.write(f"file '{temp_file_a}'\nfile '{temp_file_b}'\n")

        cmd_concat = [
            "ffmpeg",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list_file,
            "-c",
            "copy",
            "-y",
            output_file,
        ]
        subprocess.run(cmd_concat, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        print(f"Video merged and cut: {output_file}")

        # Log length of merged file
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                output_file,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        duration = float(probe.stdout.strip())
        print(f"Merged file {output_file} length: {duration} seconds")

        # Delete temporary files and concat_list after successful merge
        if os.path.exists(temp_file_a):
            os.remove(temp_file_a)
        if os.path.exists(temp_file_b):
            os.remove(temp_file_b)
        if os.path.exists(concat_list_file):
            os.remove(concat_list_file)

        return output_file

    except subprocess.CalledProcessError as e:
        print(f"Error merging videos: {e}")
        # Delete temporary files and concat_list in case of error
        if os.path.exists(temp_file_a):
            os.remove(temp_file_a)
        if os.path.exists(temp_file_b):
            os.remove(temp_file_b)
        if os.path.exists(concat_list_file):
            os.remove(concat_list_file)
        return None
    except Exception as e:
        print(f"Unknown error merging videos: {e}")
        # Delete temporary files and concat_list in case of error
        if os.path.exists(temp_file_a):
            os.remove(temp_file_a)
        if os.path.exists(temp_file_b):
            os.remove(temp_file_b)
        if os.path.exists(concat_list_file):
            os.remove(concat_list_file)
        return None
