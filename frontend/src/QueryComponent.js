import { useState, useEffect } from "react";
import SearchModeSelector from "./components/ui/SearchModeSelector";
import FileInputSection from "./components/query/FileInputSection";
import TextInputSection from "./components/query/TextInputSection";
import TimeAndQuerySection from "./components/query/TimeAndQuerySection";
import ResultList from "./components/result/ResultList";
import VideoCutter from "./components/result/VideoCutter"; // Thay CutVideoSection bằng VideoCutter
import ColumnSelectorModal from "./components/query/ColumnSelectorModal";
import api from "./api";

const QueryComponent = () => {
  const [searchType, setSearchType] = useState("Text");
  const [path, setPath] = useState("");
  const [startDate, setStartDate] = useState(null);
  const [endDate, setEndDate] = useState(null);
  const [results, setResults] = useState([]);
  const [selectedVideos, setSelectedVideos] = useState([]);
  const [cutVideos, setCutVideos] = useState([]);
  const [searchString, setSearchString] = useState("");
  const [defaultDays, setDefaultDays] = useState(30);
  const [fileContent, setFileContent] = useState("");
  const [trackingCodes, setTrackingCodes] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [headers, setHeaders] = useState([]);
  const [selectedColumn, setSelectedColumn] = useState("tracking_codes");
  const [history, setHistory] = useState({
    Shopee: "Mã vận đơn",
    Lazada: "Vận đơn",
    Tiktok: "QR mã vận đơn",
    Custom1: "Custom 1",
    Custom2: "Custom 2",
  });
  const [selectedPlatform, setSelectedPlatform] = useState("Shopee");
  const [shopeeLabel, setShopeeLabel] = useState("Shopee");
  const [lazadaLabel, setLazadaLabel] = useState("Lazada");
  const [tiktokLabel, setTiktokLabel] = useState("Tiktok");
  const [customLabel1, setCustomLabel1] = useState("Custom 1");
  const [customLabel2, setCustomLabel2] = useState("Custom 2");
  const [queryCount, setQueryCount] = useState(0);
  const [trackingCodeCount, setTrackingCodeCount] = useState(0);
  const [foundCount, setFoundCount] = useState(0);
  const [isQuerying, setIsQuerying] = useState(false);
  const [selectedCameras, setSelectedCameras] = useState([]);
  const [availableCameras, setAvailableCameras] = useState([]);
  const [hasQueried, setHasQueried] = useState(false);

  useEffect(() => {
    const savedHistory = localStorage.getItem("trackingColumnHistory");
    if (savedHistory) {
      setHistory(JSON.parse(savedHistory));
    }
    const savedLabels = localStorage.getItem("platformLabels");
    if (savedLabels) {
      const labels = JSON.parse(savedLabels);
      setShopeeLabel(labels.Shopee || "Shopee");
      setLazadaLabel(labels.Lazada || "Lazada");
      setTiktokLabel(labels.Tiktok || "Tiktok");
      setCustomLabel1(labels.Custom1 || "Custom 1");
      setCustomLabel2(labels.Custom2 || "Custom 2");
    }

    const isConfigSet = localStorage.getItem("configSet");
    if (isConfigSet) {
      const fetchCameras = async () => {
        try {
          const response = await api.get("/get-cameras");
          setAvailableCameras(response.data.cameras || []);
          const savedCameras = localStorage.getItem("selectedCameras");
          if (savedCameras) {
            setSelectedCameras(JSON.parse(savedCameras));
          }
        } catch (error) {
          console.error("Error fetching cameras:", error);
        }
      };
      fetchCameras();
    }
  }, []);

  useEffect(() => {
    let count = 0;
    if (searchString) {
      const lines = searchString.split("\n");
      count = lines.filter(line => line.trim() !== "" && line.split('. ')[1]?.trim()).length;
    }
    setTrackingCodeCount(count);
  }, [searchString]);

  const debounce = (func, delay) => {
    let timeoutId;
    return (...args) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func(...args), delay);
    };
  };

  const handleQuery = async () => {
    setIsQuerying(true);
    setHasQueried(true);
    try {
      const queryData = {
        search_string: searchString,
        default_days: defaultDays,
        from_time: startDate ? startDate.toISOString() : null,
        to_time: endDate ? endDate.toISOString() : null,
        selected_cameras: selectedCameras,
      };

      const response = await api.post("/query", queryData);
      const events = response.data.events || [];

      setResults(events);
      setSelectedVideos(events.map(event => event.event_id));
      setQueryCount(prev => prev + 1);
      setFoundCount(events.length);
    } catch (error) {
      console.error("Error in query:", error);
    } finally {
      setIsQuerying(false);
    }
  };

  const debouncedHandleQuery = debounce(handleQuery, 1000);

  const handleCameraSelection = (camera) => {
    const updatedCameras = selectedCameras.includes(camera)
      ? selectedCameras.filter((c) => c !== camera)
      : [...selectedCameras, camera];
    setSelectedCameras(updatedCameras);
    localStorage.setItem("selectedCameras", JSON.stringify(updatedCameras));
  };

  return (
    <div className="p-6 flex gap-6 w-screen h-screen">
      <div className="w-[26.67%] bg-gray-800 p-6 rounded-lg flex flex-col">
        <h1 className="text-3xl font-bold mb-4">Truy vấn</h1>
        <SearchModeSelector searchType={searchType} setSearchType={setSearchType} />
        {searchType === "File" && (
          <FileInputSection
            path={path}
            setPath={setPath}
            fileContent={fileContent}
            setFileContent={setFileContent}
            setShowModal={setShowModal}
            setHeaders={setHeaders}
          />
        )}
        <TextInputSection
          searchString={searchString}
          setSearchString={setSearchString}
          searchType={searchType}
        />
        <div className="mb-4">
          <label className="block mb-1">Truy vấn tại camera:</label>
          <div className="max-h-24 overflow-y-auto">
            {availableCameras.map((camera) => (
              <label key={camera} className="flex items-center mb-2">
                <input
                  type="checkbox"
                  checked={selectedCameras.includes(camera)}
                  onChange={() => handleCameraSelection(camera)}
                  className="mr-2"
                />
                {camera}
              </label>
            ))}
          </div>
        </div>
        <TimeAndQuerySection
          startDate={startDate}
          setStartDate={setStartDate}
          endDate={endDate}
          setEndDate={setEndDate}
          defaultDays={defaultDays}
          setDefaultDays={setDefaultDays}
          searchString={searchString}
          searchType={searchType}
          fileContent={fileContent}
          results={results}
          setResults={setResults}
          setSelectedVideos={setSelectedVideos}
          setQueryCount={setQueryCount}
          setFoundCount={setFoundCount}
          foundCount={foundCount}
          onQuery={debouncedHandleQuery}
          isQuerying={isQuerying}
        />
      </div>
      <div className="w-[53.33%] bg-gray-800 p-6 rounded-lg flex flex-col">
        <div className="flex items-center mb-4">
          <h1 className="text-3xl font-bold mr-4">Kết quả</h1>
          {(trackingCodeCount > 0 || foundCount > 0) && (
            <span className="text-lg text-gray-300">
              (Truy vấn {trackingCodeCount}/ Tìm được {foundCount})
            </span>
          )}
        </div>
        <ResultList
          results={results}
          selectedVideos={selectedVideos}
          setSelectedVideos={setSelectedVideos}
          hasQueried={hasQueried}
        />
        <VideoCutter
          results={results}
          selectedVideos={selectedVideos}
          setResults={setResults}
          setSelectedVideos={setSelectedVideos}
        /> {/* Thay CutVideoSection bằng VideoCutter */}
      </div>
      <ColumnSelectorModal
        showModal={showModal}
        setShowModal={setShowModal}
        headers={headers}
        selectedColumn={selectedColumn}
        setSelectedColumn={setSelectedColumn}
        history={history}
        setHistory={setHistory}
        selectedPlatform={selectedPlatform}
        setSelectedPlatform={setSelectedPlatform}
        shopeeLabel={shopeeLabel}
        setShopeeLabel={setShopeeLabel}
        lazadaLabel={lazadaLabel}
        setLazadaLabel={setLazadaLabel}
        tiktokLabel={tiktokLabel}
        setTiktokLabel={setTiktokLabel}
        customLabel1={customLabel1}
        setCustomLabel1={setCustomLabel1}
        customLabel2={customLabel2}
        setCustomLabel2={setCustomLabel2}
        path={path}
        fileContent={fileContent}
        setSearchString={setSearchString}
        setSearchType={setSearchType}
      />
    </div>
  );
};

export default QueryComponent;