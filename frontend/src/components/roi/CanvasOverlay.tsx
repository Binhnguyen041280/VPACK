/**
 * CanvasOverlay Component for ROI Drawing
 * Interactive HTML5 Canvas overlay for drawing ROI rectangles over video
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Box, useColorModeValue } from '@chakra-ui/react';

// ROI data interface
export interface ROIData {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
  type: 'packing_area' | 'qr_mvd' | 'qr_trigger' | 'detection';
  label: string;
  color: string;
  completed: boolean;
}

// Drawing state interface
interface DrawingState {
  isDrawing: boolean;
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
  previewROI: ROIData | null;
}

// Hand landmarks interface with TC Gốc coordinates
interface HandLandmarks {
  landmarks: Array<Array<{
    x: number;        // ROI-relative coordinates [0,1]
    y: number;
    z: number;
    x_orig: number;   // TC Gốc - pixel thực trong video gốc
    y_orig: number;   // TC Gốc - pixel thực trong video gốc  
    x_norm: number;   // Reference normalized coordinates [0,1]
    y_norm: number;   // Reference normalized coordinates [0,1]
  }>>;
  confidence: number;
  hands_detected: number;
}

// Component props interface
interface CanvasOverlayProps {
  width: number;
  height: number;
  videoWidth: number;
  videoHeight: number;
  rois: ROIData[];
  onROICreate?: (roi: Omit<ROIData, 'id'>) => void;
  onROIUpdate?: (id: string, roi: Partial<ROIData>) => void;
  onROIDelete?: (id: string) => void;
  onROISelect?: (id: string | null) => void;
  selectedROIId?: string | null;
  currentROIType?: ROIData['type'];
  currentROILabel?: string;
  packingMethod?: 'traditional' | 'qr';
  disabled?: boolean;
  className?: string;
  minROISize?: number;
  gridSnap?: boolean;
  snapSize?: number;
  // Hand landmarks props
  handLandmarks?: HandLandmarks | null;
  showHandLandmarks?: boolean;
  landmarksColor?: string;
  landmarksSize?: number;
}

// Default colors for different ROI types
const ROI_TYPE_COLORS: Record<ROIData['type'], string> = {
  packing_area: '#38A169',   // Green (changed from yellow)
  qr_mvd: '#3182CE',         // Blue  
  qr_trigger: '#E53E3E',     // Red
  detection: '#9F7AEA'       // Purple
};

const CanvasOverlay: React.FC<CanvasOverlayProps> = ({
  width,
  height,
  videoWidth,
  videoHeight,
  rois,
  onROICreate,
  onROIUpdate,
  onROIDelete,
  onROISelect,
  selectedROIId,
  currentROIType = 'packing_area',
  currentROILabel = 'ROI',
  packingMethod = 'traditional',
  disabled = false,
  className,
  minROISize = 20,
  gridSnap = false,
  snapSize = 10,
  // Hand landmarks props with defaults
  handLandmarks = null,
  showHandLandmarks = true,
  landmarksColor = '#00FF00',
  landmarksSize = 4
}) => {
  // Refs
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const contextRef = useRef<CanvasRenderingContext2D | null>(null);

  // State
  const [drawingState, setDrawingState] = useState<DrawingState>({
    isDrawing: false,
    startX: 0,
    startY: 0,
    currentX: 0,
    currentY: 0,
    previewROI: null
  });

  const [hoveredROIId, setHoveredROIId] = useState<string | null>(null);
  const [dragState, setDragState] = useState<{
    isDragging: boolean;
    roiId: string;
    startX: number;
    startY: number;
    originalROI: ROIData | null;
  }>({
    isDragging: false,
    roiId: '',
    startX: 0,
    startY: 0,
    originalROI: null
  });

  // Theme colors
  const overlayBg = useColorModeValue('rgba(255,255,255,0.1)', 'rgba(0,0,0,0.1)');
  
  // Coordinate conversion helpers
  const canvasToVideo = useCallback((x: number, y: number) => {
    const scaleX = videoWidth / width;
    const scaleY = videoHeight / height;
    return {
      x: Math.round(x * scaleX),
      y: Math.round(y * scaleY)
    };
  }, [videoWidth, videoHeight, width, height]);

  const videoToCanvas = useCallback((x: number, y: number) => {
    const scaleX = width / videoWidth;
    const scaleY = height / videoHeight;
    return {
      x: x * scaleX,
      y: y * scaleY
    };
  }, [videoWidth, videoHeight, width, height]);

  // Snap to grid helper
  const snapToGrid = useCallback((value: number): number => {
    if (!gridSnap) return value;
    return Math.round(value / snapSize) * snapSize;
  }, [gridSnap, snapSize]);

  // Initialize canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    canvas.width = width;
    canvas.height = height;

    const context = canvas.getContext('2d');
    if (!context) return;

    // Configure context
    context.lineCap = 'round';
    context.lineJoin = 'round';
    context.imageSmoothingEnabled = true;

    contextRef.current = context;
  }, [width, height]);

  // Draw ROIs on canvas
  const drawROIs = useCallback(() => {
    const context = contextRef.current;
    if (!context) return;

    // Clear canvas before drawing
    context.clearRect(0, 0, width, height);

    // Draw existing ROIs
    rois.forEach((roi) => {
      const canvasPos = videoToCanvas(roi.x, roi.y);
      const canvasSize = videoToCanvas(roi.w, roi.h);
      
      const isSelected = selectedROIId === roi.id;
      const isHovered = hoveredROIId === roi.id;
      
      // ROI rectangle
      context.strokeStyle = roi.color || ROI_TYPE_COLORS[roi.type];
      context.lineWidth = isSelected ? 3 : (isHovered ? 2 : 1);
      context.setLineDash(roi.completed ? [] : [5, 5]);
      
      context.strokeRect(canvasPos.x, canvasPos.y, canvasSize.x, canvasSize.y);
      
      // Fill with transparency
      context.fillStyle = `${roi.color || ROI_TYPE_COLORS[roi.type]}20`;
      context.fillRect(canvasPos.x, canvasPos.y, canvasSize.x, canvasSize.y);
      
      // Label
      context.fillStyle = roi.color || ROI_TYPE_COLORS[roi.type];
      context.font = '12px Arial';
      context.fillText(
        roi.label, 
        canvasPos.x + 4, 
        canvasPos.y - 4
      );
      
      // Selection handles for selected ROI
      if (isSelected) {
        const handleSize = 6;
        const handles = [
          // Top-left
          { x: canvasPos.x - handleSize/2, y: canvasPos.y - handleSize/2 },
          // Top-right
          { x: canvasPos.x + canvasSize.x - handleSize/2, y: canvasPos.y - handleSize/2 },
          // Bottom-left
          { x: canvasPos.x - handleSize/2, y: canvasPos.y + canvasSize.y - handleSize/2 },
          // Bottom-right
          { x: canvasPos.x + canvasSize.x - handleSize/2, y: canvasPos.y + canvasSize.y - handleSize/2 }
        ];
        
        context.fillStyle = '#FFFFFF';
        context.strokeStyle = roi.color || ROI_TYPE_COLORS[roi.type];
        context.lineWidth = 2;
        context.setLineDash([]);
        
        handles.forEach(handle => {
          context.fillRect(handle.x, handle.y, handleSize, handleSize);
          context.strokeRect(handle.x, handle.y, handleSize, handleSize);
        });
      }
    });

    // Draw preview ROI while drawing
    if (drawingState.previewROI) {
      const roi = drawingState.previewROI;
      const canvasPos = videoToCanvas(roi.x, roi.y);
      const canvasSize = videoToCanvas(roi.w, roi.h);
      
      context.strokeStyle = roi.color;
      context.lineWidth = 2;
      context.setLineDash([3, 3]);
      context.strokeRect(canvasPos.x, canvasPos.y, canvasSize.x, canvasSize.y);
      
      context.fillStyle = `${roi.color}15`;
      context.fillRect(canvasPos.x, canvasPos.y, canvasSize.x, canvasSize.y);
      
      // Label
      context.fillStyle = roi.color;
      context.font = '12px Arial';
      context.setLineDash([]);
      context.fillText(
        roi.label + ' (Preview)', 
        canvasPos.x + 4, 
        canvasPos.y - 4
      );
    }
  }, [
    width, 
    height, 
    rois, 
    selectedROIId, 
    hoveredROIId, 
    drawingState.previewROI, 
    videoToCanvas
  ]);

  // Calculate dynamic sizes based on video/canvas scale - 2D scaling approach
  const calculateDynamicSizes = useCallback(() => {
    const scaleX = width / videoWidth;     // Scale factor cho X axis
    const scaleY = height / videoHeight;   // Scale factor cho Y axis
    const averageScale = (scaleX + scaleY) / 2;  // Average scale cho uniform sizing
    
    // Base size proportional to video resolution - điều chỉnh về kích thước nhỏ hơn
    const baseSize = Math.max(videoWidth, videoHeight) / 400;  // Trở lại 400 như ban đầu
    
    // Sử dụng average scale để giữ landmarks circular (không méo)
    const calculatedSize = Math.max(2, Math.round(baseSize * averageScale));  // Minimum 2px
    const calculatedLineWidth = Math.max(1, Math.round(baseSize * averageScale * 0.5));  // Minimum 1px
    
    // Debug logging với thông tin chi tiết hơn
    console.log('Dynamic Size Calculation (2D Scale):', {
      videoSize: `${videoWidth}x${videoHeight}`,
      canvasSize: `${width}x${height}`,
      scaleX: scaleX.toFixed(3),
      scaleY: scaleY.toFixed(3), 
      averageScale: averageScale.toFixed(3),
      baseSize: baseSize.toFixed(1),
      landmarksSize: calculatedSize,
      lineWidth: calculatedLineWidth,
      aspectRatioVideo: (videoWidth / videoHeight).toFixed(2),
      aspectRatioCanvas: (width / height).toFixed(2)
    });
    
    return {
      landmarksSize: calculatedSize,
      lineWidth: calculatedLineWidth,
      scaleX: scaleX,      // Trả về cả 2 scale factors
      scaleY: scaleY       // Để có thể dùng riêng biệt nếu cần
    };
  }, [width, height, videoWidth, videoHeight]);

  // Draw hand landmarks on canvas (after ROIs)
  const drawHandLandmarks = useCallback(() => {
    const context = contextRef.current;
    if (!context || !handLandmarks || !showHandLandmarks) return;

    const { landmarks, confidence } = handLandmarks;
    const { landmarksSize: dynamicLandmarksSize, lineWidth: dynamicLineWidth } = calculateDynamicSizes();
    
    // Draw each hand
    landmarks.forEach((hand, handIndex) => {
      if (!hand || hand.length === 0) return;

      // Set drawing styles based on confidence
      const alpha = Math.max(0.5, confidence);
      const color = confidence > 0.7 ? landmarksColor : '#FFAA00';
      
      context.fillStyle = color;
      context.strokeStyle = color;
      context.globalAlpha = alpha;
      context.lineWidth = dynamicLineWidth;

      // Draw landmark points using TC Gốc coordinate transform
      hand.forEach((landmark, idx) => {
        // Step 3: Convert TC Gốc (pixel thực) → TCFE (canvas display)
        const canvasX = (landmark.x_orig / videoWidth) * width;
        const canvasY = (landmark.y_orig / videoHeight) * height;
        
        // Debug logging for first landmark of first hand
        if (handIndex === 0 && idx === 0) {
          console.log('🔍 COORDINATE VERIFICATION:', {
            'Step 1 - Original video pixel': `${landmark.x_orig}, ${landmark.y_orig}`,
            'Step 2 - Canvas transform': `${canvasX.toFixed(1)}, ${canvasY.toFixed(1)}`,
            'Step 3 - Reverse check': `${(canvasX/width*videoWidth).toFixed(1)}, ${(canvasY/height*videoHeight).toFixed(1)}`,
            'Video size': `${videoWidth}x${videoHeight}`,
            'Canvas size': `${width}x${height}`,
            'Scale factors': `X=${(width/videoWidth).toFixed(3)}, Y=${(height/videoHeight).toFixed(3)}`,
            'Accuracy check': Math.abs(landmark.x_orig - (canvasX/width*videoWidth)) < 1 ? '✅ ACCURATE' : '❌ ERROR'
          });
        }
        
        context.beginPath();
        context.arc(canvasX, canvasY, dynamicLandmarksSize, 0, 2 * Math.PI);
        context.fill();
      });

      // Draw hand skeleton connections
      const handConnections = [
        [0, 1], [1, 2], [2, 3], [3, 4], // Thumb
        [0, 5], [5, 6], [6, 7], [7, 8], // Index
        [0, 9], [9, 10], [10, 11], [11, 12], // Middle
        [0, 13], [13, 14], [14, 15], [15, 16], // Ring
        [0, 17], [17, 18], [18, 19], [19, 20], // Pinky
        [5, 9], [9, 13], [13, 17] // Palm
      ];

      handConnections.forEach(([startIdx, endIdx]) => {
        if (startIdx < hand.length && endIdx < hand.length) {
          const startPoint = hand[startIdx];
          const endPoint = hand[endIdx];
          
          // Use TC Gốc coordinates for line drawing
          const startX = (startPoint.x_orig / videoWidth) * width;
          const startY = (startPoint.y_orig / videoHeight) * height;
          const endX = (endPoint.x_orig / videoWidth) * width;
          const endY = (endPoint.y_orig / videoHeight) * height;
          
          context.beginPath();
          context.moveTo(startX, startY);
          context.lineTo(endX, endY);
          context.stroke();
        }
      });
    });

    // Reset global alpha
    context.globalAlpha = 1.0;
    
    // Draw confidence indicator at bottom-right
    if (landmarks.length > 0) {
      const indicatorX = width - 160;
      const indicatorY = height - 30;
      
      context.fillStyle = 'rgba(0, 0, 0, 0.7)';
      context.fillRect(indicatorX, indicatorY, 150, 25);
      
      context.fillStyle = landmarksColor;
      context.font = '11px Arial';
      context.fillText(
        `${landmarks.length} hand${landmarks.length > 1 ? 's' : ''} | ${(confidence * 100).toFixed(0)}%`, 
        indicatorX + 5, 
        indicatorY + 16
      );
    }
  }, [handLandmarks, showHandLandmarks, landmarksColor, width, height, calculateDynamicSizes]);

  // Combined redraw function
  const redrawCanvas = useCallback(() => {
    drawROIs(); // This clears canvas and draws ROIs
    if (handLandmarks && showHandLandmarks) {
      drawHandLandmarks(); // Then draw hand landmarks on top
    }
  }, [drawROIs, drawHandLandmarks, handLandmarks, showHandLandmarks]);

  // Redraw canvas when dependencies change
  useEffect(() => {
    redrawCanvas();
  }, [redrawCanvas]);

  // Find ROI at canvas coordinates (prioritize smallest ROI if overlapping)
  const findROIAtPoint = useCallback((x: number, y: number): ROIData | null => {
    const matchingROIs = [];
    
    for (let i = 0; i < rois.length; i++) {
      const roi = rois[i];
      const canvasPos = videoToCanvas(roi.x, roi.y);
      const canvasSize = videoToCanvas(roi.w, roi.h);
      
      if (x >= canvasPos.x && x <= canvasPos.x + canvasSize.x &&
          y >= canvasPos.y && y <= canvasPos.y + canvasSize.y) {
        matchingROIs.push(roi);
      }
    }
    
    if (matchingROIs.length === 0) return null;
    
    // Return the smallest ROI (by area) if multiple matches
    return matchingROIs.reduce((smallest, current) => {
      const smallestArea = smallest.w * smallest.h;
      const currentArea = current.w * current.h;
      return currentArea < smallestArea ? current : smallest;
    });
  }, [rois, videoToCanvas]);

  // Find ROI border at canvas coordinates (for dragging)
  const findROIBorderAtPoint = useCallback((x: number, y: number): ROIData | null => {
    const borderThickness = 8; // pixels
    
    for (let i = rois.length - 1; i >= 0; i--) {
      const roi = rois[i];
      const canvasPos = videoToCanvas(roi.x, roi.y);
      const canvasSize = videoToCanvas(roi.w, roi.h);
      
      // Check if point is within the outer border area
      const outerX1 = canvasPos.x - borderThickness;
      const outerY1 = canvasPos.y - borderThickness;
      const outerX2 = canvasPos.x + canvasSize.x + borderThickness;
      const outerY2 = canvasPos.y + canvasSize.y + borderThickness;
      
      // Check if point is within the inner content area
      const innerX1 = canvasPos.x + borderThickness;
      const innerY1 = canvasPos.y + borderThickness;
      const innerX2 = canvasPos.x + canvasSize.x - borderThickness;
      const innerY2 = canvasPos.y + canvasSize.y - borderThickness;
      
      // Point is on border if it's in the outer area but not in the inner area
      const inOuter = x >= outerX1 && x <= outerX2 && y >= outerY1 && y <= outerY2;
      const inInner = x >= innerX1 && x <= innerX2 && y >= innerY1 && y <= innerY2;
      
      if (inOuter && !inInner) {
        return roi;
      }
    }
    return null;
  }, [rois, videoToCanvas]);

  // Mouse event handlers
  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (disabled) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Check if clicking on ROI border (for dragging)
    const borderROI = findROIBorderAtPoint(x, y);
    
    if (borderROI) {
      // Select existing ROI and start drag operation
      onROISelect?.(borderROI.id);
      
      setDragState({
        isDragging: true,
        roiId: borderROI.id,
        startX: x,
        startY: y,
        originalROI: borderROI
      });
      
      return;
    }

    // Check if clicking inside an ROI (for selection only, no dragging)
    const clickedROI = findROIAtPoint(x, y);
    if (clickedROI) {
      // Only select the ROI, don't start dragging
      onROISelect?.(clickedROI.id);
      return;
    }

    // Start drawing new ROI
    onROISelect?.(null);
    
    const snappedX = snapToGrid(x);
    const snappedY = snapToGrid(y);
    
    setDrawingState({
      isDrawing: true,
      startX: snappedX,
      startY: snappedY,
      currentX: snappedX,
      currentY: snappedY,
      previewROI: null
    });
  }, [disabled, findROIAtPoint, findROIBorderAtPoint, onROISelect, snapToGrid]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (disabled) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Handle drag operation
    if (dragState.isDragging && dragState.originalROI) {
      const deltaX = x - dragState.startX;
      const deltaY = y - dragState.startY;
      
      const videoDelta = canvasToVideo(deltaX, deltaY);
      
      const newX = Math.max(0, Math.min(
        videoWidth - dragState.originalROI.w,
        dragState.originalROI.x + videoDelta.x
      ));
      
      const newY = Math.max(0, Math.min(
        videoHeight - dragState.originalROI.h,
        dragState.originalROI.y + videoDelta.y
      ));
      
      onROIUpdate?.(dragState.roiId, { x: newX, y: newY });
      return;
    }

    // Handle drawing new ROI
    if (drawingState.isDrawing) {
      const snappedX = snapToGrid(x);
      const snappedY = snapToGrid(y);
      
      const startX = Math.min(drawingState.startX, snappedX);
      const startY = Math.min(drawingState.startY, snappedY);
      const endX = Math.max(drawingState.startX, snappedX);
      const endY = Math.max(drawingState.startY, snappedY);
      
      const w = endX - startX;
      const h = endY - startY;
      
      if (w > minROISize && h > minROISize) {
        const videoCoords = canvasToVideo(startX, startY);
        const videoSize = canvasToVideo(w, h);
        
        const previewROI: ROIData = {
          id: 'preview',
          x: videoCoords.x,
          y: videoCoords.y,
          w: videoSize.x,
          h: videoSize.y,
          type: currentROIType,
          label: currentROILabel,
          color: ROI_TYPE_COLORS[currentROIType],
          completed: false
        };
        
        setDrawingState(prev => ({
          ...prev,
          currentX: snappedX,
          currentY: snappedY,
          previewROI
        }));
      }
      return;
    }

    // Handle hover effects
    const borderROI = findROIBorderAtPoint(x, y);
    const contentROI = findROIAtPoint(x, y);
    
    setHoveredROIId(borderROI?.id || contentROI?.id || null);
    
    // Update cursor based on location
    if (borderROI) {
      canvas.style.cursor = 'move';
    } else if (contentROI) {
      canvas.style.cursor = 'pointer';
    } else {
      canvas.style.cursor = 'crosshair';
    }
  }, [
    disabled,
    dragState,
    drawingState,
    onROIUpdate,
    canvasToVideo,
    videoWidth,
    videoHeight,
    snapToGrid,
    minROISize,
    currentROIType,
    currentROILabel,
    findROIAtPoint,
    findROIBorderAtPoint
  ]);

  const handleMouseUp = useCallback(() => {
    if (disabled) return;

    // End drag operation
    if (dragState.isDragging) {
      setDragState({
        isDragging: false,
        roiId: '',
        startX: 0,
        startY: 0,
        originalROI: null
      });
      return;
    }

    // Complete drawing new ROI
    if (drawingState.isDrawing && drawingState.previewROI) {
      const roi = drawingState.previewROI;
      
      // Validate ROI is within bounds and meets minimum size
      if (roi.w >= minROISize && roi.h >= minROISize &&
          roi.x >= 0 && roi.y >= 0 &&
          roi.x + roi.w <= videoWidth &&
          roi.y + roi.h <= videoHeight) {
        
        onROICreate?.({
          x: roi.x,
          y: roi.y,
          w: roi.w,
          h: roi.h,
          type: roi.type,
          label: roi.label,
          color: roi.color,
          completed: true
        });
      }
    }

    // Reset drawing state
    setDrawingState({
      isDrawing: false,
      startX: 0,
      startY: 0,
      currentX: 0,
      currentY: 0,
      previewROI: null
    });
  }, [
    disabled,
    dragState,
    drawingState,
    onROICreate,
    minROISize,
    videoWidth,
    videoHeight
  ]);

  const handleMouseLeave = useCallback(() => {
    setHoveredROIId(null);
    
    // Cancel drawing if in progress
    if (drawingState.isDrawing) {
      setDrawingState({
        isDrawing: false,
        startX: 0,
        startY: 0,
        currentX: 0,
        currentY: 0,
        previewROI: null
      });
    }
    
    // Cancel drag if in progress
    if (dragState.isDragging) {
      setDragState({
        isDragging: false,
        roiId: '',
        startX: 0,
        startY: 0,
        originalROI: null
      });
    }
  }, [drawingState.isDrawing, dragState.isDragging]);

  // Handle double-click for ROI deletion
  const handleDoubleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (disabled) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const clickedROI = findROIAtPoint(x, y);
    if (clickedROI) {
      onROIDelete?.(clickedROI.id);
    }
  }, [disabled, findROIAtPoint, onROIDelete]);

  return (
    <Box
      position="absolute"
      top="0"
      left="0"
      width={`${width}px`}
      height={`${height}px`}
      className={className}
      bg={overlayBg}
      cursor={disabled ? 'not-allowed' : 'crosshair'}
      pointerEvents={disabled ? 'none' : 'auto'}
    >
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        onDoubleClick={handleDoubleClick}
        style={{
          width: '100%',
          height: '100%',
          display: 'block'
        }}
      />
    </Box>
  );
};

// Export interfaces for use in other components
export type { HandLandmarks };

export default CanvasOverlay;