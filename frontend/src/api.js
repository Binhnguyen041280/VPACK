import axios from "axios";
import apiTimezoneMiddleware from "./utils/ApiTimezoneMiddleware";

// Create axios instance with timezone middleware
const api = axios.create({
  baseURL: "http://localhost:8080",
});

// Add timezone headers to all requests
api.interceptors.request.use(
  (config) => {
    // Add timezone headers
    config.headers = apiTimezoneMiddleware.addTimezoneHeaders(config.headers);
    
    // Convert request data to UTC if it contains time fields
    if (config.data && typeof config.data === 'object') {
      config.data = apiTimezoneMiddleware.convertRequestToUtc(config.data);
    }
    
    // Add timezone info to URL params if needed
    if (config.params && typeof config.params === 'object') {
      config.params = apiTimezoneMiddleware.convertRequestToUtc(config.params);
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(apiTimezoneMiddleware.enhanceError(error, 'request-interceptor'));
  }
);

// Add timezone conversion to all responses
api.interceptors.response.use(
  (response) => {
    // Convert response data to local timezone
    if (response.data && typeof response.data === 'object') {
      response.data = apiTimezoneMiddleware.convertResponseToLocal(response.data);
    }
    
    return response;
  },
  (error) => {
    // Check if this is a timezone-related error that should trigger retry
    if (error.response && apiTimezoneMiddleware.isTimezoneError(error.response)) {
      console.warn('Timezone-related API error detected:', error.response.status);
    }
    
    return Promise.reject(apiTimezoneMiddleware.enhanceError(
      error, 
      error.config?.url || 'unknown',
      error.config
    ));
  }
);

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