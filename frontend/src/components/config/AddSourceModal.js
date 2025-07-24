// components/config/AddSourceModal.js - PHASE 1 SECURITY UPDATE
import React, { useState } from 'react';
import CloudConfigurationForm from './CloudConfigurationForm';
import GoogleDriveAuthButton from './GoogleDriveAuthButton';
import CloudSyncSettings from './CloudSyncSettings';
import GoogleDriveFolderTree from './GoogleDriveFolderTree';

const AddSourceModal = ({ show, onClose, onAdd, testSourceConnection }) => {
 const [sourceType, setSourceType] = useState('local');
 const [path, setPath] = useState('');
 const [config, setConfig] = useState({});
 const [isLoading, setIsLoading] = useState(false);
 const [testResult, setTestResult] = useState(null);
 
 // 🆕 NVR-specific states
 const [nvrCameras, setNvrCameras] = useState([]);
 const [selectedNvrCameras, setSelectedNvrCameras] = useState([]);
 const [isDiscoveringCameras, setIsDiscoveringCameras] = useState(false);

 // 🆕 Cloud-specific states
 const [cloudAuthenticated, setCloudAuthenticated] = useState(false);
 const [authLoading, setAuthLoading] = useState(false);
 const [availableFolders, setAvailableFolders] = useState([]); // Keep for compatibility
 const [selectedFolders, setSelectedFolders] = useState([]); // Now handled by tree component
 const [treeFoldersSelected, setTreeFoldersSelected] = useState([]); // New: Tree selection

 const generateSourceName = (path, sourceType) => {
   if (!path) return '';
   
   if (sourceType === 'nvr') {
     // Extract hostname or IP from URL
     try {
       const url = new URL(path.startsWith('http') ? path : `http://${path}`);
       const hostname = url.hostname || path;
       return `nvr_${hostname.replace(/\./g, '_')}`;
     } catch {
       const cleanPath = path.replace(/[^\w\d]/g, '_');
       return `nvr_${cleanPath}`;
     }
   } else if (sourceType === 'cloud') {
     // Cloud source name based on selected folders
     const provider = config.provider || 'google_drive';
     const folderName = selectedFolders.length > 0 ? 'multiple_folders' : 'cloud_storage';
     return `${provider}_${folderName.replace(/[^\w\d]/g, '_')}`;
   } else {
     const folderName = path.split('/').pop() || path.split('\\').pop() || 'source';
     return `${sourceType}_${folderName}`;
   }
 };

 const resetForm = () => {
   setSourceType('local');
   setPath('');
   setConfig({});
   setTestResult(null);
   setNvrCameras([]);
   setSelectedNvrCameras([]);
   // Reset cloud states
   setCloudAuthenticated(false);
   setAvailableFolders([]);
   setSelectedFolders([]);
   setTreeFoldersSelected([]);
 };

 // 🔧 Enhanced validation for NVR (ZM credentials optional)
 const validateNvrConfig = () => {
   if (!config.url) {
     return { valid: false, message: 'Please enter NVR address first' };
   }
   
   // For ZoneMinder, credentials are optional
   if (config.protocol === 'zoneminder') {
     return { valid: true, message: 'Ready to test (ZM auth optional)' };
   }
   
   // For other protocols, credentials required
   if (!config.username || !config.password) {
     return { valid: false, message: 'Please fill in username and password for this protocol' };
   }
   
   return { valid: true, message: 'Ready to test' };
 };

 // 🔒 SECURITY: Updated Google Drive Authentication Handler with session tokens
 const handleGoogleDriveAuth = async (authResult) => {
   if (authResult.success) {
     setCloudAuthenticated(true);
     
     setConfig(prev => ({
       ...prev,
       provider: 'google_drive',
       session_token: authResult.session_token, // 🔒 SECURITY: Session token instead of credentials
       user_email: authResult.user_email
     }));

     // Store root folders for tree initialization (lazy loading enabled)
      if (authResult.lazy_loading_enabled) {
        console.log('✅ Lazy loading tree enabled');
        // Root folders will be handled by GoogleDriveFolderTree component
      } else if (authResult.folders && authResult.folders.length > 0) {
        setAvailableFolders(authResult.folders);
      }
     
   }
 };

 // 🆕 Folder Selection Handler
 const handleFolderToggle = (folder) => {
   setSelectedFolders(prev => {
     const isSelected = prev.some(f => f.id === folder.id);
     if (isSelected) {
       return prev.filter(f => f.id !== folder.id);
     } else {
       return [...prev, folder];
     }
   });
 };

 // 🆕 Select All/None Handlers
 const handleSelectAllFolders = () => {
   setSelectedFolders([...availableFolders]);
 };

 const handleDeselectAllFolders = () => {
   setSelectedFolders([]);
 };

 const handleTreeFolderSelection = (selectedTreeFolders) => {
  setTreeFoldersSelected(selectedTreeFolders);
  console.log(`📁 Tree selection updated: ${selectedTreeFolders.length} folders`);
 };

 // 🆕 Cloud Sync Settings Handler
 const handleCloudSyncSettings = (syncConfig) => {
   setConfig(prev => ({
     ...prev,
     sync_settings: syncConfig
   }));
 };

 const handleTestConnection = async () => {
   if (sourceType === 'local' && !path) {
     alert('Please enter a path first');
     return;
   }

   if (sourceType === 'nvr') {
     const validation = validateNvrConfig();
     if (!validation.valid) {
       alert(validation.message);
       return;
     }
   }

   setIsLoading(true);
   setIsDiscoveringCameras(true);
   setTestResult(null);
   setNvrCameras([]);
   
   try {
     const testData = {
       source_type: sourceType,
       path: sourceType === 'local' ? path : config.url,
       config: sourceType === 'nvr' ? {
         ...config,
         protocol: config.protocol || 'zoneminder',
         username: config.username || '',
         password: config.password || ''
       } : config
     };

     const response = await testSourceConnection(testData);
     
     setTestResult({
       success: response.accessible,
       message: response.message
     });

     // Handle NVR camera discovery
     if (response.accessible && sourceType === 'nvr' && response.cameras) {
       setNvrCameras(response.cameras);
       setSelectedNvrCameras(response.cameras.map(cam => cam.name || cam.id || `Camera ${response.cameras.indexOf(cam) + 1}`));
       
       setTestResult(prev => ({
         ...prev,
         message: `${prev.message} - Found ${response.cameras.length} camera(s)`
       }));
     }
     
   } catch (error) {
     setTestResult({
       success: false,
       message: error.message || 'Connection test failed'
     });
   } finally {
     setIsLoading(false);
     setIsDiscoveringCameras(false);
   }
 };

 // NVR Camera Selection Handler
 const handleNvrCameraToggle = (cameraName) => {
   setSelectedNvrCameras(prev => 
     prev.includes(cameraName) 
       ? prev.filter(name => name !== cameraName)
       : [...prev, cameraName]
   );
 };

 const handleSubmit = (e) => {
   e.preventDefault();
   
   if (sourceType === 'local' && !path) {
     alert('Please enter a path');
     return;
   }
   
   if (sourceType === 'nvr') {
     const validation = validateNvrConfig();
     if (!validation.valid) {
       alert(validation.message);
       return;
     }
   }

   // 🆕 Cloud submission validation - SIMPLIFIED
   if (sourceType === 'cloud') {
     if (!cloudAuthenticated) {
       alert('Please authenticate with Google Drive first');
       return;
     }
     if (treeFoldersSelected.length === 0) {
       alert('Please select at least one folder to monitor');
       return;
     }
   }

   const autoName = generateSourceName(
     sourceType === 'local' ? path : 
     sourceType === 'cloud' ? `google_drive://selected_folders` :
     config.url || 'nvr', 
     sourceType
   );

   const newSource = {
     source_type: sourceType,
     name: autoName,
     path: sourceType === 'local' ? path : 
           sourceType === 'cloud' ? `google_drive://selected_folders` :
           config.url,
     config: sourceType === 'nvr' ? {
       ...config,
       protocol: config.protocol || 'zoneminder',
       username: config.username || '',
       password: config.password || '',
       detected_cameras: nvrCameras,
       selected_cameras: selectedNvrCameras
     } : sourceType === 'cloud' ? {
       ...config,
       provider: 'google_drive',
       selected_folders: [...selectedFolders, ...treeFoldersSelected], // Combine both selections
       selected_tree_folders: treeFoldersSelected, // Store tree selections separately
       legacy_folders: selectedFolders, // Keep legacy for compatibility
       sync_settings: config.sync_settings || {
         interval_minutes: 15,
         auto_sync_enabled: true,
         sync_only_new: true,
         skip_duplicates: true
       }
     } : {}
   };

   onAdd(newSource);
   resetForm();
   onClose();
 };

 if (!show) return null;

 return (
   <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
     <div className="bg-gray-800 rounded-lg p-6 w-full max-w-4xl mx-4 max-h-[90vh] overflow-y-auto">
       <div className="flex justify-between items-center mb-6">
         <h3 className="text-xl font-bold text-white">Add New Video Source</h3>
         <button
           onClick={onClose}
           className="text-gray-400 hover:text-white text-2xl"
         >
           ×
         </button>
       </div>

       <form onSubmit={handleSubmit}>
         {/* Source Type Cards */}
         <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
           
           {/* Local Storage Card */}
           <div 
             className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
               sourceType === 'local' 
                 ? 'border-blue-500 bg-blue-900' 
                 : 'border-gray-600 bg-gray-700 hover:border-gray-500'
             }`}
             onClick={() => setSourceType('local')}
           >
             <div className="flex items-center mb-3">
               <span className="text-3xl mr-3">📁</span>
               <div>
                 <h4 className="font-semibold text-white text-lg">Browse Files Directly</h4>
                 <p className="text-sm text-gray-300">Access folders containing videos</p>
               </div>
             </div>
             <div className="text-xs text-gray-400 leading-relaxed">
               • Local server folders<br/>
               • Mounted network drives (NAS, SMB, NFS)<br/>
               • Mounted NVR file shares<br/>
               • Any accessible folder path<br/>
               <span className="text-yellow-300 font-medium">📍 Mount network sources first</span>
             </div>
           </div>

           {/* NVR/DVR Card */}
           <div 
             className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
               sourceType === 'nvr' 
                 ? 'border-blue-500 bg-blue-900' 
                 : 'border-gray-600 bg-gray-700 hover:border-gray-500'
             }`}
             onClick={() => setSourceType('nvr')}
           >
             <div className="flex items-center mb-3">
               <span className="text-3xl mr-3">🔗</span>
               <div>
                 <h4 className="font-semibold text-white text-lg">Connect & Auto-Download</h4>
                 <p className="text-sm text-gray-300">Direct NVR/DVR camera discovery</p>
               </div>
             </div>
             <div className="text-xs text-gray-400 leading-relaxed">
               • NVR/DVR systems (ONVIF)<br/>
               • IP Camera networks (RTSP)<br/>
               • Security management platforms<br/>
               • Auto-discover cameras<br/>
               <span className="text-green-300 font-medium">🔄 Real-time camera detection</span>
             </div>
           </div>

           {/* 🆕 Cloud Storage Card - SIMPLIFIED */}
           <div 
             className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
               sourceType === 'cloud' 
                 ? 'border-blue-500 bg-blue-900' 
                 : 'border-gray-600 bg-gray-700 hover:border-gray-500'
             }`}
             onClick={() => setSourceType('cloud')}
           >
             <div className="flex items-center mb-3">
               <span className="text-3xl mr-3">☁️</span>
               <div>
                 <h4 className="font-semibold text-white text-lg">Google Drive Integration</h4>
                 <p className="text-sm text-gray-300">Sync videos from cloud storage</p>
               </div>
             </div>
             <div className="text-xs text-gray-400 leading-relaxed">
               • Google Drive camera folders<br/>
               • Auto-sync new recordings<br/>
               • Simple folder selection<br/>
               • Background download to server<br/>
               <span className="text-green-300 font-medium">✅ Simplified & Reliable!</span>
             </div>
           </div>
         </div>

         {/* Local Files Form */}
         {sourceType === 'local' && (
           <div className="bg-gray-700 rounded-lg p-6 mb-6">
             <h4 className="font-semibold text-white mb-4 text-lg">📁 Browse Files Directly Configuration</h4>
             
             <div className="bg-yellow-800 border border-yellow-600 rounded-lg p-4 mb-6">
               <div className="text-yellow-200">
                 <div className="font-semibold mb-2">📍 Network Storage Setup Guide:</div>
                 <div className="text-sm mb-2">For network sources (NAS, NVR file shares), mount them first:</div>
                 <div className="font-mono text-xs bg-black bg-opacity-30 p-2 rounded">
                   # SMB Example (NAS/NVR):<br/>
                   mount -t smbfs //server/share /mnt/folder<br/><br/>
                   # NFS Example:<br/>
                   mount -t nfs server:/export /mnt/folder
                 </div>
               </div>
             </div>

             <div className="mb-4">
               <label className="block text-sm font-medium text-gray-300 mb-2">
                 Folder Path *
               </label>
               <input
                 type="text"
                 value={path}
                 onChange={(e) => setPath(e.target.value)}
                 placeholder="/Users/videos or /mnt/nas-storage or /mnt/nvr-files"
                 className="w-full p-3 border border-gray-600 rounded-lg bg-gray-800 text-white text-sm"
                 required
               />
               <div className="text-xs text-gray-400 mt-2">
                 Local path or mounted network folder containing camera subfolders
               </div>
             </div>

             {path && (
               <div className="bg-gray-600 p-4 rounded-lg">
                 <div className="text-xs text-gray-400 mb-1">Auto-generated source name:</div>
                 <div className="text-lg text-white font-medium">{generateSourceName(path, sourceType)}</div>
               </div>
             )}
           </div>
         )}

         {/* NVR/DVR Form */}
         {sourceType === 'nvr' && (
           <div className="bg-gray-700 rounded-lg p-6 mb-6">
             <h4 className="font-semibold text-white mb-4 text-lg">🔗 NVR/DVR Connection Configuration</h4>

             {/* Protocol & URL Row */}
             <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
               <div>
                 <label className="block text-sm font-medium text-gray-300 mb-2">
                   Protocol *
                 </label>
                 <select
                   value={config.protocol || 'zoneminder'}
                   onChange={(e) => setConfig(prev => ({...prev, protocol: e.target.value}))}
                   className="w-full p-3 border border-gray-600 rounded-lg bg-gray-800 text-white"
                   required
                 >
                   <option value="zoneminder">ZoneMinder API (Open Source NVR)</option>
                   <option value="onvif">ONVIF (Universal Standard)</option>
                   <option value="rtsp">RTSP Direct Stream</option>
                   <option value="hikvision">Hikvision API</option>
                   <option value="dahua">Dahua API</option>
                   <option value="generic">Generic HTTP API</option>
                 </select>
               </div>

               <div>
                 <label className="block text-sm font-medium text-gray-300 mb-2">
                   NVR/DVR Address *
                 </label>
                 <input
                   type="text"
                   value={config.url || ''}
                   onChange={(e) => setConfig(prev => ({...prev, url: e.target.value}))}
                   placeholder="localhost:5050 or 192.168.1.100:8080"
                   className="w-full p-3 border border-gray-600 rounded-lg bg-gray-800 text-white"
                   required
                 />
               </div>
             </div>

             {/* Credentials Section */}
             <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
               <div>
                 <label className="block text-sm font-medium text-gray-300 mb-2">
                   Username {config.protocol === 'zoneminder' ? '(Optional)' : '*'}
                 </label>
                 <input
                   type="text"
                   value={config.username || ''}
                   onChange={(e) => setConfig(prev => ({...prev, username: e.target.value}))}
                   placeholder={config.protocol === 'zoneminder' ? 'admin (leave blank if no auth)' : 'admin'}
                   className="w-full p-3 border border-gray-600 rounded-lg bg-gray-800 text-white"
                   required={config.protocol !== 'zoneminder'}
                 />
               </div>

               <div>
                 <label className="block text-sm font-medium text-gray-300 mb-2">
                   Password {config.protocol === 'zoneminder' ? '(Optional)' : '*'}
                 </label>
                 <input
                   type="password"
                   value={config.password || ''}
                   onChange={(e) => setConfig(prev => ({...prev, password: e.target.value}))}
                   placeholder={config.protocol === 'zoneminder' ? '••••••••  (leave blank if no auth)' : '••••••••'}
                   className="w-full p-3 border border-gray-600 rounded-lg bg-gray-800 text-white"
                   required={config.protocol !== 'zoneminder'}
                 />
               </div>
             </div>

             {/* Discovered Cameras Section */}
             {testResult?.success && nvrCameras.length > 0 && (
               <div className="mb-6">
                 <div className="flex items-center justify-between mb-3">
                   <h5 className="font-medium text-white">📹 Discovered Cameras ({nvrCameras.length})</h5>
                 </div>
                 <div className="flex gap-2 mb-2">
                   <button
                     type="button"
                     onClick={() => setSelectedNvrCameras(nvrCameras.map(cam => cam.name || cam.id || `Camera ${nvrCameras.indexOf(cam) + 1}`))}
                     className="px-3 py-1 bg-blue-600 text-white rounded text-xs"
                   >
                     Select All
                   </button>
                   <button
                     type="button"
                     onClick={() => setSelectedNvrCameras([])}
                     className="px-3 py-1 bg-gray-600 text-white rounded text-xs"
                   >
                     Deselect All
                   </button>
                 </div>
                 
                 <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 p-4 bg-gray-600 rounded-lg max-h-48 overflow-y-auto">
                   {nvrCameras.map((camera, index) => {
                     const cameraName = camera.name || camera.id || `Camera ${index + 1}`;
                     
                     return (
                       <label 
                         key={cameraName}
                         className="flex items-start space-x-3 p-2 bg-gray-700 rounded cursor-pointer hover:bg-gray-650"
                       >
                         <input
                           type="checkbox"
                           checked={selectedNvrCameras.includes(cameraName)}
                           onChange={() => handleNvrCameraToggle(cameraName)}
                           className="mt-1"
                         />
                         <div className="flex-1 min-w-0">
                           <div className="text-white text-sm font-medium truncate">
                             {cameraName}
                           </div>
                           {camera.stream_url && (
                             <div className="text-xs text-gray-400 truncate">
                               Stream: {camera.stream_url}
                             </div>
                           )}
                         </div>
                       </label>
                     );
                   })}
                 </div>
               </div>
             )}

             {/* Source Name Preview */}
             {config.url && (
               <div className="bg-gray-600 p-4 rounded-lg">
                 <div className="text-xs text-gray-400 mb-1">Auto-generated source name:</div>
                 <div className="text-lg text-white font-medium">{generateSourceName(config.url, sourceType)}</div>
               </div>
             )}
           </div>
         )}

         {/* 🆕 Cloud Storage Form - SIMPLIFIED */}
         {sourceType === 'cloud' && (
           <div className="bg-gray-700 rounded-lg p-6 mb-6">
             <h4 className="font-semibold text-white mb-4 text-lg">☁️ Google Drive Integration Configuration</h4>
             
             {/* Step 1: Authentication */}
             <div className="mb-6">
               <h5 className="font-medium text-white mb-3">Step 1: Authenticate with Google Drive</h5>
               <GoogleDriveAuthButton 
                 onAuth={handleGoogleDriveAuth}
                 isAuthenticated={cloudAuthenticated}
                 isLoading={authLoading}
                 userEmail={config?.user_email}
               />
             </div>

              {/* Step 2: Folder Selection */}
              {cloudAuthenticated && (
                <div className="mb-6">
                  <h5 className="font-medium text-white mb-3">Step 2: Navigate & Select Camera Folders</h5>
                  
                  <GoogleDriveFolderTree
                    session_token={config?.session_token}
                    onFoldersSelected={handleTreeFolderSelection}
                    maxDepth={4}
                    selectableDepth={4}
                    className="border border-gray-600 rounded-lg"
                  />
                </div>
              )}

             {/* Step 3: Sync Settings */}
             {cloudAuthenticated && treeFoldersSelected.length > 0 && (
               <div className="mb-6">
                 <h5 className="font-medium text-white mb-3">Step 3: Configure Sync Settings</h5>
                 <CloudSyncSettings
                   config={config.sync_settings || {
                     interval_minutes: 15,
                     auto_sync_enabled: true,
                     sync_only_new: true,
                     skip_duplicates: true
                   }}
                   onChange={handleCloudSyncSettings}
                 />
               </div>
             )}

             {/* Source Name Preview */}
             {treeFoldersSelected.length > 0 && (
               <div className="bg-gray-600 p-4 rounded-lg">
                 <div className="text-xs text-gray-400 mb-1">Auto-generated source name:</div>
                 <div className="text-lg text-white font-medium">{generateSourceName(`google_drive://selected_folders`, sourceType)}</div>
                 <div className="text-xs text-gray-400 mt-2">
                    {treeFoldersSelected.length} folders selected for monitoring
                  </div>
               </div>
             )}
           </div>
         )}

         {/* Test Connection - CHỈ CHO LOCAL/NVR */}
         {(sourceType === 'local' || sourceType === 'nvr') && (
           <div className="mb-6">
             <button
               type="button"
               onClick={handleTestConnection}
               disabled={isLoading || 
                 (sourceType === 'local' && !path) || 
                 (sourceType === 'nvr' && !validateNvrConfig().valid)
               }
               className="bg-yellow-600 hover:bg-yellow-700 disabled:bg-gray-600 text-white px-6 py-3 rounded-lg font-medium mr-4"
             >
               {isLoading ? (
                 <span className="flex items-center">
                   <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                     <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                     <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                   </svg>
                   {sourceType === 'nvr' ? 'Discovering Cameras...' : 'Testing...'}
                 </span>
               ) : (
                 'Test Connection'
               )}
             </button>
             
             {testResult && (
               <div className={`inline-block p-4 rounded-lg text-sm ${
                 testResult.success 
                   ? 'bg-green-800 text-green-200 border border-green-600' 
                   : 'bg-red-800 text-red-200 border border-red-600'
               }`}>
                 <div className="font-medium mb-1">
                   {testResult.success ? '✅ Connection Successful' : '❌ Connection Failed'}
                 </div>
                 <div>{testResult.message}</div>
               </div>
             )}
           </div>
         )}

         {/* Action Buttons - UPDATED CONDITIONS */}
         <div className="flex gap-4 pt-4 border-t border-gray-600">
           <button
             type="submit"
             disabled={
               (sourceType === 'local' && !path) ||
               (sourceType === 'nvr' && !testResult?.success) ||
               (sourceType === 'cloud' && (!cloudAuthenticated || treeFoldersSelected.length === 0))
             }
             className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-8 py-3 rounded-lg font-medium flex-1"
           >
             Add Source
           </button>
           <button
             type="button"
             onClick={() => {
               resetForm();
               onClose();
             }}
             className="bg-gray-600 hover:bg-gray-700 text-white px-8 py-3 rounded-lg font-medium flex-1"
           >
             Cancel
           </button>
         </div>
       </form>
     </div>
   </div>
 );
};

export default AddSourceModal;