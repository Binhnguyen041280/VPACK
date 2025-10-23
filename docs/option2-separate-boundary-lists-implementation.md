# Option 2: Separate Boundary Lists - Implementation Guide

## ⚠️ **DEPRECATED - 2025-10-23**

**Status:** REMOVED
**Reason:** Implementation was based on incorrect assumption about WeChat QR `detectAndDecode()` behavior.

**Incorrect Assumption:**
WeChat QR model returns boundary points when QR detection succeeds but decoding fails.

**Reality (from OpenCV source code):**
When decoding fails, **BOTH** `texts` and `points` are empty. The model only returns boundary points when decoding **succeeds**.

**Impact:**
- All boundary buffering logic removed from `frame_sampler_trigger.py` (221 lines deleted)
- `convergence_detector.py` deleted (288 lines)
- Database schema **KEPT** (expected_qr_size columns still useful for future detection methods)

**For Future Empty Event Detection:**
Implement alternative detection methods (template matching, edge detection, YOLO) using `expected_mvd_qr_size` from packing_profiles.

---

## Original Overview (DEPRECATED)

**Implementation Date:** 2025-10-22
**Strategy:** Separate MVD and TimeGo boundaries into different lists, log both types with different tags

---

## Mục Tiêu

### **Yêu Cầu:**
1. ✅ Lưu TẤT CẢ boundaries trong empty event (MVD + TimeGo)
2. ✅ Phân biệt rõ ràng MVD vs TimeGo boundaries
3. ✅ Chứng minh event có QR MVD decode fail
4. ✅ Giữ nguyên data cho AI processing sau

### **Lợi Ích:**
- **Tracking:** Biết chắc chắn event nào có QR MVD (dù decode fail)
- **Analysis:** AI có thể chọn chỉ xử lý MVD boundaries
- **Debug:** Dễ phân tích sự hiện diện của cả 2 loại QR
- **No Data Loss:** Không mất thông tin về boundaries

---

## Architecture Changes

### **1. Event State Structure**

**Trước (Old):**
```python
self.event_state = {
    'in_event': False,
    'ts_frame': None,
    'has_mvd': False,
    'boundaries_buffer': [],           # Single list
    'last_boundary_bbox': None
}
```

**Sau (New):**
```python
self.event_state = {
    'in_event': False,
    'ts_frame': None,
    'has_mvd': False,
    'mvd_boundaries_buffer': [],       # MVD boundaries only
    'timego_boundaries_buffer': [],    # TimeGo boundaries only
    'last_mvd_boundary_bbox': None,    # Smart sampling for MVD
    'last_timego_boundary_bbox': None  # Smart sampling for TimeGo
}
```

---

### **2. Buffering Logic**

**File:** `frame_sampler_trigger.py:791-823`

**Flow:**
```python
# Trong process_video(), khi có boundary_points:
if boundary_bbox:
    # Classify by size
    if self._is_mvd_size(boundary_bbox):
        # MVD-sized → buffer vào mvd_boundaries_buffer
        if self._should_buffer_boundary(boundary_bbox, boundary_type='mvd'):
            self.event_state['mvd_boundaries_buffer'].append({
                'frame': second,
                'bbox': boundary_bbox
            })
            self.event_state['last_mvd_boundary_bbox'] = boundary_bbox
    else:
        # TimeGo-sized → buffer vào timego_boundaries_buffer
        if self._should_buffer_boundary(boundary_bbox, boundary_type='timego'):
            self.event_state['timego_boundaries_buffer'].append({
                'frame': second,
                'bbox': boundary_bbox
            })
            self.event_state['last_timego_boundary_bbox'] = boundary_bbox
```

**Key Changes:**
- ✅ Size classification TRƯỚC KHI buffer (early filtering)
- ✅ 2 lists riêng biệt
- ✅ Smart sampling cho từng loại riêng

---

### **3. Empty Event Processing**

**File:** `frame_sampler_trigger.py:551-629`

