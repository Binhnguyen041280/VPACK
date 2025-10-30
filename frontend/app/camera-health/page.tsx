'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Flex,
  VStack,
  HStack,
  Text,
  Button,
  useColorModeValue,
  Badge,
  Icon,
  Spinner,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  useDisclosure,
  SimpleGrid,
  Progress,
  Divider,
  useToast,
} from '@chakra-ui/react';
import {
  MdCheck,
  MdWarning,
  MdError,
  MdRefresh,
  MdExpandMore,
} from 'react-icons/md';
import { useColorTheme } from '@/contexts/ColorThemeContext';
import Card from '@/components/card/Card';

interface HealthCheckItem {
  name: string;
  status: 'OK' | 'CAUTION' | 'CRITICAL' | 'NO_BASELINE';
  current_value?: number | string;
  threshold?: string;
  action?: string;
}

interface CameraHealthStatus {
  camera_name: string;
  overall_status: 'OK' | 'CAUTION' | 'CRITICAL' | 'NO_BASELINE';
  overall_rate_pct: number;
  items: HealthCheckItem[];
  baseline_success_rate_pct?: number;
  last_check?: string;
  current_success_rate_pct?: number;
  degradation_pct?: number;
  severity?: string;
  message?: string;
  recommendation?: string;
}

interface CameraBaseline {
  camera_name: string;
  baseline_success_rate_pct: number;
  status: 'active' | 'archived';
  overall_status?: 'OK' | 'CAUTION' | 'CRITICAL' | 'NO_BASELINE';  // From health check
}

