import { useState, useEffect } from "react";
import Card from "../ui/Card";
import FileList from "./FileList";

const ProgramTab = ({
  runningCard,
  fileList,
  customPath,
  firstRunCompleted,
  handleRunStop,
  isRunning,
  setCustomPath,
}) => {
  const [updatedFileList, setUpdatedFileList] = useState(fileList);

  useEffect(() => {
    const fetchProgress = async () => {
      try {
        const response = await fetch("http://localhost:8080/program-progress", {
          method: "GET",
          headers: { "Content-Type": "application/json" },
        });
        const data = await response.json();
        if (response.ok) {
          setUpdatedFileList(data.files);
        } else {
          console.error("Failed to fetch program progress:", data.error);
        }
      } catch (error) {
        console.error("Error fetching program progress:", error);
      }
    };

    fetchProgress();
    const intervalId = setInterval(fetchProgress, 10000);
    const timeoutId = setTimeout(() => {
      clearInterval(intervalId);
      console.log("Stopped polling /program-progress after 2 minutes");
    }, 120000);

    return () => {
      clearInterval(intervalId);
      clearTimeout(timeoutId);
    };
  }, [runningCard]);

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-3 gap-6">
        {!firstRunCompleted && (
          <Card
            title="Lần đầu"
            description="Chạy lần đầu để xử lý dữ liệu cơ sở."
            isRunning={isRunning("Lần đầu")}
            onRunStop={firstRunCompleted ? null : () => handleRunStop("Lần đầu")}
            isLocked={firstRunCompleted}
          />
        )}
        <Card
          title="Mặc định"
          description="Chạy khi khởi động, chạy nền."
          isRunning={isRunning("Mặc định")}
          onRunStop={() => handleRunStop("Mặc định")}
        />
        <Card
          title="Chỉ định"
          description="Chỉ định file cụ thể."
          isRunning={isRunning("Chỉ định")}
          onRunStop={() => handleRunStop("Chỉ định", customPath)}
          onPathChange={(path) => setCustomPath(path)}
        />
      </div>
      <FileList fileList={updatedFileList} />
    </div>
  );
};

export default ProgramTab;