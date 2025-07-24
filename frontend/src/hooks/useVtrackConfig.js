import { useState, useEffect } from "react";

const useVtrackConfig = () => {
  const [fromTime, setFromTime] = useState(null);
  const [toTime, setToTime] = useState(null);
  const [country, setCountry] = useState("Việt Nam");
  const [timezone, setTimezone] = useState("UTC+7");
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

  const countries = [
    "Việt Nam", "Nhật Bản", "Hàn Quốc", "Thái Lan", "Singapore",
    "Mỹ", "Anh", "Pháp", "Đức", "Úc"
  ];

  const countryTimezones = {
    "Việt Nam": "UTC+7", "Nhật Bản": "UTC+9", "Hàn Quốc": "UTC+9",
    "Thái Lan": "UTC+7", "Singapore": "UTC+8", "Mỹ": "UTC-5",
    "Anh": "UTC+0", "Pháp": "UTC+1", "Đức": "UTC+1", "Úc": "UTC+10"
  };

  const BASE_DIR = "/Users/annhu/vtrack_app/V_Track";

  useEffect(() => {
    const fetchCameraFolders = async () => {
      try {
        // ✅ SIMPLIFIED - single source of truth
        const response = await fetch("http://localhost:8080/get-camera-folders");
        if (response.ok) {
          const data = await response.json();
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
  }, []);

  const handleCountryChange = (e) => {
    const selectedCountry = e.target.value;
    setCountry(selectedCountry);
    setTimezone(countryTimezones[selectedCountry] || "UTC+0");
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
      from_time: fromTime ? fromTime.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', hour12: false }) : "07:00",
      to_time: toTime ? toTime.toLocaleTimeString('en-GB', { hour: "2-digit", minute: "2-digit", hour12: false }) : "23:00",
    };
    console.log("Data sent to /api/config/save-general-info:", data);
    try {
      const response = await fetch("http://localhost:8080/save-general-info", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (response.ok) alert("General info saved successfully");
      else throw new Error("Failed to save general info");
    } catch (error) {
      console.error("Error saving general info:", error);
      alert("Failed to save general info");
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
      const response = await fetch("http://localhost:8080/api/config/save-config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const result = await response.json();
      if (response.ok) {
        localStorage.setItem("configSet", "true");
        alert("Configuration saved successfully");
        setShowCameraDialog(false);
        const cameraResponse = await fetch("http://localhost:8080/get-cameras");
        const cameraData = await cameraResponse.json();
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
  };
};

export default useVtrackConfig;