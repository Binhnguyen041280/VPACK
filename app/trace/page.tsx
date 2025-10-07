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
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  useDisclosure,
} from '@chakra-ui/react';
import { MdAutoAwesome, MdAdd, MdAttachFile, MdImage, MdVideoFile } from 'react-icons/md';
import Bg from '../../public/img/chat/bg-image.png';
import { useColorTheme } from '@/contexts/ColorThemeContext';
import ChatMessage from '@/components/ChatMessage';
import { SidebarContext } from '@/contexts/SidebarContext';
import { useRoute } from '@/contexts/RouteContext';
import TraceHeader from '@/components/trace/TraceHeader';
import EventSearchResults from '@/components/trace/EventSearchResults';
// Removed FileProcessingCard import - using text-based processing
import {
  formatDateTimeForAPI,
  getCurrentDateTime,
  formatDateTimeForDisplay,
  autoSetDateRange
} from '@/utils/dateTimeHelpers';
import {
  createFileUploadInput,
  createImageUploadInput,
  fileToBase64,
  getFileType,
  formatHeadersAsText,
  getColumnIndex,
  formatPlatformsAsText,
  detectPlatformFromText
} from '@/utils/fileProcessing';

interface EventData {
  event_id: number;
  tracking_codes_parsed: string[];
  camera_name: string;
  packing_time_start: number;
  packing_time_end: number;
  duration: number;
}

interface Message {
  id: string;
  content: string;
  type: 'user' | 'bot' | 'file_processing';
  timestamp: Date;
  eventData?: {
    searchInput: string;
    events: EventData[];
  };
  fileProcessingData?: {
    fileContent: string;
    fileName: string;
    isExcel: boolean;
    stage?: 'headers' | 'column_selected' | 'platform_named' | 'parsed' | 'results' | 'error' | 'completed';
    waitingForInput?: 'column' | 'platform' | 'none';
    headers?: string[];
    selectedColumn?: string;
    platformName?: string;
  };
}

