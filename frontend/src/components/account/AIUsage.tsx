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
        // Load AI config from backend
        const configRes = await AccountService.getAIConfig();
        if (configRes.success && configRes.data) {
          setAiConfig({
            ai_enabled: configRes.data.ai_enabled || false,
            api_provider: configRes.data.api_provider || 'claude',
            use_vtrack_key: !configRes.data.has_custom_key,
            has_custom_key: configRes.data.has_custom_key || false,
            customer_api_key: configRes.data.masked_key || '',
          });
        }

        // Load AI stats from backend
        const statsRes = await AccountService.getAIStats();
        if (statsRes.success && statsRes.data) {
          setStats({
            total_recoveries: statsRes.data.total_recoveries || 0,
            successful: statsRes.data.successful || 0,
            failed: statsRes.data.failed || 0,
            success_rate: statsRes.data.success_rate || 0,
            total_cost_usd: statsRes.data.total_cost_usd || 0,
            avg_cost_per_recovery: statsRes.data.avg_cost_per_recovery || 0,
          });
        }

        // Load recent recovery logs
        const logsRes = await AccountService.getAIRecoveryLogs(10);
        if (logsRes.success && logsRes.data) {
          setRecoveryLogs(logsRes.data.logs || []);
        }

        setIsLoading(false);
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
      // Call backend to save config
      const response = await AccountService.updateAIConfig({
        ai_enabled: aiConfig.ai_enabled,
        api_provider: aiConfig.api_provider,
        customer_api_key: aiConfig.customer_api_key,
      });

      if (response.success) {
        toast({
          title: 'Configuration saved',
          description: response.message || 'AI settings have been updated successfully',
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
      } else {
        throw new Error(response.message || 'Failed to save configuration');
      }
      setIsSaving(false);
    } catch (error: any) {
      console.error('Failed to save config:', error);
      setError(error.message || 'Failed to save configuration');
      toast({
        title: 'Save failed',
        description: error.message || 'Failed to save configuration',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
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
      // Call backend to test API key
      const response = await AccountService.testAIApiKey(
        aiConfig.customer_api_key,
        aiConfig.api_provider
      );

      if (response.success) {
        toast({
          title: 'API Key Valid',
          description: response.message || `Successfully connected to ${aiConfig.api_provider === 'claude' ? 'Claude' : 'OpenAI'} API`,
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
      } else {
        throw new Error(response.message || 'Invalid API key');
      }
      setIsTesting(false);
    } catch (error: any) {
      toast({
        title: 'API Key Invalid',
        description: error.message || 'Failed to connect with provided API key',
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
