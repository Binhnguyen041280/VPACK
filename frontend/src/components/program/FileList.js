const FileList = ({ fileList }) => {
  if (!fileList || fileList.length === 0) {
    return (
      <div className="mt-4">
        <h3 className="text-lg font-bold">Kết quả:</h3>
        <p>Không có file nào để hiển thị.</p>
      </div>
    );
  }

  return (
    <div className="mt-4">
      <h3 className="text-lg font-bold">Kết quả:</h3>
      <ul className="list-disc pl-5">
        {fileList.map((item, index) => (
          <li key={index}>{`${item.file}: ${item.status}`}</li>
        ))}
      </ul>
    </div>
  );
};

export default FileList;