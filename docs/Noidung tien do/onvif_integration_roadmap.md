# 🔗 VTrack ONVIF Integration Roadmap

## 🎯 Mục tiêu tổng quan
Tích hợp ONVIF Camera Mock đã có sẵn vào tab **Cấu hình** của VTrack để hỗ trợ phát hiện và quản lý camera ONVIF tự động.

---

## 📋 Hiện trạng phân tích

### ✅ ONVIF Mock đã sẵn sàng
- **Container**: `onvif-mock-fixed` (IP: 172.17.0.2)
- **Services hoạt động**:
  - Port 1000: ONVIF Device & Media Services
  - Port 3702: WS-Discovery Service  
  - Port 8554: RTSP Stream
- **Test thành công**: GetDeviceInformation, GetCapabilities, GetProfiles

### ✅ Frontend Architecture hiện tại
- **NVR Support**: Đã có trong `AddSourceModal.js` và `ConfigForm.js`
- **Source Types**: Local, NVR, Cloud (NVR đã implement cơ bản)
- **Camera Discovery**: API `/detect-cameras` và `/test-source` đã có
- **Authentication**: ZoneMinder và ONVIF protocols đã support

---

## 🚀 Phase 1: ONVIF Backend Integration (Week 1-2)

### 1.1 Backend API Enhancement
```python
# backend/app.py - Thêm ONVIF endpoints
@app.route('/onvif/discover', methods=['POST'])
def discover_onvif_devices():
    """Scan network for ONVIF devices using WS-Discovery"""
    
@app.route('/onvif/device-info', methods=['POST'])
def get_onvif_device_info():
    """Get device information from ONVIF camera"""
    
@app.route('/onvif/profiles', methods=['POST'])
def get_onvif_profiles():
    """Get media profiles from ONVIF camera"""
    
@app.route('/onvif/stream-uri', methods=['POST'])
def get_onvif_stream_uri():
    """Get RTSP stream URI from ONVIF camera"""
```

### 1.2 ONVIF Python Libraries
```bash
# Requirements thêm vào
pip install onvif-zeep
pip install python-onvif-zeep
pip install netifaces
```

### 1.3 Camera Discovery Logic
```python
def discover_onvif_cameras(network_range="192.168.1.0/24"):
    """
    1. WS-Discovery scan for ONVIF devices
    2. Test ONVIF connection for each device
    3. Get device info và media profiles
    4. Return camera list với stream URLs
    """
```

---

## 🎨 Phase 2: Frontend ONVIF UI (Week 2-3)

### 2.1 Enhanced AddSourceModal
Mở rộng modal hiện tại để support ONVIF discovery:

```javascript
// components/config/AddSourceModal.js
const [onvifScanResults, setOnvifScanResults] = useState([]);
const [isScanning, setIsScanning] = useState(false);

const handleOnvifScan = async () => {
  setIsScanning(true);
  try {
    const response = await fetch('/onvif/discover', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        network_range: config.network_range || "192.168.1.0/24",
        timeout: 10 
      })
    });
    const devices = await response.json();
    setOnvifScanResults(devices.cameras || []);
  } catch (error) {
    console.error('ONVIF scan failed:', error);
  } finally {
    setIsScanning(false);
  }
};
```

### 2.2 ONVIF Device Selection UI
```jsx
{/* ONVIF Auto-Discovery Section */}
{sourceType === 'nvr' && config.protocol === 'onvif' && (
  <div className="mb-6">
    <div className="flex justify-between items-center mb-3">
      <h5 className="font-medium text-white">🔍 ONVIF Device Discovery</h5>
      <button
        onClick={handleOnvifScan}
        disabled={isScanning}
        className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
      >
        {isScanning ? 'Scanning...' : 'Scan Network'}
      </button>
    </div>
    
    {onvifScanResults.length > 0 && (
      <div className="grid gap-3 max-h-48 overflow-y-auto">
        {onvifScanResults.map((device, index) => (
          <OnvifDeviceCard 
            key={index}
            device={device}
            onSelect={(device) => handleOnvifDeviceSelect(device)}
          />
        ))}
      </div>
    )}
  </div>
)}
```

### 2.3 ONVIF Device Card Component
```jsx
const OnvifDeviceCard = ({ device, onSelect }) => (
  <div className="bg-gray-600 p-4 rounded-lg border cursor-pointer hover:border-blue-500"
       onClick={() => onSelect(device)}>
    <div className="flex justify-between items-start">
      <div className="flex-1">
        <h6 className="font-medium text-white">{device.name || device.ip}</h6>
        <p className="text-sm text-gray-300">{device.manufacturer} {device.model}</p>
        <p className="text-xs text-gray-400">
          {device.ip}:{device.port} • {device.profiles?.length || 0} profiles
        </p>
      </div>
      <div className="text-green-400 text-sm">
        ✓ ONVIF
      </div>
    </div>
  </div>
);
```

