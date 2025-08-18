import React from "react";
import useVtrackConfig from "./hooks/useVtrackConfig";
import GeneralInfoForm from "./components/config/GeneralInfoForm";
import ConfigForm from "./components/config/ConfigForm";
import CameraDialog from "./components/config/CameraDialog";
import ProcessingRegionForm from "./components/config/ProcessingRegionForm";
import ct from 'countries-and-timezones';
import timezoneManager from "./utils/TimezoneManager";

const VtrackConfig = ({ authState }) => {
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
  } = useVtrackConfig({ shouldFetchCameras: false });

  const [configFormCameras, setConfigFormCameras] = React.useState([]);
  const [configFormSelectedCameras, setConfigFormSelectedCameras] = React.useState([]);
  const [activeVideoSource, setActiveVideoSource] = React.useState(null);
  const [loadingCameras, setLoadingCameras] = React.useState(false);

  const [videoPath, setVideoPath] = React.useState("");
  const [qrSize, setQrSize] = React.useState("");
  
  const handleAnalyzeRegions = () => {
    console.log("Phân tích vùng:", videoPath, qrSize);
  };

  // Get all countries from library
  const countries = Object.values(ct.getAllCountries())
    .map(country => country.name)
    .sort();

  // Auto-detection system info
  const systemInfo = timezoneManager.getSystemDetection();

  // Auto-set defaults from system detection
  React.useEffect(() => {
    if (!country && systemInfo.country && countries.includes(systemInfo.country)) {
      console.log(`Auto-detected country: ${systemInfo.country}`);
      setCountry(systemInfo.country);
    }
  }, [countries, country, setCountry, systemInfo.country]);

  const getInputPathForSource = (source) => {
    if (!source) return "";
    
    let resultPath = "";
    
    switch (source.source_type) {
      case 'local':
        resultPath = source.path;
        console.log(`📁 Local Path Mapping: ${source.path} → ${resultPath}`);
        break;
      case 'cloud':
        resultPath = `/Users/annhu/vtrack_app/V_Track/cloud_sync/${source.name}`;
        console.log(`☁️ Cloud Path Mapping: ${source.path} → ${resultPath}`);
        break;
      default:
        resultPath = source.path;
        console.log(`❓ Unknown Path Mapping: ${source.path} → ${resultPath}`);
    }
    
    return resultPath;
  };

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
        const activeSource = sources.find(s => s.active) || sources[0];
        
        if (activeSource) {
          console.log("✅ Found active source:", activeSource.name, activeSource.source_type);
          setActiveVideoSource(activeSource);
          
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
        
        setConfigFormCameras(cameras);
        setConfigFormSelectedCameras(cameras);
        
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
          
          const cloudCameras = cloudSource.config?.selected_cameras || [];
          if (cloudCameras.length > 0) {
            console.log("🎥 Cloud cameras found in source config:", cloudCameras);
            
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
            console.log("📝 Cloud source found - checking processing_config for cameras");
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

  React.useEffect(() => {
    console.log("🚀 VtrackConfig mounted, initializing...");
    
    const initializeApp = async () => {
      const activeSource = await loadActiveSource();
      const cameras = await loadSelectedCameras();
      
      if (cameras.length === 0 && activeSource?.source_type === 'cloud') {
        console.log("☁️ Cloud source detected, checking cloud cameras...");
        await checkCloudSource();
      }
    };
    
    initializeApp();
  }, [loadActiveSource, loadSelectedCameras, checkCloudSource]);

  React.useEffect(() => {
    console.log("=== INPUT PATH SYNC DEBUG ===");
    console.log("activeVideoSource changed:", activeVideoSource);
    
    if (activeVideoSource) {
      const correctPath = getInputPathForSource(activeVideoSource);
      console.log(`${activeVideoSource.source_type.toUpperCase()} source detected - setting path:`, correctPath);
      setInputPath(correctPath);
      
      if (activeVideoSource.source_type === 'cloud') {
        console.log("☁️ Cloud source detected, loading cameras...");
        checkCloudSource();
      }
    } else {
      console.log("activeVideoSource is null, will load from backend");
    }
  }, [activeVideoSource, setInputPath, checkCloudSource]);

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
    
    setConfigFormCameras(sourceCameras);
    setConfigFormSelectedCameras(selectedCameras);
    
    const cameraObjects = sourceCameras.map(name => ({
      name: name,
      path: name
    }));
    setCameras(cameraObjects);
    setSelectedCameras(selectedCameras);
    
    if (activeSource !== undefined) {
      console.log("🔄 Updating activeVideoSource:", activeSource);
      setActiveVideoSource(activeSource);
      
      if (activeSource) {
        const correctPath = getInputPathForSource(activeSource);
        setInputPath(correctPath);
        console.log("📁 Updated inputPath:", correctPath);
      } else {
        setInputPath('');
        console.log("📁 Cleared inputPath due to source removal");
      }
    }
    
    console.log("✅ Camera state fully synced from ConfigForm");
  }, [setCameras, setSelectedCameras, setInputPath, setActiveVideoSource]);

  React.useEffect(() => {
    console.log("=== ACTIVE SOURCE CHANGED ===");
    console.log("New activeVideoSource:", activeVideoSource);
    
    if (!activeVideoSource) {
      console.log("🔄 Source cleared, resetting all related states");
      setConfigFormCameras([]);
      setConfigFormSelectedCameras([]);
      setCameras([]);
      setSelectedCameras([]);
      setInputPath('');
    }
  }, [activeVideoSource, setCameras, setSelectedCameras, setInputPath]);

  const handleShowCameraDialogCustom = async () => {
    console.log("=== SMART CAMERA DIALOG LOGIC ===");
    console.log("configFormSelectedCameras:", configFormSelectedCameras);
    console.log("configFormCameras:", configFormCameras);
    
    if (configFormCameras.length === 0) {
      console.log("🔄 No cameras detected, refreshing from server...");
      
      setLoadingCameras(true);
      const refreshedCameras = await loadSelectedCameras();
      
      if (refreshedCameras.length === 0) {
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
      
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    const currentSelectedCameras = configFormSelectedCameras.length > 0 ? configFormSelectedCameras : selectedCameras;
    const currentCameras = configFormCameras.length > 0 ? configFormCameras : cameras.map(c => c.name);
    
    if (currentSelectedCameras && currentSelectedCameras.length > 0) {
      console.log("✅ Cameras already selected, skipping dialog and saving directly");
      console.log("Selected cameras:", currentSelectedCameras);
      
      const cameraObjects = currentCameras.map(name => ({
        name: name,
        path: name
      }));
      setCameras(cameraObjects);
      setSelectedCameras(currentSelectedCameras);
      
      handleSaveConfigCustom();
      return;
    }
    
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
    setSelectedCameras([]);
    setShowCameraDialog(true);
  };

  const handleSaveConfigCustom = () => {
    console.log("=== SIMPLE SAVE CONFIG ===");
    console.log("configFormSelectedCameras:", configFormSelectedCameras);
    console.log("selectedCameras from dialog:", selectedCameras);
    console.log("inputPath:", inputPath);
    
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
    
    if (!camerasToUse || camerasToUse.length === 0) {
      alert("❌ Vui lòng chọn ít nhất một camera!");
      return;
    }

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
        camerasFromParent={configFormCameras}
        selectedCamerasFromParent={configFormSelectedCameras}
        activeSourceFromParent={activeVideoSource}
        isLoadingCameras={loadingCameras}
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
    </div>
  );
};

export default VtrackConfig;