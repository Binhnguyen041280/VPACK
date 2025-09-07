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
import VideoPlayer from './VideoPlayer';
import CanvasOverlay, { ROIData, HandLandmarks } from './CanvasOverlay';
// Generate unique IDs without external dependency
const generateId = () => Math.random().toString(36).substr(2, 9);

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


// Video player dimensions (define as constants outside component)
const VIDEO_PLAYER_WIDTH = 960;
const VIDEO_PLAYER_HEIGHT = 540;

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
  const [isVideoPlaying, setIsVideoPlaying] = useState(false);
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

  // Full screen state
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [fullScreenDimensions, setFullScreenDimensions] = useState<{
    width: number;
    height: number;
  }>({
    width: VIDEO_PLAYER_WIDTH,
    height: VIDEO_PLAYER_HEIGHT
  });

  // Toast for notifications
  const toast = useToast();

  // Theme colors
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const panelBg = useColorModeValue('gray.50', 'gray.700');
  const textColor = useColorModeValue('gray.800', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');




  // Full screen functions
  const enterFullScreen = useCallback(async () => {
    try {
      const modalContent = document.querySelector('[data-testid="modal-content"]') || document.documentElement;
      if (modalContent.requestFullscreen) {
        await modalContent.requestFullscreen();
      }
    } catch (error) {
      console.warn('Cannot enter fullscreen:', error);
      toast({
        title: 'Cannot enter fullscreen',
        description: 'Browser does not support or blocked fullscreen',
        status: 'warning',
        duration: 3000
      });
    }
  }, [toast]);

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
        
        if (videoMetadata) {
          const videoAspectRatio = videoMetadata.resolution.width / videoMetadata.resolution.height;
          
          let displayWidth, displayHeight;
          if (videoAspectRatio > screenAspectRatio) {
            // Video wider than screen - fit to width
            displayWidth = screenWidth;
            displayHeight = screenWidth / videoAspectRatio;
          } else {
            // Video taller than screen - fit to height  
            displayHeight = screenHeight;
            displayWidth = screenHeight * videoAspectRatio;
          }
          
          setFullScreenDimensions({
            width: displayWidth,
            height: displayHeight
          });
          
          console.log('Full Screen Mode:', {
            screen: `${screenWidth}x${screenHeight}`,
            video: `${videoMetadata.resolution.width}x${videoMetadata.resolution.height}`,
            display: `${displayWidth.toFixed(0)}x${displayHeight.toFixed(0)}`
          });
        }
      } else {
        // Reset to normal dimensions
        setFullScreenDimensions({
          width: VIDEO_PLAYER_WIDTH,
          height: VIDEO_PLAYER_HEIGHT
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
  }, [videoMetadata]);

  // Handle video metadata loaded
  const handleMetadataLoaded = useCallback((metadata: VideoMetadata) => {
    console.log('Video metadata loaded:', metadata);
    setVideoMetadata(metadata);
    setError(null);
  }, []);

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
          toast({
            title: 'Cannot Create ROI',
            description: 'Only one Packing Area is allowed in Traditional mode',
            status: 'warning',
            duration: 4000,
            isClosable: true
          });
          return null;
        }
        return { type: 'packing_area', label: 'Packing Area' };
      } else {
        // For QR method, allow 2 specific areas: Trigger first, then Packing
        const existingTriggerArea = rois.some(roi => roi.type === 'qr_trigger');
        const existingPackingArea = rois.some(roi => roi.type === 'packing_area');
        
        // If both areas already exist, prevent creation
        if (existingTriggerArea && existingPackingArea) {
          toast({
            title: 'Cannot Create ROI',
            description: 'Maximum of 2 areas allowed: Trigger Area and Packing Area',
            status: 'warning',
            duration: 4000,
            isClosable: true
          });
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

    toast({
      title: 'ROI Created',
      description: `${newROI.label} has been created`,
      status: 'success',
      duration: 3000,
      isClosable: true
    });

    console.log('ROI created:', newROI);

    // Set flag to trigger preprocessing after ROI creation
    if (packingMethod === 'traditional' && type === 'packing_area') {
      // Use setTimeout to trigger preprocessing after ROI state is updated
      setTimeout(() => {
        // Call preprocessing function directly - will be defined below
        triggerPreprocessing();
      }, 500);
    }
  }, [packingMethod, rois, toast]);

  // Handle ROI update
  const handleROIUpdate = useCallback((id: string, updates: Partial<ROIData>) => {
    setROIs(prev => prev.map(roi => 
      roi.id === id ? { ...roi, ...updates } : roi
    ));
    
    // Clear cache when ROI is modified - data is no longer valid
    if (preprocessingState.cacheKey) {
      // Clear cache on backend
      fetch(`http://localhost:8080/api/hand-detection/clear-cache/${preprocessingState.cacheKey}`, {
        method: 'DELETE'
      }).catch(error => console.warn('Failed to clear backend cache:', error));
      
      setPreprocessingState(prev => ({
        ...prev,
        completed: false,
        cacheKey: null,
        error: null
      }));
      
      setHandLandmarks(null);
      
      toast({
        title: 'ROI Changed',
        description: 'Hand detection needs to be reprocessed for new ROI',
        status: 'info',
        duration: 3000
      });
    }
  }, [preprocessingState.cacheKey, toast]);

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
      // Clear cache on backend
      fetch(`http://localhost:8080/api/hand-detection/clear-cache/${preprocessingState.cacheKey}`, {
        method: 'DELETE'
      }).catch(error => console.warn('Failed to clear backend cache:', error));
      
      setPreprocessingState(prev => ({
        ...prev,
        completed: false,
        cacheKey: null,
        error: null,
        isProcessing: false,
        progress: 0
      }));
      
      setHandLandmarks(null);
      
      toast({
        title: 'ROI Deleted',
        description: 'Hand detection cache cleared. Draw new ROI to start again.',
        status: 'info',
        duration: 4000
      });
    } else {
      toast({
        title: 'ROI Deleted',
        description: `${roiToDelete.label} has been deleted`,
        status: 'info',
        duration: 3000,
        isClosable: true
      });
    }

    console.log('ROI deleted:', roiToDelete);
  }, [rois, selectedROIId, preprocessingState.cacheKey, toast]);

  // Handle ROI selection
  const handleROISelect = useCallback((id: string | null) => {
    setSelectedROIId(id);
    console.log('ROI selected:', id);
  }, []);



  // Get landmarks from cached results based on current video time (PROGRESSIVE DISPLAY)
  const getLandmarksAtCurrentTime = useCallback(async (currentTime: number) => {
    if (!videoMetadata || rois.length === 0 || !isVideoPlaying || !preprocessingState.cacheKey) {
      setHandLandmarks(null);
      return;
    }

    // Only detect for packing areas in traditional method
    const packingROI = rois.find(roi => roi.type === 'packing_area');
    if (!packingROI || packingMethod !== 'traditional') {
      setHandLandmarks(null);
      return;
    }

    try {
      const response = await fetch('http://localhost:8080/api/hand-detection/get-cached-landmarks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cache_key: preprocessingState.cacheKey,
          timestamp: currentTime
        })
      });

      const result = await response.json();
      
      if (result.success && result.landmarks && result.landmarks.length > 0) {
        setHandLandmarks({
          landmarks: result.landmarks,
          confidence: result.confidence,
          hands_detected: result.landmarks.length
        });
      } else {
        setHandLandmarks(null);
      }
    } catch (error) {
      // Don't log error for incomplete processing - this is expected
      if (!preprocessingState.completed) {
        console.debug('Cache not ready yet for current timestamp:', currentTime);
      } else {
        console.error('Error getting cached landmarks:', error);
      }
      setHandLandmarks(null);
    }
  }, [videoMetadata, rois, packingMethod, isVideoPlaying, preprocessingState.cacheKey, preprocessingState.completed]);

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
            
            toast({
              title: 'Analysis Complete',
              description: `Processed ${result.detections?.length || 0} frames. Press Play to see results!`,
              status: 'success',
              duration: 4000
            });
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
  }, [toast]);

  // Start pre-processing when ROI is created
  const startPreprocessing = useCallback(async () => {
    if (!videoMetadata || rois.length === 0 || packingMethod !== 'traditional') {
      return;
    }

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
        x: Math.round(packingROI.x * videoMetadata.resolution.width / VIDEO_PLAYER_WIDTH),
        y: Math.round(packingROI.y * videoMetadata.resolution.height / VIDEO_PLAYER_HEIGHT),
        w: Math.round(packingROI.w * videoMetadata.resolution.width / VIDEO_PLAYER_WIDTH),
        h: Math.round(packingROI.h * videoMetadata.resolution.height / VIDEO_PLAYER_HEIGHT)
      };

      console.log('ROI Transform:', {
        'ROI_disp (canvas)': packingROI,
        'ROI_orig (video)': roi_orig,
        'Video size': `${videoMetadata.resolution.width}x${videoMetadata.resolution.height}`,
        'Canvas size': `${VIDEO_PLAYER_WIDTH}x${VIDEO_PLAYER_HEIGHT}`,
        'Scale factor': `${videoMetadata.resolution.width / VIDEO_PLAYER_WIDTH}x${videoMetadata.resolution.height / VIDEO_PLAYER_HEIGHT}`
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
          
          toast({
            title: 'Analysis Ready',
            description: 'Hand detection data is ready. Press Play to see results!',
            status: 'success',
            duration: 3000
          });
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
      
      toast({
        title: 'Processing Error',
        description: 'Cannot process hand detection. Please try again.',
        status: 'error',
        duration: 5000
      });
    }
  }, [videoMetadata, rois, packingMethod, videoPath, toast, pollPreprocessingProgress]);

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
      // Validate ROIs with backend
      const validationResponse = await fetch('/api/config/step4/roi/validate-roi', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_path: videoPath,
          roi_data: rois.map(roi => ({
            x: roi.x,
            y: roi.y,
            w: roi.w,
            h: roi.h,
            type: roi.type,
            label: roi.label
          }))
        })
      });

      if (!validationResponse.ok) {
        throw new Error(`ROI validation failed: ${validationResponse.status}`);
      }

      const validationResult = await validationResponse.json();
      
      if (!validationResult.success) {
        throw new Error(validationResult.error || 'ROI validation failed');
      }

      // Save configuration
      const saveResponse = await fetch('/api/config/step4/roi/save-roi-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          camera_id: cameraId,
          video_path: videoPath,
          roi_data: validationResult.data.validated_rois,
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
      toast({
        title: 'Configuration Saved',
        description: `ROI configuration for camera ${cameraId} has been saved successfully`,
        status: 'success',
        duration: 5000,
        isClosable: true
      });

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

      toast({
        title: 'Save Failed',
        description: errorMessage,
        status: 'error',
        duration: 5000,
        isClosable: true
      });
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
              p="16px"
              overflowY="auto"
              h="100vh"
            >
              <VStack spacing="24px" align="stretch">
                
                {/* Header */}
                <Box>
                  <Text fontSize="xl" fontWeight="bold" color={textColor} mb="8px">
                    ROI Configuration
                  </Text>
                  <Text fontSize="sm" color={secondaryText}>
                    Camera: {cameraId}
                  </Text>
                  <Text fontSize="sm" color={secondaryText}>
                    Method: {packingMethod === 'traditional' ? 'Traditional Detection' : 'QR Code Detection'}
                  </Text>
                </Box>



                {/* ROI List */}
                {rois.length > 0 && (
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" color={textColor} mb="8px">
                      Created ROIs ({rois.length})
                    </Text>
                    <VStack spacing="8px" align="stretch">
                      {rois.map((roi) => (
                        <Box
                          key={roi.id}
                          p="8px"
                          borderRadius="6px"
                          border="1px solid"
                          borderColor={selectedROIId === roi.id ? roi.color : borderColor}
                          bg={selectedROIId === roi.id ? `${roi.color}10` : 'white'}
                          cursor="pointer"
                          onClick={() => setSelectedROIId(roi.id)}
                        >
                          <HStack justify="space-between">
                            <VStack align="start" spacing="2px" flex="1">
                              <Text fontSize="sm" fontWeight="medium">
                                {roi.label}
                              </Text>
                              <Text fontSize="xs" color={secondaryText}>
                                {roi.type} • Position: ({roi.x}, {roi.y}) • Size: {roi.w}×{roi.h}px
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
                <VStack spacing="12px" align="stretch">
                  <Button
                    colorScheme="blue"
                    size="md"
                    onClick={handleSaveConfiguration}
                    isLoading={isSaving}
                    loadingText="Saving..."
                    isDisabled={!allRequiredCompleted}
                  >
                    Save Configuration
                  </Button>
                  
                  <Button
                    variant="outline"
                    size="md"
                    onClick={onClose}
                    isDisabled={isSaving}
                  >
                    Cancel
                  </Button>
                  
                  {!allRequiredCompleted && (
                    <Text fontSize="xs" color="orange.500" textAlign="center">
                      Complete all required steps to save
                    </Text>
                  )}
                </VStack>

              </VStack>
            </Box>

            {/* Center Panel - Video & Canvas */}
            <Box flex="1" p="20px" display="flex" flexDirection="column" alignItems="center" justifyContent="center">

              {/* Error Alert */}
              {error && (
                <Alert status="error" borderRadius="8px" mb="20px" maxW={`${fullScreenDimensions.width}px`}>
                  <AlertIcon />
                  <Box>
                    <AlertTitle>Configuration Error</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                  </Box>
                </Alert>
              )}

              {/* Video Player Container */}
              <Box 
                position="relative"
                width={`${fullScreenDimensions.width}px`}
                height={`${fullScreenDimensions.height}px`}
                borderRadius={isFullScreen ? "0" : "8px"}
                overflow="hidden"
                border={isFullScreen ? "none" : "2px solid"}
                borderColor={borderColor}
                margin="0 auto"  // Center trong full screen
              >
                {/* Video Player */}
                <VideoPlayer
                  videoPath={videoPath}
                  onMetadataLoaded={handleMetadataLoaded}
                  onTimeUpdate={(currentTime) => getLandmarksAtCurrentTime(currentTime)}
                  onPlayStateChange={handleVideoPlayStateChange}
                  onVideoError={handleVideoError}
                  width={`${fullScreenDimensions.width}px`}
                  height={`${fullScreenDimensions.height}px`}
                  showControls={true}
                  autoPlay={true}
                />

                {/* Canvas Overlay */}
                {videoMetadata && (
                  <CanvasOverlay
                    width={fullScreenDimensions.width}
                    height={fullScreenDimensions.height - (isFullScreen ? 120 : 80)} // More space for controls in full screen
                    videoWidth={videoMetadata.resolution.width}
                    videoHeight={videoMetadata.resolution.height}
                    rois={rois}
                    onROICreate={handleROICreate}
                    onROIUpdate={handleROIUpdate}
                    onROIDelete={handleROIDelete}
                    onROISelect={handleROISelect}
                    selectedROIId={selectedROIId}
                    currentROIType={packingMethod === 'traditional' ? 'packing_area' : (!rois.some(roi => roi.type === 'qr_trigger') ? 'qr_trigger' : 'packing_area')}
                    currentROILabel={packingMethod === 'traditional' ? 'Packing Area' : (!rois.some(roi => roi.type === 'qr_trigger') ? 'Trigger Area' : 'Packing Area')}
                    packingMethod={packingMethod}
                    disabled={(packingMethod === 'traditional' && rois.some(roi => roi.type === 'packing_area')) || (packingMethod === 'qr' && rois.some(roi => roi.type === 'qr_trigger') && rois.some(roi => roi.type === 'packing_area'))}
                    handLandmarks={handLandmarks}
                    showHandLandmarks={isVideoPlaying && rois.length > 0}
                    landmarksColor="#00FF00"
                    landmarksSize={4}
                  />
                )}
              </Box>


              {/* Instructions */}
              {rois.length === 0 && (
                <Text fontSize="sm" color={secondaryText} mt="16px" textAlign="center" maxW={`${fullScreenDimensions.width}px`}>
                  Click and drag on the video to create ROI rectangles. 
                  Double-click an existing ROI to delete it.
                </Text>
              )}


              {/* Pre-processing Status */}
              {rois.length > 0 && videoMetadata && packingMethod === 'traditional' && (
                <Box mt="16px" width={`${fullScreenDimensions.width}px`}>
                  {preprocessingState.isProcessing && (
                    <Box p="16px" bg={panelBg} borderRadius="8px">
                      <Text fontSize="sm" fontWeight="medium" mb="8px">
                        🤖 Processing hand analysis...
                      </Text>
                      <Box w="100%" bg="gray.200" borderRadius="4px" h="8px" mb="8px">
                        <Box 
                          w={`${preprocessingState.progress}%`} 
                          bg="blue.500" 
                          borderRadius="4px" 
                          h="100%" 
                          transition="width 0.3s ease"
                        />
                      </Box>
                      <Text fontSize="xs" color={secondaryText}>
                        Progress: {preprocessingState.progress.toFixed(1)}% - Please wait...
                      </Text>
                    </Box>
                  )}

                  {preprocessingState.completed && !isVideoPlaying && (
                    <Box p="16px" bg="green.50" borderColor="green.200" border="1px solid" borderRadius="8px">
                      <Text fontSize="sm" fontWeight="medium" color="green.700" mb="4px">
                        ✅ Analysis Ready
                      </Text>
                      <Text fontSize="xs" color="green.600">
                        Press Play to see perfectly synchronized hand detection results!
                      </Text>
                    </Box>
                  )}

                  {preprocessingState.error && (
                    <Box p="16px" bg="red.50" borderColor="red.200" border="1px solid" borderRadius="8px">
                      <Text fontSize="sm" fontWeight="medium" color="red.700" mb="4px">
                        ❌ Processing Error
                      </Text>
                      <Text fontSize="xs" color="red.600">
                        {preprocessingState.error}
                      </Text>
                      <Button size="xs" colorScheme="red" variant="outline" mt="8px" onClick={startPreprocessing}>
                        Try Again
                      </Button>
                    </Box>
                  )}

                  {!preprocessingState.isProcessing && !preprocessingState.completed && !preprocessingState.error && rois.some(roi => roi.type === 'packing_area') && (
                    <Box p="16px" bg="blue.50" borderColor="blue.200" border="1px solid" borderRadius="8px">
                      <Text fontSize="sm" fontWeight="medium" color="blue.700" mb="4px">
                        🎯 ROI Created
                      </Text>
                      <Text fontSize="xs" color="blue.600" mb="8px">
                        Click the button below to start hand detection processing
                      </Text>
                      <Button size="sm" colorScheme="blue" onClick={startPreprocessing}>
                        Start Analysis
                      </Button>
                    </Box>
                  )}
                </Box>
              )}
              


            </Box>

          </Flex>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default ROIConfigModal;