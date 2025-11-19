'use client';

import {
  Box,
  Flex,
  Text,
  Button,
  Icon,
  useColorModeValue,
  VStack,
  HStack,
  Divider
} from '@chakra-ui/react';
import { MdClose, MdSettings, MdVideoLibrary, MdCamera } from 'react-icons/md';
import { useColorTheme } from '@/contexts/ColorThemeContext';

interface EPackCanvasProps {
  isVisible: boolean;
  onClose: () => void;
}

export default function EPackCanvas({ isVisible, onClose }: EPackCanvasProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const cardBg = useColorModeValue('gray.50', 'navy.700');
  const hoverBg = useColorModeValue('gray.100', 'whiteAlpha.100');
  const hoverBg2 = useColorModeValue('gray.50', 'whiteAlpha.100');
  
  if (!isVisible) return null;

  return (
    <Box
      position="fixed"
      right="20px"
      top="50%"
      transform="translateY(-50%)"
      w="400px"
      h="600px"
      bg={bgColor}
      borderRadius="20px"
      boxShadow="0px 18px 40px rgba(112, 144, 176, 0.12)"
      border="1px solid"
      borderColor={borderColor}
      zIndex={1000}
      p="20px"
    >
      {/* Header */}
      <Flex justify="space-between" align="center" mb="20px">
        <Text fontSize="lg" fontWeight="700" color={textColor}>
          ePACK Configuration
        </Text>
        <Button
          variant="ghost"
          size="sm"
          onClick={onClose}
          _hover={{ bg: hoverBg }}
        >
          <Icon as={MdClose} w="20px" h="20px" color={textColor} />
        </Button>
      </Flex>

      <VStack spacing="16px" align="stretch">
        {/* Video Sources Section */}
        <Box>
          <HStack mb="12px">
            <Icon as={MdVideoLibrary} w="18px" h="18px" color={currentColors.brand500} />
            <Text fontSize="md" fontWeight="600" color={textColor}>
              Video Sources
            </Text>
          </HStack>
          
          <VStack spacing="8px" align="stretch">
            <Box
              bg={cardBg}
              p="12px"
              borderRadius="12px"
              cursor="pointer"
              _hover={{ transform: 'translateY(-2px)', transition: 'all 0.2s' }}
            >
              <HStack>
                <Box w="8px" h="8px" bg="green.500" borderRadius="50%" />
                <Text fontSize="sm" fontWeight="500" color={textColor}>
                  Local Files
                </Text>
              </HStack>
              <Text fontSize="xs" color="gray.500" mt="4px">
                Ready to process
              </Text>
            </Box>

            <Box
              bg={cardBg}
              p="12px"
              borderRadius="12px"
              cursor="pointer"
              _hover={{ transform: 'translateY(-2px)', transition: 'all 0.2s' }}
            >
              <HStack>
                <Box w="8px" h="8px" bg="blue.500" borderRadius="50%" />
                <Text fontSize="sm" fontWeight="500" color={textColor}>
                  Google Drive
                </Text>
              </HStack>
              <Text fontSize="xs" color="gray.500" mt="4px">
                Connected
              </Text>
            </Box>

            <Box
              bg={cardBg}
              p="12px"
              borderRadius="12px"
              cursor="pointer"
              _hover={{ transform: 'translateY(-2px)', transition: 'all 0.2s' }}
            >
              <HStack>
                <Box w="8px" h="8px" bg="yellow.500" borderRadius="50%" />
                <Text fontSize="sm" fontWeight="500" color={textColor}>
                  IP Camera
                </Text>
              </HStack>
              <Text fontSize="xs" color="gray.500" mt="4px">
                Not configured
              </Text>
            </Box>
          </VStack>
        </Box>

        <Divider />

        {/* Detection Settings */}
        <Box>
          <HStack mb="12px">
            <Icon as={MdCamera} w="18px" h="18px" color={currentColors.brand500} />
            <Text fontSize="md" fontWeight="600" color={textColor}>
              Detection Settings
            </Text>
          </HStack>
          
          <VStack spacing="8px" align="stretch">
            <Box
              bg={cardBg}
              p="12px"
              borderRadius="12px"
            >
              <Text fontSize="sm" fontWeight="500" color={textColor}>
                Hand Detection
              </Text>
              <Text fontSize="xs" color="green.500" mt="4px">
                ✓ Enabled
              </Text>
            </Box>

            <Box
              bg={cardBg}
              p="12px"
              borderRadius="12px"
            >
              <Text fontSize="sm" fontWeight="500" color={textColor}>
                QR Code Detection
              </Text>
              <Text fontSize="xs" color="green.500" mt="4px">
                ✓ Enabled
              </Text>
            </Box>

            <Box
              bg={cardBg}
              p="12px"
              borderRadius="12px"
            >
              <Text fontSize="sm" fontWeight="500" color={textColor}>
                ROI Configuration
              </Text>
              <Text fontSize="xs" color="gray.500" mt="4px">
                Auto-detect regions
              </Text>
            </Box>
          </VStack>
        </Box>

        <Divider />

        {/* Action Buttons */}
        <VStack spacing="12px">
          <Button
            bg={currentColors.gradient}
            color="white"
            w="100%"
            size="md"
            borderRadius="12px"
            _hover={{
              boxShadow: `0px 21px 27px -10px ${currentColors.primary}48 !important`,
              bg: `${currentColors.gradient} !important`,
            }}
            leftIcon={<Icon as={MdSettings} w="16px" h="16px" />}
          >
            Open Configuration
          </Button>

          <Button
            variant="outline"
            borderColor={borderColor}
            color={textColor}
            w="100%"
            size="md"
            borderRadius="12px"
            _hover={{ bg: hoverBg2 }}
          >
            Start Processing
          </Button>
        </VStack>
      </VStack>
    </Box>
  );
}