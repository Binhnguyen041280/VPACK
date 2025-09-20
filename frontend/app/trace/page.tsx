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
import TraceHeader from '@/components/trace/TraceHeader';
import {
  formatDateTimeForAPI,
  getCurrentDateTime,
  formatDateTimeForDisplay,
  autoSetDateRange
} from '@/utils/dateTimeHelpers';

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

  // DateTime state for TraceHeader
  const [fromDateTime, setFromDateTime] = useState<string>('');
  const [toDateTime, setToDateTime] = useState<string>('');
  const [defaultDays, setDefaultDays] = useState<number>(7);

  // Camera state
  const [selectedCameras, setSelectedCameras] = useState<string[]>([]);
  const [availableCameras] = useState<string[]>(['Camera01', 'Camera02', 'Camera03']);

  // Header visibility state
  const [isHeaderHidden, setIsHeaderHidden] = useState<boolean>(false);
  const [isHovering, setIsHovering] = useState<boolean>(false);

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

  // Auto-set date range when defaultDays changes
  useEffect(() => {
    const { fromDateTime, toDateTime } = autoSetDateRange(defaultDays);
    setFromDateTime(fromDateTime);
    setToDateTime(toDateTime);
  }, [defaultDays]);

  // Auto-hide header after 3 seconds of no activity
  useEffect(() => {
    const timer = setTimeout(() => {
      if (!isHovering) {
        setIsHeaderHidden(true);
      }
    }, 3000);

    return () => clearTimeout(timer);
  }, [isHovering]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading]);

  // Initial welcome message for Trace module
  useEffect(() => {
    const welcomeMessage: Message = {
      id: Date.now().toString(),
      content: `🎉 Welcome to Trace Module!\n\nYour V.PACK system is ready for event querying and video processing.\n\n✨ Quick Start:\n• Set time range and cameras in the header\n• Enter tracking codes like: TC001, TC002\n• Upload CSV files for bulk queries\n• Process videos for event detection\n\nTry typing "time settings" to see current configuration!`,
      type: 'bot',
      timestamp: new Date()
    };
    setMessages([welcomeMessage]);
  }, []);

  const handleChange = (Event: any) => {
    setInputCode(Event.target.value);
  };

  const handleSubmit = async () => {
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

    try {
      // Get response (now async for tracking codes)
      const botResponse = await getTraceResponse(inputCode);
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: botResponse,
        type: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Error getting response:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `❌ Error processing request: ${error instanceof Error ? error.message : 'Unknown error'}`,
        type: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }

    setInputCode('');
  };

  // Real API call for tracking codes
  const handleTrackingCodes = async (input: string): Promise<string> => {
    try {
      const response = await fetch('http://localhost:8080/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tracking_codes: input.split(',').map(code => code.trim()).filter(code => code.length > 0),
          from_time: fromDateTime ? new Date(fromDateTime).toISOString() : null,
          to_time: toDateTime ? new Date(toDateTime).toISOString() : null,
          timezone: "Asia/Ho_Chi_Minh",
          cameras: selectedCameras.length > 0 ? selectedCameras : [],
          default_days: defaultDays
        })
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      const events = data.events || [];

      if (events.length === 0) {
        return `🔍 Search Results for: ${input}\n\n❌ No events found\n\n📅 Time Range: ${fromDateTime ? new Date(fromDateTime).toLocaleString() : 'Not set'} to ${toDateTime ? new Date(toDateTime).toLocaleString() : 'Not set'}\n📹 Cameras: ${selectedCameras.length > 0 ? selectedCameras.join(', ') : 'All cameras'}`;
      }

      let result = `🔍 Search Results for: ${input}\n\n✅ Found ${events.length} event(s)\n\n`;

      events.forEach((event: any, index: number) => {
        const startTime = new Date(event.packing_time_start).toLocaleString();
        const endTime = new Date(event.packing_time_end).toLocaleString();
        const duration = event.duration || 0;
        const trackingCodes = event.tracking_codes_parsed || [];

        result += `📦 Event ${index + 1}:\n`;
        result += `   • Event ID: ${event.event_id}\n`;
        result += `   • Tracking Codes: ${trackingCodes.join(', ')}\n`;
        result += `   • Camera: ${event.camera_name || 'Unknown'}\n`;
        result += `   • Start: ${startTime}\n`;
        result += `   • End: ${endTime}\n`;
        result += `   • Duration: ${duration}s\n`;
        result += `   • Video: ${event.video_file || 'N/A'}\n\n`;
      });

      return result;
    } catch (error) {
      console.error('Error querying tracking codes:', error);
      return `❌ Error searching for tracking codes: ${input}\n\nError: ${error instanceof Error ? error.message : 'Unknown error'}\n\nPlease check if the backend server is running on port 8080.`;
    }
  };

  const getTraceResponse = async (input: string): Promise<string> => {
    const lowerInput = input.toLowerCase();

    // Check if input looks like tracking codes
    if (/^[A-Z0-9\-,\s]+$/.test(input.trim()) && input.length > 2) {
      return await handleTrackingCodes(input);
    }

    if (lowerInput.includes('video') || lowerInput.includes('upload')) {
      return `📹 Video Processing Available:\n\n• Drag and drop your video files\n• Supported formats: MP4, AVI, MOV\n• Real-time processing status\n• Automatic quality detection\n\nReady to process your videos!`;
    }

    if (lowerInput.includes('monitor') || lowerInput.includes('tracking')) {
      return `📊 System Monitoring:\n\n• Real-time packaging events\n• Production line status\n• Quality metrics dashboard\n• Alert notifications\n\nMonitoring is active and running smoothly.`;
    }

    if (lowerInput.includes('report') || lowerInput.includes('analytics')) {
      return `📈 Trace Reports:\n\n• Daily production summaries\n• Quality analysis reports\n• Performance metrics\n• Export to PDF/Excel\n\nGenerate your custom reports here.`;
    }

    if (lowerInput.includes('time') || lowerInput.includes('date')) {
      const displayFrom = fromDateTime ? new Date(fromDateTime).toLocaleString() : 'Not set';
      const displayTo = toDateTime ? new Date(toDateTime).toLocaleString() : 'Not set';

      return `🕐 Time Range Settings:\n\nCurrent configuration:\n• From: ${displayFrom}\n• To: ${displayTo}\n• Default: Last ${defaultDays} days\n• Cameras: ${selectedCameras.length > 0 ? selectedCameras.join(', ') : 'All cameras'}\n\nUse the header controls to adjust your time range and camera selection.`;
    }

    return `✨ V.PACK Trace System:\n\nI can help you with:\n• Video processing and analysis\n• Event query with tracking codes\n• Time range and camera filtering\n• Performance reports and analytics\n\nTry entering tracking codes like: TC01, TC02\nOr ask about "time settings", "video upload", etc.`;
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
    <>
      <Flex
        w="100%"
        direction="column"
        position="relative"
      >
        {/* TraceHeader - Fixed at top with auto-hide */}
        <TraceHeader
          fromDateTime={fromDateTime}
          toDateTime={toDateTime}
          defaultDays={defaultDays}
          onFromDateTimeChange={setFromDateTime}
          onToDateTimeChange={setToDateTime}
          onDefaultDaysChange={setDefaultDays}
          availableCameras={availableCameras}
          selectedCameras={selectedCameras}
          onCameraToggle={setSelectedCameras}
          isHeaderHidden={isHeaderHidden}
          isHovering={isHovering}
          onMouseEnter={() => {
            setIsHovering(true);
            setIsHeaderHidden(false);
          }}
          onMouseLeave={() => setIsHovering(false)}
        />

        {/* Background Image - same as main page */}
        <Img
          src={Bg.src}
          position={'absolute'}
          w="350px"
          left="50%"
          top="50%"
          transform={'translate(-50%, -50%)'}
        />

        {/* Main Content with natural page scroll */}
        <Flex
          direction="column"
          mx="auto"
          w={{ base: '100%', md: '100%', xl: '100%' }}
          maxW="1000px"
          position="relative"
          pt={(!isHeaderHidden || isHovering) ? "80px" : "20px"}
          pb="160px"
          transition="padding-top 0.3s ease-in-out"
        >
          {/* Content Area - Natural scroll */}
          <Box
            position="relative"
            px="20px"
          >
            <Box
              w="100%"
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
            </Box>
          </Box>
        </Flex>
      </Flex>

      {/* Chat Input - Container-based positioning like ChatGPT */}
      <Flex
        position="fixed"
        bottom="0"
        left={toggleSidebar ? "95px" : "288px"}
        right="0"
        h="54px"
        bg={mainBg}
        border="none"
        alignItems="center"
        zIndex={10}
        transition="left 0.2s linear"
        justifyContent="center"
      >
        <Flex
          w="100%"
          maxW="1000px"
          px="20px"
          alignItems="center"
        >
          <Box position="relative" flex="1" me="10px">
            <Input
              minH="54px"
              h="100%"
              border="1px solid"
              borderColor={chatBorderColor}
              borderRadius="full"
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
            borderRadius="full"
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
    </>
  );
}