const CameraHealthPage = () => {
  const { currentColors } = useColorTheme();
  const [cameras, setCameras] = useState<CameraBaseline[]>([]);
  const [selectedCamera, setSelectedCamera] = useState<CameraHealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const { isOpen, onOpen, onClose } = useDisclosure();

  const textColor = useColorModeValue('navy.700', 'white');
  const textSecondary = useColorModeValue('gray.600', 'gray.400');

  // Status color mapping
  const getStatusColor = (status: string | undefined) => {
    if (!status) return { bg: '#718096', text: 'white', badge: 'gray' };

    switch (status) {
      case 'OK':
        return { bg: '#48BB78', text: 'white', badge: 'green' };
      case 'CAUTION':
        return { bg: '#ED8936', text: 'white', badge: 'orange' };
      case 'CRITICAL':
        return { bg: '#F56565', text: 'white', badge: 'red' };
      case 'NO_BASELINE':
        return { bg: '#718096', text: 'white', badge: 'gray' };
      default:
        return { bg: '#718096', text: 'white', badge: 'gray' };
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'OK':
        return <MdCheck size={20} />;
      case 'CAUTION':
        return <MdWarning size={20} />;
      case 'CRITICAL':
        return <MdError size={20} />;
      default:
        return null;
    }
  };

  // Fetch cameras with baselines
  const fetchCameras = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8080/api/qr-detection/cameras');
      if (response.ok) {
        const data = await response.json();
        setCameras(data || []);
      }
    } catch (error) {
      console.error('Error fetching cameras:', error);
    } finally {
      setLoading(false);
    }
  };

  // Fetch health check status for a camera
  const fetchHealthStatus = async (cameraName: string) => {
    try {
      const response = await fetch(`http://localhost:8080/api/qr-detection/camera-health-status/${cameraName}`);
      if (response.ok) {
        const data = await response.json();

        // Build checklist first
        const checklistItems = buildChecklist(data.baseline?.success_rate_pct || 0, data.latest_check);

        // Calculate overall rate: 100% if both OK, 50% if one OK, 0% if both not OK
        const okCount = checklistItems.filter((item) => item.status === 'OK').length;
        const overallRate = (okCount / 2) * 100;

        // Determine overall status
        let overallStatus: 'OK' | 'CAUTION' | 'CRITICAL' | 'NO_BASELINE' = 'OK';
        if (okCount === 2) overallStatus = 'OK';
        else if (okCount === 1) overallStatus = 'CAUTION';
        else if (okCount === 0) overallStatus = 'CRITICAL';

        // If no baseline at all, mark as NO_BASELINE
        if (!data.baseline?.exists) {
          overallStatus = 'NO_BASELINE';
        }

        // Transform backend response to frontend format
        const transformedData: CameraHealthStatus = {
          camera_name: data.camera_name,
          overall_status: overallStatus,
          overall_rate_pct: overallRate,
          baseline_success_rate_pct: data.baseline?.success_rate_pct,
          last_check: data.latest_check?.timestamp,
          current_success_rate_pct: data.latest_check?.current_success_rate_pct,
          degradation_pct: data.latest_check?.degradation_pct,
          severity: data.latest_check?.severity,
          message: data.latest_check?.message,
          recommendation: data.latest_check?.recommendation,
          items: checklistItems,
        };

        setSelectedCamera(transformedData);
        onOpen();
      }
    } catch (error) {
      console.error('Error fetching health status:', error);
    }
  };

  // Build 2-item checklist from health check data
  const buildChecklist = (baseline: number, latestCheck: any): HealthCheckItem[] => {
    if (!latestCheck) {
      // Baseline exists but no health check yet - show "Not checked"
      return [
        {
          name: 'QR Trigger Readable',
          status: 'OK',  // Baseline = OK (until proven otherwise)
          current_value: `${baseline.toFixed(1)}% (baseline)`,
          threshold: '≥ 85%',
        },
        {
          name: 'Camera Position OK',
          status: 'OK',  // Baseline = OK
          current_value: 'Stable (baseline)',
          threshold: '< 10% offset',
        },
      ];
    }

    const items: HealthCheckItem[] = [];
    const currentRate = latestCheck.current_success_rate_pct || 0;
    const baselineRate = latestCheck.baseline_success_rate_pct || 0;

    // Item 1: QR Trigger Readable (compare with baseline)
    let qrStatus: 'OK' | 'CAUTION' | 'CRITICAL' = 'OK';
    const qrDegradation = currentRate - baselineRate;  // Can be negative (degradation)
    if (qrDegradation < -15) qrStatus = 'CRITICAL';   // > 15% degradation
    else if (qrDegradation < 0) qrStatus = 'CAUTION'; // Any degradation < 15%

    items.push({
      name: 'QR Trigger Readable',
      status: qrStatus,
      current_value: `${currentRate.toFixed(1)}% (Baseline: ${baselineRate.toFixed(1)}%)`,
      threshold: 'Degradation ≤ 0%',
      action: qrStatus !== 'OK' ? 'Clean QR trigger area or adjust lighting' : undefined,
    });

    // Item 2: Camera Position OK (from position_offset_pct)
    let positionStatus: 'OK' | 'CAUTION' | 'CRITICAL' = 'OK';
    const positionOffset = latestCheck.position_offset_pct || 0;  // Offset as % of ROI diagonal
    if (positionOffset > 20) positionStatus = 'CRITICAL';
    else if (positionOffset > 10) positionStatus = 'CAUTION';

    items.push({
      name: 'Camera Position OK',
      status: positionStatus,
      current_value: `${positionOffset.toFixed(1)}% offset`,
      threshold: '< 10% offset',
      action: positionStatus !== 'OK' ? 'Check camera mount or adjust position' : undefined,
    });

    return items;
  };

  // Refresh camera health
  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchCameras();
    setRefreshing(false);
  };

  useEffect(() => {
    fetchCameras();
  }, []);

  return (
    <Box pt={{ base: '130px', md: '80px' }} px="20px">
      {/* Header */}
      <Flex justify="space-between" align="center" mb="30px">
        <Box>
          <Text
            fontSize="2xl"
            fontWeight="700"
            color={textColor}
            mb="4px"
          >
            📊 Camera Health Check
          </Text>
          <Text fontSize="sm" color={textSecondary}>
            Monitor camera quality and QR detection performance
          </Text>
        </Box>
        <Button
          leftIcon={<MdRefresh />}
          bg={currentColors.brand500}
          color="white"
          _hover={{ opacity: 0.8 }}
          isLoading={refreshing}
          onClick={handleRefresh}
          variant="solid"
        >
          Refresh
        </Button>
      </Flex>

      {/* Status Summary Cards */}
      {loading ? (
        <Flex justify="center" align="center" h="200px">
          <Spinner size="lg" color={currentColors.brand500} />
        </Flex>
      ) : cameras.length === 0 ? (
        <Card>
          <Flex justify="center" align="center" h="200px">
            <Text color={textSecondary} fontSize="lg">
              No cameras found. Please set up a camera in Camera Config first.
            </Text>
          </Flex>
        </Card>
      ) : (
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing="20px" mb="30px">
          {cameras.map((camera) => (
            <CameraHealthCard
              key={camera.camera_name}
              camera={camera}
              onCheck={() => fetchHealthStatus(camera.camera_name)}
              getStatusColor={getStatusColor}
              getStatusIcon={getStatusIcon}
              buildChecklist={buildChecklist}
            />
          ))}
        </SimpleGrid>
      )}

      {/* Health Check Details Modal */}
      <HealthCheckModal
        isOpen={isOpen}
        onClose={onClose}
        camera={selectedCamera}
        getStatusColor={getStatusColor}
        getStatusIcon={getStatusIcon}
        onResume={() => {
          // Refresh cameras after resume
          fetchCameras();
          if (selectedCamera) {
            setTimeout(() => fetchHealthStatus(selectedCamera.camera_name), 500);
          }
        }}
      />
    </Box>
  );
};

