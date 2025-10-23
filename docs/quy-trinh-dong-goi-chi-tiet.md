# Quy Trình Đóng Gói Chi Tiết - Phân Tích Coverage

## Mục Đích
Tài liệu này mô tả chi tiết quy trình đóng gói thực tế tại hiện trường, chia thành các giai đoạn cụ thể để phân tích khả năng xử lý của hệ thống V-Track.

---

## Tổng Quan Quy Trình

**Trigger Method:** QR Trigger với TimeGo
**ROI Areas:**
- `qr_trigger_area`: Vùng nhỏ để detect QR TimeGo (trigger On/Off)
- `packing_area`: Vùng chính để detect QR MVD (mã vận đơn)

**Event Definition:**
- **Ts (Time start):** Trigger chuyển từ On → Off (bắt đầu đóng gói)
- **Te (Time end):** Trigger chuyển từ Off → On (kết thúc đóng gói)

---

## Giai Đoạn 1: TRẠNG THÁI BAN ĐẦU (Chờ Hàng)

### 1.1 Mô Tả
- QR TimeGo **luôn hiển thị** trong `qr_trigger_area`
- Hộp hàng **chưa được đưa vào** vùng đóng gói
- Hệ thống ở trạng thái IDLE

### 1.2 Dữ Liệu Phát Sinh

**Frame-by-frame:**
```
Frame N:
  - qr_trigger_area: detect TimeGo → decode "TimeGo" → state = "On"
  - packing_area: không có QR → mvd = "", boundary = None
```

**Log Output:**
```
<second>,On,
```

### 1.3 Code Coverage Analysis

**File:** `frame_sampler_trigger.py`

**Xử lý:**
```python
# Dòng 318-326: Detect TimeGo in trigger area
trigger_texts, _ = self.qr_detector.detectAndDecode(frame_trigger)
for text in trigger_texts:
    if text == "TimeGo":
        state = "On"  # ✅ XỬ LÝ OK
        break
```

**State Detection (dòng 774-812):**
```python
frame_states.append(state)  # Collect 5 frames
if len(frame_states) == 5:
    on_count = sum(1 for s in frame_states if s == "On")
    if on_count >= 3:
        final_state = "On"  # ✅ XỬ LÝ OK
```

**Kết Luận:**
- ✅ **PASS**: Code xử lý đúng trạng thái On
- ✅ **PASS**: Log ghi nhận state = "On"

---

## Giai Đoạn 2: BẮT ĐẦU ĐÓNG GÓI (Ts Event)

### 2.1 Mô Tả
- User **đưa hộp hàng vào** vùng đóng gói
- Hộp hàng **che khuất QR TimeGo**
- Trigger chuyển từ On → Off

### 2.2 Dữ Liệu Phát Sinh

**Frame-by-frame:**
```
Frame N+1:
  - qr_trigger_area: TimeGo bị che → decode fail → state = "Off"
  - packing_area: chưa có QR MVD (chưa dán nhãn) → mvd = "", boundary = None
```

**Log Output:**
```
<second>,Off,
```

### 2.3 Code Coverage Analysis

**State Transition Detection (dòng 784-794):**
```python
if final_state != last_state:
    # Detect Ts (Off state = event start)
    if final_state == "Off":
        # Reset event state for new event
        self.event_state = {
            'in_event': True,         # ✅ Bắt đầu event
            'ts_frame': second,       # ✅ Lưu Ts
            'has_mvd': False,         # ✅ Chưa có MVD
            'boundaries_buffer': [],  # ✅ Buffer rỗng
            'last_boundary_bbox': None
        }
        self.logger.debug(f"Event started (Ts) at second {second}")  # ✅ LOG
```

**Kết Luận:**
- ✅ **PASS**: Detect Ts chính xác
- ✅ **PASS**: Khởi tạo event state
- ✅ **PASS**: Log ghi nhận Off state

---

