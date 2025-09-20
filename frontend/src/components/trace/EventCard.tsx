'use client';

import {
  Box,
  Text,
  HStack,
  VStack,
  Icon,
  Progress,
  Button,
  useColorModeValue,
} from '@chakra-ui/react';
import { MdVideocam, MdSchedule, MdPlayArrow, MdFolder } from 'react-icons/md';
import { useState, useEffect } from 'react';

interface EventData {
  event_id: number;
  tracking_codes_parsed: string[];
  camera_name: string;
  packing_time_start: number;
  packing_time_end: number;
  duration: number;
}

interface ProcessingState {
  isProcessing: boolean;
  progress: number;
  status: string;
  taskId?: string;
  outputPath?: string;
}

interface EventCardProps {
  event: EventData;
  index: number;
  onClick: (event: EventData) => void;
  autoProcess?: boolean;
}

const EventCard: React.FC<EventCardProps> = ({ event, index, onClick, autoProcess = false }) => {
  const [processing, setProcessing] = useState<ProcessingState>({
    isProcessing: false,
    progress: 0,
    status: 'idle'
  });

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const hoverBg = useColorModeValue('gray.50', 'gray.700');
  const hoverBorderColor = useColorModeValue('blue.300', 'blue.500');
  const textColor = useColorModeValue('gray.700', 'gray.200');
  const accentColor = useColorModeValue('blue.600', 'blue.400');
  const overlayBg = useColorModeValue('rgba(255, 255, 255, 0.95)', 'rgba(26, 32, 44, 0.95)');
  const progressBg = useColorModeValue('gray.200', 'gray.600');

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  const startTime = formatTime(event.packing_time_start);

  // Auto-start processing if autoProcess is enabled
  useEffect(() => {
    if (autoProcess && !processing.isProcessing && processing.status === 'idle') {
      handleCardClick();
    }
  }, [autoProcess]);

  // Start processing when card is clicked
  const handleCardClick = async () => {
    if (processing.isProcessing) return;

    try {
      // Start processing
      const response = await fetch('http://localhost:8080/process-event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_id: event.event_id,
          tracking_code: event.tracking_codes_parsed[0] // Use first tracking code
        })
      });

      const data = await response.json();
      if (data.task_id) {
        setProcessing({
          isProcessing: true,
          progress: 0,
          status: 'starting',
          taskId: data.task_id
        });

        // Poll for status updates
        pollProcessingStatus(data.task_id);
      }
    } catch (error) {
      console.error('Error starting processing:', error);
    }
  };

  // Poll processing status
  const pollProcessingStatus = async (taskId: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:8080/process-status/${taskId}`);
        const data = await response.json();

        setProcessing(prev => ({
          ...prev,
          progress: data.progress || 0,
          status: data.status || 'unknown',
          outputPath: data.output_path
        }));

        // Stop polling when completed or error
        if (data.status === 'completed' || data.status === 'error') {
          clearInterval(interval);
          if (data.status === 'completed') {
            setProcessing(prev => ({
              ...prev,
              isProcessing: false
            }));
          }
        }
      } catch (error) {
        console.error('Error polling status:', error);
        clearInterval(interval);
      }
    }, 500); // Poll every 500ms
  };

  // Handle play video
  const handlePlayVideo = async () => {
    if (!processing.outputPath) return;

    try {
      await fetch('http://localhost:8080/play-video', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_path: processing.outputPath })
      });
    } catch (error) {
      console.error('Error playing video:', error);
    }
  };

  // Handle browse location
  const handleBrowseLocation = async () => {
    if (!processing.outputPath) return;

    try {
      await fetch('http://localhost:8080/browse-location', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: processing.outputPath })
      });
    } catch (error) {
      console.error('Error browsing location:', error);
    }
  };

  // Get status display text
  const getStatusText = () => {
    switch (processing.status) {
      case 'downloading': return 'Downloading from Google Drive...';
      case 'cutting': return 'Cutting video segment...';
      case 'completed': return 'Processing completed!';
      case 'starting': return 'Starting process...';
      default: return 'Processing...';
    }
  };

  return (
    <Box
      bg={cardBg}
      border="1px solid"
      borderColor={borderColor}
      borderRadius="lg"
      p={4}
      mb={3}
      cursor={processing.isProcessing || autoProcess ? "default" : "pointer"}
      transition="all 0.2s ease-in-out"
      _hover={!processing.isProcessing && !autoProcess ? {
        bg: hoverBg,
        borderColor: hoverBorderColor,
        transform: 'translateY(-1px)',
        shadow: 'md'
      } : {}}
      onClick={autoProcess ? undefined : handleCardClick}
      position="relative"
      overflow="hidden"
    >
      <VStack align="stretch" spacing={3}>
        {/* Header */}
        <HStack spacing={2} align="center">
          <Text fontSize="lg" fontWeight="bold" color={accentColor}>
            📦 Event {index + 1}
          </Text>
          <Text fontSize="sm" color={textColor} fontWeight="medium">
            {event.tracking_codes_parsed.join(', ')}
          </Text>
        </HStack>

        {/* Event Details */}
        <HStack spacing={6} wrap="wrap">
          <HStack spacing={2}>
            <Icon as={MdVideocam} color="blue.500" boxSize={4} />
            <Text fontSize="sm" color={textColor}>
              {event.camera_name || 'Unknown'}
            </Text>
          </HStack>

          <HStack spacing={2}>
            <Icon as={MdSchedule} color="green.500" boxSize={4} />
            <Text fontSize="sm" color={textColor}>
              {event.duration}s
            </Text>
          </HStack>

          <Text fontSize="sm" color={textColor}>
            📅 {startTime}
          </Text>
        </HStack>

        {/* Action Buttons - Show only when processing is complete */}
        {processing.status === 'completed' && processing.outputPath && (
          <HStack spacing={3} justify="center" pt={2}>
            <Button
              leftIcon={<Icon as={MdPlayArrow} />}
              colorScheme="green"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                handlePlayVideo();
              }}
            >
              PLAY
            </Button>
            <Button
              leftIcon={<Icon as={MdFolder} />}
              colorScheme="blue"
              size="sm"
              variant="outline"
              onClick={(e) => {
                e.stopPropagation();
                handleBrowseLocation();
              }}
            >
              BROWSE
            </Button>
          </HStack>
        )}
      </VStack>

      {/* Processing Overlay */}
      {processing.isProcessing && (
        <Box
          position="absolute"
          top="0"
          left="0"
          right="0"
          bottom="0"
          bg={overlayBg}
          backdropFilter="blur(2px)"
          display="flex"
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
          borderRadius="lg"
          zIndex={1}
        >
          <VStack spacing={4} w="80%">
            <Text fontSize="md" fontWeight="bold" color={accentColor}>
              {getStatusText()}
            </Text>

            <Box w="100%">
              <Progress
                value={processing.progress}
                colorScheme="blue"
                size="lg"
                borderRadius="md"
                bg={progressBg}
              />
              <Text fontSize="sm" color={textColor} textAlign="center" mt={1}>
                {processing.progress}%
              </Text>
            </Box>
          </VStack>
        </Box>
      )}
    </Box>
  );
};

export default EventCard;