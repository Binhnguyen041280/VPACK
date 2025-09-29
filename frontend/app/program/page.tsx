'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Flex,
  Text,
  VStack,
  HStack,
  useColorModeValue,
  useToast,
  SimpleGrid,
  Badge,
  Icon,
  Spinner,
  Input,
  FormControl,
  FormLabel,
  Radio,
  RadioGroup,
  Stack,
} from '@chakra-ui/react';
import { MdPlayArrow, MdStop, MdFolder, MdSettings, MdCheck, MdRefresh } from 'react-icons/md';
import { useColorTheme } from '@/contexts/ColorThemeContext';
import { useRoute } from '@/contexts/RouteContext';
import Card from '@/components/card/Card';
import programService, { Camera } from '@/services/programService';
import { useProgramProgress } from '@/hooks/useProgramProgress';
import { createToastError } from '@/utils/errorHandler';

interface ProgramStatus {
  current_running: string;
  custom_path: string | null;
  days: number | null;
}

interface ProgramCard {
  id: string;
  title: string;
  description: string;
  englishName: string;
  icon: React.ComponentType;
  disabled: boolean;
}

// Camera interface moved to programService.ts

const programCards: ProgramCard[] = [
  {
    id: 'first',
    title: 'First Run',
    description: 'Initialize system for first-time setup',
    englishName: 'First Run',
    icon: MdSettings,
    disabled: false
  },
  {
    id: 'default',
    title: 'Default Program',
    description: 'Run standard video processing workflow',
    englishName: 'Default',
    icon: MdPlayArrow,
    disabled: false
  },
  {
    id: 'custom',
    title: 'Custom Path',
    description: 'Specify custom file path for processing',
    englishName: 'Custom',
    icon: MdFolder,
    disabled: false
  }
];

