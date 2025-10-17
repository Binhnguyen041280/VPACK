'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  Box,
  Text,
  HStack,
  VStack,
  Spinner,
  Alert,
  AlertIcon,
  useColorModeValue,
  Icon,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  Button
} from '@chakra-ui/react';
import { MdVideocam, MdSchedule, MdFileDownload } from 'react-icons/md';

interface QRDetection {
  timestamp: number;
  tracking_code: string;
  bbox: {
    x: number;
    y: number;
    w: number;
    h: number;
  };
  magnifier_roi: {
    x: number;
    y: number;
    w: number;
    h: number;
  };
}

interface VideoPlayerModalProps {
  isOpen: boolean;
  onClose: () => void;
  videoPath: string;
  eventId?: number;
  eventInfo?: {
    tracking_code: string;
    camera_name: string;
    duration: number;
  };
}

const VideoPlayerModal: React.FC<VideoPlayerModalProps> = ({
  isOpen,
  onClose,
  videoPath,
  eventId,
  eventInfo
}) => {
  // State
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isBuffering, setIsBuffering] = useState(false);
  const [qrDetections, setQrDetections] = useState<QRDetection[]>([]);
  const [activeMagnifier, setActiveMagnifier] = useState<QRDetection | null>(null);
  const [zoomFactor, setZoomFactor] = useState(1.0); // Adjustable zoom: 1.0x - 4.0x (default: 1.0x no zoom)
  const [captureOffset, setCaptureOffset] = useState({ x: 0, y: 0 }); // User-controlled offset from QR center
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Refs
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Theme colors
  const modalBg = useColorModeValue('white', 'gray.800');
  const headerBg = useColorModeValue('gray.50', 'gray.700');
  const textColor = useColorModeValue('gray.700', 'gray.200');
  const accentColor = useColorModeValue('blue.600', 'blue.400');

  // Video event handlers
  const handleVideoLoad = useCallback(() => {
    console.log('🎬 Video loaded successfully');
    setIsLoading(false);
    setError(null);
  }, []);

  const handleVideoError = useCallback((e: React.SyntheticEvent<HTMLVideoElement, Event>) => {
    const video = e.currentTarget;
    const errorMessage = video.error
      ? `Video error code: ${video.error.code} - ${video.error.message || 'Unknown error'}`
      : 'Unknown video error';

    console.error('🚨 Video error:', errorMessage);
    setError(errorMessage);
    setIsLoading(false);
  }, []);

  const handleWaiting = useCallback(() => {
    setIsBuffering(true);
  }, []);

  const handleCanPlay = useCallback(() => {
    setIsBuffering(false);
  }, []);

  const handleLoadedMetadata = useCallback(() => {
    // Set playback rate to 2x when metadata is loaded
    if (videoRef.current) {
      videoRef.current.playbackRate = 2.0;
      console.log('⚡ Playback rate set to 2x');
    }
  }, []);

  // Reset state when modal opens/closes or video changes
  useEffect(() => {
    if (isOpen) {
      setIsLoading(true);
      setError(null);
      setIsBuffering(false);
    }
  }, [isOpen, videoPath]);

  // Fetch QR timestamps when modal opens with eventId
  useEffect(() => {
    if (!isOpen || !eventId) {
      setQrDetections([]);
      return;
    }

    const fetchQRTimestamps = async () => {
      try {
        console.log(`🔍 Fetching QR timestamps for event ${eventId}...`);
        const response = await fetch(`http://localhost:8080/api/trace/event/${eventId}/qr-timestamps`);

        if (!response.ok) {
          console.error('Failed to fetch QR timestamps:', response.status);
          return;
        }

        const data = await response.json();
        console.log(`✅ Loaded ${data.total_count} QR detections`, data.qr_detections);
        setQrDetections(data.qr_detections || []);
      } catch (error) {
        console.error('Error fetching QR timestamps:', error);
      }
    };

    fetchQRTimestamps();
  }, [isOpen, eventId]);

  // Monitor video time and activate magnifier
  useEffect(() => {
    if (!videoRef.current || qrDetections.length === 0) return;

    const video = videoRef.current;
    const PRE_DISPLAY_TIME = 2; // Show magnifier 2 seconds before QR detection

    const handleTimeUpdate = () => {
      const currentTime = video.currentTime;

      // Find active QR detection:
      // - Start: 2 seconds before QR timestamp
      // - End: Until end of video (no time limit)
      const activeQR = qrDetections.find(qr => {
        const startTime = qr.timestamp - PRE_DISPLAY_TIME;
        return currentTime >= startTime;
      });

      // Reset capture offset when switching to new QR detection
      if (activeQR && activeQR !== activeMagnifier) {
        setCaptureOffset({ x: 0, y: 0 });
      }

      setActiveMagnifier(activeQR || null);
    };

    video.addEventListener('timeupdate', handleTimeUpdate);

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate);
    };
  }, [qrDetections, activeMagnifier]);

  // Render magnifier canvas with 60fps animation
  useEffect(() => {
    if (!activeMagnifier || !videoRef.current || !canvasRef.current) {
      // Clear animation if magnifier is inactive
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
      return;
    }

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const video = videoRef.current;

    if (!ctx) return;

    const bbox = activeMagnifier.bbox;
    const MAGNIFIER_SIZE = 300;

    // Calculate capture size based on zoom factor
    // zoomFactor controls how much we zoom: higher = more zoom
    const CAPTURE_SIZE = MAGNIFIER_SIZE / zoomFactor;

    // Calculate QR center for centering the capture
    const qr_center_x = bbox.x + bbox.w / 2;
    const qr_center_y = bbox.y + bbox.h / 2;

    // Set canvas size
    canvas.width = MAGNIFIER_SIZE;
    canvas.height = MAGNIFIER_SIZE;

    const drawMagnifier = () => {
      if (!activeMagnifier) return;

      // Clear canvas
      ctx.clearRect(0, 0, MAGNIFIER_SIZE, MAGNIFIER_SIZE);

      // Calculate capture area with user offset (dragging)
      // captureOffset.x/y allows user to pan the magnifier view
      const capture_x = Math.max(0, qr_center_x - CAPTURE_SIZE / 2 + captureOffset.x);
      const capture_y = Math.max(0, qr_center_y - CAPTURE_SIZE / 2 + captureOffset.y);

      // Draw magnified ROI from video
      ctx.drawImage(
        video,
        capture_x, capture_y, CAPTURE_SIZE, CAPTURE_SIZE, // Source: dynamic based on zoom + offset
        0, 0, MAGNIFIER_SIZE, MAGNIFIER_SIZE // Destination: fixed 300x300
      );

      // Draw border
      ctx.strokeStyle = '#FFD700'; // Gold color
      ctx.lineWidth = 4;
      ctx.strokeRect(0, 0, MAGNIFIER_SIZE, MAGNIFIER_SIZE);

      // Draw drag hint when not dragging
      if (!isDragging) {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
        ctx.fillRect(0, 0, MAGNIFIER_SIZE, 25);
        ctx.fillStyle = 'white';
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('🖱️ Drag to pan', MAGNIFIER_SIZE / 2, 17);
      }

      // Request next frame
      animationFrameRef.current = requestAnimationFrame(drawMagnifier);
    };

    // Start animation loop
    animationFrameRef.current = requestAnimationFrame(drawMagnifier);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
    };
  }, [activeMagnifier, zoomFactor, captureOffset, isDragging]); // Re-render when zoom or offset changes

  // Mouse drag handlers for panning magnifier
  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDragging) return;

    const deltaX = e.clientX - dragStart.x;
    const deltaY = e.clientY - dragStart.y;

    // Update capture offset (inverse direction for intuitive panning)
    setCaptureOffset(prev => ({
      x: prev.x - deltaX,
      y: prev.y - deltaY
    }));

    setDragStart({ x: e.clientX, y: e.clientY });
  }, [isDragging, dragStart]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Export zoom video handler
  const [isExporting, setIsExporting] = useState(false);
  const [exportStatus, setExportStatus] = useState<string | null>(null);

  const handleExportZoomVideo = useCallback(async () => {
    if (!activeMagnifier || !eventId) return;

    setIsExporting(true);
    setExportStatus('Exporting zoom video...');

    try {
      const bbox = activeMagnifier.bbox;
      const MAGNIFIER_SIZE = 300;
      const CAPTURE_SIZE = MAGNIFIER_SIZE / zoomFactor;

      // Calculate ROI coordinates (same logic as canvas rendering)
      const qr_center_x = bbox.x + bbox.w / 2;
      const qr_center_y = bbox.y + bbox.h / 2;
      const crop_x = Math.max(0, qr_center_x - CAPTURE_SIZE / 2 + captureOffset.x);
      const crop_y = Math.max(0, qr_center_y - CAPTURE_SIZE / 2 + captureOffset.y);

      // Prepare request payload
      const payload = {
        event_id: eventId,
        crop_params: {
          x: Math.round(crop_x),
          y: Math.round(crop_y),
          w: Math.round(CAPTURE_SIZE),
          h: Math.round(CAPTURE_SIZE)
        },
        zoom_factor: zoomFactor,
        qr_timestamp: activeMagnifier.timestamp  // QR detection timestamp (relative to event start)
      };

      console.log('🎬 Exporting zoom video:', payload);

      // Call backend API
      const response = await fetch('http://localhost:8080/export-zoom-video', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Export failed');
      }

      console.log('✅ Zoom video exported:', data);
      setExportStatus(`Exported: ${data.filename}`);

      // Clear status after 3 seconds
      setTimeout(() => {
        setExportStatus(null);
      }, 3000);

    } catch (error) {
      console.error('❌ Export error:', error);
      setExportStatus(`Export failed: ${error instanceof Error ? error.message : 'Unknown error'}`);

      // Clear error after 5 seconds
      setTimeout(() => {
        setExportStatus(null);
      }, 5000);
    } finally {
      setIsExporting(false);
    }
  }, [activeMagnifier, eventId, zoomFactor, captureOffset]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (videoRef.current) {
        videoRef.current.pause();
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  // Build video URL
  const videoUrl = videoPath
    ? `http://localhost:8080/api/config/step4/roi/stream-video?video_path=${encodeURIComponent(videoPath)}`
    : '';

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="6xl" isCentered>
      <ModalOverlay bg="blackAlpha.800" />
      <ModalContent bg={modalBg} maxW="90vw" maxH="90vh">
        {/* Header with event info */}
        {eventInfo && (
          <ModalHeader bg={headerBg} borderTopRadius="md">
            <HStack spacing={6} wrap="wrap">
              <Text fontSize="lg" fontWeight="bold" color={accentColor}>
                📦 {eventInfo.tracking_code}
              </Text>

              <HStack spacing={2}>
                <Icon as={MdVideocam} color="blue.500" boxSize={4} />
                <Text fontSize="sm" color={textColor}>
                  {eventInfo.camera_name}
                </Text>
              </HStack>

              <HStack spacing={2}>
                <Icon as={MdSchedule} color="green.500" boxSize={4} />
                <Text fontSize="sm" color={textColor}>
                  {eventInfo.duration}s
                </Text>
              </HStack>

              <Text fontSize="sm" color="orange.500" fontWeight="medium">
                ⚡ Playing at 2x speed
              </Text>
            </HStack>
          </ModalHeader>
        )}

        <ModalCloseButton />

        <ModalBody p={0}>
          <Box position="relative" w="100%" h="75vh" bg="black">
            {/* Loading State */}
            {isLoading && (
              <Box
                position="absolute"
                top="50%"
                left="50%"
                transform="translate(-50%, -50%)"
                zIndex={10}
              >
                <VStack spacing={4}>
                  <Spinner size="xl" color="white" />
                  <Text color="white" fontSize="md">
                    Loading video...
                  </Text>
                </VStack>
              </Box>
            )}

            {/* Error State */}
            {error && (
              <Box
                position="absolute"
                top="50%"
                left="50%"
                transform="translate(-50%, -50%)"
                w="80%"
                zIndex={10}
              >
                <Alert status="error" borderRadius="md">
                  <AlertIcon />
                  <VStack align="start" flex="1" spacing={2}>
                    <Text fontWeight="bold">Video Error</Text>
                    <Text fontSize="sm">{error}</Text>
                  </VStack>
                </Alert>
              </Box>
            )}

            {/* Video Element */}
            {videoUrl && (
              <video
                ref={videoRef}
                lang="en"
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'contain',
                  backgroundColor: '#000'
                }}
                src={videoUrl}
                autoPlay
                controls
                controlsList="nodownload"
                playsInline
                preload="metadata"
                onLoadedData={handleVideoLoad}
                onLoadedMetadata={handleLoadedMetadata}
                onError={handleVideoError}
                onWaiting={handleWaiting}
                onCanPlay={handleCanPlay}
              />
            )}

            {/* Buffering Overlay */}
            {isBuffering && (
              <Box
                position="absolute"
                top="50%"
                left="50%"
                transform="translate(-50%, -50%)"
                zIndex={5}
              >
                <VStack spacing={3}>
                  <Spinner size="lg" color="white" thickness="4px" />
                  <Text color="white" fontSize="sm">
                    Buffering...
                  </Text>
                </VStack>
              </Box>
            )}

            {/* Magnifying Glass Canvas with Zoom Control */}
            {activeMagnifier && (
              <VStack
                position="absolute"
                top="20px"
                right="20px"
                zIndex={10}
                spacing={2}
                align="stretch"
              >
                {/* Canvas */}
                <Box
                  borderRadius="md"
                  overflow="hidden"
                  boxShadow="0 0 20px rgba(255, 215, 0, 0.6)"
                  animation="fadeIn 0.3s ease-in"
                  cursor={isDragging ? 'grabbing' : 'grab'}
                >
                  <canvas
                    ref={canvasRef}
                    style={{
                      display: 'block',
                      width: '300px',
                      height: '300px'
                    }}
                    onMouseDown={handleMouseDown}
                    onMouseMove={handleMouseMove}
                    onMouseUp={handleMouseUp}
                    onMouseLeave={handleMouseUp}
                  />
                </Box>

                {/* Zoom Slider */}
                <Box
                  bg="rgba(0, 0, 0, 0.8)"
                  p={3}
                  borderRadius="md"
                  boxShadow="0 2px 8px rgba(0, 0, 0, 0.3)"
                  w="300px"
                >
                  <HStack spacing={3} align="center">
                    <Text color="white" fontSize="xs" fontWeight="bold" minW="60px">
                      Zoom {zoomFactor.toFixed(1)}x
                    </Text>
                    <Slider
                      aria-label="magnifier-zoom"
                      min={1.0}
                      max={4}
                      step={0.1}
                      value={zoomFactor}
                      onChange={(val) => setZoomFactor(val)}
                      colorScheme="yellow"
                      flex="1"
                    >
                      <SliderTrack bg="gray.700">
                        <SliderFilledTrack bg="#FFD700" />
                      </SliderTrack>
                      <SliderThumb boxSize={4} bg="#FFD700" />
                    </Slider>
                  </HStack>
                </Box>

                {/* Export Zoom Video Button */}
                <Button
                  leftIcon={<Icon as={MdFileDownload} />}
                  colorScheme="blue"
                  size="sm"
                  w="300px"
                  onClick={handleExportZoomVideo}
                  isLoading={isExporting}
                  loadingText="Exporting..."
                  isDisabled={isExporting}
                >
                  Export Zoom Video ({zoomFactor.toFixed(1)}x)
                </Button>

                {/* Export Status Message */}
                {exportStatus && (
                  <Box
                    bg={exportStatus.includes('failed') ? 'rgba(229, 62, 62, 0.9)' : 'rgba(72, 187, 120, 0.9)'}
                    p={2}
                    borderRadius="md"
                    w="300px"
                  >
                    <Text color="white" fontSize="xs" textAlign="center">
                      {exportStatus}
                    </Text>
                  </Box>
                )}
              </VStack>
            )}
          </Box>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default VideoPlayerModal;
