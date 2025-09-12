'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
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
  
  // Core state
  const [packages, setPackages] = useState<Record<string, PricingPackage>>({});
  const [currentLicense, setCurrentLicense] = useState<LicenseInfo | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  
  // UI state
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
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

  // Load initial data
  useEffect(() => {
    const loadInitialData = async () => {
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
  }, []);

  // Handle section toggle
  const handleSectionToggle = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

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
    // Update current license
    setCurrentLicense(licenseData);
    
    // Reset payment flow
    setPaymentFlow({
      currentStep: 'packages',
      isProcessing: false
    });
    
    showNotification('License activated successfully! Redirecting to Trace page...', 'success');
    
    // Redirect to trace page
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

  // Calculate days remaining
  const daysRemaining = currentLicense?.expires_at 
    ? AccountService.getDaysRemaining(currentLicense.expires_at)
    : 0;
    
  const statusColor = AccountService.getStatusColor(daysRemaining);

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
          <AlertTitle>Welcome to your upgraded V_Track!</AlertTitle>
          <AlertDescription>
            Your {currentLicense.package_type} license is now active with all premium features.
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
                {currentLicense ? 
                  `${currentLicense.package_type.replace('_', ' ').toUpperCase()} Plan` : 
                  'No Active License'
                }
              </Text>
              <Text fontSize="sm" color={secondaryText}>
                {currentLicense?.expires_at ? 
                  `${daysRemaining} days left` : 
                  'Start with a plan below'
                }
              </Text>
            </VStack>
          </HStack>
          
          <HStack spacing={2}>
            <Button
              size="sm"
              variant="ghost"
              rightIcon={expandedSection === 'details' ? <MdExpandLess /> : <MdExpandMore />}
              onClick={() => handleSectionToggle('details')}
            >
              📊 Details
            </Button>
            <Button
              size="sm"
              variant="ghost"
              rightIcon={expandedSection === 'account' ? <MdExpandLess /> : <MdExpandMore />}
              onClick={() => handleSectionToggle('account')}
            >
              👤 Account
            </Button>
            <Button
              size="sm"
              variant="ghost"
              rightIcon={expandedSection === 'history' ? <MdExpandLess /> : <MdExpandMore />}
              onClick={() => handleSectionToggle('history')}
            >
              📋 History
            </Button>
          </HStack>
        </Flex>
      </Card>

      {/* Expandable Sections */}
      <Collapse in={expandedSection === 'details'}>
        <Card p={6} bg={bgColor} borderColor={borderColor}>
          <VStack align="stretch" spacing={4}>
            <Text fontSize="lg" fontWeight="bold" color={textColor}>
              📊 License Status Details
            </Text>
            
            {currentLicense ? (
              <>
                <HStack spacing={4}>
                  <IconBox icon="🔑" bg="blue.500" color="white" />
                  <VStack align="start" spacing={1}>
                    <Text fontWeight="medium">{currentLicense.package_type} License</Text>
                    <Text fontSize="sm" color={secondaryText}>
                      Expires: {AccountService.formatDate(currentLicense.expires_at || '')}
                    </Text>
                  </VStack>
                  <Badge colorScheme={statusColor} ml="auto">
                    {currentLicense.is_active ? 'Active' : 'Expired'}
                  </Badge>
                </HStack>
                
                <Box>
                  <Text fontWeight="medium" mb={2}>Current Features:</Text>
                  <Flex wrap="wrap" gap={2}>
                    {currentLicense.features.map((feature, idx) => (
                      <Badge key={idx} colorScheme="green" variant="subtle">
                        ✅ {feature}
                      </Badge>
                    ))}
                  </Flex>
                </Box>
              </>
            ) : (
              <Text color={secondaryText}>No active license found. Choose a plan below to get started.</Text>
            )}
          </VStack>
        </Card>
      </Collapse>

      <Collapse in={expandedSection === 'account'}>
        <Card p={6} bg={bgColor} borderColor={borderColor}>
          <VStack align="stretch" spacing={4}>
            <Text fontSize="lg" fontWeight="bold" color={textColor}>
              👤 Account Information
            </Text>
            
            {userProfile && (
              <HStack spacing={4}>
                <NextAvatar 
                  src={userProfile.avatar}
                  showBorder={true}
                  width={60}
                  height={60}
                />
                <VStack align="start" spacing={1} flex={1}>
                  <Text fontWeight="bold">{userProfile.name}</Text>
                  <Text color={secondaryText}>{userProfile.email}</Text>
                  <HStack spacing={4} mt={2}>
                    <Badge colorScheme={userProfile.google_drive_connected ? 'green' : 'red'}>
                      📱 Google Drive: {userProfile.google_drive_connected ? 'Connected' : 'Disconnected'}
                    </Badge>
                    <Badge colorScheme={userProfile.oauth_session_active ? 'green' : 'red'}>
                      🔐 OAuth: {userProfile.oauth_session_active ? 'Active' : 'Expired'}
                    </Badge>
                  </HStack>
                </VStack>
              </HStack>
            )}
          </VStack>
        </Card>
      </Collapse>

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