## Giai Đoạn 3: DÁN NHÃN QR MVD (Critical Phase)

### 3.1 Mô Tả
- Sau khi đóng hàng vào hộp/túi
- User **dán nhãn QR MVD** lên hộp
- QR xuất hiện trong `packing_area`
- QR TimeGo **vẫn bị che** (state vẫn là Off)

### 3.2 Sub-Cases (3 Khả Năng)

---

#### **CASE 3A: DECODE THÀNH CÔNG**

**Frame data:**
```
Frame N+k:
  - qr_trigger_area: TimeGo vẫn bị che → state = "Off"
  - packing_area:
      - detect QR MVD
      - decode thành công → text = "SPXVN057397122803"
      - có boundary points → bbox = [207, 800, 63, 60]
```

**Log Output:**
```
<second>,Off,SPXVN057397122803,bbox:[207,800,63,60]
```

**Code Coverage:**

**Detection (dòng 333-383):**
```python
packing_texts, packing_points = self.qr_detector.detectAndDecode(frame_packing)

for i, text in enumerate(packing_texts):
    if text == "TimeGo":
        continue  # Skip TimeGo (không xảy ra trong packing_area)

    if text:  # ✅ Decode thành công
        mvd = text
        mvd_index = i

        # ✅ Tính bbox từ boundary points
        if i < len(packing_points) and packing_area_offset is not None:
            box = packing_points[i]
            # ... calculate bbox ...
            mvd_bbox = (bbox_x + offset_x, bbox_y + offset_y, bbox_w, bbox_h)
        break
```

**Logging (dòng 757-769):**
```python
if mvd and mvd != last_mvd:
    if mvd_bbox is not None:
        # ✅ Log với bbox
        log_line = f"{second},{state},{mvd},bbox:[{bbox_x},{bbox_y},{bbox_w},{bbox_h}]\n"
        log_file_handle.write(log_line)
        last_mvd = mvd
```

**Event State Update (dòng 728-732):**
```python
if mvd and mvd_bbox:
    self.last_successful_bbox = mvd_bbox  # ✅ Cache bbox
    self._update_mvd_qr_size(mvd_bbox)    # ✅ Auto-update DB
    if self.event_state['in_event']:
        self.event_state['has_mvd'] = True  # ✅ Đánh dấu có MVD
```

**Kết Luận:**
- ✅ **PASS**: Decode text thành công
- ✅ **PASS**: Tính bbox chính xác
- ✅ **PASS**: Log ghi nhận MVD + bbox
- ✅ **PASS**: Update event state (has_mvd = True)
- ✅ **PASS**: Cache bbox cho adaptive threshold

---

#### **CASE 3B: DECODE FAIL - CÓ BOUNDARY (CRITICAL CASE)**

**Frame data:**
```
Frame N+k:
  - qr_trigger_area: TimeGo vẫn bị che → state = "Off"
  - packing_area:
      - detect QR MVD (có boundary points)
      - decode FAIL → text = "" (rỗng)
      - có boundary points → bbox có thể tính được
```

**Expected Log Output:**
```
# Không log ngay lập tức
# Đợi đến khi event kết thúc (Te)
# Sau đó log qua empty event processing:
<second>,Off,,boundary:[207,800,63,60]
```

**Code Coverage:**

**Detection (dòng 344-396):**
```python
mvd_index = None
non_timego_index = None  # ✅ Track non-TimeGo QR

for i, text in enumerate(packing_texts):
    if text == "TimeGo":
        continue

    # ✅ Track first non-TimeGo (kể cả decode fail)
    if non_timego_index is None:
        non_timego_index = i

    if text:  # Decode thành công
        mvd_index = i
        break
    # ⚠️ Nếu text rỗng (decode fail) → không break, tiếp tục loop

# ✅ Return boundary points
if len(packing_points) > 0 and packing_area_offset is not None:
    if mvd_index is not None:
        boundary_points = packing_points[mvd_index]  # MVD decoded
    elif non_timego_index is not None:
        boundary_points = packing_points[non_timego_index]  # ✅ MVD detected but decode failed
        self.logger.debug(f"Using non-TimeGo boundary (decode failed)")
```

