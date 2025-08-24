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
  Input,
  Select,
  Checkbox,
  SimpleGrid,
  useColorModeValue
} from '@chakra-ui/react';
import { MdAutoAwesome, MdVideoLibrary, MdCamera } from 'react-icons/md';
import { useColorTheme } from '@/contexts/ColorThemeContext';
import LocationTimeCanvas from './LocationTimeCanvas';
import GoogleDriveFolderTree from './GoogleDriveFolderTree';
import { useState, useEffect, useRef } from 'react';
import React from 'react';

interface CanvasMessageProps {
  configStep: 'brandname' | 'location_time' | 'file_save' | 'video_source' | 'packing_area' | 'timing';
  onStepChange?: (stepName: string, data: any) => void;
}

// Height breakpoints for adaptive behavior
type HeightMode = 'compact' | 'normal' | 'spacious';

interface AdaptiveConfig {
  mode: HeightMode;
  fontSize: {
    header: string;
    title: string;
    body: string;
    small: string;
  };
  spacing: {
    section: string;
    item: string;
    padding: string;
  };
  showOptional: boolean;
}

export default function CanvasMessage({ configStep, onStepChange }: CanvasMessageProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  
  // Height detection and adaptive behavior
  const containerRef = useRef<HTMLDivElement>(null);
  const [availableHeight, setAvailableHeight] = useState(0);
  const [adaptiveConfig, setAdaptiveConfig] = useState<AdaptiveConfig>({
    mode: 'normal',
    fontSize: { header: 'md', title: 'xs', body: 'xs', small: 'xs' },
    spacing: { section: '16px', item: '12px', padding: '20px' },
    showOptional: true
  });

  // Detect container height and adjust config
  useEffect(() => {
    const updateHeight = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        const height = rect.height;
        setAvailableHeight(height);
        
        // Determine adaptive config based on height
        let newConfig: AdaptiveConfig;
        
        if (height < 400) {
          // Compact mode - very small height - Match Navigator compact
          newConfig = {
            mode: 'compact',
            fontSize: { header: 'sm', title: 'xs', body: 'xs', small: 'xs' },
            spacing: { section: '8px', item: '6px', padding: '12px' },
            showOptional: false
          };
        } else if (height < 600) {
          // Normal mode - medium height - Match Navigator normal
          newConfig = {
            mode: 'normal',
            fontSize: { header: 'md', title: 'xs', body: 'xs', small: 'xs' },
            spacing: { section: '12px', item: '8px', padding: '16px' },
            showOptional: true
          };
        } else {
          // Spacious mode - large height - Slightly larger than Navigator
          newConfig = {
            mode: 'spacious',
            fontSize: { header: 'md', title: 'sm', body: 'xs', small: 'xs' },
            spacing: { section: '20px', item: '16px', padding: '24px' },
            showOptional: true
          };
        }
        
        setAdaptiveConfig(newConfig);
      }
    };

    // Initial measurement
    updateHeight();
    
    // Listen for resize events
    const resizeObserver = new ResizeObserver(updateHeight);
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }
    
    return () => resizeObserver.disconnect();
  }, []);
  
  // Render canvas based on current step with adaptive config
  const renderCanvas = () => {
    const commonProps = { 
      onStepChange, 
      adaptiveConfig, 
      availableHeight 
    };
    
    switch (configStep) {
      case 'brandname':
        return <BrandnameCanvas {...commonProps} />;
      case 'location_time':
        return <LocationTimeCanvas {...commonProps} />;
      case 'file_save':
        return <FileSaveCanvas {...commonProps} />;
      case 'video_source':
        return <VideoSourceCanvas {...commonProps} />;
      case 'packing_area':
        return <PackingAreaCanvas {...commonProps} />;
      case 'timing':
        return <TimingCanvas {...commonProps} />;
      default:
        return <BrandnameCanvas {...commonProps} />;
    }
  };

  // Determine if current step should have scroll (all except step 1)
  const shouldScroll = configStep !== 'brandname';

  return (
    <Box 
      ref={containerRef}
      h="100%" 
      w="100%"
      overflow={shouldScroll ? "auto" : "hidden"}
      css={shouldScroll ? {
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
        // Ensure content can overflow properly
        overflowY: 'auto',
        overflowX: 'hidden',
      } : {
        overflowY: 'hidden',
        overflowX: 'hidden',
      }}
    >
      {/* Dynamic Canvas Content - No Bot Avatar */}
      {renderCanvas()}
    </Box>
  );
}

// Enhanced Canvas Component Props
interface CanvasComponentProps {
  onStepChange?: (stepName: string, data: any) => void;
  adaptiveConfig: AdaptiveConfig;
  availableHeight: number;
}

