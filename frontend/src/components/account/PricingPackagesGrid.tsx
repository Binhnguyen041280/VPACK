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
  Box,
  Flex
} from '@chakra-ui/react';
import { MdCheck } from 'react-icons/md';
import { useColorTheme } from '@/contexts/ColorThemeContext';

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
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const textColor = useColorModeValue('gray.800', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');

  // Get all packages directly from props, filter out trials, and sort by price
  const orderedPackages = Object.values(packages)
    .filter(pkg => pkg.price > 0 && !pkg.code.includes('trial'))
    .sort((a, b) => a.price - b.price);

  // Check if user can purchase/upgrade to this package
  const canPurchasePackage = (packageCode: string) => {
    // Allow purchase of any package, even if currently active
    // User can renew/extend expired licenses or upgrade/downgrade plans
    return true;
  };

  // Get button text based on current license and package
  const getButtonText = (packageCode: string) => {
    if (!currentLicense) return '💳 PURCHASE';

    const isSamePlan = currentLicense.package_type === packageCode;

    // Calculate if expired based on expires_at
    const isExpired = currentLicense.expires_at
      ? new Date(currentLicense.expires_at) < new Date()
      : false;

    // If same plan and NOT expired, show as current
    if (isSamePlan && !isExpired) return '✅ CURRENT PLAN';

    // If same plan but EXPIRED, allow renew
    if (isSamePlan && isExpired) return '🔄 RENEW';

    // Different plan - upgrade/downgrade logic based on price
    const currentPkg = packages[currentLicense.package_type];
    const targetPkg = packages[packageCode];

    // If we can't find package details, default to Switch
    if (!currentPkg || !targetPkg) return '🔄 SWITCH';

    if (targetPkg.price > currentPkg.price) return '🚀 UPGRADE';
    if (targetPkg.price < currentPkg.price) return '📦 DOWNGRADE';
    return '🔄 SWITCH';
  };

  // Get button color scheme
  const getButtonColorScheme = (packageCode: string) => {
    if (!currentLicense) return 'blue';

    const isSamePlan = currentLicense.package_type === packageCode;

    // Calculate if expired based on expires_at
    const isExpired = currentLicense.expires_at
      ? new Date(currentLicense.expires_at) < new Date()
      : false;

    // Current active plan (not expired)
    if (isSamePlan && !isExpired) return 'green';

    // Expired plan (can renew)
    if (isSamePlan && isExpired) return 'orange';

    // Different plan
    // Different plan
    const currentPkg = packages[currentLicense.package_type];
    const targetPkg = packages[packageCode];

    if (!currentPkg || !targetPkg) return 'blue';

    if (targetPkg.price > currentPkg.price) return 'purple'; // Upgrade
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

      <Flex justify="center" w="full">
        <SimpleGrid
          columns={{ base: 1, md: orderedPackages.length > 2 ? 3 : 2 }}
          spacing={6}
          maxW={orderedPackages.length === 2 ? "800px" : "1200px"}
          w="full"
        >
          {orderedPackages.map((pkg) => {
            const badge = PaymentService.getBadgeForPackage(pkg.code);
            const isCurrentPlan = currentLicense?.package_type === pkg.code;
            const canPurchase = canPurchasePackage(pkg.code);

            return (
              <Card
                key={pkg.code}
                p={6}
                position="relative"
                bg={bgColor}
                borderColor={isCurrentPlan ? 'brand.500' : borderColor}
                borderWidth={isCurrentPlan ? '2px' : '1px'}
                _hover={canPurchase ? {
                  transform: 'translateY(-8px)',
                  shadow: '2xl',
                  borderColor: 'brand.400'
                } : {}}
                transition="all 0.3s ease"
                minH="450px"
                display="flex"
                flexDirection="column"
                borderRadius="20px"
              >
                {/* Badge */}
                {badge && (
                  <Box position="absolute" top="-12px" right="-12px" zIndex={1}>
                    <Badge
                      bg="linear-gradient(135deg, #868CFF 0%, #4318FF 100%)"
                      color="white"
                      variant="solid"
                      px={3}
                      py={1.5}
                      borderRadius="full"
                      fontSize="xs"
                      fontWeight="bold"
                      boxShadow="lg"
                    >
                      {badge}
                    </Badge>
                  </Box>
                )}

                {/* Current Plan Badge */}
                {isCurrentPlan && (
                  <Box position="absolute" top="-12px" left="-12px" zIndex={1}>
                    <Badge
                      colorScheme="green"
                      variant="solid"
                      px={3}
                      py={1.5}
                      borderRadius="full"
                      fontSize="xs"
                      boxShadow="md"
                    >
                      ✅ ACTIVE
                    </Badge>
                  </Box>
                )}

                <VStack align="stretch" spacing={4} h="full" justify="space-between">
                  {/* Header Section */}
                  <VStack align="center" spacing={2} minH="70px" justify="center">
                    <Text fontSize="xl" fontWeight="800" textAlign="center" color={textColor}>
                      {pkg.name}
                    </Text>
                  </VStack>

                  {/* Price Section */}
                  <VStack spacing={1} minH="90px" justify="center" bg={useColorModeValue('gray.50', 'whiteAlpha.50')} borderRadius="xl" py={4}>
                    <HStack align="baseline" justify="center">
                      <Text
                        fontSize="3xl"
                        fontWeight="800"
                        bgGradient="linear(to-r, brand.400, brand.600)"
                        bgClip="text"
                        color="brand.500"
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

                    <Text fontSize="sm" color={secondaryText} fontWeight="500">
                      /{PaymentService.formatDuration(pkg.duration_days)}
                    </Text>
                  </VStack>

                  {/* Features Section */}
                  <VStack align="stretch" spacing={3} flex={1} justify="start" py={4}>
                    {pkg.features && pkg.features.length > 0 && (
                      <List spacing={3} w="full">
                        {pkg.features.map((feature, idx) => (
                          <ListItem key={idx} fontSize="sm" display="flex" alignItems="center">
                            <ListIcon as={MdCheck} color="brand.500" w={5} h={5} />
                            <Text as="span" ml={2}>{feature}</Text>
                          </ListItem>
                        ))}
                      </List>
                    )}

                    {pkg.description && (
                      <Text fontSize="xs" color={secondaryText} textAlign="center" mt={2} fontStyle="italic">
                        {pkg.description}
                      </Text>
                    )}
                  </VStack>

                  {/* Button Section */}
                  <VStack spacing={2} minH="60px" justify="end">
                    <Button
                      bg={isCurrentPlan ? 'transparent' : currentColors.gradient}
                      color={isCurrentPlan ? 'brand.500' : 'white'}
                      border={isCurrentPlan ? '2px solid' : 'none'}
                      borderColor="brand.500"
                      w="180px"
                      h="40px"
                      mx="auto"
                      borderRadius="45px"
                      fontSize="sm"
                      fontWeight="bold"
                      boxShadow="none"
                      _hover={!isCurrentPlan ? {
                        boxShadow: `0px 21px 27px -10px ${currentColors.primary}48 !important`,
                        bg: `${currentColors.gradient} !important`,
                      } : {
                        bg: 'brand.50'
                      }}
                      _focus={{
                        bg: isCurrentPlan ? 'transparent' : currentColors.gradient,
                      }}
                      _active={{
                        bg: isCurrentPlan ? 'transparent' : currentColors.gradient,
                      }}
                      onClick={() => onPackageSelect(pkg.code)}
                      isDisabled={!canPurchase}
                    >
                      {getButtonText(pkg.code)}
                    </Button>
                  </VStack>
                </VStack>
              </Card>
            );
          })}
        </SimpleGrid>
      </Flex>

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