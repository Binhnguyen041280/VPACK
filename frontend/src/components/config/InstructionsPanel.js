import React, { useState, useEffect } from 'react';
import { getFinalRoiFrame } from "../../api";

const InstructionsPanel = ({
  step,
  customInstruction,
  analysisResult,
  errorMessage,
  onSave,
  onClose,
  onRetry,
  handDetected,
  videoPath,
  cameraId,
  onSubmit,
  setAnalysisResult,
  roiFramePath,
}) => {
  const [roiFrameSrc, setRoiFrameSrc] = useState(null);
  const [finalRoiFrameSrc, setFinalRoiFrameSrc] = useState(null);
  const [rois, setRois] = useState([]);
  const [internalError, setInternalError] = useState("");
  const [currentStep, setCurrentStep] = useState("packing");
  const [roiImageState, setRoiImageState] = useState({
    step: "packing",
    file: "roi_packing.jpg",
    ready: false,
  });
  const [imageAspectRatio, setImageAspectRatio] = useState(null);

  const loadRoiImage = async (fileSuffix, retryCount = 0, maxRetries = 3) => {
    try {
      if (!cameraId) {
        console.error("Missing cameraId", { cameraId });
        setInternalError("Thiếu cameraId.");
        return;
      }

      console.log(`Loading ROI image with camera_id: ${cameraId}, file: ${fileSuffix}`);
      const timestamp = new Date().getTime();
      const url = `http://localhost:8080/get-roi-frame?camera_id=${cameraId}&file=${fileSuffix}&t=${timestamp}`;
      const response = await fetch(url, {
        headers: { 'Cache-Control': 'no-cache' },
      });
      if (!response.ok && response.status !== 304) {
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
      }
      console.log("Response from /get-roi-frame:", response);
      setRoiFrameSrc(url);
      setRoiImageState({ step: currentStep, file: fileSuffix, ready: true });
      console.log("roiFrameSrc updated to:", url);
    } catch (error) {
      console.error("Error loading ROI image:", error);
      if (retryCount < maxRetries) {
        console.log(`Retrying loadRoiImage (${retryCount + 1}/${maxRetries})...`);
        setTimeout(() => loadRoiImage(fileSuffix, retryCount + 1, maxRetries), 500);
      } else {
        setInternalError(`Không thể tải ảnh tạm: ${error.message}. Vui lòng thử lại.`);
      }
    }
  };

  useEffect(() => {
    console.log("useEffect triggered with analysisResult:", analysisResult, "currentStep:", currentStep, "roiImageState:", roiImageState);
    if (analysisResult && analysisResult.roi_frame && roiImageState.ready) {
      loadRoiImage(roiImageState.file);
    } else if (currentStep === "packing" && analysisResult?.roi_frame) {
      loadRoiImage("roi_packing.jpg");
    }
  }, [analysisResult, currentStep, roiImageState.ready]);

  const fetchFinalRoiFrame = async () => {
    try {
      console.log(`Calling /get-final-roi-frame with camera_id: ${cameraId}`);
      const timestamp = new Date().getTime();
      const url = `http://localhost:8080/get-final-roi-frame?camera_id=${cameraId}&t=${timestamp}`;
      const response = await fetch(url, {
        headers: { 'Cache-Control': 'no-cache' },
      });
      if (!response.ok && response.status !== 304) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      console.log("Response from /get-final-roi-frame:", response);
      setFinalRoiFrameSrc(url);
    } catch (error) {
      console.error("Error fetching final ROI frame:", error);
      setInternalError("Không thể tải ảnh tổng hợp. Vui lòng thử lại.");
    }
  };

  const handleConfirmRoi = async () => {
    if (currentStep === "packing" && analysisResult?.roi) {
      if (!analysisResult || typeof analysisResult.hand_detected === "undefined") {
        setInternalError("Không tìm thấy thông tin phát hiện tay từ backend. Vui lòng thử lại.");
        return;
      }
      if (!analysisResult.hand_detected) {
        setInternalError("Không phát hiện tay. Vui lòng vẽ lại vùng packing hoặc thoát.");
        return;
      }
      if (!analysisResult.roi_frame) {
        setInternalError("Thiếu đường dẫn ảnh tạm packing. Vui lòng thử lại.");
        return;
      }

      const newRoi = { type: currentStep, ...analysisResult.roi };
      const updatedRois = [...rois, newRoi];
      setRois(updatedRois);
      setCurrentStep("mvd");
      setRoiImageState({ step: "mvd", file: "roi_packing.jpg", ready: true });
      try {
        console.log("Calling /run-qr-detector for mvd step with videoPath:", videoPath, "cameraId:", cameraId, "roiFramePath:", analysisResult.roi_frame);
        const response = await fetch('http://localhost:8080/run-qr-detector', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ videoPath, cameraId, roiFramePath: analysisResult.roi_frame }),
        });
        const result = await response.json();
        console.log("Result from /run-qr-detector (mvd):", result);
        if (result.success) {
          const tempResult = {
            success: true,
            message: result.message || "QR detection completed successfully",
            rois: result.rois,
            qr_detected: result.qr_detected,
            qr_detected_roi1: result.qr_detected_roi1,
            qr_detected_roi2: result.qr_detected_roi2,
            roi_frame: result.roi_frame,
            qr_content: result.qr_content,
            trigger_detected: result.trigger_detected,
            table_type: result.table_type,
          };
        
          if (result.roi_frame) {
            setRoiImageState({ step: "mvd", file: "roi_MVD.jpg", ready: true });
            await loadRoiImage("roi_MVD.jpg");
            setAnalysisResult(tempResult); // Chỉ set sau khi ảnh tải xong
          } else {
            console.log("No roi_frame in result, keeping roi_packing.jpg");
            setAnalysisResult(tempResult);
          }
        } else {
          setInternalError(result.error || "Không thể vẽ vùng mã vận đơn.");
        }
      } catch (error) {
        setInternalError("Lỗi khi vẽ vùng mã vận đơn: " + error.message);
      }
    } else if (currentStep === "mvd" && analysisResult?.rois) {
      if (!analysisResult || typeof analysisResult.qr_detected === "undefined") {
        setInternalError("Không tìm thấy thông tin phát hiện QR từ backend. Vui lòng thử lại.");
        return;
      }
      if (!analysisResult.qr_detected) {
        setInternalError("Không phát hiện mã QR. Vui lòng vẽ lại vùng MVD hoặc thoát.");
        return;
      }
      if (!analysisResult.roi_frame) {
        setInternalError("Thiếu đường dẫn ảnh tạm MVD. Vui lòng thử lại.");
        return;
      }

      const newRois = analysisResult.rois.map((roi) => ({ type: currentStep, ...roi }));
      const updatedRois = [...rois, ...newRois];
      setRois(updatedRois);
      setCurrentStep("done");
      try {
        const response = await fetch('http://localhost:8080/finalize-roi', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ videoPath, cameraId, rois: updatedRois }),
        });
        const result = await response.json();
        if (result.success) {
          await fetchFinalRoiFrame();
          onSubmit(updatedRois);
          onSave();
        } else {
          setInternalError(result.error || "Không thể tạo ảnh tổng hợp.");
        }
      } catch (error) {
        setInternalError("Lỗi khi tạo ảnh tổng hợp: " + error.message);
      }
    }
    if (currentStep === "done") {
      onSave();
    }
  };

  const handleRetryStep = async () => {
    if (!videoPath || !cameraId) {
      setInternalError("Thiếu videoPath hoặc cameraId.");
      return;
    }

    try {
      if (currentStep === "packing") {
        console.log("Calling /run-select-roi for retry with videoPath:", videoPath, "cameraId:", cameraId);
        const response = await fetch('http://localhost:8080/api/hand_detection/select-roi', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ videoPath, cameraId }),
        });
        const result = await response.json();
        console.log("Result from /run-select-roi (retry):", result);
        if (result.success) {
          const newAnalysisResult = {
            success: true,
            message: result.message || "Hand detection completed successfully",
            roi: result.roi,
            hand_detected: result.hand_detected,
            roi_frame: result.roi_frame,
          };
          setAnalysisResult(newAnalysisResult);
          if (result.roi_frame) {
            setRoiImageState({ step: "packing", file: "roi_packing.jpg", ready: true });
            await loadRoiImage("roi_packing.jpg");
          }
        } else {
          setInternalError(result.error || `Không thể chạy lại hand detection.`);
        }
      } else if (currentStep === "mvd") {
        console.log("Calling /run-qr-detector for retry with videoPath:", videoPath, "cameraId:", cameraId, "roiFramePath:", analysisResult.roi_frame);
        const response = await fetch('http://localhost:8080/api/qr_detection/select-qr-roi', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ videoPath, cameraId, roiFramePath: analysisResult.roi_frame }),
        });
        const result = await response.json();
        console.log("Result from /run-qr-detector (retry):", result);
        if (result.success) {
          const newAnalysisResult = {
            success: true,
            message: result.message || "QR detection completed successfully",
            rois: result.rois,
            qr_detected: result.qr_detected,
            qr_detected_roi1: result.qr_detected_roi1,
            qr_detected_roi2: result.qr_detected_roi2,
            qr_content: result.qr_content,
            roi_frame: result.roi_frame,
            trigger_detected: result.trigger_detected,
            table_type: result.table_type,
          };
          setAnalysisResult(newAnalysisResult);
          if (result.roi_frame && result.qr_detected) {
            setRoiImageState({ step: "mvd", file: "roi_MVD.jpg", ready: true });
            await loadRoiImage("roi_MVD.jpg");
          } else {
            setInternalError("Không thể tải ảnh hoặc không phát hiện QR.");
          }
        } else {
          setInternalError(result.error || `Không thể chạy lại QR detection.`);
        }
      }
    } catch (error) {
      setInternalError(`Lỗi khi chạy lại: ${error.message}`);
    }
  };

  const handleImageLoad = (e) => {
    const { width, height } = e.target;
    setImageAspectRatio(width / height);
  };

  return (
    <div className="flex w-full h-full">
      <div className="w-1/4 pr-4 flex flex-col border-r-2 border-gray-500">
        <div className="mb-4">
          <h3 className="text-2xl font-bold mb-2 text-white">Kết quả</h3>
          {currentStep === "mvd" ? (
            <>
              {analysisResult?.table_type === "standard" ? (
                <>
                  <div className={`p-2 rounded text-white flex items-center ${analysisResult?.trigger_detected ? 'bg-green-600' : 'bg-red-600'}`}>
                    <span className="mr-2">{analysisResult?.trigger_detected ? '✔' : '✘'}</span>
                    <p>ROI Trigger: {analysisResult?.trigger_detected ? 'Có' : 'Không'}</p>
                  </div>
                  <div className={`p-2 rounded text-white flex items-center mt-2 ${analysisResult?.qr_detected_roi1 ? 'bg-green-600' : 'bg-red-600'}`}>
                    <span className="mr-2">{analysisResult?.qr_detected_roi1 ? '✔' : '✘'}</span>
                    <p>ROI MVD: {analysisResult?.qr_detected_roi1 ? 'Có' : 'Không'}</p>
                  </div>
                </>
              ) : (
                <>
                  {typeof analysisResult?.qr_detected_roi1 !== 'undefined' && (
                    <div className={`p-2 rounded text-white flex items-center ${analysisResult?.qr_detected_roi1 ? 'bg-green-600' : 'bg-red-600'}`}>
                      <span className="mr-2">{analysisResult?.qr_detected_roi1 ? '✔' : '✘'}</span>
                      <p>ROI 1: {analysisResult?.qr_detected_roi1 ? 'Có' : 'Không'}</p>
                    </div>
                  )}
                </>
              )}
            </>
          ) : (
            <div className={`p-2 rounded text-white flex items-center ${handDetected ? 'bg-green-600' : 'bg-red-600'}`}>
              <span className="mr-2">{handDetected ? '✔' : '✘'}</span>
              <p>{handDetected ? `Xác nhận vùng ${currentStep}` : 'Không phát hiện chuyển động'}</p>
            </div>
          )}
          {errorMessage && (
            <div className="mt-2 p-2 bg-red-600 rounded text-white">
              <p>{errorMessage}</p>
            </div>
          )}
          {internalError && (
            <div className="mt-2 p-2 bg-red-600 rounded text-white">
              <p>{internalError}</p>
            </div>
          )}
        </div>
        <div className="mb-4 flex-1">
          <h3 className="text-xl font-bold mb-2 text-white">Hướng dẫn</h3>
          <p className="text-gray-300 text-lg">
            {currentStep === "done"
              ? "Đã hoàn tất vẽ vùng và phát hiện mã QR. Nhấn Thoát để tiếp tục."
              : currentStep === "mvd"
                ? analysisResult?.qr_detected
                  ? "Đã tìm thấy mã QR. Nhấn Hoàn tất để lưu và tiếp tục."
                  : "Vẽ lại vùng mã vận đơn hoặc thoát."
                : handDetected
                  ? "Tiếp tục xác định vùng mã vận đơn."
                  : "Vẽ lại vùng packing hoặc thoát."}
          </p>
        </div>
        <div className="mt-auto space-y-2">
          {currentStep !== "done" && (
            <button
              onClick={handleRetryStep}
              className="w-full py-2 bg-yellow-600 hover:bg-yellow-700 text-white font-bold rounded"
            >
              Vẽ lại
            </button>
          )}
          {currentStep === "mvd" && analysisResult?.qr_detected && (
            <button
              onClick={handleConfirmRoi}
              className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded"
            >
              Hoàn tất
            </button>
          )}
          {currentStep === "packing" && handDetected && (
            <button
              onClick={handleConfirmRoi}
              className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded"
            >
              Tiếp tục
            </button>
          )}
          <button
            onClick={onClose}
            className="w-full py-2 bg-red-600 hover:bg-red-700 text-white font-bold rounded"
          >
            Thoát
          </button>
        </div>
      </div>
      <div className="w-3/4 pl-4 flex flex-col">
        <div className="mb-4 flex justify-center items-center" style={{ maxHeight: 'calc(75vh - 2rem)', overflow: 'hidden' }}>
          {console.log("Rendering ROI frame with roiFrameSrc:", roiFrameSrc, "roiImageState:", roiImageState)}
          {roiFrameSrc && (
            <img 
              src={roiFrameSrc} 
              alt="ROI Frame" 
              className={`max-w-full max-h-full rounded ${imageAspectRatio && imageAspectRatio < 1 ? 'portrait' : 'landscape'}`}
              onLoad={handleImageLoad}
            />
          )}
        </div>
        {finalRoiFrameSrc && currentStep === "done" && (
          <div className="mb-4 flex justify-center items-center" style={{ maxHeight: 'calc(75vh - 2rem)', overflow: 'hidden' }}>
            <h4 className="text-lg font-bold text-white">Ảnh tổng hợp:</h4>
            <img 
              src={finalRoiFrameSrc} 
              alt="Final ROI Frame" 
              className={`max-w-full max-h-full rounded ${imageAspectRatio && imageAspectRatio < 1 ? 'portrait' : 'landscape'}`}
              onLoad={handleImageLoad}
            />
          </div>
        )}
      </div>
      <style jsx>{`
        .max-w-full {
          max-width: 100%;
        }
        .max-h-full {
          max-height: 100%;
        }
        .landscape {
          object-fit: contain;
          width: 100%;
        }
        .portrait {
          object-fit: contain;
          height: 100%;
        }
      `}</style>
    </div>
  );
};

export default InstructionsPanel;