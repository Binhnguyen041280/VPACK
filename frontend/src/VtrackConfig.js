import React from "react";
import useVtrackConfig from "./hooks/useVtrackConfig";
import GeneralInfoForm from "./components/config/GeneralInfoForm";
import ConfigForm from "./components/config/ConfigForm";
import CameraDialog from "./components/config/CameraDialog";
import ProcessingRegionForm from "./components/config/ProcessingRegionForm";

const VtrackConfig = () => {
  const {
    fromTime,
    setFromTime,
    toTime,
    setToTime,
    country,
    setCountry,
    timezone,
    setTimezone,
    brandName,
    setBrandName,
    inputPath,
    setInputPath,
    outputPath,
    setOutputPath,
    workingDays,
    setWorkingDays,
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
    cameras,
    setCameras,
    selectedCameras,
    setSelectedCameras,
    showCameraDialog,
    setShowCameraDialog,
    error,
    setError,
    handleCountryChange,
    handleFromTimeChange,
    handleToTimeChange,
    handleWorkingDayChange,
    handleOpenExplorer,
    handleSaveGeneralInfo,
    handleSaveConfig,
    handleShowCameraDialog,
    handleCameraSelection,
    runDefaultOnStart,
    setRunDefaultOnStart,
  } = useVtrackConfig();

  const [configFormCameras, setConfigFormCameras] = React.useState([]);
  const [configFormSelectedCameras, setConfigFormSelectedCameras] = React.useState([]);
  const [activeVideoSource, setActiveVideoSource] = React.useState(null);
  const [loadingCameras, setLoadingCameras] = React.useState(false);

  const [videoPath, setVideoPath] = React.useState("");
  const [qrSize, setQrSize] = React.useState("");
  
  const handleAnalyzeRegions = () => {
    console.log("Phân tích vùng:", videoPath, qrSize);
  };

  // ✅ ENHANCED: Helper function để get correct input path based on source type (NO NVR)
  const getInputPathForSource = (source) => {
    if (!source) return "";
    
    let resultPath = "";
    
    switch (source.source_type) {
      case 'local':
        // Local: Use actual file system path
        resultPath = source.path;
        console.log(`📁 Local Path Mapping: ${source.path} → ${resultPath}`);
        break;
      case 'cloud':
        // Cloud: Use sync directory
        resultPath = `/Users/annhu/vtrack_app/V_Track/cloud_sync/${source.name}`;
        console.log(`☁️ Cloud Path Mapping: ${source.path} → ${resultPath}`);
        break;
      default:
        resultPath = source.path;
        console.log(`❓ Unknown Path Mapping: ${source.path} → ${resultPath}`);
    }
    
    return resultPath;
  };

  // 🆕 NEW: Load active source from backend
  const loadActiveSource = React.useCallback(async () => {
    try {
      console.log("🔄 Loading active video source...");
      
      const response = await fetch('http://localhost:8080/api/config/get-sources', {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        const data = await response.json();
        const sources = data.sources || [];
        
        // Tìm source active (chỉ có 1 source active)
        const activeSource = sources.find(s => s.active) || sources[0];
        
        if (activeSource) {
          console.log("✅ Found active source:", activeSource.name, activeSource.source_type);
          setActiveVideoSource(activeSource);
          
          // Set correct input path
          const correctPath = getInputPathForSource(activeSource);
          setInputPath(correctPath);
          console.log("📁 Set inputPath:", correctPath);
          
          return activeSource;
        } else {
          console.log("⚠️ No active source found");
          return null;
        }
      } else {
        console.error("❌ Failed to load sources:", response.status);
        return null;
      }
    } catch (error) {
      console.error("❌ Error loading active source:", error);
      return null;
    }
  }, [setInputPath]);

  // ✅ NEW: Enhanced function to load selected cameras from processing_config
  const loadSelectedCameras = React.useCallback(async () => {
    try {
      setLoadingCameras(true);
      console.log("🔄 Loading selected cameras from processing_config...");
      
      const response = await fetch('http://localhost:8080/api/config/get-processing-cameras', {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        const data = await response.json();
        const cameras = data.selected_cameras || [];
        
        console.log("✅ Loaded processing cameras:", cameras);
        console.log("📊 Camera count:", data.count);
        
        // Update both camera lists
        setConfigFormCameras(cameras);
        setConfigFormSelectedCameras(cameras);
        
        // Also sync to hook state
        const cameraObjects = cameras.map(name => ({
          name: name,
          path: name
        }));
        setCameras(cameraObjects);
        setSelectedCameras(cameras);
        
        return cameras;
      } else {
        console.error("❌ Failed to load processing cameras:", response.status);
        return [];
      }
    } catch (error) {
      console.error("❌ Error loading processing cameras:", error);
      return [];
    } finally {
      setLoadingCameras(false);
    }
  }, [setCameras, setSelectedCameras]);

  // ✅ NEW: Check and handle cloud source specific loading
  const checkCloudSource = React.useCallback(async () => {
    try {
      console.log("🔍 Checking for cloud sources...");
      
      const response = await fetch('http://localhost:8080/api/config/get-sources', {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        const data = await response.json();
        const sources = data.sources || [];
        const cloudSource = sources.find(s => s.source_type === 'cloud');
        
        if (cloudSource) {
          console.log("☁️ Found cloud source:", cloudSource.name);
          console.log("📁 Cloud config:", cloudSource.config);
          
          // Check if cloud has selected_cameras in config
          const cloudCameras = cloudSource.config?.selected_cameras || [];
          if (cloudCameras.length > 0) {
            console.log("🎥 Cloud cameras found in source config:", cloudCameras);
            
            // Update camera states
            setConfigFormCameras(cloudCameras);
            setConfigFormSelectedCameras(cloudCameras);
            
            const cameraObjects = cloudCameras.map(name => ({
              name: name,
              path: name
            }));
            setCameras(cameraObjects);
            setSelectedCameras(cloudCameras);
            
            console.log("✅ Cloud cameras loaded successfully");
            return true;
          } else {
            console.log("⚠️ Cloud source found but no cameras in config");
          }
        } else {
          console.log("📝 No cloud source found");
        }
      }
      
      return false;
    } catch (error) {
      console.error("❌ Error checking cloud source:", error);
      return false;
    }
  }, [setCameras, setSelectedCameras]);

  // 🔄 UPDATED: Initialize với active source loading
  React.useEffect(() => {
    console.log("🚀 VtrackConfig mounted, initializing...");
    
    const initializeApp = async () => {
      // 1. Load active source trước
      const activeSource = await loadActiveSource();
      
      // 2. Load cameras
      const cameras = await loadSelectedCameras();
      
      // 3. Nếu không có cameras và có cloud source, thử cloud check
      if (cameras.length === 0 && activeSource?.source_type === 'cloud') {
        console.log("☁️ Cloud source detected, checking cloud cameras...");
        await checkCloudSource();
      }
    };
    
    initializeApp();
  }, [loadActiveSource, loadSelectedCameras, checkCloudSource]);

  // 🔄 UPDATED: Sync input path when activeVideoSource changes
  React.useEffect(() => {
    console.log("=== INPUT PATH SYNC DEBUG ===");
    console.log("activeVideoSource changed:", activeVideoSource);
    
    if (activeVideoSource) {
      const correctPath = getInputPathForSource(activeVideoSource);
      console.log(`${activeVideoSource.source_type.toUpperCase()} source detected - setting path:`, correctPath);
      setInputPath(correctPath);
      
      // For cloud sources, also load cameras
      if (activeVideoSource.source_type === 'cloud') {
        console.log("☁️ Cloud source detected, loading cameras...");
        checkCloudSource();
      }
    } else {
      console.log("activeVideoSource is null, will load from backend");
    }
  }, [activeVideoSource, setInputPath, checkCloudSource]);

  // ✅ Keep existing useEffect for syncing cameras
  React.useEffect(() => {
    if (configFormCameras && configFormCameras.length > 0) {
      const cameraObjects = configFormCameras.map(name => ({
        name: name,
        path: name
      }));
      setCameras(cameraObjects);
      console.log("🔄 Synced cameras to hook state:", cameraObjects);
    }
  }, [configFormCameras, setCameras]);

  React.useEffect(() => {
    if (configFormSelectedCameras && configFormSelectedCameras.length > 0) {
      setSelectedCameras(configFormSelectedCameras);
      console.log("🔄 Synced selectedCameras to hook state:", configFormSelectedCameras);
    }
  }, [configFormSelectedCameras, setSelectedCameras]);


const handleCamerasUpdate = React.useCallback((sourceCameras, selectedCameras, activeSource) => {
  console.log("=== CAMERAS UPDATE FROM CONFIGFORM ===");
  console.log("sourceCameras:", sourceCameras);
  console.log("selectedCameras:", selectedCameras);
  console.log("activeSource:", activeSource);
  
  // ✅ Update all camera states
  setConfigFormCameras(sourceCameras);
  setConfigFormSelectedCameras(selectedCameras);
  
  // ✅ Sync to hook state
  const cameraObjects = sourceCameras.map(name => ({
    name: name,
    path: name
  }));
  setCameras(cameraObjects);
  setSelectedCameras(selectedCameras);
  
  // ✅ CRITICAL: Handle source updates (including null for removal)
  if (activeSource !== undefined) { // Only update if explicitly passed
    console.log("🔄 Updating activeVideoSource:", activeSource);
    setActiveVideoSource(activeSource);
    
    if (activeSource) {
      // Set path for new source
      const correctPath = getInputPathForSource(activeSource);
      setInputPath(correctPath);
      console.log("📁 Updated inputPath:", correctPath);
    } else {
      // Clear path when source is removed
      setInputPath('');
      console.log("📁 Cleared inputPath due to source removal");
    }
  }
  
  console.log("✅ Camera state fully synced from ConfigForm");
}, [setCameras, setSelectedCameras, setInputPath, setActiveVideoSource]);

// ✅ THÊM: Force re-render khi activeVideoSource thay đổi
React.useEffect(() => {
  console.log("=== ACTIVE SOURCE CHANGED ===");
  console.log("New activeVideoSource:", activeVideoSource);
  
  if (!activeVideoSource) {
    console.log("🔄 Source cleared, resetting all related states");
    // Đảm bảo tất cả state được clear khi source bị xóa
    setConfigFormCameras([]);
    setConfigFormSelectedCameras([]);
    setCameras([]);
    setSelectedCameras([]);
    setInputPath('');
  }
}, [activeVideoSource, setCameras, setSelectedCameras, setInputPath]);

  // ✅ ENHANCED: Smart camera dialog logic - skip if cameras already selected
  const handleShowCameraDialogCustom = async () => {
    console.log("=== SMART CAMERA DIALOG LOGIC ===");
    console.log("configFormSelectedCameras:", configFormSelectedCameras);
    console.log("configFormCameras:", configFormCameras);
    
    // ✅ Try to refresh camera data first
    if (configFormCameras.length === 0) {
      console.log("🔄 No cameras detected, refreshing from server...");
      
      setLoadingCameras(true);
      const refreshedCameras = await loadSelectedCameras();
      
      if (refreshedCameras.length === 0) {
        // Also try cloud source check
        const cloudFound = await checkCloudSource();
        if (!cloudFound) {
          alert("❌ Không tìm thấy camera nào!\n\n" + 
                "Vui lòng kiểm tra:\n" +
                "1. Video source đã được cấu hình đúng\n" +
                "2. Cloud source đã sync cameras\n" +
                "3. Processing config đã có selected_cameras\n\n" +
                "Thử refresh lại trang nếu vẫn lỗi.");
          return;
        }
      }
      setLoadingCameras(false);
      
      // Give time for state updates
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    // ✅ Check if cameras are already selected after refresh
    const currentSelectedCameras = configFormSelectedCameras.length > 0 ? configFormSelectedCameras : selectedCameras;
    const currentCameras = configFormCameras.length > 0 ? configFormCameras : cameras.map(c => c.name);
    
    if (currentSelectedCameras && currentSelectedCameras.length > 0) {
      console.log("✅ Cameras already selected, skipping dialog and saving directly");
      console.log("Selected cameras:", currentSelectedCameras);
      
      // ✅ Sync cameras to dialog state for save process
      const cameraObjects = currentCameras.map(name => ({
        name: name,
        path: name
      }));
      setCameras(cameraObjects);
      setSelectedCameras(currentSelectedCameras);
      
      // ✅ Save directly without showing dialog
      handleSaveConfigCustom();
      return;
    }
    
    // ✅ No cameras selected, show dialog for user to select
    console.log("⚠️ No cameras selected, showing dialog for user selection");
    
    if (!currentCameras || currentCameras.length === 0) {
      alert("❌ Không tìm thấy camera nào để chọn!\n\n" + 
            "Debug info:\n" +
            `- configFormCameras: ${configFormCameras.length}\n` +
            `- cameras from hook: ${cameras.length}\n\n` +
            "Vui lòng:\n" +
            "1. Kiểm tra video source đã được cấu hình\n" +
            "2. Đảm bảo có camera folders trong source\n" +
            "3. Refresh trang và thử lại");
      return;
    }
    
    const cameraObjects = currentCameras.map(name => ({
      name: name,
      path: name
    }));
    setCameras(cameraObjects);
    setSelectedCameras([]); // Start with empty selection for user to choose
    setShowCameraDialog(true);
  };

  // ✅ SIMPLE: Back to basic validation (like before)
  const handleSaveConfigCustom = () => {
    console.log("=== SIMPLE SAVE CONFIG ===");
    console.log("configFormSelectedCameras:", configFormSelectedCameras);
    console.log("selectedCameras from dialog:", selectedCameras);
    console.log("inputPath:", inputPath);
    
    // ✅ SIMPLE: Get cameras (multiple fallbacks)
    let camerasToUse = [];
    
    if (selectedCameras && selectedCameras.length > 0) {
      camerasToUse = selectedCameras;
      console.log("📋 Using cameras from dialog selection");
    } else if (configFormSelectedCameras && configFormSelectedCameras.length > 0) {
      camerasToUse = configFormSelectedCameras;
      console.log("📋 Using cameras from config form");
    } else if (cameras && cameras.length > 0) {
      camerasToUse = cameras.map(c => c.name || c);
      console.log("📋 Using cameras from hook state");
    }
      
    console.log("Final cameras to use:", camerasToUse);
    
    // ✅ SIMPLE: Only check cameras (like before)
    if (!camerasToUse || camerasToUse.length === 0) {
      alert("❌ Vui lòng chọn ít nhất một camera!");
      return;
    }

    // ✅ SIMPLE: Auto-set path if empty and have activeVideoSource
    if (activeVideoSource && (!inputPath || inputPath.trim() === "")) {
      const correctPath = getInputPathForSource(activeVideoSource);
      console.log(`🔄 Auto-setting path: ${correctPath}`);
      setInputPath(correctPath);
    }

    console.log("💾 Saving with simple validation...");
    console.log("- Cameras:", camerasToUse.length);
    console.log("- Input Path:", inputPath || "Will be set by handleSaveConfig");

    setShowCameraDialog(false);
    console.log("💾 Calling original handleSaveConfig...");
    handleSaveConfig();
  };

  // ✅ NEW: Debug function to check camera sync status
  const handleDebugCameras = async () => {
    try {
      console.log("🔧 Debug: Checking camera sync status...");
      
      const response = await fetch('http://localhost:8080/api/config/debug-cameras', {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log("🔧 Debug camera data:", data);
        
        alert(`🔧 Camera Debug Info:\n\n` +
              `Processing Config:\n` +
              `- Selected cameras: ${data.processing_config?.camera_count || 0}\n` +
              `- Input path: ${data.processing_config?.input_path || 'N/A'}\n\n` +
              `Active Sources: ${data.active_sources?.length || 0}\n\n` +
              `Check console for full details.`);
      }
    } catch (error) {
      console.error("❌ Debug error:", error);
    }
  };

  // 🆕 NEW: Quick debug and auto-fix function
  const debugAndFix = async () => {
    try {
      console.log("🔧 DEBUG: Checking current state...");
      
      // 1. Check sources
      const sourcesResponse = await fetch('http://localhost:8080/api/config/get-sources');
      const sourcesData = await sourcesResponse.json();
      console.log("📊 Sources:", sourcesData);
      
      // 2. Check cameras
      const camerasResponse = await fetch('http://localhost:8080/api/config/get-processing-cameras');
      const camerasData = await camerasResponse.json();
      console.log("🎥 Cameras:", camerasData);
      
      // 3. Auto-fix if possible
      if (sourcesData.sources && sourcesData.sources.length > 0) {
        const activeSource = sourcesData.sources[0];
        setActiveVideoSource(activeSource);
        
        const correctPath = getInputPathForSource(activeSource);
        setInputPath(correctPath);
        
        console.log("✅ AUTO-FIXED:");
        console.log("- Source:", activeSource.name);
        console.log("- Path:", correctPath);
        
        alert("🔧 Debug complete! Source và path đã được tự động sửa.");
      } else {
        alert("❌ Không tìm thấy source nào. Vui lòng cấu hình video source trước.");
      }
      
    } catch (error) {
      console.error("❌ Debug failed:", error);
      alert("Debug thất bại. Check console để xem chi tiết.");
    }
  };

  const countries = [
    "Việt Nam", "Nhật Bản", "Hàn Quốc", "Thái Lan", "Singapore",
    "Mỹ", "Anh", "Pháp", "Đức", "Úc"
  ];

  return (
    <div className="p-6 flex gap-6 w-[100%]">
      <GeneralInfoForm
        country={country}
        setCountry={setCountry}
        timezone={timezone}
        setTimezone={setTimezone}
        brandName={brandName}
        setBrandName={setBrandName}
        workingDays={workingDays}
        setWorkingDays={setWorkingDays}
        fromTime={fromTime}
        setFromTime={setFromTime}
        toTime={toTime}
        setToTime={setToTime}
        handleCountryChange={handleCountryChange}
        handleFromTimeChange={handleFromTimeChange}
        handleToTimeChange={handleToTimeChange}
        handleWorkingDayChange={handleWorkingDayChange}
        handleSaveGeneralInfo={handleSaveGeneralInfo}
        countries={countries}
      />
      <ConfigForm
        inputPath={inputPath}
        setInputPath={setInputPath}
        outputPath={outputPath}
        setOutputPath={setOutputPath}
        defaultDays={defaultDays}
        setDefaultDays={setDefaultDays}
        minPackingTime={minPackingTime}
        setMinPackingTime={setMinPackingTime}
        maxPackingTime={maxPackingTime}
        setMaxPackingTime={setMaxPackingTime}
        frameRate={frameRate}
        setFrameRate={setFrameRate}
        frameInterval={frameInterval}
        setFrameInterval={setFrameInterval}
        videoBuffer={videoBuffer}
        setVideoBuffer={setVideoBuffer}
        error={error}
        handleOpenExplorer={handleOpenExplorer}
        handleShowCameraDialog={handleShowCameraDialogCustom}
        runDefaultOnStart={runDefaultOnStart}
        setRunDefaultOnStart={setRunDefaultOnStart}
        // 🆕 NEW: Pass camera data from VtrackConfig to ConfigForm
        camerasFromParent={configFormCameras}
        selectedCamerasFromParent={configFormSelectedCameras}
        activeSourceFromParent={activeVideoSource}
        isLoadingCameras={loadingCameras}
        // ✅ NEW: Add callback to receive camera updates from ConfigForm
        onCamerasUpdated={handleCamerasUpdate}
      />
      <ProcessingRegionForm
        videoPath={videoPath}
        setVideoPath={setVideoPath}
        qrSize={qrSize}
        setQrSize={setQrSize}
        handleAnalyzeRegions={handleAnalyzeRegions}
      />
      <CameraDialog
        showCameraDialog={showCameraDialog}
        setShowCameraDialog={setShowCameraDialog}
        cameras={cameras}
        selectedCameras={selectedCameras}
        handleCameraSelection={handleCameraSelection}
        handleSaveConfig={handleSaveConfigCustom}
      />
      
      {/* ✅ NEW: Debug Panel (Development Only) */}
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed bottom-4 right-4 bg-gray-800 border border-gray-600 rounded-lg p-4 text-xs">
          <div className="text-white font-medium mb-2">🔧 Camera Debug</div>
          <div className="text-gray-300 space-y-1">
            <div>Form Cameras: {configFormCameras.length}</div>
            <div>Selected: {configFormSelectedCameras.length}</div>
            <div>Hook Cameras: {cameras.length}</div>
            <div>Loading: {loadingCameras ? 'Yes' : 'No'}</div>
            <div>Active Source: {activeVideoSource?.name || 'None'}</div>
            <div>Input Path: {inputPath ? 'Set' : 'Empty'}</div>
          </div>
          <div className="flex gap-1 mt-2">
            <button
              onClick={handleDebugCameras}
              className="px-2 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700"
            >
              Debug Server
            </button>
            <button
              onClick={debugAndFix}
              className="px-2 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700"
            >
              Auto Fix
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default VtrackConfig;