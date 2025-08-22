'use client';

import {
  Box,
  Flex,
  Text,
  Button,
  Icon,
  VStack,
  HStack,
  Divider,
  Input,
  Select,
  Checkbox,
  SimpleGrid,
  useColorModeValue
} from '@chakra-ui/react';
import { MdAutoAwesome, MdVideoLibrary, MdCamera } from 'react-icons/md';
import { useColorTheme } from '@/contexts/ColorThemeContext';
import LocationTimeCanvas from './LocationTimeCanvas';

interface CanvasMessageProps {
  configStep: 'brandname' | 'location_time' | 'file_save' | 'video_source' | 'packing_area' | 'timing';
  onStepChange?: (stepName: string, data: any) => void;
}

export default function CanvasMessage({ configStep, onStepChange }: CanvasMessageProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  // Render canvas based on current step
  const renderCanvas = () => {
    switch (configStep) {
      case 'brandname':
        return <BrandnameCanvas />;
      case 'location_time':
        return <LocationTimeCanvas onStepChange={onStepChange} />;
      case 'file_save':
        return <FileSaveCanvas onStepChange={onStepChange} />;
      case 'video_source':
        return <VideoSourceCanvas onStepChange={onStepChange} />;
      case 'packing_area':
        return <PackingAreaCanvas onStepChange={onStepChange} />;
      case 'timing':
        return <TimingCanvas onStepChange={onStepChange} />;
      default:
        return <BrandnameCanvas />;
    }
  };

  return (
    <Flex w="100%" mb="24px" align="flex-start">
      {/* Bot Avatar */}
      <Flex
        borderRadius="full"
        justify="center"
        align="center"
        bg={currentColors.gradient}
        me="12px"
        h="32px"
        minH="32px"
        minW="32px"
        flexShrink={0}
      >
        <Icon
          as={MdAutoAwesome}
          width="16px"
          height="16px"
          color="white"
        />
      </Flex>
      
      {/* Dynamic Canvas Content */}
      {renderCanvas()}
    </Flex>
  );
}

// Brandname Canvas Component (Step 1)
function BrandnameCanvas() {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const cardBg = useColorModeValue('gray.50', 'navy.700');

  return (
    <Box
      bg={bgColor}
      borderRadius="16px"
      p="20px"
      maxW={{ base: '95%', md: '85%', xl: '75%' }}
      w="100%"
      border="1px solid"
      borderColor={borderColor}
      boxShadow="0px 4px 12px rgba(112, 144, 176, 0.08)"
    >
      {/* Header */}
      <Flex justify="space-between" align="center" mb="20px">
        <Text fontSize="lg" fontWeight="700" color={textColor}>
          🏢 Step 1: Brandname Setup
        </Text>
      </Flex>

      <VStack spacing="16px" align="stretch">
        {/* Company Information Section - Current Step */}
        <Box>
          <HStack mb="12px">
            <Text fontSize="md" fontWeight="600" color={textColor}>
              🏢 Step 1: Company Information
            </Text>
          </HStack>
          
          <Box
            bg={cardBg}
            p="16px"
            borderRadius="12px"
            textAlign="center"
          >
            <Text fontSize="sm" fontWeight="600" color={textColor} mb="8px">
              Company/Brand Name
            </Text>
            <Text fontSize="xs" color="gray.500" mb="12px">
              Type your company name in the chat below and click Submit
            </Text>
            <Text fontSize="xs" color="gray.400" fontStyle="italic">
              Example: "TechCorp Manufacturing"
            </Text>
          </Box>
        </Box>

        <Divider />

        {/* Status Summary */}
        <Box
          bg={cardBg}
          p="16px"
          borderRadius="12px"
          textAlign="center"
        >
          <Text fontSize="sm" fontWeight="600" color={textColor} mb="4px">
            ⏳ Waiting for Company Name
          </Text>
          <Text fontSize="xs" color="gray.500">
            Please enter your company name in the chat and click Submit
          </Text>
        </Box>
      </VStack>
    </Box>
  );
}