**Buffering (dòng 735-744):**
```python
# ✅ Buffer boundaries cho empty event
if self.event_state['in_event'] and not self.event_state['has_mvd'] and boundary_points is not None:
    boundary_bbox = self._calculate_bbox_from_points(boundary_points, packing_offset)
    if boundary_bbox and self._should_buffer_boundary(boundary_bbox):
        self.event_state['boundaries_buffer'].append({
            'frame': second,
            'bbox': boundary_bbox
        })
        self.event_state['last_boundary_bbox'] = boundary_bbox
        self.logger.debug(f"✓ Buffered boundary at second {second}")
```

**Smart Sampling (dòng 514-535):**
```python
def _should_buffer_boundary(self, bbox):
    """Smart sampling: chỉ buffer nếu bbox di chuyển > threshold"""
    if not self.event_state['last_boundary_bbox']:
        return True  # ✅ First boundary → luôn save

    last_bbox = self.event_state['last_boundary_bbox']
    threshold = ref_width * 0.05  # 5% của QR size

    # So sánh center positions
    distance = sqrt((curr_center - last_center)^2)
    return distance > threshold  # ✅ Chỉ buffer nếu di chuyển nhiều
```

**Empty Event Processing (dòng 537-571):**
```python
def _process_empty_event(self, te_second, log_file_handle):
    """Gọi khi event kết thúc mà không có MVD decode"""
    boundaries = self.event_state['boundaries_buffer']

    if not boundaries:
        self.logger.debug("Empty event has NO boundaries - skipping")
        return  # ❌ Nếu không có boundary nào → skip

    # ✅ Nếu có boundaries → tìm stable frames
    threshold = ref_width * 0.05
    stable_frames = self.convergence_detector.find_stable_frames(
        boundaries=boundaries,
        threshold=threshold,
        max_frames=3  # ✅ Chọn tối đa 3 frames ổn định nhất
    )

    # ✅ Log boundaries
    for frame_data in stable_frames:
        self._log_boundary(frame_data, log_file_handle)
```

**Boundary Logging với Size Filtering (dòng 573-598):**
```python
def _log_boundary(self, frame_data, log_file_handle):
    second = frame_data['frame']
    bbox = frame_data['bbox']

    # ⚠️ CRITICAL: Filter TimeGo boundaries by size
    if not self._is_mvd_size(bbox):
        self.logger.debug(f"✗ Rejected TimeGo boundary: size={bbox[2]}x{bbox[3]}")
        return  # ❌ Skip nếu size gần TimeGo hơn MVD

    # ✅ Log MVD boundary
    log_line = f"{second},Off,,boundary:[{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}]\n"
    log_file_handle.write(log_line)
    self.logger.debug(f"✓ Logged MVD boundary at second {second}")
```

**Size Filtering (dòng 199-234):**
```python
def _is_mvd_size(self, bbox):
    w, h = bbox[2], bbox[3]

    if self.expected_mvd_qr_size and self.expected_trigger_qr_size:
        mvd_w = self.expected_mvd_qr_size['width']
        mvd_h = self.expected_mvd_qr_size['height']
        trigger_w = self.expected_trigger_qr_size['width']
        trigger_h = self.expected_trigger_qr_size['height']

        # Manhattan distance
        mvd_diff = abs(w - mvd_w) + abs(h - mvd_h)
        trigger_diff = abs(w - trigger_w) + abs(h - trigger_h)

        # ✅ Accept nếu gần MVD hơn TimeGo
        is_mvd = mvd_diff < trigger_diff
        return is_mvd
    else:
        # ✅ Fallback: 100px threshold
        is_mvd = w < 100 and h < 100
        return is_mvd
```

