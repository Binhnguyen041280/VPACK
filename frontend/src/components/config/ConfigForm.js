import React, { useState, useEffect, useCallback } from 'react';
import AddSourceModal from './AddSourceModal';

const ConfigForm = ({
  inputPath,
  setInputPath,
  outputPath,
  setOutputPath,
  defaultDays,
  setDefaultDays,
  minPackingTime,
  setMinPackingTime,
  maxPackingTime,
  setMaxPackingTime,
  frameRate,
  setFrameRate,
  frameInterval,
  setFrameInterval,
  videoBuffer,
  setVideoBuffer,
  error,
  handleOpenExplorer,
  handleShowCameraDialog,
  runDefaultOnStart,
  setRunDefaultOnStart,
  
  // 🆕 NEW: Receive camera data from VtrackConfig
  camerasFromParent = [],
  selectedCamerasFromParent = [],
  activeSourceFromParent = null,
  isLoadingCameras = false,
  
  // ✅ NEW: Callback to notify parent about camera changes
  onCamerasUpdated,
}) => {
  // ✅ USE: Data from parent instead of local state
  const [activeSource, setActiveSource] = useState(activeSourceFromParent);
  const [sourceCameras, setSourceCameras] = useState(camerasFromParent);
  const [selectedCameras, setSelectedCameras] = useState(selectedCamerasFromParent);
  const [isLoadingSource, setIsLoadingSource] = useState(isLoadingCameras);
  
  // ✅ KEEP: Source management state only
  const [showAddSourceModal, setShowAddSourceModal] = useState(false);
  const [showUpdateSourceModal, setShowUpdateSourceModal] = useState(false);

  // ✅ NEW: Sync props to local state
  useEffect(() => {
    setActiveSource(activeSourceFromParent);
    setSourceCameras(camerasFromParent);
    setSelectedCameras(selectedCamerasFromParent);
    setIsLoadingSource(isLoadingCameras);
  }, [activeSourceFromParent, camerasFromParent, selectedCamerasFromParent, isLoadingCameras]);

  // API functions
  const addSources = async (sourcesData) => {
    const response = await fetch('/api/config/save-sources', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sourcesData)
    });
    return response.json();
  };

  const deleteSource = async (sourceId) => {
    const response = await fetch(`/api/config/delete-source/${sourceId}`, {
      method: 'DELETE'
    });
    return response.json();
  };

  const testSourceConnection = async (sourceData) => {
    const response = await fetch('/api/config/test-source', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sourceData)
    });
    return response.json();
  };

  const updateSourceCameras = async (sourceId, selectedCameras) => {
    const response = await fetch('/api/config/update-source-cameras', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_id: sourceId, selected_cameras: selectedCameras })
    });
    return response.json();
  };

  // ✅ NEW: Load cameras from source after adding
  const loadCamerasFromSource = async (sourceData) => {
    try {
      console.log("🔄 Loading cameras from new source:", sourceData.name);
      
      if (sourceData.source_type === 'cloud') {
        // For cloud sources, try to get cameras from config
        const cloudCameras = sourceData.config?.selected_cameras || [];
        if (cloudCameras.length > 0) {
          console.log("☁️ Found cloud cameras:", cloudCameras);
          setSourceCameras(cloudCameras);
          setSelectedCameras(cloudCameras);
          return cloudCameras;
        } else {
          console.log("☁️ No cameras in cloud config, will sync later");
        }
      } else if (sourceData.source_type === 'local') {
        // For local sources, detect camera folders
        const response = await fetch('/api/config/detect-cameras', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: sourceData.path })
        });
        
        if (response.ok) {
          const data = await response.json();
          const cameras = data.cameras || [];
          console.log("📁 Detected local cameras:", cameras);
          setSourceCameras(cameras);
          return cameras;
        }
      }
      
      return [];
    } catch (error) {
      console.error("❌ Error loading cameras from source:", error);
      return [];
    }
  };

  // ✅ ENHANCED: Simple overwrite with fresh camera reload
  const handleAddSource = async (sourceData) => {
    try {
      console.log('Adding source:', sourceData);
      setIsLoadingSource(true);
      
      // ✅ STEP 1: Try normal add first
      let response = await fetch('/api/config/save-sources', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sources: [sourceData] })
      });
      
      let result = await response.json();
      
      // ✅ STEP 2: If duplicate, automatically overwrite
      if (!response.ok && result.error && result.error.includes('already exists')) {
        console.log("🔄 Source exists, overwriting automatically...");
        
        // Add overwrite flag and retry
        const overwriteData = { 
          sources: [{ ...sourceData, overwrite: true }] 
        };
        
        response = await fetch('/api/config/save-sources', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(overwriteData)
        });
        
        result = await response.json();
        
        if (!response.ok || result.error) {
          throw new Error(result.error || 'Failed to overwrite source');
        }
        
        console.log("✅ Source overwritten successfully");
      } else if (!response.ok || result.error) {
        throw new Error(result.error || `Server error: ${response.status}`);
      }
      
      // ✅ STEP 3: Update UI state
      setActiveSource(sourceData);
      
      // ✅ CRITICAL FIX: Reload cameras from server after source change
      console.log("🔄 Reloading cameras from server after source change...");
      
      let freshCameras = [];
      try {
        const camerasResponse = await fetch('http://localhost:8080/api/config/get-processing-cameras', {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' }
        });
        
        if (camerasResponse.ok) {
          const camerasData = await camerasResponse.json();
          freshCameras = camerasData.selected_cameras || [];
          
          console.log("✅ Reloaded fresh cameras from server:", freshCameras);
          
          // Update local camera state
          setSourceCameras(freshCameras);
          setSelectedCameras(freshCameras);
          
          // ✅ NEW: Notify parent component about camera changes
          if (onCamerasUpdated) {
            onCamerasUpdated(freshCameras, freshCameras, sourceData);
            console.log("✅ Notified parent component about camera changes");
          }
          
          console.log("✅ Updated local camera state with fresh data");
        } else {
          console.error("❌ Failed to reload cameras from server");
          // Fallback to local camera detection
          freshCameras = await loadCamerasFromSource(sourceData);
        }
      } catch (cameraError) {
        console.error("❌ Error reloading cameras:", cameraError);
        // Fallback to local camera detection
        freshCameras = await loadCamerasFromSource(sourceData);
      }
      
      const workingPath = getWorkingPathForSource(sourceData);
      setInputPath(workingPath);
      
      setShowAddSourceModal(false);
      
      // ✅ STEP 4: Success message with fresh camera count
      alert(`✅ ${sourceData.source_type.toUpperCase()} source configured successfully!\n\nSource: "${sourceData.name}"\nCameras: ${freshCameras.length} detected\n\nCamera data refreshed from server.`);
      
      console.log("✅ Source setup completed with fresh camera data");
      
    } catch (error) {
      console.error('❌ Error setting up source:', error);
      alert(`❌ Failed to setup source: ${error.message}`);
    } finally {
      setIsLoadingSource(false);
    }
  };

  // Update Source Handler
  const handleUpdateSource = () => {
    if (!activeSource) return;
    setShowUpdateSourceModal(true);
  };

  // ✅ SIMPLIFIED: Clear source without complex delete logic
  const handleChangeSourceType = async () => {
    if (!activeSource) return;
    
    if (!window.confirm(`Remove current source "${activeSource.name}" to add a new one?`)) return;
    
    try {
      // ✅ FIX: Handle undefined ID gracefully
      if (activeSource.id) {
        // Delete current source if ID exists
        await deleteSource(activeSource.id);
        console.log("✅ Source deleted successfully");
      } else {
        console.log("⚠️ No source ID found, clearing local state only");
      }
      
    } catch (error) {
      console.error('❌ Error removing source:', error);
      console.log("⚠️ Delete failed, but continuing with local state reset");
    }
    
    // ✅ ALWAYS reset local state regardless of delete success/failure
    setActiveSource(null);
    setSourceCameras([]);
    setSelectedCameras([]);
    setInputPath('');
    
    // ✅ NEW: Notify parent about state reset
    if (onCamerasUpdated) {
      onCamerasUpdated([], [], null);
    }
    
    alert('Source cleared. You can now add a new source.');
  };

  const handleUpdateComplete = () => {
    // ✅ SIMPLIFIED: Just close modal and soft refresh data
    setShowUpdateSourceModal(false);
    
    // ✅ Optional: Reload source data from backend if needed
    setTimeout(async () => {
      try {
        const response = await fetch('/api/config/get-sources');
        const data = await response.json();
        const sources = data.sources || [];
        const currentActiveSource = sources.find(s => s.active) || sources[0];
        
        if (currentActiveSource) {
          setActiveSource(currentActiveSource);
          const cameras = await loadCamerasFromSource(currentActiveSource);
          console.log("🔄 Refreshed source data after update");
        }
      } catch (error) {
        console.error("❌ Error refreshing source data:", error);
      }
    }, 500);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    try {
      return new Date(dateString).toLocaleString('vi-VN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'Asia/Ho_Chi_Minh'
      });
    } catch {
      return dateString;
    }
  };

  // Get source type display info
  const getSourceTypeInfo = (sourceType) => {
    const sourceTypes = {
      local: {
        icon: '📁',
        name: 'LOCAL STORAGE',
        color: 'bg-blue-600'
      },
      cloud: {
        icon: '☁️',
        name: 'CLOUD STORAGE',
        color: 'bg-cyan-600'
      }
    };
    return sourceTypes[sourceType] || { icon: '❓', name: 'UNKNOWN', color: 'bg-gray-600' };
  };

  // ✅ Helper to get working path for different source types
  const getWorkingPathForSource = (source) => {
    if (!source) return "";
    
    switch (source.source_type) {
      case 'local':
        return source.path;
      case 'cloud':
        return `/Users/annhu/vtrack_app/V_Track/cloud_sync/${source.name}`;
      default:
        return source.path;
    }
  };

  return (
    <div className="w-[25%] bg-gray-800 p-6 rounded-lg flex flex-col">
      <h1 className="text-3xl font-bold mb-4">Cấu hình</h1>
      {error && <div style={{ color: 'red' }}>{error}</div>}
      
      {/* Single Active Video Source Section */}
      <div className="mb-6 p-4 bg-gray-700 rounded-lg">
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-lg font-bold text-white">Current Video Input Source</h3>
        </div>

        {isLoadingSource ? (
          <div className="text-center py-4">
            <div className="text-gray-400 text-sm">Loading source...</div>
          </div>
        ) : activeSource ? (
          <div className="bg-gray-600 p-4 rounded-lg">
            <div className="flex items-center gap-2 mb-3">
              <span className="font-medium text-white text-lg">{activeSource.name}</span>
              <span className="px-2 py-1 rounded text-xs bg-green-600 text-white">
                Active
              </span>
            </div>
            
            {/* Enhanced Source Type Display */}
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm text-gray-300"><strong>Type:</strong></span>
              <div className="flex items-center gap-1">
                <span className="text-sm">{getSourceTypeInfo(activeSource.source_type).icon}</span>
                <span className={`px-2 py-1 rounded text-xs text-white font-medium ${getSourceTypeInfo(activeSource.source_type).color}`}>
                  {getSourceTypeInfo(activeSource.source_type).name}
                </span>
              </div>
            </div>
            
            <div className="text-gray-300 text-sm mb-2 break-all">
              <strong>Path:</strong> {activeSource.path}
            </div>
            
            <div className="text-gray-300 text-sm mb-2">
              <strong>Added:</strong> {formatDate(activeSource.created_at)}
            </div>
            
            {/* ✅ UPDATED: Camera Information */}
            {(activeSource.source_type === 'local' || 
              activeSource.source_type === 'cloud') && (
              <div className="text-gray-300 text-sm mb-3">
                <strong>Cameras:</strong>{' '}
                {sourceCameras.length > 0 ? (
                  <span>
                    {selectedCameras.length} selected of {sourceCameras.length} detected
                    <div className="mt-1 text-xs">
                      {selectedCameras.length > 0 ? (
                        <span className="text-green-300">
                          Active: {selectedCameras.slice(0, 3).join(', ')}
                          {selectedCameras.length > 3 && ` +${selectedCameras.length - 3} more`}
                        </span>
                      ) : (
                        <span className="text-yellow-300">No cameras selected</span>
                      )}
                    </div>
                    {sourceCameras.length > selectedCameras.length && (
                      <div className="text-xs text-gray-400">
                        Available: {sourceCameras.filter(cam => !selectedCameras.includes(cam)).slice(0, 2).join(', ')}
                        {sourceCameras.filter(cam => !selectedCameras.includes(cam)).length > 2 && '...'}
                      </div>
                    )}
                  </span>
                ) : isLoadingSource ? (
                  <span className="text-blue-300">Loading cameras...</span>
                ) : (
                  <span className="text-gray-400">
                    {activeSource.source_type === 'cloud' ? 'No cameras synced' :
                     'No camera folders detected'}
                  </span>
                )}
              </div>
            )}            
            
            {/* Action Buttons */}
            <div className="flex justify-end gap-2">
              <button
                onClick={handleUpdateSource}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-medium"
              >
                Update
              </button>
              <button
                onClick={handleChangeSourceType}
                className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded text-sm font-medium"
              >
                Change
              </button>
            </div>
          </div>
        ) : (
          <div className="text-center py-6">
            <div className="text-gray-400 text-sm mb-3">
              No video source configured yet.
            </div>
            <button
              onClick={() => setShowAddSourceModal(true)}
              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded font-medium"
            >
              Add Video Source
            </button>
          </div>
        )}
      </div>

      {/* ✅ FIX: Input Path Section - DISTINGUISH CLOUD vs LOCAL */}
      <div className="mb-6 p-4 bg-gray-700 rounded-lg">
        <h3 className="text-lg font-bold text-white mb-3">Input Video Path</h3>
        
        {activeSource ? (
          <div className="bg-gray-600 p-3 rounded">
            <div className="text-sm text-gray-300 mb-1">
              <strong>Source:</strong> {activeSource.name}
            </div>
            
            {activeSource.source_type === 'local' ? (
              <>
                <div className="text-sm text-gray-300 mb-1">
                  <strong>File System Path:</strong> {activeSource.path}
                </div>
                <div className="text-sm text-gray-300 mb-1">
                  <strong>Processing Path:</strong> {getWorkingPathForSource(activeSource)}
                </div>
                <div className="mt-2 text-xs text-green-300">
                  📁 Videos will be processed directly from this location
                </div>
              </>
            ) : activeSource.source_type === 'cloud' ? (
              <>
                <div className="text-sm text-gray-300 mb-1">
                  <strong>Cloud Connection:</strong> {activeSource.path}
                </div>
                <div className="text-sm text-gray-300 mb-1">
                  <strong>Sync Directory:</strong> {getWorkingPathForSource(activeSource)}
                </div>
                <div className="mt-2 text-xs text-cyan-300">
                  ☁️ Cloud files will be synced to local directory for processing
                </div>
              </>
            ) : (
              <>
                <div className="text-sm text-gray-300 mb-1">
                  <strong>Source Path:</strong> {activeSource.path}
                </div>
                <div className="text-sm text-gray-300 mb-1">
                  <strong>Working Path:</strong> {getWorkingPathForSource(activeSource)}
                </div>
                <div className="mt-2 text-xs text-yellow-300">
                  ⚠️ Source type: {activeSource.source_type}
                </div>
              </>
            )}
            
            <div className="text-sm text-gray-300">
              <strong>Type:</strong> {getSourceTypeInfo(activeSource.source_type).name}
            </div>
            <div className="mt-2 text-xs text-green-300">
              ✅ Input path automatically configured from video source
            </div>
          </div>
        ) : (
          <div className="text-center py-4 bg-gray-600 rounded">
            <div className="text-gray-400 text-sm mb-3">
              No video source configured. Input path will be empty.
            </div>
            <button
              onClick={() => setShowAddSourceModal(true)}
              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded text-sm font-medium"
            >
              Add Video Source First
            </button>
          </div>
        )}
      </div>

      {/* Legacy Input Path Field - Hidden khi có video source */}
      {!activeSource && (
        <div className="mb-4">
          <label className="block mb-1">Legacy Input Path (Deprecated):</label>
          <div className="relative w-full">
            <input
              type="text"
              value={inputPath}
              onChange={(e) => setInputPath(e.target.value)}
              placeholder="Please add a video source instead"
              className="w-full p-2 rounded bg-gray-700 text-white"
              disabled
            />
            <div className="text-xs text-yellow-400 mt-1">
              ⚠️ Please use "Add Video Source" button above instead
            </div>
          </div>
        </div>
      )}

      <div className="mb-4">
        <label className="block mb-1">Vị trí Output Video:</label>
        <div className="relative w-full">
          <input
            type="text"
            value={outputPath}
            onChange={(e) => setOutputPath(e.target.value)}
            placeholder="Vị trí Output Video (e.g., /Users/annhu/vtrack_app/V_Track/output_clips)"
            className="w-full p-2 rounded bg-gray-700 text-white"
          />
          <button
            type="button"
            onClick={() => handleOpenExplorer("output")}
            className="absolute right-2 top-1/2 transform -translate-y-1/2 text-white"
          >
            ...
          </button>
        </div>
      </div>
      
      <div className="flex flex-col gap-4 mb-4">
        <div>
          <label className="block mb-1">Thời gian lưu trữ (ngày):</label>
          <input
            type="number"
            value={defaultDays}
            onChange={(e) => setDefaultDays(Number(e.target.value))}
            className="w-full p-2 rounded bg-gray-700 text-white"
          />
        </div>
        <div>
          <label className="block mb-1">Thời gian đóng hàng nhanh nhất (giây):</label>
          <input
            type="number"
            value={minPackingTime}
            onChange={(e) => setMinPackingTime(Number(e.target.value))}
            className="w-full p-2 rounded bg-gray-700 text-white"
          />
        </div>
        <div>
          <label className="block mb-1">Thời gian đóng hàng chậm nhất (giây):</label>
          <input
            type="number"
            value={maxPackingTime}
            onChange={(e) => setMaxPackingTime(Number(e.target.value))}
            className="w-full p-2 rounded bg-gray-700 text-white"
          />
        </div>
        <div>
          <label className="block mb-1">Tốc độ frame:</label>
          <input
            type="number"
            value={frameRate}
            onChange={(e) => setFrameRate(Number(e.target.value))}
            className="w-full p-2 rounded bg-gray-700 text-white"
          />
        </div>
        <div>
          <label className="block mb-1">Khoảng cách Frame:</label>
          <input
            type="number"
            value={frameInterval}
            onChange={(e) => setFrameInterval(Number(e.target.value))}
            min="2"
            max="30"
            className="w-full p-2 rounded bg-gray-700 text-white"
          />
        </div>
        <div>
          <label className="block mb-1">Buffer Video (giây):</label>
          <input
            type="number"
            value={videoBuffer}
            onChange={(e) => setVideoBuffer(Number(e.target.value))}
            className="w-full p-2 rounded bg-gray-700 text-white"
          />
        </div>
      </div>
      
      <div className="mt-auto flex justify-center">
        <button
          onClick={handleShowCameraDialog}
          className="w-1/2 py-2 bg-blue-600 text-white font-bold rounded"
        >
          Gửi
        </button>
      </div>

      {/* Enhanced AddSourceModal */}
      {showAddSourceModal && (
        <AddSourceModal
          show={showAddSourceModal}
          onClose={() => setShowAddSourceModal(false)}
          onAdd={handleAddSource}
          testSourceConnection={testSourceConnection}
        />
      )}

      {/* Update Source Modal */}
      {showUpdateSourceModal && activeSource && (
        <SimpleUpdateSourceModal
          show={showUpdateSourceModal}
          source={activeSource}
          sourceCameras={sourceCameras}
          selectedCameras={selectedCameras}
          onClose={() => setShowUpdateSourceModal(false)}
          onUpdate={handleUpdateComplete}
          testSourceConnection={testSourceConnection}
          detectCameras={loadCamerasFromSource}
          updateSourceCameras={updateSourceCameras}
        />
      )}
    </div>
  );
};

