/**
 * useLandmarkMapper Hook
 * React hook for coordinate mapping with fixed sizing for hand landmarks
 * Implements the requested algorithm with 3px radius and 2px line width
 */

import { useCallback, useMemo } from 'react';

// Fixed rendering sizes as per requirements
const FIXED_SIZES = {
  landmarkRadius: 3,  // Fixed 3px radius
  lineWidth: 2        // Fixed 2px line width
};

/**
 * Hand connections for drawing skeleton
 * MediaPipe hand landmark connections
 */
const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4], // Thumb
  [0, 5], [5, 6], [6, 7], [7, 8], // Index finger
  [0, 9], [9, 10], [10, 11], [11, 12], // Middle finger
  [0, 13], [13, 14], [14, 15], [15, 16], // Ring finger
  [0, 17], [17, 18], [18, 19], [19, 20], // Pinky
  [5, 9], [9, 13], [13, 17] // Palm connections
];

/**
 * Validate input parameters for coordinate mapping
 * @param {Object} roi - ROI configuration {x, y, w, h}
 * @param {Object} videoDims - Video dimensions {width, height}
 * @param {Object} canvasDims - Canvas dimensions {width, height}
 * @returns {boolean} True if valid
 */
const validateInputs = (roi, videoDims, canvasDims) => {
  // Check ROI
  if (!roi || typeof roi.x !== 'number' || typeof roi.y !== 'number' || 
      typeof roi.w !== 'number' || typeof roi.h !== 'number') {
    console.error('Invalid ROI configuration');
    return false;
  }

  if (roi.w <= 0 || roi.h <= 0 || roi.x < 0 || roi.y < 0) {
    console.error('ROI dimensions must be positive and coordinates non-negative');
    return false;
  }

  // Check video dimensions
  if (!videoDims || videoDims.width <= 0 || videoDims.height <= 0) {
    console.error('Invalid video dimensions');
    return false;
  }

  // Check canvas dimensions
  if (!canvasDims || canvasDims.width <= 0 || canvasDims.height <= 0) {
    console.error('Invalid canvas dimensions');
    return false;
  }

  // Check ROI bounds within video
  if (roi.x + roi.w > videoDims.width || roi.y + roi.h > videoDims.height) {
    console.error('ROI extends beyond video bounds');
    return false;
  }

  // Warn about aspect ratio mismatch
  const videoAspect = videoDims.width / videoDims.height;
  const canvasAspect = canvasDims.width / canvasDims.height;
  const aspectDiff = Math.abs(videoAspect - canvasAspect);
  
  if (aspectDiff > 0.1) {
    console.warn(`Aspect ratio mismatch: Video ${videoAspect.toFixed(3)} vs Canvas ${canvasAspect.toFixed(3)}`);
  }

  return true;
};

/**
 * Map single normalized point to display coordinates
 * Implements the exact requested algorithm
 * @param {number} xRel - Normalized x coordinate [0,1] within ROI
 * @param {number} yRel - Normalized y coordinate [0,1] within ROI
 * @param {Object} roi - ROI configuration {x, y, w, h}
 * @param {Object} videoDims - Video dimensions {width, height}
 * @param {Object} canvasDims - Canvas dimensions {width, height}
 * @returns {Object} {x, y} display coordinates
 */
const mapSinglePoint = (xRel, yRel, roi, videoDims, canvasDims) => {
  // Warn if normalized coordinates are out of range
  if (xRel < 0 || xRel > 1 || yRel < 0 || yRel > 1) {
    console.warn(`Normalized coordinates out of range: (${xRel.toFixed(3)}, ${yRel.toFixed(3)})`);
  }

  // Step 1 & 2: Convert ROI-relative to absolute video coordinates
  const xOrig = roi.x + (xRel * roi.w);
  const yOrig = roi.y + (yRel * roi.h);

  // Step 3 & 4: Convert to display coordinates
  const xDisp = xOrig * (canvasDims.width / videoDims.width);
  const yDisp = yOrig * (canvasDims.height / videoDims.height);

  return { x: xDisp, y: yDisp };
};

/**
 * useLandmarkMapper Hook
 * @returns {Object} Hook interface with mapping functions and utilities
 */