// Step 3: File Save Canvas
function FileSaveCanvas({ onStepChange }: { onStepChange?: (stepName: string, data: any) => void }) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  const cardBg = useColorModeValue('gray.50', 'navy.700');

  return (
    <Box
      bg={bgColor}
      borderRadius="16px"
      p="20px"
      maxW={{ base: '95%', md: '85%', xl: '75%' }}
      w="100%"
      border="1px solid"
      borderColor={borderColor}
      boxShadow="0px 4px 12px rgba(112, 144, 176, 0.08)"
    >
      {/* Header */}
      <Flex justify="space-between" align="center" mb="20px">
        <Text fontSize="lg" fontWeight="700" color={textColor}>
          💾 Step 3: File Storage Settings
        </Text>
      </Flex>

      <VStack spacing="16px" align="stretch">
        {/* Storage Path Section */}
        <Box>
          <Text fontSize="md" fontWeight="600" color={textColor} mb="12px">
            📁 Storage Path
          </Text>
          <Box bg={cardBg} p="16px" borderRadius="12px">
            <HStack spacing="12px" mb="8px">
              <Input
                placeholder="/home/user/vtrack/videos"
                size="sm"
                borderColor={borderColor}
                _focus={{ borderColor: currentColors.brand500 }}
                bg={bgColor}
                onChange={(e) => onStepChange?.('file_save', { storagePath: e.target.value })}
              />
              <Button
                size="sm"
                variant="outline"
                borderColor={borderColor}
                _hover={{ bg: useColorModeValue('gray.100', 'whiteAlpha.100') }}
              >
                Browse
              </Button>
            </HStack>
            <Text fontSize="xs" color={secondaryText}>
              📋 Current: /Users/vtrack/Documents/Videos
            </Text>
          </Box>
        </Box>

        {/* Retention Policy */}
        <Box>
          <Text fontSize="md" fontWeight="600" color={textColor} mb="12px">
            🗓️ File Retention
          </Text>
          <SimpleGrid columns={2} spacing="12px">
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize="sm" fontWeight="500" color={textColor} mb="8px">
                Auto-delete after:
              </Text>
              <HStack spacing="8px">
                <Input
                  placeholder="30"
                  size="sm"
                  w="60px"
                  borderColor={borderColor}
                  _focus={{ borderColor: currentColors.brand500 }}
                  onChange={() => onStepChange?.('file_save', { retention: '30' })}
                />
                <Select size="sm" borderColor={borderColor}>
                  <option value="days">Days</option>
                  <option value="weeks">Weeks</option>
                  <option value="months">Months</option>
                </Select>
              </HStack>
            </Box>
            
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize="sm" fontWeight="500" color={textColor} mb="8px">
                Max Storage:
              </Text>
              <HStack spacing="8px">
                <Input
                  placeholder="100"
                  size="sm"
                  w="60px"
                  borderColor={borderColor}
                  _focus={{ borderColor: currentColors.brand500 }}
                  onChange={(e) => onStepChange?.('file_save', { maxStorage: e.target.value })}
                />
                <Select size="sm" borderColor={borderColor} onChange={(e) => onStepChange?.('file_save', { storageUnit: e.target.value })}>
                  <option value="GB">GB</option>
                  <option value="TB">TB</option>
                </Select>
              </HStack>
            </Box>
          </SimpleGrid>
        </Box>

        {/* File Organization */}
        <Box>
          <Text fontSize="md" fontWeight="600" color={textColor} mb="12px">
            📋 File Organization
          </Text>
          <VStack spacing="8px" align="stretch">
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('file_save', { organizeByDate: e.target.checked })}>
              <Text fontSize="sm">Organize by date (YYYY/MM/DD)</Text>
            </Checkbox>
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('file_save', { separateFolders: e.target.checked })}>
              <Text fontSize="sm">Separate folders for each camera</Text>
            </Checkbox>
            <Checkbox colorScheme="brand" onChange={(e) => onStepChange?.('file_save', { compressOld: e.target.checked })}>
              <Text fontSize="sm">Compress videos older than 7 days</Text>
            </Checkbox>
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('file_save', { generateThumbnails: e.target.checked })}>
              <Text fontSize="sm">Generate thumbnails</Text>
            </Checkbox>
          </VStack>
        </Box>

        {/* Current Status */}
        <Box
          bg={useColorModeValue('blue.50', 'blue.900')}
          borderRadius="12px"
          p="16px"
          border="1px solid"
          borderColor={useColorModeValue('blue.200', 'blue.700')}
        >
          <Text fontSize="sm" fontWeight="600" color={textColor} mb="8px">
            💽 Current Storage Status:
          </Text>
          <VStack align="stretch" spacing="4px">
            <Text fontSize="xs" color={secondaryText}>
              <strong>Used:</strong> 45.2 GB / 100 GB (45%)
            </Text>
            <Text fontSize="xs" color={secondaryText}>
              <strong>Files:</strong> 1,247 videos, 3,891 thumbnails
            </Text>
            <Text fontSize="xs" color={secondaryText}>
              <strong>Oldest:</strong> 28 days ago
            </Text>
          </VStack>
        </Box>
      </VStack>
    </Box>
  );
}