// Brandname Canvas Component (Step 1)
function BrandnameCanvas({ adaptiveConfig }: CanvasComponentProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const cardBg = useColorModeValue('gray.50', 'navy.700');

  return (
    <Box
      w="100%"
      minH="fit-content"
    >
      {/* Header - Priority Content */}
      <Text fontSize={adaptiveConfig.fontSize.header} fontWeight="700" color={textColor} mb={adaptiveConfig.spacing.section}>
        🏢 Step 1: Brandname Setup
      </Text>

      <VStack spacing={adaptiveConfig.spacing.item} align="stretch">
        {/* Company Information Section - Priority Content */}
        <Box>
          {adaptiveConfig.mode !== 'compact' && (
            <HStack mb={adaptiveConfig.spacing.item}>
              <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor}>
                🏢 Company Information
              </Text>
            </HStack>
          )}
          
          <Box
            bg={cardBg}
            p={adaptiveConfig.spacing.item}
            borderRadius="12px"
            textAlign="center"
          >
            <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor} mb={adaptiveConfig.spacing.item}>
              Company/Brand Name
            </Text>
            {adaptiveConfig.showOptional && (
              <Text fontSize={adaptiveConfig.fontSize.small} color="gray.500" mb={adaptiveConfig.spacing.item}>
                Type your company name in the chat below and click Submit
              </Text>
            )}
            {adaptiveConfig.mode !== 'compact' && (
              <Text fontSize={adaptiveConfig.fontSize.small} color="gray.400" fontStyle="italic">
                Example: "TechCorp Manufacturing"
              </Text>
            )}
          </Box>
        </Box>

        {adaptiveConfig.showOptional && <Divider />}

        {/* Status Summary - Essential Content */}
        <Box
          bg={cardBg}
          p={adaptiveConfig.spacing.item}
          borderRadius="12px"
          textAlign="center"
        >
          <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor} mb="4px">
            ⏳ Waiting for Company Name
          </Text>
          {adaptiveConfig.showOptional && (
            <Text fontSize={adaptiveConfig.fontSize.small} color="gray.500">
              Please enter your company name in the chat and click Submit
            </Text>
          )}
        </Box>
      </VStack>
    </Box>
  );
}

