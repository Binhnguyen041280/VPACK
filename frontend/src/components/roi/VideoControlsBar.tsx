/**
 * VideoControlsBar Component - New Layout Design
 * Optimized layout for better space allocation and component positioning
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  HStack,
  VStack,
  IconButton,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  Text,
  Tooltip,
  useColorModeValue
} from '@chakra-ui/react';
import { FaPlay, FaPause } from 'react-icons/fa';

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

// Control state interface
interface VideoControlState {
  isPlaying: boolean;
  currentTime: number;
  duration: number;
}

// Component props interface
interface VideoControlsBarProps {
  videoRef: React.RefObject<HTMLVideoElement>;
  width?: number;
  height?: number;
  className?: string;
  onControlStateChange?: (state: VideoControlState) => void;
  disabled?: boolean;
  
  // Adaptive config props (copied from CanvasMessage.tsx pattern)
  adaptiveConfig?: AdaptiveConfig;
  availableHeight?: number;
}

const VideoControlsBar: React.FC<VideoControlsBarProps> = ({
  videoRef,
  width = 300,
  height = 54, // Chat controls baseline height
  className = '',
  onControlStateChange,
  disabled = false,
  
  // Adaptive config props with defaults
  adaptiveConfig = {
    mode: 'normal',
    fontSize: { header: 'md', title: 'sm', body: 'sm', small: 'xs' },
    spacing: { section: '12px', item: '8px', padding: '12px' },
    showOptional: true
  },
  availableHeight = 0
}) => {
  // Control state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  // Theme colors
  const controlBg = useColorModeValue('gray.100', 'gray.700');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const textColor = useColorModeValue('gray.700', 'gray.300');

  // Update control state callback
  const updateControlState = useCallback(() => {
    const state: VideoControlState = {
      isPlaying,
      currentTime,
      duration
    };
    onControlStateChange?.(state);
  }, [isPlaying, currentTime, duration, onControlStateChange]);

  // Format time display
  const formatTime = useCallback((time: number): string => {
    if (!isFinite(time)) return '0:00';
    
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }, []);

  // Play/Pause toggle
  const togglePlayPause = useCallback(() => {
    const video = videoRef.current;
    if (!video || disabled) return;

    if (video.paused) {
      video.play()
        .then(() => setIsPlaying(true))
        .catch(console.error);
    } else {
      video.pause();
      setIsPlaying(false);
    }
  }, [videoRef, disabled]);

  // Seek to specific time
  const handleSeek = useCallback((value: number) => {
    const video = videoRef.current;
    if (!video || disabled) return;

    video.currentTime = value;
    setCurrentTime(value);
  }, [videoRef, disabled]);

  // Video event listeners
  useEffect(() => {
    const video = videoRef.current;
    if (!video) {
      console.log('🚨 VideoControlsBar: No video ref available');
      return;
    }

    console.log('🎬 VideoControlsBar: Setting up event listeners');

    const handleTimeUpdate = () => {
      const currentTime = video.currentTime;
      const duration = video.duration || 0;
      setCurrentTime(currentTime);
      console.log('⏰ Time update:', { currentTime: currentTime.toFixed(2), duration: duration.toFixed(2) });
    };

    const handleDurationChange = () => {
      const duration = video.duration || 0;
      setDuration(duration);
      console.log('📏 Duration change:', duration.toFixed(2));
    };

    const handleLoadedMetadata = () => {
      const duration = video.duration || 0;
      setDuration(duration);
      setCurrentTime(video.currentTime || 0);
      console.log('📋 Metadata loaded:', { duration: duration.toFixed(2), currentTime: video.currentTime.toFixed(2) });
    };

    const handlePlay = () => {
      setIsPlaying(true);
      console.log('▶️ Video playing');
    };

    const handlePause = () => {
      setIsPlaying(false);
      console.log('⏸️ Video paused');
    };

    // Add event listeners
    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('durationchange', handleDurationChange);
    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);

    // Initial state - check immediately
    const initialDuration = video.duration || 0;
    const initialCurrentTime = video.currentTime || 0;
    const initialIsPlaying = !video.paused;
    
    setDuration(initialDuration);
    setCurrentTime(initialCurrentTime);
    setIsPlaying(initialIsPlaying);
    
    console.log('🎯 VideoControlsBar initial state:', { 
      duration: initialDuration.toFixed(2), 
      currentTime: initialCurrentTime.toFixed(2), 
      isPlaying: initialIsPlaying,
      readyState: video.readyState
    });

    // Cleanup
    return () => {
      console.log('🧹 VideoControlsBar: Cleaning up event listeners');
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('durationchange', handleDurationChange);
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
    };
  }, [videoRef, videoRef.current]);

  // Update control state when state changes
  useEffect(() => {
    updateControlState();
  }, [updateControlState]);

  // Fix undefined variables by defining them from adaptiveConfig
  const containerHeight = height;
  const padding = parseInt(adaptiveConfig.spacing.padding) || 12;
  const fontSize = adaptiveConfig.fontSize.body;
  const buttonSize = adaptiveConfig.mode === 'compact' ? 'xs' : 'sm';
  
  // Calculate component heights based on container
  const seekBarHeight = Math.max(12, Math.floor(height * 0.3)); // 30% of height, min 12px
  const controlsHeight = height - seekBarHeight - 8; // Remaining height minus gap
  const gap = 4; // Fixed gap between seek bar and controls

  return (
    <>
      {/* Responsive Container Pattern (copied from main canvas components) */}
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
        h="54px"
        className={className}
        bg={controlBg}
        border="1px solid"
        borderColor={borderColor}
        borderRadius="45px"
        opacity={disabled ? 0.6 : 1}
        pointerEvents={disabled ? 'none' : 'auto'}
        position="relative"
        mx="auto"
        p="15px 20px"
        display="flex"
        alignItems="center"
      >
        {/* HStack Layout - Single Row like main chat */}
        <HStack 
          spacing="12px" 
          width="100%" 
          justify="flex-start" 
          align="center"
          height="100%"
        >
        
        {/* Play/Pause Button - Exact Chat Controls Pattern */}
        <Tooltip label={isPlaying ? 'Pause' : 'Play'}>
          <IconButton
            aria-label={isPlaying ? 'Pause' : 'Play'}
            icon={isPlaying ? <FaPause size="16px" /> : <FaPlay size="16px" />}
            w="34px"
            h="34px"
            minW="34px"
            maxW="34px"
            minH="34px"
            maxH="34px"
            borderRadius="full"
            justifyContent="center"
            alignItems="center"
            onClick={togglePlayPause}
            colorScheme="blue"
            isDisabled={disabled}
            flexShrink={0}
          />
        </Tooltip>
        
        {/* Seek Bar - Center Section */}
        <Box flex="1" px="8px">
          <Slider
            value={currentTime}
            max={duration || 100}
            onChange={handleSeek}
            width="100%"
            isDisabled={disabled}
            size="sm"
          >
            <SliderTrack bg="gray.300" height="3px">
              <SliderFilledTrack bg="blue.500" />
            </SliderTrack>
            <SliderThumb boxSize="10px" bg="blue.500" />
          </Slider>
        </Box>
        
        {/* Time Display - Right Section */}
        <Text 
          fontSize="sm" 
          color={textColor} 
          fontWeight="500"
          lineHeight="1.2"
          whiteSpace="nowrap"
          flexShrink={0}
        >
          {formatTime(currentTime)} / {formatTime(duration)}
        </Text>
        
        </HStack>

        {/* Debug Info - Development Only */}
        {process.env.NODE_ENV === 'development' && (
          <Box
            position="absolute"
            top="1px"
            right="4px"
            bg="rgba(0,0,0,0.7)"
            color="white"
            px="2px"
            py="1px"
            borderRadius="2px"
            fontSize="8px"
            zIndex="10"
          >
            {width}×{containerHeight} ({adaptiveConfig.mode})
          </Box>
        )}
      </Box>
      </Box>
    </>
  );
};

export default VideoControlsBar;
export type { VideoControlState, VideoControlsBarProps };