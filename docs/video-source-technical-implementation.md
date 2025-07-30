# Technical Implementation Guide - Video Source Configuration

## Current Implementation Status

### ✅ Implemented Sources
1. **Local File System** - 100% Complete
2. **Google Drive Cloud** - 98% Complete  
3. **Camera/NVR** - Backend 85% (Frontend pending)

## Frontend Configuration Components

### 1. AddSourceModal.js Enhancement for Camera Support

```javascript
// Add Camera/NVR option to source type selection
{/* Camera/NVR Card - TO BE ADDED */}
<div 
  className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
    sourceType === 'camera' 
      ? 'border-blue-500 bg-blue-900' 
      : 'border-gray-600 bg-gray-700 hover:border-gray-500'
  }`}
  onClick={() => setSourceType('camera')}
>
  <div className="flex items-center mb-3">
    <span className="text-3xl mr-3">📹</span>
    <div>
      <h4 className="font-semibold text-white text-lg">IP Camera / NVR System</h4>
      <p className="text-sm text-gray-300">Connect to ONVIF cameras or NVR</p>
    </div>
  </div>
  <div className="text-xs text-gray-400 leading-relaxed">
    • ONVIF compatible IP cameras<br/>
    • ZoneMinder NVR systems<br/>
    • Multi-camera discovery<br/>
    • Real-time streaming ready<br/>
    <span className="text-blue-300 font-medium">🎥 Direct camera access</span>
  </div>
</div>

// Camera configuration form
{sourceType === 'camera' && (
  <div className="bg-gray-700 rounded-lg p-6 mb-6">
    <h4 className="font-semibold text-white mb-4 text-lg">📹 Camera/NVR Configuration</h4>
    
    {/* Protocol Selection */}
    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-300 mb-2">
        Protocol Type *
      </label>
      <select
        value={config.protocol || 'onvif'}
        onChange={(e) => setConfig({...config, protocol: e.target.value})}
        className="w-full p-3 border border-gray-600 rounded-lg bg-gray-800 text-white"
      >
        <option value="onvif">ONVIF Camera</option>
        <option value="zoneminder">ZoneMinder NVR</option>
      </select>
    </div>

    {/* Connection Details */}
    <div className="grid grid-cols-2 gap-4 mb-4">
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          IP Address *
        </label>
        <input
          type="text"
          value={config.ip || ''}
          onChange={(e) => setConfig({...config, ip: e.target.value})}
          placeholder="192.168.1.100"
          className="w-full p-3 border border-gray-600 rounded-lg bg-gray-800 text-white"
          required
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Port
        </label>
        <input
          type="number"
          value={config.port || (config.protocol === 'onvif' ? 80 : 443)}
          onChange={(e) => setConfig({...config, port: parseInt(e.target.value)})}
          className="w-full p-3 border border-gray-600 rounded-lg bg-gray-800 text-white"
        />
      </div>
    </div>

    {/* Credentials */}
    <div className="grid grid-cols-2 gap-4 mb-4">
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Username
        </label>
        <input
          type="text"
          value={config.username || ''}
          onChange={(e) => setConfig({...config, username: e.target.value})}
          className="w-full p-3 border border-gray-600 rounded-lg bg-gray-800 text-white"
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Password
        </label>
        <input
          type="password"
          value={config.password || ''}
          onChange={(e) => setConfig({...config, password: e.target.value})}
          className="w-full p-3 border border-gray-600 rounded-lg bg-gray-800 text-white"
        />
      </div>
    </div>

    {/* Discovered Cameras */}
    {discoveredCameras.length > 0 && (
      <div className="bg-gray-600 p-4 rounded-lg">
        <h5 className="font-medium text-white mb-2">Discovered Cameras:</h5>
        <div className="space-y-2">
          {discoveredCameras.map((camera, idx) => (
            <label key={idx} className="flex items-center text-sm text-gray-200">
              <input
                type="checkbox"
                checked={selectedCameraIds.includes(camera.id)}
                onChange={() => handleCameraToggle(camera.id)}
                className="mr-2"
              />
              {camera.name} - {camera.info}
            </label>
          ))}
        </div>
      </div>
    )}
  </div>
)}
```

### 2. Backend API Integration for Cameras

```javascript
// api.js - Add camera-specific API calls