---

## 🔧 Phase 3: Integration with Existing System (Week 3-4)

### 3.1 Update ConfigForm.js
Tích hợp ONVIF discovery vào workflow hiện tại:

```javascript
// components/config/ConfigForm.js
const handleOnvifDiscovery = async (sourceConfig) => {
  if (sourceConfig.protocol === 'onvif') {
    try {
      // Tự động discover ONVIF cameras khi test connection
      const onvifResponse = await fetch('/onvif/discover', {
        method: 'POST',
        body: JSON.stringify({ 
          target_ip: sourceConfig.url,
          username: sourceConfig.username,
          password: sourceConfig.password 
        })
      });
      
      const devices = await onvifResponse.json();
      if (devices.cameras && devices.cameras.length > 0) {
        setNvrCameras(devices.cameras);
        setTestResult({
          success: true,
          message: `ONVIF discovery successful - Found ${devices.cameras.length} camera(s)`
        });
      }
    } catch (error) {
      console.warn('ONVIF discovery failed, fallback to manual config');
    }
  }
};
```

### 3.2 Enhanced Camera Selection
Hiển thị thông tin chi tiết cho ONVIF cameras:

```javascript
// Show ONVIF-specific info in camera selection
{nvrCameras.map((camera, index) => {
  const isOnvif = camera.protocol === 'onvif';
  
  return (
    <label key={camera.name} className="flex items-start space-x-3 p-3 bg-gray-700 rounded cursor-pointer">
      <input
        type="checkbox"
        checked={selectedNvrCameras.includes(camera.name)}
        onChange={() => handleNvrCameraToggle(camera.name)}
        className="mt-1"
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-white text-sm font-medium">{camera.name}</span>
          {isOnvif && <span className="text-xs bg-blue-600 text-white px-2 py-1 rounded">ONVIF</span>}
        </div>
        
        {camera.stream_url && (
          <div className="text-xs text-gray-400 truncate">{camera.stream_url}</div>
        )}
        
        {isOnvif && camera.profiles && (
          <div className="text-xs text-green-300">
            {camera.profiles.length} profile(s) • {camera.resolution} • {camera.codec}
          </div>
        )}
      </div>
    </label>
  );
})}
```

---

## 🧪 Phase 4: Testing & Mock Integration (Week 4-5)

### 4.1 Connect to ONVIF Mock
Sử dụng container `onvif-mock-fixed` để test:

```javascript
// Test config for ONVIF Mock
const mockOnvifConfig = {
  source_type: 'nvr',
  protocol: 'onvif',
  url: '172.17.0.2',
  port: 1000,
  username: '', // Mock không cần auth
  password: '',
  discovery_port: 3702,
  rtsp_port: 8554
};
```

### 4.2 Integration Testing
```javascript
// Test scenarios
const testOnvifIntegration = async () => {
  // 1. Discovery test
  await testOnvifDiscovery('172.17.0.2:3702');
  
  // 2. Device info test  
  await testDeviceInfo('172.17.0.2:1000');
  
  // 3. Stream URI test
  await testStreamUri('rtsp://172.17.0.2:8554/stream');
  
  // 4. End-to-end source addition
  await testSourceAddition(mockOnvifConfig);
};
```

---

## 🚀 Phase 5: Advanced Features (Week 5-6)

### 5.1 Real-time Stream Preview
```jsx
const OnvifStreamPreview = ({ streamUrl }) => (
  <div className="bg-gray-700 p-4 rounded-lg">
    <h6 className="text-white mb-2">Stream Preview</h6>
    <video 
      src={streamUrl}
      controls
      className="w-full h-48 bg-black rounded"
      onError={() => console.log('Stream preview failed')}
    />
  </div>
);
```

### 5.2 ONVIF Settings Panel
```jsx
const OnvifSettingsPanel = ({ device, onUpdate }) => (
  <div className="bg-gray-700 p-4 rounded-lg">
    <h6 className="text-white mb-3">ONVIF Configuration</h6>
    
    {/* Video Settings */}
    <div className="grid grid-cols-2 gap-4 mb-4">
      <select 
        value={device.selectedProfile}
        onChange={(e) => onUpdate({...device, selectedProfile: e.target.value})}
      >
        {device.profiles?.map(profile => (
          <option key={profile.token} value={profile.token}>
            {profile.name} - {profile.resolution}
          </option>
        ))}
      </select>
      
      <select
        value={device.streamType}
        onChange={(e) => onUpdate({...device, streamType: e.target.value})}
      >
        <option value="Main">Main Stream</option>
        <option value="Sub">Sub Stream</option>
      </select>
    </div>
    
    {/* PTZ Controls (future) */}
    <div className="text-xs text-gray-400">
      PTZ controls will be available in future versions
    </div>
  </div>
);
```

