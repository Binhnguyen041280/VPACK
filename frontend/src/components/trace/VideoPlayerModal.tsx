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
  Icon
} from '@chakra-ui/react';
import { MdVideocam, MdSchedule } from 'react-icons/md';

interface VideoPlayerModalProps {
  isOpen: boolean;
  onClose: () => void;
  videoPath: string;
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
  eventInfo
}) => {
  // State
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isBuffering, setIsBuffering] = useState(false);

  // Refs
  const videoRef = useRef<HTMLVideoElement>(null);

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

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (videoRef.current) {
        videoRef.current.pause();
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
          </Box>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default VideoPlayerModal;
