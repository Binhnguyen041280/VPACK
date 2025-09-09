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

// QR detection interface for integrated display
export interface QRDetection {
  bbox: {x: number, y: number, w: number, h: number};         // Original video coordinates
  canvas_bbox: {x: number, y: number, w: number, h: number}; // Canvas display coordinates
  decoded_text: string;
  confidence: number;
}

// Hand landmarks interface with TC Gốc coordinates - extended with QR detection
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
  // NEW: Optional QR detection data merged into hand landmarks structure
  qr_detections?: QRDetection[];
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
  
  // ✅ PURE 1:1 MAPPING - Canvas dimensions MUST equal video dimensions exactly
  // WARNING: Do NOT subtract control heights or add offsets - this breaks ROI accuracy
  const getVideoDisplayArea = useCallback(() => {
    return {
      width: width,   // Exact canvas width = video display width
      height: height, // Exact canvas height = video display height (NO control offset)
      offsetX: 0,     // No horizontal offset - pure alignment
      offsetY: 0      // No vertical offset - pure alignment
    };
  }, [width, height]);

  // ✅ PERFECT 1:1 COORDINATE MAPPING - Canvas pixels = Video pixels exactly
  // This ensures ROI coordinates are 100% accurate for backend processing
  const canvasToVideo = useCallback((x: number, y: number) => {
    return {
      x: Math.round(x),  // Canvas X → Video X (direct mapping)
      y: Math.round(y)   // Canvas Y → Video Y (direct mapping)
    };
  }, []);

  const videoToCanvas = useCallback((x: number, y: number) => {
    return {
      x: x,  // Video X → Canvas X (direct mapping)
      y: y   // Video Y → Canvas Y (direct mapping)
    };
  }, []);

  // ✅ BOUNDARY VALIDATION - Check if canvas coordinates are within actual video display area
  const isWithinVideoArea = useCallback((canvasX: number, canvasY: number): boolean => {
    const displayArea = getVideoDisplayArea();
    
    // ✅ SIMPLE: Canvas = Display area exactly, no offsets  
    return canvasX >= 0 && canvasX <= width && canvasY >= 0 && canvasY <= height;
  }, [getVideoDisplayArea, videoWidth, videoHeight, width, height]);

  // ✅ SIMPLE CLAMPING - Canvas = Display area exactly
  const clampToVideoArea = useCallback((canvasX: number, canvasY: number) => {
    return {
      x: Math.max(0, Math.min(canvasX, width)),
      y: Math.max(0, Math.min(canvasY, height))
    };
  }, [width, height]);

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

  // 🐛 DEBUG: Log video dimensions and display area when component mounts or props change
  useEffect(() => {
    const displayArea = getVideoDisplayArea();
    console.log('🎬 CanvasOverlay with Aspect Ratio Aware Video Display:', {
      'Video File Dimensions': `${videoWidth}x${videoHeight}`,
      'Canvas Dimensions': `${width}x${height}`,
      'Video Aspect Ratio': (videoWidth / videoHeight).toFixed(3),
      'Canvas Aspect Ratio': (width / height).toFixed(3),
      'Video Display Area': `${displayArea.width.toFixed(0)}x${displayArea.height.toFixed(0)}`,
      'Video Position Offset': `(${displayArea.offsetX.toFixed(0)}, ${displayArea.offsetY.toFixed(0)})`,
      'Fit Strategy': videoWidth/videoHeight > width/height ? 'Fit to width' : 'Fit to height'
    });
  }, [videoWidth, videoHeight, width, height, getVideoDisplayArea]);

  // Draw ROIs on canvas
  const drawROIs = useCallback(() => {
    const context = contextRef.current;
    if (!context) return;

    // Clear canvas before drawing
    context.clearRect(0, 0, width, height);

    // ✅ DRAW VIDEO BOUNDARY - Visual indicator of actual video display area
    const displayArea = getVideoDisplayArea();
    context.strokeStyle = 'rgba(128, 128, 128, 0.5)';
    context.lineWidth = 2;
    context.setLineDash([4, 4]);
    context.strokeRect(
      displayArea.offsetX, 
      displayArea.offsetY, 
      displayArea.width, 
      displayArea.height
    );
    context.setLineDash([]); // Reset dash pattern

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
    videoToCanvas,
    videoWidth,
    videoHeight,
    getVideoDisplayArea
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

      // Draw landmark points using backend's canvas-ready coordinates
      hand.forEach((landmark, idx) => {
        // Use backend's pre-calculated display coordinates with fallback
        const canvasX = landmark.x_disp !== undefined ? landmark.x_disp : (landmark.x_orig / videoWidth) * width;
        const canvasY = landmark.y_disp !== undefined ? landmark.y_disp : (landmark.y_orig / videoHeight) * height;
        
        // Debug logging for first landmark of first hand
        if (handIndex === 0 && idx === 0) {
          console.log('🔍 COORDINATE USAGE:', {
            'Has x_disp': landmark.x_disp !== undefined,
            'Has y_disp': landmark.y_disp !== undefined,
            'x_disp': landmark.x_disp,
            'y_disp': landmark.y_disp,
            'Canvas coordinates': `${canvasX?.toFixed(1)}, ${canvasY?.toFixed(1)}`,
            'Video size': `${videoWidth}x${videoHeight}`,
            'Canvas size': `${width}x${height}`
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
          
          // Use backend's pre-calculated display coordinates for line drawing with fallback
          const startX = startPoint.x_disp !== undefined ? startPoint.x_disp : (startPoint.x_orig / videoWidth) * width;
          const startY = startPoint.y_disp !== undefined ? startPoint.y_disp : (startPoint.y_orig / videoHeight) * height;
          const endX = endPoint.x_disp !== undefined ? endPoint.x_disp : (endPoint.x_orig / videoWidth) * width;
          const endY = endPoint.y_disp !== undefined ? endPoint.y_disp : (endPoint.y_orig / videoHeight) * height;
          
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

  // Draw QR detections on canvas (separate function for clarity)
  const drawQRDetections = useCallback(() => {
    const context = contextRef.current;
    if (!context || !handLandmarks || !handLandmarks.qr_detections || !showHandLandmarks) return;

    const { qr_detections } = handLandmarks;
    if (!qr_detections || qr_detections.length === 0) return;

    // QR detection styling - blue theme to distinguish from hand landmarks (green)
    const qrColor = '#3182CE'; // Blue color for QR codes
    const qrAlpha = 0.8;
    
    context.strokeStyle = qrColor;
    context.fillStyle = qrColor;
    context.globalAlpha = qrAlpha;
    context.lineWidth = 2;
    context.font = '12px Arial';

    // Draw each QR detection
    qr_detections.forEach((qr, index) => {
      const { canvas_bbox, decoded_text, confidence } = qr;
      
      // Draw QR bounding box using canvas_bbox coordinates (already mapped by LandmarkMapper)
      const { x, y, w, h } = canvas_bbox;
      
      // Draw border rectangle
      context.strokeRect(x, y, w, h);
      
      // Draw semi-transparent fill
      context.globalAlpha = qrAlpha * 0.2; // More transparent for fill
      context.fillRect(x, y, w, h);
      context.globalAlpha = qrAlpha; // Reset alpha for text
      
      // Draw QR code label above the box
      const labelY = y > 20 ? y - 5 : y + h + 15; // Position above or below based on space
      context.fillText(`QR: ${decoded_text.substring(0, 20)}${decoded_text.length > 20 ? '...' : ''}`, x + 2, labelY);
      
      // Draw confidence below the main text
      context.font = '10px Arial';
      context.fillText(`${(confidence * 100).toFixed(0)}%`, x + 2, labelY + 12);
      context.font = '12px Arial'; // Reset font
      
      // Debug logging for first QR detection
      if (index === 0) {
        console.log('🔍 QR DETECTION RENDERING:', {
          'Canvas bbox': canvas_bbox,
          'Decoded text': decoded_text,
          'Confidence': confidence,
          'Canvas size': `${width}x${height}`
        });
      }
    });

    // Reset alpha
    context.globalAlpha = 1.0;
    
    // Draw QR count indicator next to hand landmarks indicator
    if (qr_detections.length > 0) {
      const indicatorX = width - 160;
      const indicatorY = height - 55; // Position above hand indicator
      
      context.fillStyle = 'rgba(0, 0, 0, 0.7)';
      context.fillRect(indicatorX, indicatorY, 150, 25);
      
      context.fillStyle = qrColor;
      context.font = '11px Arial';
      context.fillText(
        `${qr_detections.length} QR code${qr_detections.length > 1 ? 's' : ''}`, 
        indicatorX + 5, 
        indicatorY + 16
      );
    }
  }, [handLandmarks, showHandLandmarks, width, height]);

  // Combined redraw function
  const redrawCanvas = useCallback(() => {
    drawROIs(); // This clears canvas and draws ROIs
    if (handLandmarks && showHandLandmarks) {
      drawHandLandmarks(); // Then draw hand landmarks on top
      drawQRDetections(); // Finally draw QR detections on top
    }
  }, [drawROIs, drawHandLandmarks, drawQRDetections, handLandmarks, showHandLandmarks]);

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

    // ✅ PREVENT DRAWING OUTSIDE VIDEO AREA - Reject clicks outside video boundaries
    if (!isWithinVideoArea(x, y)) {
      console.log(`🚫 Click rejected: (${x.toFixed(1)}, ${y.toFixed(1)}) is outside video area`);
      return; // Ignore clicks outside video boundaries
    }

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
  }, [disabled, findROIAtPoint, findROIBorderAtPoint, onROISelect, snapToGrid, isWithinVideoArea]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (disabled) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // ✅ ALLOW FREE MOUSE MOVEMENT - No clamping during drawing for natural ROI creation

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
      
      // ✅ ĐƠN GIẢN - Canvas = Display, chỉ clamp trong biên canvas
      const clampedX = Math.max(0, Math.min(width, snappedX));
      const clampedY = Math.max(0, Math.min(height, snappedY));
      
      const startX = Math.min(drawingState.startX, clampedX);
      const startY = Math.min(drawingState.startY, clampedY);
      const endX = Math.max(drawingState.startX, clampedX);
      const endY = Math.max(drawingState.startY, clampedY);
      
      const w = endX - startX;
      const h = endY - startY;
      
      if (w > minROISize && h > minROISize) {
        // ✅ KHÔNG CAN THIỆP GÌ - vẽ sao để vậy
        const previewROI: ROIData = {
          id: 'preview',
          x: startX,
          y: startY,
          w: w,
          h: h,
          type: currentROIType,
          label: currentROILabel,
          color: ROI_TYPE_COLORS[currentROIType],
          completed: false
        };
        
        setDrawingState(prev => ({
          ...prev,
          currentX: clampedX,
          currentY: clampedY,
          previewROI
        }));
      }
      return;
    }

    // Handle hover effects
    const borderROI = findROIBorderAtPoint(x, y);
    const contentROI = findROIAtPoint(x, y);
    
    setHoveredROIId(borderROI?.id || contentROI?.id || null);
    
    // ✅ ENHANCED CURSOR MANAGEMENT - Dynamic cursor with drawing state feedback
    const withinVideoArea = isWithinVideoArea(x, y);
    
    if (drawingState.isDrawing) {
      // During drawing - show appropriate feedback based on boundary constraints
      if (!withinVideoArea) {
        canvas.style.cursor = 'not-allowed'; // Drawing outside bounds
      } else {
        canvas.style.cursor = 'crosshair'; // Active drawing within bounds
      }
    } else if (!withinVideoArea) {
      // Outside video area - show not-allowed cursor
      canvas.style.cursor = 'not-allowed';
    } else if (borderROI) {
      // On ROI border - allow dragging
      canvas.style.cursor = 'move';
    } else if (contentROI) {
      // Inside ROI - allow selection
      canvas.style.cursor = 'pointer';
    } else {
      // Inside video area - allow drawing (crosshair only within actual video bounds)
      canvas.style.cursor = 'crosshair';
    }
    
    // 🐛 DEBUG: Log cursor decisions and boundary validation occasionally
    if (Math.random() < 0.005) { // Very occasional logging
      console.log('🖱️ Enhanced Cursor & Boundary Decision:', {
        'Mouse': `(${x.toFixed(1)}, ${y.toFixed(1)})`,
        'Within Video Area': withinVideoArea,
        'Video Dimensions': `${videoWidth}x${videoHeight}`,
        'Drawing State': drawingState.isDrawing,
        'Cursor Set': canvas.style.cursor,
        'Has Border ROI': !!borderROI,
        'Has Content ROI': !!contentROI,
        'Video Display Area': getVideoDisplayArea()
      });
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
    findROIBorderAtPoint,
    clampToVideoArea,
    isWithinVideoArea,
    getVideoDisplayArea
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
      
      // ✅ ĐƠN GIẢN - Chỉ tạo ROI, không cần debug phức tạp
      onROICreate?.(roi);
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
export type { HandLandmarks, QRDetection };

export default CanvasOverlay;