**Convergence Detection (convergence_detector.py):**
```python
def find_stable_frames(self, boundaries, threshold, max_frames=3):
    """Tìm frames ổn định nhất từ boundary buffer"""

    # ✅ Calculate rolling variance
    for i in range(len(boundaries) - window_size + 1):
        window = boundaries[i:i + window_size]
        variance = self._calculate_position_variance(window)

    # ✅ Find minimum variance window
    stable_window = min(variances, key=lambda x: x['variance'])

    # ✅ Select evenly spaced frames
    selected = self._select_evenly_spaced(stable_window['window'], max_frames)
    return selected
```

**Kết Luận CASE 3B:**
- ✅ **PASS**: Detect boundary khi decode fail
- ✅ **PASS**: Buffer boundary vào boundaries_buffer
- ✅ **PASS**: Smart sampling (chỉ buffer khi QR di chuyển > threshold)
- ✅ **PASS**: Convergence detection (tìm frames ổn định)
- ⚠️ **CONDITIONAL PASS**: Size filtering (có thể reject nếu MVD size gần TimeGo)
- ✅ **PASS**: Log boundary sau khi event kết thúc

**Rủi Ro:**
1. **Size filtering có thể reject MVD:**
   - Nếu MVD QR có size bất thường (gần TimeGo hơn expected MVD)
   - Manhattan distance comparison có thể fail

2. **Phụ thuộc vào expected_mvd_qr_size trong DB:**
   - Nếu DB chưa có data → fallback 100px threshold
   - Có thể reject MVD lớn hơn 100px

**Khuyến Nghị:**
- Kiểm tra expected sizes trong database
- Monitor logs cho "Rejected TimeGo boundary" warnings
- Cân nhắc cải thiện size filtering logic

---

#### **CASE 3C: KHÔNG CÓ BOUNDARY - DECODE FAIL**

**Frame data:**
```
Frame N+k:
  - qr_trigger_area: TimeGo vẫn bị che → state = "Off"
  - packing_area:
      - WeChat QR detector không phát hiện QR pattern
      - decode fail → text = ""
      - KHÔNG CÓ boundary points → boundary = None
```

**Expected Behavior:**
```
# KHÔNG log gì cả (bỏ qua frame này)
# Đợi frame tiếp theo có thể detect được
```

**Code Coverage:**

**Detection (dòng 333-405):**
```python
packing_texts, packing_points = self.qr_detector.detectAndDecode(frame_packing)

# ✅ Nếu không detect được QR:
# → packing_texts = [] (empty list)
# → packing_points = [] (empty list)

if len(packing_texts) > 0:
    # ... xử lý QR ...
else:
    # ⚠️ KHÔNG có code xử lý explicit cho case này
    # Nhưng flow tự nhiên:
    # → mvd_index = None
    # → non_timego_index = None
    # → boundary_points = None
    pass

return state, mvd, mvd_bbox, boundary_points
# → return ("Off", "", None, None)  # ✅ ĐÚNG
```

**Buffering Check (dòng 735-744):**
```python
# ✅ Không buffer vì boundary_points = None
if self.event_state['in_event'] and not self.event_state['has_mvd'] and boundary_points is not None:
    # KHÔNG chạy vì boundary_points = None
    pass
```

**Empty Event Processing:**
```python
# Khi event kết thúc:
if not self.event_state['has_mvd']:
    self._process_empty_event(te_second, log_file_handle)

def _process_empty_event(...):
    boundaries = self.event_state['boundaries_buffer']

    if not boundaries:
        # ✅ Skip vì không có boundaries nào
        self.logger.debug("Empty event has NO boundaries - skipping (noise)")
        return
```

**Kết Luận CASE 3C:**
- ✅ **PASS**: Bỏ qua frame không có boundary
- ✅ **PASS**: Không buffer gì vào boundaries_buffer
- ✅ **PASS**: Nếu toàn bộ event không có boundary → log "noise event"
- ⚠️ **EXPECTED BEHAVIOR**: Đây là case hợp lệ (QR chưa hiển thị rõ/góc quay xấu)

