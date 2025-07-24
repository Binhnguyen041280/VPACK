import { useState } from "react";

const Card = ({ title, description, isRunning, onRunStop, onPathChange, isLocked }) => {
  const [path, setPath] = useState("");

  const handleOpenExplorer = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.onchange = (e) => {
      const selectedPath = e.target.files[0]?.name || "";
      setPath(selectedPath);
      if (onPathChange) {
        onPathChange(selectedPath);
      }
    };
    input.click();
  };

  return (
    <div className="bg-gray-800 p-6 rounded-lg flex flex-col items-center h-full">
      <h3 className="text-lg font-bold mb-2">{title}</h3>
      <p className="mb-4 text-center flex-1">{description}</p>
      <div className="mt-auto w-full flex flex-col items-center">
        {title === "Chỉ định" && (
          <div className="mb-4 w-full">
            <div className="relative w-full">
              <input
                type="text"
                value={path}
                onChange={(e) => {
                  setPath(e.target.value);
                  if (onPathChange) {
                    onPathChange(e.target.value);
                  }
                }}
                placeholder="Nhập đường dẫn file..."
                className="w-full p-2 rounded bg-gray-700 text-white"
              />
              <button
                type="button"
                onClick={handleOpenExplorer}
                className="absolute right-2 top-1/2 transform -translate-y-1/2 text-white"
              >
                ...
              </button>
            </div>
          </div>
        )}
        {isLocked || (title === "Lần đầu" && isRunning) ? (
          <button
            className="w-1/2 py-2 px-4 rounded font-bold text-white bg-gray-500"
            disabled
          >
            LOCKED
          </button>
        ) : (
          <button
            className={`w-1/2 py-2 px-4 rounded font-bold text-white ${
              isRunning && title !== "Lần đầu" ? "bg-[#E82127]" : "bg-[#00D4FF]"
            }`}
            onClick={onRunStop}
            disabled={title === "Chỉ định" && !path && !isRunning}
          >
            {(isRunning && title !== "Lần đầu") ? "STOP" : "RUN"}
          </button>
        )}
      </div>
    </div>
  );
};

export default Card;