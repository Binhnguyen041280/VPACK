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
  // Step 5 props
  timingStorageData?: {
    min_packing_time: number;
    max_packing_time: number;
    video_buffer: number;
    storage_duration: number;
    frame_rate: number;
    frame_interval: number;
    output_path: string;
  };
  timingStorageLoading?: boolean;
}

// Step 5: Timing & File Storage Canvas 
function TimingCanvas({ adaptiveConfig, onStepChange, timingStorageData, timingStorageLoading }: CanvasComponentProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  const cardBg = useColorModeValue('gray.50', 'navy.700');
  
  // Use controlled state from props with fallback defaults
  const currentData = timingStorageData || {
    min_packing_time: 10,
    max_packing_time: 120,
    video_buffer: 2,
    storage_duration: 30,
    frame_rate: 30,
    frame_interval: 5,
    output_path: "/default/output"
  };

  // Change handlers to notify parent component
  const handleFieldChange = (field: string, value: any) => {
    if (onStepChange) {
      onStepChange('timing', { [field]: value });
    }
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
              value={currentData.output_path}
              placeholder="Copy and paste folder path here..."
              size="sm"
              borderColor={borderColor}
              _focus={{ borderColor: currentColors.brand500 }}
              bg={bgColor}
              mb="12px"
              onChange={(e) => handleFieldChange('output_path', e.target.value)}
              onFocus={(e) => {
                e.target.select(); // Select all text for easy replacement
              }}
            />
            <Text 
              fontSize={adaptiveConfig.fontSize.small} 
              color={secondaryText}
              textAlign="right"
              title={currentData.output_path || 'No path specified'}
            >
              📋 Output folder: {currentData.output_path || 'No path specified'}
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
                  value={currentData.storage_duration}
                placeholder="30"
                size="sm"
                w="60px"
                borderColor={borderColor}
                _focus={{ borderColor: currentColors.brand500 }}
                fontFamily="var(--chatgpt-font-family)"
                onChange={(e) => handleFieldChange('storage_duration', parseInt(e.target.value) || 30)}
              />
              <Text fontSize={adaptiveConfig.fontSize.body} color={secondaryText}>days</Text>
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
                value={currentData.video_buffer}
                placeholder="2"
                size="sm"
                w="60px"
                borderColor={borderColor}
                _focus={{ borderColor: currentColors.brand500 }}
                onChange={(e) => handleFieldChange('video_buffer', parseInt(e.target.value) || 2)}
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
                      value={currentData.min_packing_time}
                  placeholder="10"
                  size="sm"
                  w="60px"
                  borderColor={borderColor}
                  _focus={{ borderColor: currentColors.brand500 }}
                  onChange={(e) => handleFieldChange('min_packing_time', parseInt(e.target.value) || 10)}
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
                      value={currentData.max_packing_time}
                  placeholder="120"
                  size="sm"
                  w="60px"
                  borderColor={borderColor}
                  _focus={{ borderColor: currentColors.brand500 }}
                  onChange={(e) => handleFieldChange('max_packing_time', parseInt(e.target.value) || 120)}
                />
                <Text fontSize={adaptiveConfig.fontSize.body} color={secondaryText}>seconds</Text>
              </HStack>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText} fontStyle="italic">
                🐌 Slowest packing acceptable
              </Text>
            </Box>
          </SimpleGrid>
        </Box>

        {/* Performance Settings */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            ⚡ Performance Settings
          </Text>
          <SimpleGrid columns={2} spacing="12px">
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} mb="8px">
                Frame Rate:
              </Text>
              <HStack spacing="8px" mb="8px">
                <Input
                      value={currentData.frame_rate}
                  placeholder="30"
                  size="sm"
                  w="60px"
                  borderColor={borderColor}
                  _focus={{ borderColor: currentColors.brand500 }}
                  onChange={(e) => handleFieldChange('frame_rate', parseInt(e.target.value) || 30)}
                />
                <Text fontSize={adaptiveConfig.fontSize.body} color={secondaryText}>fps</Text>
              </HStack>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText} fontStyle="italic">
                📹 Processing frame rate
              </Text>
            </Box>
            
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} mb="8px">
                Frame Interval:
              </Text>
              <HStack spacing="8px" mb="8px">
                <Input
                      value={currentData.frame_interval}
                  placeholder="5"
                  size="sm"
                  w="60px"
                  borderColor={borderColor}
                  _focus={{ borderColor: currentColors.brand500 }}
                  onChange={(e) => handleFieldChange('frame_interval', parseInt(e.target.value) || 5)}
                />
                <Text fontSize={adaptiveConfig.fontSize.body} color={secondaryText}>frames</Text>
              </HStack>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText} fontStyle="italic">
                🎯 Skip frames for performance
              </Text>
            </Box>
          </SimpleGrid>
        </Box>

        {/* Configuration Summary */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            📋 Current Configuration
          </Text>
          <Box bg={cardBg} p="16px" borderRadius="12px" border="1px solid" borderColor={borderColor}>
            <VStack align="stretch" spacing="4px">
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
                <strong>Output Path:</strong> {currentData.output_path || 'Not specified'}
              </Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
                <strong>File Retention:</strong> {currentData.storage_duration} days auto-delete
              </Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
                <strong>Buffer Settings:</strong> {currentData.video_buffer} seconds before/after events
              </Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
                <strong>Packing Time:</strong> {currentData.min_packing_time}s - {currentData.max_packing_time}s limits
              </Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
                <strong>Performance:</strong> {currentData.frame_rate} fps, skip {currentData.frame_interval} frames
              </Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText} fontStyle="italic" mt="8px">
                💡 Adjust values above to optimize performance, or click Continue to proceed
              </Text>
            </VStack>
          </Box>
        </Box>

      </VStack>
    </Box>
  );
}

export default TimingCanvas;