**Strategy:**
```python
def _process_empty_event(self, te_second, log_file_handle):
    mvd_boundaries = self.event_state['mvd_boundaries_buffer']
    timego_boundaries = self.event_state['timego_boundaries_buffer']

    # Process MVD boundaries (priority)
    if mvd_boundaries:
        stable_mvd_frames = convergence_detector.find_stable_frames(
            boundaries=mvd_boundaries,
            threshold=mvd_width * 0.05,
            max_frames=3
        )
        for frame_data in stable_mvd_frames:
            _log_boundary(frame_data, log_file_handle, boundary_type='mvd')

    # Process TimeGo boundaries (reference)
    if timego_boundaries:
        stable_timego_frames = convergence_detector.find_stable_frames(
            boundaries=timego_boundaries,
            threshold=timego_width * 0.05,
            max_frames=3
        )
        for frame_data in stable_timego_frames:
            _log_boundary(frame_data, log_file_handle, boundary_type='timego')
```

**Key Points:**
- ✅ Process MVD first (priority)
- ✅ Separate convergence detection for each type
- ✅ Different thresholds (MVD ~57px, TimeGo ~176px)
- ✅ Log both types

---

### **4. Log Format**

**File:** `frame_sampler_trigger.py:631-655`

```python
def _log_boundary(self, frame_data, log_file_handle, boundary_type='mvd'):
    second = frame_data['frame']
    bbox = frame_data['bbox']

    if boundary_type == 'mvd':
        # MVD: Standard format, NO tag
        log_line = f"{second},Off,,boundary:[{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}]\n"
    else:
        # TimeGo: With 'timego_ref' tag
        log_line = f"{second},Off,timego_ref,boundary:[{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}]\n"

    log_file_handle.write(log_line)
```

**Log Output Examples:**

**Empty Event với chỉ MVD decode fail:**
```
88,Off,,boundary:[207,800,57,58]
88,Off,,boundary:[208,801,58,59]
90,Off,,boundary:[207,800,57,58]
```

**Empty Event với cả TimeGo + MVD decode fail:**
```
88,Off,timego_ref,boundary:[500,100,177,180]
88,Off,timego_ref,boundary:[501,101,176,181]
88,Off,,boundary:[207,800,57,58]
90,Off,,boundary:[208,801,58,59]
```

**Empty Event với chỉ TimeGo (noise):**
```
88,Off,timego_ref,boundary:[500,100,177,180]
88,Off,timego_ref,boundary:[501,101,176,181]
```

---

## Expected Behavior

### **Scenario 1: MVD Decode Fail Only**

**Input:**
- Event 62-88 (Ts→Te)
- MVD QR hiện diện, decode fail
- TimeGo KHÔNG hiện trong packing_area

**Buffer State:**
```python
mvd_boundaries_buffer = [
    {'frame': 65, 'bbox': [207, 800, 57, 58]},
    {'frame': 70, 'bbox': [208, 801, 58, 59]},
    {'frame': 75, 'bbox': [207, 800, 57, 58]}
]
timego_boundaries_buffer = []  # Empty
```

**Log Output:**
```
# Convergence detection → chọn 3 stable frames
88,Off,,boundary:[207,800,57,58]
88,Off,,boundary:[208,801,58,59]
88,Off,,boundary:[207,800,57,58]
```

**Analysis:**
- ✅ Chứng minh event có MVD QR
- ✅ AI có thể process MVD boundaries
- ✅ Không có TimeGo noise

---

### **Scenario 2: TimeGo + MVD Decode Fail**

**Input:**
- Event 62-88 (Ts→Te)
- MVD QR decode fail
- TimeGo CŨNG hiện trong packing_area (ROI overlap)

**Buffer State:**
```python
mvd_boundaries_buffer = [
    {'frame': 65, 'bbox': [207, 800, 57, 58]},
    {'frame': 70, 'bbox': [208, 801, 58, 59]}
]
timego_boundaries_buffer = [
    {'frame': 85, 'bbox': [500, 100, 177, 180]},
    {'frame': 86, 'bbox': [501, 101, 176, 181]},
    {'frame': 87, 'bbox': [500, 100, 177, 180]}
]
```

**Log Output:**
```
# MVD boundaries (priority)
88,Off,,boundary:[207,800,57,58]
88,Off,,boundary:[208,801,58,59]

# TimeGo boundaries (reference)
88,Off,timego_ref,boundary:[500,100,177,180]
88,Off,timego_ref,boundary:[501,101,176,181]
88,Off,timego_ref,boundary:[500,100,177,180]
```

