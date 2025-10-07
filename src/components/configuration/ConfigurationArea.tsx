'use client';

import {
  Box,
  Text,
  useColorModeValue
} from '@chakra-ui/react';
import { useColorTheme } from '@/contexts/ColorThemeContext';

// Import existing canvas components
import CanvasMessage from '@/components/canvas/CanvasMessage';

interface ConfigurationAreaProps {
  currentStep: string;
  title?: string;
  onStepChange?: (stepName: string, data: any) => void;
}

export default function ConfigurationArea({ 
  currentStep, 
  title,
  onStepChange 
}: ConfigurationAreaProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');

  const getStepTitle = () => {
    switch (currentStep) {
      case 'brandname':
      case 'company':
        return '🏢 Company & Branding Setup';
      case 'location_time':
        return '📍 Location & Time Configuration';
      case 'file_save':
        return '💾 File Storage Settings';
      case 'video_source':
        return '📹 Video Source Configuration';
      case 'packing_area':
        return '📦 Packing Area Detection';
      case 'timing':
        return '⏱️ Timing & Performance';
      default:
        return '⚙️ Configuration';
    }
  };

  return (
    <Box
      bg={bgColor}
      borderRadius="20px"
      border="1px solid"
      borderColor={borderColor}
      p="24px"
      h="fit-content"
      position="relative"
    >
      {/* Configuration Content - Canvas only, no flex space */}
      <Box>
        {/* Use existing CanvasMessage but without the bot avatar */}
        <Box
          sx={{
            '& > div': {
              marginBottom: 0
            },
            '& > div > div:first-of-type': {
              display: 'none' // Hide bot avatar
            }
          }}
        >
          <CanvasMessage configStep={currentStep as any} onStepChange={onStepChange} />
        </Box>
      </Box>
    </Box>
  );
}