// Step 4: Video Source Canvas
function VideoSourceCanvas({ onStepChange }: { onStepChange?: (stepName: string, data: any) => void }) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  const cardBg = useColorModeValue('gray.50', 'navy.700');

  return (
    <Box
      bg={bgColor}
      borderRadius="16px"
      p="20px"
      maxW={{ base: '95%', md: '85%', xl: '75%' }}
      w="100%"
      border="1px solid"
      borderColor={borderColor}
      boxShadow="0px 4px 12px rgba(112, 144, 176, 0.08)"
    >
      {/* Header */}
      <Flex justify="space-between" align="center" mb="20px">
        <Text fontSize="lg" fontWeight="700" color={textColor}>
          📹 Step 4: Video Source Configuration
        </Text>
      </Flex>

      <VStack spacing="16px" align="stretch">
        {/* Source Type Selection */}
        <Box>
          <Text fontSize="md" fontWeight="600" color={textColor} mb="12px">
            🎥 Video Source Type
          </Text>
          <SimpleGrid columns={3} spacing="12px">
            <Box 
              bg={cardBg} 
              p="16px" 
              borderRadius="12px" 
              border="2px solid" 
              borderColor={currentColors.brand500}
              cursor="pointer"
              onClick={() => onStepChange?.('video_source', { sourceType: 'local_camera' })}
            >
              <Icon as={MdCamera} w="24px" h="24px" color={currentColors.brand500} mb="8px" />
              <Text fontSize="sm" fontWeight="600" color={textColor}>Local Camera</Text>
              <Text fontSize="xs" color={secondaryText}>USB/Built-in</Text>
            </Box>
            
            <Box 
              bg={cardBg} 
              p="16px" 
              borderRadius="12px" 
              border="1px solid" 
              borderColor={borderColor}
              cursor="pointer"
              onClick={() => onStepChange?.('video_source', { sourceType: 'ip_camera' })}
            >
              <Text fontSize="lg" mb="8px">🌐</Text>
              <Text fontSize="sm" fontWeight="600" color={textColor}>IP Camera</Text>
              <Text fontSize="xs" color={secondaryText}>ONVIF/RTSP</Text>
            </Box>
            
            <Box 
              bg={cardBg} 
              p="16px" 
              borderRadius="12px" 
              border="1px solid" 
              borderColor={borderColor}
              cursor="pointer"
              onClick={() => onStepChange?.('video_source', { sourceType: 'cloud_storage' })}
            >
              <Text fontSize="lg" mb="8px">☁️</Text>
              <Text fontSize="sm" fontWeight="600" color={textColor}>Cloud Storage</Text>
              <Text fontSize="xs" color={secondaryText}>Google Drive</Text>
            </Box>
          </SimpleGrid>
        </Box>

        {/* Camera Settings */}
        <Box>
          <Text fontSize="md" fontWeight="600" color={textColor} mb="12px">
            ⚙️ Camera Settings
          </Text>
          <SimpleGrid columns={2} spacing="12px">
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize="sm" fontWeight="500" color={textColor} mb="8px">
                Resolution:
              </Text>
              <Select size="sm" borderColor={borderColor} defaultValue="1080p" onChange={(e) => onStepChange?.('video_source', { resolution: e.target.value })}>
                <option value="4K">4K (3840x2160)</option>
                <option value="1080p">1080p (1920x1080)</option>
                <option value="720p">720p (1280x720)</option>
                <option value="480p">480p (640x480)</option>
              </Select>
            </Box>
            
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize="sm" fontWeight="500" color={textColor} mb="8px">
                Frame Rate:
              </Text>
              <Select size="sm" borderColor={borderColor} defaultValue="30" onChange={(e) => onStepChange?.('video_source', { frameRate: e.target.value })}>
                <option value="60">60 FPS</option>
                <option value="30">30 FPS</option>
                <option value="24">24 FPS</option>
                <option value="15">15 FPS</option>
              </Select>
            </Box>
          </SimpleGrid>
        </Box>

        {/* Recording Options */}
        <Box>
          <Text fontSize="md" fontWeight="600" color={textColor} mb="12px">
            🔴 Recording Options
          </Text>
          <VStack spacing="8px" align="stretch">
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('video_source', { continuousRecording: e.target.checked })}>
              <Text fontSize="sm">Continuous recording</Text>
            </Checkbox>
            <Checkbox colorScheme="brand" onChange={(e) => onStepChange?.('video_source', { motionTriggered: e.target.checked })}>
              <Text fontSize="sm">Motion-triggered recording</Text>
            </Checkbox>
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('video_source', { audioRecording: e.target.checked })}>
              <Text fontSize="sm">Audio recording</Text>
            </Checkbox>
            <Checkbox colorScheme="brand" onChange={(e) => onStepChange?.('video_source', { nightVision: e.target.checked })}>
              <Text fontSize="sm">Night vision mode</Text>
            </Checkbox>
          </VStack>
        </Box>

        {/* Camera Status */}
        <Box
          bg={useColorModeValue('green.50', 'green.900')}
          borderRadius="12px"
          p="16px"
          border="1px solid"
          borderColor={useColorModeValue('green.200', 'green.700')}
        >
          <Text fontSize="sm" fontWeight="600" color={textColor} mb="8px">
            📊 Camera Status:
          </Text>
          <VStack align="stretch" spacing="4px">
            <Text fontSize="xs" color={secondaryText}>
              <strong>Device:</strong> USB Camera (HD WebCam C270)
            </Text>
            <Text fontSize="xs" color={secondaryText}>
              <strong>Status:</strong> 🟢 Connected and Recording
            </Text>
            <Text fontSize="xs" color={secondaryText}>
              <strong>Quality:</strong> 1920x1080 @ 30fps
            </Text>
            <Text fontSize="xs" color={secondaryText}>
              <strong>Storage:</strong> 2.3 GB used today
            </Text>
          </VStack>
        </Box>
      </VStack>
    </Box>
  );
}

