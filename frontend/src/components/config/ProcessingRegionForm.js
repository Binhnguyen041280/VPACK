import { useState, useEffect } from "react";
import api from "../../api";
import InstructionsPanel from "./InstructionsPanel";

const ProcessingRegionForm = ({ handleAnalyzeRegions }) => {
  const [videoPath, setVideoPath] = useState("");
  const [selectedVideoPath, setSelectedVideoPath] = useState("");
  const [error, setError] = useState("");
  const [analysisResult, setAnalysisResult] = useState(null);
  const [roiFramePath, setRoiFramePath] = useState("");
  const [showResultModal, setShowResultModal] = useState(false);
  const [cameraList, setCameraList] = useState([]);
  const [selectedCamera, setSelectedCamera] = useState("");
  const [processedCameras, setProcessedCameras] = useState([]);

  useEffect(() => {
    handleGetCameras();
  }, []);

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      const path = file.path || file.name;
      setVideoPath(path);
      setSelectedVideoPath(path);
      setError("");
    } else {
      setVideoPath("");
      setSelectedVideoPath("");
    }
  };

  const handleGetCameras = async () => {
    try {
      const response = await api.get("/get-cameras");
      setCameraList(response.data.cameras || []);
      setError("");
    } catch (err) {
      setError("Không thể lấy danh sách camera.");
    }
  };

  const handleSelectCamera = (camera) => {
    setSelectedCamera(camera);
    setVideoPath("");
    setSelectedVideoPath("");
    setError("");
  };

  const handleContinue = async () => {
    if (!videoPath && !selectedVideoPath) {
      setError("Vui lòng chọn video baseline.");
      return;
    }
    if (!selectedCamera) {
      setError("Vui lòng chọn một camera.");
      return;
    }
    try {
      const response = await fetch('http://127.0.0.1:8080/api/hand_detection/select-roi', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ videoPath: selectedVideoPath || videoPath, cameraId: selectedCamera })
      });
      const result = await response.json();
      console.log("Result from run-select-roi:", result);
      if (result.success) {
        const newAnalysisResult = {
          success: true,
          message: result.message || "Hand detection completed successfully",
          roi: result.roi,
          hand_detected: result.hand_detected,
          roi_frame: result.roi_frame
        };
        console.log("Setting analysisResult in handleContinue:", newAnalysisResult);
        setAnalysisResult(newAnalysisResult);
        setRoiFramePath(result.roi_frame); // Lưu roiFramePath
        setShowResultModal(true);
      } else {
        setError(result.error || "Không thể chạy hand detection.");
      }
    } catch (err) {
      setError("Lỗi khi chạy hand detection: " + err.message);
    }
  };

  const handleRetry = async () => {
    if (!selectedVideoPath && !videoPath) {
      setError("Vui lòng chọn video baseline.");
      return;
    }
    try {
      const response = await fetch('http://127.0.0.1:8080/api/hand_detection/select-roi', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ videoPath: selectedVideoPath || videoPath, cameraId: selectedCamera })
      });
      const result = await response.json();
      console.log("Result from run-select-roi (retry):", result);
      if (result.success) {
        const newAnalysisResult = {
          success: true,
          message: result.message || "Hand detection completed successfully",
          roi: result.roi,
          hand_detected: result.hand_detected,
          roi_frame: result.roi_frame
        };
        console.log("Setting analysisResult in handleRetry:", newAnalysisResult);
        setAnalysisResult(newAnalysisResult);
        setRoiFramePath(result.roi_frame); // Cập nhật roiFramePath với file mới nhất
        setShowResultModal(true);
      } else {
        setError(result.error || "Không thể chạy hand detection.");
      }
    } catch (err) {
      setError("Lỗi khi chạy hand detection: " + err.message);
    }
  };

  const handleRoisSubmit = (rois) => {
    setProcessedCameras((prev) => [...new Set([...prev, selectedCamera])]);
    setSelectedCamera("");
  };

  const handleContinueWithAnotherCamera = () => {
    setAnalysisResult(null);
    setRoiFramePath("");
    setShowResultModal(false);
    setSelectedCamera("");
    setVideoPath("");
    setSelectedVideoPath("");
    setError("");
  };

  const handleExit = () => {
    setShowResultModal(false);
    handleAnalyzeRegions({
      success: true,
      message: "Đã hoàn tất xử lý các camera.",
      processedCameras,
    });
  };

  return (
    <div className="w-[25%] bg-gray-800 p-6 rounded-lg flex flex-col">
      <h1 className="text-3xl font-bold mb-4">Vùng xử lý</h1>
      <p className="text-gray-300 mb-4">
        Tải lên video baseline (5s-5 phút) để xác định các vùng xử lý QR và đóng gói.
      </p>
      <div className="mb-4">
        <button
          onClick={handleGetCameras}
          className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded"
        >
          Lấy danh sách camera
        </button>
      </div>
      {cameraList && cameraList.length > 0 && (
        <div className="mb-4">
          <h3 className="text-lg font-bold mb-2">Chọn camera:</h3>
          <div className="max-h-24 overflow-y-auto">
            {cameraList.map((camera) => (
              <label key={camera} className="flex items-center mb-2">
                <input
                  type="radio"
                  name="camera"
                  className="mr-2"
                  checked={selectedCamera === camera}
                  onChange={() => handleSelectCamera(camera)}
                  disabled={processedCameras.includes(camera)}
                />
                {camera}
                {processedCameras.includes(camera) && (
                  <span className="ml-2 text-green-500">✔ Đã xử lý</span>
                )}
              </label>
            ))}
          </div>
        </div>
      )}
      <div className="mb-4">
        <label className="block mb-1">Video baseline:</label>
        <div className="relative w-full">
          <input
            type="text"
            value={videoPath}
            onChange={(e) => {
              setVideoPath(e.target.value);
              setSelectedVideoPath(e.target.value);
            }}
            placeholder="Chọn video (e.g., /Users/annhu/vtrack_app/V_Track/baseline.mp4)"
            className="w-full p-2 rounded bg-gray-700 text-white"
          />
          <button
            type="button"
            onClick={() => {
              const input = document.createElement("input");
              input.type = "file";
              input.accept = "video/*";
              input.onchange = handleFileSelect;
              input.click();
            }}
            className="absolute right-2 top-1/2 transform -translate-y-1/2 text-white"
          >
            ...
          </button>
        </div>
      </div>
      {videoPath && selectedCamera && (
        <div className="mb-4 flex justify-center">
          <button
            onClick={handleContinue}
            className="py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded"
          >
            Tiếp tục
          </button>
        </div>
      )}
      {showResultModal && analysisResult && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded-lg w-3/4 h-3/4 flex">
            <InstructionsPanel
              customInstruction={
                analysisResult.qr_detected
                  ? "Tiếp tục xác định vùng trigger."
                  : "Vẽ lại vùng mã vận đơn hoặc nhấn Tiếp tục để đồng ý với vùng hiện tại."
              }
              analysisResult={analysisResult}
              handDetected={analysisResult.hand_detected}
              qrDetected={analysisResult.qr_detected}
              onClose={handleExit}
              onSave={handleContinueWithAnotherCamera}
              onRetry={handleRetry}
              errorMessage={error}
              videoPath={selectedVideoPath || videoPath}
              cameraId={selectedCamera}
              onSubmit={handleRoisSubmit}
              setAnalysisResult={setAnalysisResult}
              roiFramePath={roiFramePath}
            />
          </div>
        </div>
      )}
      {error && (
        <div className="mb-4 text-red-500 text-sm">{error}</div>
      )}
    </div>
  );
};

export default ProcessingRegionForm;
