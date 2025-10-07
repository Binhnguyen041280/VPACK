'use client';

import {
  Box,
  Flex,
  Text,
  Button,
  VStack,
  HStack,
  Input,
  Checkbox,
  useColorModeValue,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalBody,
  ModalCloseButton,
  Tooltip,
  Badge,
  Spinner
} from '@chakra-ui/react';
import { useColorTheme } from '@/contexts/ColorThemeContext';
import { useState, useEffect } from 'react';
import React from 'react';
import { stepConfigService, VideoValidationResponse } from '@/services/stepConfigService';
import ROIConfigModal from '@/components/roi/ROIConfigModal';
// SampleVideoModal removed - functionality integrated into main popup

// Height breakpoints for adaptive behavior
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

// Enhanced Canvas Component Props
interface CanvasComponentProps {
  onStepChange?: (stepName: string, data: any) => void;
  adaptiveConfig: AdaptiveConfig;
  availableHeight: number;
  // Chat-controlled props
  brandName?: string;
  isLoading?: boolean;
  // Step 2 props
  locationTimeData?: {
    country: string;
    timezone: string;
    language: string;
    working_days: string[];
    from_time: string;
    to_time: string;
  };
  locationTimeLoading?: boolean;
}

// Camera interface
interface Camera {
  id: string;
  name: string;
  ip: string;
  status: 'online' | 'offline';
}

