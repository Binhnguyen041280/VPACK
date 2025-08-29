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
  disabled?: boolean;
  className?: string;
  minROISize?: number;
  gridSnap?: boolean;
  snapSize?: number;
}

// Default colors for different ROI types
const ROI_TYPE_COLORS: Record<ROIData['type'], string> = {
  packing_area: '#3182CE',    // Blue
  qr_mvd: '#38A169',         // Green  
  qr_trigger: '#D69E2E',     // Yellow
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
  disabled = false,
  className,
  minROISize = 20,
  gridSnap = false,
  snapSize = 10
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

    // Clear canvas
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

  // Redraw canvas when dependencies change
  useEffect(() => {
    drawROIs();
  }, [drawROIs]);

  // Find ROI at canvas coordinates
  const findROIAtPoint = useCallback((x: number, y: number): ROIData | null => {
    for (let i = rois.length - 1; i >= 0; i--) {
      const roi = rois[i];
      const canvasPos = videoToCanvas(roi.x, roi.y);
      const canvasSize = videoToCanvas(roi.w, roi.h);
      
      if (x >= canvasPos.x && x <= canvasPos.x + canvasSize.x &&
          y >= canvasPos.y && y <= canvasPos.y + canvasSize.y) {
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

    // Check if clicking on existing ROI
    const clickedROI = findROIAtPoint(x, y);
    
    if (clickedROI) {
      // Select existing ROI
      onROISelect?.(clickedROI.id);
      
      // Start drag operation
      setDragState({
        isDragging: true,
        roiId: clickedROI.id,
        startX: x,
        startY: y,
        originalROI: clickedROI
      });
      
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
  }, [disabled, findROIAtPoint, onROISelect, snapToGrid]);

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
    const hoveredROI = findROIAtPoint(x, y);
    setHoveredROIId(hoveredROI?.id || null);
    
    // Update cursor
    canvas.style.cursor = hoveredROI ? 'move' : 'crosshair';
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
    findROIAtPoint
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

export default CanvasOverlay;