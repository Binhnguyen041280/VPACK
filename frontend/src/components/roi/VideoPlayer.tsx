/**
 * VideoPlayer Component for ROI Configuration
 * HTML5 video player with custom controls and streaming support
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Box,
  Flex,
  IconButton,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  Text,
  HStack,
  VStack,
  Select,
  Tooltip,
  useColorModeValue,
  Alert,
  AlertIcon,
  Spinner
} from '@chakra-ui/react';
import { FaPlay, FaPause, FaStop, FaVolumeUp, FaVolumeMute, FaExpand } from 'react-icons/fa';

// Video metadata interface
interface VideoMetadata {
  path: string;
  filename: string;
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
interface VideoPlayerProps {
  videoPath: string;
  onMetadataLoaded?: (metadata: VideoMetadata) => void;
  onTimeUpdate?: (currentTime: number, duration: number) => void;
  onVideoError?: (error: string) => void;
  onPlay?: () => void;
  onPause?: () => void;
  onSeek?: (currentTime: number) => void;
  onSpeedChange?: (speed: number) => void;
  onPlayStateChange?: (isPlaying: boolean) => void;
  className?: string;
  width?: string;
  height?: string;
  autoPlay?: boolean;
  showControls?: boolean;
}

// Playback speeds
const PLAYBACK_SPEEDS = [
  { value: 0.25, label: '0.25x' },
  { value: 0.5, label: '0.5x' },
  { value: 1, label: '1x' },
  { value: 1.5, label: '1.5x' },
  { value: 2, label: '2x' },
  { value: 5, label: '5x' },
  { value: 10, label: '10x' }
];

const VideoPlayer: React.FC<VideoPlayerProps> = ({
  videoPath,
  onMetadataLoaded,
  onTimeUpdate,
  onVideoError,
  onPlay,
  onPause,
  onSeek,
  onSpeedChange,
  onPlayStateChange,
  className,
  width = '100%',
  height = '400px',
  autoPlay = false,
  showControls = true
}) => {
  // Refs
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // State
  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isBuffering, setIsBuffering] = useState(false);
  const [videoMetadata, setVideoMetadata] = useState<VideoMetadata | null>(null);

  // Theme colors
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const controlBg = useColorModeValue('gray.50', 'gray.700');
  const textColor = useColorModeValue('gray.800', 'white');


  // Load video metadata from backend
  const loadVideoMetadata = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(
        `http://localhost:8080/api/config/step4/roi/video-info?video_path=${encodeURIComponent(videoPath)}`
      );

      if (!response.ok) {
        throw new Error(`Failed to load video metadata: ${response.status}`);
      }

      const result = await response.json();
      
      if (!result.success) {
        throw new Error(result.error || 'Failed to load video metadata');
      }

      const metadata = result.data;
      setVideoMetadata(metadata);
      onMetadataLoaded?.(metadata);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error loading video metadata';
      console.error('Error loading video metadata:', errorMessage);
      setError(errorMessage);
      onVideoError?.(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [videoPath, onMetadataLoaded, onVideoError]);

  // Calculate current frame from video time
  const getCurrentFrame = useCallback(() => {
    const video = videoRef.current;
    if (!video || !videoMetadata) return 0;
    
    const fps = videoMetadata.fps || 30;
    return Math.floor(video.currentTime * fps);
  }, [videoMetadata]);

  // Seek to specific frame
  const seekToFrame = useCallback((frameNumber: number) => {
    const video = videoRef.current;
    if (!video || !videoMetadata) return;
    
    const fps = videoMetadata.fps || 30;
    const targetTime = frameNumber / fps;
    
    video.currentTime = Math.min(targetTime, video.duration);
    setCurrentTime(video.currentTime);
    onSeek?.(video.currentTime);
  }, [videoMetadata, onSeek]);

  // Video event handlers
  const handleLoadedMetadata = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    
    setDuration(video.duration);
    setIsLoading(false);
    setError(null);

    console.log('Video metadata loaded:', {
      duration: video.duration,
      width: video.videoWidth,
      height: video.videoHeight
    });
  }, []);

  const handleTimeUpdate = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;

    setCurrentTime(video.currentTime);
    onTimeUpdate?.(video.currentTime, video.duration);
  }, [onTimeUpdate]);


  const handleLoadStart = useCallback(() => {
    setIsBuffering(true);
    setIsLoading(true);
  }, []);

  const handleCanPlay = useCallback(() => {
    setIsBuffering(false);
    setIsLoading(false);
    
    // Auto-play if enabled and video is ready
    if (autoPlay && videoRef.current && !isPlaying) {
      videoRef.current.play().catch((err) => {
        console.warn('Auto-play failed (browser policy):', err);
      });
    }
  }, [autoPlay, isPlaying]);

  const handleWaiting = useCallback(() => {
    setIsBuffering(true);
  }, []);

  const handlePlaying = useCallback(() => {
    setIsBuffering(false);
  }, []);


  const handleError = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;

    const errorMessage = video.error ? 
      `Video error: ${video.error.message} (Code: ${video.error.code})` : 
      'Unknown video error';
    
    console.error('Video error:', errorMessage);
    setError(errorMessage);
    setIsLoading(false);
    onVideoError?.(errorMessage);
  }, [onVideoError]);

  // Control handlers
  const togglePlayPause = useCallback(async () => {
    const video = videoRef.current;
    if (!video) return;

    try {
      if (video.paused) {
        await video.play();
      } else {
        video.pause();
      }
    } catch (err) {
      console.error('Error toggling playback:', err);
      setError('Failed to control video playback');
    }
  }, []);

  const handleStop = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;

    video.pause();
    video.currentTime = 0;
  }, []);


  const handleVolumeChange = useCallback((value: number) => {
    const video = videoRef.current;
    if (!video) return;

    setVolume(value);
    video.volume = value;
    setIsMuted(value === 0);
  }, []);

  const toggleMute = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;

    if (isMuted) {
      video.volume = volume;
      setIsMuted(false);
    } else {
      video.volume = 0;
      setIsMuted(true);
    }
  }, [isMuted, volume]);

  const handleSpeedChange = useCallback((speed: string) => {
    const video = videoRef.current;
    const speedValue = parseFloat(speed);
    
    if (!video || isNaN(speedValue)) return;

    video.playbackRate = speedValue;
    setPlaybackSpeed(speedValue);
    onSpeedChange?.(speedValue);
  }, [onSpeedChange]);

  // Seek handler with callback
  const handleSeek = useCallback((value: number) => {
    const video = videoRef.current;
    if (!video) return;
    
    video.currentTime = value;
    setCurrentTime(value);
    onSeek?.(value);
  }, [onSeek]);

  const toggleFullscreen = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      container.requestFullscreen().catch((err) => {
        console.error('Error entering fullscreen:', err);
      });
    }
  }, []);

  // Load metadata when video path changes
  useEffect(() => {
    if (videoPath) {
      loadVideoMetadata();
    }
  }, [videoPath, loadVideoMetadata]);

  // Add video event listeners
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handlePlay = () => {
      console.log('Video play event');
      setIsPlaying(true);
      onPlay?.();
      onPlayStateChange?.(true);
    };
    const handlePause = () => {
      console.log('Video pause event');
      setIsPlaying(false);
      onPause?.();
      onPlayStateChange?.(false);
    };
    
    // Sync initial state with video element
    setIsPlaying(!video.paused);

    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('loadstart', handleLoadStart);
    video.addEventListener('canplay', handleCanPlay);
    video.addEventListener('waiting', handleWaiting);
    video.addEventListener('playing', handlePlaying);
    video.addEventListener('error', handleError);
    video.addEventListener('timeupdate', handleTimeUpdate);

    return () => {
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      video.removeEventListener('loadstart', handleLoadStart);
      video.removeEventListener('canplay', handleCanPlay);
      video.removeEventListener('waiting', handleWaiting);
      video.removeEventListener('playing', handlePlaying);
      video.removeEventListener('error', handleError);
      video.removeEventListener('timeupdate', handleTimeUpdate);
    };
  }, [
    handleLoadedMetadata,
    handleLoadStart,
    handleCanPlay,
    handleWaiting,
    handlePlaying,
    handleError,
    handleTimeUpdate,
    onPlay,
    onPause,
    onPlayStateChange
  ]);

  // Render loading state
  if (isLoading && !videoMetadata) {
    return (
      <Box 
        width={width} 
        height={height} 
        bg={bgColor}
        border="1px solid"
        borderColor={borderColor}
        borderRadius="8px"
        className={className}
        display="flex"
        alignItems="center"
        justifyContent="center"
      >
        <VStack spacing="16px">
          <Spinner size="lg" color="blue.500" />
          <Text color={textColor}>Loading video...</Text>
        </VStack>
      </Box>
    );
  }

  // Render error state
  if (error) {
    return (
      <Box width={width} height={height} className={className}>
        <Alert status="error" borderRadius="8px">
          <AlertIcon />
          <VStack align="start" flex="1">
            <Text fontWeight="bold">Video Error</Text>
            <Text fontSize="sm">{error}</Text>
          </VStack>
        </Alert>
      </Box>
    );
  }

  return (
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
    >
      {/* Video Element */}
      <video
        ref={videoRef}
        style={{
          width: '100%',
          height: showControls ? 'calc(100% - 80px)' : '100%',
          objectFit: 'contain',
          backgroundColor: '#000'
        }}
        src={`http://localhost:8080/api/config/step4/roi/stream-video?video_path=${encodeURIComponent(videoPath)}`}
        autoPlay={autoPlay}
        muted={isMuted}
        playsInline
        preload="metadata"
      />

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

      {/* Custom Controls */}
      {showControls && (
        <Box
          position="absolute"
          bottom="0"
          left="0"
          right="0"
          bg={controlBg}
          p="12px"
          borderTop="1px solid"
          borderColor={borderColor}
        >
          <VStack spacing="8px" width="100%">
            {/* Seek Bar */}
            <Slider
              value={currentTime}
              max={duration}
              onChange={handleSeek}
              width="100%"
            >
              <SliderTrack>
                <SliderFilledTrack />
              </SliderTrack>
              <SliderThumb boxSize="12px" />
            </Slider>

            {/* Control Buttons */}
            <Flex justify="space-between" align="center" width="100%">
              {/* Left Side - Playback Controls */}
              <HStack spacing="8px">
                <Tooltip label={isPlaying ? 'Pause' : 'Play'}>
                  <IconButton
                    aria-label={isPlaying ? 'Pause' : 'Play'}
                    icon={isPlaying ? <FaPause /> : <FaPlay />}
                    size="sm"
                    onClick={togglePlayPause}
                    colorScheme="blue"
                  />
                </Tooltip>

                <Tooltip label="Stop">
                  <IconButton
                    aria-label="Stop"
                    icon={<FaStop />}
                    size="sm"
                    onClick={handleStop}
                    variant="outline"
                  />
                </Tooltip>

                <HStack spacing="4px" minW="100px">
                  <Tooltip label={isMuted ? 'Unmute' : 'Mute'}>
                    <IconButton
                      aria-label={isMuted ? 'Unmute' : 'Mute'}
                      icon={isMuted ? <FaVolumeMute /> : <FaVolumeUp />}
                      size="sm"
                      variant="ghost"
                      onClick={toggleMute}
                    />
                  </Tooltip>
                  
                  <Slider
                    value={isMuted ? 0 : volume}
                    max={1}
                    step={0.1}
                    onChange={handleVolumeChange}
                    width="60px"
                  >
                    <SliderTrack>
                      <SliderFilledTrack />
                    </SliderTrack>
                    <SliderThumb boxSize="10px" />
                  </Slider>
                </HStack>
              </HStack>

              {/* Right Side - Speed and Fullscreen */}
              <HStack spacing="8px">
                <Select
                  value={playbackSpeed}
                  onChange={(e) => handleSpeedChange(e.target.value)}
                  size="sm"
                  width="80px"
                  variant="outline"
                >
                  {PLAYBACK_SPEEDS.map((speed) => (
                    <option key={speed.value} value={speed.value}>
                      {speed.label}
                    </option>
                  ))}
                </Select>

                <Tooltip label="Fullscreen">
                  <IconButton
                    aria-label="Fullscreen"
                    icon={<FaExpand />}
                    size="sm"
                    variant="ghost"
                    onClick={toggleFullscreen}
                  />
                </Tooltip>
              </HStack>
            </Flex>

            {/* Time Display */}
            <HStack justify="space-between" width="100%" fontSize="xs">
              <Text>
                {Math.floor(currentTime / 60)}:{Math.floor(currentTime % 60).toString().padStart(2, '0')} / {Math.floor(duration / 60)}:{Math.floor(duration % 60).toString().padStart(2, '0')}
              </Text>
              {videoMetadata && (
                <Text>Frame: {getCurrentFrame()} / {videoMetadata.frame_count}</Text>
              )}
            </HStack>
          </VStack>
        </Box>
      )}

    </Box>
  );
};

export default VideoPlayer;