export default function TracePage() {
  const [inputCode, setInputCode] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  // DateTime state for TraceHeader
  const [fromDateTime, setFromDateTime] = useState<string>('');
  const [toDateTime, setToDateTime] = useState<string>('');
  const [defaultDays, setDefaultDays] = useState<number>(3);

  // Camera state
  const [selectedCameras, setSelectedCameras] = useState<string[]>([]);
  const [availableCameras, setAvailableCameras] = useState<string[]>([]);

  // Header visibility state
  const [isHeaderHidden, setIsHeaderHidden] = useState<boolean>(false);
  const [isHovering, setIsHovering] = useState<boolean>(false);

  // Event modal state
  const [selectedEvent, setSelectedEvent] = useState<EventData | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();

  // Removed file processing state - only showing headers now

  // Handle event click
  const handleEventClick = (event: EventData) => {
    setSelectedEvent(event);
    onOpen();
  };

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { currentColors } = useColorTheme();
  const { toggleSidebar, setToggleSidebar } = useContext(SidebarContext);
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

  // Set active route to Trace and collapse sidebar when component mounts
  useEffect(() => {
    setCurrentRoute('/trace');
    // Collapse sidebar when entering trace page
    if (setToggleSidebar) {
      setToggleSidebar(true); // true means collapsed in this context
    }
  }, [setCurrentRoute, setToggleSidebar]);

  // State to track manual vs automatic time changes
  const [isManualTimeChange, setIsManualTimeChange] = useState<boolean>(false);

  // Initial date range setup only (removed auto-reset to prevent search interference)
  useEffect(() => {
    if (!fromDateTime && !toDateTime) {
      const { fromDateTime: initialFrom, toDateTime: initialTo } = autoSetDateRange(defaultDays);
      setFromDateTime(initialFrom);
      setToDateTime(initialTo);
    }
  }, []); // Only run once on mount

  // Fetch available cameras from API
  useEffect(() => {
    const fetchCameras = async () => {
      try {
        const response = await fetch('http://localhost:8080/get-cameras');
        if (!response.ok) {
          throw new Error(`Failed to fetch cameras: ${response.status}`);
        }
        const data = await response.json();
        const cameraNames = data.cameras?.map((camera: any) => camera.name) || [];
        setAvailableCameras(cameraNames);
      } catch (error) {
        console.error('Error fetching cameras:', error);
        // Fallback to hardcoded cameras in case of API failure
        setAvailableCameras(['Cloud_Cam1', 'Cloud_Cam2', 'Cloud_Cam3']);
      }
    };

    fetchCameras();
  }, []); // Only run once on mount

  // Update time range when defaultDays changes (only if not manually changed)
  useEffect(() => {
    if (!isManualTimeChange) {
      const { fromDateTime: newFrom, toDateTime: newTo } = autoSetDateRange(defaultDays);
      setFromDateTime(newFrom);
      setToDateTime(newTo);
    }
  }, [defaultDays, isManualTimeChange]);

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

      // Only add bot message if content is not empty
      if (botResponse.content.trim() || botResponse.eventData) {
        const botMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: botResponse.content,
          type: 'bot',
          timestamp: new Date(),
          eventData: botResponse.eventData
        };
        setMessages(prev => [...prev, botMessage]);
      }
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
  const handleTrackingCodes = async (input: string): Promise<{ type: 'text' | 'events', content: string, eventData?: { searchInput: string, events: EventData[] } }> => {
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

      // Truncate long search string for display
      const trackingCodes = input.split(',').map(code => code.trim()).filter(code => code.length > 0);
      const displayInput = trackingCodes.length > 3
        ? `${trackingCodes.slice(0, 3).join(', ')}...`
        : input;

      // Return event data for interactive display
      return {
        type: 'events',
        content: '',
        eventData: {
          searchInput: input,
          events: events
        }
      };
    } catch (error) {
      console.error('Error querying tracking codes:', error);
      return {
        type: 'text',
        content: `❌ Error searching for tracking codes: ${input}\n\nError: ${error instanceof Error ? error.message : 'Unknown error'}\n\nPlease check if the backend server is running on port 8080.`
      };
    }
  };

  // Handle platform selection and data processing
  const handlePlatformSelection = async (platformName: string, fileData: any): Promise<{ type: 'text' | 'events', content: string, eventData?: { searchInput: string, events: EventData[] } }> => {
    try {
      setLoading(true);

      // Get column index and name
      const columnIndex = getColumnIndex(fileData.selectedColumn);
      const columnName = fileData.headers[columnIndex];

      // Normalize platform name to proper case (first letter uppercase, rest lowercase)
      const normalizedPlatformName = platformName.charAt(0).toUpperCase() + platformName.slice(1).toLowerCase();

      // 1. Check if platform already exists and save/update mapping
      const saveResponse = await fetch('http://localhost:8080/save-platform-preference', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform_name: normalizedPlatformName,
          column_letter: fileData.selectedColumn,
          headers: fileData.headers || [],
          filename: fileData.fileName,
          enforce_unique: true // Add flag to enforce uniqueness
        })
      });

      const saveResult = await saveResponse.json();
      const isUpdate = saveResult.action === 'updated';

      // 2. Parse column data to get tracking codes
      const parseResponse = await fetch('http://localhost:8080/parse-csv', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_content: fileData.fileContent,
          column_name: columnName,
          is_excel: fileData.isExcel
        })
      });

      if (!parseResponse.ok) {
        throw new Error(`Failed to parse column: ${parseResponse.status}`);
      }

      const parseData = await parseResponse.json();
      const trackingCodes = parseData.tracking_codes || [];

      // Update the file processing message with platform and mark as completed
      setMessages(prev => prev.map(msg =>
        msg.fileProcessingData ? {
          ...msg,
          fileProcessingData: {
            ...msg.fileProcessingData,
            platformName: normalizedPlatformName,
            stage: 'completed'
          }
        } : msg
      ));

      // Format the response with column data listing
      let content = isUpdate
        ? `🔄 Platform "${normalizedPlatformName}" updated to use column ${fileData.selectedColumn}\n\n`
        : `✅ Platform "${normalizedPlatformName}" saved for column ${fileData.selectedColumn}\n\n`;
      content += `📋 Column data (${trackingCodes.length} items):\n\n`;

      // Show first 10 items with numbering
      trackingCodes.slice(0, 10).forEach((code: string, index: number) => {
        content += `${index + 1}. ${code}\n`;
      });

      if (trackingCodes.length > 10) {
        content += `... and ${trackingCodes.length - 10} more items`;
      }

      content += `\n\n🔍 Searching for events...`;

      // Add the listing message first
      const listingMessage: Message = {
        id: Date.now().toString(),
        content: content,
        type: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, listingMessage]);

      // Auto-query events using the extracted tracking codes
      const trackingCodesString = trackingCodes.join(', ');
      const queryResult = await handleTrackingCodes(trackingCodesString);

      // Add the query result message
      if (queryResult.eventData) {
        const queryMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: queryResult.content,
          type: 'bot',
          timestamp: new Date(),
          eventData: queryResult.eventData
        };
        setMessages(prev => [...prev, queryMessage]);
      } else if (queryResult.content.trim()) {
        const queryMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: queryResult.content,
          type: 'bot',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, queryMessage]);
      }

      return {
        type: 'text',
        content: '' // Return empty content since we've already added messages
      };

    } catch (error) {
      console.error('Error processing platform selection:', error);
      return {
        type: 'text',
        content: `❌ Error processing platform: ${error instanceof Error ? error.message : 'Unknown error'}`
      };
    } finally {
      setLoading(false);
    }
  };

  // Process file with auto-detected platform (Scenario 2)
  const processFileWithPlatform = async (file: File, platformName: string) => {
    // Normalize platform name to proper case (first letter uppercase, rest lowercase)
    const normalizedPlatformName = platformName.charAt(0).toUpperCase() + platformName.slice(1).toLowerCase();

    try {
      // Get file type
      const { isExcel } = getFileType(file.name);

      // Convert file to base64
      const fileContent = await fileToBase64(file);

      // Get file headers using correct endpoint
      const response = await fetch('http://localhost:8080/get-csv-headers', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_content: fileContent,
          is_excel: isExcel
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to get headers: ${response.status}`);
      }

      const fileResult = await response.json();
      const headers = fileResult.headers || [];

      // Try to get platform's preferred column from database
      let selectedColumn = 'A'; // Default column
      try {
        const platformResponse = await fetch('http://localhost:8080/get-platform-list');
        const platformData = await platformResponse.json();

        const existingPlatform = platformData.platforms?.find(
          (p: any) => p.name.toLowerCase() === normalizedPlatformName.toLowerCase()
        );

        if (existingPlatform) {
          selectedColumn = existingPlatform.column;
        }
      } catch (error) {
        console.error('Error fetching platform data:', error);
      }

      // Prepare file data for processing
      const fileData = {
        fileContent,
        fileName: file.name,
        isExcel,
        headers,
        selectedColumn
      };

      // Process the file with the detected platform
      const processResult = await handlePlatformSelection(normalizedPlatformName, fileData);

      // Only add result message if there's content (handlePlatformSelection might have already added messages)
      if (processResult.content && processResult.content.trim()) {
        const botMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: processResult.content,
          type: 'bot',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, botMessage]);
      }

    } catch (error) {
      console.error('Error in processFileWithPlatform:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `❌ Error processing file with ${normalizedPlatformName}: ${error instanceof Error ? error.message : 'Unknown error'}`,
        type: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  const getTraceResponse = async (input: string): Promise<{ type: 'text' | 'events', content: string, eventData?: { searchInput: string, events: EventData[] } }> => {
    // Check if user is selecting a column for file processing (only active/incomplete ones)
    const fileProcessingMessage = messages.find(msg =>
      msg.fileProcessingData &&
      msg.fileProcessingData.stage !== 'completed' &&
      (!msg.fileProcessingData.platformName) // Not yet completed
    );
    if (fileProcessingMessage && fileProcessingMessage.fileProcessingData) {
      const fileData = fileProcessingMessage.fileProcessingData;

      // If no column selected yet, check for column selection
      if (!fileData.selectedColumn && /^[a-z]+$/i.test(input.trim()) && input.trim().length <= 3) {
        const columnLetter = input.trim().toUpperCase();
        const headers = fileData.headers || [];

        // Check if it's a valid column
        const columnIndex = getColumnIndex(columnLetter);
        if (columnIndex >= 0 && columnIndex < headers.length) {
          // Update the file processing message with selected column
          setMessages(prev => prev.map(msg =>
            msg.fileProcessingData ? {
              ...msg,
              fileProcessingData: {
                ...msg.fileProcessingData,
                selectedColumn: columnLetter
              }
            } : msg
          ));

          // Fetch available platforms and show selection UI
          try {
            const response = await fetch('http://localhost:8080/get-platform-list');
            const data = await response.json();
            const platforms = data.platforms || [];

            const platformsText = formatPlatformsAsText(platforms);

            return {
              type: 'text',
              content: `✅ Column ${columnLetter} selected: "${headers[columnIndex]}"\n\n${platformsText}`
            };
          } catch (error) {
            // Fallback to text input if API fails
            return {
              type: 'text',
              content: `✅ Column ${columnLetter} selected: "${headers[columnIndex]}"\n\n💡 Enter platform name (e.g., Shopee, TikTok, Lazada, Amazon, eBay)`
            };
          }
        } else {
          return {
            type: 'text',
            content: `❌ Invalid column ${columnLetter}. Please select from available columns shown above.`
          };
        }
      }

      // If column selected but no platform yet, check for platform selection (letter or name)
      if (fileData.selectedColumn && !fileData.platformName) {
        const trimmedInput = input.trim();

        // Check if input is a single letter (platform selection)
        if (/^[a-z]$/i.test(trimmedInput)) {
          try {
            const response = await fetch('http://localhost:8080/get-platform-list');
            const data = await response.json();
            const platforms = data.platforms || [];

            const platformIndex = trimmedInput.toUpperCase().charCodeAt(0) - 65; // A=0, B=1, etc.

            // Check if selecting existing platform
            if (platformIndex < platforms.length) {
              const selectedPlatform = platforms[platformIndex];
              return await handlePlatformSelection(selectedPlatform.name, fileData);
            }
            // Check if selecting "Create New Platform" option
            else if (platformIndex === platforms.length) {
              return {
                type: 'text',
                content: `🆕 Creating new platform. Please enter platform name (e.g., Shopee, TikTok, Lazada):`
              };
            }
            else {
              return {
                type: 'text',
                content: `❌ Invalid selection ${trimmedInput.toUpperCase()}. Please select from available options shown above.`
              };
            }
          } catch (error) {
            return {
              type: 'text',
              content: `❌ Error loading platforms. Please try again or enter platform name directly.`
            };
          }
        }
        // If not a letter, treat as platform name input (for new platform creation)
        else if (trimmedInput.length >= 2) {
          return await handlePlatformSelection(trimmedInput, fileData);
        }
      }
    }

    // All other input is treated as tracking codes - let backend validate
    return await handleTrackingCodes(input);
  };

  const handleFileUpload = () => {
    createFileUploadInput(async (file: File) => {
      try {
        setLoading(true);

        // Check if user typed platform text (Scenario 2)
        if (inputCode.trim()) {
          const detectedPlatform = detectPlatformFromText(inputCode);
          if (detectedPlatform) {
            // Scenario 2: Auto-process with detected platform
            await processFileWithPlatform(file, detectedPlatform);
            setInputCode(''); // Clear input
            return;
          }
        }

        // Scenario 3: Show platform selection menu
        // Get file type
        const { isExcel } = getFileType(file.name);

        // Convert file to base64
        const fileContent = await fileToBase64(file);

        // Send file to backend for processing
        const response = await fetch('http://localhost:8080/get-csv-headers', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            file_content: fileContent,
            is_excel: isExcel
          })
        });

        if (response.ok) {
          const result = await response.json();
          const headers = result.headers || [];

          const fileMessage: Message = {
            id: Date.now().toString(),
            content: formatHeadersAsText(headers, file.name),
            type: 'bot',
            timestamp: new Date(),
            fileProcessingData: {
              fileContent,
              fileName: file.name,
              isExcel,
              stage: 'headers',
              waitingForInput: 'column',
              headers: headers
            }
          };
          setMessages(prev => [...prev, fileMessage]);
        } else {
          const result = await response.json();
          const errorMessage: Message = {
            id: Date.now().toString(),
            content: `❌ Failed to process file: ${result.error || 'Unknown error'}`,
            type: 'bot',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, errorMessage]);
          return;
        }

      } catch (error) {
        console.error('Error processing file:', error);
        const errorMessage: Message = {
          id: Date.now().toString(),
          content: `❌ Failed to process file: ${error instanceof Error ? error.message : 'Unknown error'}`,
          type: 'bot',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
      } finally {
        setLoading(false);
      }
    });
  };

  const handleImageUpload = () => {
    createImageUploadInput(async (file: File) => {
      setLoading(true);

      try {
        // Convert image to base64
        const imageContent = await fileToBase64(file);

        // Add user message for image upload
        const userMessage: Message = {
          id: Date.now().toString(),
          content: `📷 Image uploaded: ${file.name}`,
          type: 'user',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, userMessage]);

        // Call QR detection API
        const response = await fetch('http://localhost:8080/api/qr-detection/detect-qr-image', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            image_content: imageContent,
            image_name: file.name
          })
        });

        const result = await response.json();

        if (result.success && result.qr_detections && result.qr_detections.length > 0) {
          // QR codes found - Auto query
          const qrCodes = result.qr_detections;
          const qrCodeText = qrCodes.join(', ');

          // Add bot message for found QR codes
          const qrFoundMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: `✅ Found ${result.qr_count} QR codes: \`${qrCodeText}\``,
            type: 'bot',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, qrFoundMessage]);

          // Auto query with first QR code
          const queryInput = qrCodes[0];
          const botResponse = await getTraceResponse(queryInput);

          // Add query results
          if (botResponse.content.trim() || botResponse.eventData) {
            const queryResultMessage: Message = {
              id: (Date.now() + 2).toString(),
              content: botResponse.content,
              type: 'bot',
              timestamp: new Date(),
              eventData: botResponse.eventData
            };
            setMessages(prev => [...prev, queryResultMessage]);
          }

        } else {
          // No QR codes found
          const noQrMessage: Message = {
            id: (Date.now() + 1).toString(),
            content: `❌ No QR code found on image "${file.name}"`,
            type: 'bot',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, noQrMessage]);
        }

      } catch (error) {
        console.error('Error processing image:', error);
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: `❌ Image processing error: ${error instanceof Error ? error.message : 'Unknown error'}`,
          type: 'bot',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
      } finally {
        setLoading(false);
      }
    });
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
          onFromDateTimeChange={(dateTime) => {
            setFromDateTime(dateTime);
            setIsManualTimeChange(true);
          }}
          onToDateTimeChange={(dateTime) => {
            setToDateTime(dateTime);
            setIsManualTimeChange(true);
          }}
          onDefaultDaysChange={(days) => {
            setDefaultDays(days);
            setIsManualTimeChange(false); // Reset manual flag when defaultDays changes
          }}
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
              {messages.map((message) => {
                // If message has event data, render EventSearchResults
                if (message.eventData) {
                  return (
                    <Box key={message.id} mb="16px">
                      <EventSearchResults
                        searchInput={message.eventData.searchInput}
                        events={message.eventData.events}
                        onEventClick={handleEventClick}
                      />
                    </Box>
                  );
                }

                // Render all messages as text (including file processing)
                return (
                  <ChatMessage
                    key={message.id}
                    content={message.content}
                    type={message.type}
                    timestamp={message.timestamp}
                  />
                );
              })}

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

      {/* Event Details Modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="4xl">
        <ModalOverlay bg="blackAlpha.300" />
        <ModalContent maxW="90vw" maxH="90vh">
          <ModalHeader>
            📦 Event Details - {selectedEvent?.tracking_codes_parsed.join(', ')}
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            {selectedEvent && (
              <Box>
                <Text><strong>Camera:</strong> {selectedEvent.camera_name}</Text>
                <Text><strong>Start Time:</strong> {new Date(selectedEvent.packing_time_start).toLocaleString()}</Text>
                <Text><strong>End Time:</strong> {new Date(selectedEvent.packing_time_end).toLocaleString()}</Text>
                <Text><strong>Duration:</strong> {selectedEvent.duration}s</Text>
                <Text><strong>Event ID:</strong> {selectedEvent.event_id}</Text>
                <Text mt={4} color="gray.600">
                  🚧 Full event processing interface coming in Phase 2!
                </Text>
              </Box>
            )}
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
}