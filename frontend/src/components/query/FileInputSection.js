const FileInputSection = ({ path, setPath, fileContent, setFileContent, setShowModal, setHeaders }) => {
  const handleOpenExplorer = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".csv,.xlsx";
    input.onchange = (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const fileName = file.name.toLowerCase();
      const fileType = file.type;

      // Kiểm tra đuôi file
      if (!fileName.endsWith(".csv") && !fileName.endsWith(".xlsx")) {
        alert("Vui lòng chọn file CSV hoặc Excel (.csv, .xlsx)");
        return;
      }

      // Kiểm tra MIME type
      const validCsvMimeTypes = ["text/csv", "application/csv"];
      const validXlsxMimeTypes = [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
      ];
      if (fileName.endsWith(".csv") && !validCsvMimeTypes.includes(fileType)) {
        alert("File không đúng định dạng CSV. Vui lòng chọn file CSV hợp lệ.");
        return;
      }
      if (fileName.endsWith(".xlsx") && !validXlsxMimeTypes.includes(fileType)) {
        alert("File không đúng định dạng Excel. Vui lòng chọn file XLSX hợp lệ.");
        return;
      }

      setPath(file.name);

      const reader = new FileReader();
      reader.onload = (event) => {
        const arrayBuffer = event.target.result;
        const bytes = new Uint8Array(arrayBuffer);
        const binary = Array.from(bytes).map((b) => String.fromCharCode(b)).join("");
        const base64 = btoa(binary); // Base64 encode từ nhị phân
        setFileContent(base64);
      };
      reader.onerror = () => {
        alert("Lỗi khi đọc file");
      };
      reader.readAsArrayBuffer(file); // Đọc raw binary
    };
    input.click();
  };

  const handleConfirmFile = async () => {
    if (!path) {
      alert("Vui lòng chọn file CSV hoặc nhập đường dẫn");
      return;
    }
    try {
      const response = await fetch("http://localhost:8080/get-csv-headers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          file_path: path,
          file_content: fileContent || "",
          is_excel: path.toLowerCase().endsWith(".xlsx"),
        }),
      });
      const result = await response.json();
      if (response.ok) {
        setHeaders(result.headers || []);
        setShowModal(true);
      } else {
        throw new Error(result.error || "Failed to get CSV headers");
      }
    } catch (error) {
      console.error("Error getting CSV headers:", error);
      alert(error.message || "Failed to get CSV headers");
    }
  };

  return (
    <div className="mb-4">
      <div className="relative w-full mb-2">
        <input
          type="text"
          value={path}
          onChange={(e) => setPath(e.target.value)}
          placeholder="Chọn file định dạng *.csv hoặc *.xlsx"
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
      <button
        onClick={handleConfirmFile}
        className="w-full py-2 bg-yellow-500 text-white font-bold rounded"
      >
        Xác nhận
      </button>
    </div>
  );
};

export default FileInputSection;