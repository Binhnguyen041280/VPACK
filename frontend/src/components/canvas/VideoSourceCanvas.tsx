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
  Checkbox,
  Spinner,
  Alert,
  AlertIcon,
  AlertDescription,
  Wrap,
  WrapItem,
} from '@chakra-ui/react';
import { MdVideoLibrary } from 'react-icons/md';
import { useColorTheme } from '@/contexts/ColorThemeContext';
import GoogleDriveFolderTree from './GoogleDriveFolderTree';
import { useState, useEffect, useRef } from 'react';
import React from 'react';
import { stepConfigService } from '@/services/stepConfigService';

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

// Step 3: Video Source Canvas
function VideoSourceCanvas({ adaptiveConfig, onStepChange }: CanvasComponentProps) {
  const { currentColors } = useColorTheme();
  const bgColor = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const textColor = useColorModeValue('navy.700', 'white');
  const secondaryText = useColorModeValue('gray.600', 'gray.400');
  const cardBg = useColorModeValue('gray.50', 'navy.700');
  const selectionBoxBg = useColorModeValue('gray.50', 'navy.700');

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
  
  const [inputPath, setInputPath] = useState(''); // No default path to avoid confusion
  
  // NEW: V.PACK Step 3 Enhancement - Auto-scan camera folders
  const [detectedFolders, setDetectedFolders] = useState<{name: string, path: string}[]>([]);
  const [selectedCameras, setSelectedCameras] = useState<string[]>([]);
  const [scanningFolders, setScanningFolders] = useState(false);
  const [scanError, setScanError] = useState<string>('');
  const scanTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  // Google Drive connection state
  const [driveConnected, setDriveConnected] = useState(false);
  const [driveUserEmail, setDriveUserEmail] = useState('');
  const [driveConnecting, setDriveConnecting] = useState(false);
  const [driveFolders, setDriveFolders] = useState<any[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<any>(null);
  const [folderTreeLoading, setFolderTreeLoading] = useState(false);

  // Gmail authentication state
  const [gmailAuthenticated, setGmailAuthenticated] = useState(false);
  
  // NEW: Tree-based folder selection
  const [selectedTreeFolders, setSelectedTreeFolders] = useState<any[]>([]);
  
  // UPSERT Pattern: Current active source state
  const [currentActiveSource, setCurrentActiveSource] = useState<any>(null);
  const [sourceStatistics, setSourceStatistics] = useState<any>(null);
  
  // Session token stored in ref to avoid hooks order issues
  const driveSessionTokenRef = React.useRef<string>('');
  
  // Check Google Drive connection status on component mount
  React.useEffect(() => {
    // Set setup step flag for backend
    const setSetupStep = async () => {
      try {
        await fetch('http://localhost:8080/api/cloud/set-setup-step', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({ step: 'video-source' })
        });
        console.log('✅ Setup step set to video-source');
      } catch (error) {
        console.error('❌ Failed to set setup step:', error);
      }
    };

    setSetupStep();
    checkGmailAuthStatus();
    checkDriveConnectionStatus();
    loadCurrentVideoSourceState();
  }, []);

  // UPSERT Pattern: Load current video source state on mount
  const loadCurrentVideoSourceState = async () => {
    try {
      console.log('🔄 Loading current video source state...');
      
      const result = await stepConfigService.fetchVideoSourceState();
      
      if (result.success && result.data) {
        const data = result.data;
        
        console.log('📊 Current video source state:', data);
        
        // Check if we have a current active source
        if (data.current_source) {
          const currentSource = data.current_source;
          console.log(`✅ Found active source: ${currentSource.name} (Type: ${currentSource.source_type})`);
          
          // Set current active source state
          setCurrentActiveSource(currentSource);
          setSourceStatistics(data.statistics || null);
          
          // Set source type based on current source
          const uiSourceType = currentSource.original_source_type || 
            (currentSource.source_type === 'local' ? 'local_storage' : 'cloud_storage');
          setSelectedSourceType(uiSourceType as 'local_storage' | 'cloud_storage');
          
          // Set input path
          setInputPath(data.inputPath || '');
          
          // Set detected folders and selected cameras
          if (data.detected_folders) {
            setDetectedFolders(data.detected_folders);
          }
          if (data.selectedCameras) {
            setSelectedCameras(data.selectedCameras);
          }
          
          // Set tree folders for cloud storage
          if (data.selected_tree_folders) {
            setSelectedTreeFolders(data.selected_tree_folders);
          }
          
          // Update step data
          if (onStepChange) {
            onStepChange('video_source', {
              sourceType: uiSourceType,
              inputPath: data.inputPath,
              detectedFolders: data.detected_folders,
              selectedCameras: data.selectedCameras,
              selectedTreeFolders: data.selected_tree_folders,
              currentSource: currentSource
            });
          }
          
          console.log(`🔄 Restored video source state: ${uiSourceType}`);
          
        } else {
          // No current source - set default to local_storage
          console.log('📍 No active source found - setting default to local storage');
          setSelectedSourceType('local_storage');
          
          // Fallback to backward compatibility data
          if (data.backward_compatibility) {
            const compat = data.backward_compatibility;
            if (compat.processing_config_input_path) {
              setInputPath(compat.processing_config_input_path);
              setSelectedCameras(compat.processing_config_selected_cameras || []);
              console.log('📦 Using backward compatibility data');
            }
          }
        }
        
      } else {
        // No data at all - ensure default is local_storage
        console.log('📍 No video source data found - setting default to local storage');
        setSelectedSourceType('local_storage');
      }
      
    } catch (error) {
      console.error('❌ Error loading video source state:', error);
      // On error, also default to local storage
      setSelectedSourceType('local_storage');
    }
  };

  // NEW: Auto-scan subdirectories when input path changes (with debounce)
  React.useEffect(() => {
    // Clear previous timeout
    if (scanTimeoutRef.current) {
      clearTimeout(scanTimeoutRef.current);
    }
    
    // Clear previous results
    setDetectedFolders([]);
    setSelectedCameras([]);
    setScanError('');
    
    // Only scan if we have a valid path and local storage is selected
    if (!inputPath.trim() || selectedSourceType !== 'local_storage') {
      return;
    }
    
    // Debounce API call by 500ms to prevent excessive requests
    scanTimeoutRef.current = setTimeout(async () => {
      await scanFoldersInPath(inputPath);
    }, 500);
    
    // Cleanup timeout on unmount
    return () => {
      if (scanTimeoutRef.current) {
        clearTimeout(scanTimeoutRef.current);
      }
    };
  }, [inputPath, selectedSourceType]);

  // Function to scan folders in the given path
  const scanFoldersInPath = async (path: string) => {
    if (!path.trim()) return;
    
    try {
      setScanningFolders(true);
      setScanError('');
      
      console.log(`🔍 Scanning folders in: ${path}`);
      
      const response = await fetch('http://localhost:8080/api/config/scan-folders', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ path: path })
      });
      
      const data = await response.json();
      console.log('📊 Scan result:', data);
      
      if (data.success && data.folders) {
        setDetectedFolders(data.folders);
        setScanError('');
        
        // Auto-select all detected cameras by default
        const folderNames = data.folders.map((f: any) => f.name);
        setSelectedCameras(folderNames);
        
        // Update step data
        if (onStepChange) {
          onStepChange('video_source', {
            sourceType: 'local_storage',
            inputPath: path,
            detectedFolders: data.folders,
            selectedCameras: folderNames
          });
        }
        
        console.log(`✅ Found ${data.folders.length} camera folders, auto-selected all`);
      } else {
        setDetectedFolders([]);
        setSelectedCameras([]);
        
        // ENHANCED: Show concise error messages
        let errorMessage = 'Failed to scan folders';
        if (data.message) {
          if (data.message.includes('does not exist')) {
            errorMessage = 'Path does not exist';
          } else if (data.message.includes('Permission denied')) {
            errorMessage = 'Permission denied';
          } else if (data.message.includes('not a directory')) {
            errorMessage = 'Invalid directory path';
          } else if (data.message.includes('No subdirectories')) {
            errorMessage = 'No folders found';
          } else {
            errorMessage = 'Invalid path';
          }
        }
        
        setScanError(errorMessage);
        console.log(`⚠️ Scan failed: ${data.message}`);
      }
      
    } catch (error) {
      console.error('❌ Error scanning folders:', error);
      setDetectedFolders([]);
      setSelectedCameras([]);
      setScanError('Connection error');
    } finally {
      setScanningFolders(false);
    }
  };

  // Handle camera checkbox selection
  const handleCameraToggle = (cameraName: string) => {
    let newSelection: string[];
    
    if (selectedCameras.includes(cameraName)) {
      // Deselect camera
      newSelection = selectedCameras.filter(c => c !== cameraName);
    } else {
      // Select camera
      newSelection = [...selectedCameras, cameraName];
    }
    
    setSelectedCameras(newSelection);
    
    // Update step data for UI
    if (onStepChange) {
      onStepChange('video_source', {
        sourceType: 'local_storage',
        inputPath: inputPath,
        detectedFolders: detectedFolders,
        selectedCameras: newSelection
      });
    }
    
    // Auto-save to backend (debounced)
    saveVideoSourceConfig('local_storage', inputPath, detectedFolders, newSelection);
    
    console.log(`📷 Camera selection updated: ${newSelection.join(', ')}`);
  };

  // Save video source configuration to backend with debounce (UPSERT pattern)
  const saveVideoSourceConfig = React.useCallback(
    debounceFunction(async (sourceType: string, path: string, folders: any[], cameras: string[], treeFolders?: any[]) => {
      try {
        console.log('💾 Saving video source configuration (UPSERT pattern)...');
        console.log(`   Source Type: ${sourceType}`);
        console.log(`   Input Path: ${path}`);
        console.log(`   Selected Cameras: ${cameras.length}`);
        console.log(`   Tree Folders: ${treeFolders ? treeFolders.length : 0}`);
        
        // Validation: Don't save cloud storage with no folders selected
        if (sourceType === 'cloud_storage') {
          if (!treeFolders || treeFolders.length === 0) {
            console.log('⚠️ Skipping save: Cloud storage requires at least one folder selected');
            return;
          }
        }
        
        // Validation: Don't save local storage with no path or cameras
        if (sourceType === 'local_storage') {
          if (!path || !path.trim()) {
            console.log('⚠️ Skipping save: Local storage requires input path');
            return;
          }
          if (!cameras || cameras.length === 0) {
            console.log('⚠️ Skipping save: Local storage requires at least one camera selected');
            return;
          }
        }
        
        const payload = {
          sourceType: sourceType,
          inputPath: path,
          detectedFolders: folders,
          selectedCameras: cameras,
          selected_tree_folders: treeFolders || []
        };
        
        const result = await stepConfigService.updateVideoSourceState(payload);
        
        if (result.success) {
          console.log('✅ Video source configuration saved successfully (UPSERT)');
          
          // Log UPSERT-specific response data
          if (result.data.upsert_operation) {
            console.log(`   🆔 Video Source ID: ${result.data.videoSourceId}`);
            console.log(`   📝 Source Name: ${result.data.videoSourceName}`);
            console.log(`   🔄 Single Source Mode: Active`);
          }
          
          // Handle cloud storage response
          if (sourceType === 'cloud_storage' && result.data.defaultSyncPath) {
            console.log(`   ☁️ Default Sync Path: ${result.data.defaultSyncPath}`);
            console.log(`   📁 Selected Tree Folders: ${result.data.selectedTreeFoldersCount || 0}`);
          }
          
        } else {
          console.error('❌ Failed to save video source configuration:', result.error);
        }
        
      } catch (error) {
        console.error('❌ Error saving video source configuration:', error);
      }
    }, 1000), // 1 second debounce
    []
  );

  // Utility debounce function
  function debounceFunction<T extends (...args: any[]) => any>(func: T, delay: number): T {
    let timeoutId: NodeJS.Timeout;
    return ((...args: any[]) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func.apply(null, args), delay);
    }) as T;
  }
  
  const checkGmailAuthStatus = async () => {
    try {
      const response = await fetch('http://localhost:8080/api/cloud/gmail-auth-status', {
        method: 'GET',
        credentials: 'include'
      });

      const data = await response.json();
      console.log('🔍 Gmail auth status:', data);

      if (data.success && data.authenticated) {
        setGmailAuthenticated(true);
        console.log('✅ Gmail authenticated');
      } else {
        setGmailAuthenticated(false);
        console.log('❌ Gmail not authenticated');
      }
    } catch (error) {
      console.log('Gmail auth check failed:', error);
      setGmailAuthenticated(false);
    }
  };

  const checkDriveConnectionStatus = async () => {
    try {
      const response = await fetch('http://localhost:8080/api/cloud/drive-auth-status', {
        method: 'GET',
        credentials: 'include'
      });

      const data = await response.json();
      console.log('🔍 Drive auth status:', data);

      // IMPORTANT: Always start as disconnected in video-source step
      // User must click Connect button to authenticate Drive
      // This prevents showing stale "connected" status from backend
      if (data.setup_mode || !data.authenticated) {
        console.log('🎯 Setup mode or not authenticated - showing as disconnected');
        console.log('🔴 DEBUG: setDriveConnected(false) - require manual Connect');
        setDriveConnected(false);
        setDriveUserEmail('');
        setDriveFolders([]);
      } else {
        // Even if backend says authenticated, verify with folder test
        console.log('⚠️ Backend reports authenticated - but user must click Connect for this session');
        setDriveConnected(false);
        setDriveUserEmail('');
        setDriveFolders([]);
      }
    } catch (error) {
      console.log('Drive connection check failed:', error);
      setDriveConnected(false);
      setDriveUserEmail('');
      setDriveFolders([]);
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
    
    // Auto-save cloud storage configuration (UPSERT pattern)
    saveVideoSourceConfig('cloud_storage', '', [], [], folders);
    
    console.log(`☁️ Cloud folder selection updated: ${folders.length} folders selected`);
  };

  return (
    <Box
      w="100%"
      maxW="450px"
      minH="fit-content"
      mx="auto"
      css={{
        '@media (max-width: 450px)': {
          maxW: '100%',
          px: '12px',
        }
      }}
    >
      {/* Header */}
      <Text fontSize={adaptiveConfig.fontSize.header} fontWeight="700" color={textColor} mb={adaptiveConfig.spacing.section}>
        📹 Step 3: Video Source Configuration | Single Source Mode
      </Text>

      {/* Current Active Source Indicator (UPSERT Pattern) */}
      {currentActiveSource && (
        <Box 
          bg="green.50" 
          border="1px solid" 
          borderColor="green.200"
          borderRadius="8px"
          p="12px"
          mb={adaptiveConfig.spacing.section}
        >
          <HStack justify="space-between" align="center">
            <VStack align="start" spacing="2px">
              <Text fontSize="xs" fontWeight="600" color="green.700">
                🎯 Current Active Source
              </Text>
              <Text fontSize="sm" fontWeight="500" color="green.800">
                {currentActiveSource.name} ({currentActiveSource.source_type === 'local' ? 'Local Storage' : 'Cloud Storage'})
              </Text>
            </VStack>
            <VStack align="end" spacing="2px">
              <Text fontSize="xs" color="green.600">
                📊 Cameras: {sourceStatistics?.cameras?.length || 0}
              </Text>
              <Text fontSize="xs" color="green.600">
                ⏰ {new Date(currentActiveSource.created_at).toLocaleString()}
              </Text>
            </VStack>
          </HStack>
        </Box>
      )}

      <VStack spacing={adaptiveConfig.spacing.item} align="stretch" maxW="100%">
        {/* Source Type Selection */}
        <Box>
          <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="12px">
            🎥 Video Source Type
          </Text>
          {currentActiveSource && (
            <Text fontSize="xs" color="orange.600" fontWeight="500" mb="8px">
              💡 Selecting a new source will replace the current one
            </Text>
          )}
          <Box bg={cardBg} p="16px" borderRadius="12px">
            <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText} mb="12px">
              📁 Choose where your video files are located for processing
            </Text>
            <SimpleGrid columns={2} spacing="12px" maxW="100%">
              <Box 
                bg={bgColor} 
                p="16px" 
                borderRadius="12px" 
                border="2px solid" 
                borderColor={selectedSourceType === 'local_storage' ? currentColors.brand500 : borderColor}
                cursor="pointer"
                onClick={() => {
                  setSelectedSourceType('local_storage');
                  // Clear cloud storage state when switching to local
                  setSelectedTreeFolders([]);
                  onStepChange?.('video_source', { sourceType: 'local_storage' });
                }}
              >
              <Text fontSize="24px" mb="8px">💾</Text>
              <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor}>Local Storage</Text>
              <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>PC, External Drive, Network Mount</Text>
            </Box>
            
              
              <Box 
                bg={bgColor} 
                p="16px" 
                borderRadius="12px" 
                border="2px solid" 
                borderColor={selectedSourceType === 'cloud_storage' ? currentColors.brand500 : borderColor}
                cursor="pointer"
                onClick={() => {
                  setSelectedSourceType('cloud_storage');
                  // Clear local storage state when switching to cloud
                  setInputPath('');
                  setDetectedFolders([]);
                  setSelectedCameras([]);
                  onStepChange?.('video_source', { sourceType: 'cloud_storage' });
                }}
              >
                <Text fontSize="24px" mb="8px">☁️</Text>
                <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="600" color={textColor}>Cloud Storage</Text>
                <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>Google Drive (OAuth2)</Text>
                {selectedSourceType === 'cloud_storage' && (
                  <Text fontSize="10px" color="green.500" mt="4px">✓ Selected</Text>
                )}
              </Box>
            </SimpleGrid>
          </Box>
        </Box>

        {/* Video Input Directory - Show only when Local Storage is selected */}
        {selectedSourceType === 'local_storage' && (
          <Box>
            <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="8px">
              📂 Video Input Directory
            </Text>
            <Box bg={cardBg} p="16px" borderRadius="12px" maxW="100%" overflow="hidden">
              <VStack spacing="8px" align="stretch" mb="12px" maxW="100%">
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
                maxW="100%"
                onFocus={(e) => {
                  e.target.select(); // Select all text for easy replacement
                }}
                onChange={(e) => {
                  setInputPath(e.target.value);
                }}
              />
              <Text 
                fontSize={adaptiveConfig.fontSize.small} 
                color={secondaryText}
                maxW="400px"
                overflow="hidden"
                textOverflow="ellipsis"
                whiteSpace="nowrap"
                textAlign="right"
                title={inputPath || 'No path specified'}
              >
                📋 Input folder: {inputPath || 'No path specified'}
              </Text>
              
              {/* NEW: Camera Folders Auto-Detection */}
              {inputPath && (
                <Box mt="16px">
                  {/* Scanning Status */}
                  {scanningFolders && (
                    <HStack spacing="8px" mb="12px">
                      <Spinner size="sm" color={currentColors.brand500} />
                      <Text fontSize={adaptiveConfig.fontSize.small} color={currentColors.brand500}>
                        🔍 Scanning for camera folders...
                      </Text>
                    </HStack>
                  )}
                  
                  {/* Scan Error */}
                  {scanError && !scanningFolders && (
                    <Alert status="warning" mb="12px" borderRadius="8px">
                      <AlertIcon />
                      <AlertDescription fontSize={adaptiveConfig.fontSize.small}>
                        {scanError}
                      </AlertDescription>
                    </Alert>
                  )}
                  
                  {/* Detected Camera Folders */}
                  {detectedFolders.length > 0 && !scanningFolders && (
                    <Box>
                      <Text fontSize={adaptiveConfig.fontSize.title} fontWeight="600" color={textColor} mb="8px">
                        📷 Detected Camera Folders
                      </Text>
                      <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText} mb="12px">
                        ✅ Select cameras you want to process (all selected by default)
                      </Text>
                      
                      {/* Camera Selection Grid */}
                      <Box
                        bg={selectionBoxBg}
                        p="16px"
                        borderRadius="12px"
                        border="1px solid"
                        borderColor={borderColor}
                      >
                        <Wrap spacing="12px">
                          {detectedFolders.map((folder) => (
                            <WrapItem key={folder.name}>
                              <Checkbox
                                colorScheme="brand"
                                isChecked={selectedCameras.includes(folder.name)}
                                onChange={() => handleCameraToggle(folder.name)}
                                size="md"
                              >
                                <VStack align="start" spacing="2px" ml="8px">
                                  <Text fontSize={adaptiveConfig.fontSize.body} fontWeight="500" color={textColor}>
                                    📹 {folder.name}
                                  </Text>
                                  <Text fontSize="10px" color={secondaryText} noOfLines={1}>
                                    {folder.path}
                                  </Text>
                                </VStack>
                              </Checkbox>
                            </WrapItem>
                          ))}
                        </Wrap>
                        
                        {/* Selection Summary */}
                        <HStack justify="space-between" align="center" mt="12px" pt="12px" borderTop="1px solid" borderColor={borderColor}>
                          <Text fontSize={adaptiveConfig.fontSize.small} color={secondaryText}>
                            Selected {selectedCameras.length}/{detectedFolders.length} cameras
                          </Text>
                          <HStack spacing="8px">
                            <Button
                              size="xs"
                              variant="ghost"
                              colorScheme="brand"
                              onClick={() => {
                                const allNames = detectedFolders.map(f => f.name);
                                setSelectedCameras(allNames);
                                if (onStepChange) {
                                  onStepChange('video_source', {
                                    sourceType: 'local_storage',
                                    inputPath: inputPath,
                                    detectedFolders: detectedFolders,
                                    selectedCameras: allNames
                                  });
                                }
                              }}
                            >
                              Select All
                            </Button>
                            <Button
                              size="xs"
                              variant="ghost"
                              onClick={() => {
                                setSelectedCameras([]);
                                if (onStepChange) {
                                  onStepChange('video_source', {
                                    sourceType: 'local_storage',
                                    inputPath: inputPath,
                                    detectedFolders: detectedFolders,
                                    selectedCameras: []
                                  });
                                }
                              }}
                            >
                              Clear All
                            </Button>
                          </HStack>
                        </HStack>
                      </Box>
                    </Box>
                  )}
                  
                  {/* No Folders Found */}
                  {detectedFolders.length === 0 && !scanningFolders && !scanError && inputPath && (
                    <Alert status="info" mb="12px" borderRadius="8px">
                      <AlertIcon />
                      <AlertDescription fontSize={adaptiveConfig.fontSize.small}>
                        📂 No subdirectories found in the specified path. Make sure the path contains camera folders.
                      </AlertDescription>
                    </Alert>
                  )}
                </Box>
              )}
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
                        ) : gmailAuthenticated ? (
                          <Text fontSize="12px" color="blue.500">
                            Gmail ✅ Ready • Google Drive → Click Connect
                          </Text>
                        ) : (
                          <Text fontSize="12px" color="orange.500">
                            ⚠️ Gmail authentication required first
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
                              setDriveConnecting(false);
                              alert('⚠️ Gmail authentication required\n\nPlease complete Gmail login in the welcome screen before connecting Google Drive.\n\nSteps:\n1. Return to Camera Config home\n2. Complete Gmail authentication\n3. Come back to this step to connect Google Drive');
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
                              const handleMessage = async (event: MessageEvent) => {
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
                                  console.log('🔴 DEBUG: setDriveConnected(true) from OAUTH_SUCCESS');
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
                                        // Only set connected if NOT in setup mode (avoid setup mode override)
                                        if (!statusData.setup_mode) {
                                          console.log('🔴 DEBUG: setDriveConnected(true) from polling retry');
                                          setDriveConnected(true);
                                          setDriveUserEmail(statusData.user_email || '');
                                          setDriveConnecting(false);
                                          loadInitialFolders();
                                        } else {
                                          console.log('🎯 Setup mode detected in polling - ignoring connection status');
                                        }

                                        // Clear setup step - Drive setup completed
                                        fetch('http://localhost:8080/api/cloud/clear-setup-step', {
                                          method: 'POST',
                                          credentials: 'include'
                                        }).then(() => {
                                          console.log('✅ Setup step cleared - Drive setup completed');
                                        }).catch((error) => {
                                          console.error('❌ Failed to clear setup step:', error);
                                        });
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
                        Connect
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
                              
                              console.log('🔴 DEBUG: setDriveConnected(false) from disconnect button');
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
                          STOP
                        </Button>
                      )}
                    </HStack>
                    
                    {/* Connection Status Info */}
                    {!driveConnected ? (
                      !gmailAuthenticated && (
                        <Alert status="warning" borderRadius="8px" fontSize={adaptiveConfig.fontSize.small}>
                          <AlertIcon />
                          <AlertDescription>
                            Gmail authentication must be completed first before connecting Google Drive
                          </AlertDescription>
                        </Alert>
                      )
                    ) : (
                      <Alert status="success" borderRadius="8px">
                        <AlertIcon />
                        <AlertDescription fontSize={adaptiveConfig.fontSize.small} flex="1">
                          Google Drive connected successfully
                        </AlertDescription>
                        <Button
                          size="xs"
                          variant="ghost"
                          onClick={() => checkDriveConnectionStatus()}
                          ml={2}
                        >
                          🔄 Refresh
                        </Button>
                      </Alert>
                    )}
                    
                    {/* Debug: Manual check button when stuck in connecting state */}
                    {driveConnecting && (
                      <Alert status="info" borderRadius="8px">
                        <AlertIcon />
                        <AlertDescription fontSize={adaptiveConfig.fontSize.small} flex="1">
                          Stuck connecting? Try manual check
                        </AlertDescription>
                        <Button
                          size="xs"
                          colorScheme="blue"
                          onClick={async () => {
                            console.log('🔧 Manual connection check triggered');
                            setDriveConnecting(false);
                            await checkDriveConnectionStatus();
                          }}
                          ml={2}
                        >
                          Check Status
                        </Button>
                      </Alert>
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
                    folders={driveFolders}
                    isLoading={folderTreeLoading}
                    initialSelectedFolders={selectedTreeFolders}
                    onFoldersSelected={handleTreeFolderSelection}
                    maxDepth={3}
                  />
                </Box>

              </VStack>
            </Box>
          </Box>
        )}



      </VStack>
    </Box>
  );
}

export default VideoSourceCanvas;