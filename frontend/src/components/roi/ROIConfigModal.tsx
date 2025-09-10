/**
 * ROIConfigModal Component
 * Full-screen modal for ROI configuration with video player and interactive canvas
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalBody,
  ModalCloseButton,
  Box,
  Flex,
  VStack,
  HStack,
  Text,
  Button,
  IconButton,
  Select,
  Input,
  FormControl,
  FormLabel,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Spinner,
  Badge,
  Divider,
  Tooltip,
  useColorModeValue,
  useToast
} from '@chakra-ui/react';
import { FaTrash, FaPlay, FaPause } from 'react-icons/fa';
// Simplified 2-canvas architecture  
import PureVideoCanvas from './PureVideoCanvas';
import VideoControlsBar, { VideoControlState } from './VideoControlsBar';
import { ROIData, HandLandmarks } from './CanvasOverlay';
// Generate unique IDs without external dependency
const generateId = () => Math.random().toString(36).substr(2, 9);

// Height breakpoints for adaptive behavior (copied from CanvasMessage.tsx)
type HeightMode = 'compact' | 'normal' | 'spacious';

interface AdaptiveConfig {
  mode: HeightMode;
  fontSize: {
    header: string;
    title: string;
    body: string;
    small: string;
  };
  spacing: {
    section: string;
    item: string;
    padding: string;
  };
  showOptional: boolean;
}

// Video metadata interface
interface VideoMetadata {
  path: string;
  filename: string;
  duration_seconds: number;
  duration_formatted: string;
  frame_count: number;
  fps: number;
  resolution: {
    width: number;
    height: number;
    aspect_ratio: number;
  };
  size_mb: number;
  codec: string;
}


// Component props interface
interface ROIConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  videoPath: string;
  cameraId: string;
  packingMethod: 'traditional' | 'qr';
  onSave?: (config: {
    cameraId: string;
    videoPath: string;
    rois: ROIData[];
    packingMethod: string;
    videoMetadata: VideoMetadata;
  }) => void;
  onError?: (error: string) => void;
}


// Video player dimensions will be calculated as 60% of original video size
// These are fallback values for when video metadata isn't loaded yet
const FALLBACK_VIDEO_PLAYER_WIDTH = 960;
const FALLBACK_VIDEO_PLAYER_HEIGHT = 540;

const ROIConfigModal: React.FC<ROIConfigModalProps> = ({
  isOpen,
  onClose,
  videoPath,
  cameraId,
  packingMethod,
  onSave,
  onError
}) => {
  // State
  const [videoMetadata, setVideoMetadata] = useState<VideoMetadata | null>(null);
  const [rois, setROIs] = useState<ROIData[]>([]);
  const [selectedROIId, setSelectedROIId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [handLandmarks, setHandLandmarks] = useState<HandLandmarks | null>(null);
  
  // Adaptive height detection state (copied from CanvasMessage.tsx)
  const containerRef = useRef<HTMLDivElement>(null);
  const [availableHeight, setAvailableHeight] = useState(0);
  const [adaptiveConfig, setAdaptiveConfig] = useState<AdaptiveConfig>({
    mode: 'normal',
    fontSize: { header: 'xl', title: 'sm', body: 'sm', small: 'xs' },
    spacing: { section: '24px', item: '16px', padding: '16px' },
    showOptional: true
  });
  const [isVideoPlaying, setIsVideoPlaying] = useState(false);
  const [isWaitingForAnalysis, setIsWaitingForAnalysis] = useState(false);
  const [preprocessingState, setPreprocessingState] = useState<{
    isProcessing: boolean;
    progress: number;
    cacheKey: string | null;
    completed: boolean;
    error: string | null;
  }>({
    isProcessing: false,
    progress: 0,
    cacheKey: null,
    completed: false,
    error: null
  });

  // QR preprocessing state - separate from hand preprocessing
  const [qrPreprocessingState, setQRPreprocessingState] = useState<{
    isProcessing: boolean;
    progress: number;
    cacheKey: string | null;
    completed: boolean;
    error: string | null;
  }>({
    isProcessing: false,
    progress: 0,
    cacheKey: null,
    completed: false,
    error: null
  });

  // Canvas dimensions state (60% of video dimensions)
  const [canvasDimensions, setCanvasDimensions] = useState<{
    width: number;
    height: number;
  }>({
    width: FALLBACK_VIDEO_PLAYER_WIDTH,
    height: FALLBACK_VIDEO_PLAYER_HEIGHT
  });

  // Full screen state
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [fullScreenDimensions, setFullScreenDimensions] = useState<{
    width: number;
    height: number;
  }>({
    width: FALLBACK_VIDEO_PLAYER_WIDTH,
    height: FALLBACK_VIDEO_PLAYER_HEIGHT
  });

  // Toast for notifications
  const toast = useToast();

  // Video controls state and ref
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [videoControlsState, setVideoControlsState] = useState<VideoControlState>({
    isPlaying: false,
    currentTime: 0,
    duration: 0,
  });

  // Calculate available viewport space for video display
  const calculateAvailableSpace = useCallback(() => {
    const sidebarWidth = 256; // Left panel width
    const padding = 20; // Center panel padding (10px each side) - reduced
    const controlsHeight = 80; // Video controls area - reduced
    const alertHeight = 0; // No space needed - all messages in sidebar now
    
    const availableWidth = window.innerWidth - sidebarWidth - padding;
    const availableHeight = window.innerHeight - controlsHeight - alertHeight;
    
    return {
      width: Math.max(400, availableWidth), // Min 400px width
      height: Math.max(300, availableHeight) // Min 300px height
    };
  }, []);

  // Calculate optimal scale to fit viewport (no maximum limit)
  const calculateOptimalScale = useCallback((videoResolution: { width: number; height: number }, availableSpace: { width: number; height: number }) => {
    const scaleX = availableSpace.width / videoResolution.width;
    const scaleY = availableSpace.height / videoResolution.height;
    
    // Take the smaller scale to ensure both dimensions fit perfectly in viewport
    const optimalScale = Math.min(scaleX, scaleY);
    
    console.log('Scale calculation:', {
      video: `${videoResolution.width}x${videoResolution.height}`,
      available: `${availableSpace.width}x${availableSpace.height}`,
      scaleX: scaleX.toFixed(3),
      scaleY: scaleY.toFixed(3),
      optimalScale: optimalScale.toFixed(3)
    });
    
    return optimalScale;
  }, []);

  // Theme colors
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const panelBg = useColorModeValue('gray.50', 'gray.700');
  const textColor = useColorModeValue('gray.800', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  
  // Adaptive height detection and configuration (copied from CanvasMessage.tsx)
  useEffect(() => {
    const updateHeight = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        const height = rect.height;
        setAvailableHeight(height);
        
        // Determine adaptive config based on height
        let newConfig: AdaptiveConfig;
        
        if (height < 600) {
          // Compact mode - small modal height
          newConfig = {
            mode: 'compact',
            fontSize: { header: 'lg', title: 'sm', body: 'sm', small: 'xs' },
            spacing: { section: '16px', item: '12px', padding: '12px' },
            showOptional: false
          };
        } else if (height < 800) {
          // Normal mode - medium modal height
          newConfig = {
            mode: 'normal',
            fontSize: { header: 'xl', title: 'sm', body: 'sm', small: 'xs' },
            spacing: { section: '24px', item: '16px', padding: '16px' },
            showOptional: true
          };
        } else {
          // Spacious mode - large modal height
          newConfig = {
            mode: 'spacious',
            fontSize: { header: 'xl', title: 'md', body: 'sm', small: 'xs' },
            spacing: { section: '32px', item: '20px', padding: '20px' },
            showOptional: true
          };
        }
        
        setAdaptiveConfig(newConfig);
      }
    };

    // Initial measurement
    updateHeight();
    
    // Listen for resize events
    const resizeObserver = new ResizeObserver(updateHeight);
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }
    
    return () => resizeObserver.disconnect();
  }, []);




  // Full screen functions
  const enterFullScreen = useCallback(async () => {
    try {
      const modalContent = document.querySelector('[data-testid="modal-content"]') || document.documentElement;
      if (modalContent.requestFullscreen) {
        await modalContent.requestFullscreen();
      }
    } catch (error) {
      console.warn('Cannot enter fullscreen:', error);
      // Fullscreen error - no popup needed, user can see video still works
    }
  }, []);

  const exitFullScreen = useCallback(async () => {
    try {
      if (document.exitFullscreen) {
        await document.exitFullscreen();
      }
    } catch (error) {
      console.warn('Cannot exit fullscreen:', error);
    }
  }, []);

  // Full screen change detection
  useEffect(() => {
    const handleFullScreenChange = () => {
      const isFS = document.fullscreenElement !== null;
      setIsFullScreen(isFS);
      
      if (isFS) {
        // Calculate full screen dimensions maintaining aspect ratio
        const screenWidth = window.screen.width;
        const screenHeight = window.screen.height;
        const screenAspectRatio = screenWidth / screenHeight;
        
        if (videoMetadata && canvasDimensions) {
          const canvasAspectRatio = canvasDimensions.width / canvasDimensions.height;
          
          let displayWidth, displayHeight;
          if (canvasAspectRatio > screenAspectRatio) {
            // Canvas wider than screen - fit to width
            displayWidth = screenWidth;
            displayHeight = screenWidth / canvasAspectRatio;
          } else {
            // Canvas taller than screen - fit to height  
            displayHeight = screenHeight;
            displayWidth = screenHeight * canvasAspectRatio;
          }
          
          setFullScreenDimensions({
            width: displayWidth,
            height: displayHeight
          });
          
          console.log('Full Screen Mode:', {
            screen: `${screenWidth}x${screenHeight}`,
            canvas: `${canvasDimensions.width}x${canvasDimensions.height}`,
            display: `${displayWidth.toFixed(0)}x${displayHeight.toFixed(0)}`
          });
        }
      } else {
        // Reset to normal dimensions (60% of video size)
        setFullScreenDimensions({
          width: canvasDimensions.width,
          height: canvasDimensions.height
        });
      }
    };

    document.addEventListener('fullscreenchange', handleFullScreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullScreenChange);
    document.addEventListener('mozfullscreenchange', handleFullScreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullScreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullScreenChange);
      document.removeEventListener('mozfullscreenchange', handleFullScreenChange);
    };
  }, [videoMetadata, canvasDimensions]);

  // Handle window resize to recalculate dimensions
  useEffect(() => {
    const handleResize = () => {
      if (videoMetadata && !isFullScreen) {
        // Recalculate dimensions for new viewport size
        const availableSpace = calculateAvailableSpace();
        const optimalScale = calculateOptimalScale(videoMetadata.resolution, availableSpace);
        
        const displayWidth = Math.round(videoMetadata.resolution.width * optimalScale);
        const displayHeight = Math.round(videoMetadata.resolution.height * optimalScale);
        
        setCanvasDimensions({
          width: displayWidth,
          height: displayHeight
        });

        setFullScreenDimensions({
          width: displayWidth,
          height: displayHeight
        });

        console.log('Viewport resize - dimensions recalculated:', {
          available: `${availableSpace.width}x${availableSpace.height}`,
          scale: `${(optimalScale * 100).toFixed(1)}%`,
          display: `${displayWidth}x${displayHeight}`
        });
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [videoMetadata, isFullScreen, calculateAvailableSpace, calculateOptimalScale]);

  // Handle video metadata loaded
  const handleMetadataLoaded = useCallback((metadata: VideoMetadata) => {
    console.log('Video metadata loaded:', metadata);
    setVideoMetadata(metadata);
    setError(null);

    // Calculate available space and optimal scale
    const availableSpace = calculateAvailableSpace();
    const optimalScale = calculateOptimalScale(metadata.resolution, availableSpace);
    
    // Calculate display dimensions using dynamic scale
    const displayWidth = Math.round(metadata.resolution.width * optimalScale);
    const displayHeight = Math.round(metadata.resolution.height * optimalScale);
    
    setCanvasDimensions({
      width: displayWidth,
      height: displayHeight
    });

    // Also update fullScreenDimensions for normal mode
    setFullScreenDimensions({
      width: displayWidth,
      height: displayHeight
    });

    console.log('Dynamic canvas dimensions calculated:', {
      original: `${metadata.resolution.width}x${metadata.resolution.height}`,
      available: `${availableSpace.width}x${availableSpace.height}`,
      scale: `${(optimalScale * 100).toFixed(1)}%`,
      display: `${displayWidth}x${displayHeight}`
    });
  }, [calculateAvailableSpace, calculateOptimalScale]);

  // Handle video error
  const handleVideoError = useCallback((errorMessage: string) => {
    console.error('Video error:', errorMessage);
    setError(`Video loading error: ${errorMessage}`);
    onError?.(errorMessage);
  }, [onError]);

  // Handle ROI creation
  const handleROICreate = useCallback((roiData: Omit<ROIData, 'id'>) => {
    // Determine ROI type and label based on packing method
    const getROITypeAndLabel = () => {
      if (packingMethod === 'traditional') {
        // Check if packing area already exists
        const existingPackingArea = rois.some(roi => roi.type === 'packing_area');
        if (existingPackingArea) {
          // ROI limit error - shown in sidebar Messages section
          return null;
        }
        return { type: 'packing_area', label: 'Packing Area' };
      } else {
        // For QR method, allow 2 specific areas: Trigger first, then Packing
        const existingTriggerArea = rois.some(roi => roi.type === 'qr_trigger');
        const existingPackingArea = rois.some(roi => roi.type === 'packing_area');
        
        // If both areas already exist, prevent creation
        if (existingTriggerArea && existingPackingArea) {
          // ROI limit error - shown in sidebar Messages section
          return null;
        }
        
        // Create Trigger area first, then Packing area
        if (!existingTriggerArea) {
          return { type: 'qr_trigger', label: 'Trigger Area' };
        } else {
          return { type: 'packing_area', label: 'Packing Area' };
        }
      }
    };

    const roiTypeAndLabel = getROITypeAndLabel();
    if (!roiTypeAndLabel) {
      return; // Early return if ROI creation is not allowed
    }

    const { type, label } = roiTypeAndLabel;
    
    const newROI: ROIData = {
      ...roiData,
      id: generateId(),
      type: type as any,
      label: label,
      color: roiData.color
    };

    setROIs(prev => [...prev, newROI]);
    setSelectedROIId(newROI.id);

    // ROI created success - shown in sidebar Messages section

    console.log('ROI created:', newROI);

    // Set flag to trigger preprocessing after ROI creation
    // Trigger preprocessing based on method and ROI completion
    if (type === 'packing_area') {
      console.log('Packing area ROI created - checking preprocessing requirements');
      
      if (packingMethod === 'traditional') {
        // Traditional: trigger immediately when packing area is created
        console.log('Traditional method: triggering preprocessing for packing area');
        setTimeout(() => {
          triggerBothPreprocessing();
        }, 500);
      } else if (packingMethod === 'qr') {
        // QR method: only trigger when both ROIs are complete
        const willHaveTrigger = rois.some(r => r.type === 'qr_trigger') || type === 'qr_trigger';
        const willHavePacking = rois.some(r => r.type === 'packing_area') || type === 'packing_area';
        
        if (willHaveTrigger && willHavePacking) {
          console.log('QR method: both ROIs complete - triggering dual preprocessing');
          setTimeout(() => {
            triggerBothPreprocessing();
          }, 500);
        } else {
          console.log('QR method: waiting for both ROIs to be complete before preprocessing');
        }
      }
    }
  }, [packingMethod, rois]);

  // Handle ROI update
  const handleROIUpdate = useCallback((id: string, updates: Partial<ROIData>) => {
    setROIs(prev => prev.map(roi => 
      roi.id === id ? { ...roi, ...updates } : roi
    ));
    
    // Clear cache when ROI is modified - data is no longer valid
    if (preprocessingState.cacheKey) {
      // Clear hand detection cache on backend
      fetch(`http://localhost:8080/api/hand-detection/clear-cache/${preprocessingState.cacheKey}`, {
        method: 'DELETE'
      }).catch(error => console.warn('Failed to clear hand cache:', error));
    }

    // Also clear QR cache if available
    if (qrPreprocessingState.cacheKey) {
      fetch(`http://localhost:8080/api/qr-detection/clear-cache/${qrPreprocessingState.cacheKey}`, {
        method: 'DELETE'
      }).catch(error => console.warn('Failed to clear QR cache:', error));
      
      setQRPreprocessingState(prev => ({
        ...prev,
        completed: false,
        progress: 0,
        cacheKey: null,
        error: null
      }));
      
      setPreprocessingState(prev => ({
        ...prev,
        completed: false,
        cacheKey: null,
        error: null
      }));
      
      setHandLandmarks(null);
      
      // ROI changed - processing status shown in sidebar Messages section
    }
  }, [preprocessingState.cacheKey]);

  // Handle ROI deletion
  const handleROIDelete = useCallback((id: string) => {
    const roiToDelete = rois.find(roi => roi.id === id);
    if (!roiToDelete) return;

    setROIs(prev => prev.filter(roi => roi.id !== id));
    
    if (selectedROIId === id) {
      setSelectedROIId(null);
    }

    // Clear cache when ROI is deleted - especially important for packing areas
    if (preprocessingState.cacheKey && roiToDelete.type === 'packing_area') {
      // Clear hand detection cache on backend
      fetch(`http://localhost:8080/api/hand-detection/clear-cache/${preprocessingState.cacheKey}`, {
        method: 'DELETE'
      }).catch(error => console.warn('Failed to clear hand cache:', error));
      
      setPreprocessingState(prev => ({
        ...prev,
        completed: false,
        cacheKey: null,
        error: null,
        isProcessing: false,
        progress: 0
      }));
      
      setHandLandmarks(null);
    }
    
    // Always reset hand detection state when packing area is deleted, regardless of cache state
    if (roiToDelete.type === 'packing_area') {
      setPreprocessingState(prev => ({
        ...prev,
        completed: false,
        cacheKey: null,
        error: null,
        isProcessing: false,
        progress: 0
      }));
      setHandLandmarks(null);
    }

    // Also clear QR cache when ROI is deleted
    if (qrPreprocessingState.cacheKey && roiToDelete.type === 'packing_area') {
      // Clear QR detection cache on backend
      fetch(`http://localhost:8080/api/qr-detection/clear-cache/${qrPreprocessingState.cacheKey}`, {
        method: 'DELETE'
      }).catch(error => console.warn('Failed to clear QR cache:', error));
      
      setQRPreprocessingState(prev => ({
        ...prev,
        completed: false,
        progress: 0,
        cacheKey: null,
        error: null,
        isProcessing: false
      }));
    }
    
    // Always reset QR state when packing area is deleted, regardless of cache state
    if (roiToDelete.type === 'packing_area') {
      setQRPreprocessingState(prev => ({
        ...prev,
        completed: false,
        progress: 0,
        cacheKey: null,
        error: null,
        isProcessing: false
      }));
      console.log('ROI deleted - both hand and QR preprocessing states reset');
    }

    console.log('ROI deleted:', roiToDelete);
  }, [rois, selectedROIId, preprocessingState.cacheKey]);

  // Handle ROI selection
  const handleROISelect = useCallback((id: string | null) => {
    setSelectedROIId(id);
    console.log('ROI selected:', id);
  }, []);

  // Convert canvas coordinates to original video coordinates
  const convertToOriginalCoordinates = useCallback((roi: ROIData) => {
    if (!videoMetadata) {
      return { x: roi.x, y: roi.y, w: roi.w, h: roi.h };
    }

    const scaleX = videoMetadata.resolution.width / canvasDimensions.width;
    const scaleY = videoMetadata.resolution.height / canvasDimensions.height;

    return {
      x: Math.round(roi.x * scaleX),
      y: Math.round(roi.y * scaleY),
      w: Math.round(roi.w * scaleX),
      h: Math.round(roi.h * scaleY)
    };
  }, [videoMetadata, canvasDimensions]);

// Get landmarks and QR detections from cached results (DUAL DETECTION SYSTEM)
  const getLandmarksAtCurrentTime = useCallback(async (currentTime: number) => {
    console.log('getLandmarksAtCurrentTime called:', {
      videoMetadata: !!videoMetadata,
      roisLength: rois.length,
      isVideoPlaying,
      handCacheKey: preprocessingState.cacheKey,
      qrCacheKey: qrPreprocessingState.cacheKey,
      handCompleted: preprocessingState.completed,
      qrCompleted: qrPreprocessingState.completed,
      timestamp: currentTime
    });
    
    if (!videoMetadata || rois.length === 0 || !isVideoPlaying || !preprocessingState.cacheKey) {
      setHandLandmarks(null);
      return;
    }

    // Check if preprocessing is still in progress and current timestamp is ahead
    if (!preprocessingState.completed || !qrPreprocessingState.completed) {
      try {
        // Check hand detection progress
        const handProgressResponse = await fetch(`http://localhost:8080/api/hand-detection/preprocess-status/${preprocessingState.cacheKey}`);
        const handProgress = await handProgressResponse.json();
        
        // Check QR detection progress
        const qrProgressResponse = await fetch(`http://localhost:8080/api/qr-detection/preprocess-status/${qrPreprocessingState.cacheKey}`);
        const qrProgress = await qrProgressResponse.json();

        // Calculate the furthest processed timestamp from both systems
        // Backend processes at 5fps = 0.2s per frame
        const handProcessedTime = handProgress.success ? (handProgress.processed_count || 0) * 0.2 : 0;
        const qrProcessedTime = qrProgress.success ? (qrProgress.processed_count || 0) * 0.2 : 0;
        const maxProcessedTime = Math.max(handProcessedTime, qrProcessedTime);

        console.log('🕐 Timestamp Comparison:', {
          currentTime: currentTime.toFixed(1) + 's',
          handProcessed: handProcessedTime.toFixed(1) + 's',
          qrProcessed: qrProcessedTime.toFixed(1) + 's',
          maxProcessed: maxProcessedTime.toFixed(1) + 's',
          bufferTarget: (maxProcessedTime - 10).toFixed(1) + 's',
          needsWait: currentTime > maxProcessedTime - 10
        });

        // If current timestamp is ahead of processing with 10s buffer, pause and wait
        if (currentTime > maxProcessedTime - 10) {
          if (videoRef.current && !videoRef.current.paused) {
            videoRef.current.pause();
            setIsVideoPlaying(false);
            setIsWaitingForAnalysis(true);
            console.log(`⏸️ Video paused: FE timestamp (${currentTime.toFixed(1)}s) > BE processed (${maxProcessedTime.toFixed(1)}s) - waiting for analysis`);
          }
          
          // Show waiting message by clearing landmarks
          setHandLandmarks(null);
          return;
        }
        
        // If video is paused due to waiting and now we have enough buffer, clear waiting state
        if (isWaitingForAnalysis && currentTime <= maxProcessedTime - 10) {
          setIsWaitingForAnalysis(false);
          console.log(`✅ Analysis buffer ready: BE processed (${maxProcessedTime.toFixed(1)}s) > FE (${currentTime.toFixed(1)}s) + 10s buffer - user can resume`);
          // Don't auto-resume here, let user manually resume
        }
        
      } catch (error) {
        console.warn('Failed to check preprocessing progress:', error);
      }
    }

    // Detection logic for both Traditional and QR methods
    const packingROI = rois.find(roi => roi.type === 'packing_area');
    if (!packingROI) {
      setHandLandmarks(null);
      return;
    }

    // For QR method, also need trigger ROI
    let triggerROI = null;
    if (packingMethod === 'qr') {
      triggerROI = rois.find(roi => roi.type === 'qr_trigger');
      if (!triggerROI) {
        setHandLandmarks(null);
        return;
      }
    }

    try {
      // Transform packing area ROI from canvas coordinates to video coordinates
      const packing_roi_orig = {
        x: Math.round(packingROI.x * videoMetadata.resolution.width / canvasDimensions.width),
        y: Math.round(packingROI.y * videoMetadata.resolution.height / canvasDimensions.height),
        w: Math.round(packingROI.w * videoMetadata.resolution.width / canvasDimensions.width),
        h: Math.round(packingROI.h * videoMetadata.resolution.height / canvasDimensions.height)
      };

      // Transform trigger area ROI if QR method
      let trigger_roi_orig = null;
      if (packingMethod === 'qr' && triggerROI) {
        trigger_roi_orig = {
          x: Math.round(triggerROI.x * videoMetadata.resolution.width / canvasDimensions.width),
          y: Math.round(triggerROI.y * videoMetadata.resolution.height / canvasDimensions.height),
          w: Math.round(triggerROI.w * videoMetadata.resolution.width / canvasDimensions.width),
          h: Math.round(triggerROI.h * videoMetadata.resolution.height / canvasDimensions.height)
        };
      }

      // Prepare API calls based on method
      const apiCalls = [];
      
      if (packingMethod === 'traditional') {
        // TRADITIONAL METHOD: 1 API call - Hand + QR detection on packing area
        const requestBody = {
          cache_key: preprocessingState.cacheKey,  // Hand cache key
          timestamp: currentTime,
          canvas_dims: {
            width: canvasDimensions.width,
            height: canvasDimensions.height
          },
          video_dims: {
            width: videoMetadata.resolution.width,
            height: videoMetadata.resolution.height
          },
          roi_config: packing_roi_orig
        };

        const qrRequestBody = {
          cache_key: qrPreprocessingState.cacheKey,  // QR cache key
          timestamp: currentTime,
          canvas_dims: requestBody.canvas_dims,
          video_dims: requestBody.video_dims,
          roi_config: requestBody.roi_config
        };

        apiCalls.push(
          // Hand detection on packing area
          fetch('http://localhost:8080/api/hand-detection/get-cached-landmarks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
          }),
          // QR detection on packing area (if QR cache available)
          qrPreprocessingState.cacheKey 
            ? fetch('http://localhost:8080/api/qr-detection/get-cached-qr', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(qrRequestBody)
              })
            : Promise.resolve(null)
        );

      } else if (packingMethod === 'qr') {
        // QR METHOD: 2 API calls
        // 1. Hand + QR detection on packing area (movement area)
        const packingRequestBody = {
          cache_key: preprocessingState.cacheKey,  // Hand cache key for packing area
          timestamp: currentTime,
          canvas_dims: {
            width: canvasDimensions.width,
            height: canvasDimensions.height
          },
          video_dims: {
            width: videoMetadata.resolution.width,
            height: videoMetadata.resolution.height
          },
          roi_config: packing_roi_orig
        };

        const packingQRRequestBody = {
          cache_key: qrPreprocessingState.cacheKey,  // QR cache key for packing area
          timestamp: currentTime,
          canvas_dims: packingRequestBody.canvas_dims,
          video_dims: packingRequestBody.video_dims,
          roi_config: packing_roi_orig
        };

        // 2. QR trigger detection on trigger area (looking for "timego")
        const triggerQRRequestBody = {
          cache_key: qrPreprocessingState.cacheKey + '_trigger',  // Trigger-specific cache
          timestamp: currentTime,
          canvas_dims: packingRequestBody.canvas_dims,
          video_dims: packingRequestBody.video_dims,
          roi_config: trigger_roi_orig,
          trigger_mode: true,  // Flag to look for "TimeGo" specifically
          target_text: 'TimeGo'
        };

        apiCalls.push(
          // Hand detection on packing area (movement area)
          fetch('http://localhost:8080/api/hand-detection/get-cached-landmarks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(packingRequestBody)
          }),
          // QR detection on packing area (movement area)
          qrPreprocessingState.cacheKey 
            ? fetch('http://localhost:8080/api/qr-detection/get-cached-qr', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(packingQRRequestBody)
              })
            : Promise.resolve(null),
          // QR trigger detection on trigger area (looking for "timego")
          qrPreprocessingState.cacheKey 
            ? fetch('http://localhost:8080/api/qr-detection/get-cached-trigger', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(triggerQRRequestBody)
              })
            : Promise.resolve(null)
        );
      }

      const responses = await Promise.all(apiCalls);
      
      // Parse results based on method
      let handResult, qrResult, triggerResult;
      
      if (packingMethod === 'traditional') {
        // Traditional: [handResponse, qrResponse]
        handResult = await responses[0].json();
        qrResult = responses[1] ? await responses[1].json() : { success: false, canvas_qr_detections: [] };
        triggerResult = null;
        
      } else if (packingMethod === 'qr') {
        // QR method: [handResponse, packingQRResponse, triggerQRResponse]
        handResult = await responses[0].json();
        qrResult = responses[1] ? await responses[1].json() : { success: false, canvas_qr_detections: [] };
        triggerResult = responses[2] ? await responses[2].json() : { success: false, trigger_detected: false, trigger_text: null };
      }
      
      console.log('API Results:', {
        method: packingMethod,
        handSuccess: handResult.success,
        handLandmarks: handResult.canvas_landmarks?.length || 0,
        qrSuccess: qrResult.success,
        qrDetections: qrResult.canvas_qr_detections?.length || 0,
        triggerSuccess: triggerResult?.success || false,
        triggerDetected: triggerResult?.trigger_detected || false,
        triggerText: triggerResult?.trigger_text || null,
        handCacheKey: preprocessingState.cacheKey,
        qrCacheKey: qrPreprocessingState.cacheKey
      });

      // Merge hand, QR, and trigger data into unified structure
      if (handResult.success) {
        const mergedLandmarks = {
          // Hand detection data
          landmarks: handResult.canvas_landmarks || handResult.landmarks || [],
          confidence: handResult.confidence || 0,
          hands_detected: (handResult.canvas_landmarks || handResult.landmarks || []).length,
          // QR detection data from packing area
          qr_detections: qrResult.success ? (qrResult.canvas_qr_detections || []) : [],
          // Trigger data for QR method only
          trigger_detected: triggerResult?.trigger_detected || false,
          trigger_text: triggerResult?.trigger_text || null,
          trigger_roi: packingMethod === 'qr' ? triggerROI : null
        };

        console.log('Detection Result:', {
          method: packingMethod,
          timestamp: currentTime,
          hands_detected: mergedLandmarks.hands_detected,
          qr_detections: mergedLandmarks.qr_detections.length,
          hand_confidence: mergedLandmarks.confidence,
          trigger_detected: mergedLandmarks.trigger_detected,
          trigger_text: mergedLandmarks.trigger_text
        });

        setHandLandmarks(mergedLandmarks);
      } else {
        // Hand detection failed - still show QR and trigger if available
        const fallbackLandmarks = {
          landmarks: [],
          confidence: 0,
          hands_detected: 0,
          qr_detections: qrResult.success ? (qrResult.canvas_qr_detections || []) : [],
          trigger_detected: triggerResult?.trigger_detected || false,
          trigger_text: triggerResult?.trigger_text || null,
          trigger_roi: packingMethod === 'qr' ? triggerROI : null
        };

        if (fallbackLandmarks.qr_detections.length > 0 || fallbackLandmarks.trigger_detected) {
          setHandLandmarks(fallbackLandmarks);
        } else {
          setHandLandmarks(null);
        }
      }
    } catch (error) {
      // Don't log error for incomplete processing - this is expected
      if (!preprocessingState.completed && !qrPreprocessingState.completed) {
        console.debug('Cache not ready yet for current timestamp:', currentTime);
      } else {
        console.error('Error getting cached detection data:', error);
      }
      setHandLandmarks(null);
    }
  }, [videoMetadata, rois, packingMethod, isVideoPlaying, preprocessingState.cacheKey, preprocessingState.completed, qrPreprocessingState.cacheKey, qrPreprocessingState.completed, canvasDimensions, isWaitingForAnalysis]);

  // Handle video play/pause state changes
  const handleVideoPlayStateChange = useCallback((isPlaying: boolean) => {
    setIsVideoPlaying(isPlaying);
    if (!isPlaying) {
      setHandLandmarks(null); // Clear landmarks when video is paused
    }
  }, []);

  // Poll for preprocessing progress
  const pollPreprocessingProgress = useCallback(async (cacheKey: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:8080/api/hand-detection/preprocess-status/${cacheKey}`);
        const result = await response.json();
        
        if (result.success) {
          if (result.status === 'completed') {
            clearInterval(pollInterval);
            setPreprocessingState(prev => ({
              ...prev,
              isProcessing: false,
              progress: 100,
              completed: true
            }));
            
            // Analysis complete - shown in sidebar Messages section
          } else if (result.status === 'in_progress') {
            setPreprocessingState(prev => ({
              ...prev,
              progress: result.progress || 0
            }));
            
            // Log progress for debugging
            if (result.processed_count && result.total_frames) {
              console.log(`Processing progress: Frame ${result.processed_count}/${result.total_frames} (${result.progress?.toFixed(1)}%)`);
            }
          }
        } else {
          clearInterval(pollInterval);
          setPreprocessingState(prev => ({
            ...prev,
            isProcessing: false,
            error: result.error
          }));
        }
      } catch (error) {
        console.error('Polling error:', error);
        clearInterval(pollInterval);
        setPreprocessingState(prev => ({
          ...prev,
          isProcessing: false,
          error: 'Failed to check processing status'
        }));
      }
    }, 2000); // Poll every 2 seconds
  }, []);

  // Start hand preprocessing for both Traditional and QR methods
  const startPreprocessing = useCallback(async () => {
    if (!videoMetadata || rois.length === 0) {
      return;
    }

    // Both methods need hand preprocessing on packing_area
    console.log(`Starting hand preprocessing for ${packingMethod} method`);

    const packingROI = rois.find(roi => roi.type === 'packing_area');
    if (!packingROI) {
      return;
    }

    try {
      setPreprocessingState(prev => ({
        ...prev,
        isProcessing: true,
        progress: 0,
        error: null,
        completed: false
      }));

      // Step 1: Transform ROI_disp → ROI_orig (Canvas coordinates → Video coordinates)
      const roi_orig = {
        x: Math.round(packingROI.x * videoMetadata.resolution.width / canvasDimensions.width),
        y: Math.round(packingROI.y * videoMetadata.resolution.height / canvasDimensions.height),
        w: Math.round(packingROI.w * videoMetadata.resolution.width / canvasDimensions.width),
        h: Math.round(packingROI.h * videoMetadata.resolution.height / canvasDimensions.height)
      };

      console.log('ROI Transform:', {
        'ROI_disp (canvas)': packingROI,
        'ROI_orig (video)': roi_orig,
        'Video size': `${videoMetadata.resolution.width}x${videoMetadata.resolution.height}`,
        'Canvas size': `${canvasDimensions.width}x${canvasDimensions.height}`,
        'Scale factor': `${videoMetadata.resolution.width / canvasDimensions.width}x${videoMetadata.resolution.height / canvasDimensions.height}`
      });

      const response = await fetch('http://localhost:8080/api/hand-detection/preprocess-video', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_path: videoPath,
          roi_config: roi_orig,  // Send ROI_orig instead of ROI_disp
          fps: 5
        })
      });

      const result = await response.json();
      
      if (result.success) {
        setPreprocessingState(prev => ({
          ...prev,
          cacheKey: result.cache_key
        }));

        if (result.status === 'completed') {
          // Pre-processing already completed (cached)
          setPreprocessingState(prev => ({
            ...prev,
            isProcessing: false,
            progress: 100,
            completed: true
          }));
          
          // Analysis ready - shown in sidebar Messages section
        } else {
          // Start polling for progress
          pollPreprocessingProgress(result.cache_key);
        }
      } else {
        throw new Error(result.error || 'Failed to start preprocessing');
      }
    } catch (error) {
      console.error('Preprocessing error:', error);
      setPreprocessingState(prev => ({
        ...prev,
        isProcessing: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      }));
      
      // Processing error - shown in sidebar Messages section
    }
  }, [videoMetadata, rois, packingMethod, videoPath, pollPreprocessingProgress, canvasDimensions]);

  // Use ref to store preprocessing function to avoid circular dependency
  const startPreprocessingRef = useRef<(() => Promise<void>) | null>(null);

  // Update ref when startPreprocessing changes
  useEffect(() => {
    startPreprocessingRef.current = startPreprocessing;
  }, [startPreprocessing]);

  // Helper function to trigger preprocessing (used in setTimeout)
  const triggerPreprocessing = useCallback(() => {
    if (startPreprocessingRef.current) {
      startPreprocessingRef.current();
    }
  }, []);

  // QR preprocessing progress polling
  const pollQRPreprocessingProgress = useCallback(async (cacheKey: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:8080/api/qr-detection/preprocess-status/${cacheKey}`);
        const result = await response.json();
        
        if (result.success && result.status === 'completed') {
          clearInterval(pollInterval);
          setQRPreprocessingState(prev => ({
            ...prev,
            isProcessing: false,
            progress: 100,
            completed: true
          }));
          console.log('QR preprocessing completed');
        } else if (result.success && result.status === 'in_progress') {
          setQRPreprocessingState(prev => ({
            ...prev,
            progress: Math.max(prev.progress, result.progress || 0)
          }));
        } else if (result.status === 'not_found') {
          clearInterval(pollInterval);
          setQRPreprocessingState(prev => ({
            ...prev,
            isProcessing: false,
            error: 'QR processing session expired'
          }));
        }
      } catch (error) {
        console.error('QR polling error:', error);
        clearInterval(pollInterval);
        setQRPreprocessingState(prev => ({
          ...prev,
          isProcessing: false,
          error: 'Failed to check QR processing status'
        }));
      }
    }, 2000); // Poll every 2 seconds
  }, []);

  // Start QR preprocessing for both Traditional and QR methods
  const startQRPreprocessing = useCallback(async () => {
    if (!videoMetadata || rois.length === 0) {
      return;
    }

    const packingROI = rois.find(roi => roi.type === 'packing_area');
    if (!packingROI) {
      return;
    }

    // For QR method, also check trigger ROI
    if (packingMethod === 'qr') {
      const triggerROI = rois.find(roi => roi.type === 'qr_trigger');
      if (!triggerROI) {
        return;
      }
    }

    try {
      setQRPreprocessingState(prev => ({
        ...prev,
        isProcessing: true,
        progress: 0,
        error: null,
        completed: false
      }));

      // Transform ROI coordinates same as hand preprocessing
      const roi_orig = {
        x: Math.round(packingROI.x * videoMetadata.resolution.width / canvasDimensions.width),
        y: Math.round(packingROI.y * videoMetadata.resolution.height / canvasDimensions.height),
        w: Math.round(packingROI.w * videoMetadata.resolution.width / canvasDimensions.width),
        h: Math.round(packingROI.h * videoMetadata.resolution.height / canvasDimensions.height)
      };

      console.log('QR ROI Transform:', {
        'ROI_disp (canvas)': packingROI,
        'ROI_orig (video)': roi_orig,
        'Video size': `${videoMetadata.resolution.width}x${videoMetadata.resolution.height}`,
        'Canvas size': `${canvasDimensions.width}x${canvasDimensions.height}`
      });

      const response = await fetch('http://localhost:8080/api/qr-detection/preprocess-video', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_path: videoPath,
          roi_config: roi_orig,  // Send video coordinates
          fps: 5
        })
      });

      const result = await response.json();
      
      if (result.success) {
        setQRPreprocessingState(prev => ({
          ...prev,
          cacheKey: result.cache_key
        }));

        if (result.status === 'completed') {
          // QR pre-processing already completed (cached)
          setQRPreprocessingState(prev => ({
            ...prev,
            isProcessing: false,
            progress: 100,
            completed: true
          }));
          console.log('QR preprocessing already completed');
        } else {
          // Start polling for QR progress
          pollQRPreprocessingProgress(result.cache_key);
        }
      } else {
        throw new Error(result.error || 'Failed to start QR preprocessing');
      }
    } catch (error) {
      console.error('QR preprocessing error:', error);
      setQRPreprocessingState(prev => ({
        ...prev,
        isProcessing: false,
        error: error instanceof Error ? error.message : 'Unknown QR error'
      }));
    }
  }, [videoMetadata, rois, packingMethod, videoPath, pollQRPreprocessingProgress, canvasDimensions]);

  // Modified startPreprocessing to trigger both hand and QR preprocessing
  const startBothPreprocessing = useCallback(async () => {
    if (!videoMetadata || rois.length === 0) {
      return;
    }

    // Validate required ROIs based on method
    const packingROI = rois.find(roi => roi.type === 'packing_area');
    if (!packingROI) {
      return;
    }

    if (packingMethod === 'qr') {
      const triggerROI = rois.find(roi => roi.type === 'qr_trigger');
      if (!triggerROI) {
        return;
      }
    }

    console.log(`Starting dual preprocessing for ${packingMethod} method: Hand + QR detection`);
    
    // Reset waiting state when starting new preprocessing
    setIsWaitingForAnalysis(false);
    setHandLandmarks(null);
    
    // Start both preprocessing processes in parallel
    await Promise.all([
      startPreprocessing(),      // Hand preprocessing on packing area
      startQRPreprocessing()     // QR preprocessing on packing area (+ trigger area for QR method)
    ]);
  }, [startPreprocessing, startQRPreprocessing, videoMetadata, rois, packingMethod]);

  // Update the ref to use both preprocessing
  const startBothPreprocessingRef = useRef<(() => Promise<void>) | null>(null);
  
  useEffect(() => {
    startBothPreprocessingRef.current = startBothPreprocessing;
  }, [startBothPreprocessing]);

  // Updated trigger function for both preprocessing
  const triggerBothPreprocessing = useCallback(() => {
    if (startBothPreprocessingRef.current) {
      startBothPreprocessingRef.current();
    }
  }, []);

  // Save configuration
  const handleSaveConfiguration = useCallback(async () => {
    if (!videoMetadata) {
      setError('Video metadata not loaded');
      return;
    }

    // Validate required ROIs
    if (packingMethod === 'traditional') {
      const hasPackingArea = rois.some(roi => roi.type === 'packing_area');
      if (!hasPackingArea) {
        setError('Please draw a Packing Area ROI');
        return;
      }
    } else {
      // QR mode requires both Trigger Area and Packing Area (in this order)
      const hasTriggerArea = rois.some(roi => roi.type === 'qr_trigger');
      const hasPackingArea = rois.some(roi => roi.type === 'packing_area');
      
      if (!hasTriggerArea) {
        setError('Please draw a Trigger Area ROI first');
        return;
      }
      if (!hasPackingArea) {
        setError('Please draw a Packing Area ROI');
        return;
      }
    }

    setIsSaving(true);
    setError(null);

    try {
      // Transform ROI coordinates to original video coordinates for validation
      const originalCoordinateROIs = rois.map(roi => {
        const originalCoords = convertToOriginalCoordinates(roi);
        return {
          x: originalCoords.x,
          y: originalCoords.y,
          w: originalCoords.w,
          h: originalCoords.h,
          type: roi.type,
          label: roi.label
        };
      });

      // Validate ROIs with backend
      const validationResponse = await fetch('/api/config/step4/roi/validate-roi', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_path: videoPath,
          roi_data: originalCoordinateROIs
        })
      });

      if (!validationResponse.ok) {
        throw new Error(`ROI validation failed: ${validationResponse.status}`);
      }

      const validationResult = await validationResponse.json();
      
      if (!validationResult.success) {
        throw new Error(validationResult.error || 'ROI validation failed');
      }

      // Save configuration (using already-transformed coordinates from validation)
      const saveResponse = await fetch('/api/config/step4/roi/save-roi-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          camera_id: cameraId,
          video_path: videoPath,
          roi_data: originalCoordinateROIs,
          packing_method: packingMethod
        })
      });

      if (!saveResponse.ok) {
        throw new Error(`Configuration save failed: ${saveResponse.status}`);
      }

      const saveResult = await saveResponse.json();
      
      if (!saveResult.success) {
        throw new Error(saveResult.error || 'Configuration save failed');
      }

      // Success
      // Configuration saved successfully - user will see modal close

      // Call parent save handler
      onSave?.({
        cameraId,
        videoPath,
        rois,
        packingMethod,
        videoMetadata
      });

      // Close modal
      onClose();

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      console.error('Error saving ROI configuration:', errorMessage);
      setError(errorMessage);
      onError?.(errorMessage);

      // Save error - shown in sidebar Messages section via setError
    } finally {
      setIsSaving(false);
    }
  }, [
    videoMetadata,
    rois,
    videoPath,
    cameraId,
    packingMethod,
    onSave,
    onClose,
    onError,
    toast
  ]);

  // Reset state when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setROIs([]);
      setSelectedROIId(null);
      setError(null);
      setHandLandmarks(null);
      setIsVideoPlaying(false);
      setPreprocessingState({
        isProcessing: false,
        progress: 0,
        cacheKey: null,
        completed: false,
        error: null
      });
    }
  }, [isOpen]);

  // Check if all required ROIs are created
  const allRequiredCompleted = useMemo(() => {
    if (packingMethod === 'traditional') {
      return rois.some(roi => roi.type === 'packing_area');
    } else {
      // QR mode requires both Packing Area and Trigger Area
      return rois.some(roi => roi.type === 'packing_area') && rois.some(roi => roi.type === 'qr_trigger');
    }
  }, [packingMethod, rois]);

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose}
      size="full"
      closeOnOverlayClick={false}
      closeOnEsc={false}
    >
      <ModalOverlay bg="blackAlpha.800" />
      <ModalContent 
        maxW="100vw" 
        maxH="100vh" 
        m="0" 
        borderRadius="0"
        bg={bgColor}
        data-testid="modal-content"
      >
        <ModalCloseButton size="lg" />
        
        <ModalBody p="0" h="100vh" overflow="hidden">
          <Flex h="100%" direction="row">
            
            {/* Left Panel - Instructions & Steps */}
            <Box 
              w="256px" 
              bg={panelBg} 
              borderRight="1px solid" 
              borderColor={borderColor}
              p={adaptiveConfig.spacing.padding}
              overflowY="auto"
              h="100vh"
            >
              <VStack spacing={adaptiveConfig.spacing.section} align="stretch">
                
                {/* Header */}
                <Box>
                  <Text fontSize={adaptiveConfig.fontSize.header} fontWeight="bold" color={textColor} mb={adaptiveConfig.spacing.item}>
                    🎯 ROI Configuration
                  </Text>
                  <Text fontSize={adaptiveConfig.fontSize.body} color={secondaryText}>
                    Camera: {cameraId}
                  </Text>
                  <Text fontSize={adaptiveConfig.fontSize.body} color={secondaryText}>
                    Method: {packingMethod === 'traditional' ? 'Traditional Detection' : 'QR Code Detection'}
                  </Text>
                </Box>



                {/* ROI List */}
                {rois.length > 0 && (
                  <Box>
                    <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="medium" color={textColor} mb={adaptiveConfig.spacing.item}>
                      Created ROIs ({rois.length})
                    </Text>
                    <VStack spacing={adaptiveConfig.spacing.item} align="stretch">
                      {rois.map((roi) => (
                        <Box
                          key={roi.id}
                          p={adaptiveConfig.spacing.item}
                          borderRadius="6px"
                          border="1px solid"
                          borderColor={selectedROIId === roi.id ? roi.color : borderColor}
                          bg={selectedROIId === roi.id ? `${roi.color}10` : 'white'}
                          cursor="pointer"
                          onClick={() => setSelectedROIId(roi.id)}
                        >
                          <HStack justify="space-between">
                            <VStack align="start" spacing="2px" flex="1">
                              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="medium">
                                {roi.label}
                              </Text>
                              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
                                {(() => {
                                  const original = convertToOriginalCoordinates(roi);
                                  return `${roi.type} • Position: (${original.x}, ${original.y}) • Size: ${original.w}×${original.h}px`;
                                })()}
                              </Text>
                            </VStack>
                            <IconButton
                              aria-label="Delete ROI"
                              icon={<FaTrash />}
                              size="xs"
                              colorScheme="red"
                              variant="ghost"
                              onClick={() => handleROIDelete(roi.id)}
                            />
                          </HStack>
                        </Box>
                      ))}
                    </VStack>
                  </Box>
                )}

                {/* Action Buttons */}
                <VStack spacing={adaptiveConfig.spacing.item} align="stretch">
                  <Button
                    colorScheme="blue"
                    size={adaptiveConfig.mode === 'compact' ? 'sm' : 'md'}
                    onClick={handleSaveConfiguration}
                    isLoading={isSaving}
                    loadingText="Saving..."
                    isDisabled={!allRequiredCompleted}
                  >
                    Save Configuration
                  </Button>
                  
                  <Button
                    variant="outline"
                    size={adaptiveConfig.mode === 'compact' ? 'sm' : 'md'}
                    onClick={onClose}
                    isDisabled={isSaving}
                  >
                    Cancel
                  </Button>
                  
                  {!allRequiredCompleted && (
                    <Text fontSize={adaptiveConfig.fontSize.small} color="orange.500" textAlign="center">
                      Complete all required steps to save
                    </Text>
                  )}
                </VStack>

                <Divider />

                {/* Messages & Status - Highlighted Section */}
                <Box p="12px" bg="blue.50" borderRadius="8px" border="2px solid" borderColor="blue.200">
                  <Text fontSize="sm" fontWeight="bold" color="blue.800" mb="8px">
                    📋 Status & Instructions
                  </Text>

                  {/* Error Alert */}
                  {error && (
                    <Alert status="error" size="sm" borderRadius="6px" mb="8px">
                      <AlertIcon boxSize="14px" />
                      <Box>
                        <AlertTitle fontSize="xs">Error!</AlertTitle>
                        <AlertDescription fontSize="xs">{error}</AlertDescription>
                      </Box>
                    </Alert>
                  )}

                  {/* Instructions */}
                  {rois.length === 0 && (
                    <Box p="8px" bg="gray.50" borderRadius="6px" mb="8px">
                      <Text fontSize="xs" color={secondaryText}>
                        💡 Click and drag on the video to create ROI rectangles. 
                        Double-click an existing ROI to delete it.
                      </Text>
                    </Box>
                  )}

                  {/* Pre-processing Status */}
                  {rois.length > 0 && videoMetadata && packingMethod === 'traditional' && (
                    <>
                      {preprocessingState.isProcessing && (
                        <Box p="8px" bg="blue.100" borderRadius="6px" mb="8px">
                          <Text fontSize="xs" fontWeight="medium" mb="4px">
                            🤖 Processing hand analysis...
                          </Text>
                          <Box w="100%" bg="gray.200" borderRadius="2px" h="4px" mb="4px">
                            <Box 
                              w={`${preprocessingState.progress}%`} 
                              bg="blue.500" 
                              borderRadius="2px" 
                              h="100%" 
                              transition="width 0.3s ease"
                            />
                          </Box>
                          <Text fontSize="2xs" color={secondaryText}>
                            Progress: {preprocessingState.progress.toFixed(1)}%
                          </Text>
                        </Box>
                      )}

                      {/* Waiting for analysis message */}
                      {isWaitingForAnalysis && (
                        <Box p="8px" bg="orange.100" borderRadius="6px" mb="8px">
                          <Text fontSize="xs" fontWeight="medium" color="orange.700" mb="2px">
                            ⏳ Đang phân tích...
                          </Text>
                          <Text fontSize="2xs" color="orange.600">
                            Video tạm dừng, chờ phân tích hoàn tất
                          </Text>
                        </Box>
                      )}

                      {preprocessingState.completed && !isVideoPlaying && !isWaitingForAnalysis && (
                        <Box p="8px" bg="green.100" borderRadius="6px" mb="8px">
                          <Text fontSize="xs" fontWeight="medium" color="green.700" mb="2px">
                            ✅ Analysis Ready
                          </Text>
                          <Text fontSize="2xs" color="green.600">
                            Press Play to see results!
                          </Text>
                        </Box>
                      )}

                      {preprocessingState.error && (
                        <Box p="8px" bg="red.100" borderRadius="6px" mb="8px">
                          <Text fontSize="xs" fontWeight="medium" color="red.700" mb="2px">
                            ❌ Processing Error
                          </Text>
                          <Text fontSize="2xs" color="red.600" mb="4px">
                            {preprocessingState.error}
                          </Text>
                          <Button size="xs" colorScheme="red" variant="outline" onClick={startPreprocessing}>
                            Try Again
                          </Button>
                        </Box>
                      )}

                      {!preprocessingState.isProcessing && !preprocessingState.completed && !preprocessingState.error && rois.some(roi => roi.type === 'packing_area') && (
                        <Box p="8px" bg="blue.100" borderRadius="6px" mb="8px">
                          <Text fontSize="xs" fontWeight="medium" color="blue.700" mb="2px">
                            🎯 ROI Created
                          </Text>
                          <Text fontSize="2xs" color="blue.600" mb="4px">
                            Start hand detection processing
                          </Text>
                          <Button size="xs" colorScheme="blue" onClick={startPreprocessing}>
                            Start Analysis
                          </Button>
                        </Box>
                      )}
                    </>
                  )}
                </Box>

              </VStack>
            </Box>

            {/* Center Panel - Video & Canvas */}
            <Box 
              ref={containerRef}
              flex="1" 
              display="flex" 
              flexDirection="column" 
              alignItems="center" 
              justifyContent="center"
              overflow="visible" 
              minHeight="0"
              position="relative"
              css={{
                '&::-webkit-scrollbar': {
                  width: '6px',
                },
                '&::-webkit-scrollbar-track': {
                  background: 'var(--chakra-colors-gray-100)',
                },
                '&::-webkit-scrollbar-thumb': {
                  background: 'var(--chakra-colors-gray-300)',
                  borderRadius: '3px',
                },
                '&::-webkit-scrollbar-thumb:hover': {
                  background: 'var(--chakra-colors-gray-400)',
                },
                overflowY: 'auto',
                overflowX: 'hidden',
              }}
            >

              {/* SIMPLE 2-CANVAS LAYOUT: Video trên + Controls dưới */}
              <Flex 
                direction="column"
                width="100%" 
                height="100%" 
                p={adaptiveConfig.spacing.padding}
              >
                {/* 1. PureVideoCanvas - Phần trên (flex=1) */}
                <Box 
                  flex="1"
                  width="100%" 
                  display="flex" 
                  alignItems="center" 
                  justifyContent="center"
                  minH="0"
                >
                  <PureVideoCanvas
                    videoPath={videoPath}
                    width={fullScreenDimensions.width}
                    height={fullScreenDimensions.height} // Full available height in flex container
                    onMetadataLoaded={handleMetadataLoaded}
                    onTimeUpdate={(currentTime) => getLandmarksAtCurrentTime(currentTime)}
                    onVideoRef={(ref) => { videoRef.current = ref; }}
                    onPlayStateChange={handleVideoPlayStateChange}
                    autoPlay={false}
                    muted={true}
                    
                    // Adaptive config props (copied from CanvasMessage.tsx pattern)
                    adaptiveConfig={adaptiveConfig}
                    availableHeight={availableHeight}
                    
                    // ROI props
                    rois={rois}
                    selectedROIId={selectedROIId}
                    currentROIType={packingMethod === 'traditional' ? 'packing_area' : (!rois.some(roi => roi.type === 'qr_trigger') ? 'qr_trigger' : 'packing_area')}
                    currentROILabel={packingMethod === 'traditional' ? 'Packing Area' : (!rois.some(roi => roi.type === 'qr_trigger') ? 'Trigger Area' : 'Packing Area')}
                    disabled={(packingMethod === 'traditional' && rois.some(roi => roi.type === 'packing_area')) || (packingMethod === 'qr' && rois.some(roi => roi.type === 'qr_trigger') && rois.some(roi => roi.type === 'packing_area'))}
                    showLandmarks={isVideoPlaying && rois.length > 0}
                    landmarks={handLandmarks}
                    
                    // Hand landmarks props
                    handLandmarks={handLandmarks}
                    showHandLandmarks={isVideoPlaying && rois.length > 0}
                    
                    // ROI callbacks  
                    onROICreate={handleROICreate}
                    onROIUpdate={handleROIUpdate}
                    onROIDelete={handleROIDelete}
                    onROISelect={handleROISelect}
                  />
                </Box>

                {/* 2. VideoControlsBar - Phần dưới (fixed height) */}
                <Box 
                  width="100%"
                  display="flex" 
                  alignItems="center" 
                  justifyContent="center"
                  pb="10px"
                  flexShrink={0}
                  minH="60px"
                >
                  <VideoControlsBar
                    videoRef={videoRef}
                    width={Math.min(800, fullScreenDimensions.width)}
                    height={54} // Chat input height pattern (54px)
                    onControlStateChange={setVideoControlsState}
                    
                    // Adaptive config props (copied from CanvasMessage.tsx pattern)
                    adaptiveConfig={adaptiveConfig}
                    availableHeight={availableHeight}
                  />
                </Box>
              </Flex>


            </Box>

          </Flex>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default ROIConfigModal;