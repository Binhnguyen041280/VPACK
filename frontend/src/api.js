import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8080",
});

export const getConfig = () => api.get("/config");
export const updateConfig = (configData) => api.post("/config", configData);
export const runQuery = (queryData) => api.post("/query", queryData);
export const runProgram = (programData) => api.post("/program", programData);
export const confirmRun = (confirmData) => api.post("/confirm-run", confirmData);
export const getCameras = () => api.get("/get-cameras");
export const cutVideos = (cutData) => api.post("/cut-videos", cutData);
export const analyzeRegions = (data) => api.post("/analyze-regions", data);
export const getFrames = (data) => api.post("/get-frames", data);
export const submitRois = (data) => api.post("/submit-rois", data);
export const sendHandDetection = (data) => api.post("/api/hand-detection", data);
export const getRoiFrame = () => api.get("/get-roi-frame");
export const getFinalRoiFrame = (cameraId, timestamp) => api.get(`/get-final-roi-frame?camera_id=${cameraId}&timestamp=${timestamp}`);

// Video Sources APIs
export const getSources = () => api.get("/get-sources");
export const addSources = (sourcesData) => api.post("/save-sources", sourcesData);
export const testSourceConnection = (sourceData) => api.post("/test-source", sourceData);
export const updateSource = (id, sourceData) => api.put(`/update-source/${id}`, sourceData);
export const deleteSource = (id) => api.delete(`/delete-source/${id}`);
export const toggleSource = (id, active) => api.post(`/toggle-source/${id}`, { active });

// NEW: Camera Detection APIs
export const detectCameras = (pathData) => api.post("/detect-cameras", pathData);
export const updateSourceCameras = (cameraData) => api.post("/update-source-cameras", cameraData);

export default api;