---

## 📊 Phase 6: Dashboard & Monitoring (Week 6-7)

### 6.1 ONVIF Status Dashboard
```jsx
const OnvifStatusDashboard = ({ onvifSources }) => (
  <div className="bg-gray-800 p-6 rounded-lg">
    <h3 className="text-xl font-bold text-white mb-4">ONVIF Camera Status</h3>
    
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {onvifSources.map(source => (
        <div key={source.id} className="bg-gray-700 p-3 rounded">
          <div className="flex items-center justify-between mb-2">
            <span className="text-white font-medium">{source.name}</span>
            <div className={`w-3 h-3 rounded-full ${
              source.status === 'online' ? 'bg-green-500' : 'bg-red-500'
            }`} />
          </div>
          <div className="text-xs text-gray-400">
            {source.ip} • {source.selectedCameras?.length || 0} cameras
          </div>
        </div>
      ))}
    </div>
  </div>
);
```

### 6.2 Health Monitoring
```javascript
// Periodic health check for ONVIF devices
const monitorOnvifHealth = async () => {
  const sources = await getActiveSources();
  const onvifSources = sources.filter(s => s.source_type === 'nvr' && s.config?.protocol === 'onvif');
  
  for (const source of onvifSources) {
    try {
      const health = await checkOnvifHealth(source);
      updateSourceStatus(source.id, health);
    } catch (error) {
      updateSourceStatus(source.id, { status: 'offline', error: error.message });
    }
  }
};
```

---

## 🔧 Technical Implementation Details

### Backend ONVIF Library Integration
```python
# backend/onvif_client.py
from onvif import ONVIFCamera
import netifaces

class OnvifManager:
    def __init__(self):
        self.devices = {}
    
    async def discover_devices(self, network_range="192.168.1.0/24"):
        """WS-Discovery để tìm ONVIF devices"""
        
    async def connect_device(self, ip, port, username, password):
        """Kết nối và lấy thông tin device"""
        
    async def get_stream_uri(self, device, profile_token):
        """Lấy RTSP stream URI"""
        
    async def get_device_capabilities(self, device):
        """Lấy capabilities của device"""
```

### Frontend State Management
```javascript
// hooks/useOnvifManager.js
const useOnvifManager = () => {
  const [onvifDevices, setOnvifDevices] = useState([]);
  const [discoveryStatus, setDiscoveryStatus] = useState('idle');
  const [selectedDevices, setSelectedDevices] = useState([]);
  
  const discoverDevices = useCallback(async (networkRange) => {
    // Discovery logic
  }, []);
  
  const connectDevice = useCallback(async (deviceConfig) => {
    // Connection logic
  }, []);
  
  return {
    onvifDevices,
    discoveryStatus,
    selectedDevices,
    discoverDevices,
    connectDevice
  };
};
```

---

## ✅ Testing Strategy

### Unit Tests
- ONVIF discovery functionality
- Device connection and authentication
- Stream URI generation
- Profile selection

### Integration Tests  
- End-to-end source addition workflow
- Camera selection and configuration
- Integration with existing NVR workflow
- Mock ONVIF container testing

### User Acceptance Tests
- ONVIF device auto-discovery
- Manual device addition
- Stream preview functionality
- Configuration persistence

---

## 📈 Success Metrics

1. **Discovery Success Rate**: >90% ONVIF devices detected
2. **Connection Reliability**: <5% connection failures
3. **User Experience**: <30s from scan to camera selection
4. **Integration**: Seamless với existing NVR workflow
5. **Performance**: <2s discovery time for local network

---

## 🔮 Future Enhancements

- **PTZ Control**: Pan/Tilt/Zoom controls cho cameras support
- **Event Handling**: ONVIF event subscription
- **Advanced Analytics**: Video analytics integration
- **Mobile Support**: Mobile app ONVIF discovery
- **Cloud Integration**: ONVIF cloud camera support

---

## 📅 Timeline Summary

| Phase | Duration | Deliverables |
|-------|----------|-------------|
| 1 | Week 1-2 | Backend ONVIF APIs, Discovery logic |
| 2 | Week 2-3 | Frontend UI integration, Device selection |
| 3 | Week 3-4 | System integration, Configuration workflow |
| 4 | Week 4-5 | Testing, Mock integration, Bug fixes |
| 5 | Week 5-6 | Advanced features, Stream preview |
| 6 | Week 6-7 | Dashboard, Monitoring, Documentation |

**Total Timeline: 7 weeks** 

---

*🎯 End Goal: Seamless ONVIF camera discovery và integration trong VTrack configuration tab, compatible với existing NVR workflow và enhanced user experience.*