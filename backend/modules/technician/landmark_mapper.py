"""
Landmark Mapper Utility for V_Track Hand Detection
Provides coordinate transformation with fixed sizing for landmark rendering
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from modules.config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class VideoDimensions:
    """Video dimensions data structure"""

    width: int
    height: int

    def __post_init__(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Video dimensions must be positive")


@dataclass
class CanvasDimensions:
    """Canvas dimensions data structure"""

    width: int
    height: int

    def __post_init__(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Canvas dimensions must be positive")


@dataclass
class ROIConfig:
    """ROI configuration data structure"""

    x: int
    y: int
    w: int
    h: int

    def __post_init__(self):
        if self.w <= 0 or self.h <= 0:
            raise ValueError("ROI dimensions must be positive")
        if self.x < 0 or self.y < 0:
            raise ValueError("ROI coordinates must be non-negative")


@dataclass
class MappedLandmark:
    """Mapped landmark with both original and display coordinates"""

    # Original MediaPipe normalized coordinates [0,1] within ROI
    x_rel: float
    y_rel: float
    z: float

    # Absolute pixel coordinates in original video
    x_orig: float
    y_orig: float

    # Display coordinates for canvas rendering
    x_disp: float
    y_disp: float

    # Fixed rendering properties
    radius: int = 3
    line_width: int = 2


class LandmarkMapper:
    """
    Coordinate transformation utility for hand landmarks
    Implements the requested algorithm with fixed sizing
    """

    # Fixed rendering sizes as per requirements
    LANDMARK_RADIUS = 3  # Fixed 3px radius
    LINE_WIDTH = 2  # Fixed 2px line width

    @classmethod
    def get_fixed_sizes(cls) -> Dict[str, int]:
        """
        Get fixed landmark rendering sizes

        Returns:
            dict: {landmarkRadius: 3, lineWidth: 2}
        """
        return {"landmarkRadius": cls.LANDMARK_RADIUS, "lineWidth": cls.LINE_WIDTH}

    @classmethod
    def validate_inputs(
        cls, roi: ROIConfig, video_dims: VideoDimensions, canvas_dims: CanvasDimensions
    ) -> bool:
        """
        Validate input parameters for coordinate mapping

        Args:
            roi: ROI configuration
            video_dims: Video dimensions
            canvas_dims: Canvas dimensions

        Returns:
            bool: True if all inputs are valid

        Raises:
            ValueError: If any input is invalid
        """
        # Check ROI bounds within video
        if roi.x + roi.w > video_dims.width:
            raise ValueError(
                f"ROI extends beyond video width: {roi.x + roi.w} > {video_dims.width}"
            )

        if roi.y + roi.h > video_dims.height:
            raise ValueError(
                f"ROI extends beyond video height: {roi.y + roi.h} > {video_dims.height}"
            )

        # Check aspect ratio compatibility (warning only)
        video_aspect = video_dims.width / video_dims.height
        canvas_aspect = canvas_dims.width / canvas_dims.height
        aspect_diff = abs(video_aspect - canvas_aspect)

        if aspect_diff > 0.1:  # 10% difference threshold
            logger.warning(
                f"Aspect ratio mismatch: Video {video_aspect:.3f} vs Canvas {canvas_aspect:.3f}"
            )

        return True

    @classmethod
    def map_single_point(
        cls,
        x_rel: float,
        y_rel: float,
        roi: ROIConfig,
        video_dims: VideoDimensions,
        canvas_dims: CanvasDimensions,
    ) -> Tuple[float, float]:
        """
        Map single normalized point to display coordinates
        Implements the exact requested algorithm:

        Step 1: x_orig = x_roi + (x_rel × w_roi)
        Step 2: y_orig = y_roi + (y_rel × h_roi)
        Step 3: x_disp = x_orig × (W_disp / W_orig)
        Step 4: y_disp = y_orig × (H_disp / H_orig)

        Args:
            x_rel: Normalized x coordinate [0,1] within ROI
            y_rel: Normalized y coordinate [0,1] within ROI
            roi: ROI configuration
            video_dims: Original video dimensions
            canvas_dims: Display canvas dimensions

        Returns:
            tuple: (x_disp, y_disp) display coordinates
        """
        # Validate normalized coordinates
        if not (0 <= x_rel <= 1) or not (0 <= y_rel <= 1):
            logger.warning(f"Normalized coordinates out of range: ({x_rel:.3f}, {y_rel:.3f})")

        # Step 1 & 2: Convert ROI-relative to absolute video coordinates
        x_orig = roi.x + (x_rel * roi.w)
        y_orig = roi.y + (y_rel * roi.h)

        # Step 3 & 4: Convert to display coordinates
        x_disp = x_orig * (canvas_dims.width / video_dims.width)
        y_disp = y_orig * (canvas_dims.height / video_dims.height)

        return (x_disp, y_disp)

    @classmethod
    def map_landmarks(
        cls,
        landmarks: List[List[Dict[str, float]]],
        roi: ROIConfig,
        video_dims: VideoDimensions,
        canvas_dims: CanvasDimensions,
    ) -> List[List[MappedLandmark]]:
        """
        Map multiple hands landmarks to display coordinates with fixed sizing

        Args:
            landmarks: List of hands, each hand is list of landmark dicts
                      Each landmark: {'x': float, 'y': float, 'z': float}
            roi: ROI configuration
            video_dims: Original video dimensions
            canvas_dims: Display canvas dimensions

        Returns:
            List[List[MappedLandmark]]: Mapped landmarks with display coordinates
        """
        # Validate inputs
        cls.validate_inputs(roi, video_dims, canvas_dims)

        mapped_hands = []

        for hand_idx, hand_landmarks in enumerate(landmarks):
            mapped_hand = []

            for landmark_idx, landmark in enumerate(hand_landmarks):
                try:
                    # Extract normalized coordinates
                    x_rel = float(landmark.get("x", 0))
                    y_rel = float(landmark.get("y", 0))
                    z = float(landmark.get("z", 0))

                    # Apply coordinate mapping algorithm
                    x_orig = roi.x + (x_rel * roi.w)
                    y_orig = roi.y + (y_rel * roi.h)

                    x_disp = x_orig * (canvas_dims.width / video_dims.width)
                    y_disp = y_orig * (canvas_dims.height / video_dims.height)

                    # Create mapped landmark with fixed sizing
                    mapped_landmark = MappedLandmark(
                        x_rel=x_rel,
                        y_rel=y_rel,
                        z=z,
                        x_orig=x_orig,
                        y_orig=y_orig,
                        x_disp=x_disp,
                        y_disp=y_disp,
                        radius=cls.LANDMARK_RADIUS,
                        line_width=cls.LINE_WIDTH,
                    )

                    mapped_hand.append(mapped_landmark)

                    # Debug logging for first landmark of first hand
                    if hand_idx == 0 and landmark_idx == 0:
                        logger.debug(f"Fixed-Size Landmark Mapping:")
                        logger.debug(f"  Input: ({x_rel:.3f}, {y_rel:.3f}) normalized")
                        logger.debug(f"  ROI: x={roi.x}, y={roi.y}, w={roi.w}, h={roi.h}")
                        logger.debug(f"  Video: {video_dims.width}x{video_dims.height}")
                        logger.debug(f"  Canvas: {canvas_dims.width}x{canvas_dims.height}")
                        logger.debug(f"  Result: ({x_disp:.1f}, {y_disp:.1f}) display coords")
                        logger.debug(
                            f"  Fixed sizes: radius={cls.LANDMARK_RADIUS}px, line={cls.LINE_WIDTH}px"
                        )

                except (KeyError, ValueError, TypeError) as e:
                    logger.error(f"Error mapping landmark {landmark_idx} of hand {hand_idx}: {e}")
                    continue

            if mapped_hand:  # Only add hands with valid landmarks
                mapped_hands.append(mapped_hand)

        logger.info(
            f"Mapped {len(mapped_hands)} hands with fixed {cls.LANDMARK_RADIUS}px landmarks"
        )
        return mapped_hands

    @classmethod
    def create_canvas_landmarks_response(
        cls,
        landmarks: List[List[Dict[str, float]]],
        roi: ROIConfig,
        video_dims: VideoDimensions,
        canvas_dims: CanvasDimensions,
    ) -> Dict[str, Any]:
        """
        Create complete response with mapped landmarks for web interface

        Args:
            landmarks: Raw MediaPipe landmarks
            roi: ROI configuration
            video_dims: Video dimensions
            canvas_dims: Canvas dimensions

        Returns:
            dict: Complete response with canvas_landmarks field
        """
        try:
            mapped_landmarks = cls.map_landmarks(landmarks, roi, video_dims, canvas_dims)

            # Convert to serializable format
            canvas_landmarks = []
            for hand in mapped_landmarks:
                hand_data = []
                for landmark in hand:
                    hand_data.append(
                        {
                            "x_rel": landmark.x_rel,
                            "y_rel": landmark.y_rel,
                            "z": landmark.z,
                            "x_orig": landmark.x_orig,
                            "y_orig": landmark.y_orig,
                            "x_disp": landmark.x_disp,
                            "y_disp": landmark.y_disp,
                            "radius": landmark.radius,
                            "line_width": landmark.line_width,
                        }
                    )
                canvas_landmarks.append(hand_data)

            return {
                "success": True,
                "canvas_landmarks": canvas_landmarks,
                "fixed_sizes": cls.get_fixed_sizes(),
                "mapping_info": {
                    "algorithm": "fixed_size_mapping",
                    "roi": {"x": roi.x, "y": roi.y, "w": roi.w, "h": roi.h},
                    "video_dims": {"width": video_dims.width, "height": video_dims.height},
                    "canvas_dims": {"width": canvas_dims.width, "height": canvas_dims.height},
                    "landmark_radius": cls.LANDMARK_RADIUS,
                    "line_width": cls.LINE_WIDTH,
                },
            }

        except Exception as e:
            logger.error(f"Error creating canvas landmarks response: {e}")
            return {
                "success": False,
                "error": str(e),
                "canvas_landmarks": [],
                "fixed_sizes": cls.get_fixed_sizes(),
            }

    @classmethod
    def map_qr_bbox_to_canvas(
        cls,
        qr_bbox: Dict[str, int],
        roi: ROIConfig,
        video_dims: VideoDimensions,
        canvas_dims: CanvasDimensions,
    ) -> Dict[str, int]:
        """
        Transform QR bounding box coordinates from video space to canvas display space

        Args:
            qr_bbox: Dict with x, y, w, h in video coordinates
            roi: ROI configuration
            video_dims: Video dimensions
            canvas_dims: Canvas dimensions

        Returns:
            Dict with canvas_bbox containing display coordinates: {'x': int, 'y': int, 'w': int, 'h': int}
        """
        try:
            # Validate inputs
            cls.validate_inputs(roi, video_dims, canvas_dims)

            # Extract bbox coordinates
            bbox_x = int(qr_bbox.get("x", 0))
            bbox_y = int(qr_bbox.get("y", 0))
            bbox_w = int(qr_bbox.get("w", 0))
            bbox_h = int(qr_bbox.get("h", 0))

            # Validate bbox dimensions
            if bbox_w <= 0 or bbox_h <= 0:
                logger.warning(f"Invalid QR bbox dimensions: w={bbox_w}, h={bbox_h}")
                return {"x": 0, "y": 0, "w": 0, "h": 0}

            # Calculate scale factors (same as hand landmark mapping)
            scale_x = canvas_dims.width / video_dims.width
            scale_y = canvas_dims.height / video_dims.height

            # Transform coordinates using the same algorithm as landmarks
            # The QR bbox is already in video coordinates, so we just need to scale to canvas
            canvas_x = int(bbox_x * scale_x)
            canvas_y = int(bbox_y * scale_y)
            canvas_w = int(bbox_w * scale_x)
            canvas_h = int(bbox_h * scale_y)

            # Ensure coordinates are within canvas boundaries
            canvas_x = max(0, min(canvas_x, canvas_dims.width - 1))
            canvas_y = max(0, min(canvas_y, canvas_dims.height - 1))

            # Ensure bbox doesn't exceed canvas boundaries
            if canvas_x + canvas_w > canvas_dims.width:
                canvas_w = canvas_dims.width - canvas_x
            if canvas_y + canvas_h > canvas_dims.height:
                canvas_h = canvas_dims.height - canvas_y

            # Ensure minimum size for visibility
            canvas_w = max(1, canvas_w)
            canvas_h = max(1, canvas_h)

            result = {"x": canvas_x, "y": canvas_y, "w": canvas_w, "h": canvas_h}

            logger.debug(
                f"QR bbox mapping: {qr_bbox} -> {result} (scale: {scale_x:.3f}, {scale_y:.3f})"
            )
            return result

        except Exception as e:
            logger.error(f"Error mapping QR bbox to canvas: {e}")
            return {"x": 0, "y": 0, "w": 0, "h": 0}

    @classmethod
    def create_canvas_qr_response(
        cls,
        qr_detections: List[Dict[str, Any]],
        roi: ROIConfig,
        video_dims: VideoDimensions,
        canvas_dims: CanvasDimensions,
    ) -> Dict[str, Any]:
        """
        Create complete QR detection response with both original and canvas coordinates

        Args:
            qr_detections: List of QR detections with video coordinates
                          Each detection: {'bbox': {'x': int, 'y': int, 'w': int, 'h': int},
                                          'decoded_text': str, 'confidence': float}
            roi: ROI configuration
            video_dims: Video dimensions
            canvas_dims: Canvas dimensions

        Returns:
            {
                "success": bool,
                "canvas_qr_detections": [
                    {
                        "bbox": {"x": int, "y": int, "w": int, "h": int},  // original
                        "canvas_bbox": {"x": int, "y": int, "w": int, "h": int},  // display
                        "decoded_text": str,
                        "confidence": float
                    }
                ],
                "mapping_algorithm": "qr_bbox_mapping",
                "error": str (if failed)
            }
        """
        try:
            # Validate inputs
            cls.validate_inputs(roi, video_dims, canvas_dims)

            canvas_qr_detections = []
            successful_mappings = 0
            total_detections = len(qr_detections)

            for i, qr_detection in enumerate(qr_detections):
                try:
                    # Extract QR data
                    bbox = qr_detection.get("bbox", {})
                    decoded_text = qr_detection.get("decoded_text", "")
                    confidence = qr_detection.get("confidence", 0.0)

                    # Map bbox to canvas coordinates
                    canvas_bbox = cls.map_qr_bbox_to_canvas(bbox, roi, video_dims, canvas_dims)

                    # Create enhanced QR detection with both coordinate systems
                    canvas_qr_detection = {
                        "bbox": bbox,  # Original video coordinates
                        "canvas_bbox": canvas_bbox,  # Display coordinates
                        "decoded_text": decoded_text,
                        "confidence": confidence,
                        "detection_id": i,  # Add ID for tracking
                    }

                    canvas_qr_detections.append(canvas_qr_detection)
                    successful_mappings += 1

                    # Debug logging for first QR detection
                    if i == 0:
                        logger.debug(f"QR Coordinate Mapping:")
                        logger.debug(f"  Original bbox: {bbox}")
                        logger.debug(f"  Canvas bbox: {canvas_bbox}")
                        logger.debug(f"  Text: '{decoded_text}', Confidence: {confidence}")
                        logger.debug(f"  ROI: x={roi.x}, y={roi.y}, w={roi.w}, h={roi.h}")
                        logger.debug(f"  Video: {video_dims.width}x{video_dims.height}")
                        logger.debug(f"  Canvas: {canvas_dims.width}x{canvas_dims.height}")

                except Exception as e:
                    logger.error(f"Error mapping QR detection {i}: {e}")
                    continue

            # Create response
            response = {
                "success": True,
                "canvas_qr_detections": canvas_qr_detections,
                "mapping_algorithm": "qr_bbox_mapping",
                "mapping_info": {
                    "total_detections": total_detections,
                    "successful_mappings": successful_mappings,
                    "roi": {"x": roi.x, "y": roi.y, "w": roi.w, "h": roi.h},
                    "video_dims": {"width": video_dims.width, "height": video_dims.height},
                    "canvas_dims": {"width": canvas_dims.width, "height": canvas_dims.height},
                    "scale_factors": {
                        "x": canvas_dims.width / video_dims.width,
                        "y": canvas_dims.height / video_dims.height,
                    },
                },
            }

            logger.info(
                f"Mapped {successful_mappings}/{total_detections} QR detections to canvas coordinates"
            )
            return response

        except Exception as e:
            logger.error(f"Error creating canvas QR response: {e}")
            return {
                "success": False,
                "error": str(e),
                "canvas_qr_detections": [],
                "mapping_algorithm": "qr_bbox_mapping",
            }


def test_coordinate_mapping():
    """
    Test function for coordinate mapping verification
    Test case: ROI (500,300,400,200) in 1920x1080 video, Canvas 960x540
    MediaPipe input (0.7, 0.4) → Expected canvas (390, 190)
    """
    # Test parameters
    roi = ROIConfig(x=500, y=300, w=400, h=200)
    video_dims = VideoDimensions(width=1920, height=1080)
    canvas_dims = CanvasDimensions(width=960, height=540)

    # Test input
    x_rel, y_rel = 0.7, 0.4

    # Expected calculation:
    # x_orig = 500 + (0.7 × 400) = 500 + 280 = 780
    # y_orig = 300 + (0.4 × 200) = 300 + 80 = 380
    # x_disp = 780 × (960 / 1920) = 780 × 0.5 = 390
    # y_disp = 380 × (540 / 1080) = 380 × 0.5 = 190

    expected_x_disp, expected_y_disp = 390.0, 190.0

    # Run test
    x_disp, y_disp = LandmarkMapper.map_single_point(x_rel, y_rel, roi, video_dims, canvas_dims)

    # Verify results
    assert abs(x_disp - expected_x_disp) < 0.001, f"X mismatch: {x_disp} vs {expected_x_disp}"
    assert abs(y_disp - expected_y_disp) < 0.001, f"Y mismatch: {y_disp} vs {expected_y_disp}"

    print("✅ Coordinate mapping test passed!")
    print(f"Input: ({x_rel}, {y_rel}) → Output: ({x_disp}, {y_disp})")
    print(f"Expected: ({expected_x_disp}, {expected_y_disp})")

    return True


def test_qr_bbox_mapping():
    """
    Test function for QR bbox coordinate mapping verification
    Test case: QR bbox (780, 380, 100, 50) in 1920x1080 video → Canvas 960x540
    Expected canvas bbox: (390, 190, 50, 25)
    """
    # Test parameters (same as landmark test for consistency)
    roi = ROIConfig(x=500, y=300, w=400, h=200)
    video_dims = VideoDimensions(width=1920, height=1080)
    canvas_dims = CanvasDimensions(width=960, height=540)

    # Test QR bbox in video coordinates
    test_bbox = {"x": 780, "y": 380, "w": 100, "h": 50}

    # Expected calculation (50% scale factor):
    # canvas_x = 780 × 0.5 = 390
    # canvas_y = 380 × 0.5 = 190
    # canvas_w = 100 × 0.5 = 50
    # canvas_h = 50 × 0.5 = 25
    expected_canvas_bbox = {"x": 390, "y": 190, "w": 50, "h": 25}

    # Run test
    canvas_bbox = LandmarkMapper.map_qr_bbox_to_canvas(test_bbox, roi, video_dims, canvas_dims)

    # Verify results
    assert (
        canvas_bbox["x"] == expected_canvas_bbox["x"]
    ), f"X mismatch: {canvas_bbox['x']} vs {expected_canvas_bbox['x']}"
    assert (
        canvas_bbox["y"] == expected_canvas_bbox["y"]
    ), f"Y mismatch: {canvas_bbox['y']} vs {expected_canvas_bbox['y']}"
    assert (
        canvas_bbox["w"] == expected_canvas_bbox["w"]
    ), f"W mismatch: {canvas_bbox['w']} vs {expected_canvas_bbox['w']}"
    assert (
        canvas_bbox["h"] == expected_canvas_bbox["h"]
    ), f"H mismatch: {canvas_bbox['h']} vs {expected_canvas_bbox['h']}"

    print("✅ QR bbox mapping test passed!")
    print(f"Input bbox: {test_bbox}")
    print(f"Canvas bbox: {canvas_bbox}")
    print(f"Expected: {expected_canvas_bbox}")

    return True


def test_qr_response_creation():
    """
    Test complete QR response creation with multiple detections
    """
    # Test parameters
    roi = ROIConfig(x=500, y=300, w=400, h=200)
    video_dims = VideoDimensions(width=1920, height=1080)
    canvas_dims = CanvasDimensions(width=960, height=540)

    # Test QR detections
    test_qr_detections = [
        {
            "bbox": {"x": 780, "y": 380, "w": 100, "h": 50},
            "decoded_text": "https://example.com",
            "confidence": 0.95,
        },
        {
            "bbox": {"x": 900, "y": 500, "w": 80, "h": 80},
            "decoded_text": "QR_CODE_123",
            "confidence": 0.88,
        },
    ]

    # Run test
    response = LandmarkMapper.create_canvas_qr_response(
        test_qr_detections, roi, video_dims, canvas_dims
    )

    # Verify response structure
    assert response["success"] == True, "Response should be successful"
    assert "canvas_qr_detections" in response, "Response should contain canvas_qr_detections"
    assert len(response["canvas_qr_detections"]) == 2, "Should have 2 detections"
    assert response["mapping_algorithm"] == "qr_bbox_mapping", "Correct algorithm name"

    # Verify first detection
    first_detection = response["canvas_qr_detections"][0]
    assert "bbox" in first_detection, "Should have original bbox"
    assert "canvas_bbox" in first_detection, "Should have canvas bbox"
    assert first_detection["decoded_text"] == "https://example.com", "Text should match"
    assert first_detection["confidence"] == 0.95, "Confidence should match"

    # Verify coordinate transformation for first detection
    canvas_bbox = first_detection["canvas_bbox"]
    assert canvas_bbox["x"] == 390, f"Canvas X should be 390, got {canvas_bbox['x']}"
    assert canvas_bbox["y"] == 190, f"Canvas Y should be 190, got {canvas_bbox['y']}"

    print("✅ QR response creation test passed!")
    print(f"Response contains {len(response['canvas_qr_detections'])} mapped QR detections")
    print(f"First detection canvas bbox: {first_detection['canvas_bbox']}")

    return True


if __name__ == "__main__":
    # Run verification tests
    print("Running coordinate mapping tests...\n")

    # Test hand landmark mapping
    test_coordinate_mapping()
    print()

    # Test QR bbox mapping
    test_qr_bbox_mapping()
    print()

    # Test QR response creation
    test_qr_response_creation()
    print()

    # Test fixed sizes
    sizes = LandmarkMapper.get_fixed_sizes()
    print(f"Fixed landmark sizes: {sizes}")

    print("\n✅ All tests passed! QR coordinate mapping is ready.")
