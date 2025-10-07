'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Flex,
  Badge,
  Spinner,
  Alert,
  AlertIcon,
  AlertDescription,
  IconButton,
  Checkbox,
  useColorModeValue
} from '@chakra-ui/react';
import { ChevronRightIcon, ChevronDownIcon } from '@chakra-ui/icons';

// TypeScript Interfaces
interface DriveFolder {
  id: string;
  name: string;
  path?: string;
  depth: number;
  has_subfolders: boolean;
  selectable?: boolean;
}

interface TreeNode {
  id: string;
  name: string;
  depth: number;
  selectable: boolean;
  has_subfolders: boolean;
  children?: DriveFolder[];
  loaded?: boolean;
}

interface TreeData {
  [key: string]: TreeNode;
}

interface SelectedFolder {
  id: string;
  name: string;
  path?: string;
  depth: number;
}

interface GoogleDriveFolderTreeProps {
  session_token?: string; // Optional, not used - kept for compatibility
  folders?: DriveFolder[]; // NEW: Pre-loaded folders from parent component
  isLoading?: boolean; // NEW: Loading state from parent
  initialSelectedFolders?: SelectedFolder[]; // NEW: Pre-selected folders for restoring state
  onFoldersSelected: (folders: SelectedFolder[]) => void;
  maxDepth?: number;
  className?: string;
}

interface AuthStatus {
  authenticated: boolean;
  loading: boolean;
}

