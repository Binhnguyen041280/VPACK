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

interface Camera {
  name: string;
  path: string;
}

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

  // Function to fetch cameras from backend
  const fetchCameras = async () => {
    try {
      setLoadingCameras(true);

      // Call the new camera configurations endpoint
      const response = await fetch('http://localhost:8080/api/camera-configurations', {
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          const cameraList: Camera[] = data.cameras.map((camera: any) => ({
            name: camera.name,
            path: camera.path
          }));

          setCameras(cameraList);

          toast({
            title: 'Cameras Loaded',
            description: `Found ${cameraList.length} cameras`,
            status: 'success',
            duration: 2000,
          });
        } else {
          throw new Error(data.error || 'Failed to load cameras');
        }
      } else {
        throw new Error(`HTTP ${response.status}: Failed to fetch cameras`);
      }
    } catch (error) {
      console.error('Error fetching cameras:', error);
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to load cameras',
        status: 'error',
        duration: 3000,
      });

      // Fallback to empty cameras list
      setCameras([]);
    } finally {
      setLoadingCameras(false);
    }
  };

  // Mock function to simulate backend status fetch
  const fetchProgramStatus = async () => {
    try {
      setIsLoading(true);
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 500));

      // Mock response
      const mockData = {
        current_running: isRunning ? 'First Run' : null,
        custom_path: customPath || null,
        days: days
      };

      setProgramStatus(mockData);

      toast({
        title: 'Status Updated',
        description: 'Program status refreshed successfully',
        status: 'success',
        duration: 2000,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to fetch program status',
        status: 'error',
        duration: 3000,
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Mock function to simulate starting program
  const startProgram = async (programId: string) => {
    try {
      setActionLoading(true);

      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Mock success response
      setIsRunning(true);
      setProgramStatus({
        current_running: programCards.find(p => p.id === programId)?.englishName || 'Unknown',
        custom_path: programId === 'custom' ? customPath : null,
        days: programId === 'first' ? (typeof days === 'string' ? parseInt(days) || 7 : days) : null
      });

      toast({
        title: 'Success',
        description: `${programCards.find(p => p.id === programId)?.englishName} started successfully`,
        status: 'success',
        duration: 3000,
      });

      setSelectedProgram(null);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to start program',
        status: 'error',
        duration: 5000,
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Mock function to simulate stopping program
  const stopProgram = async () => {
    try {
      setActionLoading(true);

      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000));

      setIsRunning(false);
      setProgramStatus({
        current_running: null,
        custom_path: null,
        days: null
      });

      toast({
        title: 'Success',
        description: 'Program stopped successfully',
        status: 'success',
        duration: 3000,
      });

      setSelectedProgram(null);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to stop program',
        status: 'error',
        duration: 5000,
      });
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