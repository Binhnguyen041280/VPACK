/**
 * LandmarkCanvas Component
 * React component for rendering hand landmarks with fixed sizing
 * Features: 3px landmark circles, 2px skeleton lines, multi-hand support
 */

import React, { useRef, useEffect, useCallback, useMemo } from 'react';
import { Box } from '@chakra-ui/react';
import useLandmarkMapper from '../../hooks/useLandmarkMapper';

/**
 * LandmarkCanvas Component Props
 */
const LandmarkCanvas = ({
  // Canvas dimensions
  width = 960,
  height = 540,
  
  // Video dimensions for coordinate mapping
  videoWidth = 1920,
  videoHeight = 1080,
  
  // Hand landmarks data
  landmarks = null, // Array of hands with normalized coordinates
  canvasLandmarks = null, // Pre-mapped canvas landmarks from backend
  
  // ROI configuration for coordinate mapping
  roi = null, // {x, y, w, h} in video coordinates
  
  // Display options
  showLandmarks = true,
  showSkeleton = true,
  showConfidence = true,
  
  // Styling options
  landmarkColor = '#00FF00',
  skeletonColor = '#00FF00',
  confidenceThreshold = 0.5,
  
  // Optional confidence data
  confidence = 1.0,
  handsDetected = 0,
  
  // Callback for errors
  onError = null,
  
  // CSS class and styling
  className = '',
  style = {}
}) => {
  // Refs
  const canvasRef = useRef(null);
  const contextRef = useRef(null);
  
  // Hook for coordinate mapping
  const landmarkMapper = useLandmarkMapper();
  
  // Get fixed sizes and hand connections
  const { landmarkRadius, lineWidth } = landmarkMapper.getFixedSizes();
  const handConnections = landmarkMapper.getHandConnections();
  
  // Initialize canvas context
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    canvas.width = width;
    canvas.height = height;

    const context = canvas.getContext('2d');
    if (!context) {
      onError?.('Cannot get canvas 2D context');
      return;
    }

    // Configure context for optimal rendering
    context.lineCap = 'round';
    context.lineJoin = 'round';
    context.imageSmoothingEnabled = true;
    
    contextRef.current = context;
  }, [width, height, onError]);

  // Process landmarks data - use canvas_landmarks if available, otherwise map regular landmarks
  const processedLandmarks = useMemo(() => {
    if (!showLandmarks) return [];

    // Warn about hardcoded video dimensions
    if (videoWidth === 1920 && videoHeight === 1080) {
      console.warn('⚠️  LandmarkCanvas using hardcoded video dimensions (1920x1080). ' +
                   'Pass actual video dimensions for accurate coordinate mapping.');
    }

    // Priority 1: Use pre-mapped canvas landmarks from backend
    if (canvasLandmarks && Array.isArray(canvasLandmarks)) {
      console.log('🎯 Using pre-mapped canvas landmarks from backend');
      return canvasLandmarks.map(hand =>
        hand.map(landmark => ({
          x: landmark.x_disp || landmark.xDisp || 0,
          y: landmark.y_disp || landmark.yDisp || 0,
          z: landmark.z || 0,
          radius: landmark.radius || landmarkRadius,
          lineWidth: landmark.line_width || landmark.lineWidth || lineWidth
        }))
      );
    }

    // Priority 2: Map regular landmarks using coordinate mapping
    if (landmarks && Array.isArray(landmarks) && roi) {
      console.log('🔧 Mapping landmarks using coordinate transformation');
      try {
        const videoDims = { width: videoWidth, height: videoHeight };
        const canvasDims = { width, height };
        
        const mappedLandmarks = landmarkMapper.mapLandmarks(
          landmarks, roi, videoDims, canvasDims
        );
        
        return mappedLandmarks.map(hand =>
          hand.map(landmark => ({
            x: landmark.xDisp,
            y: landmark.yDisp,
            z: landmark.z,
            radius: landmark.radius,
            lineWidth: landmark.lineWidth
          }))
        );
      } catch (error) {
        console.error('Error mapping landmarks:', error);
        onError?.(error.message);
        return [];
      }
    }

    // No valid landmarks data
    return [];
  }, [
    canvasLandmarks, 
    landmarks, 
    roi, 
    videoWidth, 
    videoHeight, 
    width, 
    height, 
    landmarkMapper, 
    landmarkRadius, 
    lineWidth, 
    showLandmarks, 
    onError
  ]);

  // Draw landmarks on canvas
  const drawLandmarks = useCallback(() => {
    const context = contextRef.current;
    if (!context || !showLandmarks) return;

    // Clear canvas
    context.clearRect(0, 0, width, height);

    if (processedLandmarks.length === 0) return;

    // Set drawing styles
    const alpha = Math.max(0.5, confidence);
    const effectiveColor = confidence > confidenceThreshold ? landmarkColor : '#FFAA00';
    
    context.fillStyle = effectiveColor;
    context.strokeStyle = skeletonColor;
    context.globalAlpha = alpha;
    context.lineWidth = lineWidth;

    // Draw each hand
    processedLandmarks.forEach((hand, handIndex) => {
      if (!hand || hand.length === 0) return;

      // Draw landmark points (fixed 3px radius)
      hand.forEach((landmark, idx) => {
        if (typeof landmark.x !== 'number' || typeof landmark.y !== 'number') {
          console.warn(`Invalid landmark coordinates at hand ${handIndex}, point ${idx}`);
          return;
        }

        context.beginPath();
        context.arc(
          landmark.x, 
          landmark.y, 
          landmark.radius || landmarkRadius, 
          0, 
          2 * Math.PI
        );
        context.fill();
      });

      // Draw skeleton connections (fixed 2px lines) if enabled
      if (showSkeleton && handConnections) {
        handConnections.forEach(([startIdx, endIdx]) => {
          if (startIdx < hand.length && endIdx < hand.length) {
            const startPoint = hand[startIdx];
            const endPoint = hand[endIdx];
            
            if (startPoint && endPoint &&
                typeof startPoint.x === 'number' && typeof startPoint.y === 'number' &&
                typeof endPoint.x === 'number' && typeof endPoint.y === 'number') {
              
              context.beginPath();
              context.moveTo(startPoint.x, startPoint.y);
              context.lineTo(endPoint.x, endPoint.y);
              context.stroke();
            }
          }
        });
      }
    });

    // Reset global alpha
    context.globalAlpha = 1.0;

    // Draw confidence indicator if enabled
    if (showConfidence && processedLandmarks.length > 0) {
      const indicatorX = width - 160;
      const indicatorY = height - 30;
      
      // Background
      context.fillStyle = 'rgba(0, 0, 0, 0.7)';
      context.fillRect(indicatorX, indicatorY, 150, 25);
      
      // Text
      context.fillStyle = landmarkColor;
      context.font = '11px Arial';
      const handsCount = handsDetected || processedLandmarks.length;
      context.fillText(
        `${handsCount} hand${handsCount !== 1 ? 's' : ''} | ${(confidence * 100).toFixed(0)}%`, 
        indicatorX + 5, 
        indicatorY + 16
      );
    }

  }, [
    processedLandmarks,
    width,
    height,
    confidence,
    confidenceThreshold,
    landmarkColor,
    skeletonColor,
    landmarkRadius,
    lineWidth,
    handConnections,
    showLandmarks,
    showSkeleton,
    showConfidence,
    handsDetected
  ]);

  // Redraw when landmarks or settings change
  useEffect(() => {
    drawLandmarks();
  }, [drawLandmarks]);

  // Render canvas with Chakra UI Box wrapper
  return (
    <Box
      position="absolute"
      top="0"
      left="0"
      width={`${width}px`}
      height={`${height}px`}
      className={className}
      style={style}
      pointerEvents="none" // Allow clicks to pass through to underlying video
    >
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        style={{
          width: '100%',
          height: '100%',
          display: 'block'
        }}
      />
    </Box>
  );
};

// Component prop types for development
LandmarkCanvas.defaultProps = {
  width: 960,
  height: 540,
  videoWidth: 1920,  // Default fallback - should be overridden with actual video dimensions
  videoHeight: 1080, // Default fallback - should be overridden with actual video dimensions
  landmarks: null,
  canvasLandmarks: null,
  roi: null,
  showLandmarks: true,
  showSkeleton: true,
  showConfidence: true,
  landmarkColor: '#00FF00',
  skeletonColor: '#00FF00',
  confidenceThreshold: 0.5,
  confidence: 1.0,
  handsDetected: 0,
  onError: null,
  className: '',
  style: {}
};

export default LandmarkCanvas;