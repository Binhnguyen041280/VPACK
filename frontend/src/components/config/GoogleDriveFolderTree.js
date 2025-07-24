// components/config/GoogleDriveFolderTree.js - CONSISTENT DEPTH SELECTION
import React, { useState, useEffect, useCallback } from 'react';

const GoogleDriveFolderTree = ({ 
  session_token, 
  onFoldersSelected, 
  maxDepth = 3, // 🎯 REQUIREMENT: Max depth 3 only
  className = ''
}) => {
  // Tree state management
  const [treeData, setTreeData] = useState({});
  const [expandedFolders, setExpandedFolders] = useState(new Set(['root']));
  const [selectedFolders, setSelectedFolders] = useState([]);
  const [selectedDepth, setSelectedDepth] = useState(null); // 🎯 NEW: Track selected depth
  const [loadingFolders, setLoadingFolders] = useState(new Set());
  const [error, setError] = useState(null);
  const [authStatus, setAuthStatus] = useState({ authenticated: false, loading: true });

  // 🔒 SECURITY: Validate session token and initialize
  useEffect(() => {
    const validateAndInit = async () => {
      if (!session_token) {
        setAuthStatus({ authenticated: false, loading: false });
        return;
      }

      try {
        setAuthStatus({ authenticated: false, loading: true });
        
        const response = await fetch('http://localhost:8080/api/cloud/auth-status', {
          method: 'GET',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${session_token}`
          },
          credentials: 'include'
        });

        if (response.ok) {
          const result = await response.json();
          if (result.authenticated) {
            setAuthStatus({ authenticated: true, loading: false });
            await loadRootFolders();
          } else {
            setAuthStatus({ authenticated: false, loading: false });
            setError('Session expired. Please re-authenticate.');
          }
        } else {
          setAuthStatus({ authenticated: false, loading: false });
          setError('Authentication validation failed.');
        }
      } catch (error) {
        console.error('Session validation error:', error);
        setAuthStatus({ authenticated: false, loading: false });
        setError('Failed to validate session.');
      }
    };

    validateAndInit();
  }, [session_token]);

  // Notify parent when selection changes
  useEffect(() => {
    if (onFoldersSelected) {
      onFoldersSelected(selectedFolders);
    }
  }, [selectedFolders, onFoldersSelected]);

  const loadRootFolders = async () => {
    try {
      setLoadingFolders(prev => new Set([...prev, 'root']));
      setError(null);

      console.log('🔄 Loading root folders with session token...');

      const response = await fetch('http://localhost:8080/api/cloud/folders/initialize', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session_token}`
        },
        credentials: 'include',
        body: JSON.stringify({
          max_folders: 30
        })
      });

      if (!response.ok) {
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

    } catch (error) {
      console.error('❌ Error loading root folders:', error);
      setError(error.message);
    } finally {
      setLoadingFolders(prev => {
        const next = new Set(prev);
        next.delete('root');
        return next;
      });
    }
  };

  const loadSubfolders = async (parentId, parentDepth) => {
    try {
      // 🎯 REQUIREMENT: Don't load beyond depth 3
      if (parentDepth >= maxDepth) {
        console.log(`🛑 Stopping at max depth ${maxDepth}, not loading subfolders for depth ${parentDepth + 1}`);
        return;
      }

      setLoadingFolders(prev => new Set([...prev, parentId]));
      setError(null);

      console.log(`🔄 Loading subfolders for: ${parentId} (will be depth ${parentDepth + 1})`);

      const response = await fetch('http://localhost:8080/api/cloud/folders/list_subfolders', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session_token}`
        },
        credentials: 'include',
        body: JSON.stringify({
          parent_id: parentId,
          max_results: 50
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to load subfolders: ${response.status}`);
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.message || 'Failed to load subfolders');
      }

      // Process folders with depth limit
      const processedFolders = (data.folders || []).map(folder => ({
        ...folder,
        depth: parentDepth + 1,
        // 🎯 REQUIREMENT: No subfolders beyond depth 3
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
      setError(error.message);
    } finally {
      setLoadingFolders(prev => {
        const next = new Set(prev);
        next.delete(parentId);
        return next;
      });
    }
  };

  const handleFolderExpand = useCallback(async (event, folder) => {
    event.stopPropagation();
    event.preventDefault();
    
    const folderId = folder.id;
    
    console.log(`🔽 Expand/collapse action for: ${folder.name} (depth ${folder.depth})`);
    
    if (expandedFolders.has(folderId)) {
      setExpandedFolders(prev => {
        const next = new Set(prev);
        next.delete(folderId);
        return next;
      });
      console.log(`📁 Collapsed: ${folder.name}`);
    } else {
      setExpandedFolders(prev => new Set([...prev, folderId]));
      console.log(`📂 Expanded: ${folder.name}`);
      
      // 🎯 REQUIREMENT: Only load if within depth limit
      if (folder.has_subfolders && folder.depth < maxDepth && (!treeData[folderId] || !treeData[folderId].loaded)) {
        await loadSubfolders(folderId, folder.depth);
      }
    }
  }, [expandedFolders, treeData, session_token, maxDepth]);

  const handleFolderSelect = useCallback((event, folder) => {
    event.stopPropagation();
    
    console.log(`🔍 Folder selection attempt:`, folder.name, `Depth: ${folder.depth}`);
    
    const folderId = folder.id;
    const folderDepth = folder.depth;
    
    // 🎯 REQUIREMENT: Check depth consistency
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
        
        // 🎯 REQUIREMENT: Reset selected depth if no folders left
        if (newSelection.length === 0) {
          setSelectedDepth(null);
          setError(null); // Clear any depth error
          console.log(`🔄 Reset selected depth - no folders selected`);
        }
        
        return newSelection;
      } else {
        console.log(`✅ Selecting folder: ${folder.name} at depth ${folderDepth}`);
        
        // 🎯 REQUIREMENT: Set selected depth on first selection
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
    const depthFolders = [];
    
    const collectDepthFolders = (nodeId) => {
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
          if (expandedFolders.has(child.id) && child.depth < selectedDepth) {
            collectDepthFolders(child.id);
          }
        });
      }
    };
    
    collectDepthFolders('root');
    setSelectedFolders(depthFolders);
    setError(null);
  }, [treeData, expandedFolders, selectedDepth]);

  const handleDeselectAll = useCallback(() => {
    console.log('🗑️ Clearing all selections and resetting depth');
    setSelectedFolders([]);
    setSelectedDepth(null);
    setError(null);
  }, []);

  // 🎯 NEW: Get folder type label by depth
  const getFolderTypeLabel = useCallback((folder) => {
    switch (folder.depth) {
      case 1: return 'Main Folder';
      case 2: return 'Camera Folder';  
      case 3: return 'Date/Category';
      default: return 'Folder';
    }
  }, []);

  // 🎯 NEW: Check if folder is selectable (considering depth constraint)
  const isFolderSelectable = useCallback((folder) => {
    // Always show checkbox for depth 1-3
    if (folder.depth < 1 || folder.depth > maxDepth) return false;
    
    // If no depth selected yet, all depths are available
    if (selectedDepth === null) return true;
    
    // If depth is selected, only same depth is selectable
    return folder.depth === selectedDepth;
  }, [selectedDepth, maxDepth]);

  const renderFolderIcon = (folder, isExpanded, isLoading) => {
    if (isLoading) {
      return (
        <svg className="animate-spin h-4 w-4 text-blue-400" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      );
    }

    if (folder.has_subfolders) {
      return isExpanded ? '▼' : '▶';
    }
    return '📁';
  };

  const renderFolderNode = (folder, depth = 0) => {
    const isExpanded = expandedFolders.has(folder.id);
    const isLoading = loadingFolders.has(folder.id);
    const isSelected = selectedFolders.some(f => f.id === folder.id);
    const hasSubfolders = folder.has_subfolders;
    
    // 🎯 REQUIREMENT: Show checkbox for all depths 1-3, but consider depth consistency
    const showCheckbox = folder.depth >= 1 && folder.depth <= maxDepth;
    const isSelectable = isFolderSelectable(folder);
    const isDisabled = showCheckbox && !isSelectable;

    return (
      <div key={folder.id} className="folder-node">
        {/* Folder Row */}
        <div 
          className={`flex items-center py-2 px-3 rounded transition-colors ${
            isSelected 
              ? 'bg-blue-600' 
              : isDisabled 
                ? 'bg-gray-600 opacity-50' 
                : 'hover:bg-gray-600'
          }`}
          style={{ paddingLeft: `${depth * 20 + 12}px` }}
        >
          {/* Expand/Collapse Button */}
          <button
            type="button"
            onClick={(e) => handleFolderExpand(e, folder)}
            disabled={isLoading || !hasSubfolders}
            className={`mr-2 w-6 h-6 flex items-center justify-center text-sm ${
              hasSubfolders ? 'text-gray-300 hover:text-white cursor-pointer' : 'text-gray-500 cursor-default'
            }`}
          >
            {renderFolderIcon(folder, isExpanded, isLoading)}
          </button>

          {/* 🎯 REQUIREMENT: Checkbox with depth consistency */}
          {showCheckbox && (
            <input
              type="checkbox"
              checked={isSelected}
              disabled={isDisabled}
              onChange={(e) => handleFolderSelect(e, folder)}
              className={`mr-3 h-4 w-4 text-blue-600 rounded border-gray-600 bg-gray-700 ${
                isDisabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
              }`}
              title={
                isDisabled 
                  ? `Cannot select depth ${folder.depth}. Currently selecting depth ${selectedDepth}.`
                  : `Select ${folder.name} (${getFolderTypeLabel(folder)})`
              }
            />
          )}

          {/* Folder Info */}
          <div className="flex-1 min-w-0">
            <div className={`text-sm truncate ${
              isSelected 
                ? 'text-white font-bold'
                : showCheckbox && isSelectable
                  ? 'text-white font-medium' 
                  : isDisabled
                    ? 'text-gray-400'
                    : 'text-gray-300'
            }`}>
              {folder.name}
            </div>
            {folder.path && (
              <div className="text-xs text-gray-400 truncate">
                {folder.path}
              </div>
            )}
          </div>

          {/* 🎯 NEW: Depth & Status Indicator */}
          <div className="flex items-center gap-2">
            {/* Depth Badge */}
            <div className={`text-xs px-2 py-1 rounded ${
              folder.depth === 1 ? 'bg-green-600 text-green-100' :
              folder.depth === 2 ? 'bg-blue-600 text-blue-100' :
              folder.depth === 3 ? 'bg-purple-600 text-purple-100' :
              'bg-gray-600 text-gray-100'
            }`}>
              D{folder.depth}
            </div>
            
            {/* Selection Status */}
            {showCheckbox && (
              <div className={`text-xs px-2 py-1 rounded ${
                isSelected 
                  ? 'bg-green-600 text-green-100' 
                  : isDisabled
                    ? 'bg-gray-500 text-gray-300'
                    : 'bg-gray-600 text-gray-300'
              }`}>
                {isSelected ? '✅ Selected' : 
                 isDisabled ? 'Different Depth' :
                 getFolderTypeLabel(folder)}
              </div>
            )}
          </div>
        </div>

        {/* Child Folders - 🎯 REQUIREMENT: Only if within depth limit */}
        {isExpanded && folder.depth < maxDepth && treeData[folder.id] && treeData[folder.id].children && (
          <div className="children">
            {treeData[folder.id].children.map(childFolder => 
              renderFolderNode(childFolder, depth + 1)
            )}
          </div>
        )}
      </div>
    );
  };

  // 🔒 SECURITY: Check authentication status
  if (!session_token) {
    return (
      <div className="text-center py-8 text-gray-400 border border-gray-600 rounded-lg">
        <div className="text-lg mb-2">🔐</div>
        <div>Please authenticate with Google Drive first</div>
      </div>
    );
  }

  if (authStatus.loading) {
    return (
      <div className="text-center py-8 text-gray-400 border border-gray-600 rounded-lg">
        <div className="text-lg mb-2">🔄</div>
        <div>Validating authentication...</div>
      </div>
    );
  }

  if (!authStatus.authenticated) {
    return (
      <div className="text-center py-8 text-red-400 border border-red-600 rounded-lg">
        <div className="text-lg mb-2">❌</div>
        <div>Authentication required</div>
        <div className="text-sm text-red-300 mt-2">
          {error || 'Please re-authenticate with Google Drive'}
        </div>
      </div>
    );
  }

  return (
    <div className={`google-drive-folder-tree ${className}`}>
      {/* Header with Depth Info */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="font-medium text-white">📁 Navigate & Select Folders (Max Depth {maxDepth})</h4>
          <div className="text-xs text-gray-400 mt-1">
            {selectedDepth !== null ? (
              <span className="text-blue-300">
                Currently selecting: <strong>Depth {selectedDepth}</strong> ({getFolderTypeLabel({depth: selectedDepth})})
              </span>
            ) : (
              <span>Select folders at any depth (1-{maxDepth}), but all must be same depth</span>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              e.preventDefault();
              handleSelectAll();
            }}
            disabled={selectedDepth === null}
            className={`px-3 py-1 rounded text-xs ${
              selectedDepth === null
                ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            Select All Depth {selectedDepth || '?'}
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              e.preventDefault();
              handleDeselectAll();
            }}
            className="px-3 py-1 bg-gray-600 text-white rounded text-xs hover:bg-gray-700"
          >
            Clear All
          </button>
        </div>
      </div>



      {/* Selection Summary */}
      {selectedFolders.length > 0 && (
        <div className="mb-4 p-3 bg-green-800 border border-green-600 rounded-lg">
          <div className="text-green-200 text-sm">
            ✅ Selected {selectedFolders.length} folder(s) at <strong>Depth {selectedDepth}</strong>:
          </div>
          <div className="text-green-100 text-xs mt-1 max-h-20 overflow-y-auto">
            {selectedFolders.map((f, idx) => (
              <div key={f.id}>
                {idx + 1}. {f.name} <span className="text-green-300">({getFolderTypeLabel(f)})</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="mb-4 p-3 bg-red-800 border border-red-600 rounded-lg">
          <div className="text-red-200 text-sm">
            ⚠️ {error}
          </div>
          <button
            onClick={() => setError(null)}
            type="button"
            className="mt-2 px-3 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Tree Container */}
      <div className="tree-container bg-gray-700 rounded-lg p-4 max-h-96 overflow-y-auto border border-gray-600">
        {treeData['root'] ? (
          <div>
            {/* Root Node */}
            <div className="flex items-center py-2 px-3 bg-gray-600 rounded mb-2">
              <span className="mr-2 text-lg">💾</span>
              <div className="flex-1">
                <div className="text-white font-medium">My Drive</div>
                <div className="text-xs text-gray-300">Root directory - expand to navigate (max depth {maxDepth})</div>
              </div>
              <div className="text-xs px-2 py-1 bg-gray-500 text-gray-200 rounded">D0 Root</div>
            </div>

            {/* Root Children */}
            {treeData['root'].children && treeData['root'].children.map(folder => 
              renderFolderNode(folder, 0)
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400">
            <div className="text-lg mb-2">🔄</div>
            <div>Loading folders...</div>
          </div>
        )}
      </div>

      {/* 🎯 NEW: Updated Instructions */}
      <div className="mt-4 p-3 bg-blue-800 border border-blue-600 rounded-lg">
        <div className="text-blue-200 text-sm">
          <div className="font-medium mb-1">📍 Selection Rules:</div>
          <div className="text-xs space-y-1">
            <div>• Folders displayed up to depth {maxDepth} only</div>
            <div>• Checkboxes available on all depth levels (1-{maxDepth})</div>
            <div>• All selected folders must be at the same depth level</div>
            <div>• Use "Clear All" to switch to different depth level</div>
          </div>
        </div>
      </div>

      {/* Debug Info (Development) */}
      {process.env.NODE_ENV === 'development' && (
        <details className="mt-4 p-3 bg-gray-800 rounded">
          <summary className="text-xs text-gray-400 cursor-pointer">🔧 Debug - Depth Consistency</summary>
          <pre className="text-xs text-gray-400 mt-2 overflow-auto max-h-32">
            {JSON.stringify({
              maxDepth: maxDepth,
              selectedDepth: selectedDepth,
              selectedCount: selectedFolders.length,
              selectedFolders: selectedFolders.map(f => ({ name: f.name, depth: f.depth, type: getFolderTypeLabel(f) })),
              expandedCount: expandedFolders.size,
              authentication: authStatus.authenticated,
              hasError: !!error
            }, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
};

export default GoogleDriveFolderTree;