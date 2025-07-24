import { useState, useEffect } from "react";
import { runProgram, confirmRun } from "../api";

const useProgramLogic = () => {
  const [runningCard, setRunningCard] = useState("Mặc định");
  const [fileList, setFileList] = useState([]);
  const [customPath, setCustomPath] = useState("");
  const [showConfirmButton, setShowConfirmButton] = useState(false);
  const [firstRunCompleted, setFirstRunCompleted] = useState(false);
  const [isLocked, setIsLocked] = useState(false);

  const checkFirstRun = async () => {
    try {
      const response = await fetch("http://localhost:8080/check-first-run");
      const data = await response.json();
      setFirstRunCompleted(data.first_run_completed);
    } catch (error) {
      console.error("Error checking first run:", error);
    }
  };

  const checkDefaultRunning = async () => {
    try {
      const response = await fetch("http://localhost:8080/program", {
        method: "GET",
      });
      const data = await response.json();
      setRunningCard("Mặc định"); // Ép Mặc định khi refresh
      setIsLocked(false);
    } catch (error) {
      console.error("Error checking default running state:", error);
      setRunningCard("Mặc định"); // Ép Mặc định nếu lỗi
      setIsLocked(false);
    }
  };

  useEffect(() => {
    const initializeState = async () => {
      await checkFirstRun();
      await checkDefaultRunning();
    };
    initializeState();
  }, []);

  const handleRunStop = async (cardTitle, path = "") => {
    if (cardTitle === "Lần đầu" && firstRunCompleted) {
      return;
    }

    if (isLocked) {
      alert("Hệ thống đang xử lý, vui lòng đợi!");
      return;
    }

    try {
      let days = null;
      if (cardTitle === "Lần đầu" && !isRunning(cardTitle)) {
        days = prompt("Bạn muốn xử lý bao nhiêu ngày? (Tối đa 30 ngày)", "30");
        days = parseInt(days);
        if (isNaN(days) || days <= 0 || days > 30) {
          alert("Số ngày không hợp lệ. Vui lòng nhập từ 1 đến 30.");
          return;
        }
      } else if (cardTitle === "Chỉ định" && !isRunning(cardTitle)) {
        if (!path) {
          alert("Vui lòng chọn đường dẫn cho chương trình Chỉ định.");
          return;
        }
        setIsLocked(true);
      }

      const response = await runProgram({
        card: cardTitle,
        action: isRunning(cardTitle) ? "stop" : "run",
        days: days,
        custom_path: cardTitle === "Chỉ định" ? path : ""
      });

      if (response.status === 200) {
        if (isRunning(cardTitle)) {
          if (cardTitle === "Mặc định") {
            setRunningCard(null);
            setFileList([]);
            alert(`Đã dừng chương trình ${cardTitle}`);
          }
        } else {
          if (cardTitle !== "Lần đầu" || !firstRunCompleted) {
            setRunningCard(cardTitle);
            setShowConfirmButton(true);
            if (cardTitle !== "Chỉ định") {
              setIsLocked(false);
            }
          }
        }
      }
    } catch (error) {
      console.error("Error calling API:", error);
      setIsLocked(false);
      if (error.response?.status === 400) {
        alert(error.response.data.error);
      } else {
        alert("Có lỗi xảy ra khi gọi API. Vui lòng kiểm tra server.");
      }
    }
  };

  const handleConfirmRun = async () => {
    try {
      const response = await confirmRun({ card: runningCard });
      if (response.status === 200) {
        setShowConfirmButton(false);
        setFileList(response.data.files || []);
        if (runningCard === "Lần đầu") {
          setFirstRunCompleted(true);
          await checkFirstRun();
        }
        if (runningCard === "Chỉ định") {
          setIsLocked(false);
          await checkDefaultRunning();
        }
      }
    } catch (error) {
      console.error("Error confirming run:", error);
      setIsLocked(false);
      alert("Có lỗi xảy ra khi xác nhận chạy chương trình.");
    }
  };

  const isRunning = (cardTitle) => runningCard === cardTitle;

  return {
    runningCard,
    setRunningCard,
    fileList,
    setFileList,
    customPath,
    setCustomPath,
    showConfirmButton,
    setShowConfirmButton,
    firstRunCompleted,
    setFirstRunCompleted,
    handleRunStop,
    handleConfirmRun,
    isRunning,
    isLocked
  };
};

export default useProgramLogic;