// Step 3: File Save Canvas
function FileSaveCanvas({ adaptiveConfig, onStepChange }: CanvasComponentProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  const cardBg = useColorModeValue('gray.50', 'navy.700');
  
  // Local state for storage path - Default based on OS
  const getDefaultPath = () => {
    const platform = navigator.platform.toLowerCase();
    if (platform.includes('win')) {
      return 'C:\\Users\\%USERNAME%\\Videos\\VTrack';
    } else if (platform.includes('mac')) {
      return '/Users/%USER%/Movies/VTrack';
    } else {
      return '/home/%USER%/Videos/VTrack';
    }
  };
  
  const [storagePath, setStoragePath] = useState(getDefaultPath());

  return (
    <Box
      w="100%"
      minH="fit-content"
    >
      {/* Header */}
      <Text fontSize={adaptiveConfig.fontSize.header} fontWeight="700" color={textColor} mb={adaptiveConfig.spacing.section}>
        💾 Step 3: File Storage Settings
      </Text>

      <VStack spacing={adaptiveConfig.spacing.item} align="stretch">
        {/* Storage Path Section */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            💾 Video Output Directory
          </Text>
          <Box bg={cardBg} p="16px" borderRadius="12px">
            <VStack spacing="8px" align="stretch" mb="12px">
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
                📝 Choose where to save processed videos and detection results
              </Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color="orange.500" fontStyle="italic">
                💡 Tip: Open folder in explorer, copy path from address bar and paste here
              </Text>
            </VStack>
            <Input
              value={storagePath}
              placeholder="Copy and paste folder path here..."
              size="sm"
              borderColor={borderColor}
              _focus={{ borderColor: currentColors.brand500 }}
              bg={bgColor}
              mb="12px"
              onFocus={(e) => {
                // Clear input when user clicks to enter new path
                if (storagePath === getDefaultPath()) {
                  setStoragePath('');
                }
                e.target.select(); // Select all text for easy replacement
              }}
              onChange={(e) => {
                setStoragePath(e.target.value);
                onStepChange?.('file_save', { storagePath: e.target.value });
              }}
            />
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              📋 Output folder: {storagePath}
            </Text>
          </Box>
        </Box>

        {/* Retention Policy */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            🗓️ File Retention
          </Text>
          <Box bg={cardBg} p="16px" borderRadius="12px">
            <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} mb="8px">
              Auto-delete after:
            </Text>
            <HStack spacing="8px">
              <Input
                placeholder="30"
                size="sm"
                w="60px"
                borderColor={borderColor}
                _focus={{ borderColor: currentColors.brand500 }}
                onChange={() => onStepChange?.('file_save', { retention: '30' })}
              />
              <Select size="sm" borderColor={borderColor}>
                <option value="days">Days</option>
                <option value="weeks">Weeks</option>
                <option value="months">Months</option>
              </Select>
            </HStack>
          </Box>
        </Box>


      </VStack>
    </Box>
  );
}

// Step 4: Video Source Canvas
function VideoSourceCanvas({ adaptiveConfig, onStepChange }: CanvasComponentProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  const cardBg = useColorModeValue('gray.50', 'navy.700');

  // State for selected source type and input path
  const [selectedSourceType, setSelectedSourceType] = useState<'local_storage' | 'cloud_storage'>('local_storage');
  
  // Default input path based on OS
  const getDefaultInputPath = () => {
    const platform = navigator.platform.toLowerCase();
    if (platform.includes('win')) {
      return 'C:\\Users\\%USERNAME%\\Videos\\Input';
    } else if (platform.includes('mac')) {
      return '/Users/%USER%/Movies/Input';
    } else {
      return '/home/%USER%/Videos/Input';
    }
  };
  
  const [inputPath, setInputPath] = useState(getDefaultInputPath());
  
  // Google Drive connection state
  const [driveConnected, setDriveConnected] = useState(false);
  const [driveUserEmail, setDriveUserEmail] = useState('');
  const [driveConnecting, setDriveConnecting] = useState(false);
  const [driveFolders, setDriveFolders] = useState<any[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<any>(null);
  const [folderTreeLoading, setFolderTreeLoading] = useState(false);
  
  // NEW: Tree-based folder selection
  const [selectedTreeFolders, setSelectedTreeFolders] = useState<any[]>([]);
  
  // Session token stored in ref to avoid hooks order issues
  const driveSessionTokenRef = React.useRef<string>('');
  
  // Check Google Drive connection status on component mount
  React.useEffect(() => {
    checkDriveConnectionStatus();
  }, []);
  
  const checkDriveConnectionStatus = async () => {
    try {
      const response = await fetch('http://localhost:8080/api/cloud/drive-auth-status', {
        method: 'GET',
        credentials: 'include'
      });
      
      const data = await response.json();
      
      if (data.success && data.authenticated) {
        setDriveConnected(true);
        setDriveUserEmail(data.user_email || '');
        // Load initial folder tree
        loadInitialFolders();
      }
    } catch (error) {
      console.log('Drive connection check failed:', error);
    }
  };
  
  const loadInitialFolders = async () => {
    try {
      setFolderTreeLoading(true);
      console.log('🔄 Loading Google Drive folders...');
      console.log('🔑 Using session token:', driveSessionTokenRef.current ? 'Available' : 'None');
      console.log('🔑 Session token value:', driveSessionTokenRef.current ? `${driveSessionTokenRef.current.substring(0, 20)}...` : 'Empty');
      
      // Prepare headers with session token if available
      const headers = {
        'Content-Type': 'application/json',
        ...(driveSessionTokenRef.current && { 'Authorization': `Bearer ${driveSessionTokenRef.current}` })
      };
      
      // Use the new lazy folder endpoint with session token authentication
      const response = await fetch('http://localhost:8080/api/cloud/list_subfolders', {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({ 
          parent_id: 'root',
          max_results: 50 
        })
      });
      
      console.log('📡 Folder API response status:', response.status);
      const data = await response.json();
      console.log('📊 Folder API response data:', data);
      
      if (data.success && data.folders) {
        console.log(`✅ Found ${data.folders.length} real Google Drive folders`);
        setDriveFolders(data.folders);
      } else {
        console.error('⚠️ Google Drive API error:', data.message);
        setDriveFolders([]);
        
        // Show detailed error information for debugging
        if (data.requires_auth) {
          console.error('🔐 Authentication required - please reconnect Google Drive');
        } else if (data.error_type) {
          console.error(`🔧 API Error Type: ${data.error_type}`);
        }
      }
      
    } catch (error) {
      console.error('❌ Failed to load folders:', error);
      setDriveFolders([]);
    } finally {
      setFolderTreeLoading(false);
    }
  };

  // NEW: Handle tree folder selection
  const handleTreeFolderSelection = (folders: any[]) => {
    console.log('📁 Tree folder selection updated:', folders);
    setSelectedTreeFolders(folders);
    
    // Update step data with tree selection
    if (onStepChange) {
      onStepChange('video_source', { 
        sourceType: 'cloud_storage',
        selectedTreeFolders: folders,
        folderCount: folders.length
      });
    }
  };

  return (
    <Box
      w="100%"
      minH="fit-content"
    >
      {/* Header */}
      <Text fontSize={adaptiveConfig.fontSize.header} fontWeight="700" color={textColor} mb={adaptiveConfig.spacing.section}>
        📹 Step 4: Video Source Configuration
      </Text>

      <VStack spacing={adaptiveConfig.spacing.item} align="stretch">
        {/* Source Type Selection */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="8px">
            🎥 Video Source Type
          </Text>
          <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText} mb="12px">
            📁 Choose where your video files are located for processing
          </Text>
          <SimpleGrid columns={2} spacing="12px">
            <Box 
              bg={cardBg} 
              p="16px" 
              borderRadius="12px" 
              border="2px solid" 
              borderColor={selectedSourceType === 'local_storage' ? currentColors.brand500 : borderColor}
              cursor="pointer"
              onClick={() => {
                setSelectedSourceType('local_storage');
                onStepChange?.('video_source', { sourceType: 'local_storage' });
              }}
            >
              <Icon as={MdVideoLibrary} w="24px" h="24px" color={currentColors.brand500} mb="8px" />
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor}>Local Storage</Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>PC, External Drive, Network Mount</Text>
            </Box>
            
            <Box 
              bg={cardBg} 
              p="16px" 
              borderRadius="12px" 
              border="2px solid" 
              borderColor={selectedSourceType === 'cloud_storage' ? currentColors.brand500 : borderColor}
              cursor="pointer"
              onClick={() => {
                setSelectedSourceType('cloud_storage');
                onStepChange?.('video_source', { sourceType: 'cloud_storage' });
              }}
            >
              <Text fontSize={adaptiveConfig.fontSize.header} mb="8px">☁️</Text>
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor}>Cloud Storage</Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>Google Drive (OAuth2)</Text>
              {selectedSourceType === 'cloud_storage' && (
                <Text fontSize="10px" color="green.500" mt="4px">✓ Selected</Text>
              )}
            </Box>
          </SimpleGrid>
        </Box>

        {/* Video Input Directory - Show only when Local Storage is selected */}
        {selectedSourceType === 'local_storage' && (
          <Box>
            <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="8px">
              📂 Video Input Directory
            </Text>
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <VStack spacing="8px" align="stretch" mb="12px">
                <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
                  📝 Choose where your input videos are stored for processing
                </Text>
                <Text fontSize={adaptiveConfig.fontSize.small} color="orange.500" fontStyle="italic">
                  💡 Tip: Open folder in explorer, copy path from address bar and paste here
                </Text>
              </VStack>
              <Input
                value={inputPath}
                placeholder="Copy and paste input video folder path here..."
                size="sm"
                borderColor={borderColor}
                _focus={{ borderColor: currentColors.brand500 }}
                bg={bgColor}
                mb="12px"
                onFocus={(e) => {
                  // Clear input when user clicks to enter new path
                  if (inputPath === getDefaultInputPath()) {
                    setInputPath('');
                  }
                  e.target.select(); // Select all text for easy replacement
                }}
                onChange={(e) => {
                  setInputPath(e.target.value);
                  onStepChange?.('video_source', { inputPath: e.target.value });
                }}
              />
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
                📋 Input folder: {inputPath}
              </Text>
            </Box>
          </Box>
        )}

        {/* Google Drive Configuration - Show only when Cloud Storage is selected */}
        {selectedSourceType === 'cloud_storage' && (
          <Box>
            <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="8px">
              ☁️ Google Drive Setup
            </Text>
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <VStack spacing="12px" align="stretch">
                <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
                  🔐 Connect to Google Drive to access your video files stored in the cloud
                </Text>
                
                {/* Connection Status */}
                <Box borderRadius="8px" bg={cardBg} p="12px">
                  <VStack align="stretch" spacing="8px">
                    <HStack justify="space-between" align="center">
                      <VStack align="start" spacing="2px">
                        <Text fontSize={adaptiveConfig.fontSize.small} fontWeight="600" color={textColor}>
                          Connection Status
                        </Text>
                        {driveConnected ? (
                          <Text fontSize="12px" color="green.500">
                            ✅ Connected as {driveUserEmail}
                          </Text>
                        ) : (
                          <Text fontSize="12px" color="orange.500">
                            ⚠️ Not connected - Authentication required
                          </Text>
                        )}
                      </VStack>
                      {!driveConnected && (
                        <Button 
                          size="sm" 
                          colorScheme="brand"
                          isLoading={driveConnecting}
                          loadingText="Connecting..."
                          onClick={async () => {
                            setDriveConnecting(true);
                          try {
                            // First check Gmail authentication
                            const gmailResponse = await fetch('http://localhost:8080/api/cloud/gmail-auth-status', {
                              method: 'GET',
                              credentials: 'include'
                            });
                            
                            const gmailData = await gmailResponse.json();
                            
                            if (!gmailData.authenticated) {
                              // Need Gmail auth first
                              alert('Gmail authentication is required first. Please complete user login before connecting Google Drive.');
                              return;
                            }
                            
                            // Proceed with Google Drive auth
                            const response = await fetch('http://localhost:8080/api/cloud/drive-auth', {
                              method: 'POST',
                              headers: {
                                'Content-Type': 'application/json',
                              },
                              credentials: 'include',
                              body: JSON.stringify({
                                action: 'initiate_auth',
                                provider: 'google_drive'
                              })
                            });
                            
                            const data = await response.json();
                            
                            if (data.success && data.auth_url) {
                              // Open OAuth URL in popup window
                              const popup = window.open(
                                data.auth_url, 
                                'google_drive_auth', 
                                'width=500,height=600,scrollbars=yes,resizable=yes'
                              );
                              
                              // Listen for OAuth completion
                              const handleMessage = async (event) => {
                                console.log('📬 Received message:', event.data);
                                console.log('📬 Message keys:', Object.keys(event.data));
                                console.log('📬 Has session_token:', 'session_token' in event.data);
                                
                                // Allow messages from any origin during OAuth flow
                                if (event.data.type === 'OAUTH_SUCCESS') {
                                  console.log('Google Drive connected successfully!');
                                  console.log('🔑 Session token received:', event.data.session_token ? 'Yes' : 'No');
                                  console.log('🔑 Session token length:', event.data.session_token ? event.data.session_token.length : 'N/A');
                                  popup?.close();
                                  window.removeEventListener('message', handleMessage);
                                  
                                  // Update UI state to show connected status
                                  setDriveConnected(true);
                                  setDriveUserEmail(event.data.user_email || '');
                                  driveSessionTokenRef.current = event.data.session_token || '';
                                  setDriveConnecting(false);
                                  
                                  // Load initial folder tree with session token
                                  loadInitialFolders();
                                  
                                } else if (event.data.type === 'OAUTH_ERROR') {
                                  console.error('Google Drive connection failed:', event.data.error);
                                  popup?.close();
                                  window.removeEventListener('message', handleMessage);
                                  setDriveConnecting(false);
                                  
                                  // Show detailed error to user
                                  const errorMessage = event.data.error || 'Unknown authentication error';
                                  alert(`❌ Google Drive connection failed!\n\nError: ${errorMessage}\n\nPlease try:\n1. Clear browser cookies\n2. Disable ad blockers\n3. Try in incognito mode\n4. Check internet connection`);
                                }
                              };
                              
                              window.addEventListener('message', handleMessage);
                              
                              // Enhanced popup closed handling with retry
                              const checkClosed = setInterval(async () => {
                                if (popup?.closed) {
                                  clearInterval(checkClosed);
                                  window.removeEventListener('message', handleMessage);
                                  
                                  // Enhanced fallback: Check connection status multiple times
                                  console.log('🔄 Popup closed, checking connection status...');
                                  
                                  let retryCount = 0;
                                  const maxRetries = 3;
                                  const checkStatus = async () => {
                                    retryCount++;
                                    try {
                                      const statusResponse = await fetch('http://localhost:8080/api/cloud/drive-auth-status', {
                                        method: 'GET',
                                        credentials: 'include'
                                      });
                                      
                                      const statusData = await statusResponse.json();
                                      
                                      if (statusData.success && statusData.authenticated) {
                                        console.log(`✅ Connection confirmed via status check (attempt ${retryCount})`);
                                        setDriveConnected(true);
                                        setDriveUserEmail(statusData.user_email || '');
                                        setDriveConnecting(false);
                                        loadInitialFolders();
                                      } else if (retryCount < maxRetries) {
                                        console.log(`⏳ Connection not found, retrying... (${retryCount}/${maxRetries})`);
                                        setTimeout(checkStatus, 2000); // Wait 2 seconds before retry
                                      } else {
                                        console.log('❌ Connection not found after all retries');
                                        setDriveConnecting(false);
                                      }
                                    } catch (error) {
                                      console.error(`Error checking connection status (attempt ${retryCount}):`, error);
                                      if (retryCount < maxRetries) {
                                        setTimeout(checkStatus, 2000);
                                      } else {
                                        setDriveConnecting(false);
                                      }
                                    }
                                  };
                                  
                                  setTimeout(checkStatus, 1000); // Initial delay
                                }
                              }, 1000);
                              
                            } else {
                              console.error('Failed to initiate OAuth:', data.message);
                              if (data.error_code === 'gmail_auth_required') {
                                alert('Please complete Gmail authentication first before connecting Google Drive.');
                              } else {
                                alert(`Failed to start Google Drive authentication: ${data.message}`);
                              }
                            }
                          } catch (error) {
                            console.error('Error initiating Google Drive auth:', error);
                            alert('Failed to connect to authentication service. Please check if the backend is running.');
                            setDriveConnecting(false);
                          }
                        }}
                      >
                        Connect Google Drive
                      </Button>
                      )}
                      
                      {driveConnected && (
                        <Button 
                          size="sm" 
                          variant="outline"
                          colorScheme="red"
                          onClick={async () => {
                            try {
                              await fetch('http://localhost:8080/api/cloud/disconnect', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                credentials: 'include',
                                body: JSON.stringify({ provider: 'google_drive', user_email: driveUserEmail })
                              });
                              
                              setDriveConnected(false);
                              setDriveUserEmail('');
                              driveSessionTokenRef.current = '';
                              setDriveFolders([]);
                              setSelectedFolder(null);
                            } catch (error) {
                              console.error('Error disconnecting Google Drive:', error);
                            }
                          }}
                        >
                          Disconnect
                        </Button>
                      )}
                    </HStack>
                    
                    {/* Requirements Info or Manual Refresh */}
                    {!driveConnected ? (
                      <Box bg={cardBg} p="8px" borderRadius="6px" border="1px solid" borderColor="yellow.400">
                        <Text fontSize="11px" color="yellow.600">
                          ℹ️ <strong>Requirement:</strong> Gmail authentication must be completed first before connecting Google Drive
                        </Text>
                      </Box>
                    ) : (
                      <HStack justify="space-between" align="center">
                        <Text fontSize="11px" color="green.600">
                          ✅ Google Drive connected successfully
                        </Text>
                        <Button 
                          size="xs" 
                          variant="ghost"
                          onClick={() => checkDriveConnectionStatus()}
                        >
                          🔄 Refresh
                        </Button>
                      </HStack>
                    )}
                    
                    {/* Debug: Manual check button when stuck in connecting state */}
                    {driveConnecting && (
                      <Box bg={cardBg} p="8px" borderRadius="6px" border="1px solid" borderColor="orange.400">
                        <HStack justify="space-between" align="center">
                          <Text fontSize="11px" color="orange.600">
                            Stuck connecting? Try manual check:
                          </Text>
                          <Button 
                            size="xs" 
                            colorScheme="orange"
                            onClick={async () => {
                              console.log('🔧 Manual connection check triggered');
                              setDriveConnecting(false);
                              await checkDriveConnectionStatus();
                            }}
                          >
                            Check Status
                          </Button>
                        </HStack>
                      </Box>
                    )}
                  </VStack>
                </Box>

                {/* Google Drive Folder Tree */}
                <Box 
                  border="1px solid" 
                  borderColor={borderColor} 
                  borderRadius="8px" 
                  overflow="visible"
                >
                  <GoogleDriveFolderTree
                    session_token={driveSessionTokenRef.current}
                    onFoldersSelected={handleTreeFolderSelection}
                    maxDepth={3}
                  />
                </Box>

              </VStack>
            </Box>
          </Box>
        )}

        {/* Camera Settings */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            ⚙️ Camera Settings
          </Text>
          <SimpleGrid columns={2} spacing="12px">
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} mb="8px">
                Resolution:
              </Text>
              <Select size="sm" borderColor={borderColor} defaultValue="1080p" onChange={(e) => onStepChange?.('video_source', { resolution: e.target.value })}>
                <option value="4K">4K (3840x2160)</option>
                <option value="1080p">1080p (1920x1080)</option>
                <option value="720p">720p (1280x720)</option>
                <option value="480p">480p (640x480)</option>
              </Select>
            </Box>
            
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} mb="8px">
                Frame Rate:
              </Text>
              <Select size="sm" borderColor={borderColor} defaultValue="30" onChange={(e) => onStepChange?.('video_source', { frameRate: e.target.value })}>
                <option value="60">60 FPS</option>
                <option value="30">30 FPS</option>
                <option value="24">24 FPS</option>
                <option value="15">15 FPS</option>
              </Select>
            </Box>
          </SimpleGrid>
        </Box>


      </VStack>
    </Box>
  );
}

