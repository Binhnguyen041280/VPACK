'use client';

import {
  Box,
  VStack,
  Text,
  Flex,
  Icon,
  useColorModeValue,
  Badge,
  SimpleGrid
} from '@chakra-ui/react';
import { 
  MdBusiness,
  MdLocationOn, 
  MdSave,
  MdVideoLibrary,
  MdCropFree,
  MdTimer
} from 'react-icons/md';
import { useColorTheme } from '@/contexts/ColorThemeContext';

interface Step {
  id: number;
  key: string;
  title: string;
  description: string;
  icon: any;
}

const steps: Step[] = [
  {
    id: 1,
    key: 'brandname',
    title: 'Brandname',
    description: 'Company info & branding',
    icon: MdBusiness
  },
  {
    id: 2,
    key: 'location_time',
    title: 'Location & Time',
    description: 'Address & timezone setup',
    icon: MdLocationOn
  },
  {
    id: 3,
    key: 'file_save',
    title: 'File Save',
    description: 'Storage path & retention',
    icon: MdSave
  },
  {
    id: 4,
    key: 'video_source',
    title: 'Video Source',
    description: 'Camera & quality settings',
    icon: MdVideoLibrary
  },
  {
    id: 5,
    key: 'packing_area',
    title: 'Packing Area',
    description: 'Detection zones & triggers',
    icon: MdCropFree
  },
  {
    id: 6,
    key: 'timing',
    title: 'Timing',
    description: 'Speed & buffer settings',
    icon: MdTimer
  }
];

interface StepNavigatorProps {
  currentStep: string;
  completedSteps: { [key: string]: boolean };
  highestStepReached: number;
  onStepClick?: (stepKey: string) => void;
}

export default function StepNavigator({ 
  currentStep, 
  completedSteps,
  highestStepReached,
  onStepClick 
}: StepNavigatorProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');

  const getStepStatus = (step: Step) => {
    // Current step always has priority over completed status
    if (step.key === currentStep) return 'current';
    if (completedSteps[step.key]) return 'completed';
    return 'pending';
  };

  const getStepColors = (status: string) => {
    switch (status) {
      case 'completed':
        return {
          bg: `${currentColors.brand500}20`,
          borderColor: currentColors.brand500,
          iconColor: currentColors.brand500,
          textColor: textColor
        };
      case 'current':
        return {
          bg: `${currentColors.brand500}10`,
          borderColor: currentColors.brand500,
          iconColor: currentColors.brand500,
          textColor: textColor
        };
      default:
        return {
          bg: 'transparent',
          borderColor: borderColor,
          iconColor: secondaryText,
          textColor: secondaryText
        };
    }
  };

  return (
    <Box
      h="100%"
      display="flex"
      flexDirection="column"
    >
      {/* Header with Progress */}
      <Flex
        align="center"
        mb="12px"
        flexShrink={0}
        gap="8px"
      >
        <Text
          fontSize="md"
          fontWeight="700"
          color={textColor}
        >
          🚀 Configuration Steps
        </Text>
        <Box
          px="6px"
          py="2px"
          bg={useColorModeValue('gray.50', 'whiteAlpha.100')}
          borderRadius="4px"
        >
          <Text fontSize="xs" color={secondaryText} fontWeight="500">
            {highestStepReached}/6
          </Text>
        </Box>
      </Flex>

      {/* Steps List - 2 Columns */}
      <SimpleGrid columns={2} spacing="8px" flex="1">
        {steps.map((step) => {
          const status = getStepStatus(step);
          const colors = getStepColors(status);
          const isClickable = onStepClick && (status === 'completed' || status === 'current');

          return (
            <Flex
              key={step.id}
              align="center"
              p="8px"
              borderRadius="8px"
              border="1px solid"
              borderColor={colors.borderColor}
              bg={colors.bg}
              cursor={isClickable ? 'pointer' : 'default'}
              transition="all 0.2s ease"
              _hover={isClickable ? {
                transform: 'translateY(-1px)',
                boxShadow: 'sm'
              } : {}}
              onClick={() => isClickable && onStepClick(step.key)}
              minH="45px"
              h="fit-content"
            >
              {/* Step Number & Icon */}
              <Flex
                w="22px"
                h="22px"
                borderRadius="full"
                align="center"
                justify="center"
                bg={status === 'current' ? currentColors.brand500 : 'transparent'}
                border={status !== 'current' ? '1px solid' : 'none'}
                borderColor={colors.iconColor}
                flexShrink={0}
                me="6px"
              >
                {status === 'completed' ? (
                  <Text color={colors.iconColor} fontSize="xs" fontWeight="bold">✓</Text>
                ) : status === 'current' ? (
                  <Icon as={step.icon} w="12px" h="12px" color="white" />
                ) : (
                  <Text color={colors.iconColor} fontSize="xs" fontWeight="bold">{step.id}</Text>
                )}
              </Flex>

              {/* Step Content - Text canh phải */}
              <Box flex="1" textAlign="left">
                <Flex align="center" justify="space-between">
                  <Text
                    fontSize="xs"
                    fontWeight="600"
                    color={colors.textColor}
                    lineHeight="short"
                  >
                    {step.title}
                  </Text>
                  {status === 'current' && (
                    <Badge
                      colorScheme="brand"
                      size="xs"
                      borderRadius="full"
                      fontSize="xs"
                      ml="4px"
                    >
                      ►
                    </Badge>
                  )}
                </Flex>
                <Text
                  fontSize="xs"
                  color={secondaryText}
                  lineHeight="short"
                  opacity={0.8}
                  mt="1px"
                >
                  {step.description}
                </Text>
              </Box>
            </Flex>
          );
        })}
      </SimpleGrid>
    </Box>
  );
}