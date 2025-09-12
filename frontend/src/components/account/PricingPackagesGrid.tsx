'use client';

import React from 'react';
import {
  SimpleGrid,
  VStack,
  HStack,
  Text,
  Button,
  Badge,
  List,
  ListItem,
  ListIcon,
  useColorModeValue,
  Box
} from '@chakra-ui/react';
import { MdCheck } from 'react-icons/md';

import Card from '@/components/card/Card';
import IconBox from '@/components/icons/IconBox';
import { PaymentService } from '@/services/paymentService';
import { PricingPackage, LicenseInfo } from '@/types/account';

interface PricingPackagesGridProps {
  packages: Record<string, PricingPackage>;
  currentLicense?: LicenseInfo | null;
  onPackageSelect: (packageCode: string) => void;
}

const PricingPackagesGrid: React.FC<PricingPackagesGridProps> = ({
  packages,
  currentLicense,
  onPackageSelect
}) => {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const textColor = useColorModeValue('gray.800', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  
  // Order packages for display
  const packageOrder = ['personal_1y', 'personal_1m', 'business_1y', 'business_1m', 'trial_24h'];
  const orderedPackages = packageOrder
    .map(code => ({ code, ...packages[code] }))
    .filter(pkg => pkg.name); // Only include packages that exist

  // Check if user can purchase/upgrade to this package
  const canPurchasePackage = (packageCode: string) => {
    if (!currentLicense) return true; // No license, can purchase anything
    return currentLicense.package_type !== packageCode; // Can't purchase same package
  };

  // Get button text based on current license and package
  const getButtonText = (packageCode: string) => {
    if (!currentLicense) return '💳 PURCHASE';
    if (currentLicense.package_type === packageCode) return '✅ CURRENT PLAN';
    
    // Simple upgrade logic
    const upgrades = {
      'trial_24h': 'personal_1m',
      'personal_1m': 'personal_1y',
      'personal_1y': 'business_1y',
      'business_1m': 'business_1y'
    };
    
    const currentOrder = packageOrder.indexOf(currentLicense.package_type);
    const targetOrder = packageOrder.indexOf(packageCode);
    
    if (targetOrder > currentOrder) return '🚀 UPGRADE';
    if (targetOrder < currentOrder) return '📦 DOWNGRADE';
    return '🔄 SWITCH';
  };

  // Get button color scheme
  const getButtonColorScheme = (packageCode: string) => {
    if (!currentLicense) return 'blue';
    if (currentLicense.package_type === packageCode) return 'green';
    
    const currentOrder = packageOrder.indexOf(currentLicense.package_type);
    const targetOrder = packageOrder.indexOf(packageCode);
    
    if (targetOrder > currentOrder) return 'purple'; // Upgrade
    return 'blue'; // Downgrade or switch
  };

  if (Object.keys(packages).length === 0) {
    return (
      <Card p={8} textAlign="center">
        <Text color={secondaryText}>No pricing packages available at the moment.</Text>
      </Card>
    );
  }

  return (
    <VStack align="stretch" spacing={6}>
      <Text fontSize="2xl" fontWeight="bold" textAlign="center" color={textColor}>
        💰 Choose Your Plan
      </Text>
      
      <SimpleGrid columns={{ base: 1, sm: 2, md: 3, lg: 5 }} spacing={3}>
        {orderedPackages.map((pkg) => {
          const badge = PaymentService.getBadgeForPackage(pkg.code);
          const isCurrentPlan = currentLicense?.package_type === pkg.code;
          const canPurchase = canPurchasePackage(pkg.code);
          
          return (
            <Card 
              key={pkg.code}
              p={4} 
              position="relative"
              bg={bgColor}
              borderColor={isCurrentPlan ? 'green.500' : borderColor}
              borderWidth={isCurrentPlan ? '2px' : '1px'}
              _hover={canPurchase ? { 
                transform: 'translateY(-4px)', 
                shadow: 'xl',
                borderColor: 'blue.300'
              } : {}}
              transition="all 0.3s ease"
              minH="400px"
              display="flex"
              flexDirection="column"
            >
              {/* Badge */}
              {badge && (
                <Box position="absolute" top="-10px" right="-10px" zIndex={1}>
                  <Badge 
                    colorScheme="orange" 
                    variant="solid" 
                    px={2} 
                    py={1}
                    borderRadius="full"
                    fontSize="xs"
                    fontWeight="bold"
                  >
                    {badge}
                  </Badge>
                </Box>
              )}
              
              {/* Current Plan Badge */}
              {isCurrentPlan && (
                <Box position="absolute" top="-10px" left="-10px" zIndex={1}>
                  <Badge 
                    colorScheme="green" 
                    variant="solid" 
                    px={2} 
                    py={1}
                    borderRadius="full"
                    fontSize="xs"
                  >
                    ✅ ACTIVE
                  </Badge>
                </Box>
              )}

              <VStack align="stretch" spacing={3} h="full" justify="space-between">
                {/* Header Section - Fixed Height */}
                <VStack align="center" spacing={2} minH="60px" justify="center">
                  <Text fontSize="lg" fontWeight="bold" textAlign="center" color={textColor}>
                    {pkg.name}
                  </Text>
                </VStack>

                {/* Price Section - Fixed Height */}
                <VStack spacing={1} minH="80px" justify="center">
                  <HStack align="baseline" justify="center">
                    <Text 
                      fontSize="2xl" 
                      fontWeight="bold" 
                      color="blue.500"
                    >
                      {PaymentService.formatPrice(pkg.price)}
                    </Text>
                  </HStack>
                  
                  {pkg.original_price && pkg.original_price > pkg.price && (
                    <Text 
                      fontSize="sm" 
                      color={secondaryText} 
                      textDecoration="line-through"
                    >
                      {PaymentService.formatPrice(pkg.original_price)}
                    </Text>
                  )}
                  
                  <Text fontSize="sm" color={secondaryText}>
                    /{PaymentService.formatDuration(pkg.duration_days)}
                  </Text>
                </VStack>

                {/* Features Section - Flexible Height */}
                <VStack align="stretch" spacing={2} flex={1} justify="start">
                  {pkg.features && pkg.features.length > 0 && (
                    <List spacing={1} w="full">
                      {pkg.features.map((feature, idx) => (
                        <ListItem key={idx} fontSize="sm">
                          <ListIcon as={MdCheck} color="green.500" />
                          {feature}
                        </ListItem>
                      ))}
                    </List>
                  )}
                  
                  {pkg.description && (
                    <Text fontSize="xs" color={secondaryText} textAlign="center" mt={2}>
                      {pkg.description}
                    </Text>
                  )}
                </VStack>

                {/* Button Section - Fixed Height */}
                <VStack spacing={2} minH="60px" justify="end">
                  <Button
                    colorScheme={getButtonColorScheme(pkg.code)}
                    size="md"
                    w="full"
                    onClick={() => onPackageSelect(pkg.code)}
                    isDisabled={!canPurchase}
                    variant={isCurrentPlan ? 'outline' : 'solid'}
                  >
                    {getButtonText(pkg.code)}
                  </Button>
                </VStack>
              </VStack>
            </Card>
          );
        })}
      </SimpleGrid>
      
      {/* Additional Information */}
      <Card p={4} bg="blue.50" borderColor="blue.200">
        <VStack spacing={2} align="center">
          <Text fontSize="sm" color="blue.800" fontWeight="medium" textAlign="center">
            💳 Secure Payment via PayOS • 📧 License key delivered to email • 🔒 30-day satisfaction guarantee
          </Text>
          <Text fontSize="xs" color="blue.600" textAlign="center">
            Need help choosing? Contact support: alanngaongo@gmail.com
          </Text>
        </VStack>
      </Card>
    </VStack>
  );
};

export default PricingPackagesGrid;