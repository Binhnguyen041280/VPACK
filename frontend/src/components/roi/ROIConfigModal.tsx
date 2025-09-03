/**
 * ROIConfigModal Component
 * Full-screen modal for ROI configuration with video player and interactive canvas
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
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
import CanvasOverlay, { ROIData } from './CanvasOverlay';
import DualAnalysisCanvas from './DualAnalysisCanvas';
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
  const [analysisSessionId, setAnalysisSessionId] = useState<string | null>(null);
  const [showAnalysis, setShowAnalysis] = useState(false);

  // Toast for notifications
  const toast = useToast();

  // Theme colors
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const panelBg = useColorModeValue('gray.50', 'gray.700');
  const textColor = useColorModeValue('gray.800', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');



  // Video player dimensions (maintain aspect ratio)
  const videoPlayerWidth = 960;
  const videoPlayerHeight = 540;

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
  }, [packingMethod, rois, toast]);

  // Handle ROI update
  const handleROIUpdate = useCallback((id: string, updates: Partial<ROIData>) => {
    setROIs(prev => prev.map(roi => 
      roi.id === id ? { ...roi, ...updates } : roi
    ));
  }, []);

  // Handle ROI deletion
  const handleROIDelete = useCallback((id: string) => {
    const roiToDelete = rois.find(roi => roi.id === id);
    if (!roiToDelete) return;

    setROIs(prev => prev.filter(roi => roi.id !== id));
    
    if (selectedROIId === id) {
      setSelectedROIId(null);
    }

    toast({
      title: 'ROI Deleted',
      description: `${roiToDelete.label} has been deleted`,
      status: 'info',
      duration: 3000,
      isClosable: true
    });

    console.log('ROI deleted:', roiToDelete);
  }, [rois, selectedROIId, toast]);

  // Handle ROI selection
  const handleROISelect = useCallback((id: string | null) => {
    setSelectedROIId(id);
    console.log('ROI selected:', id);
  }, []);



  // Start real-time analysis
  const startAnalysis = useCallback(async () => {
    if (!videoMetadata || rois.length === 0) {
      toast({
        title: 'Cannot Start Analysis',
        description: 'Please configure ROI areas first',
        status: 'warning',
        duration: 3000
      });
      return;
    }

    try {
      setIsLoading(true);
      
      // Prepare ROI data for analysis
      const analysisROIs = rois.map(roi => ({
        x: roi.x,
        y: roi.y,
        w: roi.w,
        h: roi.h,
        type: roi.type,
        label: roi.label
      }));

      const analysisMethod = packingMethod === 'traditional' ? 'traditional' : 'qr_code';

      const response = await fetch('/api/analysis-streaming/start-analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_path: videoPath,
          method: analysisMethod,
          rois: analysisROIs
        })
      });

      const result = await response.json();
      
      if (result.success) {
        setAnalysisSessionId(result.session_id);
        setShowAnalysis(true);
        
        toast({
          title: 'Analysis Started',
          description: `Real-time ${packingMethod} analysis started`,
          status: 'success',
          duration: 3000
        });
      } else {
        throw new Error(result.error || 'Failed to start analysis');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      toast({
        title: 'Analysis Failed',
        description: errorMessage,
        status: 'error',
        duration: 5000
      });
    } finally {
      setIsLoading(false);
    }
  }, [videoMetadata, rois, packingMethod, videoPath, toast]);

  // Stop analysis
  const stopAnalysis = useCallback(async () => {
    if (!analysisSessionId) return;

    try {
      await fetch(`/api/analysis-streaming/stop-analysis/${analysisSessionId}`, {
        method: 'POST'
      });
      
      setAnalysisSessionId(null);
      setShowAnalysis(false);
      
      toast({
        title: 'Analysis Stopped',
        description: 'Real-time analysis stopped',
        status: 'info',
        duration: 3000
      });
    } catch (error) {
      console.error('Error stopping analysis:', error);
    }
  }, [analysisSessionId, toast]);

  // Handle analysis completion
  const handleAnalysisComplete = useCallback((results: any) => {
    setAnalysisSessionId(null);
    
    toast({
      title: 'Analysis Complete',
      description: 'Video analysis has been completed successfully',
      status: 'success',
      duration: 5000
    });
  }, [toast]);

  // Handle analysis error
  const handleAnalysisError = useCallback((errorMessage: string) => {
    toast({
      title: 'Analysis Error',
      description: errorMessage,
      status: 'error',
      duration: 5000
    });
  }, [toast]);

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
      setAnalysisSessionId(null);
      setShowAnalysis(false);
    } else {
      // Clean up analysis session when modal closes
      if (analysisSessionId) {
        fetch(`/api/analysis-streaming/cleanup-session/${analysisSessionId}`, {
          method: 'POST'
        }).catch(console.error);
      }
    }
  }, [isOpen, analysisSessionId]);

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
                                {roi.type} • {roi.w}×{roi.h}px
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
                <Alert status="error" borderRadius="8px" mb="20px" maxW={`${videoPlayerWidth}px`}>
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
                width={`${videoPlayerWidth}px`}
                height={`${videoPlayerHeight}px`}
                borderRadius="8px"
                overflow="hidden"
                border="2px solid"
                borderColor={borderColor}
              >
                {/* Video Player */}
                <VideoPlayer
                  videoPath={videoPath}
                  onMetadataLoaded={handleMetadataLoaded}
                  onVideoError={handleVideoError}
                  width={`${videoPlayerWidth}px`}
                  height={`${videoPlayerHeight}px`}
                  showControls={true}
                  autoPlay={true}
                />

                {/* Canvas Overlay */}
                {videoMetadata && (
                  <CanvasOverlay
                    width={videoPlayerWidth}
                    height={videoPlayerHeight - 80} // Account for video controls
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
                  />
                )}
              </Box>

              {/* Instructions */}
              <Text fontSize="sm" color={secondaryText} mt="16px" textAlign="center" maxW={`${videoPlayerWidth}px`}>
                Click and drag on the video to create ROI rectangles. 
                Double-click an existing ROI to delete it. 
                Use the controls below to navigate between configuration steps.
              </Text>

              {/* Analysis Controls */}
              {rois.length > 0 && videoMetadata && (
                <HStack spacing="12px" mt="16px">
                  {!showAnalysis ? (
                    <Button
                      colorScheme="green"
                      size="sm"
                      onClick={startAnalysis}
                      isLoading={isLoading}
                      leftIcon={<FaPlay />}
                    >
                      Start Real-time Analysis
                    </Button>
                  ) : (
                    <>
                      <Button
                        colorScheme="red"
                        size="sm"
                        onClick={stopAnalysis}
                        leftIcon={<FaPause />}
                      >
                        Stop Analysis
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => setShowAnalysis(false)}
                        variant="outline"
                      >
                        Hide Analysis
                      </Button>
                    </>
                  )}
                  
                  {analysisSessionId && !showAnalysis && (
                    <Button
                      colorScheme="blue"
                      size="sm"
                      onClick={() => setShowAnalysis(true)}
                      leftIcon={<FaPlay />}
                    >
                      Show Analysis
                    </Button>
                  )}
                </HStack>
              )}

              {/* Real-time Analysis Display */}
              {showAnalysis && analysisSessionId && videoMetadata && (
                <Box mt="20px" width={`${videoPlayerWidth}px`}>
                  <DualAnalysisCanvas
                    sessionId={analysisSessionId}
                    method={packingMethod}
                    rois={rois.map(roi => ({
                      x: roi.x,
                      y: roi.y,
                      w: roi.w,
                      h: roi.h,
                      type: roi.type,
                      label: roi.label
                    }))}
                    videoWidth={videoMetadata.resolution.width}
                    videoHeight={videoMetadata.resolution.height}
                    onAnalysisComplete={handleAnalysisComplete}
                    onError={handleAnalysisError}
                  />
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