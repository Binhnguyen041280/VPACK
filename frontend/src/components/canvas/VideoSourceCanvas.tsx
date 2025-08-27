'use client';

import {
  Box,
  Flex,
  Text,
  Button,
  VStack,
  HStack,
  Input,
  Select,
  SimpleGrid,
  useColorModeValue,
} from '@chakra-ui/react';
import { MdVideoLibrary } from 'react-icons/md';
import { useColorTheme } from '@/contexts/ColorThemeContext';
import GoogleDriveFolderTree from './GoogleDriveFolderTree';
import { useState, useEffect, useRef } from 'react';
import React from 'react';

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

// Enhanced Canvas Component Props
interface CanvasComponentProps {
  onStepChange?: (stepName: string, data: any) => void;
  adaptiveConfig: AdaptiveConfig;
  availableHeight: number;
  // Chat-controlled props
  brandName?: string;
  isLoading?: boolean;
  // Step 2 props
  locationTimeData?: {
    country: string;
    timezone: string;
    language: string;
    working_days: string[];
    from_time: string;
    to_time: string;
  };
  locationTimeLoading?: boolean;
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
        📹 Step 3: Video Source Configuration
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
              <Text fontSize="24px" mb="8px">💾</Text>
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

export default VideoSourceCanvas;