**Nguyên Nhân Case 3C:**
1. QR chưa được dán
2. QR bị che khuất một phần
3. Góc camera không thấy QR
4. QR bị nhàu/hư hỏng
5. Frame bị mờ/motion blur

---

## Giai Đoạn 4: GIAI ĐOẠN QUÁ ĐỘ (TimeGo Decode Fail)

### 4.1 Mô Tả
- Hộp hàng được **lấy ra khỏi** vùng đóng gói
- QR TimeGo **bắt đầu lộ ra** nhưng chưa rõ
- WeChat QR detector detect được QR pattern nhưng **decode fail**

### 4.2 Dữ Liệu Phát Sinh

**Frame-by-frame:**
```
Frame N+m:
  - qr_trigger_area:
      - detect QR pattern (có boundary)
      - decode FAIL → text = "" hoặc text != "TimeGo"
      - state vẫn = "Off" (vì không decode được "TimeGo")
  - packing_area:
      - có thể vẫn thấy MVD QR
      - hoặc không còn QR nào
```

**Code Coverage:**

**TimeGo Detection (dòng 318-326):**
```python
if frame_trigger is not None and frame_trigger.size > 0:
    trigger_texts, _ = self.qr_detector.detectAndDecode(frame_trigger)
    for text in trigger_texts:
        if text == "TimeGo":  # ⚠️ Chỉ chấp nhận exact match
            state = "On"
            break
    # ✅ Nếu decode fail hoặc text != "TimeGo":
    # → state vẫn là "Off" (không thay đổi)
```

**State Update:**
```python
frame_states.append(state)  # → append "Off"

# ✅ 5 frames liên tiếp "off off off off off"
# → final_state = "Off" (không thay đổi)
# → last_state vẫn là "Off"
# → KHÔNG trigger Te event (vì final_state == last_state)
```

**Kết Luận:**
- ✅ **PASS**: Không trigger Te sớm (tránh false positive)
- ✅ **PASS**: Đợi decode thành công "TimeGo" mới chuyển On
- ✅ **EXPECTED**: Event tiếp tục (chưa kết thúc)

---

## Giai Đoạn 5: KẾT THÚC ĐÓNG GÓI (Te Event)

### 5.1 Mô Tả
- QR TimeGo **lộ ra hoàn toàn**
- Decode thành công "TimeGo"
- Trigger chuyển từ Off → On

### 5.2 Dữ Liệu Phát Sinh

**Frame-by-frame:**
```
Frame N+p:
  - qr_trigger_area:
      - detect QR TimeGo
      - decode thành công → text = "TimeGo"
      - state = "On"
  - packing_area:
      - không còn QR (hộp đã ra khỏi vùng)
```

**Log Output:**
```
<second>,On,
```

### 5.3 Code Coverage

**State Transition (dòng 797-804):**
```python
if final_state != last_state:
    # Detect Te (On state = event end)
    elif final_state == "On" and self.event_state['in_event']:
        # ✅ Process empty event if no MVD detected
        if not self.event_state['has_mvd']:
            self._process_empty_event(second, log_file_handle)  # ✅ Chạy empty event

        # ✅ Reset state
        self.event_state['in_event'] = False
        self.logger.debug(f"Event ended (Te) at second {second}, has_mvd={self.event_state['has_mvd']}")
```

**Log State Change (dòng 806-808):**
```python
log_line = f"{second},{final_state},\n"
log_file_handle.write(log_line)  # ✅ Log "On" state
self.logger.info(f"Log second {second}: {final_state}")
```

**Empty Event Processing:**
```python
# ✅ Nếu has_mvd = False (chỉ có CASE 3B hoặc 3C trong event):
self._process_empty_event(second, log_file_handle)
    → boundaries = self.event_state['boundaries_buffer']
    → find_stable_frames()
    → _log_boundary() cho từng stable frame
    → Log: "<second>,Off,,boundary:[x,y,w,h]"
```

