const ColumnSelectorModal = ({
  showModal,
  setShowModal,
  headers,
  selectedColumn,
  setSelectedColumn,
  history,
  setHistory,
  selectedPlatform,
  setSelectedPlatform,
  shopeeLabel,
  setShopeeLabel,
  lazadaLabel,
  setLazadaLabel,
  tiktokLabel,
  setTiktokLabel,
  customLabel1,
  setCustomLabel1,
  customLabel2,
  setCustomLabel2,
  path,
  fileContent,
  setSearchString,
  setSearchType,
}) => {
  const handleModalConfirm = async () => {
    const columnName = history[selectedPlatform] || "tracking_codes";
    const data = {
      file_path: path,
      file_content: fileContent || "",
      column_name: columnName,
      is_excel: path.toLowerCase().endsWith(".xlsx"), // Thêm logic xác định is_excel dựa trên path
    };
    try {
      console.log("Sending file data:", data);
      const response = await fetch("http://localhost:8080/parse-csv", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const result = await response.json();
      console.log("Response from parse-csv:", result);
      if (response.ok) {
        const trackingCodes = result.tracking_codes || [];
        const formattedCodes = trackingCodes
          .map((code, index) => `${index + 1}. ${code}`)
          .join("\n");
        setSearchString(formattedCodes);
        setSearchType("Text");
        setShowModal(false);
      } else {
        throw new Error(result.error || "Failed to parse CSV");
      }
    } catch (error) {
      console.error("Error parsing CSV:", error);
      alert(error.message || "Failed to parse CSV");
    }
  };

  const handleUpdateColumn = () => {
    const newColumn = selectedColumn;
    const updatedHistory = { ...history };
    updatedHistory[selectedPlatform] = newColumn;
    setHistory(updatedHistory);
    localStorage.setItem("trackingColumnHistory", JSON.stringify(updatedHistory));

    const updatedLabels = {
      Shopee: shopeeLabel,
      Lazada: lazadaLabel,
      Tiktok: tiktokLabel,
      Custom1: customLabel1,
      Custom2: customLabel2,
    };
    localStorage.setItem("platformLabels", JSON.stringify(updatedLabels));
  };

  const handlePlatformChange = (platform) => {
    setSelectedPlatform(platform);
    setSelectedColumn(history[platform] || "tracking_codes");
  };

  if (!showModal) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
      <div className="bg-gray-800 p-6 rounded-lg w-1/2">
        <h2 className="text-xl font-bold mb-4">Chọn cột mã vận đơn</h2>
        <div className="mb-4">
          <label className="block mb-1">Chọn từ danh sách:</label>
          <select
            value={selectedColumn}
            onChange={(e) => setSelectedColumn(e.target.value)}
            className="w-full p-2 rounded bg-gray-700 text-white"
          >
            {headers.map((header, index) => (
              <option key={index} value={header}>{header}</option>
            ))}
          </select>
        </div>
        <div className="mb-4">
          <button
            onClick={handleUpdateColumn}
            className="w-full py-2 bg-blue-600 text-white font-bold rounded"
          >
            Cập nhật
          </button>
        </div>
        <div className="mb-4">
          <h3 className="text-lg font-bold mb-2">Lịch sử lựa chọn:</h3>
          <label className="flex items-center mb-2">
            <input
              type="radio"
              name="platform"
              value="Shopee"
              checked={selectedPlatform === "Shopee"}
              onChange={() => handlePlatformChange("Shopee")}
              className="mr-2"
            />
            <input
              type="text"
              value={shopeeLabel}
              onChange={(e) => setShopeeLabel(e.target.value)}
              placeholder="Tên Shopee"
              className="mr-2 p-1 rounded bg-gray-700 text-white"
            />
            <input
              type="text"
              value={history.Shopee}
              onChange={(e) => setHistory({ ...history, Shopee: e.target.value })}
              className="p-1 rounded bg-gray-700 text-white"
            />
          </label>
          <label className="flex items-center mb-2">
            <input
              type="radio"
              name="platform"
              value="Lazada"
              checked={selectedPlatform === "Lazada"}
              onChange={() => handlePlatformChange("Lazada")}
              className="mr-2"
            />
            <input
              type="text"
              value={lazadaLabel}
              onChange={(e) => setLazadaLabel(e.target.value)}
              placeholder="Tên Lazada"
              className="mr-2 p-1 rounded bg-gray-700 text-white"
            />
            <input
              type="text"
              value={history.Lazada}
              onChange={(e) => setHistory({ ...history, Lazada: e.target.value })}
              className="p-1 rounded bg-gray-700 text-white"
            />
          </label>
          <label className="flex items-center mb-2">
            <input
              type="radio"
              name="platform"
              value="Tiktok"
              checked={selectedPlatform === "Tiktok"}
              onChange={() => handlePlatformChange("Tiktok")}
              className="mr-2"
            />
            <input
              type="text"
              value={tiktokLabel}
              onChange={(e) => setTiktokLabel(e.target.value)}
              placeholder="Tên Tiktok"
              className="mr-2 p-1 rounded bg-gray-700 text-white"
            />
            <input
              type="text"
              value={history.Tiktok}
              onChange={(e) => setHistory({ ...history, Tiktok: e.target.value })}
              className="p-1 rounded bg-gray-700 text-white"
            />
          </label>
          <label className="flex items-center mb-2">
            <input
              type="radio"
              name="platform"
              value="Custom1"
              checked={selectedPlatform === "Custom1"}
              onChange={() => handlePlatformChange("Custom1")}
              className="mr-2"
            />
            <input
              type="text"
              value={customLabel1}
              onChange={(e) => setCustomLabel1(e.target.value)}
              placeholder="Tên tùy chỉnh 1"
              className="mr-2 p-1 rounded bg-gray-700 text-white"
            />
            <input
              type="text"
              value={history.Custom1}
              onChange={(e) => setHistory({ ...history, Custom1: e.target.value })}
              className="p-1 rounded bg-gray-700 text-white"
            />
          </label>
          <label className="flex items-center mb-2">
            <input
              type="radio"
              name="platform"
              value="Custom2"
              checked={selectedPlatform === "Custom2"}
              onChange={() => handlePlatformChange("Custom2")}
              className="mr-2"
            />
            <input
              type="text"
              value={customLabel2}
              onChange={(e) => setCustomLabel2(e.target.value)}
              placeholder="Tên tùy chỉnh 2"
              className="mr-2 p-1 rounded bg-gray-700 text-white"
            />
            <input
              type="text"
              value={history.Custom2}
              onChange={(e) => setHistory({ ...history, Custom2: e.target.value })}
              className="p-1 rounded bg-gray-700 text-white"
            />
          </label>
        </div>
        <div className="flex justify-end gap-4">
          <button
            onClick={() => setShowModal(false)}
            className="py-2 px-4 bg-gray-600 text-white rounded"
          >
            Hủy
          </button>
          <button
            onClick={handleModalConfirm}
            className="py-2 px-4 bg-green-600 text-white rounded"
          >
            Xác nhận
          </button>
        </div>
      </div>
    </div>
  );
};

export default ColumnSelectorModal;