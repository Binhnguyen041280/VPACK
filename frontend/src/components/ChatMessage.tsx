import React from 'react';
import { Box, Flex, Text, useColorModeValue, Icon } from '@chakra-ui/react';
import { MdAutoAwesome, MdPerson } from 'react-icons/md';
import { useColorTheme } from '@/contexts/ColorThemeContext';

interface ChatMessageProps {
  content: string;
  type: 'user' | 'bot';
  timestamp: Date;
}

const ChatMessage = ({ content, type, timestamp }: ChatMessageProps) => {
  const { currentColors } = useColorTheme();
  const textColor = useColorModeValue('navy.700', 'white');
  const userBubbleBg = useColorModeValue(currentColors.brand500, currentColors.brand400);
  const botBubbleBg = useColorModeValue('gray.50', 'whiteAlpha.100');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');

  if (type === 'user') {
    return (
      <Flex w="100%" mb="16px" justify="flex-end" align="flex-start">
        <Box
          bg={userBubbleBg}
          color="white"
          borderRadius="16px"
          px="16px"
          py="12px"
          maxW="75%"
          mr="12px"
          fontSize={{ base: 'sm', md: 'md' }}
          lineHeight={{ base: '20px', md: '22px' }}
          fontWeight="400"
        >
          <Text whiteSpace="pre-wrap">{content}</Text>
        </Box>
        <Flex
          borderRadius="full"
          justify="center"
          align="center"
          bg="transparent"
          border="1px solid"
          borderColor={borderColor}
          h="32px"
          minH="32px"
          minW="32px"
          flexShrink={0}
        >
          <Icon
            as={MdPerson}
            width="16px"
            height="16px"
            color={textColor}
          />
        </Flex>
      </Flex>
    );
  }

  return (
    <Flex w="100%" mb="16px" align="flex-start">
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
        bg={botBubbleBg}
        borderRadius="16px"
        px="16px"
        py="12px"
        maxW="75%"
        color={textColor}
        fontSize={{ base: 'sm', md: 'md' }}
        lineHeight={{ base: '20px', md: '22px' }}
        fontWeight="400"
      >
        <Text whiteSpace="pre-wrap">{content}</Text>
      </Box>
    </Flex>
  );
};

export default ChatMessage;