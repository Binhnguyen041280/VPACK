import React, { useState, useEffect } from 'react';
import { Box, Flex, Text, useColorModeValue, Icon } from '@chakra-ui/react';
import { MdAutoAwesome } from 'react-icons/md';
import Card from '@/components/card/Card';
import { useColorTheme } from '@/contexts/ColorThemeContext';

const WelcomeMessage = () => {
  const [isVisible, setIsVisible] = useState<boolean>(false);
  const { currentColors } = useColorTheme();
  
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const bubbleBg = useColorModeValue('gray.50', 'whiteAlpha.100');

  useEffect(() => {
    const hasSeenWelcome = localStorage.getItem('hasSeenWelcome');
    if (!hasSeenWelcome) {
      setIsVisible(true);
      // Auto-mark as seen after showing (no close button)
      localStorage.setItem('hasSeenWelcome', 'true');
    }
  }, []);

  if (!isVisible) return null;

  return (
    <Flex w="100%" mb="24px" align="flex-start">
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
      <Box
        bg={bubbleBg}
        borderRadius="16px"
        px="16px"
        py="12px"
        maxW="75%"
        color={textColor}
        fontSize={{ base: 'sm', md: 'md' }}
        lineHeight={{ base: '20px', md: '22px' }}
        fontWeight="400"
      >
        <Text mb="12px" fontSize="md" fontWeight="600">
          Welcome to V.PACK! 🚀
        </Text>
        <Text mb="10px" fontSize="sm">
          The smart video monitoring solution that lets you:
        </Text>
        <Box mb="10px" fontSize="sm">
          <Text mb="4px">• Automatically detect packaging events—no manual trigger needed</Text>
          <Text mb="4px">• Support multiple sources (Local, Google Drive)</Text>
          <Text mb="4px">• Run 24/7 seamlessly in the background</Text>
          <Text mb="4px">• Generate reports & extract events with high accuracy</Text>
        </Box>
        <Text fontSize="sm" fontWeight="500">
          👉 Sign up now or enter your Gmail to get started!
        </Text>
      </Box>
    </Flex>
  );
};

export default WelcomeMessage;