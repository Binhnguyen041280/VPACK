import DatePicker from "react-datepicker";
import { useState, useEffect, useRef } from "react";
import timezoneManager from "../../utils/TimezoneManager";
import TimezoneValidation from "../../utils/TimezoneValidation";
import useGlobalTimezone from "../../hooks/useGlobalTimezone";
import ct from 'countries-and-timezones';
import { DateTime } from 'luxon';

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
  const [timezones, setTimezones] = useState([]);
  const [currentTimezone, setCurrentTimezone] = useState(null);
  const [showTimezoneConfirmation, setShowTimezoneConfirmation] = useState(false);
  const [pendingTimezone, setPendingTimezone] = useState(null);
  const [validationErrors, setValidationErrors] = useState({});
  const [validationWarnings, setValidationWarnings] = useState([]);
  const [autoDetected, setAutoDetected] = useState(false);

  const [showCountryDropdown, setShowCountryDropdown] = useState(false);
  const [countrySearch, setCountrySearch] = useState('');
  const [filteredCountries, setFilteredCountries] = useState(countries);
  const countryDropdownRef = useRef(null);

  const { 
    timezoneInfo, 
    getTimezoneOffset, 
    getTimezoneIana, 
    setGlobalTimezone,
    loading: globalTimezoneLoading 
  } = useGlobalTimezone();

  const getTimezoneForCountry = (countryName) => {
    const country = Object.values(ct.getAllCountries())
      .find(c => c.name === countryName);
    return country?.timezones[0];
  };

  // Auto-detection on component mount
  useEffect(() => {
    const systemInfo = timezoneManager.getSystemDetection();
    
    // Auto-detect and set defaults if not already set
    if (!country && systemInfo.country && countries.includes(systemInfo.country)) {
      console.log(`Auto-detected country from system: ${systemInfo.country}`);
      setCountry(systemInfo.country);
      setCountrySearch(systemInfo.country);
      setAutoDetected(true);
      
      // Auto-set timezone for detected country
      const detectedTimezone = getTimezoneForCountry(systemInfo.country);
      if (detectedTimezone) {
        console.log(`Auto-setting timezone: ${detectedTimezone}`);
        timezoneManager.saveUserPreference(detectedTimezone);
        
        const tzInfo = timezoneManager.getTimezoneInfo();
        setCurrentTimezone(tzInfo);
        
        const utcOffset = DateTime.now().setZone(detectedTimezone).offsetNameShort;
        setTimezone(utcOffset);
      }
    }
  }, [countries, country, setCountry, setTimezone]);

  useEffect(() => {
    const commonTimezones = timezoneManager.getCommonTimezones();
    setTimezones(commonTimezones);
    
    if (timezoneInfo) {
      setCurrentTimezone({
        userTimezone: timezoneInfo.timezone_iana,
        systemTimezone: timezoneInfo.timezone_iana,
        currentOffset: getTimezoneOffset(),
        zoneName: timezoneInfo.timezone_display
      });
    } else {
      const tzInfo = timezoneManager.getTimezoneInfo();
      setCurrentTimezone(tzInfo);
    }
  }, [timezoneInfo, getTimezoneOffset]);

  useEffect(() => {
    const filtered = countries.filter(c => 
      c.toLowerCase().includes(countrySearch.toLowerCase())
    );
    setFilteredCountries(filtered);
  }, [countrySearch, countries]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (countryDropdownRef.current && !countryDropdownRef.current.contains(event.target)) {
        setShowCountryDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleTimezoneChange = (e) => {
    const selectedTimezone = e.target.value;
    
    if (currentTimezone && selectedTimezone !== currentTimezone.userTimezone) {
      setPendingTimezone(selectedTimezone);
      setShowTimezoneConfirmation(true);
    } else {
      applyTimezoneChange(selectedTimezone);
    }
  };

  const applyTimezoneChange = (timezoneValue) => {
    const success = timezoneManager.saveUserPreference(timezoneValue);
    if (success) {
      const tzInfo = timezoneManager.getTimezoneInfo();
      setCurrentTimezone(tzInfo);
      
      const utcOffset = DateTime.now().setZone(timezoneValue).offsetNameShort;
      setTimezone(utcOffset);
      
      const countryForTimezone = Object.values(ct.getAllCountries())
        .find(c => c.timezones.includes(timezoneValue));
      
      if (countryForTimezone && countries.includes(countryForTimezone.name)) {
        setCountry(countryForTimezone.name);
        setCountrySearch(countryForTimezone.name);
      }
    }
  };

  const handleCountrySelect = (selectedCountry) => {
    setCountry(selectedCountry);
    setCountrySearch(selectedCountry);
    setShowCountryDropdown(false);
    setAutoDetected(false); // User manually selected
    
    const primaryTimezone = getTimezoneForCountry(selectedCountry);
    
    if (primaryTimezone) {
      try {
        timezoneManager.saveUserPreference(primaryTimezone);
        const tzInfo = timezoneManager.getTimezoneInfo();
        setCurrentTimezone(tzInfo);
        
        const utcOffset = DateTime.now().setZone(primaryTimezone).offsetNameShort;
        setTimezone(utcOffset);
        
        setValidationErrors(prev => ({ ...prev, country: null, timezone: null }));
      } catch (error) {
        console.error('Error updating timezone for country:', error);
      }
    }
    
    if (handleCountryChange) {
      handleCountryChange({ target: { value: selectedCountry } });
    }
  };

  const confirmTimezoneChange = () => {
    if (pendingTimezone) {
      applyTimezoneChange(pendingTimezone);
      setPendingTimezone(null);
      setShowTimezoneConfirmation(false);
    }
  };

  const cancelTimezoneChange = () => {
    setPendingTimezone(null);
    setShowTimezoneConfirmation(false);
  };

  const validateForm = () => {
    const formData = {
      country,
      timezone: currentTimezone?.userTimezone,
      brandName,
      workingDays,
      fromTime,
      toTime
    };

    const validation = TimezoneValidation.validateGeneralInfo(formData);
    setValidationErrors(validation.fieldErrors || {});
    setValidationWarnings(validation.warnings || []);
    
    return validation.isValid;
  };

  const handleSaveWithValidation = async () => {
    if (validateForm()) {
      await handleSaveGeneralInfo();
    }
  };

  return (
    <div className="w-[25%] bg-gray-800 p-6 rounded-lg flex flex-col">
      <h1 className="text-3xl font-bold mb-4">Thông tin chung</h1>
      
      {autoDetected && (
        <div className="mb-4 p-3 bg-green-900 bg-opacity-50 border border-green-500 rounded">
          <div className="text-green-300 text-sm font-medium mb-1">🌍 Tự động nhận diện</div>
          <div className="text-green-200 text-xs">
            Quốc gia và múi giờ đã được tự động nhận diện từ hệ thống
          </div>
        </div>
      )}
      
      <div className="mb-4" ref={countryDropdownRef}>
        <label className="block mb-1">Quốc gia:</label>
        <div className="relative">
          <input
            type="text"
            value={showCountryDropdown ? countrySearch : country}
            onChange={(e) => {
              setCountrySearch(e.target.value);
              if (!showCountryDropdown) setShowCountryDropdown(true);
            }}
            onFocus={() => {
              setCountrySearch('');
              setShowCountryDropdown(true);
            }}
            placeholder="Tìm kiếm quốc gia..."
            className={`w-full p-2 rounded bg-gray-700 text-white ${validationErrors.country ? 'border-2 border-red-500' : ''}`}
          />
          
          {showCountryDropdown && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-gray-700 border border-gray-600 rounded max-h-48 overflow-y-auto z-50">
              {filteredCountries.length > 0 ? (
                filteredCountries.map((countryOption) => (
                  <div
                    key={countryOption}
                    onClick={() => handleCountrySelect(countryOption)}
                    className="p-2 hover:bg-gray-600 cursor-pointer text-white"
                  >
                    {countryOption}
                  </div>
                ))
              ) : (
                <div className="p-2 text-gray-400">Không tìm thấy quốc gia</div>
              )}
            </div>
          )}
        </div>
        {validationErrors.country && (
          <div className="mt-1 text-xs text-red-400">
            {validationErrors.country[0]}
          </div>
        )}
      </div>

      <div className="mb-4">
        <label className="block mb-1">Múi giờ:</label>
        <select
          value={currentTimezone?.userTimezone || ''}
          onChange={handleTimezoneChange}
          className={`w-full p-2 rounded bg-gray-700 text-white ${validationErrors.timezone ? 'border-2 border-red-500' : ''}`}
        >
          {timezones.map((tz) => (
            <option key={tz.value} value={tz.value}>
              {tz.label} - {tz.current}
            </option>
          ))}
        </select>
        {currentTimezone && (
          <div className="mt-1 text-xs text-gray-400">
            Hiện tại: {currentTimezone.currentOffset} • 
            {currentTimezone.isDST ? " Giờ mùa hè" : " Giờ chuẩn"}
          </div>
        )}
        {validationErrors.timezone && (
          <div className="mt-1 text-xs text-red-400">
            {validationErrors.timezone[0]}
          </div>
        )}
      </div>

      <div className="mb-4">
        <label className="block mb-1">Tên thương hiệu:</label>
        <input
          type="text"
          value={brandName}
          onChange={(e) => setBrandName(e.target.value)}
          placeholder="Nhập tên thương hiệu"
          className={`w-full p-2 rounded bg-gray-700 text-white ${validationErrors.brandName ? 'border-2 border-red-500' : ''}`}
        />
        {validationErrors.brandName && (
          <div className="mt-1 text-xs text-red-400">
            {validationErrors.brandName[0]}
          </div>
        )}
      </div>

      <div className="mb-4">
        <h3 className="text-lg font-bold mb-2">Ngày làm việc</h3>
        <div className={validationErrors.workingDays ? 'border border-red-500 rounded p-2' : ''}>
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
        {validationErrors.workingDays && (
          <div className="mt-1 text-xs text-red-400">
            {validationErrors.workingDays[0]}
          </div>
        )}
      </div>

      <div className="mb-4">
        <h3 className="text-lg font-bold mb-2">Thời gian làm việc</h3>
        <div className={`flex gap-4 ${validationErrors.timeRange ? 'border border-red-500 rounded p-2' : ''}`}>
          <div className="flex-1">
            <label className="block mb-1">
              Từ:
              <span className="text-xs text-gray-400 ml-1">
                ({currentTimezone?.currentOffset || 'UTC'})
              </span>
            </label>
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
            <label className="block mb-1">
              Đến:
              <span className="text-xs text-gray-400 ml-1">
                ({currentTimezone?.currentOffset || 'UTC'})
              </span>
            </label>
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
        {validationErrors.timeRange && (
          <div className="mt-1 text-xs text-red-400">
            {validationErrors.timeRange[0]}
          </div>
        )}
      </div>
      
      {validationWarnings.length > 0 && (
        <div className="mb-4 p-3 bg-yellow-900 bg-opacity-50 border border-yellow-500 rounded">
          <div className="text-yellow-300 text-sm font-medium mb-1">⚠️ Cảnh báo:</div>
          {validationWarnings.map((warning, index) => (
            <div key={index} className="text-yellow-200 text-xs">
              • {warning}
            </div>
          ))}
        </div>
      )}

      <div className="mt-auto flex justify-center">
        <button
          onClick={handleSaveWithValidation}
          className="w-1/2 py-2 bg-blue-600 text-white font-bold rounded hover:bg-blue-500"
        >
          Gửi
        </button>
      </div>
      
      {showTimezoneConfirmation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded-lg max-w-md w-full mx-4">
            <h3 className="text-lg font-bold mb-4">Xác nhận thay đổi múi giờ</h3>
            <p className="mb-4 text-gray-300">
              Bạn có chắc muốn thay đổi múi giờ? Điều này sẽ ảnh hưởng đến cách hiển thị thời gian trong toàn bộ ứng dụng.
            </p>
            <div className="mb-4 text-sm">
              <div className="flex justify-between">
                <span>Múi giờ hiện tại:</span>
                <span className="font-mono">
                  {currentTimezone?.userTimezone} ({currentTimezone?.currentOffset})
                </span>
              </div>
              <div className="flex justify-between mt-2">
                <span>Múi giờ mới:</span>
                <span className="font-mono">
                  {pendingTimezone} ({timezones.find(tz => tz.value === pendingTimezone)?.offset})
                </span>
              </div>
            </div>
            <div className="flex gap-3 justify-end">
              <button
                onClick={cancelTimezoneChange}
                className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-500"
              >
                Hủy
              </button>
              <button
                onClick={confirmTimezoneChange}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-500"
              >
                Xác nhận
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GeneralInfoForm;