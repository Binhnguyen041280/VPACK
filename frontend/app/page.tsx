'use client';
/*eslint-disable*/

import Link from '@/components/link/Link';
import MessageBoxChat from '@/components/MessageBox';
import WelcomeMessage from '@/components/WelcomeMessage';
import ChatMessage from '@/components/ChatMessage';
import { ChatBody, OpenAIModel } from '@/types/types';
import {
  Box,
  Button,
  Flex,
  HStack,
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
import StepNavigator from '@/components/navigation/StepNavigator';
import CanvasMessage from '@/components/canvas/CanvasMessage';

interface Message {
  id: string;
  content: string;
  type: 'user' | 'bot' | 'canvas';
  timestamp: Date;
}

// Step mapping constants
const STEP_NUMBER_TO_KEY: { [key: string]: 'brandname' | 'location_time' | 'video_source' | 'packing_area' | 'timing' } = {
  '1': 'brandname',
  '2': 'location_time', 
  '3': 'video_source',
  '4': 'packing_area',
  '5': 'timing'
};

const STEP_KEY_TO_NUMBER: { [key: string]: number } = {
  'brandname': 1,
  'location_time': 2,
  'video_source': 3,
  'packing_area': 4,
  'timing': 5
};

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
  // Configuration state - Updated for 5-step workflow
  const [configStep, setConfigStep] = useState<'brandname' | 'location_time' | 'video_source' | 'packing_area' | 'timing'>('brandname');
  const [companyName, setCompanyName] = useState<string>('');
  // Step completion tracking for 5 steps - All start as completed with defaults
  const [stepCompleted, setStepCompleted] = useState<{[key: string]: boolean}>({
    brandname: true,   // Default: "Alan_go"
    location_time: true,   // Default: Auto-detected timezone/schedule
    video_source: true,   // Default: Camera settings
    packing_area: true,   // Default: Detection zones
    timing: true   // Default: Performance & file storage settings
  });
  // Track highest step reached for progress display
  const [highestStepReached, setHighestStepReached] = useState<number>(1);
  // UI Layout state
  const [showConfigLayout, setShowConfigLayout] = useState<boolean>(false);

  // Color mode values - ALL at top level to prevent hooks order violation
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const inputColor = useColorModeValue('navy.700', 'white');
  const textColor = useColorModeValue('navy.700', 'white');
  const loadingBubbleBg = useColorModeValue('gray.50', 'whiteAlpha.100');
  const placeholderColor = useColorModeValue(
    { color: 'gray.500' },
    { color: 'whiteAlpha.600' },
  );
  const errorBg = useColorModeValue('red.50', 'red.900');
  const errorColor = useColorModeValue('red.700', 'red.200');
  const errorBorderColor = useColorModeValue('red.200', 'red.700');
  const chatBg = useColorModeValue('white', 'navy.900');
  const chatBorderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const chatTextColor = useColorModeValue('navy.700', 'white');
  const inputBorderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const inputTextColor = useColorModeValue('navy.700', 'white');
  const loadingBg = useColorModeValue('gray.50', 'whiteAlpha.100');
  const loadingTextColor = useColorModeValue('navy.700', 'white');
  const mainBg = useColorModeValue('white', 'navy.900');
  // Submit button text
  const getSubmitButtonText = (): string => {
    if (inputCode.trim() === '') {
      // Empty input - check if current step is completed
      if (stepCompleted[configStep]) {
        return 'Continue';
      } else {
        return 'Submit';
      }
    } else {
      // Has input - always submit
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

  // Color values that depend on currentColors - after hooks initialization
  const brandColor = useColorModeValue(currentColors.brand500, 'white');
  const gray = useColorModeValue('gray.500', 'white');

  // Handle Back Command - Go to Previous Step
  const handleBackCommand = (): string => {
    const stepOrder = ['brandname', 'location_time', 'video_source', 'packing_area', 'timing'];
    const currentIndex = stepOrder.indexOf(configStep);
    
    if (currentIndex <= 0) {
      return '⚠️ Already at the first step (Brandname).';
    }
    
    const previousStep = stepOrder[currentIndex - 1] as typeof configStep;
    setConfigStep(previousStep);
    
    return `← Back to Step ${currentIndex}: ${previousStep.replace('_', ' ')}\n\nYou can now modify settings for this step.`;
  };

  // Handle Step Jump Command - Direct Navigation
  const handleStepJump = (stepNumber: string): string => {
    const targetStep = STEP_NUMBER_TO_KEY[stepNumber];
    if (!targetStep) {
      return '❌ Invalid step number. Use: step 1, step 2, step 3, step 4, or step 5';
    }
    
    setConfigStep(targetStep);
    // Update highest step reached if moving forward
    const newStepNumber = STEP_KEY_TO_NUMBER[targetStep];
    if (newStepNumber > highestStepReached) {
      setHighestStepReached(newStepNumber);
    }
    return `→ Jumped to Step ${stepNumber}: ${targetStep.replace('_', ' ')}\n\nYou can now configure this step.`;
  };

  // Handle Continue Command - Save defaults and transition
  const handleContinueCommand = (): string => {
    // Only proceed if current step is completed
    if (!stepCompleted[configStep]) {
      return 'Please complete the current step first before continuing.';
    }

    // Save current defaults before transitioning
    switch (configStep) {
      case 'brandname':
        // Save default company name if not set
        if (!companyName.trim()) {
          setCompanyName('Alan_go');
          setRouteCompanyName('Alan_go');
          stopAnimation();
          localStorage.setItem('userConfigured', 'true');
          setShowConfigLayout(true);
        }
        setConfigStep('location_time');
        setHighestStepReached(prev => Math.max(prev, 2));
        return '📍 Step 2: Location & Time Configuration\n\nNow we\'ll set up your timezone, work schedule, and language preferences.\n\nThe system will auto-detect your location and timezone. You can modify these settings if needed.\n\n⚡ Auto-detection is running...';
      
      case 'location_time':
        // Save default location/time settings
        setConfigStep('video_source');
        setHighestStepReached(prev => Math.max(prev, 3));
        return '📹 Step 3: Video Source Configuration\n\nChoose where your video files are located for processing.\n\nSelect between local storage (PC, external drive, network mount) or cloud storage (Google Drive). Configure video quality and frame rate settings.\n\n📁 Choose the source that best fits your video storage setup.';
      
      case 'video_source':
        // Save default video source settings
        setConfigStep('packing_area');
        setHighestStepReached(prev => Math.max(prev, 4));
        return '📦 Step 4: Packing Area Detection\n\nDefine the detection zones for monitoring.\n\nSet up areas to monitor and configure detection zones for optimal coverage.\n\n🎯 Detection zones are ready for customization.';
      
      case 'packing_area':
        // Save default packing area settings
        setConfigStep('timing');
        setHighestStepReached(prev => Math.max(prev, 5));
        return '⏱️ Step 5: Timing & File Storage\n\nFinal step! Configure timing settings and file storage.\n\nSet up buffer times, packing time limits, storage paths, and retention policies.\n\n🚀 Timing and storage settings are ready for configuration.';
      
      case 'timing':
        // Save default timing settings - Final step
        return '✅ Step 5 completed. Timing & storage settings saved.\n\n🎉 All configuration completed!\n\nAll 5 steps finished with your settings. Ready to start processing.';
      
      default:
        return 'Configuration step completed.';
    }
  };

  // Handle Submit Command - Confirm changes and mark step completed
  const handleSubmitCommand = (): string => {
    // Mark current step as completed
    setStepCompleted(prev => ({ ...prev, [configStep]: true }));
    
    switch (configStep) {
      case 'brandname':
        // If no company name set, use default
        if (!companyName.trim()) {
          setCompanyName('Alan_go');
          setRouteCompanyName('Alan_go');
          stopAnimation();
          localStorage.setItem('userConfigured', 'true');
          setShowConfigLayout(true);
          return '✅ Changes confirmed. Using default: "Alan_go"\n\nType "continue" to proceed to next step.';
        } else {
          setShowConfigLayout(true);
          return `✅ Changes confirmed: "${companyName}"\n\nType "continue" to proceed to next step.`;
        }
      
      case 'location_time':
        return '✅ Location & Time settings confirmed.\n\nType "continue" to proceed to next step.';
      
      case 'video_source':
        return '✅ Video source settings confirmed.\n\nType "continue" to proceed to next step.';
      
      case 'packing_area':
        return '✅ Packing area settings confirmed.\n\nType "continue" to proceed to next step.';
      
      case 'timing':
        return '✅ Timing & storage settings confirmed.\n\nConfiguration completed!';
      
      default:
        return '✅ Settings confirmed.\n\nType "continue" to proceed.';
    }
  };

  // Handle Edit Commands
  const handleEditCommand = (newValue: string): string => {
    if (!newValue.trim()) {
      return 'Please provide a new value after "edit:"\n\nExample: edit: New Company Name';
    }

    switch (configStep) {
      case 'company':
      case 'location_time':
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
    const input = userInput.toLowerCase().trim();
    
    // Handle Empty Submit
    if (userInput.trim() === '') {
      // Empty submit should behave like "continue" if step is completed
      if (stepCompleted[configStep]) {
        return handleContinueCommand();
      } else {
        // Step is incomplete - this is a Submit to confirm changes
        return handleSubmitCommand();
      }
    }
    
    // Handle "continue" command
    if (input === 'continue') {
      return handleContinueCommand();
    }

    // Handle "next" command
    if (input === 'next') {
      return handleContinueCommand(); // Same as continue
    }

    // Handle "back" command
    if (input === 'back') {
      return handleBackCommand();
    }

    // Handle "step X" command
    if (input.startsWith('step ')) {
      const stepNumber = input.substring(5).trim();
      return handleStepJump(stepNumber);
    }
    
    // Handle Edit Pattern
    if (input.startsWith('edit:')) {
      return handleEditCommand(userInput.substring(5).trim());
    }

    // Handle "edit" command to reset current step
    if (input === 'edit') {
      // Mark current step as incomplete to allow editing
      setStepCompleted(prev => ({ ...prev, [configStep]: false }));
      
      return `🔄 Returning to ${configStep.replace('_', ' ')} configuration...\n\nYou can now modify your settings.\n\nCommands: "continue", "edit", "help"`;
    }
    
    // Handle help command
    if (input === 'help') {
      return 'Available commands:\n• "continue" or "next" - Proceed to next step\n• "back" - Go to previous step\n• "step X" - Jump to specific step (1-5)\n• "edit" - Modify current step settings\n• "help" - Show this help\n\nOr enter data to configure the current step.';
    }
    
    // Handle company name input when in brandname step - Direct Submit (no intermediate step)
    if (configStep === 'brandname' && userInput.trim().length > 0) {
      setCompanyName(userInput.trim());
      
      // Update sidebar route name (replaces "Alan_go")
      setRouteCompanyName(userInput.trim());
      
      // Stop company name blinking animation
      stopAnimation();
      
      // Mark user as configured (allow future database operations)
      localStorage.setItem('userConfigured', 'true');
      setShowConfigLayout(true);
      
      // Mark step as completed immediately (direct submit pattern)
      setStepCompleted(prev => ({ ...prev, brandname: true }));
      
      // Direct submit result - no intermediate confirmation
      return `✅ Changes confirmed: "${userInput.trim()}"\n\nType "continue" to proceed to next step.`;
    }
    
    // Handle empty submit for brandname (use default) - this is covered by handleSubmitCommand now
    
    // Default response for unrecognized input
    return 'Available commands:\n• "continue" or "next" - Proceed to next step\n• "back" - Go to previous step\n• "step X" - Jump to specific step (1-5)\n• "edit" - Modify current step settings\n• "help" - Show this help\n\nOr enter data to configure the current step.';
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
          
          // Refresh user info to get downloaded avatar from backend
          setTimeout(() => {
            refreshUserInfo();
          }, 2000);
          
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
          
          // Add messages without canvas (canvas is now fixed in Configuration Area)
          setMessages(prev => [...prev, successMessage, configMessage]);
          
          // Trigger 3-panel layout immediately after OAuth
          setShowConfigLayout(true);
          
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
                    
                    // Refresh user info to get downloaded avatar from backend
                    setTimeout(() => {
                      refreshUserInfo();
                    }, 2000);
                    
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
                    
                    // Add messages without canvas (canvas is now fixed in Configuration Area)
                    setMessages(prev => [...prev, successMessage, configMessage]);
                    
                    // Trigger 3-panel layout immediately after OAuth
                    setShowConfigLayout(true);
                    
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

  // Step Navigator click handler
  const handleStepClick = (stepKey: string) => {
    setConfigStep(stepKey as any);
  };

  // Handle canvas changes - mark step incomplete for submission
  const handleStepChange = (stepName: string, data: any) => {
    // Mark step as incomplete when modified - requires Submit
    // No intermediate message - user will Submit directly
    setStepCompleted(prev => ({ ...prev, [stepName]: false }));
  };

  return (
    <Flex
      w="100%"
      direction="column"
      position="relative"
      overflow="hidden"
      h="100vh"
    >
      {/* Background Image - only show in single-panel mode */}
      {!showConfigLayout && (
        <Img
          src={Bg.src}
          position={'absolute'}
          w="350px"
          left="50%"
          top="50%"
          transform={'translate(-50%, -50%)'}
        />
      )}
      
      {/* Conditional Layout Rendering */}
      {showConfigLayout ? (
        // 3-Panel Configuration Layout  
        <Flex
          direction="row"
          h="100vh"
          p="20px"
          gap="20px"
          position="fixed"
          top="0"
          left={toggleSidebar ? "95px" : "288px"}
          right="0"
          transition="left 0.2s linear"
        >
          {/* Column 1: Chat History + Chat Input - 40% */}
          <Flex
            flex="2"
            direction="column"
            gap="20px"
          >
            {/* Top: Chat History */}
            <Box
              bg={chatBg}
              borderRadius="20px"
              border="1px solid"
              borderColor={chatBorderColor}
              p="20px"
              flex="1"
              overflow="auto"
              css={{
                '&::-webkit-scrollbar': {
                  width: '6px',
                },
                '&::-webkit-scrollbar-track': {
                  background: 'var(--chakra-colors-gray-100)',
                },
                '&::-webkit-scrollbar-thumb': {
                  background: 'var(--chakra-colors-gray-300)',
                  borderRadius: '3px',
                },
                '&::-webkit-scrollbar-thumb:hover': {
                  background: 'var(--chakra-colors-gray-400)',
                },
              }}
            >
              {/* Chat Header */}
              <Text
                fontSize="lg"
                fontWeight="700"
                color={chatTextColor}
                mb="20px"
                textAlign="center"
                flexShrink={0}
              >
                💬 Chat Control
              </Text>
              
              {/* Chat Messages - Scrollable */}
              <Box
                flex="1"
                overflow="auto"
                pt="16px"
                css={{
                  '&::-webkit-scrollbar': {
                    width: '6px',
                  },
                  '&::-webkit-scrollbar-track': {
                    background: 'var(--chakra-colors-gray-100)',
                  },
                  '&::-webkit-scrollbar-thumb': {
                    background: 'var(--chakra-colors-gray-300)',
                    borderRadius: '3px',
                  },
                  '&::-webkit-scrollbar-thumb:hover': {
                    background: 'var(--chakra-colors-gray-400)',
                  },
                }}
              >
                {/* Chat Messages History */}
                {messages.map((message) => (
                  message.type !== 'canvas' && (
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
                      bg={loadingBg}
                      borderRadius="16px"
                      px="16px"
                      py="12px"
                      align="center"
                    >
                      <Text fontSize="sm" color={chatTextColor}>
                        Typing...
                      </Text>
                    </Flex>
                  </Flex>
                )}
                
                {/* Scroll anchor for auto-scroll */}
                <div ref={messagesEndRef} />
              </Box>
            </Box>

            {/* Bottom: Chat Input - Fixed at bottom */}
            <Box
              bg={chatBg}
              borderRadius="20px"
              border="1px solid"
              borderColor={chatBorderColor}
              p="20px"
              flexShrink={0}
            >
              <HStack spacing="10px">
                <Box position="relative" flex="1">
                  <Input
                    h="54px"
                    border="1px solid"
                    borderColor={chatBorderColor}
                    borderRadius="45px"
                    p="15px 50px 15px 20px"
                    fontSize="sm"
                    fontWeight="500"
                    _focus={{ borderColor: 'none' }}
                    color={chatTextColor}
                    _placeholder={placeholderColor}
                    placeholder="Type command here..."
                    value={inputCode}
                    onChange={handleChange}
                  />
                  {/* Add Button Menu - Inside Input */}
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
                      _hover={{ bg: useColorModeValue('gray.50', 'whiteAlpha.100') }}
                    >
                      <Icon as={MdAdd} width="16px" height="16px" color={chatTextColor} />
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
                </Box>
                <Button
                  bg={currentColors.gradient}
                  color="white"
                  py="20px"
                  px="16px"
                  fontSize="sm"
                  borderRadius="45px"
                  w="120px"
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
              </HStack>
            </Box>
          </Flex>

          {/* Column 2: Canvas - 40% */}
          <Flex
            flex="2"
            direction="column"
          >
            <Box
              bg={chatBg}
              borderRadius="20px"
              border="1px solid"
              borderColor={chatBorderColor}
              p="20px"
              h="100%"
              overflow="hidden"
            >
              <CanvasMessage 
                configStep={configStep} 
                onStepChange={handleStepChange}
              />
            </Box>
          </Flex>

          {/* Column 3: Navigator - 20% */}
          <Flex
            flex="1"
            direction="column"
          >
            <Box
              bg={chatBg}
              borderRadius="20px"
              border="1px solid"
              borderColor={chatBorderColor}
              p="20px"
              h="100%"
              overflow="auto"
            >
              <StepNavigator
                currentStep={configStep}
                completedSteps={stepCompleted}
                highestStepReached={highestStepReached}
                onStepClick={handleStepClick}
              />
            </Box>
          </Flex>
        </Flex>
      ) : (
        // Original Single-Panel Layout
        <Flex
          direction="column"
          mx="auto"
          w={{ base: '100%', md: '100%', xl: '100%' }}
          minH="100vh"
          maxW="1000px"
          position="relative"
        >
          {/* Content Area */}
          <Flex direction="column" flex="1" pb="100px" pt="36px" overflowY="auto">
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
              
              {/* Chat Messages History - No canvas messages */}
              {messages.map((message) => (
                message.type !== 'canvas' && (
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
                    bg={loadingBg}
                    borderRadius="16px"
                    px="16px"
                    py="12px"
                    align="center"
                  >
                    <Text fontSize="sm" color={chatTextColor}>
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
                placeholder="Type your message here..."
                value={inputCode}
                onChange={handleChange}
              />
              {/* Add Button Menu - Inside Input */}
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
                  _hover={{ bg: useColorModeValue('gray.50', 'whiteAlpha.100') }}
                >
                  <Icon as={MdAdd} width="16px" height="16px" color={chatTextColor} />
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
              onClick={handleTranslate}
              isLoading={loading ? true : false}
            >
              {getSubmitButtonText()}
            </Button>
          </Flex>
        </Flex>
      )}
    </Flex>
  );
}
