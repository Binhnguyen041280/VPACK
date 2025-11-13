import cv2
import argparse
import os
import logging


def setup_logging():
    # Use var/logs for application logs
    from modules.path_utils import get_logs_dir

    log_dir = get_logs_dir()
    log_file_path = os.path.join(log_dir, f"roi_preview_{os.getpid()}.log")
    logging.basicConfig(
        filename=log_file_path,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logging.info(f"ROI Preview started with PID {os.getpid()}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, help="File video .mp4")
    parser.add_argument("--roi", nargs=4, type=int, required=True, help="Tọa độ ROI: x y w h")
    args = parser.parse_args()

    setup_logging()
    x, y, w, h = args.roi
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        logging.error(f"Cannot open {args.video}")
        return

    win = "ROI Preview"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, w, h)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        crop = frame[y : y + h, x : x + w]
        cv2.imshow(win, crop)
        if cv2.waitKey(30) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    logging.info("ROI Preview closed")


if __name__ == "__main__":
    main()