// Step 5: Packing Area Canvas
function PackingAreaCanvas({ onStepChange }: { onStepChange?: (stepName: string, data: any) => void }) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  const cardBg = useColorModeValue('gray.50', 'navy.700');

  return (
    <Box
      bg={bgColor}
      borderRadius="16px"
      p="20px"
      maxW={{ base: '95%', md: '85%', xl: '75%' }}
      w="100%"
      border="1px solid"
      borderColor={borderColor}
      boxShadow="0px 4px 12px rgba(112, 144, 176, 0.08)"
    >
      {/* Header */}
      <Flex justify="space-between" align="center" mb="20px">
        <Text fontSize="lg" fontWeight="700" color={textColor}>
          📦 Step 5: Packing Area Detection
        </Text>
      </Flex>

      <VStack spacing="16px" align="stretch">
        {/* Detection Zone Preview */}
        <Box>
          <Text fontSize="md" fontWeight="600" color={textColor} mb="12px">
            🎯 Detection Zones
          </Text>
          <Box 
            bg={cardBg} 
            p="16px" 
            borderRadius="12px"
            border="2px dashed" 
            borderColor={currentColors.brand500}
            minH="200px"
            position="relative"
            display="flex"
            alignItems="center"
            justifyContent="center"
          >
            <Box textAlign="center">
              <Text fontSize="lg" mb="8px">📹</Text>
              <Text fontSize="sm" color={secondaryText} mb="12px">
                Camera preview area
              </Text>
              <Button 
                size="sm" 
                colorScheme="brand" 
                variant="outline"
                onClick={() => onStepChange?.('packing_area', { defineZone: true })}
              >
                Define Detection Zone
              </Button>
            </Box>
            
            {/* Sample ROI Box */}
            <Box
              position="absolute"
              top="40px"
              left="40px"
              w="120px"
              h="80px"
              border="2px solid"
              borderColor={currentColors.brand500}
              bg={`${currentColors.brand500}20`}
              borderRadius="8px"
              display="flex"
              alignItems="center"
              justifyContent="center"
            >
              <Text fontSize="xs" color={currentColors.brand500} fontWeight="bold">
                Zone 1
              </Text>
            </Box>
          </Box>
        </Box>

        {/* Detection Settings */}
        <Box>
          <Text fontSize="md" fontWeight="600" color={textColor} mb="12px">
            ⚡ Detection Triggers
          </Text>
          <SimpleGrid columns={2} spacing="12px">
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize="sm" fontWeight="500" color={textColor} mb="8px">
                Motion Sensitivity:
              </Text>
              <HStack spacing="8px">
                <Text fontSize="xs" color={secondaryText}>Low</Text>
                <Box flex="1" bg={borderColor} h="4px" borderRadius="2px" position="relative">
                  <Box
                    bg={currentColors.brand500}
                    h="4px"
                    w="70%"
                    borderRadius="2px"
                  />
                </Box>
                <Text fontSize="xs" color={secondaryText}>High</Text>
              </HStack>
            </Box>
            
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize="sm" fontWeight="500" color={textColor} mb="8px">
                Object Size Filter:
              </Text>
              <Select size="sm" borderColor={borderColor} defaultValue="medium" onChange={(e) => onStepChange?.('packing_area', { objectSize: e.target.value })}>
                <option value="any">Any Size</option>
                <option value="small">Small Objects</option>
                <option value="medium">Medium Objects</option>
                <option value="large">Large Objects Only</option>
              </Select>
            </Box>
          </SimpleGrid>
        </Box>

        {/* Alert Settings */}
        <Box>
          <Text fontSize="md" fontWeight="600" color={textColor} mb="12px">
            🚨 Alert Settings
          </Text>
          <VStack spacing="8px" align="stretch">
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('packing_area', { instantNotifications: e.target.checked })}>
              <Text fontSize="sm">Instant notifications</Text>
            </Checkbox>
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('packing_area', { emailAlerts: e.target.checked })}>
              <Text fontSize="sm">Email alerts</Text>
            </Checkbox>
            <Checkbox colorScheme="brand" onChange={(e) => onStepChange?.('packing_area', { soundAlarm: e.target.checked })}>
              <Text fontSize="sm">Sound alarm</Text>
            </Checkbox>
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('packing_area', { autoRecord: e.target.checked })}>
              <Text fontSize="sm">Auto-record on detection</Text>
            </Checkbox>
          </VStack>
        </Box>

        {/* Detection Stats */}
        <Box
          bg={useColorModeValue('purple.50', 'purple.900')}
          borderRadius="12px"
          p="16px"
          border="1px solid"
          borderColor={useColorModeValue('purple.200', 'purple.700')}
        >
          <Text fontSize="sm" fontWeight="600" color={textColor} mb="8px">
            📈 Detection Statistics:
          </Text>
          <VStack align="stretch" spacing="4px">
            <Text fontSize="xs" color={secondaryText}>
              <strong>Today:</strong> 47 detections, 23 alerts sent
            </Text>
            <Text fontSize="xs" color={secondaryText}>
              <strong>This Week:</strong> 312 detections, 85% accuracy
            </Text>
            <Text fontSize="xs" color={secondaryText}>
              <strong>Active Zones:</strong> 2 configured, 1 active
            </Text>
            <Text fontSize="xs" color={secondaryText}>
              <strong>Last Detection:</strong> 2 minutes ago
            </Text>
          </VStack>
        </Box>
      </VStack>
    </Box>
  );
}

