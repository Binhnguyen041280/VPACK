import { useState, useEffect } from "react";
import timezoneManager from "../utils/TimezoneManager";
import TimezoneAwareFetch from "../utils/TimezoneAwareFetch";
import useGlobalTimezone from "./useGlobalTimezone";
import countriesAndTimezones from "../utils/CountriesAndTimezones";

const useVtrackConfig = (options = {}) => {
  const { shouldFetchCameras = true, activeVideoSource = null } = options;
  const [fromTime, setFromTime] = useState(null);
  const [toTime, setToTime] = useState(null);
  const [country, setCountry] = useState("Vietnam");
  
  // Use global timezone configuration instead of hardcoded values
  const { timezoneOffset, getTimezoneOffset, getTimezoneIana, loading: timezoneLoading } = useGlobalTimezone();
  const [timezone, setTimezone] = useState(() => {
    // Initialize with global timezone or fallback
    return timezoneOffset || "UTC+7"; // Fallback for backward compatibility
  });
  
  // Update timezone when global timezone changes
  useEffect(() => {
    if (!timezoneLoading && timezoneOffset) {
      setTimezone(timezoneOffset);
    }
  }, [timezoneOffset, timezoneLoading]);
  const [brandName, setBrandName] = useState("");
  const [inputPath, setInputPath] = useState("");
  const [outputPath, setOutputPath] = useState("");
  const [workingDays, setWorkingDays] = useState([]);
  const [defaultDays, setDefaultDays] = useState(30);
  const [minPackingTime, setMinPackingTime] = useState(10);
  const [maxPackingTime, setMaxPackingTime] = useState(120);
  const [frameRate, setFrameRate] = useState(30);
  const [frameInterval, setFrameInterval] = useState(5);
  const [videoBuffer, setVideoBuffer] = useState(2);
  const [cameras, setCameras] = useState([]);
  const [selectedCameras, setSelectedCameras] = useState([]);
  const [showCameraDialog, setShowCameraDialog] = useState(false);
  const [error, setError] = useState(null);
  const [runDefaultOnStart, setRunDefaultOnStart] = useState(false);

  // Get all countries from the comprehensive countries library
  const countries = countriesAndTimezones.getAllCountryNames(true); // true = prioritize common countries

  // Get timezone offset for a country using the comprehensive library
  const getCountryTimezoneOffset = (countryName) => {
    return countriesAndTimezones.getTimezoneOffset(countryName);
  };

  // Get primary timezone IANA name for a country
  const getCountryTimezone = (countryName) => {
    return countriesAndTimezones.getTimezone(countryName);
  };

  const BASE_DIR = "/Users/annhu/vtrack_app/V_Track";

  useEffect(() => {
    const fetchCameraFolders = async () => {
      // ✅ FIXED: Only fetch camera folders if explicitly requested and there's an active video source
      if (!shouldFetchCameras) {
        console.log("⏹️ Camera fetching disabled by parent component");
        setCameras([]);
        setError(null);
        return;
      }

      if (!activeVideoSource) {
        console.log("⏹️ No active video source - skipping camera folders API call");
        setCameras([]);
        setError(null); // Clear any previous errors
        return;
      }

      try {
        console.log("📡 Fetching camera folders for active source:", activeVideoSource.name);
        // ✅ SIMPLIFIED - single source of truth with timezone-aware fetch
        const response = await TimezoneAwareFetch.get("http://localhost:8080/get-camera-folders");
        if (response.ok) {
          const data = await TimezoneAwareFetch.parseJsonResponse(response);
          if (Array.isArray(data.folders)) {
            setCameras(data.folders);
            setError(null);
          } else {
            setCameras([]);
            setError(data.error || "Failed to load camera folders");
          }
        } else {
          setCameras([]);
          setError("Camera folders not available");
        }
      } catch (error) {
        console.error("Error fetching camera folders:", error);
        setError("Error fetching camera folders: " + error.message);
        setCameras([]);
      }
    };
    fetchCameraFolders();
  }, [shouldFetchCameras, activeVideoSource]); // ✅ FIXED: Depend on both flags

  const handleCountryChange = (e) => {
    const selectedCountry = e.target.value;
    setCountry(selectedCountry);
    
    // Get timezone information for the selected country
    const selectedTimezoneOffset = getCountryTimezoneOffset(selectedCountry);
    const selectedTimezoneIana = getCountryTimezone(selectedCountry);
    
    setTimezone(selectedTimezoneOffset);
    
    // Update TimezoneManager preference based on selected country
    if (selectedTimezoneIana) {
      try {
        // Use the IANA timezone from the country mapper
        timezoneManager.saveUserPreference(selectedTimezoneIana);
        console.log(`Updated timezone to ${selectedTimezoneIana} for country ${selectedCountry}`);
      } catch (error) {
        console.error('Error updating timezone:', error);
        // Fallback to global timezone if country-specific timezone fails
        const fallbackTimezone = getTimezoneIana() || 'Asia/Ho_Chi_Minh';
        timezoneManager.saveUserPreference(fallbackTimezone);
      }
    }
  };

  const handleFromTimeChange = (time) => {
    setFromTime(time);
    if (toTime && time > toTime) setToTime(time);
  };

  const handleToTimeChange = (time) => {
    if (fromTime && time < fromTime) setFromTime(time);
    setToTime(time);
  };

  const handleWorkingDayChange = (day) => {
    setWorkingDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]
    );
  };

  useEffect(() => {
    console.log("workingDays updated:", workingDays);
  }, [workingDays]);

  const handleOpenExplorer = (type) => {
    const input = document.createElement("input");
    input.type = "file";
    input.webkitdirectory = true;
    input.onchange = (e) => {
      const files = e.target.files;
      if (files.length > 0) {
        const file = files[0];
        let selectedPath = file.path || file.webkitRelativePath || file.name || "";
        if (!selectedPath.startsWith('/')) {
          selectedPath = `${BASE_DIR}/${selectedPath}`;
        }
        selectedPath = selectedPath.split('/').slice(0, -1).join('/');
        if (selectedPath.includes('.DS_Store')) {
          selectedPath = selectedPath.replace('/.DS_Store', '');
        }
        console.log(`Selected ${type} path:`, selectedPath);
        if (type === "input") setInputPath(selectedPath);
        else setOutputPath(selectedPath);
      }
    };
    input.click();
  };

  const handleSaveGeneralInfo = async () => {
    const data = {
      country,
      timezone,
      brand_name: brandName,
      working_days: workingDays.length > 0 ? workingDays : ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"],
      from_time: fromTime ? fromTime : "07:00", // Let middleware handle timezone conversion
      to_time: toTime ? toTime : "23:00", // Let middleware handle timezone conversion
    };
    console.log("Data sent to /api/config/save-general-info:", data);
    try {
      const response = await TimezoneAwareFetch.post("http://localhost:8080/save-general-info", data);
      if (response.ok) {
        alert("General info saved successfully");
      } else {
        throw new Error("Failed to save general info");
      }
    } catch (error) {
      console.error("Error saving general info:", error);
      alert(`Failed to save general info: ${error.message}`);
    }
  };

  const handleSaveConfig = async () => {
    let normalizedInputPath = inputPath.trim();
    if (!normalizedInputPath) {
      alert("Input path cannot be empty");
      return;
    }
    if (!normalizedInputPath.startsWith('/')) {
      normalizedInputPath = `${BASE_DIR}/${normalizedInputPath}`;
    }
    if (normalizedInputPath.includes('.DS_Store')) {
      normalizedInputPath = normalizedInputPath.replace('/.DS_Store', '');
    }

    let normalizedOutputPath = outputPath.trim();
    if (!normalizedOutputPath) {
      normalizedOutputPath = `${BASE_DIR}/output_clips`;
    }
    if (!normalizedOutputPath.startsWith('/')) {
      normalizedOutputPath = `${BASE_DIR}/${normalizedOutputPath}`;
    }
    if (normalizedOutputPath.includes('.DS_Store')) {
      normalizedOutputPath = normalizedOutputPath.replace('/.DS_Store', '');
    }

    const data = {
      video_root: normalizedInputPath,
      output_path: normalizedOutputPath,
      db_path: "/Users/annhu/Downloads/V_Track project/events.db",
      default_days: defaultDays,
      min_packing_time: minPackingTime,
      max_packing_time: maxPackingTime,
      frame_rate: frameRate,
      frame_interval: frameInterval,
      video_buffer: videoBuffer,
      selected_cameras: selectedCameras,
    };
    console.log("Data sent to /save-config:", data);
    try {
      const response = await TimezoneAwareFetch.post("http://localhost:8080/api/config/save-config", data);
      const result = await TimezoneAwareFetch.parseJsonResponse(response);
      if (response.ok) {
        localStorage.setItem("configSet", "true");
        alert("Configuration saved successfully");
        setShowCameraDialog(false);
        const cameraResponse = await TimezoneAwareFetch.get("http://localhost:8080/get-cameras");
        const cameraData = await TimezoneAwareFetch.parseJsonResponse(cameraResponse);
        if (cameraData && Array.isArray(cameraData.cameras)) {
          setCameras(cameraData.cameras.map(name => ({ name, path: "" })));
          setError(null);
        } else {
          setCameras([]);
          setError(cameraData?.error || "Failed to load cameras");
        }
      } else {
        throw new Error(result.error || "Failed to save config");
      }
    } catch (error) {
      console.error("Error saving config:", error);
      alert("Failed to save config: " + error.message);
    }
  };

  const handleShowCameraDialog = () => {
    setShowCameraDialog(true);
  };

  const handleCameraSelection = (cameraName) => {
    setSelectedCameras((prev) =>
      prev.includes(cameraName) ? prev.filter((c) => c !== cameraName) : [...prev, cameraName]
    );
  };

  return {
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
    // Timezone utilities
    timezoneManager,
  };
};

export default useVtrackConfig;