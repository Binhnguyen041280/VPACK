import api from "../../api"; // Thêm import api để gọi /cut-videos

const CutVideoSection = ({ results, selectedVideos, setResults, setSelectedVideos, cutVideos, setCutVideos }) => {
  const handleCutVideos = async () => {
    if (selectedVideos.length === 0) {
      alert("Vui lòng chọn ít nhất một sự kiện để cắt video.");
      return;
    }
    const videosToCut = results.filter((event) => selectedVideos.includes(event.event_id));
    try {
      const cutData = {
        selected_events: videosToCut,
      };
      const response = await api.post("/cut-videos", cutData); // Gọi API /cut-videos
      const cutFiles = response.data.cut_files || []; // Lấy danh sách file từ phản hồi
      setCutVideos(prev => [...prev, ...cutFiles]); // Tối ưu với prev
      setResults(results.filter((event) => !selectedVideos.includes(event.event_id)));
      setSelectedVideos([]);
    } catch (error) {
      console.error("Error cutting videos:", error);
      alert("Có lỗi xảy ra khi cắt video. Vui lòng thử lại.");
    }
  };

  const handleRefresh = () => {
    setResults([]);
    setSelectedVideos([]);
    setCutVideos([]); // Xóa danh sách video đã cắt
  };

  return (
    <>
      <div className="flex gap-4 mb-4">
        <button
          className="w-1/2 py-2 bg-red-600 text-white font-bold rounded"
          onClick={handleCutVideos}
        >
          Cắt Video
        </button>
        <button
          className="w-1/2 py-2 px-4 rounded font-bold text-white bg-[#00D4FF]"
          onClick={handleRefresh}
        >
          Refresh
        </button>
      </div>
      <div className="flex-1 bg-gray-700 rounded p-2 overflow-y-auto">
        {cutVideos.map((video, index) => (
          <label key={index} className="flex items-center mb-2">
            <input type="checkbox" className="mr-2" />
            {`${index + 1}. ${video}`}
          </label>
        ))}
      </div>
    </>
  );
};

export default CutVideoSection;