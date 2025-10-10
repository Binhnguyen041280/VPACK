'use client';

/**
 * License Guard Component - ChatGPT UI Style
 * Created: 2025-10-09
 * Purpose: UI-level protection for licensed features (Trace page)
 * Style: ChatGPT theme with navy background and purple accents
 */

import React, { ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import {
  Box,
  VStack,
  Heading,
  Text,
  Button,
  Spinner,
  useColorModeValue
} from '@chakra-ui/react';
import { useLicense } from '@/contexts/LicenseContext';

interface LicenseGuardProps {
  children: ReactNode;
  feature?: string;
}

/**
 * License Guard Component - ChatGPT Style
 *
 * Wraps protected features and shows upgrade prompt if license invalid
 */
export const LicenseGuard: React.FC<LicenseGuardProps> = ({
  children,
  feature = 'this feature'
}) => {
  const router = useRouter();
  const { license, refreshLicense } = useLicense();

  // ChatGPT theme colors
  const bgColor = 'var(--chatgpt-navy-dark)';
  const cardBg = 'var(--chatgpt-navy-medium)';
  const borderColor = 'var(--chatgpt-gray-600)';
  const textColor = 'var(--chatgpt-white)';
  const secondaryText = 'var(--chatgpt-gray-400)';
  const accentColor = 'var(--chatgpt-purple-primary)';

  // Loading state
  if (license.isLoading) {
    return (
      <Box
        className="chatgpt-theme"
        display="flex"
        alignItems="center"
        justifyContent="center"
        minH="100vh"
        bg={bgColor}
      >
        <VStack spacing={4}>
          <Box className="chatgpt-pulse">
            <Spinner size="xl" color={accentColor} thickness="4px" />
          </Box>
          <Text color={secondaryText} fontFamily="var(--chatgpt-font-family)">
            Checking license...
          </Text>
        </VStack>
      </Box>
    );
  }

  // Error state
  if (license.error) {
    return (
      <Box
        className="chatgpt-theme"
        minH="100vh"
        bg={bgColor}
        p={8}
        display="flex"
        alignItems="center"
        justifyContent="center"
      >
        <Box
          className="chatgpt-card chatgpt-animate-fade-in"
          maxW="500px"
          p={8}
          bg={cardBg}
          borderRadius="var(--chatgpt-radius-lg)"
          border={`1px solid ${borderColor}`}
        >
          <VStack spacing={6}>
            <Box fontSize="4xl">⚠️</Box>
            <Heading size="md" color={textColor} fontFamily="var(--chatgpt-font-family)">
              License Check Failed
            </Heading>
            <Text color={secondaryText} textAlign="center" fontFamily="var(--chatgpt-font-family)">
              {license.error}
            </Text>
            <Button
              className="chatgpt-button-primary"
              onClick={() => refreshLicense()}
              w="full"
            >
              Retry
            </Button>
          </VStack>
        </Box>
      </Box>
    );
  }

  // Valid license - render children
  if (license.hasValidLicense) {
    return <>{children}</>;
  }

  // Invalid license - show ChatGPT-style upgrade prompt
  return (
    <Box
      className="chatgpt-theme"
      minH="100vh"
      bg={bgColor}
      p={8}
      display="flex"
      alignItems="center"
      justifyContent="center"
    >
      <Box maxW="600px" w="full">
        {/* Main Card */}
        <Box
          className="chatgpt-card chatgpt-animate-slide-up"
          bg={cardBg}
          borderRadius="var(--chatgpt-radius-xl)"
          border={`1px solid ${borderColor}`}
          p={10}
          boxShadow="var(--chatgpt-shadow-xl)"
        >
          <VStack spacing={8} align="center">
            {/* Lock Icon with Glow */}
            <Box
              fontSize="6xl"
              className="chatgpt-hover-glow"
              filter="drop-shadow(0 0 20px var(--chatgpt-purple-subtle))"
            >
              🔒
            </Box>

            {/* Title */}
            <VStack spacing={3} textAlign="center">
              <Heading
                size="xl"
                color={textColor}
                fontFamily="var(--chatgpt-font-family)"
                fontWeight="var(--chatgpt-font-weight-bold)"
              >
                {license.isExpired ? 'License Expired' : 'License Required'}
              </Heading>

              {/* Description */}
              <Text
                color={secondaryText}
                fontSize="md"
                fontFamily="var(--chatgpt-font-family)"
                maxW="450px"
                lineHeight="1.6"
              >
                {license.isExpired
                  ? `Your license has expired ${Math.abs(license.daysRemaining || 0)} days ago. Please activate a valid license to continue using ${feature}.`
                  : `Access to ${feature} requires an active license. Please activate a license to continue.`}
              </Text>
            </VStack>

            {/* Features List - ChatGPT Card Style */}
            <Box
              w="full"
              bg="var(--chatgpt-navy-dark)"
              borderRadius="var(--chatgpt-radius-lg)"
              p={6}
              border={`1px solid ${borderColor}`}
            >
              <Text
                fontWeight="var(--chatgpt-font-weight-semibold)"
                mb={4}
                color={textColor}
                fontFamily="var(--chatgpt-font-family)"
              >
                ✨ With a license you get:
              </Text>
              <VStack align="start" spacing={3} color={secondaryText} fontFamily="var(--chatgpt-font-family)">
                <Text>✓ Full access to Trace features</Text>
                <Text>✓ Query and filter events by tracking code</Text>
                <Text>✓ Video cutting and processing</Text>
                <Text>✓ Export and analysis tools</Text>
              </VStack>
            </Box>

            {/* Action Button - ChatGPT Style */}
            <Button
              className="chatgpt-button-primary chatgpt-hover-lift"
              onClick={() => router.push('/plan')}
              w="full"
              size="lg"
              h="54px"
              fontSize="md"
              fontWeight="var(--chatgpt-font-weight-medium)"
            >
              Go to Plan
            </Button>
          </VStack>
        </Box>
      </Box>
    </Box>
  );
};

export default LicenseGuard;