// Enhanced Update Source Modal Component
const SimpleUpdateSourceModal = ({ 
  show, 
  source, 
  sourceCameras,
  selectedCameras: initialSelectedCameras,
  onClose, 
  onUpdate, 
  testSourceConnection, 
  detectCameras, 
  updateSourceCameras
}) => {
  const [path] = useState(source.path);
  const [detectedCameras, setDetectedCameras] = useState(sourceCameras);
  const [selectedCameras, setSelectedCameras] = useState(initialSelectedCameras);
  
  // Loading states
  const [isDetecting, setIsDetecting] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [testResult, setTestResult] = useState(null);

  useEffect(() => {
    setDetectedCameras(sourceCameras);
    setSelectedCameras(initialSelectedCameras);
  }, [sourceCameras, initialSelectedCameras]);

  const detectCamerasInPath = async () => {
    if (!path) return;
    
    setIsDetecting(true);
    try {
      if (source.source_type === 'local') {
        // ✅ SIMPLIFIED: For local source, use API call
        const response = await fetch('/api/config/get-camera-folders');
        if (response.ok) {
          const result = await response.json();
          const cameras = result.folders?.map(f => f.name) || [];
          
          if (cameras.length > 0) {
            setDetectedCameras(cameras);
            // Keep existing selected cameras that are still available
            const validSelectedCameras = selectedCameras.filter(cam => 
              cameras.includes(cam)
            );
            setSelectedCameras(validSelectedCameras);
          }
        }
      } else if (source.source_type === 'cloud') {
        // ✅ NEW: Cloud source handling
        alert('Cloud camera detection is handled automatically. Please refresh the page to see latest cameras.');
      }
    } catch (error) {
      console.error('Camera detection failed:', error);
      setDetectedCameras([]);
      setSelectedCameras([]);
    } finally {
      setIsDetecting(false);
    }
  };

  const handleTestConnection = async () => {
    if (!path) {
      alert('No path to test');
      return;
    }

    setIsLoading(true);
    try {
      const testData = {
        source_type: source.source_type,
        path: path,
        config: source.config || {}
      };
      
      const response = await testSourceConnection(testData);
      setTestResult({
        success: response.accessible,
        message: response.message
      });
      
    } catch (error) {
      setTestResult({
        success: false,
        message: error.message || 'Connection test failed'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCameraToggle = (cameraName) => {
    setSelectedCameras(prev => 
      prev.includes(cameraName) 
        ? prev.filter(c => c !== cameraName)
        : [...prev, cameraName]
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      // Update camera selection
      await updateSourceCameras(source.id, selectedCameras);
      
      alert('Source updated successfully!');
      onUpdate();
    } catch (error) {
      console.error('Error updating source:', error);
      alert('Failed to update source: ' + (error.response?.data?.error || error.message));
    }
  };

  if (!show) return null;

  const getSourceTypeInfo = (sourceType) => {
    const sourceTypes = {
      local: { icon: '📁', name: 'LOCAL STORAGE' },
      cloud: { icon: '☁️', name: 'CLOUD STORAGE' }
    };
    return sourceTypes[sourceType] || { icon: '❓', name: 'UNKNOWN' };
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg p-6 w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-bold text-white">🔧 Update Video Source</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Source Type Info */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Source Type
            </label>
            <div className="w-full p-3 border border-gray-600 rounded bg-gray-700 text-white flex items-center">
              <span className="mr-2">{getSourceTypeInfo(source.source_type).icon}</span>
              <span className="font-medium">{getSourceTypeInfo(source.source_type).name}</span>
              <span className="ml-2 text-gray-400 text-sm">(ReadOnly)</span>
            </div>
          </div>

          {/* Path Info */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Path
            </label>
            <div className="w-full p-3 border border-gray-600 rounded bg-gray-700 text-white break-all">
              {path}
            </div>
          </div>

          {/* Camera Selection */}
          <div className="mb-4">
            <div className="flex justify-between items-center mb-3">
              <label className="block text-sm font-medium text-gray-300">
                {source.source_type === 'cloud' ? 'Synced Cameras' : 'Camera Folders'}
              </label>
              <button
                type="button"
                onClick={detectCamerasInPath}
                disabled={isDetecting}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-3 py-1 rounded text-xs"
              >
                {isDetecting ? 'Scanning...' : source.source_type === 'cloud' ? 'Refresh' : 'Rescan'}
              </button>
            </div>
            
            {isDetecting ? (
              <div className="text-center py-4">
                <div className="text-gray-400 text-sm">
                  {source.source_type === 'cloud' ? 'Refreshing cameras...' : 'Detecting cameras...'}
                </div>
              </div>
            ) : detectedCameras.length > 0 ? (
              <div className="grid grid-cols-2 gap-2 p-3 bg-gray-700 rounded">
                {detectedCameras.map(camera => (
                  <label key={camera} className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedCameras.includes(camera)}
                      onChange={() => handleCameraToggle(camera)}
                      className="rounded"
                    />
                    <span className="text-white text-sm">{camera}</span>
                  </label>
                ))}
              </div>
            ) : (
              <div className="text-center py-4 bg-gray-700 rounded">
                <div className="text-gray-400 text-sm">
                  {source.source_type === 'cloud' ? 'No cameras synced' : 'No camera folders detected'}
                </div>
              </div>
            )}
            
            {selectedCameras.length > 0 && (
              <div className="mt-2 text-xs text-gray-400">
                Selected: {selectedCameras.length} camera(s)
              </div>
            )}
          </div>

          {/* Test Connection */}
          <div className="mb-4">
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={isLoading}
              className="bg-yellow-600 hover:bg-yellow-700 disabled:bg-gray-600 text-white px-4 py-2 rounded font-medium"
            >
              {isLoading ? 'Testing...' : 'Test Connection'}
            </button>
            
            {testResult && (
              <div className={`mt-2 p-3 rounded text-sm ${
                testResult.success ? 'bg-green-800 text-green-200' : 'bg-red-800 text-red-200'
              }`}>
                {testResult.message}
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              type="submit"
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded font-medium"
            >
              Save Changes
            </button>
            <button
              type="button"
              onClick={onClose}
              className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded font-medium"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ConfigForm;