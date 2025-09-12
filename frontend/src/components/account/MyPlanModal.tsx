'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  VStack,
  HStack,
  Box,
  Text,
  Button,
  Flex,
  Badge,
  useColorModeValue,
  useToast,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Spinner
} from '@chakra-ui/react';

import Card from '@/components/card/Card';
import { NextAvatar } from '@/components/image/Avatar';

import { PaymentService } from '@/services/paymentService';
import { AccountService } from '@/services/accountService';
import {
  PricingPackage,
  LicenseInfo,
  UserProfile,
  PaymentFlowState,
  NotificationState
} from '@/types/account';

import PricingPackagesGrid from './PricingPackagesGrid';
import LicenseActivationModal from './LicenseActivationModal';

interface MyPlanModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const MyPlanModal: React.FC<MyPlanModalProps> = ({ isOpen, onClose }) => {
  const router = useRouter();
  const toast = useToast();
  
  // Core state
  const [packages, setPackages] = useState<Record<string, PricingPackage>>({});
  const [currentLicense, setCurrentLicense] = useState<LicenseInfo | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  
  // UI state
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Payment flow state
  const [paymentFlow, setPaymentFlow] = useState<PaymentFlowState>({
    currentStep: 'packages',
    isProcessing: false
  });
  
  // Theme colors
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const textColor = useColorModeValue('gray.800', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  
  // Show notification helper
  const showNotification = (message: string, type: NotificationState['type'] = 'info') => {
    toast({
      title: message,
      status: type,
      duration: 5000,
      isClosable: true,
    });
  };

  // Load initial data
  useEffect(() => {
    const loadInitialData = async () => {
      if (!isOpen) return;
      
      setIsLoading(true);
      setError(null);
      
      try {
        // Load in parallel
        const [packagesRes, licenseRes, userRes] = await Promise.allSettled([
          PaymentService.getPackages(),
          PaymentService.getLicenseStatus(),
          AccountService.getUserProfile()
        ]);
        
        // Handle packages
        if (packagesRes.status === 'fulfilled' && packagesRes.value.success) {
          setPackages(packagesRes.value.packages);
        } else {
          console.warn('Failed to load packages:', packagesRes);
        }
        
        // Handle license
        if (licenseRes.status === 'fulfilled' && licenseRes.value.success) {
          setCurrentLicense(licenseRes.value.license || null);
        } else {
          console.warn('Failed to load license:', licenseRes);
        }
        
        // Handle user profile
        if (userRes.status === 'fulfilled') {
          setUserProfile(userRes.value);
        } else {
          console.warn('Failed to load user profile:', userRes);
        }
        
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to load data';
        setError(errorMessage);
        showNotification('Failed to load plan information', 'error');
      } finally {
        setIsLoading(false);
      }
    };
    
    loadInitialData();
  }, [isOpen]);


  // Handle package selection for payment - directly process payment
  const handlePackageSelect = async (packageCode: string) => {
    const selectedPackage = packages[packageCode];
    if (!selectedPackage || !userProfile?.email) {
      showNotification('Missing required information for payment', 'error');
      return;
    }
    
    setPaymentFlow({
      currentStep: 'packages', // Keep on packages view but show processing
      selectedPackage: packageCode,
      isProcessing: true
    });

    try {
      // Create payment directly
      const paymentResult = await PaymentService.createPayment({
        customer_email: userProfile.email,
        package_type: selectedPackage.code,
        provider: 'payos'
      });

      if (!paymentResult.success || !paymentResult.payment_url) {
        throw new Error(paymentResult.error || 'Failed to create payment');
      }

      // Open PayOS popup directly
      PaymentService.openPayOSPopup(
        paymentResult.payment_url,
        (popupResult) => {
          setPaymentFlow({
            currentStep: 'packages',
            isProcessing: false
          });
          
          // Auto-proceed to license activation
          handlePaymentComplete({
            order_code: popupResult.orderCode || `MANUAL_${Date.now()}`,
            package_type: selectedPackage.code,
            email: userProfile.email!
          });
        }
      );

    } catch (error) {
      setPaymentFlow({
        currentStep: 'packages',
        isProcessing: false
      });
      const errorMessage = error instanceof Error ? error.message : 'Payment failed';
      showNotification(errorMessage, 'error');
    }
  };

  // Handle payment completion
  const handlePaymentComplete = (paymentData: { order_code: string; package_type: string; email: string }) => {
    setPaymentFlow({
      currentStep: 'activation',
      selectedPackage: paymentData.package_type,
      paymentData,
      isProcessing: false
    });
    
    showNotification('Payment successful! Please activate your license.', 'success');
  };

  // Handle license activation completion
  const handleActivationComplete = async (licenseData: LicenseInfo) => {
    // Update current license immediately
    setCurrentLicense(licenseData);
    
    // Also refresh license status from API to ensure consistency
    try {
      const licenseStatusRes = await PaymentService.getLicenseStatus();
      if (licenseStatusRes.success && licenseStatusRes.license) {
        setCurrentLicense(licenseStatusRes.license);
        console.log('✅ License status refreshed after activation:', licenseStatusRes.license);
      }
    } catch (error) {
      console.warn('⚠️ Could not refresh license status after activation:', error);
    }
    
    // Reset payment flow
    setPaymentFlow({
      currentStep: 'packages',
      isProcessing: false
    });
    
    showNotification('License activated successfully! Redirecting to Trace page...', 'success');
    
    // Close modal and redirect to trace page
    onClose();
    setTimeout(() => {
      router.push('/trace');
    }, 1000);
  };

  // Handle modal close
  const handleModalClose = () => {
    setPaymentFlow({
      currentStep: 'packages',
      isProcessing: false
    });
  };


  return (
    <>
      <Modal isOpen={isOpen} onClose={onClose} size="4xl">
        <ModalOverlay bg="blackAlpha.600" />
        <ModalContent 
          maxW="90vw" 
          mx={4}
          bg={bgColor}
          borderColor={borderColor}
          borderWidth={1}
        >
          <ModalHeader pr="60px">
            <Flex justify="space-between" align="center" w="full">
              <Text fontSize="lg" fontWeight="semibold">My Plan</Text>
              
              {userProfile && (
                <HStack spacing={3}>
                  <Text fontSize="sm" color={secondaryText}>{userProfile.email}</Text>
                  <Badge colorScheme={userProfile.oauth_session_active ? 'green' : 'red'} size="sm">
                    OAuth: {userProfile.oauth_session_active ? 'Active' : 'Expired'}
                  </Badge>
                </HStack>
              )}
            </Flex>
          </ModalHeader>
          <ModalCloseButton />
          
          <ModalBody pb={4} pt={2}>
            {isLoading ? (
              <Box 
                display="flex" 
                alignItems="center" 
                justifyContent="center" 
                minH="400px"
              >
                <VStack spacing={4}>
                  <Spinner size="xl" />
                  <Text color={secondaryText}>Loading your plan information...</Text>
                </VStack>
              </Box>
            ) : (
              <VStack spacing={4} align="stretch">
                
                {/* Error Alert */}
                {error && (
                  <Alert status="error">
                    <AlertIcon />
                    <AlertTitle>Error loading plan data!</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}
                



                {/* Main Pricing Packages Grid - Always Visible */}
                <PricingPackagesGrid
                  packages={packages}
                  currentLicense={currentLicense}
                  onPackageSelect={handlePackageSelect}
                />
                
              </VStack>
            )}
          </ModalBody>
        </ModalContent>
      </Modal>

      {/* License Activation Modal */}
      <LicenseActivationModal
        isOpen={paymentFlow.currentStep === 'activation'}
        paymentData={paymentFlow.paymentData}
        onClose={handleModalClose}
        onActivationComplete={handleActivationComplete}
      />
    </>
  );
};

export default MyPlanModal;