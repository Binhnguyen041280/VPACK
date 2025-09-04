/**
 * SampleVideoModal Component
 * Popup riêng cho Sample Video for Traditional Detection Setup/🎯 QR Code Packing Table (Trigger)
 */

import React, { useState, useEffect } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  Box,
  VStack,
  HStack,
  Text,
  Input,
  Button,
  Badge,
  Tab,
  Tabs,
  TabList,
  TabPanels,
  TabPanel,
  Alert,
  AlertIcon,
  Spinner,
  useColorModeValue,
} from '@chakra-ui/react';
import { useColorTheme } from '@/contexts/ColorThemeContext';
import { stepConfigService, VideoValidationResponse } from '@/services/stepConfigService';

interface SampleVideoModalProps {
  isOpen: boolean;
  onClose: () => void;
  onVideoSelected: (videoPath: string, method: 'traditional' | 'qr') => void;
  onPackingMethodSelected: (method: 'traditional' | 'qr') => void;
  selectedPackingMethod?: 'traditional' | 'qr' | null;
  configuringCameraId?: string | null;
}

const SampleVideoModal: React.FC<SampleVideoModalProps> = ({
  isOpen,
  onClose,
  onVideoSelected,
  onPackingMethodSelected,
  selectedPackingMethod,
  configuringCameraId,
}) => {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'var(--chatgpt-navy-medium)');
  const cardBg = useColorModeValue('gray.50', 'var(--chatgpt-navy-light)');
  const textColor = useColorModeValue('navy.700', 'var(--chatgpt-white)');
  const secondaryText = useColorModeValue('gray.600', 'var(--chatgpt-gray-400)');
  const borderColor = useColorModeValue('gray.200', 'var(--chatgpt-gray-600)');

  // State for video paths
  const [traditionalInputPath, setTraditionalInputPath] = useState(() => {
    const platform = navigator.platform.toLowerCase();
    if (platform.includes('win')) {
      return 'C:\\\\Users\\\\%USERNAME%\\\\Videos\\\\Input';
    } else if (platform.includes('mac')) {
      return '/Users/%USER%/Movies/Input';
    } else {
      return '/home/%USER%/Videos/Input';
    }
  });
  
  const [qrInputPath, setQrInputPath] = useState(() => {
    const platform = navigator.platform.toLowerCase();
    if (platform.includes('win')) {
      return 'C:\\\\Users\\\\%USERNAME%\\\\Videos\\\\Input';
    } else if (platform.includes('mac')) {
      return '/Users/%USER%/Movies/Input';
    } else {
      return '/home/%USER%/Videos/Input';
    }
  });

  // Video validation states
  const [traditionalValidation, setTraditionalValidation] = useState<VideoValidationResponse | null>(null);
  const [traditionalValidating, setTraditionalValidating] = useState(false);
  const [qrValidation, setQrValidation] = useState<VideoValidationResponse | null>(null);
  const [qrValidating, setQrValidating] = useState(false);

  // Debounced validation
  const debounceRef = React.useRef<NodeJS.Timeout | null>(null);

  // Active tab state
  const [tabIndex, setTabIndex] = useState(selectedPackingMethod === 'qr' ? 1 : 0);

  const getDefaultInputPath = () => {
    const platform = navigator.platform.toLowerCase();
    if (platform.includes('win')) {
      return 'C:\\\\Users\\\\%USERNAME%\\\\Videos\\\\Input';
    } else if (platform.includes('mac')) {
      return '/Users/%USER%/Movies/Input';
    } else {
      return '/home/%USER%/Videos/Input';
    }
  };

  // Video validation function
  const validateVideo = async (filePath: string, videoType: 'traditional' | 'qr') => {
    if (!filePath || filePath.trim() === '' || filePath === getDefaultInputPath()) {
      // Clear validation state for empty paths
      if (videoType === 'traditional') {
        setTraditionalValidation(null);
      } else {
        setQrValidation(null);
      }
      return;
    }

    try {
      // Set loading state
      if (videoType === 'traditional') {
        setTraditionalValidating(true);
      } else {
        setQrValidating(true);
      }

      console.log(`🔍 Validating ${videoType} video:`, filePath);
      const result = await stepConfigService.validatePackingVideo(filePath, videoType);
      
      console.log(`✅ Validation result for ${videoType}:`, result);
      
      // Update validation state
      if (videoType === 'traditional') {
        setTraditionalValidation(result);
      } else {
        setQrValidation(result);
      }

    } catch (error) {
      console.error(`❌ Error validating ${videoType} video:`, error);
      
      // Set error validation state
      const errorResult: VideoValidationResponse = {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        video_file: {
          filename: filePath.split('/').pop() || '',
          path: filePath,
          duration_seconds: 0,
          duration_formatted: '0s',
          valid: false,
          error: error instanceof Error ? error.message : 'Unknown error',
          file_size_mb: 0,
          format: 'unknown'
        },
        summary: {
          valid: false,
          duration_seconds: 0,
          scan_time_ms: 0
        },
        file_info: {
          exists: false,
          readable: false
        }
      };
      
      if (videoType === 'traditional') {
        setTraditionalValidation(errorResult);
      } else {
        setQrValidation(errorResult);
      }
    } finally {
      // Clear loading state
      if (videoType === 'traditional') {
        setTraditionalValidating(false);
      } else {
        setQrValidating(false);
      }
    }
  };

  // Debounced validation handler
  const handleVideoPathChange = (filePath: string, videoType: 'traditional' | 'qr') => {
    // Clear previous debounce
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    // Set new debounced validation
    debounceRef.current = setTimeout(() => {
      validateVideo(filePath, videoType);
    }, 1000);
  };

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  // Helper function to render validation result
  const renderValidationResult = (validation: VideoValidationResponse | null, isLoading: boolean) => {
    if (isLoading) {
      return (
        <HStack spacing="8px" mt="8px">
          <Spinner size="sm" color="var(--chatgpt-purple-primary)" />
          <Text fontSize="sm" className="chatgpt-text-secondary">
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
          borderRadius="var(--chatgpt-radius-md)" 
          border="1px solid" 
          borderColor="var(--chatgpt-success)"
          className="chatgpt-animate-fade-in"
        >
          <Text fontSize="16px">✅</Text>
          <VStack align="start" spacing="2px" flex="1">
            <Text fontSize="sm" color="var(--chatgpt-success)" fontWeight="500">
              Valid video ({video_file.duration_formatted})
            </Text>
            <Text fontSize="xs" color="var(--chatgpt-success)">
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
      const borderColorError = isFileIssue ? "var(--chatgpt-error)" : "var(--chatgpt-warning)";
      const textColorError = isFileIssue ? "var(--chatgpt-error)" : "var(--chatgpt-warning)";

      return (
        <HStack 
          spacing="8px" 
          mt="8px" 
          p="8px" 
          bg={bgColor} 
          borderRadius="var(--chatgpt-radius-md)" 
          border="1px solid" 
          borderColor={borderColorError}
          className="chatgpt-animate-fade-in"
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
      onPackingMethodSelected(method);
      onVideoSelected(videoPath, method);
      onClose();
    }
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose}
      size="4xl"
      isCentered
    >
      <ModalOverlay 
        bg="rgba(26, 32, 44, 0.8)" 
        backdropFilter="blur(4px)"
      />
      <ModalContent 
        className="chatgpt-card chatgpt-animate-scale"
        maxW="75vw" 
        maxH="85vh"
        bg={bgColor}
        borderRadius="var(--chatgpt-radius-xl)"
        boxShadow="var(--chatgpt-shadow-xl)"
      >
        <ModalHeader
          className="chatgpt-text-primary"
          fontFamily="var(--chatgpt-font-family)"
          fontWeight="var(--chatgpt-font-weight-semibold)"
          borderBottom="1px solid"
          borderColor={borderColor}
        >
          📹 Sample Video Configuration
          {configuringCameraId && (
            <Badge 
              ml="12px"
              className="chatgpt-badge-info"
              bg="var(--chatgpt-purple-primary)"
              color="var(--chatgpt-white)"
            >
              Camera: {configuringCameraId}
            </Badge>
          )}
        </ModalHeader>
        <ModalCloseButton 
          className="chatgpt-hover-glow"
          color="var(--chatgpt-gray-400)"
          _hover={{ color: 'var(--chatgpt-white)' }}
        />
        
        <ModalBody p="24px">
          <Tabs 
            index={tabIndex} 
            onChange={setTabIndex}
            variant="enclosed"
            colorScheme="purple"
          >
            <TabList mb="24px">
              <Tab 
                className="chatgpt-hover-lift"
                _selected={{ 
                  bg: 'var(--chatgpt-purple-primary)', 
                  color: 'var(--chatgpt-white)',
                  borderColor: 'var(--chatgpt-purple-primary)'
                }}
                fontFamily="var(--chatgpt-font-family)"
                fontWeight="var(--chatgpt-font-weight-medium)"
              >
                📦 Traditional Detection Setup
              </Tab>
              <Tab 
                className="chatgpt-hover-lift"
                _selected={{ 
                  bg: 'var(--chatgpt-purple-primary)', 
                  color: 'var(--chatgpt-white)',
                  borderColor: 'var(--chatgpt-purple-primary)'
                }}
                fontFamily="var(--chatgpt-font-family)"
                fontWeight="var(--chatgpt-font-weight-medium)"
              >
                🎯 QR Code Packing Table (Trigger)
              </Tab>
            </TabList>

            <TabPanels>
              {/* Traditional Detection Tab */}
              <TabPanel p="0">
                <VStack spacing="24px" align="stretch">
                  {/* Method Description */}
                  <Box 
                    className="chatgpt-card chatgpt-animate-slide-up"
                    bg={cardBg}
                    p="20px"
                    borderRadius="var(--chatgpt-radius-lg)"
                    border="2px solid"
                    borderColor="var(--chatgpt-warning)"
                  >
                    <Text 
                      fontSize="sm" 
                      className="chatgpt-text-secondary"
                      lineHeight="tall"
                      fontFamily="var(--chatgpt-font-family)"
                      mb="16px"
                    >
                      Use the packing table as it currently is, without changing layout or adding any equipment. 
                      The system will detect packing events based on motion and image changes.
                    </Text>
                    
                    <HStack spacing="24px">
                      <VStack align="start" spacing="8px">
                        <Text fontSize="md" fontWeight="500" color="var(--chatgpt-success)">
                          ✅ Advantages:
                        </Text>
                        <Text fontSize="sm" className="chatgpt-text-secondary">
                          • No adjustments needed
                        </Text>
                      </VStack>
                      
                      <VStack align="start" spacing="8px">
                        <Text fontSize="md" fontWeight="500" color="var(--chatgpt-warning)">
                          ⚠️ Disadvantages:
                        </Text>
                        <Text fontSize="sm" className="chatgpt-text-secondary">
                          • Sometimes need to adjust buffer for correct events
                        </Text>
                      </VStack>
                    </HStack>
                  </Box>

                  {/* Video Path Input */}
                  <Box 
                    className="chatgpt-card chatgpt-animate-slide-up"
                    style={{ animationDelay: '0.1s' }}
                  >
                    <Text 
                      fontSize="md" 
                      fontWeight="var(--chatgpt-font-weight-semibold)" 
                      className="chatgpt-text-primary"
                      mb="12px"
                      fontFamily="var(--chatgpt-font-family)"
                    >
                      📂 Sample Video Path
                    </Text>
                    
                    <VStack spacing="12px" align="stretch">
                      <Text fontSize="sm" className="chatgpt-text-secondary">
                        📝 Choose where your traditional packing videos are stored for processing
                      </Text>
                      <Text fontSize="sm" color="var(--chatgpt-info)" fontWeight="500">
                        ⏱️ Video Requirements: Minimum 1 minute - Maximum 5 minutes duration
                      </Text>
                      <Text fontSize="sm" color="var(--chatgpt-warning)" fontStyle="italic">
                        💡 Tip: Open folder in explorer, copy path from address bar and paste here
                      </Text>
                      
                      <Input
                        className="chatgpt-input"
                        value={traditionalInputPath}
                        placeholder="Copy and paste traditional video folder path here..."
                        size="md"
                        onFocus={(e) => {
                          if (traditionalInputPath === getDefaultInputPath()) {
                            setTraditionalInputPath('');
                          }
                          e.target.select();
                        }}
                        onChange={(e) => {
                          const newPath = e.target.value;
                          setTraditionalInputPath(newPath);
                          handleVideoPathChange(newPath, 'traditional');
                        }}
                      />
                      
                      {/* Validation Result */}
                      {renderValidationResult(traditionalValidation, traditionalValidating)}
                      
                      {/* Use Video Button */}
                      {traditionalValidation?.success && traditionalValidation.video_file?.valid && (
                        <Button
                          className="chatgpt-button-primary chatgpt-hover-lift"
                          bg="var(--chatgpt-purple-primary)"
                          color="var(--chatgpt-white)"
                          fontFamily="var(--chatgpt-font-family)"
                          fontWeight="var(--chatgpt-font-weight-medium)"
                          leftIcon={<Text>🎯</Text>}
                          onClick={() => handleUseVideo('traditional')}
                          _hover={{
                            bg: 'var(--chatgpt-purple-light)',
                            transform: 'translateY(-2px)',
                            boxShadow: 'var(--chatgpt-shadow-lg)'
                          }}
                        >
                          Use This Video for ROI Configuration
                        </Button>
                      )}
                    </VStack>
                  </Box>
                </VStack>
              </TabPanel>

              {/* QR Code Tab */}
              <TabPanel p="0">
                <VStack spacing="24px" align="stretch">
                  {/* Method Description */}
                  <Box 
                    className="chatgpt-card chatgpt-animate-slide-up"
                    bg={cardBg}
                    p="20px"
                    borderRadius="var(--chatgpt-radius-lg)"
                    border="2px solid"
                    borderColor="var(--chatgpt-success)"
                  >
                    <HStack justify="space-between" mb="16px">
                      <Badge 
                        className="chatgpt-badge-success"
                        bg="var(--chatgpt-success)"
                        color="var(--chatgpt-white)"
                        fontSize="sm"
                      >
                        Recommended Method
                      </Badge>
                    </HStack>
                    
                    <Text 
                      fontSize="sm" 
                      className="chatgpt-text-secondary"
                      lineHeight="tall"
                      mb="16px"
                      fontFamily="var(--chatgpt-font-family)"
                    >
                      Paste QR Code (Trigger) in the center of packing area. When packages move to cover/uncover the QR code, 
                      the system will accurately identify the start and end times of packing events.
                    </Text>
                    
                    <VStack align="start" spacing="8px">
                      <Text fontSize="md" fontWeight="500" color="var(--chatgpt-success)">
                        ✅ Advantages:
                      </Text>
                      <Text fontSize="sm" className="chatgpt-text-secondary">
                        • High timing accuracy<br/>
                        • Clear distinction of packing events
                      </Text>
                    </VStack>
                  </Box>

                  {/* QR Code Display and Video Path - Horizontal Layout */}
                  <HStack spacing="20px" align="start">
                    {/* QR Code Display */}
                    <Box 
                      className="chatgpt-card chatgpt-animate-slide-up"
                      style={{ animationDelay: '0.1s' }}
                      flex="1"
                      minW="0"
                    >
                      <Text 
                        fontSize="md" 
                        fontWeight="var(--chatgpt-font-weight-semibold)" 
                        className="chatgpt-text-primary"
                        mb="12px"
                        fontFamily="var(--chatgpt-font-family)"
                      >
                        🏷️ Trigger QR Code for Printing
                      </Text>
                      
                      <VStack spacing="16px" align="center">
                        <Text fontSize="sm" className="chatgpt-text-secondary" textAlign="center">
                          📋 Print this QR code and place it in the center of your packing area
                        </Text>
                        
                        {/* QR Code Image and Buttons Layout */}
                        <Box position="relative" display="flex" justifyContent="center" alignItems="center" width="100%" minH="180px">
                          {/* QR Code Image - Centered in container */}
                          <Box 
                            className="chatgpt-hover-scale chatgpt-hover-glow"
                            p="12px" 
                            bg="white" 
                            borderRadius="var(--chatgpt-radius-md)"
                            border="2px solid" 
                            borderColor="var(--chatgpt-gray-300)"
                            boxShadow="var(--chatgpt-shadow-md)"
                            cursor="pointer"
                            onClick={() => {
                              const link = document.createElement('a');
                              link.href = '/images/TimeGo-qr.png';
                              link.download = 'TimeGo-QR-Code.png';
                              document.body.appendChild(link);
                              link.click();
                              document.body.removeChild(link);
                            }}
                            width="144px"
                            height="144px"
                            display="flex"
                            justifyContent="center"
                            alignItems="center"
                            flexShrink={0}
                          >
                            <img 
                              src="/images/TimeGo-qr.png" 
                              alt="TimeGo QR Code" 
                              style={{
                                width: '120px',
                                height: '120px',
                                objectFit: 'contain'
                              }}
                            />
                          </Box>
                          
                          {/* Print & Download Buttons - Positioned to the right */}
                          <VStack 
                            spacing="12px" 
                            align="stretch"
                            position="absolute"
                            right="16px"
                            top="50%"
                            transform="translateY(-50%)"
                            minW="120px"
                          >
                            <Button
                              className="chatgpt-button-secondary chatgpt-hover-lift"
                              leftIcon={<Text fontSize="sm">📥</Text>}
                              size="sm"
                              fontSize="sm"
                              onClick={() => {
                                const link = document.createElement('a');
                                link.href = '/images/TimeGo-qr.png';
                                link.download = 'TimeGo-QR-Code.png';
                                document.body.appendChild(link);
                                link.click();
                                document.body.removeChild(link);
                              }}
                            >
                              Download
                            </Button>
                            
                            <Button 
                              className="chatgpt-button-primary chatgpt-hover-lift"
                              bg="var(--chatgpt-success)"
                              color="var(--chatgpt-white)"
                              leftIcon={<Text fontSize="sm">🖨️</Text>}
                              size="sm"
                              fontSize="sm"
                              _hover={{
                                bg: 'var(--chatgpt-success)',
                                filter: 'brightness(1.1)',
                                transform: 'translateY(-1px)',
                                boxShadow: 'var(--chatgpt-shadow-sm)'
                              }}
                              onClick={() => {
                                // Print QR code logic here
                                const printWindow = window.open('', '_blank');
                                if (printWindow) {
                                  printWindow.document.write(`
                                    <html>
                                      <head><title>TimeGo QR Code - Print</title></head>
                                      <body style="display:flex;justify-content:center;align-items:center;height:100vh;margin:0;">
                                        <img src="/images/TimeGo-qr.png" style="width:300px;height:300px;" />
                                      </body>
                                    </html>
                                  `);
                                  printWindow.document.close();
                                  printWindow.print();
                                  printWindow.close();
                                }
                              }}
                            >
                              Print
                            </Button>
                          </VStack>
                        </Box>
                      </VStack>
                    </Box>

                    {/* Video Path Input */}
                    <Box 
                      className="chatgpt-card chatgpt-animate-slide-up"
                      style={{ animationDelay: '0.2s' }}
                      flex="1"
                      minW="0"
                    >
                      <Text 
                        fontSize="md" 
                        fontWeight="var(--chatgpt-font-weight-semibold)" 
                        className="chatgpt-text-primary"
                        mb="12px"
                        fontFamily="var(--chatgpt-font-family)"
                      >
                        📂 Sample Video Path
                      </Text>
                      
                      <VStack spacing="12px" align="stretch">
                        <Text fontSize="sm" className="chatgpt-text-secondary">
                          📝 Choose where your QR code packing videos are stored for processing
                        </Text>
                        <Text fontSize="sm" color="var(--chatgpt-success)" fontWeight="500">
                          ⏱️ Video Requirements: Minimum 1 minute - Maximum 5 minutes duration
                        </Text>
                        <Text fontSize="sm" color="var(--chatgpt-warning)" fontStyle="italic">
                          💡 Tip: Open folder in explorer, copy path from address bar and paste here
                        </Text>
                        
                        <Input
                          className="chatgpt-input"
                          value={qrInputPath}
                          placeholder="Copy and paste QR video folder path here..."
                          size="md"
                          onFocus={(e) => {
                            if (qrInputPath === getDefaultInputPath()) {
                              setQrInputPath('');
                            }
                            e.target.select();
                          }}
                          onChange={(e) => {
                            const newPath = e.target.value;
                            setQrInputPath(newPath);
                            handleVideoPathChange(newPath, 'qr');
                          }}
                        />
                        
                        {/* Validation Result */}
                        {renderValidationResult(qrValidation, qrValidating)}
                        
                        {/* Use Video Button */}
                        {qrValidation?.success && qrValidation.video_file?.valid && (
                          <Button
                            className="chatgpt-button-primary chatgpt-hover-lift"
                            bg="var(--chatgpt-purple-primary)"
                            color="var(--chatgpt-white)"
                            fontFamily="var(--chatgpt-font-family)"
                            fontWeight="var(--chatgpt-font-weight-medium)"
                            leftIcon={<Text>🎯</Text>}
                            onClick={() => handleUseVideo('qr')}
                            _hover={{
                              bg: 'var(--chatgpt-purple-light)',
                              transform: 'translateY(-2px)',
                              boxShadow: 'var(--chatgpt-shadow-lg)'
                            }}
                          >
                            Use This Video for ROI Configuration
                          </Button>
                        )}
                      </VStack>
                    </Box>
                  </HStack>
                </VStack>
              </TabPanel>
            </TabPanels>
          </Tabs>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default SampleVideoModal;