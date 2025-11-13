import cv2
import logging
import time
import os
from datetime import timedelta
from modules.db_utils.safe_connection import safe_db_connection
from modules.scheduler.db_sync import db_rwlock


def run_trigger_logic(
    core_sampler,
    video_capture,
    video_metadata,
    trigger_roi_coords_for_state_check,
    get_log_handle_callback,
):
    core_sampler.logger.info(f"TRIGGER_PROCESSOR: Starting for {video_metadata['base_video_name']}")
    frame_idx_counter_tr = 0
    frame_states_buffer_list_tr = []
    mvd_buffer_list_tr = []
    last_recorded_state_tr = None
    last_recorded_mvd_tr = ""
    second = 0
    current_start_second = 0
    current_end_second = core_sampler.log_segment_duration
    log_file = os.path.join(
        core_sampler.log_dir_output_segments,
        f"log_{video_metadata['base_video_name']}_{current_start_second:04d}_{current_end_second:04d}.txt",
    )
    log_file_handle = open(log_file, "w")
    log_file_handle.write(
        f"# Start: {current_start_second}, End: {current_end_second}, Start_Time: {(video_metadata['start_time_obj'] + timedelta(seconds=current_start_second)).strftime('%Y-%m-%d %H:%M:%S')}, Camera_Name: {video_metadata['camera_name']}, Video_File: {video_metadata['absolute_video_path']}\n"
    )
    log_file_handle.flush()
    with db_rwlock.gen_wlock():
        with safe_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM processed_logs WHERE log_file = ?", (log_file,))
            log_exists = cursor.fetchone()
            if not log_exists:
                cursor.execute(
                    "INSERT INTO processed_logs (log_file, is_processed) VALUES (?, 0)", (log_file,)
                )
    while video_capture.isOpened():
        ret, bgr_frame = video_capture.read()
        if not ret:
            break
        frame_idx_counter_tr += 1
        if frame_idx_counter_tr % core_sampler.frame_interval != 0:
            continue
        state_val, mvd_val = core_sampler._internal_process_frame_qr(
            bgr_frame,
            frame_idx_counter_tr,
            trigger_roi_coords_for_state_check=trigger_roi_coords_for_state_check,
        )
        frame_states_buffer_list_tr.append(state_val)
        mvd_buffer_list_tr.append(mvd_val)
        second_in_video = (frame_idx_counter_tr - 1) / core_sampler.fps
        second = round(second_in_video)
        if second >= current_end_second:
            log_file_handle.close()
            current_start_second = current_end_second
            current_end_second += core_sampler.log_segment_duration
            log_file = os.path.join(
                core_sampler.log_dir_output_segments,
                f"log_{video_metadata['base_video_name']}_{current_start_second:04d}_{current_end_second:04d}.txt",
            )
            log_file_handle = open(log_file, "w")
            log_file_handle.write(
                f"# Start: {current_start_second}, End: {current_end_second}, Start_Time: {(video_metadata['start_time_obj'] + timedelta(seconds=current_start_second)).strftime('%Y-%m-%d %H:%M:%S')}, Camera_Name: {video_metadata['camera_name']}, Video_File: {video_metadata['absolute_video_path']}\n"
            )
            log_file_handle.flush()
            with db_rwlock.gen_wlock():
                with safe_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1 FROM processed_logs WHERE log_file = ?", (log_file,))
                    log_exists = cursor.fetchone()
                    if not log_exists:
                        cursor.execute(
                            "INSERT INTO processed_logs (log_file, is_processed) VALUES (?, 0)",
                            (log_file,),
                        )
        if len(frame_states_buffer_list_tr) == 5:
            on_count_tr = frame_states_buffer_list_tr.count("On")
            determined_final_state_tr = "On" if on_count_tr >= 3 else "Off"
            determined_final_mvd_tr = mvd_buffer_list_tr[-1] if mvd_buffer_list_tr else ""
            if (
                determined_final_state_tr != last_recorded_state_tr
                or determined_final_mvd_tr != last_recorded_mvd_tr
            ):
                log_handle_tr = get_log_handle_callback(second_in_video)
                log_handle_tr.write(
                    f"{second},{determined_final_state_tr},{determined_final_mvd_tr}\n"
                )
                log_handle_tr.flush()
                last_recorded_state_tr = determined_final_state_tr
                last_recorded_mvd_tr = determined_final_mvd_tr
            frame_states_buffer_list_tr.clear()
            mvd_buffer_list_tr.clear()
    log_file_handle.close()
    core_sampler.logger.info(f"TRIGGER_PROCESSOR: Finished for {video_metadata['base_video_name']}")
