'use client';

import { useState, useRef, useEffect, useContext } from 'react';
import {
  Box,
  Button,
  Flex,
  Icon,
  Img,
  Input,
  Text,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  useColorModeValue,
} from '@chakra-ui/react';
import { MdAutoAwesome, MdAdd, MdAttachFile, MdImage, MdVideoFile } from 'react-icons/md';
import Bg from '../../public/img/chat/bg-image.png';
import { useColorTheme } from '@/contexts/ColorThemeContext';
import ChatMessage from '@/components/ChatMessage';
import { SidebarContext } from '@/contexts/SidebarContext';
import { useRoute } from '@/contexts/RouteContext';

interface Message {
  id: string;
  content: string;
  type: 'user' | 'bot';
  timestamp: Date;
}

export default function TracePage() {
  const [inputCode, setInputCode] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { currentColors } = useColorTheme();
  const { toggleSidebar } = useContext(SidebarContext);
  const { setCurrentRoute } = useRoute();
  
  // Color mode values - ALL at top level to prevent hooks order violation
  const textColor = useColorModeValue('navy.700', 'white');
  const mainBg = useColorModeValue('white', 'navy.900');
  const chatBorderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const chatTextColor = useColorModeValue('navy.700', 'white');
  const placeholderColor = useColorModeValue(
    { color: 'gray.500' },
    { color: 'whiteAlpha.600' },
  );
  const loadingBg = useColorModeValue('gray.50', 'whiteAlpha.100');
  // Menu colors to prevent hooks order violation
  const menuHoverBg = useColorModeValue('gray.50', 'whiteAlpha.100');
  const menuBoxShadow = useColorModeValue(
    '14px 17px 40px 4px rgba(112, 144, 176, 0.18)',
    '0px 41px 75px #081132',
  );
  const menuBg = useColorModeValue('white', 'navy.800');
  const menuItemHoverBg = useColorModeValue('gray.100', 'whiteAlpha.100');

  // Set active route to Trace when component mounts
  useEffect(() => {
    setCurrentRoute('/trace');
  }, [setCurrentRoute]);

  // Auto-scroll to bottom when new message
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading]);

  // Initial welcome message for Trace module
  useEffect(() => {
    const welcomeMessage: Message = {
      id: Date.now().toString(),
      content: `🎉 Welcome to Trace Module!\n\nYour V.PACK system is ready for video processing and monitoring.\n\nYou can now:\n• Upload videos for processing\n• Monitor packaging events\n• Generate trace reports\n• Track system performance\n\nWhat would you like to do?`,
      type: 'bot',
      timestamp: new Date()
    };
    setMessages([welcomeMessage]);
  }, []);

  const handleChange = (Event: any) => {
    setInputCode(Event.target.value);
  };

  const handleSubmit = () => {
    if (!inputCode.trim()) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputCode,
      type: 'user',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);
    setLoading(true);

    // Simple bot response for Trace functionality
    setTimeout(() => {
      const botResponse = getTraceResponse(inputCode);
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: botResponse,
        type: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, botMessage]);
      setLoading(false);
    }, 1000);

    setInputCode('');
  };

  const getTraceResponse = (input: string): string => {
    const lowerInput = input.toLowerCase();
    
    if (lowerInput.includes('video') || lowerInput.includes('upload')) {
      return `📹 Video Processing Available:\n\n• Drag and drop your video files\n• Supported formats: MP4, AVI, MOV\n• Real-time processing status\n• Automatic quality detection\n\nReady to process your videos!`;
    }
    
    if (lowerInput.includes('monitor') || lowerInput.includes('tracking')) {
      return `📊 System Monitoring:\n\n• Real-time packaging events\n• Production line status\n• Quality metrics dashboard\n• Alert notifications\n\nMonitoring is active and running smoothly.`;
    }
    
    if (lowerInput.includes('report') || lowerInput.includes('analytics')) {
      return `📈 Trace Reports:\n\n• Daily production summaries\n• Quality analysis reports\n• Performance metrics\n• Export to PDF/Excel\n\nGenerate your custom reports here.`;
    }
    
    return `✨ V.PACK Trace System:\n\nI can help you with:\n• Video processing and analysis\n• System monitoring and alerts\n• Performance reports and analytics\n• Quality control tracking\n\nWhat specific task would you like to accomplish?`;
  };

  const handleFileUpload = () => {
    console.log('File upload clicked');
  };

  const handleImageUpload = () => {
    console.log('Image upload clicked');
  };

  const handleVideoUpload = () => {
    console.log('Video upload clicked');
  };

  return (
    <Flex
      w="100%"
      direction="column"
      position="relative"
      overflow="hidden"
      h="100vh"
    >
      {/* Background Image - same as main page */}
      <Img
        src={Bg.src}
        position={'absolute'}
        w="350px"
        left="50%"
        top="50%"
        transform={'translate(-50%, -50%)'}
      />
      
      {/* Original Single-Panel Layout - Exact copy from main page */}
      <Flex
        direction="column"
        mx="auto"
        w={{ base: '100%', md: '100%', xl: '100%' }}
        minH="100vh"
        maxW="1000px"
        position="relative"
      >
        {/* Content Area */}
        <Flex direction="column" flex="1" pb="100px" pt="36px" overflow="hidden">
          {/* Main Box */}
          <Flex
            direction="column"
            w="100%"
            mx="auto"
            mb={'auto'}
          >
            {/* Chat Messages History */}
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                content={message.content}
                type={message.type}
                timestamp={message.timestamp}
              />
            ))}
            
            {/* Loading indicator */}
            {loading && (
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
                <Flex
                  bg={loadingBg}
                  borderRadius="16px"
                  px="16px"
                  py="12px"
                  align="center"
                >
                  <Text fontSize="sm" color={textColor}>
                    Typing...
                  </Text>
                </Flex>
              </Flex>
            )}
            
            {/* Scroll anchor */}
            <div ref={messagesEndRef} />
          </Flex>
        </Flex>
        
        {/* Chat Input - Exact same as main page */}
        <Flex
          position="fixed"
          bottom="0"
          left={toggleSidebar ? 'calc(95px + (100vw - 95px - 800px) / 2)' : 'calc(288px + (100vw - 288px - 800px) / 2)'}
          w="800px"
          pt="20px"
          pb="20px"
          bg={mainBg}
          alignItems="center"
          zIndex={10}
          transition="left 0.2s linear"
        >
          <Box position="relative" flex="1" me="10px">
            <Input
              minH="54px"
              h="100%"
              border="1px solid"
              borderColor={chatBorderColor}
              borderRadius="45px"
              p="15px 50px 15px 20px"
              fontSize="sm"
              fontWeight="500"
              _focus={{ borderColor: 'none' }}
              color={chatTextColor}
              _placeholder={placeholderColor}
              placeholder="Ask about video processing, monitoring, or reports..."
              value={inputCode}
              onChange={handleChange}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  handleSubmit();
                }
              }}
            />
            {/* Add Button Menu - Inside Input - Same as main page */}
            <Menu>
              <MenuButton
                as={Button}
                position="absolute"
                right="10px"
                top="50%"
                transform="translateY(-50%)"
                variant="transparent"
                borderRadius="full"
                w="34px"
                h="34px"
                px="0px"
                minW="34px"
                maxW="34px"
                minH="34px"
                maxH="34px"
                justifyContent={'center'}
                alignItems="center"
                flexShrink={0}
                _hover={{ bg: menuHoverBg }}
              >
                <Icon as={MdAdd} width="16px" height="16px" color={chatTextColor} />
              </MenuButton>
              <MenuList
                boxShadow={menuBoxShadow}
                p="10px"
                borderRadius="20px"
                bg={menuBg}
                border="none"
              >
                <MenuItem
                  onClick={handleFileUpload}
                  _hover={{ bg: menuItemHoverBg }}
                  borderRadius="8px"
                  p="10px"
                >
                  <Icon as={MdAttachFile} width="16px" height="16px" me="8px" />
                  <Text fontSize="sm">Add File</Text>
                </MenuItem>
                <MenuItem
                  onClick={handleImageUpload}
                  _hover={{ bg: menuItemHoverBg }}
                  borderRadius="8px"
                  p="10px"
                >
                  <Icon as={MdImage} width="16px" height="16px" me="8px" />
                  <Text fontSize="sm">Add Image</Text>
                </MenuItem>
                <MenuItem
                  onClick={handleVideoUpload}
                  _hover={{ bg: menuItemHoverBg }}
                  borderRadius="8px"
                  p="10px"
                >
                  <Icon as={MdVideoFile} width="16px" height="16px" me="8px" />
                  <Text fontSize="sm">Add Video</Text>
                </MenuItem>
              </MenuList>
            </Menu>
          </Box>

          <Button
            bg={currentColors.gradient}
            color="white"
            py="20px"
            px="16px"
            fontSize="sm"
            borderRadius="45px"
            ms="auto"
            w={{ base: '160px', md: '210px' }}
            h="54px"
            boxShadow="none"
            _hover={{
              boxShadow: `0px 21px 27px -10px ${currentColors.primary}48 !important`,
              bg: `${currentColors.gradient} !important`,
              _disabled: {
                bg: currentColors.gradient,
              },
            }}
            _focus={{
              bg: currentColors.gradient,
            }}
            _active={{
              bg: currentColors.gradient,
            }}
            onClick={handleSubmit}
            isLoading={loading}
          >
            Submit
          </Button>
        </Flex>
      </Flex>
    </Flex>
  );
}