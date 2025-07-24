# RTSP Video Download - Hướng dẫn & Xử lý lỗi

## Quy trình Download Video qua RTSP

### 1. Chuẩn bị ONVIF Connection
```bash
# Khởi động ONVIF service
docker exec -d onvif-mock-fixed bash -c "
export INTERFACE=eth0
export MP4FILE=/tmp/video2.mp4
python3 /onvif-camera-mock/main.py
"

# Verify service running
docker exec -it onvif-mock-fixed ps aux | grep python
```

### 2. Lấy RTSP Stream URL từ ONVIF
```python
import socket

def get_rtsp_url():
    soap_request = '''POST /onvif/media_service HTTP/1.1
Host: localhost:1000
Content-Type: application/soap+xml; charset=utf-8
Content-Length: 500

<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:trt="http://www.onvif.org/ver10/media/wsdl">
<soap:Header/>
<soap:Body>
<trt:GetStreamUri>
<trt:StreamSetup>
<tt:Stream xmlns:tt="http://www.onvif.org/ver10/schema">RTP-Unicast</tt:Stream>
<tt:Transport xmlns:tt="http://www.onvif.org/ver10/schema">
<tt:Protocol>RTSP</tt:Protocol>
</tt:Transport>
</trt:StreamSetup>
<trt:ProfileToken>RTSP</trt:ProfileToken>
</trt:GetStreamUri>
</soap:Body>
</soap:Envelope>'''

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    try:
        s.connect(('127.0.0.1', 1000))
        s.sendall(soap_request.encode())
        response = s.recv(4096)
        return response.decode()
    finally:
        s.close()
```

**Kết quả mong đợi:**
```xml
<trt:GetStreamUriResponse>
    <trt:MediaUri>
        <tt:Uri>rtsp://172.17.0.2:8554/stream1</tt:Uri>
    </trt:MediaUri>
</trt:GetStreamUriResponse>
```

### 3. Download Video bằng FFmpeg

#### Lệnh download cơ bản:
```bash
# Download 10 giây video
docker exec -it onvif-mock-fixed ffmpeg \
    -i rtsp://127.0.0.1:8554/stream1 \
    -t 10 \
    -c copy \
    /tmp/downloaded_video.mp4 \
    -y
```

#### Tham số FFmpeg quan trọng:
- `-i`: Input RTSP URL
- `-t 10`: Duration (10 seconds)
- `-c copy`: Copy codec without re-encoding
- `-y`: Overwrite output file
- `-rtsp_transport tcp`: Force TCP transport (nếu UDP fails)

### 4. Verify Download Result
```bash
# Check file size
docker exec -it onvif-mock-fixed ls -lh /tmp/downloaded_video.mp4

# Get video information
docker exec -it onvif-mock-fixed ffprobe /tmp/downloaded_video.mp4

# Copy to host
docker cp onvif-mock-fixed:/tmp/downloaded_video.mp4 ./downloaded_from_onvif.mp4
```

## Các lỗi thường gặp và cách khắc phục

### 🔴 Lỗi 1: Connection Timeout
```
Error: timed out
curl: (28) Connection timed out after 5005 milliseconds
```

**Nguyên nhân:**
- ONVIF service chưa start
- Service chạy nhưng bind sai interface
- Port không accessible từ bên ngoài container

**Khắc phục:**
```bash
# Check service status
docker exec -it onvif-mock-fixed ps aux | grep python

# Check port listening
docker exec -it onvif-mock-fixed ss -tlnp

# Restart service với đúng interface
docker exec -it onvif-mock-fixed pkill python3
docker exec -d onvif-mock-fixed bash -c "export INTERFACE=eth0 && python3 /onvif-camera-mock/main.py"
```

### 🔴 Lỗi 2: "No interface such as 'eth0' provided"
```
No interface such as 'eth0' or 'eno1' provided
```

**Nguyên nhân:**
- Environment variable INTERFACE không được set
- Code check interface theo cách cũ

**Khắc phục:**
```bash
# Check available interfaces
docker exec -it onvif-mock-fixed ip link show

# Set proper environment variable
export INTERFACE=eth0
# Hoặc
docker exec -d onvif-mock-fixed bash -c "INTERFACE=eth0 python3 /onvif-camera-mock/main.py"
```

