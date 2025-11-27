'use client';

import React, { useState, useEffect } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  VStack,
  HStack,
  Text,
  Button,
  Input,
  FormControl,
  FormLabel,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  List,
  ListItem,
  ListIcon,
  useColorModeValue,
  Spinner,
  Progress,
  Divider
} from '@chakra-ui/react';
import { MdCheck, MdVpnKey, MdArrowBack } from 'react-icons/md';

import Card from '@/components/card/Card';
import { PaymentService } from '@/services/paymentService';
import { LicenseInfo } from '@/types/account';

interface LicenseActivationModalProps {
  isOpen: boolean;
  paymentData?: {
    order_code: string;
    package_type: string;
    email: string;
  };
  onClose: () => void;
  onActivationComplete: (licenseData: LicenseInfo) => void;
}

const LicenseActivationModal: React.FC<LicenseActivationModalProps> = ({
  isOpen,
  paymentData,
  onClose,
  onActivationComplete
}) => {
  const [licenseKey, setLicenseKey] = useState('');
  const [isActivating, setIsActivating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [redirectCountdown, setRedirectCountdown] = useState(0);

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const textColor = useColorModeValue('gray.800', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setLicenseKey('');
      setError(null);
      setRedirectCountdown(0);
    }
  }, [isOpen]);

  // Handle redirect countdown
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (redirectCountdown > 0) {
      interval = setInterval(() => {
        setRedirectCountdown(prev => {
          if (prev <= 1) {
            // Redirect will be handled by parent component
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [redirectCountdown]);

  const handleActivation = async () => {
    if (!licenseKey.trim()) {
      setError('Please enter a license key');
      return;
    }

    setIsActivating(true);
    setError(null);

    try {
      const result = await PaymentService.activateLicense({
        license_key: licenseKey.trim()
      });

      if (!result.success || !result.valid) {
        throw new Error(result.error || 'License activation failed');
      }

      // Start redirect countdown
      setRedirectCountdown(3);
      
      // Call success handler after short delay
      setTimeout(() => {
        onActivationComplete(result.data!);
      }, 3000);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Activation failed';
      setError(errorMessage);
    } finally {
      setIsActivating(false);
    }
  };

  const handleClose = () => {
    if (!isActivating && redirectCountdown === 0) {
      onClose();
    }
  };

  const handleGoToTrace = () => {
    if (paymentData) {
      // Simulate successful activation for immediate redirect
      const mockLicenseData: LicenseInfo = {
        package_type: paymentData.package_type,
        expires_at: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
        is_active: true,
        features: ['unlimited_cameras', 'advanced_analytics', 'priority_support'],
      };
      onActivationComplete(mockLicenseData);
    }
  };

  if (!paymentData) return null;

  return (
    <Modal isOpen={isOpen} onClose={handleClose} closeOnOverlayClick={false}>
      <ModalOverlay bg="blackAlpha.600" />
      <ModalContent 
        bg={bgColor} 
        borderColor={borderColor} 
        borderWidth={1}
        maxW="95vw"
        maxH="95vh"
        w={{ base: "95vw", sm: "90vw", md: "80vw", lg: "600px" }}
        mx={4}
        my={4}
        overflow="hidden"
      >
        <ModalHeader>
          <Text fontSize="lg" fontWeight="semibold">License Activation</Text>
        </ModalHeader>
        <ModalCloseButton isDisabled={isActivating || redirectCountdown > 0} />
        
        <ModalBody pb={6} overflowY="auto" maxH="calc(95vh - 120px)">
          <VStack spacing={6} align="stretch">

            {/* Simple License Input - Only when not redirecting */}
            {redirectCountdown === 0 && (
              <>
                {/* Simple Success Message */}
                <VStack spacing={4} align="center" textAlign="center">
                  <VStack spacing={2}>
                    <Text fontSize="xl" fontWeight="bold" color={textColor}>
                      Payment Successful!
                    </Text>
                    <Text fontSize="sm" color={secondaryText}>
                      Check your email: <strong>{paymentData?.email}</strong>
                    </Text>
                  </VStack>
                </VStack>

                {/* Simple License Input */}
                <Card p={6} bg={bgColor} borderColor={borderColor}>
                  <VStack align="stretch" spacing={4}>
                    <FormControl>
                      <FormLabel fontSize="lg" fontWeight="bold" color={textColor}>
                        🔑 Enter License Key:
                      </FormLabel>
                      <Input
                        placeholder="VTRACK-XXXXX-XXXXX-XXXXX-XXXXX"
                        value={licenseKey}
                        onChange={(e) => setLicenseKey(e.target.value)}
                        isDisabled={isActivating}
                        fontFamily="mono"
                        fontSize="md"
                        size="lg"
                      />
                    </FormControl>

                    {error && (
                      <Alert status="error" borderRadius="md">
                        <AlertIcon />
                        <Text fontSize="sm">{error}</Text>
                      </Alert>
                    )}
                  </VStack>
                </Card>

                {/* Simple Action Buttons */}
                <HStack spacing={4} justify="stretch">
                  <Button
                    variant="outline"
                    onClick={handleClose}
                    isDisabled={isActivating}
                    flex={1}
                  >
                    Cancel
                  </Button>
                  
                  <Button
                    colorScheme="green"
                    leftIcon={isActivating ? <Spinner size="sm" /> : <MdVpnKey />}
                    onClick={handleActivation}
                    isLoading={isActivating}
                    loadingText="Activating..."
                    isDisabled={!licenseKey.trim()}
                    flex={2}
                  >
                    Activate License
                  </Button>
                </HStack>

                {/* Simple Skip Option */}
                <Button size="sm" variant="link" colorScheme="blue" onClick={handleGoToTrace}>
                  🎯 Skip for now (testing)
                </Button>
              </>
            )}

            {/* Success and Redirect */}
            {redirectCountdown > 0 && (
              <Card p={6} bg="green.50" borderColor="green.200" textAlign="center">
                <VStack spacing={4}>
                  <VStack spacing={2}>
                    <Text fontSize="lg" fontWeight="bold" color="green.800">
                      License Activated Successfully!
                    </Text>
                    <Text fontSize="sm" color="green.700">
                      Your {paymentData.package_type.replace('_', ' ')} plan is now active with all premium features.
                    </Text>
                  </VStack>

                  <VStack spacing={2}>
                    <Text fontSize="sm" color="green.700">
                      🚀 Ready to start using ePACK with your new license!
                    </Text>
                    <Text fontSize="sm" color="green.600">
                      Redirecting to Trace page in {redirectCountdown} seconds...
                    </Text>
                    <Progress 
                      value={(3 - redirectCountdown) / 3 * 100} 
                      colorScheme="green" 
                      size="sm" 
                      w="200px" 
                      borderRadius="full"
                    />
                  </VStack>

                  <Button colorScheme="green" onClick={handleGoToTrace}>
                    🎯 Go to Trace Now
                  </Button>
                </VStack>
              </Card>
            )}


          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default LicenseActivationModal;