export default function Program() {
  const { currentColors } = useColorTheme();
  const { setCurrentRoute } = useRoute();
  const toast = useToast();

  // UI Colors
  const bgColor = useColorModeValue('white', 'navy.900');
  const textColor = useColorModeValue('navy.700', 'white');
  const cardBg = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');

  // State - Mock data for frontend-only version
  const [programStatus, setProgramStatus] = useState<ProgramStatus | null>({
    current_running: null,
    custom_path: null,
    days: null
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [customPath, setCustomPath] = useState('');
  const [days, setDays] = useState<number | string>(7);
  const [selectedProgram, setSelectedProgram] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedCamera, setSelectedCamera] = useState<string | null>(null);
  const [loadingCameras, setLoadingCameras] = useState(false);

  // Progress monitoring hook
  const {
    progressData,
    isLoading: isProgressLoading,
    error: progressError,
    startPolling,
    stopPolling,
    isPolling
  } = useProgramProgress({
    interval: 3000, // Poll every 3 seconds
    onError: (error) => {
      toast({
        title: 'Progress Monitoring Error',
        description: error,
        status: 'warning',
        duration: 4000,
      });
    }
  });

  // Function to fetch cameras from backend
  const fetchCameras = async () => {
    try {
      setLoadingCameras(true);

      const cameras = await programService.getCameras();
      setCameras(cameras);

      toast({
        title: 'Cameras Loaded',
        description: `Found ${cameras.length} cameras`,
        status: 'success',
        duration: 2000,
      });
    } catch (error) {
      console.error('Error fetching cameras:', error);
      const toastError = createToastError(error, 'Camera configuration');
      toast(toastError);

      setCameras([]);
    } finally {
      setLoadingCameras(false);
    }
  };

  // Function to fetch program status from backend
  const fetchProgramStatus = async () => {
    try {
      setIsLoading(true);

      const status = await programService.getProgramStatus();
      setProgramStatus(status);

      // Update UI state based on backend status
      setIsRunning(!!status.current_running);

      toast({
        title: 'Status Updated',
        description: 'Program status refreshed successfully',
        status: 'success',
        duration: 2000,
      });
    } catch (error) {
      console.error('Error fetching program status:', error);
      const toastError = createToastError(error, 'Program status');
      toast(toastError);
    } finally {
      setIsLoading(false);
    }
  };

  // Function to start program via backend API
  const startProgram = async (programId: string) => {
    try {
      setActionLoading(true);

      const response = await programService.startProgram({
        programType: programId as 'first' | 'default' | 'custom',
        action: 'run',
        days: programId === 'first' ? (typeof days === 'string' ? parseInt(days) || 7 : days) : undefined,
        customPath: programId === 'custom' ? customPath : undefined
      });

      // Update state based on backend response
      setIsRunning(true);
      setProgramStatus({
        current_running: response.current_running,
        custom_path: response.custom_path,
        days: response.days
      });

      toast({
        title: 'Success',
        description: `${programCards.find(p => p.id === programId)?.englishName} started successfully`,
        status: 'success',
        duration: 3000,
      });

      setSelectedProgram(null);

      // Start progress monitoring
      startPolling();
    } catch (error) {
      console.error('Error starting program:', error);
      const toastError = createToastError(error, 'Starting program');
      toast(toastError);
    } finally {
      setActionLoading(false);
    }
  };

  // Function to stop program via backend API
  const stopProgram = async () => {
    try {
      setActionLoading(true);

      const response = await programService.stopProgram();

      setIsRunning(false);
      setProgramStatus({
        current_running: response.current_running,
        custom_path: response.custom_path,
        days: response.days
      });

      toast({
        title: 'Success',
        description: 'Program stopped successfully',
        status: 'success',
        duration: 3000,
      });

      setSelectedProgram(null);

      // Stop progress monitoring
      stopPolling();
    } catch (error) {
      console.error('Error stopping program:', error);
      const toastError = createToastError(error, 'Stopping program');
      toast(toastError);
    } finally {
      setActionLoading(false);
    }
  };

  // Set active route on component mount
  useEffect(() => {
    setCurrentRoute('/program');
    // Initialize with mock data
    fetchProgramStatus();
  }, [setCurrentRoute]);

  // Fetch cameras when custom program is selected
  useEffect(() => {
    if (selectedProgram === 'custom' && cameras.length === 0) {
      fetchCameras();
    }
  }, [selectedProgram, cameras.length]);

  if (isLoading && !programStatus) {
    return (
      <Box p="20px">
        <Flex justify="center" align="center" h="200px">
          <VStack spacing={4}>
            <Spinner size="lg" color={currentColors.brand500} />
            <Text color={textColor}>Loading program status...</Text>
          </VStack>
        </Flex>
      </Box>
    );
  }

  return (
    <Box p="20px">
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <Box>
          <Text fontSize="2xl" fontWeight="700" color={textColor} mb={2}>
            Program Control
          </Text>
          <Text fontSize="md" color={textColor} opacity={0.7}>
            Select and manage video processing programs
          </Text>
        </Box>

        {/* Current Status */}
        {programStatus && (
          <Card bg={cardBg} p={6}>
            <VStack spacing={4} align="stretch">
              <Flex justify="space-between" align="center">
                <Text fontSize="lg" fontWeight="600" color={textColor}>
                  Current Status
                </Text>
                <HStack spacing={2}>
                  <Button
                    size="sm"
                    variant="ghost"
                    leftIcon={<Icon as={MdRefresh} />}
                    onClick={fetchProgramStatus}
                    isLoading={isLoading}
                  >
                    Refresh
                  </Button>
                  <Badge
                    colorScheme={isRunning ? 'green' : 'gray'}
                    variant="subtle"
                    fontSize="sm"
                    px={3}
                    py={1}
                    borderRadius="full"
                  >
                    {isRunning ? 'Running' : 'Stopped'}
                  </Badge>
                </HStack>
              </Flex>

              {isRunning && (
                <Box>
                  <Text fontSize="sm" color={textColor} opacity={0.7} mb={2}>
                    Active Program:
                  </Text>
                  <Text fontSize="md" fontWeight="600" color={currentColors.brand500}>
                    {programStatus.current_running}
                  </Text>
                  {programStatus.custom_path && (
                    <Text fontSize="sm" color={textColor} opacity={0.7} mt={2}>
                      Path: {programStatus.custom_path}
                    </Text>
                  )}

                  {/* Real-time Progress Display */}
                  {isPolling && progressData && (
                    <Box mt={4} p={3} bg={borderColor} borderRadius="md">
                      <HStack justify="space-between" mb={2}>
                        <Text fontSize="sm" fontWeight="600" color={textColor}>
                          Processing Progress
                        </Text>
                        {isProgressLoading && (
                          <Spinner size="sm" color={currentColors.brand500} />
                        )}
                      </HStack>

                      {progressData.files && progressData.files.length > 0 ? (
                        <VStack spacing={1} align="stretch">
                          {progressData.files.slice(0, 3).map((file, index) => (
                            <Flex key={`${file.file}-${index}`} justify="space-between" align="center">
                              <Text fontSize="xs" color={textColor} opacity={0.8} isTruncated maxW="60%">
                                {file.file.split('/').pop() || file.file}
                              </Text>
                              <Badge
                                size="sm"
                                colorScheme={
                                  file.status === 'xong' ? 'green' :
                                  file.status === 'đang frame sampler ...' ? 'blue' :
                                  file.status === 'lỗi' ? 'red' : 'gray'
                                }
                              >
                                {file.status}
                              </Badge>
                            </Flex>
                          ))}
                          {progressData.files.length > 3 && (
                            <Text fontSize="xs" color={textColor} opacity={0.6} textAlign="center">
                              +{progressData.files.length - 3} more files...
                            </Text>
                          )}
                        </VStack>
                      ) : (
                        <Text fontSize="xs" color={textColor} opacity={0.6}>
                          No files in processing queue
                        </Text>
                      )}

                      {progressError && (
                        <Text fontSize="xs" color="red.500" mt={2}>
                          {progressError}
                        </Text>
                      )}
                    </Box>
                  )}
                </Box>
              )}

              {/* Stop Button - Always show when program is running */}
              {isRunning && (
                <Flex justify="flex-end">
                  <Button
                    colorScheme="red"
                    leftIcon={<Icon as={MdStop} />}
                    onClick={stopProgram}
                    isLoading={actionLoading && !selectedProgram}
                    loadingText="Stopping..."
                    size="sm"
                  >
                    Stop Program
                  </Button>
                </Flex>
              )}
            </VStack>
          </Card>
        )}

        {/* Program Cards */}
        <Box>
          <Text fontSize="lg" fontWeight="600" color={textColor} mb={4}>
            Select Program
          </Text>

          <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
            {programCards.map((program) => (
              <Card
                key={program.id}
                bg={cardBg}
                p={6}
                cursor={program.disabled || isRunning ? 'not-allowed' : 'pointer'}
                opacity={program.disabled || isRunning ? 0.5 : 1}
                border="2px solid"
                borderColor={selectedProgram === program.id ? currentColors.brand500 : borderColor}
                _hover={!program.disabled && !isRunning ? {
                  borderColor: currentColors.brand500,
                  transform: 'translateY(-2px)',
                  shadow: 'lg',
                } : {}}
                transition="all 0.2s"
                onClick={() => {
                  if (!program.disabled && !isRunning) {
                    setSelectedProgram(program.id);
                  }
                }}
              >
                <VStack spacing={4} align="center" textAlign="center">
                  <Icon
                    as={program.icon}
                    boxSize={8}
                    color={selectedProgram === program.id ? currentColors.brand500 : textColor}
                  />

                  <VStack spacing={1}>
                    <Text fontSize="lg" fontWeight="600" color={textColor}>
                      {program.englishName}
                    </Text>
                    <Text fontSize="sm" color={textColor} opacity={0.7}>
                      {program.title}
                    </Text>
                    <Text fontSize="xs" color={textColor} opacity={0.5} textAlign="center">
                      {program.description}
                    </Text>
                  </VStack>

                  {selectedProgram === program.id && (
                    <Icon as={MdCheck} color={currentColors.brand500} boxSize={5} />
                  )}
                </VStack>
              </Card>
            ))}
          </SimpleGrid>
        </Box>

        {/* Custom Path Input */}
        {selectedProgram === 'custom' && (
          <Card bg={cardBg} p={6}>
            <VStack spacing={6} align="stretch">
              <FormControl>
                <FormLabel color={textColor} fontSize="sm" fontWeight="600">
                  Custom Path
                </FormLabel>
                <Input
                  placeholder="Enter custom file or directory path..."
                  value={customPath}
                  onChange={(e) => setCustomPath(e.target.value)}
                  color={textColor}
                  borderColor={borderColor}
                  _focus={{ borderColor: currentColors.brand500 }}
                />
              </FormControl>

              {/* Camera Selection */}
              <FormControl>
                <Flex justify="space-between" align="center" mb={3}>
                  <FormLabel color={textColor} fontSize="sm" fontWeight="600" mb={0}>
                    Select Camera Configuration
                  </FormLabel>
                  {loadingCameras && (
                    <Spinner size="sm" color={currentColors.brand500} />
                  )}
                </Flex>

                {cameras.length > 0 ? (
                  <RadioGroup
                    value={selectedCamera || ''}
                    onChange={setSelectedCamera}
                  >
                    <Stack spacing={3}>
                      {cameras.map((camera) => (
                        <Radio
                          key={camera.name}
                          value={camera.name}
                          colorScheme="red"
                          borderColor={borderColor}
                          _checked={{
                            bg: currentColors.brand500,
                            borderColor: currentColors.brand500,
                          }}
                        >
                          <Text color={textColor} fontSize="sm">
                            {camera.name}
                          </Text>
                        </Radio>
                      ))}
                    </Stack>
                  </RadioGroup>
                ) : !loadingCameras ? (
                  <Box p={4} borderRadius="md" bg={borderColor} opacity={0.5}>
                    <Text color={textColor} fontSize="sm" textAlign="center">
                      No cameras available. Please configure video sources first.
                    </Text>
                  </Box>
                ) : null}

                <Text fontSize="xs" color={textColor} opacity={0.6} mt={2}>
                  Select one camera configuration for this custom processing session
                </Text>
              </FormControl>
            </VStack>
          </Card>
        )}

        {/* Days Input for First Run */}
        {selectedProgram === 'first' && (
          <Card bg={cardBg} p={6}>
            <FormControl>
              <FormLabel color={textColor} fontSize="sm" fontWeight="600">
                Number of Days to Process
              </FormLabel>
              <Input
                type="number"
                min="1"
                max="30"
                placeholder="Enter number of days (e.g., 7)"
                value={days}
                onChange={(e) => {
                  const value = e.target.value;
                  if (value === '') {
                    setDays('');
                  } else {
                    const num = parseInt(value);
                    if (!isNaN(num) && num >= 1 && num <= 30) {
                      setDays(num);
                    }
                  }
                }}
                color={textColor}
                borderColor={borderColor}
                _focus={{ borderColor: currentColors.brand500 }}
              />
              <Text fontSize="xs" color={textColor} opacity={0.6} mt={2}>
                How many days back to scan for video files (maximum 30 days)
              </Text>
            </FormControl>
          </Card>
        )}

        {/* Action Buttons */}
        {selectedProgram && !isRunning && (
          <Flex justify="center">
            <HStack spacing={4}>
              <Button
                variant="outline"
                onClick={() => {
                  setSelectedProgram(null);
                  setCustomPath('');
                  setDays(7);
                  setSelectedCamera(null);
                }}
                disabled={actionLoading}
              >
                Cancel
              </Button>
              <Button
                bg={currentColors.gradient}
                color="white"
                leftIcon={<Icon as={MdPlayArrow} />}
                onClick={() => startProgram(selectedProgram)}
                isLoading={actionLoading}
                loadingText="Starting..."
                disabled={selectedProgram === 'custom' && (!customPath.trim() || !selectedCamera)}
                _hover={{
                  bg: currentColors.gradient,
                }}
              >
                Start Program
              </Button>
            </HStack>
          </Flex>
        )}
      </VStack>
    </Box>
  );
}