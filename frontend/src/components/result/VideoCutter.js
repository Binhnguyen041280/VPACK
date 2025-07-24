import { useState } from "react";
import api from "../../api"; // Điều chỉnh đường dẫn tương đối từ thư mục result

const VideoCutter = ({ results, selectedVideos, setResults, setSelectedVideos }) => {
  const [cutVideos, setCutVideos] = useState([]);
  const [selectedCutVideo, setSelectedCutVideo] = useState(null); // Thêm trạng thái để lưu video đã cắt được chọn

  // Hàm xử lý yêu cầu cắt video
  const handleCutVideos = async () => {
    if (selectedVideos.length === 0) {
      alert("Vui lòng chọn ít nhất một sự kiện để cắt video.");
      return;
    }
    try {
      const selectedEvents = results.filter(event => selectedVideos.includes(event.event_id));
      const cutData = {
        selected_events: selectedEvents,
        // tracking_codes_filter sẽ được thêm sau nếu cần từ QueryComponent
      };

      const response = await api.post("/cut-videos", cutData); // Gọi API cắt video
      const cutFiles = response.data.cut_files || [];

      setCutVideos(prev => [...prev, ...cutFiles]); // Cập nhật danh sách video đã cắt
      setResults(prev => prev.filter(event => !selectedVideos.includes(event.event_id))); // Xóa sự kiện đã cắt
      setSelectedVideos([]); // Reset danh sách chọn
    } catch (error) {
      console.error("Error cutting videos:", error);
      alert("Có lỗi xảy ra khi cắt video. Vui lòng thử lại.");
    }
  };

  const handleRefresh = () => {
    setResults([]);
    setSelectedVideos([]);
    setCutVideos([]);
    setSelectedCutVideo(null); // Reset video đã chọn khi refresh
  };

  // Hàm xử lý khi nhấn nút "Play Video"
  const handlePlayVideo = () => {
    if (!selectedCutVideo) {
      alert("Vui lòng chọn một video để phát");
      return;
    }
    alert(`Đang phát video "${selectedCutVideo}" được chọn`);
  };

  return (
    <>
      <div className="flex gap-4 mb-4">
        <button
          className="w-1/3 py-2 bg-red-600 text-white font-bold rounded"
          onClick={handleCutVideos}
        >
          Cắt Video
        </button>
        <button
          className="w-1/3 py-2 px-4 rounded font-bold text-white bg-[#00D4FF]"
          onClick={handleRefresh}
        >
          Refresh
        </button>
        <button
          className="w-1/3 py-2 px-4 rounded font-bold text-white bg-green-600"
          onClick={handlePlayVideo}
        >
          Play Video
        </button>
      </div>
      <div className="flex-1 bg-gray-700 rounded p-2 overflow-y-auto">
        {cutVideos.map((video, index) => (
          <label
            key={index}
            className="flex items-center mb-2 cursor-pointer hover:bg-gray-600 transition duration-300"
            onClick={() => setSelectedCutVideo(video)}
          >
            <input
              type="radio"
              name="cutVideo"
              className="mr-2"
              checked={selectedCutVideo === video}
              onChange={() => setSelectedCutVideo(video)}
            />
            <span className="flex-1 truncate">{`${index + 1}. ${video}`}</span>
          </label>
        ))}
      </div>
    </>
  );
};

export default VideoCutter;