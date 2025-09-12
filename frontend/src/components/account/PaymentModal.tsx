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
  Divider,
  List,
  ListItem,
  ListIcon,
  Badge,
  Alert,
  AlertIcon,
  useColorModeValue,
  Spinner
} from '@chakra-ui/react';
import { MdCheck, MdPayment, MdCancel } from 'react-icons/md';

import Card from '@/components/card/Card';
import IconBox from '@/components/icons/IconBox';
import { PaymentService } from '@/services/paymentService';
import { PricingPackage } from '@/types/account';

interface PaymentModalProps {
  isOpen: boolean;
  selectedPackage: PricingPackage | null;
  userEmail?: string;
  onClose: () => void;
  onPaymentComplete: (paymentData: { order_code: string; package_type: string; email: string }) => void;
}

const PaymentModal: React.FC<PaymentModalProps> = ({
  isOpen,
  selectedPackage,
  userEmail,
  onClose,
  onPaymentComplete
}) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const textColor = useColorModeValue('gray.800', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');

  // Auto-start payment when modal opens
  useEffect(() => {
    if (isOpen && selectedPackage && userEmail && !isProcessing) {
      handlePayment();
    }
  }, [isOpen, selectedPackage, userEmail]);

  const handlePayment = async () => {
    if (!selectedPackage || !userEmail) {
      setError('Missing required information for payment');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      // Create payment
      const paymentResult = await PaymentService.createPayment({
        customer_email: userEmail,
        package_type: selectedPackage.code,
        provider: 'payos'
      });

      if (!paymentResult.success || !paymentResult.payment_url) {
        throw new Error(paymentResult.error || 'Failed to create payment');
      }

      // Open PayOS popup
      PaymentService.openPayOSPopup(
        paymentResult.payment_url,
        (popupResult) => {
          setIsProcessing(false);
          
          // Auto-proceed to license activation regardless of popup result
          // User will enter license key if payment was successful
          onPaymentComplete({
            order_code: popupResult.orderCode || `MANUAL_${Date.now()}`,
            package_type: selectedPackage.code,
            email: userEmail
          });
        }
      );

    } catch (error) {
      setIsProcessing(false);
      const errorMessage = error instanceof Error ? error.message : 'Payment failed';
      setError(errorMessage);
    }
  };

  const handleClose = () => {
    if (!isProcessing) {
      setError(null);
      onClose();
    }
  };

  const handleManualComplete = () => {
    // Manual completion for when payment was successful but callback failed
    onPaymentComplete({
      order_code: `MANUAL_${Date.now()}`,
      package_type: selectedPackage!.code,
      email: userEmail!
    });
  };

  if (!selectedPackage) return null;

  const savingsAmount = selectedPackage.original_price && selectedPackage.original_price > selectedPackage.price
    ? selectedPackage.original_price - selectedPackage.price
    : 0;

  const savingsPercent = savingsAmount > 0 
    ? Math.round((savingsAmount / selectedPackage.original_price!) * 100)
    : 0;

  return (
    <Modal isOpen={isOpen} onClose={handleClose} closeOnOverlayClick={!isProcessing}>
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
          <Text fontSize="lg" fontWeight="semibold">Processing Payment</Text>
        </ModalHeader>
        <ModalCloseButton isDisabled={isProcessing} />
        
        <ModalBody pb={6}>
          <VStack spacing={6} align="center" justify="center" minH="300px">
            
            {/* Error State */}
            {error ? (
              <VStack spacing={4} align="center">
                <Alert status="error" borderRadius="md">
                  <AlertIcon />
                  <VStack align="start" spacing={1}>
                    <Text fontSize="sm" fontWeight="medium">Payment Failed</Text>
                    <Text fontSize="sm">{error}</Text>
                  </VStack>
                </Alert>
                
                <VStack spacing={2}>
                  <Button
                    colorScheme="blue"
                    onClick={handlePayment}
                    leftIcon={<MdPayment />}
                    isLoading={isProcessing}
                  >
                    Try Again
                  </Button>
                  
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleClose}
                  >
                    Cancel
                  </Button>
                </VStack>
              </VStack>
            ) : (
              /* Processing State */
              <VStack spacing={6} align="center">
                <Spinner size="xl" color="blue.500" />
                
                <VStack spacing={2} textAlign="center">
                  <Text fontSize="lg" fontWeight="medium">
                    {isProcessing ? 'Opening Payment Gateway...' : 'Preparing Payment...'}
                  </Text>
                  <Text fontSize="sm" color={secondaryText}>
                    {selectedPackage.name} - {PaymentService.formatPrice(selectedPackage.price)}
                  </Text>
                </VStack>
                
                <Alert status="info" borderRadius="md" maxW="400px">
                  <AlertIcon />
                  <VStack align="start" spacing={1}>
                    <Text fontSize="sm" fontWeight="medium">Secure Payment via PayOS</Text>
                    <Text fontSize="xs">
                      A payment window will open shortly. Complete your payment and return here.
                    </Text>
                  </VStack>
                </Alert>
                
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleClose}
                  isDisabled={isProcessing}
                >
                  Cancel
                </Button>
              </VStack>
            )}
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default PaymentModal;