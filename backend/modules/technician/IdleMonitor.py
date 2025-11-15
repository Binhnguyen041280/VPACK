import logging
import os
import queue
import uuid
from datetime import datetime

import cv2
import mediapipe as mp
from modules.config.logging_config import get_logger


class IdleMonitor:
    def __init__(self, processing_config=None):
        """Initialize IdleMonitor with queue and processing_config."""
        self.video_file = None
        self.logger = get_logger("app", {"video_id": None})
        self.logger.setLevel(logging.INFO)
        self.work_block_queue = queue.Queue()  # Queue to store work blocks
        # Initialize MediaPipe Hands (using pattern from hand_detection.py)
        try:
            self.mp_hands = mp.solutions.hands  # type: ignore
            self.mp_drawing = mp.solutions.drawing_utils  # type: ignore
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.6,
                min_tracking_confidence=0.5,
            )
        except AttributeError as e:
            logging.error(f"MediaPipe import error: {e}")
            raise ImportError("MediaPipe modules not found. Please reinstall MediaPipe.")
        self.IDLE_GAP = 120  # seconds
        self.HAND_SAMPLE_INTERVAL = 1  # seconds
        self.MIN_WORK_BLOCK = 10  # seconds
        self.MIN_PACKING_TIME = (
            processing_config.get("min_packing_time", 5) if processing_config else 5
        )  # seconds
        self.CHUNK_SIZE = int(self.MIN_PACKING_TIME * 0.8)  # seconds
        self.video_id = str(uuid.uuid4())  # Unique identifier for video

    def process_video(self, video_file, camera_name, packing_area):
        """Process video, identify work blocks, save to queue, using packing_area from program_runner."""
        self.video_file = video_file
        self.logger = get_logger("app", {"video_id": os.path.basename(self.video_file)})
        # Open video
        cap = cv2.VideoCapture(video_file)
        if not cap.isOpened():
            self.logger.error(f"Failed to open video: {video_file}")
            return

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_duration = int(total_frames / fps)
        self.logger.info(
            f"Processing video: {video_file}, Duration: {video_duration}s, Video ID: {self.video_id}"
        )

        # Check packing_area
        roi = packing_area
        if not roi:
            self.logger.warning(f"No packing_area for {camera_name}, using full frame")
            roi = None

        hand_timeline = []
        event_id = 0

        # Scan video by chunks
        sec = 0
        while sec < video_duration:
            chunk_end = min(sec + self.CHUNK_SIZE, video_duration)
            chunk_has_hand = False
            check_time = sec
            # Scan entire chunk uniformly
            while check_time < chunk_end:
                frame_id = int(check_time * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
                ret, frame = cap.read()
                if not ret:
                    break

                # Apply ROI if available
                if roi:
                    x, y, w, h = roi
                    frame_height, frame_width = frame.shape[:2]
                    if w > 0 and h > 0 and y + h <= frame_height and x + w <= frame_width:
                        frame = frame[y : y + h, x : x + w]
                    else:
                        self.logger.warning(f"Invalid ROI for frame {frame_id}: {roi}")
                        frame = frame

                # Hand detection
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.hands.process(rgb_frame)
                if results.multi_hand_landmarks is not None:
                    chunk_has_hand = True
                    break
                check_time += self.HAND_SAMPLE_INTERVAL

            hand_timeline.append(chunk_has_hand)
            # self.logger.info(f"[Chunk {sec:04d}-{chunk_end:04d}s] Hand: {chunk_has_hand}, Video ID: {self.video_id}")
            sec += self.CHUNK_SIZE

        # Detect idle blocks
        idle_gap_list = []
        idle_candidate_start = None
        for tick_time, hand_detected in enumerate(hand_timeline):
            if hand_detected:
                if idle_candidate_start is not None:
                    idle_duration = tick_time - idle_candidate_start
                    if idle_duration * self.CHUNK_SIZE >= self.IDLE_GAP:
                        idle_gap_list.append(
                            {
                                "start": idle_candidate_start * self.CHUNK_SIZE,
                                "end": tick_time * self.CHUNK_SIZE,
                            }
                        )
                    idle_candidate_start = None
            else:
                if idle_candidate_start is None:
                    idle_candidate_start = tick_time

        if idle_candidate_start is not None:
            idle_duration = len(hand_timeline) - idle_candidate_start
            if idle_duration * self.CHUNK_SIZE >= self.IDLE_GAP:
                idle_gap_list.append(
                    {
                        "start": idle_candidate_start * self.CHUNK_SIZE,
                        "end": len(hand_timeline) * self.CHUNK_SIZE,
                    }
                )

        # Detect work blocks
        work_blocks = []
        prev_end = 0
        for idle in idle_gap_list:
            if idle["start"] > prev_end:
                work_blocks.append({"start": prev_end, "end": idle["start"]})
            prev_end = idle["end"]
        if prev_end < len(hand_timeline) * self.CHUNK_SIZE:
            work_blocks.append({"start": prev_end, "end": len(hand_timeline) * self.CHUNK_SIZE})

        # Save work blocks to queue
        for idx, block in enumerate(work_blocks):
            duration = block["end"] - block["start"]
            event_id += 1
            if duration < self.MIN_WORK_BLOCK:
                self.logger.info(
                    f"Skipping work block {idx+1}: duration {duration}s < {self.MIN_WORK_BLOCK}s"
                )
                continue
            self.work_block_queue.put(
                {
                    "video_id": self.video_id,
                    "event_id": f"evt_{event_id:03d}",
                    "file_path": video_file,
                    "start_time": block["start"],
                    "end_time": block["end"],
                }
            )
            self.logger.info(
                f"Work block {idx+1}: {block['start']}s --> {block['end']}s (duration: {duration}s), Video ID: {self.video_id}"
            )
            if duration < self.MIN_WORK_BLOCK:
                self.logger.warning(f"Block shorter than {self.MIN_WORK_BLOCK}s")

        cap.release()
        self.hands.close()

    def get_work_block_queue(self):
        """Return queue containing work blocks."""
        return self.work_block_queue