**Analysis:**
- ✅ Chứng minh event có cả 2 loại QR
- ✅ MVD boundaries rõ ràng (no tag)
- ✅ TimeGo tagged với 'timego_ref'
- ✅ AI có thể filter TimeGo, chỉ xử lý MVD

---

### **Scenario 3: Only TimeGo (Noise Event)**

**Input:**
- Event 62-88
- Chỉ có TimeGo decode fail
- KHÔNG có MVD

**Buffer State:**
```python
mvd_boundaries_buffer = []  # Empty!
timego_boundaries_buffer = [
    {'frame': 85, 'bbox': [500, 100, 177, 180]},
    {'frame': 86, 'bbox': [501, 101, 176, 181]}
]
```

**Log Output:**
```
88,Off,timego_ref,boundary:[500,100,177,180]
88,Off,timego_ref,boundary:[501,101,176,181]
```

**Analysis:**
- ✅ Tracking: Event KHÔNG có MVD (chỉ có timego_ref)
- ✅ AI có thể skip event này
- ⚠️ Có thể là noise (TimeGo transition)

---

## Testing Plan

### **Test 1: Normal MVD Decode Fail**
```bash
# Input: Video with MVD decode fail
# Expected: Log MVD boundaries (no timego_ref)
grep "boundary:" log.txt | grep -v "timego_ref"
```

### **Test 2: TimeGo + MVD Mixed**
```bash
# Expected: Both types logged
grep "boundary:" log.txt | grep "timego_ref"  # Should have results
grep "boundary:" log.txt | grep -v "timego_ref"  # Should have results
```

### **Test 3: Verify Separation**
```bash
# Count MVD boundaries
grep "boundary:" log.txt | grep -v "timego_ref" | wc -l

# Count TimeGo boundaries
grep "boundary:" log.txt | grep "timego_ref" | wc -l
```

---

## Migration Notes

### **Breaking Changes:**
- ❌ Log format có thêm `timego_ref` tag cho TimeGo boundaries
- ❌ Event state structure thay đổi (2 lists thay vì 1)

### **Backward Compatibility:**
- ✅ MVD boundaries vẫn dùng format cũ (no tag)
- ✅ AI processing cũ vẫn hoạt động (chỉ cần ignore timego_ref entries)

### **Upgrade Path:**
1. Deploy code mới
2. Test với videos mẫu
3. Verify logs có cả 2 loại boundaries
4. Update AI processing để skip timego_ref (optional)

---

## Performance Impact

### **Memory:**
- **Before:** 1 list × N boundaries = N items
- **After:** 2 lists × N boundaries = N items (same!)
- ✅ **No increase** (boundaries vẫn được split ra 2 lists)

### **CPU:**
- **Before:** 1× convergence detection
- **After:** 2× convergence detection (MVD + TimeGo)
- ⚠️ **Slight increase** (~2x for empty events only)
- ✅ **Acceptable** (empty events chiếm <10% total events)

### **Disk:**
- **Before:** N log entries
- **After:** M (MVD) + K (TimeGo) entries
- ⚠️ **May increase** if TimeGo boundaries được log
- ✅ **Acceptable** (compress logs định kỳ)

---

## Success Criteria

### **Functional:**
- ✅ MVD boundaries được log (no tag)
- ✅ TimeGo boundaries được log (with timego_ref tag)
- ✅ Events có MVD được tracking chính xác
- ✅ No crashes, no data loss

### **Non-Functional:**
- ✅ Performance overhead <10%
- ✅ Log size increase <20%
- ✅ Code maintainability OK

---

## Rollback Plan

**If issues occur:**

1. Revert code changes:
   ```bash
   git revert <commit_hash>
   ```

2. Restore event_state structure:
   ```python
   self.event_state = {
       'boundaries_buffer': [],  # Single list
       'last_boundary_bbox': None
   }
   ```

3. Restore _process_empty_event():
   ```python
   # Process single boundaries list
   # Reject TimeGo by size
   ```

---

## Summary

**Implementation:** ✅ Complete
**Testing:** ⏳ Pending
**Deployment:** ⏳ Pending

**Key Benefits:**
- ✅ No data loss
- ✅ Clear separation MVD vs TimeGo
- ✅ Easy to analyze and debug
- ✅ AI can filter by tag

**Next Steps:**
1. Test with real videos
2. Verify log output format
3. Update AI processing (optional)
4. Deploy to production
