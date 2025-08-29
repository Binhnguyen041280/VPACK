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
  Progress,
  Badge,
  Divider,
  Tooltip,
  useColorModeValue,
  useToast
} from '@chakra-ui/react';
import { FaTrash, FaEdit, FaCheck, FaTimes, FaPlay, FaPause } from 'react-icons/fa';
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

// Configuration step interface
interface ConfigStep {
  id: string;
  title: string;
  description: string;
  roiType: ROIData['type'];
  required: boolean;
  completed: boolean;
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

// Configuration steps for different packing methods
const TRADITIONAL_STEPS: ConfigStep[] = [
  {
    id: 'packing_area',
    title: 'Packing Area',
    description: 'Draw a rectangle around the main packing area where hand movements will be detected',
    roiType: 'packing_area',
    required: true,
    completed: false
  }
];

const QR_STEPS: ConfigStep[] = [
  {
    id: 'qr_mvd',
    title: 'QR Movement Detection',
    description: 'Draw a rectangle around the QR code area for movement detection',
    roiType: 'qr_mvd',
    required: true,
    completed: false
  },
  {
    id: 'qr_trigger',
    title: 'QR Trigger Area',
    description: 'Draw a rectangle around the QR trigger zone (optional for standard tables)',
    roiType: 'qr_trigger',
    required: false,
    completed: false
  }
];

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
  const [currentStep, setCurrentStep] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingROI, setEditingROI] = useState<{ id: string; label: string } | null>(null);
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

  // Configuration steps based on packing method
  const configSteps = useMemo(() => {
    const steps = packingMethod === 'traditional' ? TRADITIONAL_STEPS : QR_STEPS;
    return steps.map(step => ({
      ...step,
      completed: rois.some(roi => roi.type === step.roiType && roi.completed)
    }));
  }, [packingMethod, rois]);

  // Current step configuration
  const currentStepConfig = configSteps[currentStep] || configSteps[0];

  // Video player dimensions (maintain aspect ratio)
  const videoPlayerWidth = 800;
  const videoPlayerHeight = 450;

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
    const newROI: ROIData = {
      ...roiData,
      id: generateId(),
      type: currentStepConfig.roiType,
      label: `${currentStepConfig.title} ${rois.filter(r => r.type === currentStepConfig.roiType).length + 1}`,
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
  }, [currentStepConfig, rois, toast]);

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

  // Handle step navigation
  const handleNextStep = useCallback(() => {
    if (currentStep < configSteps.length - 1) {
      setCurrentStep(prev => prev + 1);
    }
  }, [currentStep, configSteps.length]);

  const handlePrevStep = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1);
    }
  }, [currentStep]);

  // Handle ROI label editing
  const handleStartEditLabel = useCallback((roi: ROIData) => {
    setEditingROI({ id: roi.id, label: roi.label });
  }, []);

  const handleSaveLabel = useCallback(() => {
    if (!editingROI) return;

    handleROIUpdate(editingROI.id, { label: editingROI.label });
    setEditingROI(null);

    toast({
      title: 'Label Updated',
      description: 'ROI label has been updated',
      status: 'success',
      duration: 2000,
      isClosable: true
    });
  }, [editingROI, handleROIUpdate, toast]);

  const handleCancelEdit = useCallback(() => {
    setEditingROI(null);
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
    const requiredSteps = configSteps.filter(step => step.required);
    const missingSteps = requiredSteps.filter(step => !step.completed);

    if (missingSteps.length > 0) {
      setError(`Please complete required steps: ${missingSteps.map(s => s.title).join(', ')}`);
      return;
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
    configSteps,
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
      setCurrentStep(0);
      setError(null);
      setEditingROI(null);
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

  // Calculate overall progress
  const overallProgress = useMemo(() => {
    const completedRequired = configSteps.filter(step => step.required && step.completed).length;
    const totalRequired = configSteps.filter(step => step.required).length;
    return totalRequired > 0 ? (completedRequired / totalRequired) * 100 : 0;
  }, [configSteps]);

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
              w="300px" 
              bg={panelBg} 
              borderRight="1px solid" 
              borderColor={borderColor}
              p="20px"
              overflowY="auto"
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

                {/* Progress */}
                <Box>
                  <Text fontSize="sm" fontWeight="medium" color={textColor} mb="8px">
                    Overall Progress
                  </Text>
                  <Progress 
                    value={overallProgress} 
                    colorScheme="blue" 
                    size="sm" 
                    borderRadius="full"
                  />
                  <Text fontSize="xs" color={secondaryText} mt="4px">
                    {Math.round(overallProgress)}% Complete
                  </Text>
                </Box>

                {/* Steps */}
                <Box>
                  <Text fontSize="sm" fontWeight="medium" color={textColor} mb="12px">
                    Configuration Steps
                  </Text>
                  <VStack spacing="12px" align="stretch">
                    {configSteps.map((step, index) => (
                      <Box
                        key={step.id}
                        p="12px"
                        borderRadius="8px"
                        border="2px solid"
                        borderColor={index === currentStep ? 'blue.500' : 'transparent'}
                        bg={step.completed ? 'green.50' : index === currentStep ? 'blue.50' : 'white'}
                        cursor="pointer"
                        onClick={() => setCurrentStep(index)}
                        transition="all 0.2s"
                      >
                        <HStack justify="space-between">
                          <VStack align="start" spacing="2px" flex="1">
                            <HStack>
                              <Text fontSize="sm" fontWeight="medium">
                                {step.title}
                              </Text>
                              {step.required && (
                                <Badge size="sm" colorScheme="red">Required</Badge>
                              )}
                            </HStack>
                            <Text fontSize="xs" color={secondaryText} lineHeight="short">
                              {step.description}
                            </Text>
                          </VStack>
                          {step.completed ? (
                            <FaCheck color="green" />
                          ) : index === currentStep ? (
                            <Box w="12px" h="12px" borderRadius="full" bg="blue.500" />
                          ) : (
                            <Box w="12px" h="12px" borderRadius="full" border="2px solid" borderColor="gray.300" />
                          )}
                        </HStack>
                      </Box>
                    ))}
                  </VStack>
                </Box>

                {/* Current Step Instructions */}
                <Box>
                  <Text fontSize="sm" fontWeight="medium" color={textColor} mb="8px">
                    Current Step
                  </Text>
                  <Box p="12px" bg="blue.50" borderRadius="8px" border="1px solid" borderColor="blue.200">
                    <Text fontSize="sm" fontWeight="medium" color="blue.700" mb="4px">
                      {currentStepConfig.title}
                    </Text>
                    <Text fontSize="xs" color="blue.600" lineHeight="tall">
                      {currentStepConfig.description}
                    </Text>
                  </Box>
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
                              {editingROI?.id === roi.id ? (
                                <HStack spacing="4px" width="100%">
                                  <Input
                                    value={editingROI.label}
                                    onChange={(e) => setEditingROI(prev => 
                                      prev ? { ...prev, label: e.target.value } : null
                                    )}
                                    size="xs"
                                    flex="1"
                                  />
                                  <IconButton
                                    aria-label="Save label"
                                    icon={<FaCheck />}
                                    size="xs"
                                    colorScheme="green"
                                    onClick={handleSaveLabel}
                                  />
                                  <IconButton
                                    aria-label="Cancel edit"
                                    icon={<FaTimes />}
                                    size="xs"
                                    variant="ghost"
                                    onClick={handleCancelEdit}
                                  />
                                </HStack>
                              ) : (
                                <Text fontSize="sm" fontWeight="medium">
                                  {roi.label}
                                </Text>
                              )}
                              <Text fontSize="xs" color={secondaryText}>
                                {roi.type} • {roi.w}×{roi.h}px
                              </Text>
                            </VStack>
                            {editingROI?.id !== roi.id && (
                              <HStack spacing="4px">
                                <IconButton
                                  aria-label="Edit label"
                                  icon={<FaEdit />}
                                  size="xs"
                                  variant="ghost"
                                  onClick={() => handleStartEditLabel(roi)}
                                />
                                <IconButton
                                  aria-label="Delete ROI"
                                  icon={<FaTrash />}
                                  size="xs"
                                  colorScheme="red"
                                  variant="ghost"
                                  onClick={() => handleROIDelete(roi.id)}
                                />
                              </HStack>
                            )}
                          </HStack>
                        </Box>
                      ))}
                    </VStack>
                  </Box>
                )}

              </VStack>
            </Box>

            {/* Center Panel - Video & Canvas */}
            <Box flex="1" p="20px" display="flex" flexDirection="column" alignItems="center" justifyContent="center">
              
              {/* Video Title */}
              <VStack spacing="16px" mb="20px">
                <Text fontSize="lg" fontWeight="medium" color={textColor}>
                  Video Configuration
                </Text>
                {videoMetadata && (
                  <HStack spacing="24px" fontSize="sm" color={secondaryText}>
                    <Text>{videoMetadata.filename}</Text>
                    <Text>{videoMetadata.resolution.width}×{videoMetadata.resolution.height}</Text>
                    <Text>{videoMetadata.duration_formatted}</Text>
                    <Text>{videoMetadata.size_mb.toFixed(1)} MB</Text>
                  </HStack>
                )}
              </VStack>

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
                    currentROIType={currentStepConfig.roiType}
                    currentROILabel={currentStepConfig.title}
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

            {/* Right Panel - Controls */}
            <Box 
              w="250px" 
              bg={panelBg} 
              borderLeft="1px solid" 
              borderColor={borderColor}
              p="20px"
              display="flex"
              flexDirection="column"
              justifyContent="space-between"
            >
              
              {/* Step Navigation */}
              <VStack spacing="16px" align="stretch">
                <Text fontSize="sm" fontWeight="medium" color={textColor}>
                  Step Navigation
                </Text>
                
                <HStack spacing="8px">
                  <Button
                    size="sm"
                    onClick={handlePrevStep}
                    isDisabled={currentStep === 0}
                    leftIcon={<Text>←</Text>}
                  >
                    Previous
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleNextStep}
                    isDisabled={currentStep >= configSteps.length - 1}
                    rightIcon={<Text>→</Text>}
                  >
                    Next
                  </Button>
                </HStack>

                <Text fontSize="xs" color={secondaryText} textAlign="center">
                  Step {currentStep + 1} of {configSteps.length}
                </Text>

                <Divider />

                {/* Drawing Instructions */}
                <Box>
                  <Text fontSize="sm" fontWeight="medium" color={textColor} mb="8px">
                    Drawing Instructions
                  </Text>
                  <VStack spacing="4px" align="start" fontSize="xs" color={secondaryText}>
                    <Text>• Click and drag to create ROI</Text>
                    <Text>• Click existing ROI to select</Text>
                    <Text>• Drag selected ROI to move</Text>
                    <Text>• Double-click ROI to delete</Text>
                  </VStack>
                </Box>

                {selectedROIId && (
                  <>
                    <Divider />
                    <Box>
                      <Text fontSize="sm" fontWeight="medium" color={textColor} mb="8px">
                        Selected ROI
                      </Text>
                      {(() => {
                        const selectedROI = rois.find(r => r.id === selectedROIId);
                        return selectedROI ? (
                          <VStack spacing="4px" align="start" fontSize="xs" color={secondaryText}>
                            <Text>Type: {selectedROI.type}</Text>
                            <Text>Position: {selectedROI.x}, {selectedROI.y}</Text>
                            <Text>Size: {selectedROI.w} × {selectedROI.h}</Text>
                            <Text>Label: {selectedROI.label}</Text>
                          </VStack>
                        ) : null;
                      })()}
                    </Box>
                  </>
                )}

              </VStack>

              {/* Action Buttons */}
              <VStack spacing="12px" align="stretch">
                <Button
                  colorScheme="blue"
                  size="md"
                  onClick={handleSaveConfiguration}
                  isLoading={isSaving}
                  loadingText="Saving..."
                  isDisabled={overallProgress < 100}
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
                
                {overallProgress < 100 && (
                  <Text fontSize="xs" color="orange.500" textAlign="center">
                    Complete all required steps to save
                  </Text>
                )}
              </VStack>

            </Box>
          </Flex>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default ROIConfigModal;