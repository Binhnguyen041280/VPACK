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
import { useEffect, useState, useContext, useRef, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { MdAutoAwesome, MdEdit, MdPerson, MdAdd, MdAttachFile, MdImage, MdVideoFile } from 'react-icons/md';
import Bg from '../public/img/chat/bg-image.png';
import { useColorTheme } from '@/contexts/ColorThemeContext';
import { SidebarContext } from '@/contexts/SidebarContext';
import { useUser } from '@/contexts/UserContext';
import { useRoute } from '@/contexts/RouteContext';
import StepNavigator from '@/components/navigation/StepNavigator';
import CanvasMessage from '@/components/canvas/CanvasMessage';
import { stepConfigService } from '@/services/stepConfigService';

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

function Chat(props: { apiKeyApp: string }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  
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
  // Auto-authentication state
  const [authLoading, setAuthLoading] = useState<boolean>(true); // Start with true to check on mount
  // Config check state to prevent UI flash
  const [isCheckingConfig, setIsCheckingConfig] = useState<boolean>(true);
  // Configuration state - Updated for 5-step workflow
  const [configStep, setConfigStep] = useState<'brandname' | 'location_time' | 'video_source' | 'packing_area' | 'timing'>('brandname');
  const [companyName, setCompanyName] = useState<string>('');
  
  // Chat-controlled Canvas state
  const [canvasState, setCanvasState] = useState<{
    brandName: string;
    isLoading: boolean;
    // Step 2 state
    locationTime: {
      country: string;
      timezone: string;
      language: string;
      working_days: string[];
      from_time: string;
      to_time: string;
    };
    locationTimeLoading: boolean;
    // Step 3 state
    videoSource?: {
      sourceType: 'local_storage' | 'cloud_storage';
      inputPath?: string;
      detectedFolders?: { name: string; path: string }[];
      selectedCameras?: string[];
      selectedTreeFolders?: any[];  // For cloud storage
      currentSource?: any;  // Current active source info
    };
    videoSourceLoading?: boolean;
    // Step 5 state
    timingStorage: {
      min_packing_time: number;
      max_packing_time: number;
      video_buffer: number;
      storage_duration: number;
      frame_rate: number;
      frame_interval: number;
      output_path: string;
    };
    timingStorageLoading: boolean;
  }>({
    brandName: 'Alan_go',
    isLoading: false,
    // Step 2 defaults (IANA timezone format)
    locationTime: {
      country: 'Vietnam',
      timezone: 'Asia/Ho_Chi_Minh',
      language: 'English (en-US)',
      working_days: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
      from_time: '07:00',
      to_time: '23:00'
    },
    locationTimeLoading: false,
    // Step 3 defaults
    videoSource: undefined,
    videoSourceLoading: false,
    // Step 5 defaults - matching backend defaults
    timingStorage: {
      min_packing_time: 10,
      max_packing_time: 120,
      video_buffer: 2,
      storage_duration: 30,
      frame_rate: 30,
      frame_interval: 5,
      output_path: "/default/output"
    },
    timingStorageLoading: false
  });
  // Step completion tracking for 5 steps - Start as incomplete, mark completed when user interacts
  const [stepCompleted, setStepCompleted] = useState<{[key: string]: boolean}>({
    brandname: false,   // Will be marked true when user completes step 1
    location_time: false,   // Will be marked true when user completes step 2
    video_source: false,   // Will be marked true when user completes step 3
    packing_area: false,   // Will be marked true when user completes step 4
    timing: false   // Will be marked true when user completes step 5
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
  // Menu colors to prevent hooks order violation
  const menuHoverBg = useColorModeValue('gray.50', 'whiteAlpha.100');
  const menuBoxShadow = useColorModeValue(
    '14px 17px 40px 4px rgba(112, 144, 176, 0.18)',
    '0px 41px 75px #081132',
  );
  const menuBg = useColorModeValue('white', 'navy.800');
  const menuItemHoverBg = useColorModeValue('gray.100', 'whiteAlpha.100');
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
  const { setCompanyName: setRouteCompanyName, startAnimation, stopAnimation, setCurrentRoute } = useRoute();

  // Auto-scroll to bottom when new message
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading]);

  // Auto-check existing Gmail authentication on page load
  const checkExistingGmailAuth = async () => {
    try {
      console.log('🔍 Checking existing Gmail authentication...');
      setAuthLoading(true);
      
      const response = await fetch('http://localhost:8080/api/cloud/gmail-auth-status', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log('📡 Gmail auth status result:', result);
        
        if (result.success && result.authenticated) {
          console.log('✅ Existing Gmail authentication found for:', result.user_email);
          
          // Set authentication state
          setIsAuthenticated(true);
          setAuthenticatedUser(result.user_email);
          
          // Update user context immediately
          updateUserInfo({
            name: result.user_info?.name || result.user_email.split('@')[0],
            email: result.user_email,
            avatar: result.user_info?.photo_url || '/img/avatars/avatar4.png',
            authenticated: true
          });
          
          // Add welcome back message
          const welcomeBackMessage: Message = {
            id: Date.now().toString(),
            content: `🎉 Welcome back, ${result.user_info?.name || result.user_email}! Your Gmail authentication is still active.`,
            type: 'bot',
            timestamp: new Date()
          };
          
          const configMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: `⚙️ Continuing with your configuration setup...`,
            type: 'bot',
            timestamp: new Date()
          };
          
          setMessages([welcomeBackMessage, configMessage]);
          
          // IMMEDIATE transition to configuration layout
          setShowConfigLayout(true);
          setCurrentRoute('/camera-config'); // Set active route to Camera Config in sidebar
          
          // Start company name blinking animation
          startAnimation();
          
          console.log('🚀 Auto-triggered configuration layout for returning user');
          
        } else {
          console.log('📭 No existing Gmail authentication found');
          // User needs to authenticate - stay in welcome mode
        }
      } else {
        console.log('❌ Failed to check Gmail auth status:', response.status);
      }
      
    } catch (error) {
      console.error('❌ Error checking existing Gmail auth:', error);
      // Fallback to normal flow if auto-check fails
    } finally {
      setAuthLoading(false);
    }
  };

  // Auto-check authentication on component mount
  useEffect(() => {
    checkExistingGmailAuth();
  }, []);

  // Check if user has NOT completed configuration and show camera config page
  useEffect(() => {
    // Only check after component has mounted (client-side only)
    if (typeof window !== 'undefined') {
      const userConfigured = localStorage.getItem('userConfigured');
      const configParam = searchParams.get('config');

      // Skip redirect if user intentionally navigated to Camera Config
      if (configParam === 'camera') {
        console.log('🎯 User navigated to Camera Config - skipping auto-redirect');

        // Check if step parameter is provided and set the configStep accordingly
        const stepParam = searchParams.get('step');
        if (stepParam && STEP_NUMBER_TO_KEY[stepParam]) {
          const stepKey = STEP_NUMBER_TO_KEY[stepParam];
          console.log(`📍 Setting config step to ${stepParam} (${stepKey})`);
          setConfigStep(stepKey);
        }

        setIsCheckingConfig(false); // Allow render
        return;
      }

      // If user has NOT completed configuration, stay on camera config page (no redirect)
      if (userConfigured !== 'true') {
        console.log('🎯 First-time user - showing camera config page...');
        setIsCheckingConfig(false); // Allow render
        return;
      }

      // If user has completed configuration, redirect to trace page
      console.log('🔄 Redirecting configured user to trace page...');
      router.push('/trace');
    }
  }, [router, searchParams]);

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
        // For Step 1, always use async API call - return flag to trigger async handling
        return 'ASYNC_CONTINUE_BRANDNAME_DEFAULT';
      
      case 'location_time':
        // For Step 2, always use async API call - return flag to trigger async handling
        return 'ASYNC_CONTINUE_LOCATION_TIME_DEFAULT';
      
      case 'video_source':
        // Save default video source settings
        // Auto-advance to next step
        setConfigStep('packing_area');
        setHighestStepReached(prev => Math.max(prev, 4));
        return '📦 Step 4: Packing Area Detection\n\nDefine the detection zones for monitoring.\n\nSet up areas to monitor and configure detection zones for optimal coverage.\n\n🎯 Detection zones are ready for customization.';
      
      case 'packing_area':
        // Save default packing area settings
        // Auto-advance to next step
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
    switch (configStep) {
      case 'brandname':
        // Mark step as completed for navigation sync
        setStepCompleted(prev => ({ ...prev, brandname: true }));
        // For Step 1, always use async API call - return flag to trigger async handling
        return 'ASYNC_SUBMIT_BRANDNAME_DEFAULT';
      
      case 'location_time':
        // Mark step as completed for navigation sync
        setStepCompleted(prev => ({ ...prev, location_time: true }));
        // For Step 2, always use async API call - return flag to trigger async handling
        return 'ASYNC_SUBMIT_LOCATION_TIME_DEFAULT';
      
      case 'video_source':
        // Mark step as completed for navigation sync (same as other steps)
        setStepCompleted(prev => ({ ...prev, video_source: true }));
        // For Step 3, always use async API call - return flag to trigger async handling
        return 'ASYNC_SUBMIT_VIDEO_SOURCE_DEFAULT';
      
      case 'packing_area':
        // Mark step as completed for navigation sync
        setStepCompleted(prev => ({ ...prev, packing_area: true }));
        // Auto-advance to next step
        setConfigStep('timing');
        setHighestStepReached(prev => Math.max(prev, 5));
        return '⏱️ Step 5: Timing & File Storage\n\nFinal step! Configure timing settings and file storage.\n\nSet up buffer times, packing time limits, storage paths, and retention policies.\n\n🚀 Timing and storage settings are ready for configuration.';
      
      case 'timing':
        // Mark step as completed for navigation sync
        setStepCompleted(prev => ({ ...prev, timing: true }));
        // For Step 5, always use async API call - return flag to trigger async handling
        return 'ASYNC_SUBMIT_TIMING_DEFAULT';
      
      default:
        return 'Configuration step completed.';
    }
  };

  // Handle Edit Commands
  const handleEditCommand = (newValue: string): string => {
    if (!newValue.trim()) {
      return 'Please provide a new value after "edit:"\n\nExample: edit: New Company Name';
    }

    switch (configStep) {
      case 'brandname':
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
    
    // Handle company name input when in brandname step - Direct Submit with auto-advance
    if (configStep === 'brandname' && userInput.trim().length > 0) {
      // This will be handled asynchronously by handleBrandnameSubmit
      return 'ASYNC_BRANDNAME_SUBMIT';
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

    // Add user message with auto-response if input is empty but action taken
    let userMessageContent = inputCode.trim();
    
    // Special case: if user entered company name, show it in user message
    if (userMessageContent && configStep === 'brandname') {
      userMessageContent = `Tôi thiết lập tên công ty: "${userMessageContent}"`;
    }
    
    // If empty input but step completed, show auto-response based on current step
    if (!inputCode.trim() && stepCompleted[configStep]) {
      switch (configStep) {
        case 'brandname':
          userMessageContent = 'I agree with Step 1 setup content';
          break;
        case 'location_time':
          userMessageContent = 'I agree with Step 2 setup content';
          break;
        case 'video_source':
          userMessageContent = 'I agree with Step 3 setup content';
          break;
        case 'packing_area':
          userMessageContent = 'I agree with Step 4 setup content';
          break;
        case 'timing':
          userMessageContent = 'I agree with Step 5 setup content';
          break;
        default:
          userMessageContent = 'I agree with this setup';
      }
    } else if (!inputCode.trim() && !stepCompleted[configStep]) {
      // Empty submit on incomplete step - show confirmation message
      switch (configStep) {
        case 'brandname':
          userMessageContent = 'I confirm default setup';
          break;
        case 'location_time':
          userMessageContent = 'I confirm Location & Time setup';
          break;
        case 'video_source':
          userMessageContent = 'I confirm Video Source setup';
          break;
        case 'packing_area':
          userMessageContent = 'I confirm Packing Area setup';
          break;
        case 'timing':
          userMessageContent = 'I confirm Timing & Storage setup';
          break;
        default:
          userMessageContent = 'I confirm this setup';
      }
    }
    
    // Add user message (always add for visual feedback)
    if (userMessageContent) {
      const userMessage: Message = {
        id: Date.now().toString(),
        content: userMessageContent,
        type: 'user',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, userMessage]);
    }
    setLoading(true);

    // Get auto response first to check for async flags
    const botResponse = getAutoResponse(inputCode);
    
    // Handle async brandname operations
    if (configStep === 'brandname' && inputCode.trim().length > 0) {
      // User entered brandname text
      handleBrandnameSubmit(inputCode.trim())
        .then(response => {
          const botMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: response,
            type: 'bot',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, botMessage]);
          setLoading(false);
        })
        .catch(error => {
          const errorMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: `❌ Error: ${error.message || 'Failed to process request'}`,
            type: 'bot',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, errorMessage]);
          setLoading(false);
        });
    } else if (botResponse === 'ASYNC_SUBMIT_BRANDNAME_DEFAULT') {
      // Empty submit for brandname
      handleBrandnameSubmitDefault()
        .then(response => {
          const botMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: response,
            type: 'bot',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, botMessage]);
          setLoading(false);
        })
        .catch(error => {
          const errorMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: `❌ Error: ${error.message || 'Failed to process request'}`,
            type: 'bot',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, errorMessage]);
          setLoading(false);
        });
    } else if (botResponse === 'ASYNC_CONTINUE_BRANDNAME_DEFAULT') {
      // Continue command for brandname
      handleBrandnameContinueDefault()
        .then(response => {
          const botMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: response,
            type: 'bot',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, botMessage]);
          setLoading(false);
        })
        .catch(error => {
          const errorMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: `❌ Error: ${error.message || 'Failed to process request'}`,
            type: 'bot',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, errorMessage]);
          setLoading(false);
        });
    } else if (botResponse === 'ASYNC_SUBMIT_LOCATION_TIME_DEFAULT') {
      // Empty submit for location-time
      handleLocationTimeSubmitDefault()
        .then(response => {
          const botMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: response,
            type: 'bot',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, botMessage]);
          setLoading(false);
        })
        .catch(error => {
          const errorMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: `❌ Error: ${error.message || 'Failed to process request'}`,
            type: 'bot',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, errorMessage]);
          setLoading(false);
        });
    } else if (botResponse === 'ASYNC_CONTINUE_LOCATION_TIME_DEFAULT') {
      // Continue command for location-time
      handleLocationTimeContinueDefault()
        .then(response => {
          const botMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: response,
            type: 'bot',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, botMessage]);
          setLoading(false);
        })
        .catch(error => {
          const errorMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: `❌ Error: ${error.message || 'Failed to process request'}`,
            type: 'bot',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, errorMessage]);
          setLoading(false);
        });
    } else if (botResponse === 'ASYNC_SUBMIT_VIDEO_SOURCE_DEFAULT') {
      // Empty submit for video source - save current canvas state
      handleVideoSourceSubmitDefault()
        .then(response => {
          const botMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: response,
            type: 'bot',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, botMessage]);
          setLoading(false);
        })
        .catch(error => {
          const errorMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: `❌ Error: ${error.message || 'Failed to save video source configuration'}`,
            type: 'bot',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, errorMessage]);
          setLoading(false);
        });
    } else if (botResponse === 'ASYNC_SUBMIT_TIMING_DEFAULT') {
      // Empty submit for timing/storage - save current canvas state
      handleTimingSubmitDefault()
        .then(response => {
          const botMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: response,
            type: 'bot',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, botMessage]);
          setLoading(false);
        })
        .catch(error => {
          const errorMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: `❌ Error: ${error.message || 'Failed to save timing/storage configuration'}`,
            type: 'bot',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, errorMessage]);
          setLoading(false);
        });
    } else if (configStep === 'video_source' && inputCode.trim().length > 0) {
      // User entered video source path - treat as input path and trigger save
      const inputPath = inputCode.trim();
      
      // Create video source data from input
      const videoSourceData = {
        sourceType: 'local_storage' as const,
        inputPath: inputPath,
        detectedFolders: canvasState.videoSource?.detectedFolders || [],
        selectedCameras: canvasState.videoSource?.selectedCameras || []
      };
      
      handleVideoSourceSubmit(videoSourceData)
        .then(response => {
          const botMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: response,
            type: 'bot',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, botMessage]);
          setLoading(false);
        })
        .catch(error => {
          const errorMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: `❌ Error: ${error.message || 'Failed to save video source configuration'}`,
            type: 'bot',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, errorMessage]);
          setLoading(false);
        });
    } else {
      // Handle other responses synchronously
      setTimeout(() => {
        // Skip if async response
        if (botResponse === 'ASYNC_BRANDNAME_SUBMIT' || 
            botResponse === 'ASYNC_SUBMIT_BRANDNAME_DEFAULT' || 
            botResponse === 'ASYNC_CONTINUE_BRANDNAME_DEFAULT' ||
            botResponse === 'ASYNC_SUBMIT_LOCATION_TIME_DEFAULT' ||
            botResponse === 'ASYNC_CONTINUE_LOCATION_TIME_DEFAULT' ||
            botResponse === 'ASYNC_SUBMIT_VIDEO_SOURCE_DEFAULT' ||
            botResponse === 'ASYNC_SUBMIT_TIMING_DEFAULT') {
          setLoading(false);
          return;
        }
        
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
    }

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
          setCurrentRoute('/camera-config'); // Set active route to Camera Config in sidebar
          
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
                    setCurrentRoute('/camera-config'); // Set active route to Camera Config in sidebar
                    
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
    // If user is moving back to a step they've already reached, mark current step as completed
    const currentStepNumber = STEP_KEY_TO_NUMBER[configStep];
    const targetStepNumber = STEP_KEY_TO_NUMBER[stepKey as keyof typeof STEP_KEY_TO_NUMBER];
    
    // Mark current step as completed if user has interacted with it and is moving to another step
    if (currentStepNumber <= highestStepReached && currentStepNumber < targetStepNumber) {
      setStepCompleted(prev => ({ ...prev, [configStep]: true }));
    }
    
    setConfigStep(stepKey as any);
  };

  // Store canvas refresh functions (legacy - can be removed)
  const [canvasRefreshFunctions, setCanvasRefreshFunctions] = useState<{[key: string]: any}>({});

  // Load initial brandname from database (Chat controller)
  const loadBrandnameState = async () => {
    try {
      setCanvasState(prev => ({ ...prev, isLoading: true }));
      const result = await stepConfigService.fetchBrandnameState();
      if (result.success) {
        setCanvasState(prev => ({ 
          ...prev, 
          brandName: result.data.brand_name,
          isLoading: false 
        }));
        setCompanyName(result.data.brand_name); // Sync with local state
        setRouteCompanyName(result.data.brand_name); // Sync with RouteContext for sidebar
      }
    } catch (error) {
      console.error('Error loading brandname:', error);
      setCanvasState(prev => ({ ...prev, isLoading: false }));
    }
  };

  // Load initial location/time from database (Chat controller)
  const loadLocationTimeState = async () => {
    try {
      setCanvasState(prev => ({ ...prev, locationTimeLoading: true }));
      const result = await stepConfigService.fetchLocationTimeState();
      if (result.success) {
        setCanvasState(prev => ({
          ...prev,
          locationTime: {
            country: result.data.country,
            timezone: result.data.timezone,
            language: result.data.language,
            working_days: result.data.working_days,
            from_time: result.data.from_time,
            to_time: result.data.to_time
          },
          locationTimeLoading: false
        }));
      }
    } catch (error) {
      console.error('Error loading location-time:', error);
      setCanvasState(prev => ({ ...prev, locationTimeLoading: false }));
    }
  };

  // Load initial timing/storage from database (Chat controller)
  const loadTimingStorageState = async () => {
    try {
      setCanvasState(prev => ({ ...prev, timingStorageLoading: true }));
      const result = await stepConfigService.fetchTimingStorageState();
      if (result.success) {
        setCanvasState(prev => ({
          ...prev,
          timingStorage: {
            min_packing_time: result.data.min_packing_time,
            max_packing_time: result.data.max_packing_time,
            video_buffer: result.data.video_buffer,
            storage_duration: result.data.storage_duration,
            frame_rate: result.data.frame_rate,
            frame_interval: result.data.frame_interval,
            output_path: result.data.output_path
          },
          timingStorageLoading: false
        }));
      }
    } catch (error) {
      console.error('Error loading timing-storage:', error);
      setCanvasState(prev => ({ ...prev, timingStorageLoading: false }));
    }
  };

  // Initialize step data when component mounts
  useEffect(() => {
    if (isAuthenticated) {
      loadBrandnameState();
      loadLocationTimeState();
      loadTimingStorageState();
    }
  }, [isAuthenticated]);

  // Load Step 2 data when switching to location_time step
  useEffect(() => {
    if (configStep === 'location_time') {
      loadLocationTimeState();
    }
  }, [configStep]);

  // Load Step 5 data when switching to timing step
  useEffect(() => {
    if (configStep === 'timing') {
      loadTimingStorageState();
    }
  }, [configStep]);

  // Handle canvas changes - mark step incomplete for submission
  const handleStepChange = (stepName: string, data: any) => {
    // Store refresh functions from canvas components
    if (data && data.refreshBrandname) {
      setCanvasRefreshFunctions(prev => ({ 
        ...prev, 
        [stepName]: { ...prev[stepName], refreshBrandname: data.refreshBrandname }
      }));
      return; // Don't mark as incomplete for refresh function registration
    }

    // Update Canvas state in real-time for Step 2 location_time
    if (stepName === 'location_time' && data) {
      console.log('🔄 Step 2 Canvas Change:', data);
      setCanvasState(prev => {
        const newLocationTime = { ...prev.locationTime };
        
        // Handle workDay toggle specifically
        if (data.workDay) {
          const dayKey = data.workDay;
          const currentWorkingDays = [...newLocationTime.working_days];
          const dayName = dayKey.charAt(0).toUpperCase() + dayKey.slice(1); // monday -> Monday
          
          if (currentWorkingDays.includes(dayName)) {
            // Remove the day
            newLocationTime.working_days = currentWorkingDays.filter(d => d !== dayName);
          } else {
            // Add the day
            newLocationTime.working_days = [...currentWorkingDays, dayName];
          }
        } else {
          // Handle other field updates with field name mapping
          if (data.workStartTime) {
            newLocationTime.from_time = data.workStartTime;
          } else if (data.workEndTime) {
            newLocationTime.to_time = data.workEndTime;
          } else {
            // Direct field mapping for country, timezone, language
            Object.assign(newLocationTime, data);
          }
        }
        
        return {
          ...prev,
          locationTime: newLocationTime
        };
      });
    }

    // Update Canvas state in real-time for Step 3 video_source
    if (stepName === 'video_source' && data) {
      console.log('🔄 Step 3 Canvas Change:', data);
      setCanvasState(prev => ({
        ...prev,
        videoSource: {
          sourceType: data.sourceType || prev.videoSource?.sourceType || 'local_storage',
          inputPath: data.inputPath || prev.videoSource?.inputPath || '',
          detectedFolders: data.detectedFolders || prev.videoSource?.detectedFolders || [],
          selectedCameras: data.selectedCameras || prev.videoSource?.selectedCameras || [],
          selectedTreeFolders: data.selectedTreeFolders || prev.videoSource?.selectedTreeFolders || [],
          currentSource: data.currentSource || prev.videoSource?.currentSource
        }
      }));
    }

    // Update Canvas state in real-time for Step 5 timing
    if (stepName === 'timing' && data) {
      console.log('🔄 Step 5 Canvas Change:', data);
      setCanvasState(prev => ({
        ...prev,
        timingStorage: {
          ...prev.timingStorage,
          ...data // Direct field mapping for timing fields
        }
      }));
    }

    // Mark step as incomplete when modified - requires Submit
    // No intermediate message - user will Submit directly
    setStepCompleted(prev => ({ ...prev, [stepName]: false }));
  };

  // Handle brandname submission with API call (for user input)
  const handleBrandnameSubmit = async (brandName: string): Promise<string> => {
    try {
      // Show loading state on Canvas
      setCanvasState(prev => ({ ...prev, isLoading: true }));
      
      const result = await stepConfigService.updateBrandnameState(brandName);
      
      if (result.success) {
        // Update Canvas state (Chat controls Canvas)
        setCanvasState(prev => ({ 
          ...prev, 
          brandName: result.data.brand_name,
          isLoading: false 
        }));
        
        // Update local state
        setCompanyName(result.data.brand_name);
        setRouteCompanyName(result.data.brand_name);
        stopAnimation();
        localStorage.setItem('userConfigured', 'true');
        setShowConfigLayout(true);
        setStepCompleted(prev => ({ ...prev, brandname: true }));
        setConfigStep('location_time');
        setHighestStepReached(prev => Math.max(prev, 2));

        // Show different message based on whether brand name was changed
        if (result.data.changed) {
          return `✅ Brand name updated to: "${result.data.brand_name}"\n\n📍 Step 2: Location & Time Configuration\n\nNow we'll set up your timezone, work schedule, and language preferences.\n\nThe system will auto-detect your location and timezone. You can modify these settings if needed.\n\n⚡ Auto-detection is running...`;
        } else {
          return `✅ Brand name confirmed: "${result.data.brand_name}" (no changes)\n\n📍 Step 2: Location & Time Configuration\n\nNow we'll set up your timezone, work schedule, and language preferences.\n\nThe system will auto-detect your location and timezone. You can modify these settings if needed.\n\n⚡ Auto-detection is running...`;
        }
      } else {
        // Hide loading state on error
        setCanvasState(prev => ({ ...prev, isLoading: false }));
        return `❌ Failed to update brand name: ${result.error || result.message || 'Unknown error'}`;
      }
    } catch (error) {
      // Hide loading state on error
      setCanvasState(prev => ({ ...prev, isLoading: false }));
      console.error('Error submitting brand name:', error);
      return `❌ Failed to update brand name: ${error instanceof Error ? error.message : 'Network error'}`;
    }
  };

  // Handle brandname Submit with default value (empty submit)
  const handleBrandnameSubmitDefault = async (): Promise<string> => {
    const brandNameToUse = companyName.trim() || 'Alan_go';
    return await handleBrandnameSubmit(brandNameToUse);
  };

  // Handle brandname Continue with default value
  const handleBrandnameContinueDefault = async (): Promise<string> => {
    const brandNameToUse = companyName.trim() || 'Alan_go';
    return await handleBrandnameSubmit(brandNameToUse);
  };

  // Handle Step 2 location/time submission with API call
  const handleLocationTimeSubmit = async (locationTimeData?: {
    country: string;
    timezone: string;
    language: string;
    working_days: string[];
    from_time: string;
    to_time: string;
  }): Promise<string> => {
    try {
      // Show loading state on Canvas
      setCanvasState(prev => ({ ...prev, locationTimeLoading: true }));
      
      // Use provided data or current Canvas state
      const dataToSubmit = locationTimeData || canvasState.locationTime;
      
      console.log('🔄 Step 2 Submit - Data to submit:', dataToSubmit);
      
      const result = await stepConfigService.updateLocationTimeState(dataToSubmit);
      
      console.log('✅ Step 2 Submit - API Result:', result);
      
      if (result.success) {
        // Update Canvas state (Chat controls Canvas)
        setCanvasState(prev => ({
          ...prev,
          locationTime: {
            country: result.data.country,
            timezone: result.data.timezone,
            language: result.data.language,
            working_days: result.data.working_days,
            from_time: result.data.from_time,
            to_time: result.data.to_time
          },
          locationTimeLoading: false
        }));
        
        // Update step completion and advance
        setStepCompleted(prev => ({ ...prev, location_time: true }));
        setConfigStep('video_source');
        setHighestStepReached(prev => Math.max(prev, 3));

        // Show different message based on whether data was changed
        if (result.data.changed) {
          return `✅ Location & Time configuration updated\n\n📹 Step 3: Video Source Configuration\n\nChoose where your video files are located for processing.\n\nSelect between local storage (PC, external drive, network mount) or cloud storage (Google Drive). Configure video quality and frame rate settings.\n\n📁 Choose the source that best fits your video storage setup.`;
        } else {
          return `✅ Location & Time configuration confirmed (no changes)\n\n📹 Step 3: Video Source Configuration\n\nChoose where your video files are located for processing.\n\nSelect between local storage (PC, external drive, network mount) or cloud storage (Google Drive). Configure video quality and frame rate settings.\n\n📁 Choose the source that best fits your video storage setup.`;
        }
      } else {
        // Hide loading state on error
        setCanvasState(prev => ({ ...prev, locationTimeLoading: false }));
        return `❌ Failed to update location/time configuration: ${result.error || result.message || 'Unknown error'}`;
      }
    } catch (error) {
      // Hide loading state on error
      setCanvasState(prev => ({ ...prev, locationTimeLoading: false }));
      console.error('Error submitting location/time:', error);
      return `❌ Failed to update location/time configuration: ${error instanceof Error ? error.message : 'Network error'}`;
    }
  };

  // Handle Step 2 Submit with default value (empty submit)
  const handleLocationTimeSubmitDefault = async (): Promise<string> => {
    return await handleLocationTimeSubmit();
  };

  // Handle Step 2 Continue with default value
  const handleLocationTimeContinueDefault = async (): Promise<string> => {
    return await handleLocationTimeSubmit();
  };

  // Step 3: Video Source Submit Handler
  const handleVideoSourceSubmit = async (videoSourceData?: {
    sourceType: 'local_storage' | 'cloud_storage';
    inputPath?: string;
    detectedFolders?: { name: string; path: string }[];
    selectedCameras?: string[];
    selectedTreeFolders?: any[];  // For cloud storage
    currentSource?: any;  // Current active source info
  }): Promise<string> => {
    try {
      // Show loading state on Canvas
      setCanvasState(prev => ({ ...prev, videoSourceLoading: true }));
      
      // Use provided data or current Canvas state
      const dataToSubmit = videoSourceData || canvasState.videoSource;
      
      console.log('🔄 Step 3 Submit - Data to submit:', dataToSubmit);
      
      // Handle case where no video source data is configured yet
      if (!dataToSubmit || !dataToSubmit.sourceType) {
        // No configuration yet - just advance to next step with defaults
        setConfigStep('packing_area');
        setHighestStepReached(prev => Math.max(prev, 4));
        setCanvasState(prev => ({ ...prev, videoSourceLoading: false }));
        return '📦 Step 4: Packing Area Detection\n\nDefine the detection zones for monitoring.\n\nSet up areas to monitor and configure detection zones for optimal coverage.\n\n🎯 Detection zones are ready for customization.';
      }
      
      // Validate required data for local storage
      if (dataToSubmit.sourceType === 'local_storage' && !dataToSubmit.inputPath) {
        throw new Error('Input path is required for local storage');
      }
      
      // Build payload with all required fields for UPSERT
      const payloadToSend = {
        sourceType: dataToSubmit.sourceType,
        inputPath: dataToSubmit.inputPath || '',
        detectedFolders: dataToSubmit.detectedFolders || [],
        selectedCameras: dataToSubmit.selectedCameras || [],
        selected_tree_folders: dataToSubmit.selectedTreeFolders || []  // For cloud storage
      };
      
      console.log('🔍 Step 3 Submit - Full payload:', JSON.stringify(payloadToSend, null, 2));
      
      // Call the step config service
      const result = await stepConfigService.updateVideoSourceState(payloadToSend);
      
      console.log('✅ Step 3 Submit - API Result:', result);
      
      if (result.success) {
        // Update Canvas state (Chat controls Canvas)
        setCanvasState(prev => ({
          ...prev,
          videoSource: {
            sourceType: dataToSubmit.sourceType,
            inputPath: dataToSubmit.inputPath || '',
            detectedFolders: dataToSubmit.detectedFolders || [],
            selectedCameras: dataToSubmit.selectedCameras || [],
            selectedTreeFolders: dataToSubmit.selectedTreeFolders || [],
            currentSource: dataToSubmit.currentSource
          },
          videoSourceLoading: false
        }));
        
        // Mark step as completed and advance to next step
        setStepCompleted(prev => ({ ...prev, video_source: true }));
        setConfigStep('packing_area');
        setHighestStepReached(prev => Math.max(prev, 4));
        
        if (result.data.changed) {
          // Build success message based on source type
          let successMessage = `✅ Video source configuration updated successfully\n\n📂 Source Type: ${dataToSubmit.sourceType}`;
          
          if (dataToSubmit.sourceType === 'local_storage') {
            successMessage += `\n📁 Input Path: ${dataToSubmit.inputPath || 'Not specified'}`;
            successMessage += `\n📷 Selected Cameras: ${dataToSubmit.selectedCameras?.join(', ') || 'None'}`;
          } else if (dataToSubmit.sourceType === 'cloud_storage') {
            const folderCount = dataToSubmit.selectedTreeFolders?.length || 0;
            successMessage += `\n☁️ Google Drive Folders: ${folderCount} selected`;
            successMessage += `\n📁 Sync Path: ${result.data.defaultSyncPath || 'Default'}`;
          }
          
          successMessage += `\n\n🎯 Configuration saved to database ✓`;
          if (result.data.upsert_operation) {
            successMessage += `\n🔄 Single Source Mode: Active (ID: ${result.data.videoSourceId})`;
          }
          
          successMessage += `\n\n📦 Step 4: Packing Area Detection\n\nDefine the detection zones for monitoring.\n\nSet up areas to monitor and configure detection zones for optimal coverage.\n\n🎯 Detection zones are ready for customization.`;
          
          return successMessage;
        } else {
          return `✅ Video source configuration confirmed (no changes)\n\n📂 Current settings validated ✓\n\n📦 Step 4: Packing Area Detection\n\nDefine the detection zones for monitoring.\n\nSet up areas to monitor and configure detection zones for optimal coverage.\n\n🎯 Detection zones are ready for customization.`;
        }
      } else {
        throw new Error(result.error || 'Failed to save video source configuration');
      }
      
    } catch (error) {
      console.error('❌ Step 3 Submit Error:', error);
      setCanvasState(prev => ({ ...prev, videoSourceLoading: false }));
      return `❌ Error saving video source configuration: ${error instanceof Error ? error.message : 'Unknown error'}\n\nPlease check your settings and try again.`;
    }
  };

  const handleVideoSourceSubmitDefault = async (): Promise<string> => {
    return await handleVideoSourceSubmit();
  };

  // Step 5: Timing/Storage Submit Handler
  const handleTimingSubmit = async (timingData?: {
    min_packing_time?: number;
    max_packing_time?: number;
    video_buffer?: number;
    storage_duration?: number;
    frame_rate?: number;
    frame_interval?: number;
    output_path?: string;
  }): Promise<string> => {
    try {
      // Show loading state on Canvas
      setCanvasState(prev => ({ ...prev, timingStorageLoading: true }));
      
      // Use provided data or current Canvas state
      const dataToSubmit = timingData || canvasState.timingStorage;
      
      console.log('🔄 Step 5 Submit - Data to submit:', dataToSubmit);
      
      const result = await stepConfigService.updateTimingStorageState(dataToSubmit);
      
      console.log('✅ Step 5 Submit - API Result:', result);
      
      if (result.success) {
        // Update Canvas state (Chat controls Canvas)
        setCanvasState(prev => ({
          ...prev,
          timingStorage: {
            min_packing_time: result.data.min_packing_time,
            max_packing_time: result.data.max_packing_time,
            video_buffer: result.data.video_buffer,
            storage_duration: result.data.storage_duration,
            frame_rate: result.data.frame_rate,
            frame_interval: result.data.frame_interval,
            output_path: result.data.output_path
          },
          timingStorageLoading: false
        }));
        
        // Update step completion - FINAL STEP!
        setStepCompleted(prev => ({ ...prev, timing: true }));
        
        // Redirect to Trace page sau khi hoàn thành configuration
        setTimeout(() => {
          window.location.href = '/trace';
        }, 1500);

        // Show different message based on whether data was changed
        if (result.data.changed) {
          return `✅ Configuration completed successfully!\n\n🎉 Your V.PACK system is now ready.\n\nRedirecting to Trace module for video processing and monitoring...`;
        } else {
          return `✅ Configuration completed successfully!\n\n🎉 Your V.PACK system is now ready.\n\nRedirecting to Trace module for video processing and monitoring...`;
        }
      } else {
        // Hide loading state on error
        setCanvasState(prev => ({ ...prev, timingStorageLoading: false }));
        return `❌ Failed to update timing/storage configuration: ${result.error || result.message || 'Unknown error'}`;
      }
    } catch (error) {
      // Hide loading state on error
      setCanvasState(prev => ({ ...prev, timingStorageLoading: false }));
      console.error('Error submitting timing/storage:', error);
      return `❌ Failed to update timing/storage configuration: ${error instanceof Error ? error.message : 'Network error'}`;
    }
  };

  // Handle Step 5 Submit with default value (empty submit)
  const handleTimingSubmitDefault = async (): Promise<string> => {
    return await handleTimingSubmit();
  };

  // Handle Step 5 Continue with default value
  const handleTimingContinueDefault = async (): Promise<string> => {
    return await handleTimingSubmit();
  };

  // Show loading while checking config to prevent UI flash
  if (isCheckingConfig) {
    return (
      <Flex
        w="100%"
        h="100vh"
        justify="center"
        align="center"
        bg={mainBg}
      >
        <Text fontSize="sm" color={textColor}>
          Loading...
        </Text>
      </Flex>
    );
  }

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
        // 3-Panel Configuration Layout - Pure Percentage Approach
        <Flex
          direction="row"
          h="100vh"
          p="20px"
          gap="20px"
          position="fixed"
          top="0"
          left={toggleSidebar ? "95px" : "288px"}
          w={`calc(100vw - ${toggleSidebar ? "95px" : "288px"})`}
          minW="900px"
          transition="left 0.2s linear"
          overflowX="auto"
          css={{
            '&::-webkit-scrollbar': {
              height: '8px',
            },
            '&::-webkit-scrollbar-track': {
              background: 'var(--chakra-colors-gray-100)',
            },
            '&::-webkit-scrollbar-thumb': {
              background: 'var(--chakra-colors-gray-300)',
              borderRadius: '4px',
            },
            '&::-webkit-scrollbar-thumb:hover': {
              background: 'var(--chakra-colors-gray-400)',
            },
          }}
        >
          {/* Column 1: Chat History + Chat Input - 40% */}
          <Flex
            flex="4"
            direction="column"
            gap="20px"
            minW="300px"
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
            flex="4"
            direction="column"
            minW="400px"
          >
            <Box
              bg={chatBg}
              borderRadius="20px"
              border="1px solid"
              borderColor={chatBorderColor}
              p="20px"
              h="100%"
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
              <CanvasMessage 
                configStep={configStep} 
                onStepChange={handleStepChange}
                brandName={canvasState.brandName}
                isLoading={canvasState.isLoading}
                locationTimeData={canvasState.locationTime}
                locationTimeLoading={canvasState.locationTimeLoading}
                timingStorageData={canvasState.timingStorage}
                timingStorageLoading={canvasState.timingStorageLoading}
              />
            </Box>
          </Flex>

          {/* Column 3: Navigator - 20% */}
          <Flex
            flex="2"
            direction="column"
            minW="200px"
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
              
              {/* Auth Loading Indicator */}
              {authLoading && (
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
                  <Flex
                    bg={loadingBubbleBg}
                    borderRadius="16px"
                    px="16px"
                    py="12px"
                    align="center"
                  >
                    <Text fontSize="sm" color={textColor}>
                      Checking existing authentication...
                    </Text>
                  </Flex>
                </Flex>
              )}

              {/* Gmail Sign Up Button - Only show if not authenticated and not loading */}
              {!isAuthenticated && !authLoading && (
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

// Loading component for Suspense fallback
function ChatLoading() {
  return (
    <Flex
      w="100%"
      h="100vh"
      justifyContent="center"
      alignItems="center"
      bg="linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
    >
      <Text color="white" fontSize="xl">
        Loading V.PACK...
      </Text>
    </Flex>
  );
}

// Wrap Chat in Suspense to handle useSearchParams() in Next.js 15
export default function HomePage() {
  return (
    <Suspense fallback={<ChatLoading />}>
      <Chat apiKeyApp="" />
    </Suspense>
  );
}
