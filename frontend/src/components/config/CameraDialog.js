const CameraDialog = ({
  showCameraDialog,
  setShowCameraDialog,
  cameras,
  selectedCameras,
  handleCameraSelection,
  handleSaveConfig,
}) => {
  if (!showCameraDialog) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
      <div className="bg-gray-800 p-6 rounded-lg w-1/2">
        <h2 className="text-2xl font-bold mb-4 text-white">Xác nhận camera</h2>
        <div className="max-h-64 overflow-y-auto">
          {cameras.map((camera) => (
            <label key={camera.name} className="flex items-center mb-2 text-white">
              <input
                type="checkbox"
                className="mr-2"
                checked={selectedCameras.includes(camera.name)}
                onChange={() => handleCameraSelection(camera.name)}
              />
              {camera.name} ({camera.path})
            </label>
          ))}
        </div>
        <div className="mt-4 flex justify-end gap-4">
          <button
            onClick={() => setShowCameraDialog(false)}
            className="py-2 px-4 bg-gray-600 text-white font-bold rounded"
          >
            Hủy
          </button>
          <button
            onClick={handleSaveConfig}
            className="py-2 px-4 bg-blue-600 text-white font-bold rounded"
          >
            Xác nhận
          </button>
        </div>
      </div>
    </div>
  );
};
export default CameraDialog;