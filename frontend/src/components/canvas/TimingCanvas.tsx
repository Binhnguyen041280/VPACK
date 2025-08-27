'use client';

import {
  Box,
  Text,
  VStack,
  HStack,
  Input,
  Select,
  SimpleGrid,
  useColorModeValue,
} from '@chakra-ui/react';
import { useColorTheme } from '@/contexts/ColorThemeContext';
import { useState } from 'react';
import React from 'react';

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

// Step 5: Timing & File Storage Canvas 
function TimingCanvas({ adaptiveConfig, onStepChange }: CanvasComponentProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  const cardBg = useColorModeValue('gray.50', 'navy.700');
  
  // Local state for storage path - Default based on OS
  const getDefaultPath = () => {
    const platform = navigator.platform.toLowerCase();
    if (platform.includes('win')) {
      return 'C:\\Users\\%USERNAME%\\Videos\\VTrack';
    } else if (platform.includes('mac')) {
      return '/Users/%USER%/Movies/VTrack';
    } else {
      return '/home/%USER%/Videos/VTrack';
    }
  };
  
  const [storagePath, setStoragePath] = useState(getDefaultPath());

  return (
    <Box
      w="100%"
      minH="fit-content"
    >
      {/* Header */}
      <Text fontSize={adaptiveConfig.fontSize.header} fontWeight="700" color={textColor} mb={adaptiveConfig.spacing.section}>
        ⏱️ Step 5: Timing & File Storage
      </Text>

      <VStack spacing={adaptiveConfig.spacing.item} align="stretch">
        {/* Storage Path Section */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            💾 Video Output Directory
          </Text>
          <Box bg={cardBg} p="16px" borderRadius="12px">
            <VStack spacing="8px" align="stretch" mb="12px">
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
                📝 Choose where to save processed videos and detection results
              </Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color="orange.500" fontStyle="italic">
                💡 Tip: Open folder in explorer, copy path from address bar and paste here
              </Text>
            </VStack>
            <Input
              value={storagePath}
              placeholder="Copy and paste folder path here..."
              size="sm"
              borderColor={borderColor}
              _focus={{ borderColor: currentColors.brand500 }}
              bg={bgColor}
              mb="12px"
              onFocus={(e) => {
                // Clear input when user clicks to enter new path
                if (storagePath === getDefaultPath()) {
                  setStoragePath('');
                }
                e.target.select(); // Select all text for easy replacement
              }}
              onChange={(e) => {
                setStoragePath(e.target.value);
                onStepChange?.('timing', { storagePath: e.target.value });
              }}
            />
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              📋 Output folder: {storagePath}
            </Text>
          </Box>
        </Box>

        {/* Retention Policy */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            🗓️ File Retention
          </Text>
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
                onChange={(e) => onStepChange?.('timing', { retention: e.target.value })}
              />
              <Select size="sm" borderColor={borderColor} onChange={(e) => onStepChange?.('timing', { retentionUnit: e.target.value })}>
                <option value="days">Days</option>
                <option value="weeks">Weeks</option>
                <option value="months">Months</option>
              </Select>
            </HStack>
          </Box>
        </Box>

        {/* Buffer Settings */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            📹 Buffer Settings
          </Text>
          <Box bg={cardBg} p="16px" borderRadius="12px">
            <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} mb="8px">
              Event Buffer Duration:
            </Text>
            <HStack spacing="8px" mb="8px">
              <Input
                placeholder="5"
                size="sm"
                w="60px"
                borderColor={borderColor}
                _focus={{ borderColor: currentColors.brand500 }}
                onChange={(e) => onStepChange?.('timing', { eventBuffer: e.target.value })}
              />
              <Text fontSize={adaptiveConfig.fontSize.body} color={secondaryText}>seconds before and after detection</Text>
            </HStack>
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText} fontStyle="italic">
              💡 Same buffer time applied for both pre and post event recording
            </Text>
          </Box>
        </Box>

        {/* Packing Time Settings */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            ⏰ Packing Time Limits
          </Text>
          <SimpleGrid columns={2} spacing="12px">
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} mb="8px">
                Min Packing Time:
              </Text>
              <HStack spacing="8px" mb="8px">
                <Input
                  placeholder="30"
                  size="sm"
                  w="60px"
                  borderColor={borderColor}
                  _focus={{ borderColor: currentColors.brand500 }}
                  onChange={(e) => onStepChange?.('timing', { minPackingTime: e.target.value })}
                />
                <Text fontSize={adaptiveConfig.fontSize.body} color={secondaryText}>seconds</Text>
              </HStack>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText} fontStyle="italic">
                🚀 Fastest packing expected
              </Text>
            </Box>
            
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} mb="8px">
                Max Packing Time:
              </Text>
              <HStack spacing="8px" mb="8px">
                <Input
                  placeholder="300"
                  size="sm"
                  w="60px"
                  borderColor={borderColor}
                  _focus={{ borderColor: currentColors.brand500 }}
                  onChange={(e) => onStepChange?.('timing', { maxPackingTime: e.target.value })}
                />
                <Text fontSize={adaptiveConfig.fontSize.body} color={secondaryText}>seconds</Text>
              </HStack>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText} fontStyle="italic">
                🐌 Slowest packing acceptable
              </Text>
            </Box>
          </SimpleGrid>
        </Box>

      </VStack>
    </Box>
  );
}

export default TimingCanvas;