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
import { useState, useEffect, useRef } from 'react';

interface CanvasMessageProps {
  configStep: 'brandname' | 'location_time' | 'file_save' | 'video_source' | 'packing_area' | 'timing';
  onStepChange?: (stepName: string, data: any) => void;
}

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

export default function CanvasMessage({ configStep, onStepChange }: CanvasMessageProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  
  // Height detection and adaptive behavior
  const containerRef = useRef<HTMLDivElement>(null);
  const [availableHeight, setAvailableHeight] = useState(0);
  const [adaptiveConfig, setAdaptiveConfig] = useState<AdaptiveConfig>({
    mode: 'normal',
    fontSize: { header: 'md', title: 'xs', body: 'xs', small: 'xs' },
    spacing: { section: '16px', item: '12px', padding: '20px' },
    showOptional: true
  });

  // Detect container height and adjust config
  useEffect(() => {
    const updateHeight = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        const height = rect.height;
        setAvailableHeight(height);
        
        // Determine adaptive config based on height
        let newConfig: AdaptiveConfig;
        
        if (height < 400) {
          // Compact mode - very small height - Match Navigator compact
          newConfig = {
            mode: 'compact',
            fontSize: { header: 'sm', title: 'xs', body: 'xs', small: 'xs' },
            spacing: { section: '8px', item: '6px', padding: '12px' },
            showOptional: false
          };
        } else if (height < 600) {
          // Normal mode - medium height - Match Navigator normal
          newConfig = {
            mode: 'normal',
            fontSize: { header: 'md', title: 'xs', body: 'xs', small: 'xs' },
            spacing: { section: '12px', item: '8px', padding: '16px' },
            showOptional: true
          };
        } else {
          // Spacious mode - large height - Slightly larger than Navigator
          newConfig = {
            mode: 'spacious',
            fontSize: { header: 'md', title: 'sm', body: 'xs', small: 'xs' },
            spacing: { section: '20px', item: '16px', padding: '24px' },
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
  
  // Render canvas based on current step with adaptive config
  const renderCanvas = () => {
    const commonProps = { 
      onStepChange, 
      adaptiveConfig, 
      availableHeight 
    };
    
    switch (configStep) {
      case 'brandname':
        return <BrandnameCanvas {...commonProps} />;
      case 'location_time':
        return <LocationTimeCanvas {...commonProps} />;
      case 'file_save':
        return <FileSaveCanvas {...commonProps} />;
      case 'video_source':
        return <VideoSourceCanvas {...commonProps} />;
      case 'packing_area':
        return <PackingAreaCanvas {...commonProps} />;
      case 'timing':
        return <TimingCanvas {...commonProps} />;
      default:
        return <BrandnameCanvas {...commonProps} />;
    }
  };

  // Determine if current step should have scroll (all except step 1)
  const shouldScroll = configStep !== 'brandname';

  return (
    <Box 
      ref={containerRef}
      h="100%" 
      w="100%"
      overflow={shouldScroll ? "auto" : "hidden"}
      css={shouldScroll ? {
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
        // Ensure content can overflow properly
        overflowY: 'auto',
        overflowX: 'hidden',
      } : {
        overflowY: 'hidden',
        overflowX: 'hidden',
      }}
    >
      {/* Dynamic Canvas Content - No Bot Avatar */}
      {renderCanvas()}
    </Box>
  );
}

// Enhanced Canvas Component Props
interface CanvasComponentProps {
  onStepChange?: (stepName: string, data: any) => void;
  adaptiveConfig: AdaptiveConfig;
  availableHeight: number;
}

// Brandname Canvas Component (Step 1)
function BrandnameCanvas({ adaptiveConfig }: CanvasComponentProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const cardBg = useColorModeValue('gray.50', 'navy.700');

  return (
    <Box
      w="100%"
      minH="fit-content"
    >
      {/* Header - Priority Content */}
      <Text fontSize={adaptiveConfig.fontSize.header} fontWeight="700" color={textColor} mb={adaptiveConfig.spacing.section}>
        🏢 Step 1: Brandname Setup
      </Text>

      <VStack spacing={adaptiveConfig.spacing.item} align="stretch">
        {/* Company Information Section - Priority Content */}
        <Box>
          {adaptiveConfig.mode !== 'compact' && (
            <HStack mb={adaptiveConfig.spacing.item}>
              <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor}>
                🏢 Company Information
              </Text>
            </HStack>
          )}
          
          <Box
            bg={cardBg}
            p={adaptiveConfig.spacing.item}
            borderRadius="12px"
            textAlign="center"
          >
            <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor} mb={adaptiveConfig.spacing.item}>
              Company/Brand Name
            </Text>
            {adaptiveConfig.showOptional && (
              <Text fontSize={adaptiveConfig.fontSize.small} color="gray.500" mb={adaptiveConfig.spacing.item}>
                Type your company name in the chat below and click Submit
              </Text>
            )}
            {adaptiveConfig.mode !== 'compact' && (
              <Text fontSize={adaptiveConfig.fontSize.small} color="gray.400" fontStyle="italic">
                Example: "TechCorp Manufacturing"
              </Text>
            )}
          </Box>
        </Box>

        {adaptiveConfig.showOptional && <Divider />}

        {/* Status Summary - Essential Content */}
        <Box
          bg={cardBg}
          p={adaptiveConfig.spacing.item}
          borderRadius="12px"
          textAlign="center"
        >
          <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor} mb="4px">
            ⏳ Waiting for Company Name
          </Text>
          {adaptiveConfig.showOptional && (
            <Text fontSize={adaptiveConfig.fontSize.small} color="gray.500">
              Please enter your company name in the chat and click Submit
            </Text>
          )}
        </Box>
      </VStack>
    </Box>
  );
}

// Step 3: File Save Canvas
function FileSaveCanvas({ adaptiveConfig, onStepChange }: CanvasComponentProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  const cardBg = useColorModeValue('gray.50', 'navy.700');

  return (
    <Box
      w="100%"
      minH="fit-content"
    >
      {/* Header */}
      <Text fontSize={adaptiveConfig.fontSize.header} fontWeight="700" color={textColor} mb={adaptiveConfig.spacing.section}>
        💾 Step 3: File Storage Settings
      </Text>

      <VStack spacing={adaptiveConfig.spacing.item} align="stretch">
        {/* Storage Path Section */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
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
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              📋 Current: /Users/vtrack/Documents/Videos
            </Text>
          </Box>
        </Box>

        {/* Retention Policy */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            🗓️ File Retention
          </Text>
          <SimpleGrid columns={2} spacing="12px">
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} mb="8px">
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
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} mb="8px">
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
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            📋 File Organization
          </Text>
          <VStack spacing="8px" align="stretch">
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('file_save', { organizeByDate: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Organize by date (YYYY/MM/DD)</Text>
            </Checkbox>
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('file_save', { separateFolders: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Separate folders for each camera</Text>
            </Checkbox>
            <Checkbox colorScheme="brand" onChange={(e) => onStepChange?.('file_save', { compressOld: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Compress videos older than 7 days</Text>
            </Checkbox>
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('file_save', { generateThumbnails: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Generate thumbnails</Text>
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
          <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor} mb="8px">
            💽 Current Storage Status:
          </Text>
          <VStack align="stretch" spacing="4px">
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>Used:</strong> 45.2 GB / 100 GB (45%)
            </Text>
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>Files:</strong> 1,247 videos, 3,891 thumbnails
            </Text>
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>Oldest:</strong> 28 days ago
            </Text>
          </VStack>
        </Box>
      </VStack>
    </Box>
  );
}

// Step 4: Video Source Canvas
function VideoSourceCanvas({ adaptiveConfig, onStepChange }: CanvasComponentProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  const cardBg = useColorModeValue('gray.50', 'navy.700');

  return (
    <Box
      w="100%"
      minH="fit-content"
    >
      {/* Header */}
      <Text fontSize={adaptiveConfig.fontSize.header} fontWeight="700" color={textColor} mb={adaptiveConfig.spacing.section}>
        📹 Step 4: Video Source Configuration
      </Text>

      <VStack spacing={adaptiveConfig.spacing.item} align="stretch">
        {/* Source Type Selection */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
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
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor}>Local Camera</Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>USB/Built-in</Text>
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
              <Text fontSize={adaptiveConfig.fontSize.header} mb="8px">🌐</Text>
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor}>IP Camera</Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>ONVIF/RTSP</Text>
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
              <Text fontSize={adaptiveConfig.fontSize.header} mb="8px">☁️</Text>
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor}>Cloud Storage</Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>Google Drive</Text>
            </Box>
          </SimpleGrid>
        </Box>

        {/* Camera Settings */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            ⚙️ Camera Settings
          </Text>
          <SimpleGrid columns={2} spacing="12px">
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} mb="8px">
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
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} mb="8px">
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
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            🔴 Recording Options
          </Text>
          <VStack spacing="8px" align="stretch">
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('video_source', { continuousRecording: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Continuous recording</Text>
            </Checkbox>
            <Checkbox colorScheme="brand" onChange={(e) => onStepChange?.('video_source', { motionTriggered: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Motion-triggered recording</Text>
            </Checkbox>
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('video_source', { audioRecording: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Audio recording</Text>
            </Checkbox>
            <Checkbox colorScheme="brand" onChange={(e) => onStepChange?.('video_source', { nightVision: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Night vision mode</Text>
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
          <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor} mb="8px">
            📊 Camera Status:
          </Text>
          <VStack align="stretch" spacing="4px">
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>Device:</strong> USB Camera (HD WebCam C270)
            </Text>
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>Status:</strong> 🟢 Connected and Recording
            </Text>
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>Quality:</strong> 1920x1080 @ 30fps
            </Text>
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>Storage:</strong> 2.3 GB used today
            </Text>
          </VStack>
        </Box>
      </VStack>
    </Box>
  );
}

// Step 5: Packing Area Canvas
function PackingAreaCanvas({ adaptiveConfig, onStepChange }: CanvasComponentProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  const cardBg = useColorModeValue('gray.50', 'navy.700');

  return (
    <Box
      w="100%"
      minH="fit-content"
    >
      {/* Header */}
      <Text fontSize={adaptiveConfig.fontSize.header} fontWeight="700" color={textColor} mb={adaptiveConfig.spacing.section}>
        📦 Step 5: Packing Area Detection
      </Text>

      <VStack spacing={adaptiveConfig.spacing.item} align="stretch">
        {/* Detection Zone Preview */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
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
              <Text fontSize={adaptiveConfig.fontSize.header} mb="8px">📹</Text>
              <Text fontSize={adaptiveConfig.fontSize.body} color={secondaryText} mb="12px">
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
              <Text fontSize={adaptiveConfig.fontSize.small} color={currentColors.brand500} fontWeight="bold">
                Zone 1
              </Text>
            </Box>
          </Box>
        </Box>

        {/* Detection Settings */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            ⚡ Detection Triggers
          </Text>
          <SimpleGrid columns={2} spacing="12px">
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} mb="8px">
                Motion Sensitivity:
              </Text>
              <HStack spacing="8px">
                <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>Low</Text>
                <Box flex="1" bg={borderColor} h="4px" borderRadius="2px" position="relative">
                  <Box
                    bg={currentColors.brand500}
                    h="4px"
                    w="70%"
                    borderRadius="2px"
                  />
                </Box>
                <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>High</Text>
              </HStack>
            </Box>
            
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} mb="8px">
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
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            🚨 Alert Settings
          </Text>
          <VStack spacing="8px" align="stretch">
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('packing_area', { instantNotifications: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Instant notifications</Text>
            </Checkbox>
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('packing_area', { emailAlerts: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Email alerts</Text>
            </Checkbox>
            <Checkbox colorScheme="brand" onChange={(e) => onStepChange?.('packing_area', { soundAlarm: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Sound alarm</Text>
            </Checkbox>
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('packing_area', { autoRecord: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Auto-record on detection</Text>
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
    </Box>
  );
}

// Step 6: Timing Canvas
function TimingCanvas({ adaptiveConfig, onStepChange }: CanvasComponentProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  const cardBg = useColorModeValue('gray.50', 'navy.700');

  return (
    <Box
      w="100%"
      minH="fit-content"
    >
      {/* Header */}
      <Text fontSize={adaptiveConfig.fontSize.header} fontWeight="700" color={textColor} mb={adaptiveConfig.spacing.section}>
        ⏱️ Step 6: Timing & Performance
      </Text>

      <VStack spacing={adaptiveConfig.spacing.item} align="stretch">
        {/* Processing Speed Settings */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
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
              <Text fontSize={adaptiveConfig.fontSize.header} mb="8px">🐌</Text>
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor}>Slow</Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>High Accuracy</Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>3-5 seconds</Text>
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
              <Text fontSize={adaptiveConfig.fontSize.header} mb="8px">⚡</Text>
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor}>Medium</Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>Balanced</Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>1-2 seconds</Text>
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
              <Text fontSize={adaptiveConfig.fontSize.header} mb="8px">🏃</Text>
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor}>Fast</Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>Real-time</Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>{'< 1 second'}</Text>
            </Box>
          </SimpleGrid>
        </Box>

        {/* Buffer Settings */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            📹 Buffer Settings
          </Text>
          <SimpleGrid columns={2} spacing="12px">
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} mb="8px">
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
                <Text fontSize={adaptiveConfig.fontSize.body} color={secondaryText}>seconds before detection</Text>
              </HStack>
            </Box>
            
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} mb="8px">
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
                <Text fontSize={adaptiveConfig.fontSize.body} color={secondaryText}>seconds after detection</Text>
              </HStack>
            </Box>
          </SimpleGrid>
        </Box>

        {/* Performance Optimization */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            ⚙️ Performance Optimization
          </Text>
          <VStack spacing="8px" align="stretch">
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('timing', { gpuAcceleration: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>GPU acceleration (if available)</Text>
            </Checkbox>
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('timing', { multiThreaded: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Multi-threaded processing</Text>
            </Checkbox>
            <Checkbox colorScheme="brand" onChange={(e) => onStepChange?.('timing', { lowPowerMode: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Low-power mode (battery saving)</Text>
            </Checkbox>
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('timing', { adaptiveQuality: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Adaptive quality based on load</Text>
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
          <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor} mb="8px">
            📊 Current Performance:
          </Text>
          <VStack align="stretch" spacing="4px">
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>Processing Time:</strong> 1.2s average (Medium mode)
            </Text>
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>CPU Usage:</strong> 45% average, 78% peak
            </Text>
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>Memory Usage:</strong> 2.1 GB / 8 GB (26%)
            </Text>
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>Queue Status:</strong> 3 videos pending processing
            </Text>
          </VStack>
        </Box>
      </VStack>
    </Box>
  );
}