// Step 6: Timing Canvas
function TimingCanvas({ onStepChange }: { onStepChange?: (stepName: string, data: any) => void }) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  const cardBg = useColorModeValue('gray.50', 'navy.700');

  return (
    <Box
      bg={bgColor}
      borderRadius="16px"
      p="20px"
      maxW={{ base: '95%', md: '85%', xl: '75%' }}
      w="100%"
      border="1px solid"
      borderColor={borderColor}
      boxShadow="0px 4px 12px rgba(112, 144, 176, 0.08)"
    >
      {/* Header */}
      <Flex justify="space-between" align="center" mb="20px">
        <Text fontSize="lg" fontWeight="700" color={textColor}>
          ⏱️ Step 6: Timing & Performance
        </Text>
      </Flex>

      <VStack spacing="16px" align="stretch">
        {/* Processing Speed Settings */}
        <Box>
          <Text fontSize="md" fontWeight="600" color={textColor} mb="12px">
            🚀 Processing Speed
          </Text>
          <SimpleGrid columns={3} spacing="12px">
            <Box 
              bg={cardBg} 
              p="16px" 
              borderRadius="12px" 
              border="1px solid" 
              borderColor={borderColor}
              textAlign="center"
              cursor="pointer"
              onClick={() => onStepChange?.('timing', { processingSpeed: 'slow' })}
            >
              <Text fontSize="lg" mb="8px">🐌</Text>
              <Text fontSize="sm" fontWeight="600" color={textColor}>Slow</Text>
              <Text fontSize="xs" color={secondaryText}>High Accuracy</Text>
              <Text fontSize="xs" color={secondaryText}>3-5 seconds</Text>
            </Box>
            
            <Box 
              bg={cardBg} 
              p="16px" 
              borderRadius="12px" 
              border="2px solid" 
              borderColor={currentColors.brand500}
              textAlign="center"
              cursor="pointer"
              onClick={() => onStepChange?.('timing', { processingSpeed: 'medium' })}
            >
              <Text fontSize="lg" mb="8px">⚡</Text>
              <Text fontSize="sm" fontWeight="600" color={textColor}>Medium</Text>
              <Text fontSize="xs" color={secondaryText}>Balanced</Text>
              <Text fontSize="xs" color={secondaryText}>1-2 seconds</Text>
            </Box>
            
            <Box 
              bg={cardBg} 
              p="16px" 
              borderRadius="12px" 
              border="1px solid" 
              borderColor={borderColor}
              textAlign="center"
              cursor="pointer"
              onClick={() => onStepChange?.('timing', { processingSpeed: 'fast' })}
            >
              <Text fontSize="lg" mb="8px">🏃</Text>
              <Text fontSize="sm" fontWeight="600" color={textColor}>Fast</Text>
              <Text fontSize="xs" color={secondaryText}>Real-time</Text>
              <Text fontSize="xs" color={secondaryText}>{'< 1 second'}</Text>
            </Box>
          </SimpleGrid>
        </Box>

        {/* Buffer Settings */}
        <Box>
          <Text fontSize="md" fontWeight="600" color={textColor} mb="12px">
            📹 Buffer Settings
          </Text>
          <SimpleGrid columns={2} spacing="12px">
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize="sm" fontWeight="500" color={textColor} mb="8px">
                Pre-event Buffer:
              </Text>
              <HStack spacing="8px">
                <Input
                  placeholder="5"
                  size="sm"
                  w="60px"
                  borderColor={borderColor}
                  _focus={{ borderColor: currentColors.brand500 }}
                  onChange={(e) => onStepChange?.('timing', { preEventBuffer: e.target.value })}
                />
                <Text fontSize="sm" color={secondaryText}>seconds before detection</Text>
              </HStack>
            </Box>
            
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize="sm" fontWeight="500" color={textColor} mb="8px">
                Post-event Buffer:
              </Text>
              <HStack spacing="8px">
                <Input
                  placeholder="10"
                  size="sm"
                  w="60px"
                  borderColor={borderColor}
                  _focus={{ borderColor: currentColors.brand500 }}
                  onChange={(e) => onStepChange?.('timing', { postEventBuffer: e.target.value })}
                />
                <Text fontSize="sm" color={secondaryText}>seconds after detection</Text>
              </HStack>
            </Box>
          </SimpleGrid>
        </Box>

        {/* Performance Optimization */}
        <Box>
          <Text fontSize="md" fontWeight="600" color={textColor} mb="12px">
            ⚙️ Performance Optimization
          </Text>
          <VStack spacing="8px" align="stretch">
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('timing', { gpuAcceleration: e.target.checked })}>
              <Text fontSize="sm">GPU acceleration (if available)</Text>
            </Checkbox>
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('timing', { multiThreaded: e.target.checked })}>
              <Text fontSize="sm">Multi-threaded processing</Text>
            </Checkbox>
            <Checkbox colorScheme="brand" onChange={(e) => onStepChange?.('timing', { lowPowerMode: e.target.checked })}>
              <Text fontSize="sm">Low-power mode (battery saving)</Text>
            </Checkbox>
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('timing', { adaptiveQuality: e.target.checked })}>
              <Text fontSize="sm">Adaptive quality based on load</Text>
            </Checkbox>
          </VStack>
        </Box>

        {/* Performance Stats */}
        <Box
          bg={useColorModeValue('orange.50', 'orange.900')}
          borderRadius="12px"
          p="16px"
          border="1px solid"
          borderColor={useColorModeValue('orange.200', 'orange.700')}
        >
          <Text fontSize="sm" fontWeight="600" color={textColor} mb="8px">
            📊 Current Performance:
          </Text>
          <VStack align="stretch" spacing="4px">
            <Text fontSize="xs" color={secondaryText}>
              <strong>Processing Time:</strong> 1.2s average (Medium mode)
            </Text>
            <Text fontSize="xs" color={secondaryText}>
              <strong>CPU Usage:</strong> 45% average, 78% peak
            </Text>
            <Text fontSize="xs" color={secondaryText}>
              <strong>Memory Usage:</strong> 2.1 GB / 8 GB (26%)
            </Text>
            <Text fontSize="xs" color={secondaryText}>
              <strong>Queue Status:</strong> 3 videos pending processing
            </Text>
          </VStack>
        </Box>
      </VStack>
    </Box>
  );
}