// Test camera connection and discover
export const testCameraConnection = async (connectionData) => {
  const response = await fetch(`${API_BASE_URL}/config/test-source`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source_type: 'camera',
      path: `${connectionData.protocol}://${connectionData.ip}:${connectionData.port}`,
      config: connectionData
    })
  });
  return response.json();
};

// Start/stop camera recording
export const controlCameraRecording = async (sourceId, action) => {
  const response = await fetch(`${API_BASE_URL}/camera/control`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      source_id: sourceId,
      action: action // 'start', 'stop', 'snapshot'
    })
  });
  return response.json();
};

// Get camera stream URL
export const getCameraStreamUrl = async (sourceId, cameraId) => {
  const response = await fetch(`${API_BASE_URL}/camera/stream/${sourceId}/${cameraId}`);
  return response.json();
};
```

## Backend Configuration Details

### 1. Camera Source Handler Pattern

```python
# backend/modules/sources/camera_source_handler.py

class CameraSourceHandler:
    def __init__(self):
        self.onvif_client = VTrackOnvifClient()
        self.nvr_client = NVRClient()
        self.active_connections = {}
        
    def connect_source(self, source_config):
        """Connect to camera source based on protocol"""
        protocol = source_config.get('protocol')
        
        if protocol == 'onvif':
            return self._connect_onvif(source_config)
        elif protocol == 'zoneminder':
            return self._connect_zoneminder(source_config)
        else:
            raise ValueError(f"Unsupported protocol: {protocol}")
            
    def _connect_onvif(self, config):
        """Connect to ONVIF camera(s)"""
        result = self.onvif_client.test_device_connection(
            ip=config['ip'],
            port=config.get('port', 80),
            username=config.get('username', ''),
            password=config.get('password', '')
        )
        
        if result['accessible']:
            # Store connection for later use
            connection_id = f"onvif_{config['ip']}"
            self.active_connections[connection_id] = {
                'client': self.onvif_client,
                'config': config,
                'cameras': result['cameras']
            }
            
        return result
        
    def _connect_zoneminder(self, config):
        """Connect to ZoneMinder NVR"""
        # Parse URL to get base_url
        parsed = urlparse(config['path'])
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        result = self.nvr_client.test_nvr_connection(
            config={
                'nvr_type': 'zoneminder',
                'url': base_url,
                'username': config.get('username'),
                'password': config.get('password')
            }
        )
        
        return result
        
    def start_recording(self, source_id, camera_ids=None):
        """Start recording from camera source"""
        # Implementation for recording logic
        pass
        
    def get_stream_url(self, source_id, camera_id):
        """Get RTSP/HTTP stream URL for camera"""
        # Implementation for stream URL generation
        pass
```

### 2. Database Schema Extensions

```sql
-- Add camera-specific tables

-- Camera configurations
CREATE TABLE camera_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    camera_id TEXT NOT NULL,
    camera_name TEXT,
    stream_url TEXT,
    snapshot_url TEXT,
    ptz_capable INTEGER DEFAULT 0,
    audio_capable INTEGER DEFAULT 0,
    resolution TEXT,
    fps INTEGER,
    codec TEXT,
    FOREIGN KEY (source_id) REFERENCES video_sources(id),
    UNIQUE(source_id, camera_id)
);

-- Recording schedules
CREATE TABLE recording_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    camera_id TEXT,
    schedule_type TEXT, -- 'continuous', 'motion', 'scheduled'
    start_time TIME,
    end_time TIME,
    days_of_week TEXT, -- JSON array
    enabled INTEGER DEFAULT 1,
    FOREIGN KEY (source_id) REFERENCES video_sources(id)
);

