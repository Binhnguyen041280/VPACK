'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useLicense } from '@/contexts/LicenseContext';
import {
  VStack,
  HStack,
  Box,
  Text,
  Button,
  Flex,
  Badge,
  Collapse,
  useColorModeValue,
  useToast,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Spinner
} from '@chakra-ui/react';
import { MdExpandMore, MdExpandLess } from 'react-icons/md';

import Card from '@/components/card/Card';
import IconBox from '@/components/icons/IconBox';
import { NextAvatar } from '@/components/image/Avatar';

import { PaymentService } from '@/services/paymentService';
import { AccountService } from '@/services/accountService';
import {
  PricingPackage,
  LicenseInfo,
  UserProfile,
  PaymentFlowState,
  NotificationState,
  PaymentStep
} from '@/types/account';

import PricingPackagesGrid from './PricingPackagesGrid';
import PaymentModal from './PaymentModal';
import LicenseActivationModal from './LicenseActivationModal';

const MyPlan: React.FC = () => {
  const router = useRouter();
  const toast = useToast();
  const license = useLicense();

  // Core state
  const [packages, setPackages] = useState<Record<string, PricingPackage>>({});
  const [currentLicense, setCurrentLicense] = useState<LicenseInfo | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);

  // NEW: Trial status state
  const [trialStatus, setTrialStatus] = useState<any>(null);

  // UI state
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Payment flow state
  const [paymentFlow, setPaymentFlow] = useState<PaymentFlowState>({
    currentStep: 'packages',
    isProcessing: false
  });

  // Notification state
  const [notification, setNotification] = useState<NotificationState | null>(null);

  // Theme colors
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const textColor = useColorModeValue('gray.800', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');

  // Show notification helper
  const showNotification = (message: string, type: NotificationState['type'] = 'info') => {
    setNotification({ message, type, timestamp: Date.now() });

    toast({
      title: message,
      status: type,
      duration: 5000,
      isClosable: true,
    });

    setTimeout(() => setNotification(null), 5000);
  };

  // NEW: Get license status for badge display
  const getLicenseStatusBadge = () => {
    // Priority 1: Active paid license
    if (currentLicense?.is_active && currentLicense?.package_type && !currentLicense.is_trial) {
      const packageType = currentLicense.package_type;
      const formattedType = packageType
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());

      return {
        text: `🔑 ${formattedType}`,
        color: "green"
      };
    }

    // Priority 2: Active trial (from license or trial_status)
    if ((currentLicense?.is_trial && currentLicense?.is_active) ||
      (trialStatus?.is_trial && trialStatus?.days_left > 0)) {

      const daysLeft = trialStatus?.days_left ||
        (currentLicense?.expires_at ?
          Math.ceil((new Date(currentLicense.expires_at).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24)) :
          0);

      return {
        text: `🔑 Trial: ${daysLeft}d left`,
        color: daysLeft > 3 ? "blue" : "orange"
      };
    }

    // Priority 3: Expired trial
    if (trialStatus?.status === 'expired' ||
      (currentLicense?.is_trial && !currentLicense?.is_active)) {
      return {
        text: "🔑 Trial Expired",
        color: "red"
      };
    }

    // Priority 4: Expired paid license
    if (currentLicense && !currentLicense.is_active) {
      return {
        text: "🔑 License Expired",
        color: "red"
      };
    }

    // Priority 5: Authentication required (unauthenticated user)
    if (trialStatus?.reason === 'authentication_required' || (!userProfile?.email)) {
      return {
        text: "🔐 Sign Up Required",
        color: "orange"
      };
    }

    // Priority 6: No license, not eligible for trial
    if (trialStatus?.eligible === false) {
      return {
        text: "🔑 Buy License",
        color: "purple"
      };
    }

    // Fallback: No license
    return {
      text: "🔑 No License",
      color: "gray"
    };
  };

  // Load initial data
  useEffect(() => {
    const loadInitialData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Load in parallel - ALWAYS fetch fresh packages from Firestore (SSOT)
        const [packagesRes, licenseRes, userRes] = await Promise.allSettled([
          PaymentService.getUpgradePackages(),  // Changed: Always fetch fresh from CloudFunction/Firestore
          PaymentService.getLicenseStatus(),
          AccountService.getUserProfile()
        ]);

        // Handle packages
        if (packagesRes.status === 'fulfilled' && packagesRes.value.success) {
          setPackages(packagesRes.value.packages);
          console.log('📦 Loaded packages from SSOT:', Object.keys(packagesRes.value.packages));
        } else {
          console.warn('Failed to load packages:', packagesRes);
        }

        // Handle license
        if (licenseRes.status === 'fulfilled' && licenseRes.value.success) {
          const license = licenseRes.value.license;
          setCurrentLicense(license || null);
          if (license && packagesRes.status === 'fulfilled') {
            console.log('🔑 Current license package_type:', license.package_type);
            console.log('📋 Package name lookup:', packagesRes.value.packages?.[license.package_type]?.name);
          }

          // NEW: Capture trial status from enhanced API response
          if (licenseRes.value.trial_status) {
            setTrialStatus(licenseRes.value.trial_status);
          } else {
            setTrialStatus(null);
          }
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
  }, []);

  // Handle package selection for payment
  const handlePackageSelect = (packageCode: string) => {
    const selectedPackage = packages[packageCode];
    if (!selectedPackage) return;

    setPaymentFlow({
      currentStep: 'payment',
      selectedPackage: packageCode,
      isProcessing: false
    });
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
  const handleActivationComplete = (licenseData: LicenseInfo) => {
    // Update current license locally
    setCurrentLicense(licenseData);

    // Reset payment flow
    setPaymentFlow({
      currentStep: 'packages',
      isProcessing: false
    });

    showNotification('License activated successfully! Refreshing license status...', 'success');

    // Trigger license context refresh to sync with backend
    license.refreshLicense();

    // Redirect to trace page after refresh completes
    setTimeout(() => {
      router.push('/trace');
    }, 3000);
  };

  // Handle modal close
  const handleModalClose = () => {
    setPaymentFlow({
      currentStep: 'packages',
      isProcessing: false
    });
  };

  // Format expiry date for display (like Claude style with timezone)
  const formatExpiryDate = (isoDate: string): string => {
    const date = new Date(isoDate);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
      timeZoneName: 'short'  // Adds "GMT+7" or "ICT"
    });
  };

  // Calculate expiry status - FIX: Use timestamp for minute-based licenses
  const isExpired = currentLicense?.expires_at
    ? new Date(currentLicense.expires_at) < new Date()
    : false;

  // Calculate days remaining for display (but use isExpired for logic)
  const daysRemaining = currentLicense?.expires_at
    ? AccountService.getDaysRemaining(currentLicense.expires_at)
    : 0;

  const statusColor = isExpired ? 'red' : (currentLicense ? 'green' : 'gray');

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
          <Text color={secondaryText}>Loading your plan information...</Text>
        </VStack>
      </Box>
    );
  }

  return (
    <VStack spacing={6} align="stretch" w="full">

      {/* Error Alert */}
      {error && (
        <Alert status="error">
          <AlertIcon />
          <AlertTitle>Error loading plan data!</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Success notification for license activation */}
      {paymentFlow.currentStep === 'packages' && currentLicense && daysRemaining > 300 && (
        <Alert status="success">
          <AlertIcon />
          <AlertTitle>Welcome to your upgraded ePACK!</AlertTitle>
          <AlertDescription>
            Your {currentLicense.package_type || 'Unknown'} license is now active with all premium features.
          </AlertDescription>
        </Alert>
      )}

      {/* Quick Status Bar - Always Visible */}
      <Card p={4} bg={bgColor} borderColor={borderColor}>
        <Flex justify="space-between" align="center" wrap="wrap">
          <HStack spacing={4}>
            <IconBox
              icon="🔑"
              bg={`${statusColor}.500`}
              color="white"
              w="40px"
              h="40px"
            />
            <VStack align="start" spacing={1}>
              <Text fontWeight="bold" color={textColor}>
                {currentLicense ? (
                  // Try to get package name from packages object first
                  packages[currentLicense.package_type]?.name ||
                  // Fallback: Handle special cases
                  (currentLicense.package_type === 'trial_14d' ? '14 Days Free Trial' :
                   currentLicense.package_type === 'test_10m' ? '10 Minutes Test' :
                   // Default: Format package type string
                   (currentLicense.package_type || 'Unknown').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) + ' Plan')
                ) : 'No Active License'}
              </Text>
              <Text fontSize="sm" color={!isExpired ? 'green.600' : (currentLicense?.expires_at ? 'red.600' : secondaryText)} fontWeight="500">
                {currentLicense?.expires_at ? (
                  !isExpired ?
                    `✅ Active • Expires ${formatExpiryDate(currentLicense.expires_at)}` :
                    `❌ Expired • ${formatExpiryDate(currentLicense.expires_at)}`
                ) : 'Start with a plan below'}
              </Text>
            </VStack>
          </HStack>

          <HStack spacing={2}>
            {userProfile && userProfile.email ? (
              <Text fontSize="sm" color={secondaryText}>
                📧 {userProfile.email}
              </Text>
            ) : (
              <Text fontSize="sm" color="orange.500">
                🔐 Please sign up to access features
              </Text>
            )}
          </HStack>
        </Flex>
      </Card>

      {/* Main Pricing Packages Grid - Always Visible */}
      <PricingPackagesGrid
        packages={packages}
        currentLicense={currentLicense}
        onPackageSelect={handlePackageSelect}
      />

      {/* Payment Modal */}
      <PaymentModal
        isOpen={paymentFlow.currentStep === 'payment'}
        selectedPackage={paymentFlow.selectedPackage ? packages[paymentFlow.selectedPackage] : null}
        userEmail={userProfile?.email}
        onClose={handleModalClose}
        onPaymentComplete={handlePaymentComplete}
      />

      {/* License Activation Modal */}
      <LicenseActivationModal
        isOpen={paymentFlow.currentStep === 'activation'}
        paymentData={paymentFlow.paymentData}
        onClose={handleModalClose}
        onActivationComplete={handleActivationComplete}
      />

    </VStack>
  );
};

export default MyPlan;