# V_Track Code Style & Conventions

## Python Backend Conventions

### Naming Conventions
- **Variables & Functions**: snake_case
  ```python
  video_file_path = "/path/to/video"
  def process_video_frame():
  ```
- **Classes**: PascalCase
  ```python
  class VideoProcessor:
  class OAuthManager:
  ```
- **Constants**: UPPER_SNAKE_CASE
  ```python
  BASE_DIR = os.path.dirname(__file__)
  DEFAULT_TIMEOUT = 60
  ```
- **Private methods**: Leading underscore
  ```python
  def _internal_helper():
  ```

### Import Organization
- **Standard library first**
- **Third-party packages second**
- **Local modules last**
- **Absolute imports from modules/**
```python
import os
import json
from pathlib import Path

import cv2
import mediapipe as mp
from flask import Flask, request

from modules.config.oauth_manager import OAuthManager
from modules.db_utils import get_db_connection
```

### Error Handling Pattern
```python
def database_operation():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Database operations
        conn.commit()
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Database operation failed: {str(e)}")
        return {"status": "error", "message": str(e)}
    finally:
        if conn:
            conn.close()
```

### Logging Pattern
```python
import logging
logger = logging.getLogger(__name__)

# Usage
logger.info("Operation started")
logger.warning("Potential issue detected")
logger.error(f"Operation failed: {str(e)}")
```

### Database Access Pattern
```python
from modules.scheduler.db_sync import db_rwlock
from modules.db_utils import get_db_connection

# Thread-safe database operations
with db_rwlock.gen_wlock():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SQL QUERY", (params,))
    conn.commit()
    conn.close()
```

## React Frontend Conventions

### Component Structure
- **Functional components with hooks**
- **Destructure props in parameters**
- **Use const for component declaration**
```javascript
const VideoConfig = ({ sourceType, onConfigChange }) => {
  const [config, setConfig] = useState({});
  
  return (
    <div className="component-container">
      {/* Component content */}
    </div>
  );
};
```

### Naming Conventions
- **Components**: PascalCase
  ```javascript
  const VideoSourceConfig = () => {}
  const HandDetectionPanel = () => {}
  ```
- **Variables & Functions**: camelCase
  ```javascript
  const videoFile = "example.mp4";
  const handleVideoUpload = () => {};
  ```
- **Constants**: UPPER_SNAKE_CASE
  ```javascript
  const API_BASE_URL = "http://localhost:8080";
  const DEFAULT_CONFIG = {};
  ```

### Styling Conventions
- **Tailwind CSS classes only** (no separate CSS files)
- **Responsive design**: Use sm:, md:, lg: prefixes
- **Custom colors**: Use defined color scheme
```javascript
<div className="bg-gray-800 text-white p-4 rounded-lg shadow-md">
  <button className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded">
    Process Video
  </button>
</div>
```

### State Management Pattern
```javascript
// Local state with useState
const [isProcessing, setIsProcessing] = useState(false);
const [config, setConfig] = useState({});

// Custom hooks for business logic
const { videoSources, addSource, removeSource } = useVideoSources();
```

### API Call Pattern
```javascript
const handleApiCall = async () => {
  try {
    setLoading(true);
    const response = await axios.post('/api/endpoint', data);
    if (response.data.status === 'success') {
      // Handle success
    } else {
      setError(response.data.message);
    }
  } catch (error) {
    setError('Network error occurred');
    console.error('API call failed:', error);
  } finally {
    setLoading(false);
  }
};
```

## File Organization Rules

### Backend Structure
```
backend/
├── app.py                 # Main Flask application
├── database.py           # Database initialization
├── modules/              # Core business logic
│   ├── config/          # Configuration management
│   ├── sources/         # Video source handling
│   ├── technician/      # Video processing
│   ├── scheduler/       # Background tasks
│   └── db_utils/        # Database utilities
├── blueprints/          # Flask route handlers
└── tests/               # Test files
```

### Frontend Structure
```
frontend/src/
├── App.js              # Main application
├── Dashboard.js        # Primary interface
├── components/         # Reusable UI components
├── hooks/              # Custom React hooks
└── api.js              # API communication layer
```

## Code Quality Standards

### Documentation
- **Function docstrings** for complex functions
- **Inline comments** for business logic
- **README files** for each major module
```python
def process_video_with_detection(video_path, roi_coords):
    """
    Process video file with hand detection and ROI analysis.
    
    Args:
        video_path (str): Path to video file
        roi_coords (list): List of ROI coordinates [(x1,y1), (x2,y2)]
    
    Returns:
        dict: Processing results with events and timestamps
    """
```

### Type Hints (Recommended)
```python
from typing import List, Dict, Optional

def get_video_sources() -> List[Dict[str, str]]:
    """Return list of configured video sources."""
    pass

def process_frame(frame: np.ndarray) -> Optional[Dict]:
    """Process single video frame."""
    pass
```

### Constants Definition
```python
# backend/modules/config/constants.py
DEFAULT_ROI_COORDS = [(100, 100), (200, 200)]
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.avi', '.mov']
MAX_FILE_SIZE_MB = 500
```

## Security Guidelines

### Environment Variables
```python
# Use environment variables for sensitive data
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
SECRET_KEY = os.getenv('SECRET_KEY', 'default-dev-key')
```

### Input Validation
```python
def validate_video_path(path: str) -> bool:
    """Validate video file path for security."""
    if not path or '..' in path:
        return False
    return os.path.exists(path) and path.endswith(('.mp4', '.avi', '.mov'))
```

### Database Security
```python
# Always use parameterized queries
cursor.execute(
    "INSERT INTO events (timestamp, event_type, data) VALUES (?, ?, ?)",
    (timestamp, event_type, json.dumps(data))
)
```