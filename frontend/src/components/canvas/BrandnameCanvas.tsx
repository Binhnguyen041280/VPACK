'use client';

import {
  Box,
  Text,
  VStack,
  HStack,
  Divider,
  useColorModeValue,
} from '@chakra-ui/react';
import { useColorTheme } from '@/contexts/ColorThemeContext';
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

// Brandname Canvas Component (Step 1) - Pure Display
function BrandnameCanvas({ adaptiveConfig, brandName = 'Alan_go', isLoading = false }: CanvasComponentProps) {
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
      maxW="450px"
      mx="auto"
      css={{
        '@media (max-width: 450px)': {
          maxW: '100%',
          px: '12px',
        }
      }}
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
            p="16px"
            borderRadius="12px"
            textAlign="center"
          >
            <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor} mb="12px">
              Company/Brand Name
            </Text>
            {adaptiveConfig.showOptional && (
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText} mb="12px">
                Type your company name in the chat below and click Submit
              </Text>
            )}
            {adaptiveConfig.mode !== 'compact' && (
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText} fontStyle="italic">
                Example: "TechCorp Manufacturing"
              </Text>
            )}
          </Box>
        </Box>

        {adaptiveConfig.showOptional && <Divider />}

        {/* Current Brand Name Display - Essential Content */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            📋 Current Configuration
          </Text>
          <Box
            bg={cardBg}
            p="16px"
            borderRadius="12px"
            textAlign="center"
          >
            <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor} mb="4px">
              Current Brand Name:
            </Text>
            {isLoading ? (
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
                Loading...
              </Text>
            ) : (
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="700" color={currentColors.brand500} mb="8px">
                "{brandName}"
              </Text>
            )}
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              💡 Type new company name in chat and click Submit, or click Continue to proceed
            </Text>
          </Box>
        </Box>
      </VStack>
    </Box>
  );
}

export default BrandnameCanvas;