// Individual Camera Health Card Component
interface CameraHealthCardProps {
  camera: CameraBaseline;
  onCheck: () => void;
  getStatusColor: (status: string) => any;
  getStatusIcon: (status: string) => React.ReactNode;
  buildChecklist: (baseline: number, latestCheck: any) => HealthCheckItem[];
}

const CameraHealthCard: React.FC<CameraHealthCardProps> = ({
  camera,
  onCheck,
  getStatusColor,
  getStatusIcon,
  buildChecklist,
}) => {
  const { currentColors } = useColorTheme();
  const textColor = useColorModeValue('navy.700', 'white');
  const bgCard = useColorModeValue('white', '#111C44');
  const borderColorValue = useColorModeValue('gray.200', 'gray.600');
  const textSecondary = useColorModeValue('gray.600', 'gray.400');
  const [loading, setLoading] = useState(false);
  const [healthData, setHealthData] = useState<any>(null);

  // Auto-fetch health status on mount
  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const response = await fetch(`http://localhost:8080/api/qr-detection/camera-health-status/${camera.camera_name}`);
        if (response.ok) {
          const data = await response.json();
          setHealthData(data);
        }
      } catch (error) {
        console.error('Error fetching health status:', error);
      }
    };
    fetchHealth();
  }, [camera.camera_name]);

  const handleClick = async () => {
    setLoading(true);
    onCheck();
    setLoading(false);
  };

  // Color values must be defined at top level (Rules of Hooks)
  const bgGrayLight = useColorModeValue('gray.50', 'gray.900');

  // ✅ Use overall_status from database (Backend decision authority)
  // Do NOT recalculate - trust the backend's QR priority logic
  const overallStatus = (camera.overall_status || 'OK') as 'OK' | 'CAUTION' | 'CRITICAL' | 'NO_BASELINE';

  const statusColor = getStatusColor(overallStatus);

  // Count critical/non-OK items for dynamic message
  const criticalItems = healthData?.latest_check
    ? buildChecklist(healthData.baseline?.success_rate_pct || 0, healthData.latest_check)
        .filter((item) => item.status !== 'OK').length
    : 0;

  // Build status message based on actual critical item count
  const getStatusMessage = () => {
    if (overallStatus === 'OK') return 'All checks passed';
    if (criticalItems === 0) return 'All checks passed';
    if (criticalItems === 1) return '1 issue detected';
    return `${criticalItems} issues detected`;
  };

  return (
    <Card
      p="20px"
      bg={bgCard}
      border="2px solid"
      borderColor={borderColorValue}
      cursor="pointer"
      transition="all 0.3s ease"
      _hover={{
        borderColor: currentColors.brand500,
        boxShadow: `0 0 20px ${currentColors.brand500}40`,
      }}
      onClick={handleClick}
    >
      <VStack spacing="12px" align="stretch">
        {/* Camera Name - Bold */}
        <HStack justify="space-between" align="center">
          <Text fontWeight="700" color={textColor} fontSize="md">
            {camera.camera_name}
          </Text>
          {loading && <Spinner size="sm" color={currentColors.brand500} />}
        </HStack>

        {/* Last Checked - Timestamp only */}
        {healthData?.latest_check?.timestamp && (
          <Text fontSize="xs" color={textSecondary}>
            Last checked: {new Date(healthData.latest_check.timestamp).toLocaleString('en-GB', {
              hour12: false,
              year: 'numeric',
              month: '2-digit',
              day: '2-digit',
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit'
            }).replace(/(\d{2})\/(\d{2})\/(\d{4}),/, '$3-$2-$1')}
          </Text>
        )}

        {/* Overall Health Status Badge - No label, centered */}
        {healthData?.latest_check && (
          <VStack spacing="6px" align="center" py="8px">
            <Flex align="center" gap="6px" px="12px" py="6px" borderRadius="md" bg={statusColor.bg}>
              {getStatusIcon(overallStatus)}
              <Text fontSize="sm" fontWeight="700" color={statusColor.text}>
                {overallStatus}
              </Text>
            </Flex>
            <Text fontSize="xs" color={textSecondary}>
              {getStatusMessage()}
            </Text>
          </VStack>
        )}

        {/* Click to see details */}
        <Text
          fontSize="xs"
          color={currentColors.brand500}
          fontWeight="600"
          display="flex"
          alignItems="center"
          justifyContent="center"
          gap="4px"
          _hover={{ textDecoration: 'underline' }}
          pt="4px"
        >
          <Icon as={MdExpandMore} />
          Click to see 2-item checklist
        </Text>
      </VStack>
    </Card>
  );
};

