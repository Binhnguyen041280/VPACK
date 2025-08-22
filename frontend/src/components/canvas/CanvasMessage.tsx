'use client';

import {
  Box,
  Flex,
  Text,
  Button,
  Icon,
  VStack,
  HStack,
  Divider,
  useColorModeValue
} from '@chakra-ui/react';
import { MdAutoAwesome, MdVideoLibrary, MdCamera } from 'react-icons/md';
import { useColorTheme } from '@/contexts/ColorThemeContext';

export default function CanvasMessage() {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const cardBg = useColorModeValue('gray.50', 'navy.700');
  const hoverBg = useColorModeValue('gray.100', 'whiteAlpha.100');
  const hoverBg2 = useColorModeValue('gray.50', 'whiteAlpha.100');

  return (
    <Flex w="100%" mb="24px" align="flex-start">
      {/* Bot Avatar */}
      <Flex
        borderRadius="full"
        justify="center"
        align="center"
        bg={currentColors.gradient}
        me="12px"
        h="32px"
        minH="32px"
        minW="32px"
        flexShrink={0}
      >
        <Icon
          as={MdAutoAwesome}
          width="16px"
          height="16px"
          color="white"
        />
      </Flex>
      
      {/* Canvas Content */}
      <Box
        bg={bgColor}
        borderRadius="16px"
        p="20px"
        maxW={{ base: '95%', md: '85%', xl: '75%' }}
        w="100%"
        border="1px solid"
        borderColor={borderColor}
        boxShadow="0px 4px 12px rgba(112, 144, 176, 0.08)"
      >
        {/* Header */}
        <Flex justify="space-between" align="center" mb="20px">
          <Text fontSize="lg" fontWeight="700" color={textColor}>
            🔧 V.PACK Configuration
          </Text>
        </Flex>

        <VStack spacing="16px" align="stretch">
          {/* Company Information Section - Current Step */}
          <Box>
            <HStack mb="12px">
              <Text fontSize="md" fontWeight="600" color={textColor}>
                🏢 Step 1: Company Information
              </Text>
            </HStack>
            
            <Box
              bg={cardBg}
              p="16px"
              borderRadius="12px"
              textAlign="center"
            >
              <Text fontSize="sm" fontWeight="600" color={textColor} mb="8px">
                Company/Brand Name
              </Text>
              <Text fontSize="xs" color="gray.500" mb="12px">
                Type your company name in the chat below and click Submit
              </Text>
              <Text fontSize="xs" color="gray.400" fontStyle="italic">
                Example: "TechCorp Manufacturing"
              </Text>
            </Box>
          </Box>

          <Divider />

          {/* Status Summary */}
          <Box
            bg={cardBg}
            p="16px"
            borderRadius="12px"
            textAlign="center"
          >
            <Text fontSize="sm" fontWeight="600" color={textColor} mb="4px">
              ⏳ Waiting for Company Name
            </Text>
            <Text fontSize="xs" color="gray.500">
              Please enter your company name in the chat and click Submit
            </Text>
          </Box>
        </VStack>
      </Box>
    </Flex>
  );
}