'use client';

import React, { useState, useEffect } from 'react';
import {
  VStack,
  HStack,
  Box,
  Text,
  Button,
  Switch,
  FormControl,
  FormLabel,
  Input,
  Select,
  Divider,
  Badge,
  Progress,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Spinner,
  useColorModeValue,
  useToast,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
} from '@chakra-ui/react';

import Card from '@/components/card/Card';
import IconBox from '@/components/icons/IconBox';
import { AccountService } from '@/services/accountService';
import { useColorTheme } from '@/contexts/ColorThemeContext';

const AIUsage: React.FC = () => {
  const toast = useToast();

  // Core state - Mock data for now (backend chưa có)
  const [aiConfig, setAiConfig] = useState({
    ai_enabled: false,
    api_provider: 'claude' as 'claude' | 'openai',
    use_vtrack_key: true,
    has_custom_key: false,
    customer_api_key: '',
  });

  const [stats, setStats] = useState({
    total_recoveries: 0,
    successful: 0,
    failed: 0,
    success_rate: 0,
    total_cost_usd: 0,
    avg_cost_per_recovery: 0,
  });

  const [recoveryLogs, setRecoveryLogs] = useState<any[]>([]);

  // UI state
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Theme colors (pattern từ MyPlan)
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const textColor = useColorModeValue('gray.800', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  const statBg = useColorModeValue('gray.50', 'gray.700');

  // Import color theme for gradient button
  const { currentColors } = useColorTheme();

  // Load initial data
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        // TODO: Gọi API khi backend ready
        // const configRes = await AIService.getConfig();
        // const statsRes = await AIService.getStats();
        // const logsRes = await AIService.getRecoveryLogs(10);

        // Mock data for now
        setTimeout(() => {
          setAiConfig({
            ai_enabled: false,
            api_provider: 'claude',
            use_vtrack_key: true,
            has_custom_key: false,
            customer_api_key: '',
          });

          setStats({
            total_recoveries: 0,
            successful: 0,
            failed: 0,
            success_rate: 0,
            total_cost_usd: 0,
            avg_cost_per_recovery: 0,
          });

          setRecoveryLogs([]);
          setIsLoading(false);
        }, 500);
      } catch (error) {
        console.error('Failed to load AI usage data:', error);
        setError('Failed to load AI configuration');
        setIsLoading(false);
      }
    };

    loadData();
  }, []);

  // Handle config save
  const handleSaveConfig = async () => {
    setIsSaving(true);
    setError(null);

    try {
      // TODO: Gọi API khi backend ready
      // await AIService.updateConfig(aiConfig);

      // Mock success
      setTimeout(() => {
        toast({
          title: 'Configuration saved',
          description: 'AI settings have been updated successfully',
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
        setIsSaving(false);
      }, 500);
    } catch (error) {
      console.error('Failed to save config:', error);
      setError('Failed to save configuration');
      setIsSaving(false);
    }
  };

  // Handle API key test
  const handleTestApiKey = async () => {
    if (!aiConfig.customer_api_key.trim()) {
      toast({
        title: 'No API key provided',
        description: 'Please enter an API key to test',
        status: 'warning',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setIsTesting(true);

    try {
      // TODO: Gọi API khi backend ready
      // await AIService.testApiKey(aiConfig.customer_api_key, aiConfig.api_provider);

      // Mock success
      setTimeout(() => {
        toast({
          title: 'API Key Valid',
          description: `Successfully connected to ${aiConfig.api_provider === 'claude' ? 'Claude' : 'OpenAI'} API`,
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
        setIsTesting(false);
      }, 1000);
    } catch (error) {
      toast({
        title: 'API Key Invalid',
        description: 'Failed to connect with provided API key',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      setIsTesting(false);
    }
  };

  // Use AccountService format methods
  const formatCostVND = AccountService.formatCostVND;
  const formatCostUSD = AccountService.formatCostUSD;

  if (isLoading) {
    return (
      <Box
        display="flex"
        alignItems="center"
        justifyContent="center"
        minH="400px"
      >
        <VStack spacing={4}>
          <Spinner size="xl" />
          <Text color={secondaryText}>Loading AI usage data...</Text>
        </VStack>
      </Box>
    );
  }

  return (
    <VStack spacing={6} align="stretch" w="full" maxW="700px" mx="auto" px={6}>

      {/* Error Alert */}
      {error && (
        <Alert status="error">
          <AlertIcon />
          <AlertTitle>Error!</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Quick Status Bar */}
      <Card p={4} bg={bgColor} borderColor={borderColor}>
        <HStack justify="space-between" align="center" wrap="wrap">
          <HStack spacing={4}>
            <IconBox
              icon="🤖"
              bg={aiConfig.ai_enabled ? 'green.500' : 'gray.500'}
              color="white"
              w="40px"
              h="40px"
            />
            <VStack align="start" spacing={1}>
              <Text fontWeight="bold" color={textColor}>
                AI Usage
              </Text>
              <Text fontSize="sm" color={secondaryText}>
                {aiConfig.ai_enabled ? 'Active' : 'Inactive'}
              </Text>
            </VStack>
          </HStack>

          <HStack spacing={4}>
            {aiConfig.ai_enabled && (
              <Badge colorScheme="blue">
                {aiConfig.api_provider === 'claude' ? 'Claude API' : 'OpenAI API'}
              </Badge>
            )}
            <Button
              size="sm"
              colorScheme={aiConfig.ai_enabled ? 'red' : 'green'}
              onClick={() => setAiConfig({ ...aiConfig, ai_enabled: !aiConfig.ai_enabled })}
            >
              {aiConfig.ai_enabled ? 'Disable' : 'Enable'}
            </Button>
          </HStack>
        </HStack>
      </Card>

      {/* Configuration Card - Only show when enabled */}
      {aiConfig.ai_enabled && (
        <Card p={6} bg={bgColor} borderColor={borderColor}>
          <VStack align="stretch" spacing={4}>
            <Text fontSize="xl" fontWeight="bold" color={textColor}>
              ⚙️ Configuration
            </Text>

            <Divider />

            {/* AI Provider Selection */}
            <FormControl>
              <FormLabel fontSize="sm">Provider</FormLabel>
              <Select
                value={aiConfig.api_provider}
                onChange={(e) => setAiConfig({ ...aiConfig, api_provider: e.target.value as any })}
              >
                <option value="claude">Claude 3.5 Sonnet</option>
                <option value="openai">OpenAI GPT-4 Vision</option>
              </Select>
            </FormControl>

            {/* API Key Input - Always show */}
            <FormControl>
              <FormLabel fontSize="sm">API Key</FormLabel>
              <HStack>
                <Input
                  type="password"
                  placeholder="sk-ant-api... or sk-..."
                  value={aiConfig.customer_api_key}
                  onChange={(e) => setAiConfig({ ...aiConfig, customer_api_key: e.target.value })}
                />
                <Button
                  colorScheme="blue"
                  variant="outline"
                  onClick={handleTestApiKey}
                  isLoading={isTesting}
                  size="sm"
                  minW="60px"
                >
                  Test
                </Button>
              </HStack>
            </FormControl>

            {/* Save Button - Using gradient theme like Submit button */}
            <Box display="flex" justifyContent="center" w="full">
              <Button
                bg={currentColors.gradient}
                color="white"
                size="md"
                w="120px"
                onClick={handleSaveConfig}
                isLoading={isSaving}
                loadingText="Saving..."
                boxShadow="none"
                _hover={{
                  boxShadow: `0px 21px 27px -10px ${currentColors.primary}48 !important`,
                  bg: `${currentColors.gradient} !important`,
                  _disabled: {
                    bg: currentColors.gradient,
                  },
                }}
                _focus={{
                  bg: currentColors.gradient,
                }}
                _active={{
                  bg: currentColors.gradient,
                }}
              >
                Save
              </Button>
            </Box>
          </VStack>
        </Card>
      )}


    </VStack>
  );
};

export default AIUsage;