// Health Check Modal Component
interface HealthCheckModalProps {
  isOpen: boolean;
  onClose: () => void;
  camera: CameraHealthStatus | null;
  getStatusColor: (status: string) => any;
  getStatusIcon: (status: string) => React.ReactNode;
  onResume?: () => void;
}

const HealthCheckModal: React.FC<HealthCheckModalProps> = ({
  isOpen,
  onClose,
  camera,
  getStatusColor,
  getStatusIcon,
  onResume,
}) => {
  const { currentColors } = useColorTheme();
  const textColor = useColorModeValue('navy.700', 'white');
  const bgModal = useColorModeValue('white', '#111C44');
  const textSecondary = useColorModeValue('gray.600', 'gray.400');
  const [resumeLoading, setResumeLoading] = React.useState(false);
  const toast = useToast();

  // Handle resume processing
  const handleResumeProcessing = async () => {
    if (!camera) return;

    setResumeLoading(true);
    try {
      const response = await fetch('http://localhost:8080/api/qr-detection/resume-processing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_name: camera.camera_name }),
      });

      const result = await response.json();

      if (result.success && result.overall_status === 'OK') {
        // ✅ SUCCESS - Health check passed, processing resumed
        console.log('✅ Processing resumed:', result.message);

        // Show success message
        toast({
          title: '✅ Success!',
          description: `${result.message}\n${result.videos_resumed} videos ready to process`,
          status: 'success',
          duration: 5000,
          isClosable: true,
          position: 'top-right',
        });

        // Refresh cameras and close modal
        onResume?.();
        onClose();

      } else if (!result.success && result.overall_status) {
        // ⚠️ FAILED - Health check still not OK (expected behavior, not an error)
        console.warn('⚠️ Health check still failed:', result.overall_status);

        // Show error message
        toast({
          title: '⚠️ Health Check Failed',
          description: result.message || `Health check still ${result.overall_status}. Please fix the camera and try again.`,
          status: 'warning',
          duration: 6000,
          isClosable: true,
          position: 'top-right',
        });

        // Reload camera health data to show updated status
        // (Keep modal open for user to see updated checklist)
        onResume?.();

      } else {
        // Error case - show message from backend if available
        console.error('❌ Unexpected response:', result);
        const errorMsg = result.message || result.error || 'Failed to resume processing';
        toast({
          title: '❌ Error',
          description: errorMsg,
          status: 'error',
          duration: 5000,
          isClosable: true,
          position: 'top-right',
        });
      }
    } catch (error) {
      console.error('Error resuming processing:', error);
      toast({
        title: '❌ Network Error',
        description: 'Failed to connect to server. Please check your connection and try again.',
        status: 'error',
        duration: 5000,
        isClosable: true,
        position: 'top-right',
      });
    } finally {
      setResumeLoading(false);
    }
  };

  if (!camera) return null;

  const statusColor = getStatusColor(camera.overall_status);
  const overallRate = camera.overall_rate_pct || 0;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg" isCentered>
      <ModalOverlay backdropFilter="blur(4px)" />
      <ModalContent bg={bgModal}>
        <ModalHeader>
          <HStack spacing="12px">
            {getStatusIcon(camera.overall_status) && (
              <Box color={statusColor.bg}>{getStatusIcon(camera.overall_status)}</Box>
            )}
            <Box>
              <Text color={textColor}>{camera.camera_name} Health Check</Text>
              <Text fontSize="sm" color={textSecondary}>
                {camera.last_check
                  ? `Last checked: ${new Date(camera.last_check).toLocaleString()}`
                  : '✓ Baseline ready - No health check history yet'}
              </Text>
            </Box>
          </HStack>
        </ModalHeader>
        <ModalCloseButton />

        <ModalBody>
          <VStack spacing="20px" align="stretch">
            {/* Checklist Items */}
            <Box>
              <Text fontWeight="700" color={textColor} mb="12px">
                🔍 2-Item Health Checklist
              </Text>

              <VStack spacing="12px" align="stretch">
                {camera.items && camera.items.length > 0 ? (
                  camera.items.map((item, idx) => (
                    <ChecklistItem
                      key={idx}
                      item={item}
                      getStatusColor={getStatusColor}
                      getStatusIcon={getStatusIcon}
                    />
                  ))
                ) : (
                  <Text color={textSecondary} fontSize="sm">
                    No health check data available yet.
                  </Text>
                )}
              </VStack>
            </Box>

            {/* Go to Step 4 Configuration Button */}
            <Divider />
            <Button
              w="full"
              bg={currentColors.brand500}
              color="white"
              fontWeight="600"
              _hover={{ opacity: 0.8 }}
              onClick={() => {
                onClose();
                window.location.href = '/?config=camera&step=4';
              }}
              size="md"
            >
              Go to Step 4: Packing Area Configuration
            </Button>

            {/* Resume Button - Show only for CRITICAL status */}
            {camera.overall_status === 'CRITICAL' && (
              <Box
                p="16px"
                bg="red.50"
                borderRadius="lg"
                border="2px solid"
                borderColor="red.200"
              >
                <Text color="red.700" fontWeight="600" mb="12px" fontSize="md">
                  🛑 Processing Paused - Camera CRITICAL
                </Text>
                <Text color="red.600" fontSize="sm" mb="12px">
                  Processing has been paused due to critical camera health issues. Please fix the camera and click the button below to resume.
                </Text>
                <Button
                  w="full"
                  bg="green.500"
                  color="white"
                  fontWeight="600"
                  _hover={{ bg: 'green.600' }}
                  isLoading={resumeLoading}
                  onClick={handleResumeProcessing}
                  size="lg"
                  leftIcon={<MdCheck />}
                >
                  ✅ Fixed - Resume Processing
                </Button>
              </Box>
            )}
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

