'use client';

import {
  Box,
  Text,
  Flex,
  Select,
  Input,
  Checkbox,
  VStack,
  HStack,
  SimpleGrid,
  useColorModeValue,
  Spinner,
  Badge,
} from '@chakra-ui/react';
import { useState, useEffect } from 'react';
import { useColorTheme } from '@/contexts/ColorThemeContext';

interface LocationTimeCanvasProps {
  // Chat-controlled data
  locationTimeData?: {
    country: string;
    timezone: string;
    language: string;
    working_days: string[];
    from_time: string;
    to_time: string;
  };
  isLoading?: boolean;
  onStepChange?: (stepName: string, data: any) => void;
  adaptiveConfig?: {
    mode: 'compact' | 'normal' | 'spacious';
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
  };
  availableHeight?: number;
}

export default function LocationTimeCanvas({ 
  locationTimeData,
  isLoading = false,
  onStepChange, 
  adaptiveConfig = {
    mode: 'normal',
    fontSize: { header: 'md', title: 'xs', body: 'xs', small: 'xs' },
    spacing: { section: '20px', item: '16px', padding: '30px' },
    showOptional: true
  }
}: LocationTimeCanvasProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  const cardBg = useColorModeValue('gray.50', 'navy.700');

  // Debug logging for workdays
  console.log('🔄 Step 2 Canvas - locationTimeData:', locationTimeData);
  console.log('🔄 Step 2 Canvas - working_days:', locationTimeData?.working_days);

  // Convert working_days array to workDays object for display
  const workDays = {
    monday: locationTimeData?.working_days?.includes('Monday') ?? true,
    tuesday: locationTimeData?.working_days?.includes('Tuesday') ?? true,
    wednesday: locationTimeData?.working_days?.includes('Wednesday') ?? true,
    thursday: locationTimeData?.working_days?.includes('Thursday') ?? true,
    friday: locationTimeData?.working_days?.includes('Friday') ?? true,
    saturday: locationTimeData?.working_days?.includes('Saturday') ?? true,
    sunday: locationTimeData?.working_days?.includes('Sunday') ?? true
  };

  // Default values for display
  const displayData = {
    country: locationTimeData?.country ?? 'Vietnam',
    timezone: locationTimeData?.timezone ?? 'Asia/Ho_Chi_Minh',
    language: locationTimeData?.language ?? 'English (en-US)',
    workStartTime: locationTimeData?.from_time ?? '07:00',
    workEndTime: locationTimeData?.to_time ?? '22:00',
    workDays: workDays
  };

  // Pure display component - no business logic

  // Country options
  const countryOptions = [
    'Vietnam', 'Thailand', 'Singapore', 'Indonesia', 'Philippines',
    'United States', 'United Kingdom', 'France', 'Germany', 'Japan',
    'South Korea', 'Australia', 'Canada', 'India', 'China'
  ];

  // Timezone options (IANA format for backend compatibility)
  const timezoneOptions = [
    'Asia/Ho_Chi_Minh', 'Asia/Bangkok', 'Asia/Singapore',
    'Asia/Jakarta', 'Asia/Manila', 'Asia/Tokyo',
    'Asia/Seoul', 'Australia/Sydney', 'Europe/London',
    'Europe/Paris', 'America/New_York', 'America/Los_Angeles'
  ];

  // Display names for timezone options
  const timezoneDisplayNames: { [key: string]: string } = {
    'Asia/Ho_Chi_Minh': 'Ho Chi Minh (UTC+7)',
    'Asia/Bangkok': 'Bangkok (UTC+7)', 
    'Asia/Singapore': 'Singapore (UTC+8)',
    'Asia/Jakarta': 'Jakarta (UTC+7)',
    'Asia/Manila': 'Manila (UTC+8)',
    'Asia/Tokyo': 'Tokyo (UTC+9)',
    'Asia/Seoul': 'Seoul (UTC+9)',
    'Australia/Sydney': 'Sydney (UTC+11)',
    'Europe/London': 'London (UTC+0)',
    'Europe/Paris': 'Paris (UTC+1)',
    'America/New_York': 'New York (UTC-5)',
    'America/Los_Angeles': 'Los Angeles (UTC-8)'
  };

  // Language options
  const languageOptions = [
    'English (en-US)', 'English (en-GB)', 'Tiếng Việt (vi-VN)',
    'Chinese (zh-CN)', 'Japanese (ja-JP)', 'Korean (ko-KR)',
    'Thai (th-TH)', 'Indonesian (id-ID)', 'French (fr-FR)'
  ];

  // Day labels
  const dayLabels = [
    { key: 'monday', label: 'Mon' },
    { key: 'tuesday', label: 'Tue' },
    { key: 'wednesday', label: 'Wed' },
    { key: 'thursday', label: 'Thu' },
    { key: 'friday', label: 'Fri' },
    { key: 'saturday', label: 'Sat' },
    { key: 'sunday', label: 'Sun' }
  ];

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
        📍 Step 2: Location & Time Configuration
      </Text>

      <VStack spacing={adaptiveConfig.spacing.item} align="stretch">

        {/* Location Settings */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            🌍 Location & Language
          </Text>
          <Box bg={cardBg} p="16px" borderRadius="12px">
            <SimpleGrid 
              columns={adaptiveConfig.mode === 'compact' ? 1 : { base: 1, md: 3 }} 
              spacing="12px"
              maxW="100%"
            >
              {/* Country - Essential */}
              <VStack align="stretch" spacing="6px">
                <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor}>
                  Country
                </Text>
                <Select
                  value={displayData.country}
                  onChange={(e) => {
                    onStepChange?.('location_time', { country: e.target.value });
                  }}
                  size="sm"
                  borderColor={borderColor}
                  _focus={{ borderColor: currentColors.brand500 }}
                >
                  {countryOptions.map(country => (
                    <option key={country} value={country}>{country}</option>
                  ))}
                </Select>
              </VStack>

              {/* Timezone */}
              <VStack align="stretch" spacing="6px">
                <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor}>
                  Timezone
                </Text>
                <Select
                  value={displayData.timezone}
                  onChange={(e) => {
                    onStepChange?.('location_time', { timezone: e.target.value });
                  }}
                  size="sm"
                  borderColor={borderColor}
                  _focus={{ borderColor: currentColors.brand500 }}
                >
                  {timezoneOptions.map(timezone => (
                    <option key={timezone} value={timezone}>
                      {timezoneDisplayNames[timezone] || timezone}
                    </option>
                  ))}
                </Select>
              </VStack>

              {/* Language */}
              <VStack align="stretch" spacing="6px">
                <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor}>
                  Language
                </Text>
                <Select
                  value={displayData.language}
                  onChange={(e) => {
                    onStepChange?.('location_time', { language: e.target.value });
                  }}
                  size="sm"
                  borderColor={borderColor}
                  _focus={{ borderColor: currentColors.brand500 }}
                >
                  {languageOptions.map(language => (
                    <option key={language} value={language}>{language}</option>
                  ))}
                </Select>
              </VStack>
            </SimpleGrid>
          </Box>
        </Box>

        {/* Work Schedule */}
        {adaptiveConfig.showOptional && (
          <Box>
            <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
              ⏰ Work Schedule
            </Text>
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <VStack spacing="16px" align="stretch">
                {/* Work Hours */}
                <HStack spacing="16px" align="center" wrap="wrap">
                  <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} minW="60px">
                    Hours:
                  </Text>
                  <HStack spacing="8px">
                    <Input
                      type="time"
                      value={displayData.workStartTime}
                      onChange={(e) => {
                        onStepChange?.('location_time', { workStartTime: e.target.value });
                      }}
                      size="sm"
                      w="120px"
                      borderColor={borderColor}
                      _focus={{ borderColor: currentColors.brand500 }}
                    />
                    <Text fontSize={adaptiveConfig.fontSize.body} color={secondaryText}>to</Text>
                    <Input
                      type="time"
                      value={displayData.workEndTime}
                      onChange={(e) => {
                        onStepChange?.('location_time', { workEndTime: e.target.value });
                      }}
                      size="sm"
                      w="120px"
                      borderColor={borderColor}
                      _focus={{ borderColor: currentColors.brand500 }}
                    />
                  </HStack>
                </HStack>

                {/* Work Days */}
                <VStack align="stretch" spacing="8px">
                  <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor}>
                    Days:
                  </Text>
                  <SimpleGrid columns={{ base: 4, md: 7 }} spacing="8px" maxW="100%">
                    {dayLabels.map(({ key, label }) => (
                      <Checkbox
                        key={key}
                        isChecked={displayData.workDays[key as keyof typeof displayData.workDays]}
                        onChange={() => {
                          onStepChange?.('location_time', { workDay: key });
                        }}
                        colorScheme="brand"
                        size="sm"
                      >
                        <Text fontSize={adaptiveConfig.fontSize.small}>{label}</Text>
                      </Checkbox>
                    ))}
                  </SimpleGrid>
                </VStack>
              </VStack>
            </Box>
          </Box>
        )}

        {/* Current Configuration Summary */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            📋 Current Configuration
          </Text>
          <Box
            bg={cardBg}
            borderRadius="12px"
            p="16px"
            border="1px solid"
            borderColor={borderColor}
          >
            <VStack align="stretch" spacing="4px">
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
                <strong>Location:</strong> {displayData.country}, {displayData.timezone}
              </Text>
              {adaptiveConfig.showOptional && (
                <>
                  <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
                    <strong>Language:</strong> {displayData.language}
                  </Text>
                  <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
                    <strong>Work Schedule:</strong> {displayData.workStartTime} - {displayData.workEndTime}, {Object.values(displayData.workDays).filter(Boolean).length} days/week
                  </Text>
                </>
              )}
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText} fontStyle="italic" mt="8px">
                💡 Change values above to update configuration, or click Continue to proceed
              </Text>
            </VStack>
          </Box>
        </Box>
      </VStack>
    </Box>
  );
}