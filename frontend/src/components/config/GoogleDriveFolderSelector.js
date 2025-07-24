// ⚠️ DEPRECATED: This component has been replaced by GoogleDrivePickerIntegration
// This file is kept for rollback purposes only and will be removed in future versions
// Use GoogleDrivePickerIntegration.js instead

console.warn('⚠️ GoogleDriveFolderSelector is deprecated. Use GoogleDrivePickerIntegration instead.');

// components/config/GoogleDriveFolderSelector.js - 2-Step Folder Selection
import React, { useState, useEffect } from 'react';

const GoogleDriveFolderSelector = ({
  rootFolders = [],
  subFolders = [],
  selectedRootFolder = null,
  selectedCameraFolders = [],
  isLoadingFolders = false,
  onSelectRoot,
  onSelectCameras
}) => {
  // ⚠️ DEPRECATION WARNING: Show to developers
  useEffect(() => {
    console.warn('⚠️ GoogleDriveFolderSelector is DEPRECATED');
    console.warn('   → Replace with GoogleDrivePickerIntegration.js');
    console.warn('   → This component will be removed in future versions');
    console.warn('   → Phase 3 migration completed - update your imports');
  }, []);

  // Local state
  const [expandedFolders, setExpandedFolders] = useState(new Set());
  const [searchTerm, setSearchTerm] = useState('');
  const [viewMode, setViewMode] = useState('tree'); // 'tree' or 'list'
  const [folderStructure, setFolderStructure] = useState('unknown');

  // Filter folders based on search term
  const filteredRootFolders = rootFolders.filter(folder =>
    folder.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredSubFolders = subFolders.filter(folder =>
    folder.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Detect folder structure when subfolders load
  useEffect(() => {
    if (subFolders.length > 0) {
      // Check if subfolders look like camera folders
      const cameraKeywords = ['cam', 'camera', 'channel', 'ch', 'zone', 'area'];
      const cameraFolderCount = subFolders.filter(folder =>
        cameraKeywords.some(keyword => 
          folder.name.toLowerCase().includes(keyword)
        )
      ).length;

      if (cameraFolderCount > 0) {
        setFolderStructure('nested_cameras');
      } else {
        setFolderStructure('nested_general');
      }
    } else {
      setFolderStructure('unknown');
    }
  }, [subFolders]);

  // Handle root folder click/selection
  const handleRootFolderClick = (folder) => {
    if (selectedRootFolder?.id === folder.id) {
      // Already selected - toggle expansion
      const newExpanded = new Set(expandedFolders);
      if (newExpanded.has(folder.id)) {
        newExpanded.delete(folder.id);
      } else {
        newExpanded.add(folder.id);
      }
      setExpandedFolders(newExpanded);
    } else {
      // New selection
      if (onSelectRoot) {
        onSelectRoot(folder);
      }
      
      // Auto-expand the selected folder
      const newExpanded = new Set(expandedFolders);
      newExpanded.add(folder.id);
      setExpandedFolders(newExpanded);
    }
  };

  // Handle camera folder toggle
  const handleCameraFolderToggle = (cameraFolder) => {
    const currentSelected = [...selectedCameraFolders];
    const folderName = cameraFolder.name;
    
    if (currentSelected.includes(folderName)) {
      // Remove from selection
      const newSelected = currentSelected.filter(name => name !== folderName);
      if (onSelectCameras) {
        onSelectCameras(newSelected);
      }
    } else {
      // Add to selection
      const newSelected = [...currentSelected, folderName];
      if (onSelectCameras) {
        onSelectCameras(newSelected);
      }
    }
  };

  // Select all camera folders
  const handleSelectAllCameras = () => {
    const allCameraNames = subFolders.map(folder => folder.name);
    if (onSelectCameras) {
      onSelectCameras(allCameraNames);
    }
  };

  // Deselect all camera folders
  const handleDeselectAllCameras = () => {
    if (onSelectCameras) {
      onSelectCameras([]);
    }
  };

  // Get folder icon based on folder type
  const getFolderIcon = (folder) => {
    const name = folder.name.toLowerCase();
    
    if (name.includes('camera') || name.includes('cam')) return '📹';
    if (name.includes('security') || name.includes('surveillance')) return '🔒';
    if (name.includes('recording') || name.includes('video')) return '🎬';
    if (name.includes('storage') || name.includes('archive')) return '💾';
    if (name.includes('backup')) return '🔄';
    
    return '📁';
  };

  // Get selection status for bulk operations
  const getSelectionStatus = () => {
    if (subFolders.length === 0) return 'none';
    if (selectedCameraFolders.length === 0) return 'none';
    if (selectedCameraFolders.length === subFolders.length) return 'all';
    return 'partial';
  };

  return (
    <div className="space-y-4">
      
      {/* ⚠️ DEPRECATION WARNING BANNER */}
      <div className="bg-orange-800 border border-orange-600 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <span className="text-orange-200 text-xl">⚠️</span>
          <div className="text-orange-200">
            <div className="font-medium">DEPRECATED COMPONENT</div>
            <div className="text-sm">This component has been replaced by GoogleDrivePickerIntegration. Please update your code.</div>
          </div>
        </div>
      </div>
      
      {/* Header with Search and View Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h4 className="font-medium text-white">📁 Folder Selection</h4>
          
          {/* View Mode Toggle */}
          <div className="flex bg-gray-600 rounded overflow-hidden">
            <button
              onClick={() => setViewMode('tree')}
              className={`px-3 py-1 text-xs font-medium ${
                viewMode === 'tree' 
                  ? 'bg-blue-600 text-white' 
                  : 'text-gray-300 hover:text-white'
              }`}
            >
              Tree
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`px-3 py-1 text-xs font-medium ${
                viewMode === 'list' 
                  ? 'bg-blue-600 text-white' 
                  : 'text-gray-300 hover:text-white'
              }`}
            >
              List
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <input
            type="text"
            placeholder="Search folders..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-48 px-3 py-1 bg-gray-600 text-white text-sm rounded border border-gray-500 focus:border-blue-500"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white"
            >
              ×
            </button>
          )}
        </div>
      </div>

      {/* Step 1: Root Folder Selection */}
      <div className="bg-gray-600 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <h5 className="font-medium text-white">Step 1: Select Root Folder</h5>
          <span className="text-xs text-gray-300">
            {filteredRootFolders.length} folder(s) available
          </span>
        </div>

        {filteredRootFolders.length === 0 ? (
          <div className="text-center py-6 text-gray-400">
            <div className="text-2xl mb-2">📂</div>
            <div className="text-sm">
              {searchTerm ? 'No folders match your search' : 'No folders available'}
            </div>
          </div>
        ) : (
          <div className="space-y-2 max-h-32 overflow-y-auto">
            {filteredRootFolders.map((folder) => (
              <div
                key={folder.id}
                onClick={() => handleRootFolderClick(folder)}
                className={`flex items-center gap-3 p-3 rounded cursor-pointer transition-colors ${
                  selectedRootFolder?.id === folder.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 hover:bg-gray-650 text-gray-300'
                }`}
              >
                <span className="text-lg">{getFolderIcon(folder)}</span>
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{folder.name}</div>
                  {folder.description && (
                    <div className="text-xs opacity-75 truncate">{folder.description}</div>
                  )}
                </div>
                {selectedRootFolder?.id === folder.id && (
                  <span className="text-green-300 text-sm">✓ Selected</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Step 2: Camera Folder Selection */}
      {selectedRootFolder && (
        <div className="bg-gray-600 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h5 className="font-medium text-white">
              Step 2: Select Camera Folders
              <span className="text-sm text-gray-300 ml-2">
                from "{selectedRootFolder.name}"
              </span>
            </h5>
            
            {/* Bulk Selection Controls */}
            {subFolders.length > 0 && (
              <div className="flex gap-2">
                <button
                  onClick={handleSelectAllCameras}
                  disabled={getSelectionStatus() === 'all'}
                  className="px-3 py-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-500 text-white rounded text-xs font-medium"
                >
                  Select All
                </button>
                <button
                  onClick={handleDeselectAllCameras}
                  disabled={getSelectionStatus() === 'none'}
                  className="px-3 py-1 bg-gray-500 hover:bg-gray-600 disabled:bg-gray-400 text-white rounded text-xs font-medium"
                >
                  Clear All
                </button>
              </div>
            )}
          </div>

          {/* Loading State */}
          {isLoadingFolders && (
            <div className="text-center py-6">
              <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-2"></div>
              <div className="text-sm text-gray-400">Loading camera folders...</div>
            </div>
          )}

          {/* No Subfolders */}
          {!isLoadingFolders && subFolders.length === 0 && (
            <div className="text-center py-6 text-gray-400">
              <div className="text-2xl mb-2">📹</div>
              <div className="text-sm">
                No camera folders found in "{selectedRootFolder.name}"
              </div>
              <div className="text-xs mt-1">
                Try selecting a different root folder
              </div>
            </div>
          )}

          {/* Camera Folders List */}
          {!isLoadingFolders && filteredSubFolders.length > 0 && (
            <div>
              {/* Folder Structure Info */}
              {folderStructure === 'nested_cameras' && (
                <div className="bg-green-800 border border-green-600 rounded p-2 mb-3">
                  <div className="text-xs text-green-200">
                    🎯 Camera folder structure detected! These appear to be camera recording folders.
                  </div>
                </div>
              )}

              {viewMode === 'tree' ? (
                /* Tree View */
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {filteredSubFolders.map((folder) => (
                    <label
                      key={folder.id}
                      className="flex items-center gap-3 p-2 rounded cursor-pointer hover:bg-gray-700 transition-colors"
                    >
                      <input
                        type="checkbox"
                        checked={selectedCameraFolders.includes(folder.name)}
                        onChange={() => handleCameraFolderToggle(folder)}
                        className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
                      />
                      <span className="text-lg">{getFolderIcon(folder)}</span>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-white truncate">{folder.name}</div>
                        {folder.file_count && (
                          <div className="text-xs text-gray-400">
                            {folder.file_count} files
                          </div>
                        )}
                      </div>
                      {folder.size && (
                        <div className="text-xs text-gray-400">
                          {(folder.size / 1024 / 1024).toFixed(1)} MB
                        </div>
                      )}
                    </label>
                  ))}
                </div>
              ) : (
                /* List View */
                <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                  {filteredSubFolders.map((folder) => (
                    <label
                      key={folder.id}
                      className={`flex items-center gap-2 p-2 rounded cursor-pointer transition-colors ${
                        selectedCameraFolders.includes(folder.name)
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-700 hover:bg-gray-650 text-gray-300'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedCameraFolders.includes(folder.name)}
                        onChange={() => handleCameraFolderToggle(folder)}
                        className="w-4 h-4"
                      />
                      <span>{getFolderIcon(folder)}</span>
                      <span className="font-medium text-sm truncate">{folder.name}</span>
                    </label>
                  ))}
                </div>
              )}

              {/* Selection Summary */}
              <div className="mt-3 p-2 bg-gray-700 rounded">
                <div className="text-sm text-gray-300">
                  <strong>Selected:</strong> {selectedCameraFolders.length} of {subFolders.length} camera folders
                </div>
                {selectedCameraFolders.length > 0 && (
                  <div className="text-xs text-gray-400 mt-1">
                    {selectedCameraFolders.slice(0, 3).join(', ')}
                    {selectedCameraFolders.length > 3 && ` +${selectedCameraFolders.length - 3} more`}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Configuration Summary */}
      {selectedRootFolder && selectedCameraFolders.length > 0 && (
        <div className="bg-green-800 border border-green-600 rounded-lg p-3">
          <h5 className="font-medium text-green-100 mb-2">📋 Selection Summary</h5>
          <div className="text-sm text-green-200 space-y-1">
            <div><strong>Root Folder:</strong> {selectedRootFolder.name}</div>
            <div><strong>Camera Folders:</strong> {selectedCameraFolders.length} selected</div>
            <div><strong>Structure:</strong> {folderStructure === 'nested_cameras' ? 'Nested Camera Folders' : 'Nested General Folders'}</div>
            <div className="text-xs text-green-300 mt-2">
              Videos will be synced from: {selectedRootFolder.name}/{selectedCameraFolders.join(', ')}
            </div>
          </div>
        </div>
      )}

      {/* Debug Info (Development) */}
      {process.env.NODE_ENV === 'development' && (
        <details className="bg-gray-800 rounded p-2">
          <summary className="text-xs text-gray-400 cursor-pointer">🔧 Debug - Folder Selection</summary>
          <pre className="text-xs text-gray-400 mt-2 overflow-auto">
            {JSON.stringify({
              rootFolders: rootFolders.length,
              subFolders: subFolders.length,
              selectedRoot: selectedRootFolder?.name,
              selectedCameras: selectedCameraFolders,
              folderStructure,
              searchTerm,
              viewMode,
              DEPRECATED: true,
              replacement: 'GoogleDrivePickerIntegration.js'
            }, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
};

export default GoogleDriveFolderSelector;