**Kết Luận:**
- ✅ **PASS**: Detect Te chính xác (Off → On)
- ✅ **PASS**: Process empty event nếu không có MVD decode
- ✅ **PASS**: Log stable boundaries cho failed decode cases
- ✅ **PASS**: Reset event state sau khi kết thúc
- ✅ **PASS**: Log "On" state để đánh dấu Te

---

## Tổng Kết Coverage Analysis

### A. Các Giai Đoạn Đã Xử Lý Đầy Đủ

| Giai Đoạn | Mô Tả | Status | Note |
|-----------|-------|--------|------|
| **1. Trạng Thái Ban Đầu** | TimeGo On, chờ hàng | ✅ PASS | State detection OK |
| **2. Bắt Đầu Đóng Gói (Ts)** | On → Off | ✅ PASS | Event init OK |
| **3A. MVD Decode OK** | Có text + boundary | ✅ PASS | Log MVD + bbox |
| **3B. MVD Decode Fail + Boundary** | Không text, có boundary | ⚠️ CONDITIONAL | Size filter có thể reject |
| **3C. Không Boundary** | Không detect QR | ✅ PASS | Bỏ qua (expected) |
| **4. TimeGo Decode Fail** | QR lộ ra chưa rõ | ✅ PASS | Không trigger Te sớm |
| **5. Kết Thúc (Te)** | Off → On | ✅ PASS | Empty event processing |

### B. Điểm Mạnh

1. ✅ **Event Lifecycle Management**: Hoàn chỉnh (Ts, Ts→Te, Te)
2. ✅ **Dual ROI Detection**: Tách biệt trigger và MVD
3. ✅ **Smart Buffering**: Chỉ buffer khi QR di chuyển > threshold
4. ✅ **Convergence Detection**: Tìm frames ổn định bằng variance analysis
5. ✅ **Auto-Update Expected Size**: Học từ successful decodes
6. ✅ **Fallback Logic**: 100px threshold khi không có DB data

### C. Điểm Yếu / Rủi Ro

#### 1. **Size Filtering Logic (CASE 3B)**
**Vấn đề:**
- Manhattan distance có thể reject MVD nếu size bất thường
- Ví dụ: MVD = 120x130, expected MVD = 57x58, TimeGo = 176x181
  - mvd_diff = |120-57| + |130-58| = 135
  - trigger_diff = |120-176| + |130-181| = 107
  - → mvd_diff > trigger_diff → **REJECT** (sai!)

**Impact:**
- Boundary của MVD bị bỏ qua
- Empty event không log gì (noise event)

**Khuyến Nghị:**
- Thêm tolerance range cho MVD size
- Dùng percentage-based threshold thay vì absolute distance
- Log rejected boundaries để debug

#### 2. **Phụ Thuộc Database Expected Sizes**
**Vấn đề:**
- Nếu `expected_mvd_qr_size` hoặc `expected_trigger_qr_size` = NULL
- → Fallback 100px threshold
- → Có thể reject MVD lớn hơn 100px

**Impact:**
- Boundary của MVD lớn bị reject

**Khuyến Nghị:**
- Ensure database có data cho tất cả cameras
- Monitor fallback threshold usage

#### 3. **TimeGo Decode Transition**
**Vấn đề:**
- Giai đoạn 4: TimeGo decode fail có thể kéo dài nhiều frames
- Nếu QR di chuyển trong lúc này → buffer nhiều boundaries không cần thiết

**Impact:**
- boundaries_buffer phình to
- Performance overhead

**Khuyến Nghị:**
- Đã có smart sampling (5% threshold) để giảm overhead
- Monitor buffer size trong logs

### D. Test Cases Khuyến Nghị

