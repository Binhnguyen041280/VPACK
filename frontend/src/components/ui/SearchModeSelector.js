const SearchModeSelector = ({ searchType, setSearchType }) => {
  return (
    <div className="mb-4">
      <label className="block mb-1">Loại tìm kiếm:</label>
      <div className="flex gap-4">
        <label className="flex items-center">
          <input
            type="radio"
            name="searchType"
            value="File"
            className="mr-1"
            checked={searchType === "File"}
            onChange={() => setSearchType("File")}
          />
          File
        </label>
        <label className="flex items-center">
          <input
            type="radio"
            name="searchType"
            value="Text"
            className="mr-1"
            checked={searchType === "Text"}
            onChange={() => setSearchType("Text")}
          />
          Text
        </label>
      </div>
    </div>
  );
};

export default SearchModeSelector;