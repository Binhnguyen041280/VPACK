import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { useState, useEffect } from "react";
import timezoneManager from "../../utils/TimezoneManager";

const TimeAndQuerySection = ({
  startDate,
  setStartDate,
  endDate,
  setEndDate,
  defaultDays,
  setDefaultDays,
  searchString,
  searchType,
  fileContent,
  results,
  setResults,
  setSelectedVideos,
  setQueryCount,
  setFoundCount,
  foundCount,
  onQuery, // Prop để nhận hàm debounce từ QueryComponent
  isQuerying, // Prop để vô hiệu hóa nút
}) => {
  const [currentTimezone, setCurrentTimezone] = useState(null);

  useEffect(() => {
    // Load current timezone info
    const tzInfo = timezoneManager.getTimezoneInfo();
    setCurrentTimezone(tzInfo);
  }, []);
  const handleStartDateChange = (date) => {
    setStartDate(date);
    if (endDate) {
      const diffDays = (endDate - date) / (1000 * 60 * 60 * 24);
      if (diffDays > 30) {
        setEndDate(new Date(date.getTime() + 30 * 24 * 60 * 60 * 1000));
      } else if (date > endDate) {
        setEndDate(date);
      }
    }
  };

  const handleEndDateChange = (date) => {
    const today = new Date();
    if (date > today) {
      date = today;
    }
    if (startDate) {
      const diffDays = (date - startDate) / (1000 * 60 * 60 * 24);
      if (diffDays > 30) {
        setStartDate(new Date(date.getTime() - 30 * 24 * 60 * 60 * 1000));
      } else if (date < startDate) {
        setStartDate(date);
      }
    }
    setEndDate(date);
  };

  return (
    <>
      <div className="mb-4">
        <label className="block mb-1">Thời gian mặc định (ngày):</label>
        <input
          type="number"
          value={defaultDays}
          onChange={(e) => setDefaultDays(Number(e.target.value))}
          className="w-full p-2 rounded bg-gray-700 text-white"
        />
      </div>
      <div className="flex gap-4 mb-4">
        <div className="flex-1">
          <label className="block mb-1">
            Từ:
            <span className="text-xs text-gray-400 ml-1">
              ({currentTimezone?.currentOffset || 'UTC'})
            </span>
          </label>
          <DatePicker
            selected={startDate}
            onChange={handleStartDateChange}
            showTimeSelect
            timeIntervals={60}
            dateFormat="Pp"
            className="w-full p-2 rounded bg-gray-700 text-white"
            placeholderText={`Thời gian bắt đầu (${currentTimezone?.currentOffset || 'UTC'})`}
          />
          {startDate && (
            <div className="mt-1 text-xs text-gray-400">
              UTC: {timezoneManager.toUtcForBackend(startDate).replace('T', ' ').slice(0, 19)}
            </div>
          )}
        </div>
        <div className="flex-1">
          <label className="block mb-1">
            Đến:
            <span className="text-xs text-gray-400 ml-1">
              ({currentTimezone?.currentOffset || 'UTC'})
            </span>
          </label>
          <DatePicker
            selected={endDate}
            onChange={handleEndDateChange}
            showTimeSelect
            timeIntervals={60}
            dateFormat="Pp"
            maxDate={new Date()}
            className="w-full p-2 rounded bg-gray-700 text-white"
            placeholderText={`Thời gian kết thúc (${currentTimezone?.currentOffset || 'UTC'})`}
          />
          {endDate && (
            <div className="mt-1 text-xs text-gray-400">
              UTC: {timezoneManager.toUtcForBackend(endDate).replace('T', ' ').slice(0, 19)}
            </div>
          )}
        </div>
      </div>
      <button
        onClick={onQuery} // Dùng onQuery từ props
        disabled={isQuerying} // Vô hiệu hóa nút khi đang xử lý
        className={`w-full py-2 bg-green-600 text-white font-bold rounded ${isQuerying ? "opacity-50 cursor-not-allowed" : ""}`}
      >
        Truy vấn
      </button>
    </>
  );
};

export default TimeAndQuerySection;