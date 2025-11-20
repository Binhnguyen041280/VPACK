#!/usr/bin/env python3
"""
Camera Simulator - Main orchestrator for multi-camera simulation
"""
import os
import sys
import argparse
import logging
import time
import signal
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import yaml

from video_generator import VideoGenerator
from camera import CameraSimulator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class SimulatorOrchestrator:
    """Orchestrates multiple camera simulators"""

    def __init__(self, config_path: str):
        """
        Initialize simulator orchestrator

        Args:
            config_path: Path to configuration YAML file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.video_generator = VideoGenerator()
        self.cameras: List[CameraSimulator] = []
        self.is_running = False

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _load_config(self) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

    def setup(self):
        """Setup cameras from configuration"""
        logger.info("Setting up cameras...")

        cameras_config = self.config.get('cameras', [])
        if not cameras_config:
            raise ValueError("No cameras configured")

        # Get base path for resolving relative paths
        base_path = Path(self.config_path).parent

        for cam_config in cameras_config:
            try:
                name = cam_config['name']
                source_video = cam_config['source_video']
                output_folder = cam_config['output_folder']
                pattern_type = cam_config['pattern']
                pattern_config = cam_config.get('config', {})

                # Resolve relative paths
                if not os.path.isabs(source_video):
                    source_video = os.path.join(base_path, source_video)
                if not os.path.isabs(output_folder):
                    output_folder = os.path.join(base_path, output_folder)

                # Create camera simulator
                camera = CameraSimulator(
                    name=name,
                    source_video=source_video,
                    output_folder=output_folder,
                    pattern_type=pattern_type,
                    config=pattern_config,
                    video_generator=self.video_generator
                )

                self.cameras.append(camera)
                logger.info(f"✓ Setup camera: {name}")

            except Exception as e:
                logger.error(f"Failed to setup camera '{cam_config.get('name', 'unknown')}': {e}")
                raise

        logger.info(f"Setup complete: {len(self.cameras)} cameras ready")

    def start(self, start_time: datetime = None):
        """Start all camera simulators"""
        if not self.cameras:
            logger.error("No cameras to start. Run setup() first")
            return

        self.is_running = True

        # Get simulation parameters
        sim_config = self.config.get('simulator', {})
        duration_hours = sim_config.get('run_duration_hours', 24)

        # Use provided start_time or now
        if start_time is None:
            start_time = datetime.now()

        logger.info(
            f"Starting simulation: "
            f"start_time={start_time}, "
            f"duration={duration_hours}h"
        )

        # Generate schedules for all cameras
        for camera in self.cameras:
            camera.generate_schedule(start_time, duration_hours)

        # Start all cameras
        for camera in self.cameras:
            camera.start(start_time)

        logger.info("All cameras started")

        # Monitor and display status
        self._monitor_loop()

    def stop(self):
        """Stop all camera simulators"""
        if not self.is_running:
            return

        logger.info("Stopping all cameras...")
        self.is_running = False

        for camera in self.cameras:
            camera.stop()

        logger.info("All cameras stopped")

        # Display final statistics
        self._display_final_stats()

    def pause(self):
        """Pause all camera simulators"""
        logger.info("Pausing all cameras...")
        for camera in self.cameras:
            camera.pause()

    def resume(self):
        """Resume all camera simulators"""
        logger.info("Resuming all cameras...")
        for camera in self.cameras:
            camera.resume()

    def _monitor_loop(self):
        """Monitor cameras and display status"""
        sim_config = self.config.get('simulator', {})
        duration_hours = sim_config.get('run_duration_hours', 24)
        status_interval = sim_config.get('status_interval_seconds', 60)

        start_time = datetime.now()
        end_time = start_time + timedelta(hours=duration_hours) if duration_hours > 0 else None

        logger.info("Monitoring cameras (Ctrl+C to stop)...")

        last_status_time = time.time()

        try:
            while self.is_running:
                # Check if all cameras are done
                all_done = all(
                    not camera.is_running or
                    camera.current_event_index >= len(camera.events)
                    for camera in self.cameras
                )

                if all_done:
                    logger.info("All cameras completed their schedules")
                    break

                # Check if duration exceeded
                if end_time and datetime.now() >= end_time:
                    logger.info("Simulation duration exceeded")
                    break

                # Display status periodically
                current_time = time.time()
                if current_time - last_status_time >= status_interval:
                    self._display_status()
                    last_status_time = current_time

                # Sleep
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Interrupted by user")

        finally:
            self.stop()

    def _display_status(self):
        """Display current status of all cameras"""
        logger.info("=" * 80)
        logger.info("CAMERA STATUS:")

        total_videos = 0
        total_errors = 0

        for camera in self.cameras:
            stats = camera.get_stats()
            status = camera.get_status()

            logger.info(
                f"  {stats['name']:20s} | "
                f"Status: {status:25s} | "
                f"Videos: {stats['videos_created']:3d} | "
                f"Errors: {stats['errors']:2d} | "
                f"Duration: {stats['total_duration_minutes']:.1f}m"
            )

            total_videos += stats['videos_created']
            total_errors += stats['errors']

        logger.info(f"TOTAL: {total_videos} videos, {total_errors} errors")
        logger.info("=" * 80)

    def _display_final_stats(self):
        """Display final statistics"""
        logger.info("=" * 80)
        logger.info("FINAL STATISTICS:")

        total_videos = 0
        total_duration = 0
        total_errors = 0

        for camera in self.cameras:
            stats = camera.get_stats()

            elapsed_time = None
            if stats['start_time'] and stats['end_time']:
                elapsed_time = stats['end_time'] - stats['start_time']

            logger.info(
                f"\n{stats['name']}:"
                f"\n  Videos Created: {stats['videos_created']}"
                f"\n  Total Duration: {stats['total_duration_minutes']:.1f} minutes"
                f"\n  Errors: {stats['errors']}"
                f"\n  Elapsed Time: {elapsed_time}"
            )

            total_videos += stats['videos_created']
            total_duration += stats['total_duration_minutes']
            total_errors += stats['errors']

        logger.info(
            f"\nOVERALL:"
            f"\n  Total Videos: {total_videos}"
            f"\n  Total Duration: {total_duration:.1f} minutes ({total_duration/60:.1f} hours)"
            f"\n  Total Errors: {total_errors}"
        )
        logger.info("=" * 80)

    def cleanup_old_files(self):
        """Cleanup old simulated files based on retention settings"""
        sim_config = self.config.get('simulator', {})
        cleanup_enabled = sim_config.get('cleanup_old_files', False)
        retention_count = sim_config.get('retention_count', 100)

        if not cleanup_enabled:
            return

        logger.info("Cleaning up old files...")

        for camera in self.cameras:
            try:
                output_folder = camera.output_folder
                if not os.path.exists(output_folder):
                    continue

                # Get all video files sorted by modification time
                video_files = []
                for filename in os.listdir(output_folder):
                    if filename.endswith('.mp4'):
                        filepath = os.path.join(output_folder, filename)
                        mtime = os.path.getmtime(filepath)
                        video_files.append((filepath, mtime))

                # Sort by modification time (newest first)
                video_files.sort(key=lambda x: x[1], reverse=True)

                # Delete files beyond retention count
                deleted_count = 0
                for filepath, _ in video_files[retention_count:]:
                    try:
                        os.remove(filepath)
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Failed to delete {filepath}: {e}")

                if deleted_count > 0:
                    logger.info(
                        f"[{camera.name}] Deleted {deleted_count} old files "
                        f"(retained {min(len(video_files), retention_count)})"
                    )

            except Exception as e:
                logger.error(f"Error cleaning up {camera.name}: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Camera Simulator - Simulate multiple camera video streams',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default config
  python simulator.py

  # Run with custom config
  python simulator.py -c my_config.yaml

  # Run with custom start time
  python simulator.py --start-time "2025-11-20 08:00:00"

  # Enable debug logging
  python simulator.py -v
        """
    )

    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )

    parser.add_argument(
        '--start-time',
        help='Simulation start time (format: "YYYY-MM-DD HH:MM:SS")'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose (debug) logging'
    )

    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Cleanup old files before starting'
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Parse start time if provided
    start_time = None
    if args.start_time:
        try:
            start_time = datetime.strptime(args.start_time, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            logger.error("Invalid start time format. Use: YYYY-MM-DD HH:MM:SS")
            sys.exit(1)

    try:
        # Create orchestrator
        orchestrator = SimulatorOrchestrator(args.config)

        # Setup cameras
        orchestrator.setup()

        # Cleanup old files if requested
        if args.cleanup:
            orchestrator.cleanup_old_files()

        # Start simulation
        orchestrator.start(start_time)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
