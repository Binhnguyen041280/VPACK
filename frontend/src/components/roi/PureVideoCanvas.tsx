/**
 * PureVideoCanvas Component
 * HTML5 video player with integrated ROI overlay - no controls
 * Complete video + ROI solution in single component
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Box,
  Alert,
  AlertIcon,
  Text,
  VStack,
  Spinner,
  useColorModeValue
} from '@chakra-ui/react';
import CanvasOverlay, { ROIData, HandLandmarks } from './CanvasOverlay';

// Height breakpoints for adaptive behavior (copied from CanvasMessage.tsx)
type HeightMode = 'compact' | 'normal' | 'spacious';

interface AdaptiveConfig {
  mode: HeightMode;
  fontSize: {
    header: string;
    title: string;
    body: string;
    small: string;
  };
  spacing: {
    section: string;
    item: string;
    padding: string;
  };
  showOptional: boolean;
}

// Video metadata interface
interface VideoMetadata {
  filename: string;
  path: string;
  duration_seconds: number;
  duration_formatted: string;
  frame_count: number;
  fps: number;
  resolution: {
    width: number;
    height: number;
    aspect_ratio: number;
  };
  size_mb: number;
  codec: string;
}

// Component props interface
interface PureVideoCanvasProps {
  videoPath: string;
  width: number;
  height: number;
  className?: string;
  autoPlay?: boolean;
  muted?: boolean;
  onMetadataLoaded?: (metadata: VideoMetadata) => void;
  onTimeUpdate?: (currentTime: number, duration: number) => void;
  onVideoRef?: (ref: HTMLVideoElement | null) => void;
  
  // Adaptive config props (copied from CanvasMessage.tsx pattern)
  adaptiveConfig?: AdaptiveConfig;
  availableHeight?: number;
  
  // ROI props
  rois?: ROIData[];
  selectedROIId?: string | null;
  hoveredROIId?: string | null;
  currentROIType?: string;
  currentROILabel?: string;
  disabled?: boolean;
  snapToGrid?: boolean;
  gridSize?: number;
  minROISize?: number;
  showLandmarks?: boolean;
  landmarks?: HandLandmarks[];

  // ROI callbacks
  onROICreate?: (roi: ROIData) => void;
  onROIUpdate?: (roiId: string, roi: ROIData) => void;
  onROIDelete?: (roiId: string) => void;
  onROISelect?: (roiId: string | null) => void;
  onROIHover?: (roiId: string | null) => void;
}

const PureVideoCanvas: React.FC<PureVideoCanvasProps> = ({
  videoPath,
  width,
  height,
  className = '',
  autoPlay = false,
  muted = true,
  onMetadataLoaded,
  onTimeUpdate,
  onVideoRef,
  
  // Adaptive config props with defaults
  adaptiveConfig = {
    mode: 'normal',
    fontSize: { header: 'xl', title: 'sm', body: 'sm', small: 'xs' },
    spacing: { section: '24px', item: '16px', padding: '16px' },
    showOptional: true
  },
  availableHeight = 0,
  
  // ROI props
  rois = [],
  selectedROIId = null,
  hoveredROIId = null,
  currentROIType = 'packing_area',
  currentROILabel = 'Packing Area',
  disabled = false,
  snapToGrid = false,
  gridSize = 10,
  minROISize = 20,
  showLandmarks = false,
  landmarks = [],

  // ROI callbacks
  onROICreate,
  onROIUpdate,
  onROIDelete,
  onROISelect,
  onROIHover
}) => {
  // State management
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isBuffering, setIsBuffering] = useState(false);
  const [videoMetadata, setVideoMetadata] = useState<VideoMetadata | null>(null);

  // Refs
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Theme colors
  const bgColor = useColorModeValue('gray.50', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  // Fetch video metadata
  const fetchVideoMetadata = useCallback(async () => {
    if (!videoPath) return;

    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(
        `http://localhost:8080/api/config/step4/roi/video-info?video_path=${encodeURIComponent(videoPath)}`
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      
      if (result.success && result.data) {
        setVideoMetadata(result.data);
        onMetadataLoaded?.(result.data);
      } else {
        throw new Error(result.error || 'Failed to fetch video metadata');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load video metadata';
      console.error('Video metadata error:', errorMessage);
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [videoPath, onMetadataLoaded]);

  // Video event handlers
  const handleVideoLoad = useCallback(() => {
    console.log('🎬 Pure video loaded successfully');
    setIsLoading(false);
    setError(null);
  }, []);

  const handleVideoError = useCallback((e: React.SyntheticEvent<HTMLVideoElement, Event>) => {
    const video = e.currentTarget;
    const errorMessage = video.error 
      ? `Video error code: ${video.error.code}`
      : 'Unknown video error';
    
    console.error('🚨 Pure video error:', errorMessage);
    setError(errorMessage);
    setIsLoading(false);
  }, []);

  const handleTimeUpdate = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;

    onTimeUpdate?.(video.currentTime, video.duration || 0);
  }, [onTimeUpdate]);

  const handleWaiting = useCallback(() => {
    setIsBuffering(true);
  }, []);

  const handleCanPlay = useCallback(() => {
    setIsBuffering(false);
  }, []);

  // Initialize video metadata on mount or path change
  useEffect(() => {
    fetchVideoMetadata();
  }, [fetchVideoMetadata]);

  // Provide video ref to parent
  useEffect(() => {
    onVideoRef?.(videoRef.current);
  }, [onVideoRef]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (videoRef.current) {
        videoRef.current.pause();
      }
    };
  }, []);

  // Render loading state with adaptive styling
  if (isLoading) {
    return (
      <Box
        w="100%"
        minH="fit-content"
        css={{
          '@media (max-width: 768px)': {
            maxW: '100%',
            px: adaptiveConfig.spacing.padding,
          }
        }}
      >
        <Box 
          width={width} 
          height={height} 
          className={className}
          position="relative"
          bg={bgColor}
          border="1px solid"
          borderColor={borderColor}
          borderRadius="8px"
          display="flex"
          alignItems="center"
          justifyContent="center"
          mx="auto"
        >
          <VStack spacing={adaptiveConfig.spacing.item}>
            <Spinner size={adaptiveConfig.mode === 'compact' ? 'md' : 'lg'} />
            <Text fontSize={adaptiveConfig.fontSize.body} color="gray.500">
              Loading video...
            </Text>
          </VStack>
        </Box>
      </Box>
    );
  }

  // Render error state with adaptive styling
  if (error) {
    return (
      <Box
        w="100%"
        minH="fit-content"
        css={{
          '@media (max-width: 768px)': {
            maxW: '100%',
            px: adaptiveConfig.spacing.padding,
          }
        }}
      >
        <Box width={width} height={height} className={className} mx="auto">
          <Alert status="error" borderRadius="8px">
            <AlertIcon />
            <VStack align="start" flex="1" spacing={adaptiveConfig.spacing.item}>
              <Text fontWeight="bold" fontSize={adaptiveConfig.fontSize.body}>Video Error</Text>
              <Text fontSize={adaptiveConfig.fontSize.small}>{error}</Text>
            </VStack>
          </Alert>
        </Box>
      </Box>
    );
  }

  return (
    <>
      {/* Responsive Container Pattern (copied from main canvas components) */}
      <Box
        w="100%"
        minH="fit-content"
        position="relative"
        css={{
          '@media (max-width: 768px)': {
            maxW: '100%',
            px: adaptiveConfig.spacing.padding,
          }
        }}
      >
      <Box
        ref={containerRef}
        width={width}
        height={height}
        className={className}
        position="relative"
        bg={bgColor}
        border="1px solid"
        borderColor={borderColor}
        borderRadius="8px"
        overflow="hidden"
        mx="auto" // Center the video
      >
      {/* Pure Video Element - No Controls */}
      <video
        ref={videoRef}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          backgroundColor: '#000'
        }}
        src={`http://localhost:8080/api/config/step4/roi/stream-video?video_path=${encodeURIComponent(videoPath)}`}
        autoPlay={autoPlay}
        muted={muted}
        playsInline
        preload="metadata"
        onLoadedData={handleVideoLoad}
        onError={handleVideoError}
        onTimeUpdate={handleTimeUpdate}
        onWaiting={handleWaiting}
        onCanPlay={handleCanPlay}
        // No controls prop - pure video display
      />

      {/* ROI Canvas Overlay - Integrated directly over video */}
      {videoMetadata && (
        <Box
          position="absolute"
          top={0}
          left={0}
          width="100%"
          height="100%"
          pointerEvents={disabled ? 'none' : 'auto'}
          zIndex="5"
        >
          <CanvasOverlay
            width={width}
            height={height}
            videoWidth={videoMetadata.resolution.width}
            videoHeight={videoMetadata.resolution.height}
            rois={rois}
            selectedROIId={selectedROIId}
            hoveredROIId={hoveredROIId}
            currentROIType={currentROIType}
            currentROILabel={currentROILabel}
            disabled={disabled}
            snapToGrid={snapToGrid}
            gridSize={gridSize}
            minROISize={minROISize}
            showLandmarks={showLandmarks}
            landmarks={landmarks}
            onROICreate={onROICreate}
            onROIUpdate={onROIUpdate}
            onROIDelete={onROIDelete}
            onROISelect={onROISelect}
            onROIHover={onROIHover}
          />
        </Box>
      )}

      {/* Buffering Overlay */}
      {isBuffering && (
        <Box
          position="absolute"
          top="50%"
          left="50%"
          transform="translate(-50%, -50%)"
          zIndex="10"
        >
          <VStack spacing="8px">
            <Spinner size="lg" color="white" />
            <Text color="white" fontSize="sm">
              Buffering...
            </Text>
          </VStack>
        </Box>
      )}

      {/* Debug Info - Development Only */}
      {process.env.NODE_ENV === 'development' && (
        <Box
          position="absolute"
          top="8px"
          right="8px"
          bg="rgba(0,0,0,0.7)"
          color="white"
          p="4px 8px"
          borderRadius="4px"
          fontSize="xs"
          zIndex="5"
        >
          Pure Video: {width}×{height} (Mode: {adaptiveConfig.mode})
        </Box>
      )}
      </Box>
      </Box>
    </>
  );
};

export default PureVideoCanvas;
export type { VideoMetadata, PureVideoCanvasProps };