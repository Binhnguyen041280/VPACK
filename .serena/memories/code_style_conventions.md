# V_Track - Code Style & Conventions

## General Principles
- **Nocode approach**: Ưu tiên sử dụng thư viện có sẵn
- **User-friendly**: Desktop app cho người dùng phổ thông
- **Vietnamese UI**: Giao diện và comments bằng tiếng Việt

## Frontend Code Style (React)
- **Naming**: camelCase cho biến/function, PascalCase cho components
- **Components**: Functional components với hooks
- **Styling**: Tailwind CSS classes
- **Font**: Montserrat (@fontsource/montserrat)
- **Theme**: Dark theme (bg-gray-900, text-white)
- **State**: useState hooks, không localStorage

### Example:
```javascript
import { useState } from "react";

function App() {
  const [activeMenu, setActiveMenu] = useState("Chương trình");
  return (
    <div className="flex min-h-screen bg-gray-900 text-white font-montserrat">
      // Component content
    </div>
  );
}
```

## Backend Code Style (Python)
- **Naming**: snake_case cho variables/functions, PascalCase cho classes
- **Comments**: Tiếng Việt để giải thích logic
- **Error Handling**: Comprehensive error handling và logging
- **Environment**: Tắt verbose logs từ TensorFlow, MediaPipe, OpenCV
- **Modules**: Tách thành modules rõ ràng (technician, sources, config...)

### Example:
```python
# ==================== TẮT TẤT CẢ LOGS TRƯỚC KHI IMPORT ====================
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings('ignore')

def process_video():
    """Xử lý video với error handling"""
    try:
        # Logic here
        pass
    except Exception as e:
        logger.error(f"Lỗi xử lý video: {e}")
```

## File Organization
- **Modular**: Tách các chức năng vào modules riêng
- **Clear naming**: Tên file mô tả chức năng cụ thể
- **Documentation**: README và progress docs bằng tiếng Việt