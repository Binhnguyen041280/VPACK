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
import SampleVideoModal from '@/components/roi/SampleVideoModal';

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
  const [camerasDisabled, setCamerasDisabled] = useState(false);
  
  // ROI configuration modal state
  const [showROIModal, setShowROIModal] = useState(false);
  const [roiVideoPath, setROIVideoPath] = useState<string>('');
  
  // Sample Video Modal state
  const [showSampleVideoModal, setShowSampleVideoModal] = useState(false);
  
  // Helper function to check if a camera is currently being configured
  const isCameraConfiguring = (cameraId: string): boolean => {
    return configuringCameraId === cameraId;
  };
  
  // Helper function to check if a camera should be disabled
  const isCameraDisabled = (cameraId: string): boolean => {
    return camerasDisabled && configuringCameraId !== cameraId;
  };
  
  // Function to cancel camera configuration
  const cancelCameraConfiguration = () => {
    console.log('🚫 Cancelling camera configuration');
    setConfiguringCameraId(null);
    setCamerasDisabled(false);
    setShowCameraPopup(false);
    setSelectedCameraForConfig(null);
    // Keep selected cameras as they were
  };
  
  // Function to complete camera configuration
  const completeCameraConfiguration = () => {
    console.log('✅ Completing camera configuration');
    setConfiguringCameraId(null);
    setCamerasDisabled(false);
    setShowCameraPopup(false);
    setSelectedCameraForConfig(null);
  };
  
  // ROI configuration handlers
  const handleDefineDetectionZone = () => {
    if (!selectedPackingMethod) {
      console.warn('No packing method selected');
      return;
    }
    
    // Get the appropriate video path based on selected method
    const videoPath = selectedPackingMethod === 'traditional' ? traditionalInputPath : qrInputPath;
    
    if (!videoPath || videoPath === getDefaultInputPath()) {
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
    
    // Update parent component with configuration first
    onStepChange?.('packing_area', {
      selectedCameras,
      packingMethod: selectedPackingMethod,
      roiConfiguration: config,
      configuredCamera: configuringCameraId
    });
    
    // Complete the camera configuration workflow (reset states)
    completeCameraConfiguration();
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
          // Transform selectedCameras into availableCameras format
          const transformedCameras: Camera[] = response.data.selectedCameras.map((cameraName, index) => ({
            id: cameraName, // Use camera name as ID
            name: `Camera - ${cameraName}`, // Add "Camera - " prefix
            ip: `192.168.1.${100 + index}`, // Generate mock IP based on index
            status: 'online' as const // Default to online
          }));
          
          console.log('✅ PackingAreaCanvas - Transformed cameras from processing_config:', transformedCameras);
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
    >
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
            
            {/* Configuration Status Message */}
            {configuringCameraId && (
              <Box 
                bg="orange.50" 
                border="2px solid" 
                borderColor="orange.300" 
                borderRadius="12px" 
                p="12px" 
                mb="16px"
              >
                <Flex align="center" justify="space-between">
                  <HStack spacing="8px">
                    <Text fontSize="16px">🔧</Text>
                    <Text fontSize={adaptiveConfig.fontSize.small} color="orange.700" fontWeight="500">
                      Configuring {availableCameras.find(c => c.id === configuringCameraId)?.name} - Other cameras temporarily disabled
                    </Text>
                  </HStack>
                  <Button 
                    className="chatgpt-button-primary chatgpt-hover-lift"
                    bg="var(--chatgpt-purple-primary)"
                    color="var(--chatgpt-white)"
                    size="sm" 
                    fontSize="sm"
                    fontFamily="var(--chatgpt-font-family)"
                    fontWeight="var(--chatgpt-font-weight-medium)"
                    onClick={cancelCameraConfiguration}
                    _hover={{
                      bg: 'var(--chatgpt-purple-light)',
                      transform: 'translateY(-2px)',
                      boxShadow: 'var(--chatgpt-shadow-lg)'
                    }}
                  >
                    Cancel
                  </Button>
                </Flex>
              </Box>
            )}
            
            {/* Success State - Display Cameras */}
            {!isLoadingCameras && !cameraError && availableCameras.length > 0 && (
              <>
                <VStack spacing="8px" align="stretch">
                  {availableCameras.map((camera) => {
                    const isDisabled = isCameraDisabled(camera.id);
                    const isConfiguring = isCameraConfiguring(camera.id);
                    
                    return (
                      <Flex
                        key={camera.id}
                        align="center"
                        p="8px"
                        borderRadius="8px"
                        border="1px solid"
                        borderColor={borderColor}
                        bg={bgColor}
                        opacity={isDisabled ? 0.5 : 1}
                        cursor={isDisabled ? 'not-allowed' : 'default'}
                        transition="opacity 0.2s ease"
                      >
                        <Checkbox
                          isChecked={selectedCameras.includes(camera.id)}
                          isDisabled={isDisabled}
                          onChange={(e) => {
                            if (e.target.checked) {
                              // Single camera workflow: disable others when selecting one
                              console.log(`🔧 Starting configuration for camera: ${camera.id}`);
                              setSelectedCameras(prev => [...prev, camera.id]);
                              setSelectedCameraForConfig(camera.id);
                              setConfiguringCameraId(camera.id);
                              setCamerasDisabled(true);
                              setShowCameraPopup(true);
                            } else {
                              // Only allow unchecking if not currently configuring this camera
                              if (!isConfiguring) {
                                setSelectedCameras(prev => prev.filter(id => id !== camera.id));
                              }
                            }
                            onStepChange?.('packing_area', { selectedCameras });
                          }}
                          colorScheme="brand"
                          me="12px"
                        />
                        <Box flex="1">
                          <Flex align="center" gap="8px">
                            <Text 
                              fontSize={adaptiveConfig.fontSize.body} 
                              fontWeight="600" 
                              color={isDisabled ? secondaryText : textColor}
                            >
                              {camera.name}
                            </Text>
                            {isConfiguring && (
                              <Text fontSize="12px" color="orange.500">⚙️</Text>
                            )}
                          </Flex>
                          <Text 
                            fontSize={adaptiveConfig.fontSize.small} 
                            color={isDisabled ? 'gray.400' : secondaryText}
                          >
                            {camera.ip} • Status: {camera.status}
                            {isDisabled && ' (Temporarily disabled)'}
                          </Text>
                        </Box>
                        <Box
                          w="8px"
                          h="8px"
                          borderRadius="full"
                          bg={camera.status === 'online' ? (isDisabled ? 'gray.300' : 'green.400') : 'red.400'}
                          flexShrink={0}
                        />
                      </Flex>
                    );
                  })}
                </VStack>
                <Text fontSize={adaptiveConfig.fontSize.small} color="blue.500" mt="12px" fontStyle="italic">
                  📊 Selected: {selectedCameras.length} camera(s) for detection monitoring
                </Text>
              </>
            )}
          </Box>
        </Box>
        
        {/* Sample Video Configuration Button */}
        {selectedPackingMethod && (
          <Box>
            <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
              🎬 Video Configuration
            </Text>
            <Box bg={cardBg} p="16px" borderRadius="12px" border="1px solid" borderColor={borderColor}>
              <VStack spacing="12px">
                <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText} textAlign="center">
                  Configure sample videos for {selectedPackingMethod === 'traditional' ? 'Traditional Detection' : 'QR Code Packing Table (Trigger)'}
                </Text>
                <Button
                  colorScheme="brand"
                  size="lg"
                  leftIcon={<Text>📹</Text>}
                  onClick={() => setShowSampleVideoModal(true)}
                  _hover={{ transform: 'translateY(-2px)', boxShadow: 'lg' }}
                >
                  {selectedPackingMethod === 'traditional' 
                    ? 'Configure Traditional Detection Setup' 
                    : 'Configure QR Code Packing Table (Trigger)'
                  }
                </Button>
              </VStack>
            </Box>
          </Box>
        )}



        {/* ROI Configuration Status */}
        {configuringCameraId && selectedPackingMethod && (
          <Box>
            <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
              🎯 ROI Configuration Status
            </Text>
            <Box 
              bg={cardBg} 
              p="16px" 
              borderRadius="12px"
              border="2px solid" 
              borderColor={currentColors.brand500}
              minH="150px"
            >
              <VStack spacing="12px" align="stretch">
                <HStack justify="space-between">
                  <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor}>
                    Camera: {availableCameras.find(c => c.id === configuringCameraId)?.name}
                  </Text>
                  <Badge colorScheme="blue">
                    {selectedPackingMethod === 'traditional' ? 'Traditional' : 'QR Code'}
                  </Badge>
                </HStack>
                
                {/* Video Path Status */}
                <Box>
                  <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText} mb="4px">
                    Training Video Status:
                  </Text>
                  {roiVideoPath ? (
                    <HStack spacing="8px">
                      <Text fontSize="16px">✅</Text>
                      <Text fontSize="sm" color="green.600" fontWeight="500">
                        Video configured and ready for ROI setup
                      </Text>
                    </HStack>
                  ) : (
                    <Text fontSize="sm" color="orange.500">
                      Please configure training video using the button above
                    </Text>
                  )}
                </Box>
                
                {/* Instructions */}
                <Box>
                  <Text fontSize={adaptiveConfig.fontSize.small} color="blue.600" fontStyle="italic">
                    💡 Once video is validated, ROI configuration modal will open automatically
                  </Text>
                </Box>
              </VStack>
            </Box>
          </Box>
        )}

        {/* Detection Stats */}
        <Box
          bg={cardBg}
          borderRadius="12px"
          p="16px"
          border="1px solid"
          borderColor="purple.400"
        >
          <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor} mb="8px">
            📈 Detection Statistics:
          </Text>
          <VStack align="stretch" spacing="4px">
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>Today:</strong> 47 detections, 23 alerts sent
            </Text>
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>This Week:</strong> 312 detections, 85% accuracy
            </Text>
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>Active Zones:</strong> 2 configured, 1 active
            </Text>
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>Last Detection:</strong> 2 minutes ago
            </Text>
          </VStack>
        </Box>
      </VStack>

      {/* Camera Configuration Popup */}
      <Modal 
        isOpen={showCameraPopup} 
        onClose={cancelCameraConfiguration}
        size="6xl"
        isCentered
      >
        <ModalOverlay bg="blackAlpha.600" />
        <ModalContent maxW="90vw" maxH="90vh">
          <ModalCloseButton />
          <ModalBody pt="40px">
            <Flex direction="row" h="70vh" gap="20px">
              {/* Left Panel - Section 1 */}
              <Box 
                flex="1" 
                bg={cardBg} 
                p="20px" 
                borderRadius="12px"
                border="1px solid"
                borderColor={borderColor}
                cursor="pointer"
                _hover={{ transform: 'translateY(-2px)', boxShadow: 'lg' }}
                transition="all 0.2s ease"
                onClick={() => {
                  console.log('🎯 Traditional method selected - Opening Sample Video Modal');
                  setSelectedPackingMethod('traditional');
                  setShowCameraPopup(false);
                  setShowSampleVideoModal(true);
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
                </VStack>
              </Box>
              
              {/* Right Panel - Section 2 */}
              <Box 
                flex="1" 
                bg={cardBg} 
                p="20px" 
                borderRadius="12px"
                border="2px solid"
                borderColor={currentColors.brand500}
                cursor="pointer"
                _hover={{ transform: 'translateY(-2px)', boxShadow: 'lg' }}
                transition="all 0.2s ease"
                position="relative"
                onClick={() => {
                  console.log('🎯 QR method selected - Opening Sample Video Modal');
                  setSelectedPackingMethod('qr');
                  setShowCameraPopup(false);
                  setShowSampleVideoModal(true);
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
                  
                  {/* Visual Illustration */}
                  <Box>
                    <Text fontSize="md" fontWeight="500" color={textColor} mb="8px">
                      📷 Setup Illustration:
                    </Text>
                    <Box 
                      bg={cardBg} 
                      p="20px" 
                      borderRadius="12px"
                      border="2px dashed" 
                      borderColor={currentColors.brand500}
                      minH="180px"
                      h="180px"
                      position="relative"
                      w="80%"
                      mx="auto"
                    >
                      {/* Camera preview area text - moved to top right corner */}
                      <Text 
                        position="absolute"
                        top="8px"
                        right="8px"
                        fontSize={adaptiveConfig.fontSize.small} 
                        color={secondaryText}
                      >
                        Camera preview area
                      </Text>
                      
                      {/* Packing Area - Outer frame around QR Code */}
                      <Box
                        position="absolute"
                        top="50%"
                        left="50%"
                        transform="translate(-50%, -50%)"
                        w="140px"
                        h="100px"
                        border="2px solid"
                        borderColor="orange.400"
                        bg="orange.50"
                        borderRadius="8px"
                        display="flex"
                        alignItems="center"
                        justifyContent="center"
                      >
                        {/* Packing area text */}
                        <Text 
                          position="absolute"
                          top="4px"
                          left="6px"
                          fontSize={adaptiveConfig.fontSize.small} 
                          color="orange.600"
                          fontWeight="500"
                        >
                          Packing area
                        </Text>
                        
                        {/* QR Code Zone in center of packing area */}
                        <Box
                          w="70px"
                          h="45px"
                          border="2px solid"
                          borderColor={currentColors.brand500}
                          bg={`${currentColors.brand500}20`}
                          borderRadius="6px"
                          display="flex"
                          alignItems="center"
                          justifyContent="center"
                        >
                          <Text fontSize={adaptiveConfig.fontSize.small} color={currentColors.brand500} fontWeight="bold">
                            QR Code
                          </Text>
                        </Box>
                      </Box>
                    </Box>
                  </Box>
                </VStack>
              </Box>
            </Flex>
          </ModalBody>
        </ModalContent>
      </Modal>

      {/* Sample Video Configuration Modal */}
      <SampleVideoModal
        isOpen={showSampleVideoModal}
        onClose={() => setShowSampleVideoModal(false)}
        onVideoSelected={(videoPath, method) => {
          console.log('📹 Video selected:', { videoPath, method });
          setROIVideoPath(videoPath);
          // Auto-open ROI modal after video selection
          setTimeout(() => {
            setShowROIModal(true);
          }, 500);
        }}
        onPackingMethodSelected={(method) => {
          console.log('📦 Packing method selected:', method);
          setSelectedPackingMethod(method);
        }}
        selectedPackingMethod={selectedPackingMethod}
        configuringCameraId={configuringCameraId}
      />

      {/* ROI Configuration Modal */}
      {console.log('🔍 ROI Modal render check:', {
        showROIModal,
        configuringCameraId,
        selectedPackingMethod,
        roiVideoPath,
        shouldRender: showROIModal && configuringCameraId && selectedPackingMethod
      })}
      {showROIModal && configuringCameraId && selectedPackingMethod && (
        <ROIConfigModal
          isOpen={showROIModal}
          onClose={handleROIModalClose}
          videoPath={roiVideoPath}
          cameraId={configuringCameraId}
          packingMethod={selectedPackingMethod}
          onSave={handleROIConfigSave}
          onError={handleROIConfigError}
        />
      )}

    </Box>
  );
}

export default PackingAreaCanvas;