// Step 5: Packing Area Canvas
function PackingAreaCanvas({ adaptiveConfig, onStepChange }: CanvasComponentProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  const cardBg = useColorModeValue('gray.50', 'navy.700');

  return (
    <Box
      w="100%"
      minH="fit-content"
    >
      {/* Header */}
      <Text fontSize={adaptiveConfig.fontSize.header} fontWeight="700" color={textColor} mb={adaptiveConfig.spacing.section}>
        📦 Step 5: Packing Area Detection
      </Text>

      <VStack spacing={adaptiveConfig.spacing.item} align="stretch">
        {/* Detection Zone Preview */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            🎯 Detection Zones
          </Text>
          <Box 
            bg={cardBg} 
            p="16px" 
            borderRadius="12px"
            border="2px dashed" 
            borderColor={currentColors.brand500}
            minH="200px"
            position="relative"
            display="flex"
            alignItems="center"
            justifyContent="center"
          >
            <Box textAlign="center">
              <Text fontSize={adaptiveConfig.fontSize.header} mb="8px">📹</Text>
              <Text fontSize={adaptiveConfig.fontSize.body} color={secondaryText} mb="12px">
                Camera preview area
              </Text>
              <Button 
                size="sm" 
                colorScheme="brand" 
                variant="outline"
                onClick={() => onStepChange?.('packing_area', { defineZone: true })}
              >
                Define Detection Zone
              </Button>
            </Box>
            
            {/* Sample ROI Box */}
            <Box
              position="absolute"
              top="40px"
              left="40px"
              w="120px"
              h="80px"
              border="2px solid"
              borderColor={currentColors.brand500}
              bg={`${currentColors.brand500}20`}
              borderRadius="8px"
              display="flex"
              alignItems="center"
              justifyContent="center"
            >
              <Text fontSize={adaptiveConfig.fontSize.small} color={currentColors.brand500} fontWeight="bold">
                Zone 1
              </Text>
            </Box>
          </Box>
        </Box>

        {/* Detection Settings */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            ⚡ Detection Triggers
          </Text>
          <SimpleGrid columns={2} spacing="12px">
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} mb="8px">
                Motion Sensitivity:
              </Text>
              <HStack spacing="8px">
                <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>Low</Text>
                <Box flex="1" bg={borderColor} h="4px" borderRadius="2px" position="relative">
                  <Box
                    bg={currentColors.brand500}
                    h="4px"
                    w="70%"
                    borderRadius="2px"
                  />
                </Box>
                <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>High</Text>
              </HStack>
            </Box>
            
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} mb="8px">
                Object Size Filter:
              </Text>
              <Select size="sm" borderColor={borderColor} defaultValue="medium" onChange={(e) => onStepChange?.('packing_area', { objectSize: e.target.value })}>
                <option value="any">Any Size</option>
                <option value="small">Small Objects</option>
                <option value="medium">Medium Objects</option>
                <option value="large">Large Objects Only</option>
              </Select>
            </Box>
          </SimpleGrid>
        </Box>

        {/* Alert Settings */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            🚨 Alert Settings
          </Text>
          <VStack spacing="8px" align="stretch">
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('packing_area', { instantNotifications: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Instant notifications</Text>
            </Checkbox>
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('packing_area', { emailAlerts: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Email alerts</Text>
            </Checkbox>
            <Checkbox colorScheme="brand" onChange={(e) => onStepChange?.('packing_area', { soundAlarm: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Sound alarm</Text>
            </Checkbox>
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('packing_area', { autoRecord: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Auto-record on detection</Text>
            </Checkbox>
          </VStack>
        </Box>

        {/* Detection Stats */}
        <Box
          bg={cardBg}
          borderRadius="12px"
          p="16px"
          border="1px solid"
          borderColor="purple.400"
        >
          <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor} mb="8px">
            📈 Detection Statistics:
          </Text>
          <VStack align="stretch" spacing="4px">
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>Today:</strong> 47 detections, 23 alerts sent
            </Text>
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>This Week:</strong> 312 detections, 85% accuracy
            </Text>
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>Active Zones:</strong> 2 configured, 1 active
            </Text>
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>Last Detection:</strong> 2 minutes ago
            </Text>
          </VStack>
        </Box>
      </VStack>
    </Box>
  );
}

// Step 6: Timing Canvas
function TimingCanvas({ adaptiveConfig, onStepChange }: CanvasComponentProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  const cardBg = useColorModeValue('gray.50', 'navy.700');

  return (
    <Box
      w="100%"
      minH="fit-content"
    >
      {/* Header */}
      <Text fontSize={adaptiveConfig.fontSize.header} fontWeight="700" color={textColor} mb={adaptiveConfig.spacing.section}>
        ⏱️ Step 6: Timing & Performance
      </Text>

      <VStack spacing={adaptiveConfig.spacing.item} align="stretch">
        {/* Processing Speed Settings */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            🚀 Processing Speed
          </Text>
          <SimpleGrid columns={3} spacing="12px">
            <Box 
              bg={cardBg} 
              p="16px" 
              borderRadius="12px" 
              border="1px solid" 
              borderColor={borderColor}
              textAlign="center"
              cursor="pointer"
              onClick={() => onStepChange?.('timing', { processingSpeed: 'slow' })}
            >
              <Text fontSize={adaptiveConfig.fontSize.header} mb="8px">🐌</Text>
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor}>Slow</Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>High Accuracy</Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>3-5 seconds</Text>
            </Box>
            
            <Box 
              bg={cardBg} 
              p="16px" 
              borderRadius="12px" 
              border="2px solid" 
              borderColor={currentColors.brand500}
              textAlign="center"
              cursor="pointer"
              onClick={() => onStepChange?.('timing', { processingSpeed: 'medium' })}
            >
              <Text fontSize={adaptiveConfig.fontSize.header} mb="8px">⚡</Text>
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor}>Medium</Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>Balanced</Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>1-2 seconds</Text>
            </Box>
            
            <Box 
              bg={cardBg} 
              p="16px" 
              borderRadius="12px" 
              border="1px solid" 
              borderColor={borderColor}
              textAlign="center"
              cursor="pointer"
              onClick={() => onStepChange?.('timing', { processingSpeed: 'fast' })}
            >
              <Text fontSize={adaptiveConfig.fontSize.header} mb="8px">🏃</Text>
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor}>Fast</Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>Real-time</Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>&lt; 1 second</Text>
            </Box>
          </SimpleGrid>
        </Box>

        {/* Buffer Settings */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            📹 Buffer Settings
          </Text>
          <SimpleGrid columns={2} spacing="12px">
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} mb="8px">
                Pre-event Buffer:
              </Text>
              <HStack spacing="8px">
                <Input
                  placeholder="5"
                  size="sm"
                  w="60px"
                  borderColor={borderColor}
                  _focus={{ borderColor: currentColors.brand500 }}
                  onChange={(e) => onStepChange?.('timing', { preEventBuffer: e.target.value })}
                />
                <Text fontSize={adaptiveConfig.fontSize.body} color={secondaryText}>seconds before detection</Text>
              </HStack>
            </Box>
            
            <Box bg={cardBg} p="16px" borderRadius="12px">
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor} mb="8px">
                Post-event Buffer:
              </Text>
              <HStack spacing="8px">
                <Input
                  placeholder="10"
                  size="sm"
                  w="60px"
                  borderColor={borderColor}
                  _focus={{ borderColor: currentColors.brand500 }}
                  onChange={(e) => onStepChange?.('timing', { postEventBuffer: e.target.value })}
                />
                <Text fontSize={adaptiveConfig.fontSize.body} color={secondaryText}>seconds after detection</Text>
              </HStack>
            </Box>
          </SimpleGrid>
        </Box>

        {/* Performance Optimization */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            ⚙️ Performance Optimization
          </Text>
          <VStack spacing="8px" align="stretch">
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('timing', { gpuAcceleration: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>GPU acceleration (if available)</Text>
            </Checkbox>
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('timing', { multiThreaded: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Multi-threaded processing</Text>
            </Checkbox>
            <Checkbox colorScheme="brand" onChange={(e) => onStepChange?.('timing', { lowPowerMode: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Low-power mode (battery saving)</Text>
            </Checkbox>
            <Checkbox defaultChecked colorScheme="brand" onChange={(e) => onStepChange?.('timing', { adaptiveQuality: e.target.checked })}>
              <Text fontSize={adaptiveConfig.fontSize.body}>Adaptive quality based on load</Text>
            </Checkbox>
          </VStack>
        </Box>

        {/* Performance Stats */}
        <Box
          bg={cardBg}
          borderRadius="12px"
          p="16px"
          border="1px solid"
          borderColor="orange.400"
        >
          <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor} mb="8px">
            📊 Current Performance:
          </Text>
          <VStack align="stretch" spacing="4px">
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>Processing Time:</strong> 1.2s average (Medium mode)
            </Text>
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>CPU Usage:</strong> 45% average, 78% peak
            </Text>
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>Memory Usage:</strong> 2.1 GB / 8 GB (26%)
            </Text>
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
              <strong>Queue Status:</strong> 3 videos pending processing
            </Text>
          </VStack>
        </Box>
      </VStack>
    </Box>
  );
}