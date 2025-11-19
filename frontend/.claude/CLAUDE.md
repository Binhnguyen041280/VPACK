# Claude Code Guidelines for ePACK Frontend

## 🌍 Language Policy: ENGLISH ONLY

### Critical Rules
**ALL user-facing content MUST be in English**

- ❌ NO Vietnamese in UI text, labels, buttons, placeholders
- ❌ NO Vietnamese in component names, variables, functions
- ❌ NO Vietnamese in comments, documentation
- ❌ NO Vietnamese in error messages, alerts, toasts
- ✅ ALWAYS use English for everything

### Examples

**Component Names:**
```typescript
// ❌ WRONG
const VideoPlayerModal = () => {}  // Vietnamese name would be wrong
const [dangXuLy, setDangXuLy] = useState(false);

// ✅ CORRECT
const VideoPlayerModal = () => {}
const [isProcessing, setIsProcessing] = useState(false);
```

**UI Text:**
```typescript
// ❌ WRONG
<Button>Tải xuống</Button>
<Text>Đang xử lý...</Text>

// ✅ CORRECT
<Button>Download</Button>
<Text>Processing...</Text>
```

**Comments:**
```typescript
// ❌ WRONG
// Hàm này xử lý video
const processVideo = () => {}

// ✅ CORRECT
// This function processes video
const processVideo = () => {}
```

## 🎬 Video Player Implementation

### HTML5 Video Element
Always use these attributes:
```typescript
<video
  lang="en"                    // ✅ REQUIRED: Force English UI
  controls                     // Show native controls
  controlsList="nodownload"    // Hide download button
  autoPlay                     // Auto-play when loaded
  playsInline                  // iOS inline playback
  preload="metadata"           // Performance optimization
/>
```

### Video Streaming URL
```typescript
const videoUrl = `http://localhost:8080/api/config/step4/roi/stream-video?video_path=${encodeURIComponent(videoPath)}`;
```

### Playback Rate Control
```typescript
useEffect(() => {
  if (videoRef.current) {
    videoRef.current.playbackRate = 2.0; // Set 2x speed
  }
}, []);
```

## 🎨 Component Patterns

### Modal Components
```typescript
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton
} from '@chakra-ui/react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  // ... other props
}

const MyModal: React.FC<ModalProps> = ({ isOpen, onClose }) => (
  <Modal isOpen={isOpen} onClose={onClose} size="6xl" isCentered>
    <ModalOverlay />
    <ModalContent>
      <ModalHeader>Title in English</ModalHeader>
      <ModalCloseButton />
      <ModalBody>{/* Content */}</ModalBody>
    </ModalContent>
  </Modal>
);
```

### Loading States
```typescript
// Use Chakra UI Spinner
{isLoading && (
  <VStack spacing={4}>
    <Spinner size="xl" />
    <Text>Loading...</Text>  {/* English text */}
  </VStack>
)}
```

### Error States
```typescript
// Use Chakra UI Alert
{error && (
  <Alert status="error">
    <AlertIcon />
    <Text>Error: {error}</Text>  {/* English error */}
  </Alert>
)}
```

## 📁 File Structure

```
src/
├── components/
│   ├── trace/
│   │   ├── TraceHeader.tsx
│   │   ├── EventCard.tsx
│   │   └── VideoPlayerModal.tsx
│   └── roi/
│       ├── ROIConfigModal.tsx
│       └── PureVideoCanvas.tsx
├── contexts/
├── hooks/
└── utils/
```

## 🔧 Common Patterns

### State Management
```typescript
// Event data interface
interface EventData {
  event_id: number;
  tracking_codes_parsed: string[];
  camera_name: string;
  packing_time_start: number;
  packing_time_end: number;
  duration: number;
}

// Processing state
const [processing, setProcessing] = useState({
  isProcessing: false,
  progress: 0,
  status: 'idle'
});
```

### API Calls
```typescript
const response = await fetch('http://localhost:8080/api/endpoint', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data)
});

const result = await response.json();
```

### Color Mode
```typescript
import { useColorModeValue } from '@chakra-ui/react';

const bg = useColorModeValue('white', 'gray.800');
const text = useColorModeValue('gray.700', 'gray.200');
```

## ✅ Pre-Commit Checklist

### Before Every Commit
- [ ] All text is in English
- [ ] No Vietnamese in code or comments
- [ ] Component names are in PascalCase
- [ ] Variables/functions are in camelCase
- [ ] No console.log() in production code
- [ ] No unused imports
- [ ] TypeScript errors resolved
- [ ] Dark/light mode tested

### Video Features Checklist
- [ ] Video element has `lang="en"`
- [ ] Auto-play works
- [ ] Playback rate is set correctly
- [ ] Controls are in English
- [ ] Error states show English messages
- [ ] Loading states show English text

## 🚫 Common Mistakes to Avoid

### ❌ Vietnamese Text
```typescript
// WRONG
<Text>Đang tải video...</Text>
const [videoPath, setVideoPath] = useState('');  // Vietnamese variable name

// CORRECT
<Text>Loading video...</Text>
const [videoPath, setVideoPath] = useState('');
```

### ❌ Missing Language Attribute
```typescript
// WRONG
<video controls autoPlay />

// CORRECT
<video lang="en" controls autoPlay controlsList="nodownload" />
```

### ❌ Hardcoded Vietnamese
```typescript
// WRONG
alert('Lỗi khi tải video');

// CORRECT
console.error('Error loading video');
// Or use proper error handling with English message
```

## 📚 Resources

- Chakra UI: https://chakra-ui.com/
- React TypeScript: https://react-typescript-cheatsheet.netlify.app/
- HTML5 Video: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/video

---

**Remember: ENGLISH ONLY for all user-facing content!**

**Last Updated:** October 2025
