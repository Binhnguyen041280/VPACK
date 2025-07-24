const TextInputSection = ({ searchString, setSearchString, searchType }) => {
  const handleTextInputChange = (e) => {
    const value = e.target.value;
    const lines = value.split("\n");
    const codes = [];
    
    lines.forEach(line => {
      const trimmedLine = line.trim();
      if (!trimmedLine) return;
      const match = trimmedLine.match(/^\d+\.\s*(.+)$/);
      const lineContent = match ? match[1].trim() : trimmedLine;
      const lineCodes = lineContent.split(";").map(code => code.trim()).filter(code => code);
      codes.push(...lineCodes);
    });

    let formattedCodes = codes
      .map((code, index) => `${index + 1}. ${code}`)
      .join("\n");

    if (value.endsWith("\n")) {
      formattedCodes += `\n${codes.length + 1}. `;
    }

    setSearchString(formattedCodes);
  };

  return (
    <textarea
      value={searchString}
      onChange={handleTextInputChange}
      placeholder="Nhập chuỗi tìm kiếm (mỗi mã trên một dòng)"
      className="w-full p-2 mb-4 rounded bg-gray-700 text-white h-1/2 overflow-y-auto whitespace-pre-wrap resize-none"
      disabled={searchType === "File"}
    />
  );
};

export default TextInputSection;