-- Camera events/alerts
CREATE TABLE camera_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    camera_id TEXT NOT NULL,
    event_type TEXT, -- 'motion', 'connection_lost', 'recording_started'
    event_data TEXT, -- JSON
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES video_sources(id)
);
```

### 3. Configuration File Structure

```yaml
# config/camera_sources.yaml

# ONVIF camera defaults
onvif:
  default_port: 80
  discovery_timeout: 5
  stream_protocols: ['rtsp', 'http']
  authentication_methods: ['digest', 'basic']
  
# NVR system configs  
nvr:
  zoneminder:
    api_version: 'v1'
    default_port: 443
    use_https: true
    api_endpoints:
      login: '/api/host/login.json'
      monitors: '/api/monitors.json'
      events: '/api/events.json'
      
# Recording settings
recording:
  default_format: 'mp4'
  segment_duration: 600  # 10 minutes
  retention_days: 30
  storage_path: 'nvr_downloads'
  
# Stream settings
streaming:
  rtsp_transport: 'tcp'  # tcp, udp, http
  buffer_size: 1048576  # 1MB
  reconnect_delay: 5
  max_reconnect_attempts: 3
```

### 4. Environment Configuration

```bash
# .env file additions

# Camera source settings
CAMERA_DISCOVERY_ENABLED=true
CAMERA_DISCOVERY_TIMEOUT=10
CAMERA_MAX_CONNECTIONS=50

# ONVIF settings
ONVIF_DISCOVERY_MULTICAST=true
ONVIF_DISCOVERY_BROADCAST=true
ONVIF_USER_AGENT="VTrack/1.0"

# NVR settings  
NVR_CONNECTION_POOL_SIZE=10
NVR_REQUEST_TIMEOUT=30
NVR_VERIFY_SSL=false

# Recording settings
RECORDING_STORAGE_PATH="/opt/vtrack/nvr_downloads"
RECORDING_SEGMENT_DURATION=600
RECORDING_MAX_FILE_SIZE=1073741824  # 1GB

# Stream proxy settings
STREAM_PROXY_ENABLED=false
STREAM_PROXY_PORT=8554
STREAM_PROXY_PROTOCOL="rtsp"
```

## Implementation Roadmap

### Phase 1: Basic Camera Integration (Current)
- [x] ONVIF client implementation
- [x] ZoneMinder NVR client
- [x] Basic authentication
- [x] Camera discovery
- [ ] Frontend UI for camera sources
- [ ] Basic recording to disk

### Phase 2: Advanced Features
- [ ] Real-time streaming proxy
- [ ] PTZ (Pan-Tilt-Zoom) control
- [ ] Motion detection integration
- [ ] Event-based recording
- [ ] Camera health monitoring
- [ ] Bandwidth management

### Phase 3: Enterprise Features
- [ ] Multi-site support
- [ ] Failover/redundancy
- [ ] Advanced analytics integration
- [ ] Cloud backup for recordings
- [ ] Mobile app support
- [ ] AI-powered alerts

## Testing Configuration

```python
# Test camera connections
def test_camera_configurations():
    test_configs = [
        {
            'name': 'ONVIF Test Camera',
            'source_type': 'camera',
            'config': {
                'protocol': 'onvif',
                'ip': '192.168.1.100',
                'port': 80,
                'username': 'admin',
                'password': 'admin123'
            }
        },
        {
            'name': 'ZoneMinder Test',
            'source_type': 'camera', 
            'config': {
                'protocol': 'zoneminder',
                'url': 'https://192.168.1.200/zm',
                'username': 'admin',
                'password': 'zmpass'
            }
        }
    ]
    
    for config in test_configs:
        result = test_source_connection(config)
        print(f"{config['name']}: {result}")
```

This technical guide provides the foundation for extending VTrack's video source configuration to support direct camera integration while maintaining compatibility with existing local and cloud sources.