const useLandmarkMapper = () => {
  /**
   * Get fixed landmark rendering sizes
   * @returns {Object} {landmarkRadius: 3, lineWidth: 2}
   */
  const getFixedSizes = useCallback(() => {
    return { ...FIXED_SIZES };
  }, []);

  /**
   * Get hand connection indices for drawing skeleton
   * @returns {Array} Array of [startIdx, endIdx] connections
   */
  const getHandConnections = useCallback(() => {
    return [...HAND_CONNECTIONS];
  }, []);

  /**
   * Map landmarks from normalized coordinates to display coordinates
   * @param {Array} landmarks - Array of hands, each hand is array of landmarks
   *                           Each landmark: {x, y, z} normalized [0,1]
   * @param {Object} roi - ROI configuration {x, y, w, h}
   * @param {Object} videoDims - Video dimensions {width, height}
   * @param {Object} canvasDims - Canvas dimensions {width, height}
   * @returns {Array} Mapped landmarks with display coordinates and fixed sizes
   */
  const mapLandmarks = useCallback((landmarks, roi, videoDims, canvasDims) => {
    // Validate inputs
    if (!validateInputs(roi, videoDims, canvasDims)) {
      return [];
    }

    if (!Array.isArray(landmarks)) {
      console.error('Landmarks must be an array');
      return [];
    }

    const mappedHands = [];

    landmarks.forEach((hand, handIdx) => {
      if (!Array.isArray(hand)) {
        console.error(`Hand ${handIdx} must be an array`);
        return;
      }

      const mappedHand = [];

      hand.forEach((landmark, landmarkIdx) => {
        try {
          // Extract normalized coordinates
          const xRel = parseFloat(landmark.x || 0);
          const yRel = parseFloat(landmark.y || 0);
          const z = parseFloat(landmark.z || 0);

          // Apply coordinate mapping algorithm
          const xOrig = roi.x + (xRel * roi.w);
          const yOrig = roi.y + (yRel * roi.h);
          
          const xDisp = xOrig * (canvasDims.width / videoDims.width);
          const yDisp = yOrig * (canvasDims.height / videoDims.height);

          // Create mapped landmark with fixed sizing
          const mappedLandmark = {
            // Original normalized coordinates
            xRel,
            yRel,
            z,
            // Absolute pixel coordinates in original video
            xOrig,
            yOrig,
            // Display coordinates for canvas rendering
            xDisp,
            yDisp,
            // Fixed rendering properties
            radius: FIXED_SIZES.landmarkRadius,
            lineWidth: FIXED_SIZES.lineWidth
          };

          mappedHand.push(mappedLandmark);

          // Debug logging for first landmark of first hand
          if (handIdx === 0 && landmarkIdx === 0) {
            console.log('🔧 Fixed-Size Landmark Mapping (Frontend):', {
              'Input': `(${xRel.toFixed(3)}, ${yRel.toFixed(3)}) normalized`,
              'ROI': `x=${roi.x}, y=${roi.y}, w=${roi.w}, h=${roi.h}`,
              'Video': `${videoDims.width}x${videoDims.height}`,
              'Canvas': `${canvasDims.width}x${canvasDims.height}`,
              'Result': `(${xDisp.toFixed(1)}, ${yDisp.toFixed(1)}) display coords`,
              'Fixed sizes': `radius=${FIXED_SIZES.landmarkRadius}px, line=${FIXED_SIZES.lineWidth}px`
            });
          }

        } catch (error) {
          console.error(`Error mapping landmark ${landmarkIdx} of hand ${handIdx}:`, error);
        }
      });

      if (mappedHand.length > 0) {
        mappedHands.push(mappedHand);
      }
    });

    console.info(`Mapped ${mappedHands.length} hands with fixed ${FIXED_SIZES.landmarkRadius}px landmarks`);
    return mappedHands;
  }, []);

  /**
   * Create canvas landmarks response compatible with backend format
   * @param {Array} landmarks - Raw MediaPipe landmarks
   * @param {Object} roi - ROI configuration
   * @param {Object} videoDims - Video dimensions
   * @param {Object} canvasDims - Canvas dimensions
   * @returns {Object} Complete response with canvas_landmarks field
   */
  const createCanvasLandmarksResponse = useCallback((landmarks, roi, videoDims, canvasDims) => {
    try {
      const mappedLandmarks = mapLandmarks(landmarks, roi, videoDims, canvasDims);
      
      // Convert to serializable format matching backend response
      const canvasLandmarks = mappedLandmarks.map(hand => 
        hand.map(landmark => ({
          x_rel: landmark.xRel,
          y_rel: landmark.yRel,
          z: landmark.z,
          x_orig: landmark.xOrig,
          y_orig: landmark.yOrig,
          x_disp: landmark.xDisp,
          y_disp: landmark.yDisp,
          radius: landmark.radius,
          line_width: landmark.lineWidth
        }))
      );

      return {
        success: true,
        canvas_landmarks: canvasLandmarks,
        fixed_sizes: getFixedSizes(),
        mapping_info: {
          algorithm: 'fixed_size_mapping',
          roi: { x: roi.x, y: roi.y, w: roi.w, h: roi.h },
          video_dims: { width: videoDims.width, height: videoDims.height },
          canvas_dims: { width: canvasDims.width, height: canvasDims.height },
          landmark_radius: FIXED_SIZES.landmarkRadius,
          line_width: FIXED_SIZES.lineWidth
        }
      };

    } catch (error) {
      console.error('Error creating canvas landmarks response:', error);
      return {
        success: false,
        error: error.message,
        canvas_landmarks: [],
        fixed_sizes: getFixedSizes()
      };
    }
  }, [mapLandmarks, getFixedSizes]);

  /**
   * Verify coordinate mapping accuracy
   * Test case: ROI (500,300,400,200) in 1920x1080 video, Canvas 960x540
   * Input (0.7, 0.4) should map to (390, 190)
   * @returns {boolean} True if test passes
   */
  const verifyCoordinateMapping = useCallback(() => {
    try {
      // Test parameters
      const roi = { x: 500, y: 300, w: 400, h: 200 };
      const videoDims = { width: 1920, height: 1080 };
      const canvasDims = { width: 960, height: 540 };
      
      const xRel = 0.7;
      const yRel = 0.4;
      
      // Expected results
      // xOrig = 500 + (0.7 × 400) = 780
      // yOrig = 300 + (0.4 × 200) = 380  
      // xDisp = 780 × (960 / 1920) = 390
      // yDisp = 380 × (540 / 1080) = 190
      const expectedXDisp = 390.0;
      const expectedYDisp = 190.0;
      
      // Run test
      const result = mapSinglePoint(xRel, yRel, roi, videoDims, canvasDims);
      
      // Verify results
      const xError = Math.abs(result.x - expectedXDisp);
      const yError = Math.abs(result.y - expectedYDisp);
      
      if (xError < 0.001 && yError < 0.001) {
        console.log('✅ Coordinate mapping verification passed!');
        console.log(`Input: (${xRel}, ${yRel}) → Output: (${result.x}, ${result.y})`);
        console.log(`Expected: (${expectedXDisp}, ${expectedYDisp})`);
        return true;
      } else {
        console.error('❌ Coordinate mapping verification failed!');
        console.error(`Expected: (${expectedXDisp}, ${expectedYDisp})`);
        console.error(`Got: (${result.x}, ${result.y})`);
        return false;
      }
      
    } catch (error) {
      console.error('Coordinate mapping verification error:', error);
      return false;
    }
  }, []);

  // Memoize the hook interface
  const hookInterface = useMemo(() => ({
    // Core mapping functions
    mapLandmarks,
    mapSinglePoint: (xRel, yRel, roi, videoDims, canvasDims) => 
      mapSinglePoint(xRel, yRel, roi, videoDims, canvasDims),
    
    // Utility functions
    getFixedSizes,
    getHandConnections,
    
    // Advanced functions
    createCanvasLandmarksResponse,
    verifyCoordinateMapping,
    
    // Constants
    FIXED_SIZES,
    HAND_CONNECTIONS
  }), [
    mapLandmarks, 
    getFixedSizes, 
    getHandConnections, 
    createCanvasLandmarksResponse, 
    verifyCoordinateMapping
  ]);

  return hookInterface;
};

export default useLandmarkMapper;