const GoogleDriveFolderTree: React.FC<GoogleDriveFolderTreeProps> = ({
  session_token,
  folders = [], // NEW: Pre-loaded folders from parent
  isLoading = false, // NEW: Loading state from parent
  initialSelectedFolders = [], // NEW: Pre-selected folders for restoring state
  onFoldersSelected,
  maxDepth = 3,
  className = ''
}) => {
  // Color mode values
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const textColor = useColorModeValue('gray.800', 'white');
  const hoverBg = useColorModeValue('gray.100', 'gray.600');
  const selectedBg = useColorModeValue('blue.100', 'blue.600');

  // Tree state management
  const [treeData, setTreeData] = useState<TreeData>({});
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['root']));
  const [selectedFolders, setSelectedFolders] = useState<SelectedFolder[]>([]);
  const [selectedDepth, setSelectedDepth] = useState<number | null>(null);
  const [loadingFolders, setLoadingFolders] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [authStatus, setAuthStatus] = useState<AuthStatus>({ authenticated: false, loading: true });
  const [hasHadInitialLoad, setHasHadInitialLoad] = useState(false);
  const [hasTriedRetry, setHasTriedRetry] = useState(false);

  // Initialize component with pre-loaded folders
  useEffect(() => {
    const initializeComponent = () => {
      try {
        setAuthStatus({ authenticated: false, loading: true });

        // Use pre-loaded folders from parent component if available
        if (folders && folders.length > 0) {
          console.log(`📁 Initializing with ${folders.length} pre-loaded folders`);
          loadPreloadedFolders(folders);
          setAuthStatus({ authenticated: true, loading: false });
          setError(null);
        } else {
          console.log('⏸️ No pre-loaded folders - waiting for user to click Connect button');
          setAuthStatus({ authenticated: false, loading: false });
          setError(null); // Don't show error - just wait for user action
        }
        setHasHadInitialLoad(true);
      } catch (error) {
        console.error('Folder initialization error:', error);
        setAuthStatus({ authenticated: false, loading: false });
        setError('Failed to initialize folders.');
      }
    };

    initializeComponent();
  }, [folders]); // Re-run when folders prop changes

  // Restore initial selected folders (for edit mode)
  useEffect(() => {
    if (initialSelectedFolders && initialSelectedFolders.length > 0) {
      console.log(`🔄 Restoring ${initialSelectedFolders.length} previously selected folders`);
      setSelectedFolders(initialSelectedFolders);

      // Set selected depth based on first folder
      if (initialSelectedFolders[0]?.depth !== undefined) {
        setSelectedDepth(initialSelectedFolders[0].depth);
      }

      // Notify parent immediately
      onFoldersSelected(initialSelectedFolders);
    }
  }, [initialSelectedFolders]);

  // Auto-retry ONLY after initial load (for stop & auth scenarios) - ONE TIME ONLY
  useEffect(() => {
    // Only retry if we've had initial load, now unauthenticated, and haven't tried retry yet
    if (hasHadInitialLoad && !authStatus.authenticated && !authStatus.loading && !hasTriedRetry) {
      console.log('🔄 Auth change detected after initial load, auto-retrying ONCE...');
      setHasTriedRetry(true); // Prevent multiple retries

      const timeout = setTimeout(() => {
        setAuthStatus({ authenticated: false, loading: true });
        setError(null);
        loadRootFolders();
      }, 1000);

      return () => clearTimeout(timeout);
    }
  }, [hasHadInitialLoad, authStatus.authenticated, authStatus.loading, hasTriedRetry]);

  // Notify parent when selection changes
  useEffect(() => {
    if (onFoldersSelected) {
      onFoldersSelected(selectedFolders);
    }
  }, [selectedFolders]); // Remove onFoldersSelected from dependencies

  // NEW: Load pre-loaded folders from parent component
  const loadPreloadedFolders = (folderList: DriveFolder[]) => {
    try {
      console.log('📁 Processing pre-loaded folders:', folderList);

      // Convert folders to tree format
      const newTreeData: TreeData = {
        root: {
          id: 'root',
          name: 'Google Drive',
          depth: 0,
          selectable: false,
          has_subfolders: true,
          children: folderList,
          loaded: true
        }
      };

      // Add each folder to tree data
      folderList.forEach(folder => {
        newTreeData[folder.id] = {
          id: folder.id,
          name: folder.name,
          depth: folder.depth || 1,
          selectable: folder.selectable !== false, // Default to true if not specified
          has_subfolders: folder.has_subfolders || false,
          children: [],
          loaded: false
        };
      });

      setTreeData(newTreeData);
      console.log(`✅ Loaded ${folderList.length} folders into tree`);

    } catch (error) {
      console.error('❌ Error processing pre-loaded folders:', error);
      setError('Failed to process folder data');
    }
  };

  const loadRootFolders = async () => {
    try {
      setLoadingFolders(prev => new Set([...prev, 'root']));
      setError(null);

      console.log('🔄 Loading root folders with session credentials...');

      const response = await fetch('http://localhost:8080/api/cloud/list_subfolders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include', // Use session cookies only
        body: JSON.stringify({
          parent_id: 'root',
          max_results: 30
        })
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication expired. Please click Connect to re-authenticate Google Drive.');
        }
        throw new Error(`Failed to load root folders: ${response.status}`);
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.message || 'Failed to load root folders');
      }

      // Initialize tree with root data
      setTreeData({
        'root': {
          id: 'root',
          name: 'My Drive',
          depth: 0,
          selectable: false,
          has_subfolders: true,
          children: data.folders || [],
          loaded: true
        }
      });

      console.log(`✅ Loaded ${(data.folders || []).length} root folders`);
      setAuthStatus({ authenticated: true, loading: false });

    } catch (error) {
      console.error('❌ Error loading root folders:', error);

      // Handle 401 as authentication required, not error
      const errorMessage = error instanceof Error ? error.message : 'Failed to load folders';
      if (errorMessage.includes('401') || errorMessage.includes('authenticate')) {
        setError(null); // Don't show 401 as error
        setAuthStatus({ authenticated: false, loading: false });
      } else {
        setError(errorMessage);
        setAuthStatus({ authenticated: false, loading: false });
      }
    } finally {
      setLoadingFolders(prev => {
        const next = new Set(prev);
        next.delete('root');
        return next;
      });
    }
  };

  const loadSubfolders = useCallback(async (parentId: string, parentDepth: number) => {
    try {
      // Don't load beyond max depth
      if (parentDepth >= maxDepth) {
        console.log(`🛑 Stopping at max depth ${maxDepth}, not loading subfolders for depth ${parentDepth + 1}`);
        return;
      }

      setLoadingFolders(prev => new Set([...prev, parentId]));
      setError(null);

      console.log(`🔄 Loading subfolders for: ${parentId} (will be depth ${parentDepth + 1})`);

      const response = await fetch('http://localhost:8080/api/cloud/list_subfolders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include', // Use session cookies only
        body: JSON.stringify({
          parent_id: parentId,
          max_results: 50
        })
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication expired. Please click Connect to re-authenticate Google Drive.');
        }
        throw new Error(`Failed to load subfolders: ${response.status}`);
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.message || 'Failed to load subfolders');
      }

      // Process folders with depth limit
      const processedFolders: DriveFolder[] = (data.folders || []).map((folder: any) => ({
        ...folder,
        depth: parentDepth + 1,
        // No subfolders beyond max depth
        has_subfolders: (parentDepth + 1) < maxDepth ? folder.has_subfolders : false
      }));

      // Update tree data
      setTreeData(prev => ({
        ...prev,
        [parentId]: {
          ...prev[parentId],
          children: processedFolders,
          loaded: true
        }
      }));

      console.log(`✅ Loaded ${processedFolders.length} subfolders for ${parentId} (depth ${parentDepth + 1})`);

    } catch (error) {
      console.error(`❌ Error loading subfolders for ${parentId}:`, error);
      setError(error instanceof Error ? error.message : 'Failed to load subfolders');
    } finally {
      setLoadingFolders(prev => {
        const next = new Set(prev);
        next.delete(parentId);
        return next;
      });
    }
  }, [maxDepth]); // No session_token needed

  const handleFolderExpand = useCallback((event: React.MouseEvent, folder: DriveFolder) => {
    event.stopPropagation();
    event.preventDefault();
    
    const folderId = folder.id;
    
    console.log(`🔽 Expand/collapse action for: ${folder.name} (depth ${folder.depth})`);
    
    setExpandedFolders(prev => {
      const isExpanded = prev.has(folderId);
      const next = new Set(prev);
      
      if (isExpanded) {
        next.delete(folderId);
        console.log(`📁 Collapsed: ${folder.name}`);
      } else {
        next.add(folderId);
        console.log(`📂 Expanded: ${folder.name}`);
        
        // Only load if within depth limit and not already loaded
        if (folder.has_subfolders && folder.depth < maxDepth) {
          // Check if already loaded to avoid duplicate requests
          setTreeData(currentTreeData => {
            if (!currentTreeData[folderId] || !currentTreeData[folderId].loaded) {
              // Trigger loading asynchronously
              setTimeout(() => {
                loadSubfolders(folderId, folder.depth);
              }, 10);
            }
            return currentTreeData;
          });
        }
      }
      
      return next;
    });
  }, [maxDepth, loadSubfolders]);

  const handleFolderSelect = useCallback((event: React.MouseEvent, folder: DriveFolder) => {
    event.stopPropagation();
    
    console.log(`🔍 Folder selection attempt:`, folder.name, `Depth: ${folder.depth}`);
    
    const folderId = folder.id;
    const folderDepth = folder.depth;
    
    // Check depth consistency
    if (selectedDepth !== null && selectedDepth !== folderDepth) {
      // Show warning and don't allow selection
      setError(`Cannot mix different depth levels. Currently selected: Depth ${selectedDepth}. Clear selection to choose Depth ${folderDepth} folders.`);
      return;
    }
    
    setSelectedFolders(prev => {
      const isSelected = prev.some(f => f.id === folderId);
      if (isSelected) {
        console.log(`❌ Deselecting folder: ${folder.name}`);
        const newSelection = prev.filter(f => f.id !== folderId);
        
        // Reset selected depth if no folders left
        if (newSelection.length === 0) {
          setSelectedDepth(null);
          setError(null); // Clear any depth error
          console.log(`🔄 Reset selected depth - no folders selected`);
        }
        
        return newSelection;
      } else {
        console.log(`✅ Selecting folder: ${folder.name} at depth ${folderDepth}`);
        
        // Set selected depth on first selection
        if (selectedDepth === null) {
          setSelectedDepth(folderDepth);
          setError(null); // Clear any previous errors
          console.log(`🎯 Set selected depth to: ${folderDepth}`);
        }
        
        return [...prev, {
          id: folder.id,
          name: folder.name,
          path: folder.path,
          depth: folder.depth
        }];
      }
    });
  }, [selectedDepth]);

  const handleSelectAll = useCallback(() => {
    if (selectedDepth === null) {
      setError('Please select a folder first to determine the depth level, then use "Select All" for that depth.');
      return;
    }
    
    console.log(`✅ Selecting all visible folders at depth ${selectedDepth}`);
    const depthFolders: SelectedFolder[] = [];
    
    const collectDepthFolders = (nodeId: string) => {
      const node = treeData[nodeId];
      if (!node) return;
      
      if (node.children) {
        node.children.forEach(child => {
          if (child.depth === selectedDepth) {
            depthFolders.push({
              id: child.id,
              name: child.name,
              path: child.path,
              depth: child.depth
            });
          }
          if (expandedFolders.has(child.id) && child.depth < selectedDepth!) {
            collectDepthFolders(child.id);
          }
        });
      }
    };
    
    collectDepthFolders('root');
    setSelectedFolders(depthFolders);
    setError(null);
  }, [selectedDepth]); // Remove treeData and expandedFolders from deps

  const handleDeselectAll = useCallback(() => {
    console.log('🗑️ Clearing all selections and resetting depth');
    setSelectedFolders([]);
    setSelectedDepth(null);
    setError(null);
  }, []);

  // Get folder type label by depth
  const getFolderTypeLabel = useCallback((folder: DriveFolder) => {
    switch (folder.depth) {
      case 1: return 'Main Folder';
      case 2: return 'Camera Folder';  
      case 3: return 'Date/Category';
      default: return 'Folder';
    }
  }, []);

  // Check if folder is selectable (considering depth constraint) - Memoized to prevent re-renders
  const isFolderSelectable = useCallback((folder: DriveFolder) => {
    // Always show checkbox for depth 1-3
    if (folder.depth < 1 || folder.depth > maxDepth) return false;
    
    // If no depth selected yet, all depths are available
    if (selectedDepth === null) return true;
    
    // If depth is selected, only same depth is selectable
    return folder.depth === selectedDepth;
  }, [selectedDepth, maxDepth]);

  const renderFolderIcon = (folder: DriveFolder, isExpanded: boolean, isLoading: boolean) => {
    if (isLoading) {
      return <Spinner size="sm" color="blue.400" />;
    }

    if (folder.has_subfolders) {
      return isExpanded ? <ChevronDownIcon /> : <ChevronRightIcon />;
    }
    return '📁';
  };

  const renderFolderNode = (folder: DriveFolder, depth: number = 0): JSX.Element => {
    const isExpanded = expandedFolders.has(folder.id);
    const isLoading = loadingFolders.has(folder.id);
    const isSelected = selectedFolders.some(f => f.id === folder.id);
    const hasSubfolders = folder.has_subfolders;
    
    // Show checkbox for all depths 1-3, but consider depth consistency
    const showCheckbox = folder.depth >= 1 && folder.depth <= maxDepth;
    const isSelectable = isFolderSelectable(folder);
    const isDisabled = showCheckbox && !isSelectable;

    const getDepthBadgeColor = (depth: number) => {
      switch (depth) {
        case 1: return 'green';
        case 2: return 'blue';
        case 3: return 'purple';
        default: return 'gray';
      }
    };

    return (
      <Box key={folder.id}>
        {/* Folder Row */}
        <Flex
          align="center"
          py={1}
          px={2}
          borderRadius="md"
          bg={isSelected ? selectedBg : isDisabled ? 'gray.600' : 'transparent'}
          opacity={isDisabled ? 0.5 : 1}
          _hover={!isDisabled ? { bg: hoverBg } : {}}
          pl={`${depth * 16 + 8}px`}
          cursor={isDisabled ? 'not-allowed' : 'pointer'}
          minH="32px"
        >
          {/* Expand/Collapse Button */}
          <Box
            as="button"
            w="6"
            h="6"
            display="flex"
            alignItems="center"
            justifyContent="center"
            mr={2}
            fontSize="sm"
            cursor={hasSubfolders && !isLoading ? "pointer" : "default"}
            color={hasSubfolders ? "gray.300" : "gray.500"}
            _hover={hasSubfolders ? { color: "white" } : {}}
            onClick={(e) => {
              e.stopPropagation();
              if (!isLoading && hasSubfolders) {
                handleFolderExpand(e as any, folder);
              }
            }}
          >
            {renderFolderIcon(folder, isExpanded, isLoading)}
          </Box>

          {/* Checkbox */}
          {showCheckbox && (
            <Box
              as="input"
              type="checkbox"
              checked={isSelected}
              disabled={isDisabled}
              onChange={(e: any) => {
                if (!isDisabled) {
                  handleFolderSelect(e, folder);
                }
              }}
              mr={3}
              w="4"
              h="4"
              cursor={isDisabled ? "not-allowed" : "pointer"}
            />
          )}

          {/* Folder Info */}
          <Box flex="1" minW="0">
            <Text
              fontSize={{ base: "xs", md: "sm" }}
              fontWeight={isSelected ? 'bold' : showCheckbox && isSelectable ? 'medium' : 'normal'}
              color={isSelected ? 'white' : showCheckbox && isSelectable ? textColor : 'gray.400'}
              isTruncated
            >
              {folder.name}
            </Text>
            {folder.path && (
              <Text fontSize={{ base: "10px", md: "xs" }} color="gray.400" isTruncated display={{ base: "none", md: "block" }}>
                {folder.path}
              </Text>
            )}
          </Box>

          {/* Depth & Status Indicator */}
          <HStack spacing={1} flexShrink={0}>
            {/* Depth Badge - Always show */}
            <Badge colorScheme={getDepthBadgeColor(folder.depth)} size="sm" fontSize="10px">
              D{folder.depth}
            </Badge>
            
            {/* Selection Status - Hide on mobile when not selected */}
            {showCheckbox && (isSelected || !isDisabled) && (
              <Badge 
                colorScheme={isSelected ? 'green' : isDisabled ? 'gray' : 'gray'} 
                size="sm"
                fontSize="9px"
                display={{ base: isSelected ? "inline" : "none", md: "inline" }}
              >
                {isSelected ? '✓' : 
                 isDisabled ? 'X' :
                 getFolderTypeLabel(folder).split(' ')[0]} {/* Short form on mobile */}
              </Badge>
            )}
          </HStack>
        </Flex>

        {/* Child Folders */}
        {isExpanded && folder.depth < maxDepth && treeData[folder.id] && treeData[folder.id].children && (
          <Box ml={4}>
            {treeData[folder.id].children!.map(childFolder => 
              renderFolderNode(childFolder, depth + 1)
            )}
          </Box>
        )}
      </Box>
    );
  };

  // Note: Authentication is handled via session cookies, no token check needed

  if (authStatus.loading) {
    return (
      <Alert status="info" borderRadius="8px">
        <Spinner size="sm" mr={3} />
        <AlertDescription fontSize="sm">
          Loading folders...
        </AlertDescription>
      </Alert>
    );
  }

  // Show loading if parent is loading folders OR if we're loading subfolders
  if (isLoading || (loadingFolders.has('root') && !authStatus.authenticated)) {
    return (
      <Alert status="info" borderRadius="8px">
        <Spinner size="sm" mr={3} />
        <AlertDescription fontSize="sm">
          Loading folders from Google Drive...
        </AlertDescription>
      </Alert>
    );
  }

  if (!authStatus.authenticated && !authStatus.loading) {
    return (
      <Alert status="warning" borderRadius="8px">
        <AlertIcon />
        <AlertDescription fontSize="sm">
          {error || 'Click "Connect to Google Drive" button above to get started'}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Box className={className}>



      {/* Error Display */}
      {error && (
        <Alert status="error" borderRadius="8px" mb={4}>
          <AlertIcon />
          <AlertDescription fontSize="sm" flex="1">
            {error}
          </AlertDescription>
          <Button
            size="xs"
            colorScheme="red"
            onClick={() => setError(null)}
            ml={2}
          >
            Dismiss
          </Button>
        </Alert>
      )}

      {/* Tree Container */}
      <Box 
        bg={bgColor} 
        borderRadius="md" 
        p={{ base: 2, md: 4 }} 
        maxH={{ base: "350px", md: "450px" }} 
        overflowY="auto" 
        overflowX="hidden"
        border="1px solid" 
        borderColor={borderColor}
        fontSize={{ base: "xs", md: "sm" }}
        sx={{
          '&::-webkit-scrollbar': {
            width: '6px',
          },
          '&::-webkit-scrollbar-track': {
            background: 'gray.100',
            borderRadius: '3px',
          },
          '&::-webkit-scrollbar-thumb': {
            background: 'gray.400',
            borderRadius: '3px',
          },
          '&::-webkit-scrollbar-thumb:hover': {
            background: 'gray.500',
          },
        }}
      >
        {treeData['root'] ? (
          <VStack align="stretch" spacing={0}>
            {/* Root Node */}
            <Flex align="center" py={2} px={3} bg="gray.600" borderRadius="md" mb={2}>
              <Text mr={2} fontSize="lg">💾</Text>
              <Box flex="1">
                <Text fontWeight="medium" color="white">My Drive</Text>
                <Text fontSize="xs" color="gray.300">Root directory - expand to navigate (max depth {maxDepth})</Text>
              </Box>
              <Badge colorScheme="gray" size="sm">D0 Root</Badge>
            </Flex>

            {/* Root Children */}
            {treeData['root'].children && treeData['root'].children.map(folder => 
              renderFolderNode(folder, 0)
            )}
          </VStack>
        ) : (
          <VStack py={8} color="gray.400">
            <Spinner size="lg" />
            <Text>Loading folders...</Text>
          </VStack>
        )}
      </Box>
    </Box>
  );
};

export default GoogleDriveFolderTree;