#### Test 1: Normal Flow (CASE 3A)
```
Ts → Dán MVD → Decode OK → Te
Expected: Log MVD + bbox
```

#### Test 2: Failed Decode with Boundary (CASE 3B)
```
Ts → Dán MVD → Decode Fail (có boundary) → Te
Expected: Log 3 stable boundaries
Check: Size filtering không reject
```

#### Test 3: No Boundary (CASE 3C)
```
Ts → Không dán MVD → Te
Expected: Log "noise event", không có boundary
```

#### Test 4: Large MVD QR
```
Ts → Dán MVD lớn (>100px) → Decode Fail → Te
Expected: Boundary được log (không bị reject)
Check: Size filtering với large QR
```

#### Test 5: Multiple MVD in Event
```
Ts → Dán MVD 1 (decode OK) → Dán MVD 2 (decode fail) → Te
Expected: Log MVD 1, không log MVD 2 boundary (vì has_mvd = True)
```

---

## ⚠️ PHÁT HIỆN CRITICAL: TimeGo Boundary Lẫn Vào MVD Buffer

### Vấn Đề Nghiêm Trọng

**Phát hiện:** Code KHÔNG phân biệt được TimeGo vs MVD boundaries trước khi lọc size!

#### Scenario Thực Tế:

**Giai đoạn 4-5: TimeGo decode fail → success**

```
Frame 100-101: (TimeGo đang lộ ra, chưa rõ)
  - qr_trigger_area: TimeGo decode FAIL → state = "Off"
  - packing_area: TimeGo CŨNG xuất hiện (ROI chồng lấn hoặc QR di chuyển)
      → detect QR, decode FAIL → text = ""
      → boundary_points CÓ DATA!

Frame 102:
  - qr_trigger_area: TimeGo decode SUCCESS → state = "On"
  - packing_area: TimeGo decode SUCCESS → text = "TimeGo" → skip
```

#### Code Xử Lý Như Thế Nào?

```python
# process_frame(), dòng 344-398
for i, text in enumerate(packing_texts):
    if text == "TimeGo":
        continue  # ← CHỈ SKIP KHI DECODE THÀNH CÔNG!

    # ⚠️ NHƯNG NẾU DECODE FAIL (text = ""):
    # → KHÔNG skip!
    # → non_timego_index = i  ← LƯU INDEX CỦA TIMEGO (SAI!)

    if non_timego_index is None:
        non_timego_index = i  # ← Lần đầu tiên KHÔNG PHẢI "TimeGo" text
```

**Kết quả:**
- `boundary_points = packing_points[non_timego_index]` ← **TIMEGO BOUNDARY!**
- Buffer vào `boundaries_buffer` ← **TimeGo lẫn vào MVD buffer!**
- Duy nhất size filtering có thể ngăn chặn ← **Single Point of Failure!**

#### Khi Nào TimeGo Rơi Vào packing_area?

1. **ROI Chồng Lấn**: `qr_trigger_area` và `packing_area` overlap
2. **QR Di Chuyển**: Hộp hàng/tay người đẩy TimeGo vào packing_area
3. **Camera Góc Rộng**: 2 ROI gần nhau, cùng thấy TimeGo

#### Hậu Quả:

**Nếu size filtering FAIL:**
```
# Log sai hoàn toàn:
<second>,Off,,boundary:[x,y,176,181]  ← TimeGo boundary, KHÔNG PHẢI MVD!
```

**Impact:**
- AI processing nhận sai input (TimeGo thay vì MVD)
- Waste resources
- Data bị nhiễu

### Hàng Rào Phòng Thủ Duy Nhất: Size Filtering

**File:** `frame_sampler_trigger.py:587`

```python
def _log_boundary(self, frame_data, log_file_handle):
    if not self._is_mvd_size(bbox):
        return  # ← DUY NHẤT CÁCH LỌC TIMEGO!
```

