# Claude Code Guidelines for ePACK Project

## Language Guidelines

### UI Language: English Only
**CRITICAL**: All user-facing content MUST be in English.

- ❌ NEVER use Vietnamese for UI text, labels, buttons, placeholders
- ❌ NEVER use Vietnamese for error messages, alerts, notifications
- ❌ NEVER use Vietnamese for component props, state names, or constants
- ✅ ALWAYS use English for all user-facing content
- ✅ ALWAYS set `lang="en"` for HTML video/audio elements
- ✅ ALWAYS use English for comments in frontend code

**Examples:**
```typescript
// ❌ WRONG
<Button>Tải xuống</Button>
const [dangXuLy, setDangXuLy] = useState(false);

// ✅ CORRECT
<Button>Download</Button>
const [isProcessing, setIsProcessing] = useState(false);
```

### Code Language: English
**Backend & Frontend Code:**
- Variable names: English only
- Function names: English only
- Class names: English only
- Constants: English only
- Type definitions: English only

**Comments:**
- Frontend: English only
- Backend: Vietnamese allowed for complex business logic explanation

### Video Player Specifications
When implementing HTML5 video players:
```typescript
<video
  lang="en"                    // Force English controls
  controls                     // Show controls
  controlsList="nodownload"    // Hide download button
  playsInline                  // iOS inline playback
  preload="metadata"           // Preload metadata only
/>
```

## Project Structure

### Frontend (`/frontend`)
- React + TypeScript + Next.js
- Chakra UI for components
- All UI text must be in English
- Component naming: PascalCase (e.g., `VideoPlayerModal.tsx`)

### Backend (`/backend`)
- Python + Flask
- Module structure: feature-based organization
- API responses: English error messages for client-facing, Vietnamese logs allowed

## Video Processing

### Video Cutting Logic
- `ts` (time start) and `te` (time end) are in **seconds**, NOT frame indices
- Never divide `ts/te` by `fps` when cutting video
- Use FFmpeg with `-ss` (start time) and `-t` (duration) in seconds

**Example:**
```python
# ❌ WRONG
start_time = ts / fps  # ts is already in seconds!

# ✅ CORRECT
start_time = ts  # Use ts directly
```

### Video Streaming
- Endpoint: `/api/config/step4/roi/stream-video`
- Supports HTTP Range requests for seeking
- Use `encodeURIComponent()` for video paths in URLs

## Common Patterns

### Modal Components
```typescript
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  // ... other props
}

// Use Chakra UI Modal
<Modal isOpen={isOpen} onClose={onClose} size="6xl" isCentered>
  <ModalOverlay />
  <ModalContent>
    {/* content */}
  </ModalContent>
</Modal>
```

### Event Processing
- Events have `packing_time_start` and `packing_time_end` in milliseconds (UTC)
- Event detection creates events in database with proper timezone info
- Video timestamps calculated from `video_start_time + ts_offset`

## Git Commit Guidelines

### Commit Message Format
```
type: brief description in English

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Types:** feat, fix, docs, refactor, test, chore

### Before Committing
1. Check `git status` for untracked files
2. Check `git diff` for staged/unstaged changes
3. Review recent commits for style consistency
4. Ensure commit message explains the "why" not just "what"

## Debugging Tips

### Video Not Playing
1. Check video path exists: `os.path.exists(video_path)`
2. Check backend streaming endpoint is accessible
3. Check browser console for CORS errors
4. Verify video format is supported (MP4, MOV, AVI)

### Database Query Issues
1. Use `safe_db_connection()` with proper locks
2. Check timezone handling (UTC in DB, local for display)
3. Verify `ts/te` are in seconds, not frames

## Testing Checklist

### Frontend Components
- [ ] Component renders without errors
- [ ] All text is in English
- [ ] Dark/light mode both work
- [ ] Responsive on different screen sizes
- [ ] No console errors/warnings

### Video Features
- [ ] Video auto-plays correctly
- [ ] Playback rate set to desired speed
- [ ] Controls work (play/pause/seek/volume)
- [ ] Modal opens/closes properly
- [ ] Multiple events open correct videos

## References

- Frontend: `/frontend/src/components/`
- Backend APIs: `/backend/modules/query/query.py`
- Video streaming: `/backend/modules/config/routes/steps/step4_roi_routes.py`
- Event detection: `/backend/modules/technician/event_detector.py`

---

**Last Updated:** October 2025
**Maintained By:** Development Team + Claude Code