// Step 4: Packing Area Canvas
function PackingAreaCanvas({ adaptiveConfig, onStepChange }: CanvasComponentProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  const cardBg = useColorModeValue('gray.50', 'navy.700');
  const hoverBg = useColorModeValue('gray.50', 'navy.600');
  
  // State for camera data from Step 3
  const [availableCameras, setAvailableCameras] = useState<Camera[]>([]);
  const [isLoadingCameras, setIsLoadingCameras] = useState(true);
  const [cameraError, setCameraError] = useState<string | null>(null);
  
  const [selectedCameras, setSelectedCameras] = useState<string[]>([]);
  const [showCameraPopup, setShowCameraPopup] = useState(false);
  const [selectedCameraForConfig, setSelectedCameraForConfig] = useState<string | null>(null);
  const [selectedPackingMethod, setSelectedPackingMethod] = useState<'traditional' | 'qr' | null>(null);
  
  // Single-camera workflow state
  const [configuringCameraId, setConfiguringCameraId] = useState<string | null>(null);
  const [configuredCameras, setConfiguredCameras] = useState<string[]>([]);
  
  // ROI configuration modal state
  const [showROIModal, setShowROIModal] = useState(false);
  const [roiVideoPath, setROIVideoPath] = useState<string>('');
  
  // Sample Video Modal state - REMOVED: functionality integrated into main popup
  
  // Video validation states for integrated workflow
  const [traditionalInputPath, setTraditionalInputPath] = useState(''); // Start empty like Step 3
  const [qrInputPath, setQrInputPath] = useState(''); // Start empty like Step 3

  // Video validation states
  const [traditionalValidation, setTraditionalValidation] = useState<VideoValidationResponse | null>(null);
  const [traditionalValidating, setTraditionalValidating] = useState(false);
  const [qrValidation, setQrValidation] = useState<VideoValidationResponse | null>(null);
  const [qrValidating, setQrValidating] = useState(false);

  // Scroll refs for auto-scroll
  const traditionalScrollRef = React.useRef<HTMLDivElement>(null);
  const qrScrollRef = React.useRef<HTMLDivElement>(null);

  // Auto-scroll when validation results appear
  useEffect(() => {
    if (traditionalValidation && traditionalScrollRef.current) {
      traditionalScrollRef.current.scrollTop = traditionalScrollRef.current.scrollHeight;
    }
  }, [traditionalValidation]);

  useEffect(() => {
    if (qrValidation && qrScrollRef.current) {
      qrScrollRef.current.scrollTop = qrScrollRef.current.scrollHeight;
    }
  }, [qrValidation]);

  // Helper function to check if a camera is currently being configured
  const isCameraConfiguring = (cameraId: string): boolean => {
    return configuringCameraId === cameraId;
  };

  // Helper function to check if a camera is configured
  const isCameraConfigured = (cameraId: string): boolean => {
    return configuredCameras.includes(cameraId);
  };

  // Function to complete camera configuration
  const completeCameraConfiguration = () => {
    console.log('✅ Completing camera configuration');
    if (configuringCameraId && !configuredCameras.includes(configuringCameraId)) {
      setConfiguredCameras(prev => [...prev, configuringCameraId]);
    }
    setConfiguringCameraId(null);
    setShowCameraPopup(false);
    setSelectedCameraForConfig(null);
  };
  
  // Helper function for placeholder path (Step 3 standard)
  const getPlaceholderPath = () => {
    // Return generic placeholder like Step 3
    return "Select video file or paste path...";
  };

  // Create video upload input (copied from trace page createImageUploadInput pattern)
  const createVideoUploadInput = (onVideoSelected: (file: File) => void): void => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'video/*';
    input.style.display = 'none';

    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        onVideoSelected(file);
      }
      input.remove();
    };

    document.body.appendChild(input);
    input.click();
  };

  // Trigger file browser for Traditional
  const handleTraditionalBrowseClick = () => {
    createVideoUploadInput(async (file: File) => {
      const formData = new FormData();
      formData.append('video', file);

      try {
        const response = await fetch('http://localhost:8080/api/config/step4/roi/upload-video', {
          method: 'POST',
          body: formData
        });

        const result = await response.json();

        if (result.success && result.file_path) {
          setTraditionalInputPath(result.file_path);
          handleVideoPathChange(result.file_path, 'traditional');
        }
      } catch (error) {
        console.error('Upload error:', error);
      }
    });
  };

  // Trigger file browser for QR
  const handleQRBrowseClick = () => {
    createVideoUploadInput(async (file: File) => {
      const formData = new FormData();
      formData.append('video', file);

      try {
        const response = await fetch('http://localhost:8080/api/config/step4/roi/upload-video', {
          method: 'POST',
          body: formData
        });

        const result = await response.json();

        if (result.success && result.file_path) {
          setQrInputPath(result.file_path);
          handleVideoPathChange(result.file_path, 'qr');
        }
      } catch (error) {
        console.error('Upload error:', error);
      }
    });
  };

  // Debounced validation
  const debounceRef = React.useRef<NodeJS.Timeout | null>(null);

  // Video validation function
  const validateVideoPath = async (path: string, method: 'traditional' | 'qr') => {
    if (method === 'traditional') {
      setTraditionalValidating(true);
    } else {
      setQrValidating(true);
    }

    try {
      const response = await stepConfigService.validatePackingVideo(path, method);
      if (method === 'traditional') {
        setTraditionalValidation(response);
        setTraditionalValidating(false);
      } else {
        setQrValidation(response);
        setQrValidating(false);
      }
    } catch (error) {
      console.error('Video validation error:', error);
      if (method === 'traditional') {
        setTraditionalValidation(null);
        setTraditionalValidating(false);
      } else {
        setQrValidation(null);
        setQrValidating(false);
      }
    }
  };

  // Handle video path change with debounce
  const handleVideoPathChange = (path: string, method: 'traditional' | 'qr') => {
    if (method === 'traditional') {
      setTraditionalInputPath(path);
      setTraditionalValidation(null);
    } else {
      setQrInputPath(path);
      setQrValidation(null);
    }

    // Debounced validation (Step 3 standard - validate only when path is not empty)
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    if (path && path.trim() !== '') {
      debounceRef.current = setTimeout(() => {
        validateVideoPath(path, method);
      }, 1000);
    }
  };

  // Helper function to render validation result
  const renderValidationResult = (validation: VideoValidationResponse | null, isLoading: boolean) => {
    if (isLoading) {
      return (
        <HStack spacing="8px" mt="8px">
          <Spinner size="sm" color={currentColors.brand500} />
          <Text fontSize="sm" color={secondaryText}>
            Validating video file...
          </Text>
        </HStack>
      );
    }

    if (!validation) {
      return null;
    }

    const { video_file, file_info } = validation;

    if (validation.success && video_file.valid) {
      return (
        <HStack 
          spacing="8px" 
          mt="8px" 
          p="8px" 
          bg="rgba(72, 187, 120, 0.1)" 
          borderRadius="8px" 
          border="1px solid" 
          borderColor="green.400"
        >
          <Text fontSize="16px">✅</Text>
          <VStack align="start" spacing="2px" flex="1">
            <Text fontSize="sm" color="green.500" fontWeight="500">
              Valid video ({video_file.duration_formatted})
            </Text>
            <Text fontSize="xs" color="green.400">
              {video_file.filename} • {video_file.file_size_mb}MB • {video_file.format.toUpperCase()}
            </Text>
          </VStack>
        </HStack>
      );
    } else {
      // Error cases
      const isFileIssue = !file_info.exists || !file_info.readable;
      const icon = isFileIssue ? "❌" : "⚠️";
      const bgColor = isFileIssue ? "rgba(245, 101, 101, 0.1)" : "rgba(237, 137, 54, 0.1)";
      const borderColorError = isFileIssue ? "red.400" : "orange.400";
      const textColorError = isFileIssue ? "red.500" : "orange.500";

      return (
        <HStack 
          spacing="8px" 
          mt="8px" 
          p="8px" 
          bg={bgColor} 
          borderRadius="8px" 
          border="1px solid" 
          borderColor={borderColorError}
        >
          <Text fontSize="16px">{icon}</Text>
          <VStack align="start" spacing="2px" flex="1">
            <Text fontSize="sm" color={textColorError} fontWeight="500">
              {video_file.error || validation.error || 'Unknown error'}
            </Text>
            {video_file.filename && (
              <Text fontSize="xs" color={textColorError}>
                {video_file.filename}
                {video_file.duration_seconds > 0 && ` • ${video_file.duration_formatted}`}
              </Text>
            )}
          </VStack>
        </HStack>
      );
    }
  };

  // Handle use video button
  const handleUseVideo = (method: 'traditional' | 'qr') => {
    const videoPath = method === 'traditional' ? traditionalInputPath : qrInputPath;
    const validation = method === 'traditional' ? traditionalValidation : qrValidation;

    if (validation?.success && validation.video_file?.valid) {
      setROIVideoPath(videoPath);
      setShowCameraPopup(false);
      // Auto-open ROI modal after video selection
      setTimeout(() => {
        setShowROIModal(true);
      }, 500);
    }
  };

  // ROI configuration handlers
  const handleDefineDetectionZone = () => {
    if (!selectedPackingMethod) {
      console.warn('No packing method selected');
      return;
    }
    
    // Get the appropriate video path based on selected method
    const videoPath = selectedPackingMethod === 'traditional' ? traditionalInputPath : qrInputPath;

    if (!videoPath) {
      console.warn('No valid video path selected');
      return;
    }
    
    // Get validation result to check if video is valid
    const validation = selectedPackingMethod === 'traditional' ? traditionalValidation : qrValidation;
    
    if (!validation?.success || !validation.video_file?.valid) {
      console.warn('Video validation failed or not completed');
      return;
    }
    
    console.log('🎯 Opening ROI configuration modal', {
      cameraId: configuringCameraId,
      videoPath,
      packingMethod: selectedPackingMethod
    });
    
    setROIVideoPath(videoPath);
    setShowROIModal(true);
  };
  
  const handleROIModalClose = () => {
    console.log('🔒 Closing ROI configuration modal');
    setShowROIModal(false);
    setROIVideoPath('');
  };
  
  const handleROIConfigSave = (config: any) => {
    console.log('💾 ROI configuration saved:', config);

    // Mark camera as configured
    if (configuringCameraId && !configuredCameras.includes(configuringCameraId)) {
      setConfiguredCameras(prev => [...prev, configuringCameraId]);
    }

    // Update parent component with configuration
    onStepChange?.('packing_area', {
      selectedCameras,
      packingMethod: selectedPackingMethod,
      roiConfiguration: config,
      configuredCamera: configuringCameraId
    });

    // Close ROI modal
    setShowROIModal(false);
    setROIVideoPath('');
  };
  
  const handleROIConfigError = (error: string) => {
    console.error('❌ ROI configuration error:', error);
  };
  
  // Load camera data from processing_config table on component mount
  useEffect(() => {
    const loadCamerasFromProcessingConfig = async () => {
      try {
        setIsLoadingCameras(true);
        setCameraError(null);

        console.log('🔍 PackingAreaCanvas - Fetching cameras from processing_config...');
        const response = await stepConfigService.fetchProcessingConfigCameras();

        if (response.success && response.data.selectedCameras && response.data.selectedCameras.length > 0) {
          // Fetch ROI status for all cameras
          console.log('🔍 PackingAreaCanvas - Fetching ROI status...');
          const roiStatusResponse = await fetch('http://localhost:8080/api/config/step/packing-area/cameras/status', {
            method: 'GET',
            credentials: 'include',
            headers: {
              'Content-Type': 'application/json',
            },
          });

          let roiStatusMap: { [key: string]: boolean } = {};
          if (roiStatusResponse.ok) {
            const roiData = await roiStatusResponse.json();
            if (roiData.success && roiData.data.cameras) {
              // Create map of camera_name -> has_roi
              roiStatusMap = roiData.data.cameras.reduce((map: any, camera: any) => {
                map[camera.camera_name] = camera.has_roi;
                return map;
              }, {});
              console.log('✅ PackingAreaCanvas - ROI status loaded:', roiStatusMap);
            }
          }

          // Transform selectedCameras into availableCameras format with ROI status
          const transformedCameras: Camera[] = response.data.selectedCameras.map((cameraName, index) => ({
            id: cameraName, // Use camera name as ID
            name: `Camera - ${cameraName}`, // Add "Camera - " prefix
            ip: `192.168.1.${100 + index}`, // Generate mock IP based on index
            status: 'online' as const // Default to online
          }));

          // Update configuredCameras state with cameras that have ROI
          const camerasWithROI = response.data.selectedCameras.filter((cameraName: string) => roiStatusMap[cameraName]);
          setConfiguredCameras(camerasWithROI);

          console.log('✅ PackingAreaCanvas - Transformed cameras:', transformedCameras);
          console.log('✅ PackingAreaCanvas - Configured cameras:', camerasWithROI);
          setAvailableCameras(transformedCameras);
        } else {
          // No cameras found in processing_config
          console.log('⚠️ PackingAreaCanvas - No cameras found in processing_config');
          setAvailableCameras([]);
        }
      } catch (error) {
        console.error('❌ PackingAreaCanvas - Error loading cameras:', error);
        setCameraError('Failed to load cameras from processing_config. Please configure your system first.');
        setAvailableCameras([]);
      } finally {
        setIsLoadingCameras(false);
      }
    };

    loadCamerasFromProcessingConfig();
  }, []);
  
  // Retry function for error state
  const retryCameraLoad = () => {
    const loadCamerasFromProcessingConfig = async () => {
      try {
        setIsLoadingCameras(true);
        setCameraError(null);
        
        const response = await stepConfigService.fetchProcessingConfigCameras();
        
        if (response.success && response.data.selectedCameras && response.data.selectedCameras.length > 0) {
          const transformedCameras: Camera[] = response.data.selectedCameras.map((cameraName, index) => ({
            id: cameraName,
            name: `Camera - ${cameraName}`,
            ip: `192.168.1.${100 + index}`,
            status: 'online' as const
          }));
          
          setAvailableCameras(transformedCameras);
        } else {
          setAvailableCameras([]);
        }
      } catch (error) {
        console.error('❌ PackingAreaCanvas - Error loading cameras:', error);
        setCameraError('Failed to load cameras from processing_config. Please configure your system first.');
        setAvailableCameras([]);
      } finally {
        setIsLoadingCameras(false);
      }
    };
    
    loadCamerasFromProcessingConfig();
  };
  



  return (
    <Box
      w="100%"
      minH="fit-content"
      maxW="450px"
      mx="auto"
      css={{
        '@media (max-width: 450px)': {
          maxW: '100%',
          px: '12px',
        }
      }}
    >
      <>
        {/* Header */}
        <Text fontSize={adaptiveConfig.fontSize.header} fontWeight="700" color={textColor} mb={adaptiveConfig.spacing.section}>
          📦 Step 4: Packing Area Detection
        </Text>

      <VStack spacing={adaptiveConfig.spacing.item} align="stretch">
        {/* Camera Selection */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            📹 Select Cameras for Detection
          </Text>
          <Box bg={cardBg} p="16px" borderRadius="12px">
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText} mb="12px">
              Choose cameras from processing_config to monitor for packing area detection
            </Text>
            
            {/* Loading State */}
            {isLoadingCameras && (
              <VStack spacing="16px" py="20px">
                <Text fontSize="24px">⏳</Text>
                <Text fontSize={adaptiveConfig.fontSize.body} color={secondaryText}>
                  Loading cameras from processing_config...
                </Text>
              </VStack>
            )}
            
            {/* Error State */}
            {cameraError && !isLoadingCameras && (
              <VStack spacing="16px" py="20px">
                <Text fontSize="24px">⚠️</Text>
                <Text fontSize={adaptiveConfig.fontSize.body} color="red.500" textAlign="center">
                  {cameraError}
                </Text>
                <Button 
                  size="sm" 
                  colorScheme="brand" 
                  onClick={retryCameraLoad}
                >
                  Retry
                </Button>
              </VStack>
            )}
            
            {/* Empty State */}
            {!isLoadingCameras && !cameraError && availableCameras.length === 0 && (
              <VStack spacing="16px" py="20px">
                <Text fontSize="24px">📹</Text>
                <Text fontSize={adaptiveConfig.fontSize.body} color={secondaryText} textAlign="center">
                  No cameras found in processing_config
                </Text>
                <Text fontSize={adaptiveConfig.fontSize.small} color="blue.500" textAlign="center">
                  Please configure your system and select cameras first
                </Text>
              </VStack>
            )}
            
            {/* Success State - Display Cameras */}
            {!isLoadingCameras && !cameraError && availableCameras.length > 0 && (
              <>
                <VStack spacing="8px" align="stretch">
                  {availableCameras.map((camera) => {
                    const isConfiguring = isCameraConfiguring(camera.id);
                    const isConfigured = isCameraConfigured(camera.id);

                    return (
                      <Flex
                        key={camera.id}
                        align="center"
                        p="12px"
                        borderRadius="8px"
                        border="1px solid"
                        borderColor={borderColor}
                        bg={bgColor}
                        transition="all 0.2s ease"
                        cursor="pointer"
                        _hover={{ bg: hoverBg, transform: 'translateY(-2px)', boxShadow: 'md' }}
                        onClick={() => {
                          console.log(`🔧 Opening configuration for camera: ${camera.id}`);
                          setSelectedCameras(prev => {
                            if (!prev.includes(camera.id)) {
                              return [...prev, camera.id];
                            }
                            return prev;
                          });
                          setSelectedCameraForConfig(camera.id);
                          setConfiguringCameraId(camera.id);
                          setShowCameraPopup(true);
                        }}
                      >
                        <Box flex="1">
                          <Flex align="center" gap="8px">
                            <Text
                              fontSize={adaptiveConfig.fontSize.body}
                              fontWeight="600"
                              color={textColor}
                            >
                              {camera.name}
                            </Text>
                            {isConfigured && (
                              <Text fontSize="14px" color="green.500">✅</Text>
                            )}
                          </Flex>
                          <Text
                            fontSize={adaptiveConfig.fontSize.small}
                            color={secondaryText}
                          >
                            {isConfigured ? 'Configured' : 'Not configured'}
                          </Text>
                        </Box>
                        <Box
                          w="10px"
                          h="10px"
                          borderRadius="full"
                          bg={isConfigured ? 'green.400' : 'red.400'}
                          flexShrink={0}
                        />
                      </Flex>
                    );
                  })}
                </VStack>
              </>
            )}
          </Box>
        </Box>
        
      </VStack>

      {/* Camera Configuration Popup */}
      <Modal
        isOpen={showCameraPopup}
        onClose={() => setShowCameraPopup(false)}
        size="6xl"
        isCentered
      >
        <ModalOverlay bg="blackAlpha.600" />
        <ModalContent 
          maxW="95vw" 
          maxH="95vh" 
          w="85%"
          overflow="hidden"
        >
          <ModalCloseButton />
          <ModalBody 
            pt="40px" 
            overflow="auto" 
            maxH="calc(95vh - 60px)"
            sx={{
              '&::-webkit-scrollbar': {
                width: '8px',
              },
              '&::-webkit-scrollbar-track': {
                bg: 'gray.100',
                borderRadius: '4px',
              },
              '&::-webkit-scrollbar-thumb': {
                bg: 'gray.400',
                borderRadius: '4px',
                _hover: {
                  bg: 'gray.500',
                },
              },
            }}
          >
            <Flex 
              direction="row" 
              minH="auto"
              gap="20px"
              overflow="visible"
            >
              {/* Left Panel - Section 1 */}
              <Box
                ref={traditionalScrollRef}
                flex="1"
                w="auto"
                minW="0"
                bg={cardBg}
                p="20px"
                borderRadius="12px"
                border="1px solid"
                borderColor={borderColor}
                cursor="pointer"
                _hover={{ transform: 'translateY(-2px)', boxShadow: 'lg' }}
                transition="all 0.2s ease"
                overflow="auto"
                maxH="calc(95vh - 140px)"
                onClick={() => {
                  console.log('🎯 Traditional method selected');
                  setSelectedPackingMethod('traditional');
                  // Don't close popup yet - show video input directly
                  onStepChange?.('packing_area', { 
                    packingMethod: 'traditional',
                    selectedCameras,
                    configuredCamera: configuringCameraId
                  });
                }}
              >
                <Text fontSize="lg" fontWeight="600" color={textColor} mb="16px">
                  📦 Traditional Packing Table
                </Text>
                
                <VStack spacing="16px" align="stretch">
                  <Box>
                    <Text fontSize="md" fontWeight="500" color={textColor} mb="8px">
                      🏷️ Description:
                    </Text>
                    <Text fontSize="sm" color={secondaryText} lineHeight="tall">
                      Use the packing table as it currently is, without changing layout or adding any equipment. 
                      The system will detect packing events based on motion and image changes.
                    </Text>
                  </Box>
                  
                  <Box>
                    <Text fontSize="md" fontWeight="500" color="green.500" mb="8px">
                      ✅ Advantages:
                    </Text>
                    <Text fontSize="sm" color={secondaryText} lineHeight="tall">
                      • No adjustments needed
                    </Text>
                  </Box>
                  
                  <Box>
                    <Text fontSize="md" fontWeight="500" color="orange.500" mb="8px">
                      ⚠️ Disadvantages:
                    </Text>
                    <Text fontSize="sm" color={secondaryText} lineHeight="tall">
                      • Sometimes need to adjust buffer for correct events
                    </Text>
                  </Box>

                  {/* Video Path Input for Traditional */}
                  <Box>
                    <Text fontSize="md" fontWeight="500" color={textColor} mb="12px">
                      📂 Sample Video Path
                    </Text>
                    
                    <VStack spacing="12px" align="stretch">
                      <Text fontSize="sm" color={secondaryText}>
                        📝 Choose where your traditional packing videos are stored for processing
                      </Text>
                      <Text fontSize="sm" color="blue.500" fontWeight="500">
                        ⏱️ Video Requirements: Minimum 1 minute - Maximum 5 minutes duration
                      </Text>

                      {/* Input field with Browse button */}
                      <HStack spacing="8px">
                        <Input
                          value={traditionalInputPath}
                          placeholder={getPlaceholderPath()}
                          size="sm"
                          borderColor={borderColor}
                          _focus={{ borderColor: currentColors.brand500 }}
                          bg="white"
                          flex="1"
                          onFocus={(e) => {
                            e.target.select();
                          }}
                          onChange={(e) => {
                            handleVideoPathChange(e.target.value, 'traditional');
                          }}
                        />
                        <Button
                          size="sm"
                          minW="80px"
                          onClick={handleTraditionalBrowseClick}
                          colorScheme="gray"
                        >
                          📁 Browse...
                        </Button>
                      </HStack>

                      {/* Validation Result */}
                      {renderValidationResult(traditionalValidation, traditionalValidating)}

                      {/* Use Video Button */}
                      {traditionalValidation?.success && traditionalValidation.video_file?.valid && (
                        <Button
                          colorScheme="green"
                          size="md"
                          onClick={() => handleUseVideo('traditional')}
                          _hover={{ transform: 'translateY(-2px)', boxShadow: 'lg' }}
                          mt="8px"
                        >
                          ✅ Use This Video & Configure ROI →
                        </Button>
                      )}
                    </VStack>
                  </Box>
                </VStack>
              </Box>
              
              {/* Right Panel - Section 2 */}
              <Box
                ref={qrScrollRef}
                flex="1"
                w="auto"
                minW="0"
                bg={cardBg}
                p="20px"
                borderRadius="12px"
                border="2px solid"
                borderColor={currentColors.brand500}
                cursor="pointer"
                _hover={{ transform: 'translateY(-2px)', boxShadow: 'lg' }}
                transition="all 0.2s ease"
                overflow="auto"
                maxH="calc(95vh - 140px)"
                position="relative"
                sx={{
                  '&::-webkit-scrollbar': {
                    width: '8px',
                  },
                  '&::-webkit-scrollbar-track': {
                    bg: 'gray.100',
                    borderRadius: '4px',
                  },
                  '&::-webkit-scrollbar-thumb': {
                    bg: 'gray.400',
                    borderRadius: '4px',
                    _hover: {
                      bg: 'gray.500',
                    },
                  },
                }}
                onClick={() => {
                  console.log('🎯 QR method selected');
                  setSelectedPackingMethod('qr');
                  // Don't close popup yet - show video input directly
                  onStepChange?.('packing_area', { 
                    packingMethod: 'qr',
                    selectedCameras,
                    configuredCamera: configuringCameraId
                  });
                }}
              >
                {/* Recommended Badge */}
                <Box
                  position="absolute"
                  top="-8px"
                  right="16px"
                  bg={currentColors.brand500}
                  color="white"
                  px="8px"
                  py="2px"
                  borderRadius="full"
                  fontSize="xs"
                  fontWeight="600"
                >
                  Recommended
                </Box>
                
                <Text fontSize="lg" fontWeight="600" color={textColor} mb="16px">
                  🎯 QR Code Packing Table (Trigger)
                </Text>
                
                <VStack spacing="16px" align="stretch">
                  <Box>
                    <Text fontSize="md" fontWeight="500" color={textColor} mb="8px">
                      🏷️ Description:
                    </Text>
                    <Text fontSize="sm" color={secondaryText} lineHeight="tall">
                      Paste QR Code (Trigger) in the center of packing area. When packages move to cover/uncover the QR code, 
                      the system will accurately identify the start and end times of packing events.
                    </Text>
                  </Box>
                  
                  <Box>
                    <Text fontSize="md" fontWeight="500" color="green.500" mb="8px">
                      ✅ Advantages:
                    </Text>
                    <Text fontSize="sm" color={secondaryText} lineHeight="tall">
                      • High timing accuracy<br/>
                      • Clear distinction of packing events
                    </Text>
                  </Box>
                  
                  {/* QR Setup & Download Section - Horizontal Layout */}
                  <Box>
                    <Text fontSize="md" fontWeight="500" color={textColor} mb="12px">
                      📷 Setup & QR Code Download
                    </Text>
                    
                    {/* Horizontal layout: Setup Illustration + QR Image + Download buttons */}
                    <HStack 
                      spacing="16px" 
                      align="flex-start"
                      direction="row"
                      wrap="wrap"
                    >
                      
                      {/* Setup Illustration - Left */}
                      <Box 
                        flex="2"
                        w="auto"
                        minW="0"
                      >
                        <Text fontSize="sm" color={secondaryText} mb="6px">Setup Illustration:</Text>
                        <Box 
                          bg={cardBg} 
                          p="12px"
                          borderRadius="8px"
                          border="2px dashed" 
                          borderColor={currentColors.brand500}
                          h="140px"
                          position="relative"
                          overflow="hidden"
                        >
                          <Text 
                            position="absolute"
                            top="4px"
                            right="4px"
                            fontSize="xs" 
                            color={secondaryText}
                          >
                            Camera view
                          </Text>
                          
                          {/* Packing Area Box */}
                          <Box
                            position="absolute"
                            top="50%"
                            left="50%"
                            transform="translate(-50%, -50%)"
                            w="100px"
                            h="80px"
                            border="2px solid"
                            borderColor="orange.500"
                            bg="orange.50"
                            borderRadius="6px"
                            display="flex"
                            alignItems="center"
                            justifyContent="center"
                          >
                            <Text 
                              position="absolute"
                              top="2px"
                              left="4px"
                              fontSize="xs" 
                              color="orange.600"
                              fontWeight="500"
                            >
                              Packing area
                            </Text>
                            
                            {/* QR Code Zone in center */}
                            <Box
                              w="50px"
                              h="30px"
                              border="2px solid"
                              borderColor={currentColors.brand500}
                              bg={`${currentColors.brand500}20`}
                              borderRadius="4px"
                              display="flex"
                              alignItems="center"
                              justifyContent="center"
                            >
                              <Text fontSize="xs" color={currentColors.brand500} fontWeight="bold">
                                QR
                              </Text>
                            </Box>
                          </Box>
                        </Box>
                      </Box>

                      {/* QR Code Image - Center */}
                      <Box 
                        flex="1"
                        w="auto"
                        textAlign="center"
                        minW="0"
                      >
                        <Text fontSize="sm" color={secondaryText} mb="6px">TimeGo QR:</Text>
                        <Box 
                          w="100px"
                          h="100px"
                          mx="auto"
                          border="2px solid" 
                          borderColor={borderColor}
                          borderRadius="8px"
                          overflow="hidden"
                          bg="white"
                        >
                          <img 
                            src="/images/TimeGo-qr.png" 
                            alt="TimeGo QR Code" 
                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                          />
                        </Box>
                      </Box>

                      {/* Download buttons - Right */}
                      <Box 
                        flex="1"
                        w="auto"
                        minW="0"
                      >
                        <Text fontSize="sm" color={secondaryText} mb="6px">Actions:</Text>
                        <VStack spacing="6px">
                          <Button
                            colorScheme="blue"
                            size="sm"
                            w="full"
                            leftIcon={<Text>💾</Text>}
                            fontSize="sm"
                            onClick={() => {
                              // Download the existing QR image
                              const link = document.createElement('a');
                              link.download = 'TimeGo-QR.png';
                              link.href = '/images/TimeGo-qr.png';
                              link.click();
                            }}
                            _hover={{ transform: 'translateY(-1px)' }}
                          >
                            Download
                          </Button>
                          
                          <Button
                            colorScheme="green"
                            size="sm"
                            w="full"
                            leftIcon={<Text>🖨️</Text>}
                            fontSize="sm"
                            onClick={() => {
                              // Generate clean printable version - QR code only
                              const printWindow = window.open('', '_blank');
                              if (printWindow) {
                                printWindow.document.write(`
                                  <html>
                                    <head>
                                      <title>TimeGo QR Code</title>
                                      <style>
                                        body { margin: 0; padding: 20px; text-align: center; }
                                        .qr-container { width: 300px; height: 300px; margin: 0 auto; }
                                        @media print { body { margin: 0; padding: 10px; } }
                                      </style>
                                    </head>
                                    <body>
                                      <div class="qr-container">
                                        <img src="/images/TimeGo-qr.png" style="width: 100%; height: 100%; object-fit: cover;" />
                                      </div>
                                    </body>
                                  </html>
                                `);
                                printWindow.print();
                              }
                            }}
                            _hover={{ transform: 'translateY(-1px)' }}
                          >
                            Print
                          </Button>
                        </VStack>
                      </Box>

                    </HStack>
                    
                    {/* Instructions */}
                    <Text fontSize="xs" color={secondaryText} mt="8px" textAlign="center">
                      📝 Download and print the TimeGo QR code, then place it in the center of your packing area
                    </Text>
                  </Box>

                  {/* Video Path Input for QR - Compact */}
                  <Box>
                    <Text fontSize="md" fontWeight="500" color={textColor} mb="8px">
                      📂 Sample Video Path
                    </Text>
                    
                    <VStack spacing="8px" align="stretch">
                      <Text fontSize="xs" color={secondaryText}>
                        📝 QR code packing videos (1-5 min) • Record with QR visible in center
                      </Text>

                      {/* Input field with Browse button */}
                      <HStack spacing="8px">
                        <Input
                          value={qrInputPath}
                          placeholder={getPlaceholderPath()}
                          size="sm"
                          borderColor={borderColor}
                          _focus={{ borderColor: currentColors.brand500 }}
                          bg="white"
                          flex="1"
                          onFocus={(e) => {
                            e.target.select();
                          }}
                          onChange={(e) => {
                            handleVideoPathChange(e.target.value, 'qr');
                          }}
                        />
                        <Button
                          size="sm"
                          minW="80px"
                          onClick={handleQRBrowseClick}
                          colorScheme="gray"
                        >
                          📁 Browse...
                        </Button>
                      </HStack>

                      {/* Validation Result - Compact */}
                      {renderValidationResult(qrValidation, qrValidating)}

                      {/* Use Video Button - Compact */}
                      {qrValidation?.success && qrValidation.video_file?.valid && (
                        <Button
                          colorScheme="green"
                          size="sm"
                          onClick={() => handleUseVideo('qr')}
                          _hover={{ transform: 'translateY(-1px)' }}
                          w="full"
                        >
                          ✅ Use Video & Configure ROI →
                        </Button>
                      )}
                    </VStack>
                  </Box>
                </VStack>
              </Box>
            </Flex>

            {/* Sample Video Configuration Section - REMOVED: Now integrated directly into cards above */}
          </ModalBody>
        </ModalContent>
      </Modal>

      {/* Sample Video Configuration Modal - REMOVED: Now integrated into main popup */}

      {/* ROI Configuration Modal */}
      {console.log('🔍 ROI Modal render check:', {
        showROIModal,
        configuringCameraId,
        selectedPackingMethod,
        selectedPackingMethodType: typeof selectedPackingMethod,
        roiVideoPath,
        shouldRender: showROIModal && configuringCameraId && selectedPackingMethod,
        wouldPassToProp: selectedPackingMethod as 'traditional' | 'qr'
      })}
      {showROIModal && configuringCameraId && selectedPackingMethod && (
        <ROIConfigModal
          isOpen={showROIModal}
          onClose={handleROIModalClose}
          videoPath={roiVideoPath}
          cameraId={configuringCameraId}
          packingMethod={selectedPackingMethod as 'traditional' | 'qr'}
          onSave={handleROIConfigSave}
          onError={handleROIConfigError}
        />
      )}
      </>
    </Box>
  );
}

export default PackingAreaCanvas;