**Độ tin cậy:**
- ⚠️ Manhattan distance có thể fail với edge cases
- ⚠️ Phụ thuộc database expected sizes
- ⚠️ Không có backup logic

### Khuyến Nghị URGENT

#### 1. **Lọc Size SỚM HƠN** (trong process_frame)

```python
# Đề xuất: Filter TRƯỚC KHI chọn non_timego_index
for i, text in enumerate(packing_texts):
    if text == "TimeGo":
        continue

    # ✅ THÊM: Skip TimeGo-sized QR (kể cả decode fail)
    if i < len(packing_points):
        bbox = self._calculate_bbox_from_points(packing_points[i], packing_offset)
        if bbox and not self._is_mvd_size(bbox):
            continue  # ← LỌC SỚM!

    if non_timego_index is None:
        non_timego_index = i
```

#### 2. **Validate TRƯỚC KHI Buffer**

```python
# Trước khi buffer vào boundaries_buffer:
if boundary_bbox and self._should_buffer_boundary(boundary_bbox):
    # ✅ THÊM: Validate size
    if not self._is_mvd_size(boundary_bbox):
        self.logger.debug("Rejected TimeGo boundary before buffering")
        return

    self.event_state['boundaries_buffer'].append(...)
```

#### 3. **Strengthen Size Filtering**

```python
def _is_mvd_size(self, bbox):
    # THÊM: Tolerance range + explicit rejection
    if self.expected_mvd_qr_size:
        mvd_w = self.expected_mvd_qr_size['width']
        tolerance = mvd_w * 0.3  # 30% tolerance

        # MVD range: accept
        if abs(w - mvd_w) <= tolerance:
            return True

        # Quá lớn: definitely TimeGo
        if w > mvd_w * 1.5:
            return False

        # Else: distance comparison
```

---

## Kết Luận

### Coverage Summary (CẬP NHẬT)
- **Giai Đoạn 1-2**: ✅ 100% coverage
- **Giai Đoạn 3A**: ✅ 100% coverage
- **Giai Đoạn 3B**: ⚠️ 70% coverage (**TimeGo contamination risk**)
- **Giai Đoạn 3C**: ✅ 100% coverage
- **Giai Đoạn 4-5**: ⚠️ 80% coverage (**TimeGo decode fail buffer risk**)

### Tổng Quan (CẬP NHẬT)

Code hiện tại **XỬ LÝ ĐƯỢC** hầu hết trường hợp, nhưng có **LỖ HỔNG NGHIÊM TRỌNG**:

**❌ CRITICAL ISSUE:**
- TimeGo decode fail boundaries bị buffer vào MVD buffer
- KHÔNG có logic phân biệt TimeGo vs MVD trước size filtering
- **Single Point of Failure**: Size filtering duy nhất

**Điểm cần lưu ý (CẬP NHẬT):**
1. ❌ **CRITICAL**: TimeGo boundaries có thể lẫn vào MVD buffer
2. ⚠️ Size filtering là hàng rào duy nhất (không đủ tin cậy)
3. ⚠️ Cần implement early filtering trong process_frame()
4. ✅ Kiểm tra expected sizes trong database
5. ✅ Monitor logs cho "Rejected TimeGo boundary" warnings

### Next Steps (CẬP NHẬT - URGENT)

**TRƯỚC KHI CHẠY PRODUCTION:**
1. 🔴 **URGENT**: Implement early size filtering trong process_frame()
2. 🔴 **URGENT**: Validate boundaries trước khi buffer
3. 🟡 Kiểm tra database expected sizes
4. 🟡 Test với video có ROI chồng lấn
5. 🟡 Monitor logs cho TimeGo contamination

**SAU KHI FIX:**
1. ✅ Chạy test với video thực tế
2. ✅ Verify không có TimeGo boundaries trong MVD logs
3. ✅ Performance testing

---

**⚠️ Tài liệu này highlight CRITICAL ISSUE cần fix URGENT trước khi deploy production!**
