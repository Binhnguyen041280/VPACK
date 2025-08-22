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

interface LocationTimeData {
  country: string;
  timezone: string;
  language: string;
  workStartTime: string;
  workEndTime: string;
  workDays: {
    monday: boolean;
    tuesday: boolean;
    wednesday: boolean;
    thursday: boolean;
    friday: boolean;
    saturday: boolean;
    sunday: boolean;
  };
}

interface DetectedInfo {
  country: string;
  timezone: string;
  language: string;
  isDetecting: boolean;
}

interface LocationTimeCanvasProps {
  onStepChange?: (stepName: string, data: any) => void;
}

export default function LocationTimeCanvas({ onStepChange }: LocationTimeCanvasProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.300');
  const textColor = useColorModeValue('navy.700', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  const labelColor = useColorModeValue('navy.700', 'white');

  // Auto-detection state
  const [detected, setDetected] = useState<DetectedInfo>({
    country: '',
    timezone: '',
    language: '',
    isDetecting: true
  });

  // Configuration state
  const [config, setConfig] = useState<LocationTimeData>({
    country: 'Vietnam',
    timezone: 'Asia/Ho_Chi_Minh (UTC+7)',
    language: 'English (en-US)',
    workStartTime: '07:00',
    workEndTime: '22:00',
    workDays: {
      monday: true,
      tuesday: true,
      wednesday: true,
      thursday: true,
      friday: true,
      saturday: true,
      sunday: true
    }
  });

  // Auto-detection logic
  useEffect(() => {
    const detectUserLocation = async () => {
      try {
        // Detect timezone
        const detectedTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        
        // Detect language
        const detectedLanguage = navigator.language || 'en-US';
        
        // Map timezone to country (simplified mapping)
        const timezoneToCountry: { [key: string]: string } = {
          'Asia/Ho_Chi_Minh': 'Vietnam',
          'Asia/Bangkok': 'Thailand',
          'Asia/Singapore': 'Singapore',
          'Asia/Jakarta': 'Indonesia',
          'Asia/Manila': 'Philippines',
          'America/New_York': 'United States',
          'America/Los_Angeles': 'United States',
          'Europe/London': 'United Kingdom',
          'Europe/Paris': 'France',
          'Asia/Tokyo': 'Japan',
          'Asia/Seoul': 'South Korea',
          'Australia/Sydney': 'Australia'
        };

        const detectedCountry = timezoneToCountry[detectedTimezone] || 'Vietnam';
        
        // Format timezone display
        const timezoneOffset = new Intl.DateTimeFormat('en', {
          timeZoneName: 'short'
        }).formatToParts(new Date()).find(part => part.type === 'timeZoneName')?.value || 'UTC+7';
        
        const formattedTimezone = `${detectedTimezone.split('/')[1]?.replace('_', ' ')} (${timezoneOffset})`;
        
        // Format language display
        const languageNames: { [key: string]: string } = {
          'en': 'English',
          'en-US': 'English (US)',
          'en-GB': 'English (UK)',
          'vi': 'Tiếng Việt',
          'vi-VN': 'Tiếng Việt (VN)',
          'zh': 'Chinese',
          'ja': 'Japanese',
          'ko': 'Korean',
          'th': 'Thai',
          'id': 'Indonesian'
        };
        
        const languageCode = detectedLanguage.split('-')[0];
        const formattedLanguage = languageNames[detectedLanguage] || languageNames[languageCode] || 'English (en-US)';

        setTimeout(() => {
          setDetected({
            country: detectedCountry,
            timezone: formattedTimezone,
            language: formattedLanguage,
            isDetecting: false
          });

          // Update config with detected values
          setConfig(prev => ({
            ...prev,
            country: detectedCountry,
            timezone: formattedTimezone,
            language: formattedLanguage
          }));
        }, 1500); // Simulate detection delay

      } catch (error) {
        console.error('Detection error:', error);
        setTimeout(() => {
          setDetected({
            country: 'Vietnam',
            timezone: 'Ho Chi Minh (UTC+7)',
            language: 'English (en-US)',
            isDetecting: false
          });
        }, 1500);
      }
    };

    detectUserLocation();
  }, []);

  // Handle work day toggle
  const handleWorkDayChange = (day: keyof typeof config.workDays) => {
    setConfig(prev => ({
      ...prev,
      workDays: {
        ...prev.workDays,
        [day]: !prev.workDays[day]
      }
    }));
  };

  // Country options
  const countryOptions = [
    'Vietnam', 'Thailand', 'Singapore', 'Indonesia', 'Philippines',
    'United States', 'United Kingdom', 'France', 'Germany', 'Japan',
    'South Korea', 'Australia', 'Canada', 'India', 'China'
  ];

  // Timezone options
  const timezoneOptions = [
    'Ho Chi Minh (UTC+7)', 'Bangkok (UTC+7)', 'Singapore (UTC+8)',
    'Jakarta (UTC+7)', 'Manila (UTC+8)', 'Tokyo (UTC+9)',
    'Seoul (UTC+9)', 'Sydney (UTC+11)', 'London (UTC+0)',
    'Paris (UTC+1)', 'New York (UTC-5)', 'Los Angeles (UTC-8)'
  ];

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
      bg={bgColor}
      borderRadius="20px"
      p={{ base: '20px', md: '30px' }}
      border="1px solid"
      borderColor={borderColor}
      maxW="100%"
      mx="auto"
      position="relative"
    >
      {/* Header */}
      <VStack spacing="20px" align="stretch">
        <Flex align="center" justify="space-between">
          <Text
            fontSize={{ base: 'lg', md: 'xl' }}
            fontWeight="700"
            color={textColor}
          >
            📍 Location & Time Configuration
          </Text>
          {detected.isDetecting && (
            <HStack spacing="8px">
              <Spinner size="sm" color={currentColors.brand500} />
              <Text fontSize="sm" color={secondaryText}>Detecting...</Text>
            </HStack>
          )}
        </Flex>

        {/* Location Settings */}
        <VStack spacing="16px" align="stretch">
          <Text fontSize="md" fontWeight="600" color={labelColor}>
            🌍 Location & Language
          </Text>
          
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing="16px">
            {/* Country */}
            <VStack align="stretch" spacing="8px">
              <HStack>
                <Text fontSize="sm" fontWeight="500" color={labelColor}>
                  Country
                </Text>
                {!detected.isDetecting && detected.country === config.country && (
                  <Badge colorScheme="green" size="sm">detected</Badge>
                )}
              </HStack>
              <Select
                value={config.country}
                onChange={(e) => {
                  setConfig(prev => ({ ...prev, country: e.target.value }));
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
            <VStack align="stretch" spacing="8px">
              <HStack>
                <Text fontSize="sm" fontWeight="500" color={labelColor}>
                  Timezone
                </Text>
                {!detected.isDetecting && detected.timezone === config.timezone && (
                  <Badge colorScheme="green" size="sm">detected</Badge>
                )}
              </HStack>
              <Select
                value={config.timezone}
                onChange={(e) => {
                  setConfig(prev => ({ ...prev, timezone: e.target.value }));
                  onStepChange?.('location_time', { timezone: e.target.value });
                }}
                size="sm"
                borderColor={borderColor}
                _focus={{ borderColor: currentColors.brand500 }}
              >
                {timezoneOptions.map(timezone => (
                  <option key={timezone} value={timezone}>{timezone}</option>
                ))}
              </Select>
            </VStack>

            {/* Language */}
            <VStack align="stretch" spacing="8px">
              <HStack>
                <Text fontSize="sm" fontWeight="500" color={labelColor}>
                  Language
                </Text>
                {!detected.isDetecting && detected.language === config.language && (
                  <Badge colorScheme="green" size="sm">detected</Badge>
                )}
              </HStack>
              <Select
                value={config.language}
                onChange={(e) => {
                  setConfig(prev => ({ ...prev, language: e.target.value }));
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
        </VStack>

        {/* Work Schedule */}
        <VStack spacing="16px" align="stretch">
          <Text fontSize="md" fontWeight="600" color={labelColor}>
            ⏰ Work Schedule
          </Text>
          
          {/* Work Hours */}
          <HStack spacing="16px" align="center" wrap="wrap">
            <Text fontSize="sm" fontWeight="500" color={labelColor} minW="60px">
              Hours:
            </Text>
            <HStack spacing="8px">
              <Input
                type="time"
                value={config.workStartTime}
                onChange={(e) => {
                  setConfig(prev => ({ ...prev, workStartTime: e.target.value }));
                  onStepChange?.('location_time', { workStartTime: e.target.value });
                }}
                size="sm"
                w="120px"
                borderColor={borderColor}
                _focus={{ borderColor: currentColors.brand500 }}
              />
              <Text fontSize="sm" color={secondaryText}>to</Text>
              <Input
                type="time"
                value={config.workEndTime}
                onChange={(e) => {
                  setConfig(prev => ({ ...prev, workEndTime: e.target.value }));
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
            <Text fontSize="sm" fontWeight="500" color={labelColor}>
              Days:
            </Text>
            <SimpleGrid columns={{ base: 4, md: 7 }} spacing="8px">
              {dayLabels.map(({ key, label }) => (
                <Checkbox
                  key={key}
                  isChecked={config.workDays[key as keyof typeof config.workDays]}
                  onChange={() => {
                    handleWorkDayChange(key as keyof typeof config.workDays);
                    onStepChange?.('location_time', { workDay: key });
                  }}
                  colorScheme="brand"
                  size="sm"
                >
                  <Text fontSize="sm">{label}</Text>
                </Checkbox>
              ))}
            </SimpleGrid>
          </VStack>
        </VStack>

        {/* Current Summary */}
        <Box
          bg={useColorModeValue('gray.50', 'whiteAlpha.100')}
          borderRadius="12px"
          p="16px"
          border="1px solid"
          borderColor={borderColor}
        >
          <Text fontSize="sm" fontWeight="600" color={labelColor} mb="8px">
            📋 Current Configuration:
          </Text>
          <VStack align="stretch" spacing="4px">
            <Text fontSize="xs" color={secondaryText}>
              <strong>Location:</strong> {config.country}, {config.timezone}
            </Text>
            <Text fontSize="xs" color={secondaryText}>
              <strong>Language:</strong> {config.language}
            </Text>
            <Text fontSize="xs" color={secondaryText}>
              <strong>Work Schedule:</strong> {config.workStartTime} - {config.workEndTime}, {Object.values(config.workDays).filter(Boolean).length} days/week
            </Text>
          </VStack>
        </Box>
      </VStack>
    </Box>
  );
}