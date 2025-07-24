import DatePicker from "react-datepicker";

const GeneralInfoForm = ({
  country,
  setCountry,
  timezone,
  setTimezone,
  brandName,
  setBrandName,
  workingDays,
  setWorkingDays,
  fromTime,
  setFromTime,
  toTime,
  setToTime,
  handleCountryChange,
  handleFromTimeChange,
  handleToTimeChange,
  handleWorkingDayChange,
  handleSaveGeneralInfo,
  countries,
}) => {
  return (
    <div className="w-[25%] bg-gray-800 p-6 rounded-lg flex flex-col">
      <h1 className="text-3xl font-bold mb-4">Thông tin chung</h1>
      <div className="mb-4">
        <label className="block mb-1">Quốc gia:</label>
        <select
          value={country}
          onChange={handleCountryChange}
          className="w-full p-2 rounded bg-gray-700 text-white"
        >
          {countries.map((country) => (
            <option key={country} value={country}>
              {country}
            </option>
          ))}
        </select>
      </div>
      <div className="mb-4">
        <label className="block mb-1">Múi giờ:</label>
        <input
          type="text"
          value={timezone}
          readOnly
          className="w-full p-2 rounded bg-gray-700 text-white"
        />
      </div>
      <div className="mb-4">
        <label className="block mb-1">Tên thương hiệu:</label>
        <input
          type="text"
          value={brandName}
          onChange={(e) => setBrandName(e.target.value)}
          placeholder="Nhập tên thương hiệu"
          className="w-full p-2 rounded bg-gray-700 text-white"
        />
      </div>
      <div className="mb-4">
        <h3 className="text-lg font-bold mb-2">Ngày làm việc</h3>
        {["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"].map((day) => (
          <label key={day} className="flex items-center mb-2">
            <input
              type="checkbox"
              className="mr-2"
              onChange={() => handleWorkingDayChange(day)}
              checked={workingDays.includes(day)}
            />
            {day}
          </label>
        ))}
      </div>
      <div className="mb-4">
        <h3 className="text-lg font-bold mb-2">Thời gian làm việc</h3>
        <div className="flex gap-4">
          <div className="flex-1">
            <label className="block mb-1">Từ:</label>
            <DatePicker
              selected={fromTime}
              onChange={handleFromTimeChange}
              showTimeSelect
              showTimeSelectOnly
              timeIntervals={30}
              timeCaption="Giờ"
              dateFormat="HH:mm"
              className="w-full p-2 rounded bg-gray-700 text-white"
            />
          </div>
          <div className="flex-1">
            <label className="block mb-1">Đến:</label>
            <DatePicker
              selected={toTime}
              onChange={handleToTimeChange}
              showTimeSelect
              showTimeSelectOnly
              timeIntervals={30}
              timeCaption="Giờ"
              dateFormat="HH:mm"
              className="w-full p-2 rounded bg-gray-700 text-white"
            />
          </div>
        </div>
      </div>
      <div className="mt-auto flex justify-center">
        <button
          onClick={handleSaveGeneralInfo}
          className="w-1/2 py-2 bg-blue-600 text-white font-bold rounded"
        >
          Gửi
        </button>
      </div>
    </div>
  );
};

export default GeneralInfoForm;