### 🔴 Lỗi 3: RTSP Stream Connection Failed
```
[rtsp @ 0x...] method DESCRIBE failed: 404 Not Found
```

**Nguyên nhân:**
- Wrong RTSP URL path
- RTSP service chưa start
- Video file không tồn tại

**Khắc phục:**
```bash
# Check correct RTSP URL from ONVIF
# URL thường là: rtsp://172.17.0.2:8554/stream1 (not /stream)

# Verify video file exists
docker exec -it onvif-mock-fixed ls -la /tmp/video*.mp4

# Test RTSP with VLC first before FFmpeg
```

### 🔴 Lỗi 4: FFmpeg Permission Denied
```
Permission denied
```

**Khắc phục:**
```bash
# Install FFmpeg trong container
docker exec -it onvif-mock-fixed apt update && apt install -y ffmpeg

# Check write permission
docker exec -it onvif-mock-fixed touch /tmp/test_write
```

### 🔴 Lỗi 5: Video Format Issues
```
[h264 @ 0x...] no frame!
```

**Khắc phục:**
```bash
# Thêm format options
ffmpeg -i rtsp://127.0.0.1:8554/stream1 \
    -t 10 \
    -c:v libx264 \
    -c:a aac \
    -f mp4 \
    /tmp/downloaded_video.mp4 \
    -y
```

### 🔴 Lỗi 6: Container Network Issues
```
No route to host
```

**Khắc phục:**
```bash
# Check container IP
docker inspect onvif-mock-fixed | grep IPAddress

# Test từ trong container thay vì từ host
docker exec -it onvif-mock-fixed curl localhost:1000

# Use localhost thay vì container IP cho internal calls
```

## Best Practices cho Production

### 1. Error Handling trong Code
```python
import subprocess
import logging

def download_rtsp_video(rtsp_url, output_path, duration=10):
    try:
        cmd = [
            'ffmpeg',
            '-i', rtsp_url,
            '-t', str(duration),
            '-c', 'copy',
            '-y',
            output_path
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=duration + 30  # Extra timeout buffer
        )
        
        if result.returncode == 0:
            logging.info(f"Video downloaded successfully: {output_path}")
            return True
        else:
            logging.error(f"FFmpeg error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logging.error("FFmpeg timeout - video download failed")
        return False
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return False
```

### 2. Resource Management
```bash
# Cleanup old videos
find /tmp -name "*.mp4" -mtime +1 -delete

# Monitor disk space
df -h /tmp

# Limit video duration để tránh files quá lớn
MAX_DURATION=60  # seconds
```

### 3. Network Optimization
```bash
# Sử dụng TCP transport cho stable connection
ffmpeg -rtsp_transport tcp -i rtsp://... 

# Buffer size adjustment
ffmpeg -rtbufsize 100M -i rtsp://...

# Reconnect on failure
ffmpeg -reconnect 1 -reconnect_streamed 1 -i rtsp://...
```

## Kết quả mong đợi khi thành công

### Video Specifications
- **Format**: MP4 container, H.264 video codec
- **Resolution**: 1080x1920 (portrait) hoặc tùy theo source
- **Framerate**: 29.97 fps
- **Duration**: Đúng thời gian yêu cầu (10s → 10.14s)
- **Bitrate**: ~3063 kb/s
- **File size**: ~3.7MB cho 10 seconds

### Success Indicators
```bash
# File exists và có size > 0
ls -lh downloaded_video.mp4
# Output: -rw-r--r-- 1 root root 3.7M Jul 14 12:45 downloaded_video.mp4

# Video info valid
ffprobe downloaded_video.mp4 2>&1 | grep Duration
# Output: Duration: 00:00:10.14, start: 0.000000, bitrate: 3063 kb/s

# No errors in logs
echo $?
# Output: 0
```

## Monitoring & Debugging Commands

```bash
# Real-time monitoring during download
docker exec -it onvif-mock-fixed tail -f /var/log/*.log

# Check network connections
docker exec -it onvif-mock-fixed netstat -tulnp

# Monitor resource usage
docker stats onvif-mock-fixed

# Debug RTSP stream
docker exec -it onvif-mock-fixed ffplay -rtsp_transport tcp rtsp://127.0.0.1:8554/stream1
```

---

**Lưu ý quan trọng:** Luôn test từ trong container trước (`127.0.0.1`) trước khi test từ bên ngoài (`172.17.0.2`) để tránh network issues.