// Individual Checklist Item Component
interface ChecklistItemProps {
  item: HealthCheckItem;
  getStatusColor: (status: string) => any;
  getStatusIcon: (status: string) => React.ReactNode;
}

const ChecklistItem: React.FC<ChecklistItemProps> = ({
  item,
  getStatusColor,
  getStatusIcon,
}) => {
  const textColor = useColorModeValue('navy.700', 'white');
  const statusColor = getStatusColor(item.status);
  const bgItem = useColorModeValue('gray.50', '#1a202c');
  const textSecondary = useColorModeValue('gray.600', 'gray.400');

  return (
    <Box
      p="12px"
      bg={bgItem}
      borderLeft="4px solid"
      borderColor={statusColor.bg}
      borderRadius="md"
    >
      <VStack align="flex-start" spacing="6px">
        <HStack align="flex-start" spacing="8px">
          {getStatusIcon(item.status) && (
            <Box color={statusColor.bg} mt="2px" flexShrink={0}>
              {getStatusIcon(item.status)}
            </Box>
          )}
          <Text fontWeight="600" color={textColor} fontSize="md">
            {item.name}
          </Text>
        </HStack>
        {item.current_value !== undefined && (
          <Text fontSize="sm" color={textSecondary} ml="28px">
            Current: {item.current_value}
            {item.threshold && ` (Threshold: ${item.threshold})`}
          </Text>
        )}
        {item.action && (
          <Text fontSize="sm" color={statusColor.bg} fontWeight="600" ml="28px">
            💡 {item.action}
          </Text>
        )}
      </VStack>
    </Box>
  );
};

export default CameraHealthPage;
