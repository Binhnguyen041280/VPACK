'use client';
/*eslint-disable*/

import Link from '@/components/link/Link';
import MessageBoxChat from '@/components/MessageBox';
import WelcomeMessage from '@/components/WelcomeMessage';
import ChatMessage from '@/components/ChatMessage';
import { ChatBody, OpenAIModel } from '@/types/types';
import {
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
import { useEffect, useState, useContext, useRef } from 'react';
import { MdAutoAwesome, MdEdit, MdPerson, MdAdd, MdAttachFile, MdImage, MdVideoFile } from 'react-icons/md';
import Bg from '../public/img/chat/bg-image.png';
import { useColorTheme } from '@/contexts/ColorThemeContext';
import { SidebarContext } from '@/contexts/SidebarContext';
import { useUser } from '@/contexts/UserContext';
import { useRoute } from '@/contexts/RouteContext';
import CanvasMessage from '@/components/canvas/CanvasMessage';

interface Message {
  id: string;
  content: string;
  type: 'user' | 'bot' | 'canvas';
  timestamp: Date;
}

export default function Chat(props: { apiKeyApp: string }) {
  // Input States
  const [inputCode, setInputCode] = useState<string>('');
  // Messages history
  const [messages, setMessages] = useState<Message[]>([]);
  // Loading state
  const [loading, setLoading] = useState<boolean>(false);
  // Gmail OAuth state
  const [gmailLoading, setGmailLoading] = useState<boolean>(false);
  const [gmailError, setGmailError] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [authenticatedUser, setAuthenticatedUser] = useState<string>('');
  // Configuration state
  const [configStep, setConfigStep] = useState<'company' | 'location' | 'video' | 'detection' | 'complete'>('company');
  const [companyName, setCompanyName] = useState<string>('');
  // Submit button text
  const getSubmitButtonText = (): string => {
    if (inputCode.trim() === '') {
      // Empty input - show contextual action
      switch (configStep) {
        case 'company': return 'Continue';
        case 'location': return 'Continue';
        case 'video': return 'Continue';  
        case 'detection': return 'Complete';
        case 'complete': return 'Start';
        default: return 'Continue';
      }
    } else {
      // Has input - show regular submit
      return 'Submit';
    }
  };
  // Scroll ref for auto-scroll
  const messagesEndRef = useRef<HTMLDivElement>(null);
  // OAuth refs
  const popupRef = useRef<Window | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const messageHandlerRef = useRef<((event: MessageEvent) => void) | null>(null);

  // API Key
  // const [apiKey, setApiKey] = useState<string>(apiKeyApp);
  const { currentColors } = useColorTheme();
  const { toggleSidebar } = useContext(SidebarContext);
  const { userInfo, updateUserInfo, refreshUserInfo } = useUser();
  const { setCompanyName: setRouteCompanyName, startAnimation, stopAnimation } = useRoute();

  // Auto-scroll to bottom when new message
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading]);

  // Remove auto-authentication check for clean first-time experience

  // Cleanup OAuth on component unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (messageHandlerRef.current) {
        window.removeEventListener('message', messageHandlerRef.current);
      }
      if (popupRef.current && !popupRef.current.closed) {
        popupRef.current.close();
      }
    };
  }, []);
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const inputColor = useColorModeValue('navy.700', 'white');
  const brandColor = useColorModeValue(currentColors.brand500, 'white');
  const gray = useColorModeValue('gray.500', 'white');
  const textColor = useColorModeValue('navy.700', 'white');
  const loadingBubbleBg = useColorModeValue('gray.50', 'whiteAlpha.100');
  const placeholderColor = useColorModeValue(
    { color: 'gray.500' },
    { color: 'whiteAlpha.600' },
  );
  // Error display colors - must be outside conditional rendering
  const errorBg = useColorModeValue('red.50', 'red.900');
  const errorColor = useColorModeValue('red.700', 'red.200');
  const errorBorderColor = useColorModeValue('red.200', 'red.700');

  // Handle Empty Submit - Universal Confirmation Pattern
  const handleEmptySubmit = (): string => {
    switch (configStep) {
      case 'company':
        // Move to location step
        setConfigStep('location');
        return 'Moving to location setup...\n\nPlease enter your city/location and timezone.\n\nExample: "Ho Chi Minh City, UTC+7"';
      
      case 'location':
        // Move to video sources
        setConfigStep('video');
        return 'Location saved! Moving to video sources setup...\n\nConfiguring video sources...';
      
      case 'video':
        // Move to detection settings
        setConfigStep('detection');
        return 'Video sources configured! Moving to detection settings...\n\nSetting up detection parameters...';
      
      case 'detection':
        // Complete configuration
        setConfigStep('complete');
        return '✅ Configuration completed!\n\nReady to start processing. All systems configured and ready.';
      
      case 'complete':
        return 'Configuration is already complete. Ready to start processing!';
      
      default:
        return 'Continuing to next step...';
    }
  };

  // Handle Edit Commands
  const handleEditCommand = (newValue: string): string => {
    if (!newValue.trim()) {
      return 'Please provide a new value after "edit:"\n\nExample: edit: New Company Name';
    }

    switch (configStep) {
      case 'company':
      case 'location':
        // Edit company name
        setCompanyName(newValue);
        setRouteCompanyName(newValue);
        
        // Stop company name blinking animation since user has set a name
        stopAnimation();
        
        return `✅ Company name updated: "${newValue}"\n\nSidebar updated ✓\n\nTo continue: just click Submit (empty)`;
      
      default:
        return `Edit not available for current step. Current value updated to: "${newValue}"`;
    }
  };

  // Auto-response system
  const getAutoResponse = (userInput: string): string => {
    // Handle Empty Submit (Universal Confirmation Pattern)
    if (userInput.trim() === '') {
      return handleEmptySubmit();
    }
    
    const input = userInput.toLowerCase().trim();
    
    // Handle Edit Pattern
    if (input.startsWith('edit:')) {
      return handleEditCommand(userInput.substring(5).trim());
    }
    
    // Removed "ok" trigger - canvas now auto-appears after OAuth
    
    // Handle company name input when in company step
    if (configStep === 'company' && userInput.trim().length > 0) {
      setCompanyName(userInput.trim());
      setConfigStep('location');
      
      // Update sidebar route name (replaces "Alan_go")
      setRouteCompanyName(userInput.trim());
      
      // Stop company name blinking animation
      stopAnimation();
      
      // Mark user as configured (allow future database operations)
      localStorage.setItem('userConfigured', 'true');
      
      return `✅ Company name saved: "${userInput.trim()}"\n\nNext step: Location and timezone setup...\n\nTo edit: type "edit: NEW COMPANY NAME"\nTo continue: just click Submit (empty)`;
    }
    
    if (input.includes('hello') || input.includes('xin chào') || input.includes('hi')) {
      return 'Hello! I\'m your V.PACK assistant. How can I help you today?';
    }
    
    if (input.includes('help') || input.includes('giúp đỡ')) {
      return 'Available commands:\n• Empty Submit - Confirm/Continue current step\n• "edit: NEW VALUE" - Update current field\n• "hello" - Greeting\n• "help" - Show this help\n\nSign in with Gmail to start configuration!';
    }
    
    if (input.includes('config') || input.includes('cấu hình')) {
      return 'Configuration starts automatically after Gmail sign-in. Please sign in with Gmail first.';
    }
    
    // Default response
    return 'Thank you for your message! I\'m learning to respond better. Try typing "help" to see available commands.';
  };

  const handleTranslate = () => {
    // Validation - Allow empty input for Universal Confirmation Pattern
    if (inputCode.length > 500) {
      alert('Message too long. Please enter less than 500 characters.');
      return;
    }

    // Add user message (only if not empty)
    if (inputCode.trim()) {
      const userMessage: Message = {
        id: Date.now().toString(),
        content: inputCode.trim(),
        type: 'user',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, userMessage]);
    }
    setLoading(true);

    // Simulate processing time
    setTimeout(() => {
      // Get auto response - pass original input to detect empty vs content
      const botResponse = getAutoResponse(inputCode);
      
      // Add bot message
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: botResponse,
        type: 'bot',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botMessage]);
      setLoading(false);
    }, 800); // Small delay for realistic feel

    // Clear input
    setInputCode('');
  };
  // -------------- Copy Response --------------
  // const copyToClipboard = (text: string) => {
  //   const el = document.createElement('textarea');
  //   el.value = text;
  //   document.body.appendChild(el);
  //   el.select();
  //   document.execCommand('copy');
  //   document.body.removeChild(el);
  // };

  // *** Initializing apiKey with .env.local value
  // useEffect(() => {
  // ENV file verison
  // const apiKeyENV = process.env.NEXT_PUBLIC_OPENAI_API_KEY
  // if (apiKey === undefined || null) {
  //   setApiKey(apiKeyENV)
  // }
  // }, [])

  const handleChange = (Event: any) => {
    setInputCode(Event.target.value);
  };

  // Gmail OAuth handler
  const handleGmailAuth = async () => {
    if (gmailLoading) {
      console.log('⚠️ Authentication already in progress, skipping...');
      return;
    }

    try {
      setGmailLoading(true);
      setGmailError(null);
      
      console.log('🔐 Starting Gmail authentication...');

      const response = await fetch('http://localhost:8080/api/cloud/gmail-auth', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          action: 'initiate_auth'
        })
      });

      console.log('📡 Response status:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Authentication failed: ${response.status} - ${errorText}`);
      }

      const authData = await response.json();
      console.log('✅ Auth data received:', authData);

      if (!authData.success || !authData.auth_url) {
        throw new Error(authData.message || 'Failed to get authorization URL');
      }

      console.log('🌐 Opening OAuth popup...');
      
      // Close any existing popup
      if (popupRef.current && !popupRef.current.closed) {
        popupRef.current.close();
      }
      
      // Clear any existing intervals/listeners
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (messageHandlerRef.current) {
        window.removeEventListener('message', messageHandlerRef.current);
      }
      
      // Open popup window
      const popup = window.open(
        authData.auth_url,
        'gmail_auth',
        'width=600,height=700,scrollbars=yes,resizable=yes'
      );

      if (!popup) {
        throw new Error('Popup blocked. Please allow popups for this site.');
      }
      
      popupRef.current = popup;

      // Listen for popup completion using message passing
      const handleMessage = async (event: MessageEvent) => {
        // Only accept messages from our OAuth callback
        if (event.origin !== 'http://localhost:8080') {
          return;
        }

        console.log('📨 Received OAuth message:', event.data);

        if (event.data.type === 'GMAIL_AUTH_SUCCESS') {
          // Cleanup listeners and intervals
          if (messageHandlerRef.current) {
            window.removeEventListener('message', messageHandlerRef.current);
            messageHandlerRef.current = null;
          }
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          
          // Close popup
          if (popupRef.current && !popupRef.current.closed) {
            popupRef.current.close();
          }
          popupRef.current = null;
          
          setGmailLoading(false);
          
          console.log('✅ Authentication successful:', event.data.user_email);
          
          // Update authentication state AND sidebar with user info
          setIsAuthenticated(true);
          setAuthenticatedUser(event.data.user_email);
          
          // Update sidebar with authenticated user info immediately
          updateUserInfo({
            name: event.data.user_info?.name || event.data.user_email.split('@')[0],
            email: event.data.user_email,
            avatar: event.data.user_info?.photo_url || '/img/avatars/avatar4.png',
            authenticated: true
          });
          
          // Add success message to chat
          const successMessage: Message = {
            id: Date.now().toString(),
            content: `🎉 Welcome ${event.data.user_email}! You're now signed in with Gmail.`,
            type: 'bot',
            timestamp: new Date()
          };
          
          // Add configuration message
          const configMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: `⚙️ Initial configuration is starting...\nLet's start with your company information.`,
            type: 'bot',
            timestamp: new Date()
          };
          
          // Auto-trigger canvas (no "ok" needed)
          const canvasMessage: Message = {
            id: (Date.now() + 2).toString(),
            content: 'configuration-panel',
            type: 'canvas',
            timestamp: new Date()
          };
          
          setMessages(prev => [...prev, successMessage, configMessage, canvasMessage]);
          
          // Start company name blinking animation
          startAnimation();
          
        } else if (event.data.type === 'GMAIL_AUTH_ERROR') {
          // Cleanup listeners and intervals
          if (messageHandlerRef.current) {
            window.removeEventListener('message', messageHandlerRef.current);
            messageHandlerRef.current = null;
          }
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          
          // Close popup
          if (popupRef.current && !popupRef.current.closed) {
            popupRef.current.close();
          }
          popupRef.current = null;
          
          setGmailLoading(false);
          setGmailError(event.data.message || 'Authentication failed');
        }
      };

      // Store reference and listen for messages from popup
      messageHandlerRef.current = handleMessage;
      window.addEventListener('message', handleMessage);

      // Fallback: Check popup status
      const checkPopup = setInterval(() => {
        // Skip if popup ref is null (already cleaned up)
        if (!popupRef.current) {
          clearInterval(checkPopup);
          return;
        }
        
        try {
          if (popupRef.current.closed) {
            // Cleanup
            clearInterval(checkPopup);
            intervalRef.current = null;
            
            if (messageHandlerRef.current) {
              window.removeEventListener('message', messageHandlerRef.current);
              messageHandlerRef.current = null;
            }
            
            popupRef.current = null;
            setGmailLoading(false);
            
            // Check if authentication was successful (fallback)
            const checkAuthStatus = async () => {
              try {
                const statusResponse = await fetch('http://localhost:8080/api/cloud/gmail-auth-status', {
                  credentials: 'include'
                });
                
                if (statusResponse.ok) {
                  const result = await statusResponse.json();
                  if (result.success && result.authenticated) {
                    console.log('✅ Authentication successful (fallback check):', result.user_email);
                    
                    // Update authentication state AND sidebar with user info
                    setIsAuthenticated(true);
                    setAuthenticatedUser(result.user_email);
                    
                    // Update sidebar with authenticated user info immediately  
                    updateUserInfo({
                      name: result.user_info?.name || result.user_email.split('@')[0],
                      email: result.user_email,
                      avatar: result.user_info?.photo_url || '/img/avatars/avatar4.png',
                      authenticated: true
                    });
                    
                    // Add success message and auto-trigger canvas
                    const successMessage: Message = {
                      id: Date.now().toString(),
                      content: `🎉 Welcome ${result.user_email}! You're now signed in with Gmail.`,
                      type: 'bot',
                      timestamp: new Date()
                    };
                    
                    const configMessage: Message = {
                      id: (Date.now() + 1).toString(),
                      content: `⚙️ Initial configuration is starting...\nLet's start with your company information.`,
                      type: 'bot',
                      timestamp: new Date()
                    };
                    
                    const canvasMessage: Message = {
                      id: (Date.now() + 2).toString(),
                      content: 'configuration-panel', 
                      type: 'canvas',
                      timestamp: new Date()
                    };
                    
                    setMessages(prev => [...prev, successMessage, configMessage, canvasMessage]);
                    
                    // Start company name blinking animation
                    startAnimation();
                  } else {
                    setGmailError('Authentication was not completed successfully');
                  }
                } else {
                  setGmailError('Failed to verify authentication status');
                }
              } catch (error) {
                console.error('Error checking auth status:', error);
                setGmailError('Failed to verify authentication');
              }
            };
            
            setTimeout(checkAuthStatus, 1000);
          }
        } catch (coopError) {
          // Silently ignore COOP errors - this is expected with OAuth providers
        }
      }, 2000);  // Check every 2 seconds
      
      intervalRef.current = checkPopup;

      // Timeout after 5 minutes
      setTimeout(() => {
        if (popupRef.current && !popupRef.current.closed) {
          // Cleanup
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          if (messageHandlerRef.current) {
            window.removeEventListener('message', messageHandlerRef.current);
            messageHandlerRef.current = null;
          }
          
          popupRef.current.close();
          popupRef.current = null;
          setGmailLoading(false);
          setGmailError('Authentication timeout - please try again');
        }
      }, 300000);

    } catch (error: any) {
      console.error('❌ Gmail authentication error:', error);
      setGmailLoading(false);
      setGmailError(error.message);
    }
  };

  // File upload handlers
  const handleFileUpload = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.doc,.docx,.txt,.xlsx,.pptx';
    input.onchange = (e: any) => {
      const file = e.target.files[0];
      if (file) {
        console.log('File selected:', file.name);
        // Handle file upload here
      }
    };
    input.click();
  };

  const handleImageUpload = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = (e: any) => {
      const file = e.target.files[0];
      if (file) {
        console.log('Image selected:', file.name);
        // Handle image upload here
      }
    };
    input.click();
  };

  const handleVideoUpload = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'video/*';
    input.onchange = (e: any) => {
      const file = e.target.files[0];
      if (file) {
        console.log('Video selected:', file.name);
        // Handle video upload here
      }
    };
    input.click();
  };

  return (
    <Flex
      w="100%"
      pt={{ base: '70px', md: '0px' }}
      direction="column"
      position="relative"
    >
      <Img
        src={Bg.src}
        position={'absolute'}
        w="350px"
        left="50%"
        top="50%"
        transform={'translate(-50%, -50%)'}
      />
      <Flex
        direction="column"
        mx="auto"
        w={{ base: '100%', md: '100%', xl: '100%' }}
        minH="100vh"
        maxW="1000px"
        position="relative"
      >
        {/* Content Area */}
        <Flex direction="column" flex="1" pb="100px" pt="20px" overflowY="auto">
          {/* Main Box */}
          <Flex
            direction="column"
            w="100%"
            mx="auto"
            mb={'auto'}
          >
            {/* Welcome Message */}
            <WelcomeMessage />
            
            
            {/* Gmail Sign Up Button - Only show if not authenticated */}
            {!isAuthenticated && (
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
              <Button
                bg={currentColors.gradient}
                color="white"
                py="12px"
                px="16px"
                fontSize="sm"
                borderRadius="16px"
                boxShadow="none"
                leftIcon={<Icon as={MdPerson} width="18px" height="18px" />}
                isLoading={gmailLoading}
                loadingText="Authenticating..."
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
                onClick={handleGmailAuth}
                disabled={gmailLoading}
              >
                {gmailLoading ? 'Authenticating...' : 'Sign up with Gmail'}
              </Button>
            </Flex>
            )}
            
            {/* Gmail OAuth Error Display */}
            {gmailError && (
              <Flex w="100%" mb="24px" align="flex-start">
                <Flex
                  borderRadius="full"
                  justify="center"
                  align="center"
                  bg="red.500"
                  me="12px"
                  h="32px"
                  minH="32px"
                  minW="32px"
                  flexShrink={0}
                >
                  <Text color="white" fontSize="16px">❌</Text>
                </Flex>
                <Flex
                  bg={errorBg}
                  borderRadius="16px"
                  px="16px"
                  py="12px"
                  maxW="75%"
                  color={errorColor}
                  fontSize={{ base: 'sm', md: 'md' }}
                  lineHeight={{ base: '20px', md: '22px' }}
                  fontWeight="400"
                  border="1px solid"
                  borderColor={errorBorderColor}
                  direction="column"
                >
                  <Text fontWeight="600" mb="8px">Authentication Error</Text>
                  <Text fontSize="sm" mb="12px">{gmailError}</Text>
                  <Button
                    size="sm"
                    colorScheme="red"
                    variant="outline"
                    onClick={() => setGmailError(null)}
                  >
                    Dismiss
                  </Button>
                </Flex>
              </Flex>
            )}
            
            {/* Chat Messages History */}
            {messages.map((message) => (
              message.type === 'canvas' ? (
                <CanvasMessage key={message.id} />
              ) : (
                <ChatMessage
                  key={message.id}
                  content={message.content}
                  type={message.type}
                  timestamp={message.timestamp}
                />
              )
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
                  bg={loadingBubbleBg}
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
        
        {/* Chat Input */}
        <Flex
          position="fixed"
          bottom="0"
          left={toggleSidebar ? 'calc(95px + (100vw - 95px - 800px) / 2)' : 'calc(288px + (100vw - 288px - 800px) / 2)'}
          w="800px"
          pt="20px"
          pb="20px"
          bg={useColorModeValue('white', 'navy.900')}
          alignItems="center"
          zIndex={10}
          transition="left 0.2s linear"
        >
          {/* Add Button */}
          <Menu>
            <MenuButton
              as={Button}
              variant="transparent"
              border="1px solid"
              borderColor={borderColor}
              borderRadius="full"
              w="34px"
              h="34px"
              px="0px"
              minW="34px"
              maxW="34px"
              minH="34px"
              maxH="34px"
              me="10px"
              justifyContent={'center'}
              alignItems="center"
              flexShrink={0}
              _hover={{ bg: useColorModeValue('gray.50', 'whiteAlpha.100') }}
            >
              <Icon as={MdAdd} width="16px" height="16px" color={textColor} />
            </MenuButton>
            <MenuList
              boxShadow={useColorModeValue(
                '14px 17px 40px 4px rgba(112, 144, 176, 0.18)',
                '0px 41px 75px #081132',
              )}
              p="10px"
              borderRadius="20px"
              bg={useColorModeValue('white', 'navy.800')}
              border="none"
            >
              <MenuItem
                onClick={handleFileUpload}
                _hover={{ bg: useColorModeValue('gray.100', 'whiteAlpha.100') }}
                borderRadius="8px"
                p="10px"
              >
                <Icon as={MdAttachFile} width="16px" height="16px" me="8px" />
                <Text fontSize="sm">Add File</Text>
              </MenuItem>
              <MenuItem
                onClick={handleImageUpload}
                _hover={{ bg: useColorModeValue('gray.100', 'whiteAlpha.100') }}
                borderRadius="8px"
                p="10px"
              >
                <Icon as={MdImage} width="16px" height="16px" me="8px" />
                <Text fontSize="sm">Add Image</Text>
              </MenuItem>
              <MenuItem
                onClick={handleVideoUpload}
                _hover={{ bg: useColorModeValue('gray.100', 'whiteAlpha.100') }}
                borderRadius="8px"
                p="10px"
              >
                <Icon as={MdVideoFile} width="16px" height="16px" me="8px" />
                <Text fontSize="sm">Add Video</Text>
              </MenuItem>
            </MenuList>
          </Menu>
          
          <Input
            minH="54px"
            h="100%"
            border="1px solid"
            borderColor={borderColor}
            borderRadius="45px"
            p="15px 20px"
            me="10px"
            fontSize="sm"
            fontWeight="500"
            _focus={{ borderColor: 'none' }}
            color={inputColor}
            _placeholder={placeholderColor}
            placeholder="Type your message here..."
            value={inputCode}
            onChange={handleChange}
          />
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
            onClick={handleTranslate}
            isLoading={loading ? true : false}
          >
            {getSubmitButtonText()}
          </Button>
        </Flex>


      </Flex>
    </Flex>
  );
}
