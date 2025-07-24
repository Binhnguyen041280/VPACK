from readerwriterlock import rwlock
import threading

db_rwlock = rwlock.RWLockFairD()  # Sử dụng RWLockFairD để tránh deadlock
frame_sampler_event = threading.Event()
event_detector_event = threading.Event()
event_detector_done = threading.Event()
event_detector_done.set()  # Ban đầu cho phép Frame Sampler chạy
