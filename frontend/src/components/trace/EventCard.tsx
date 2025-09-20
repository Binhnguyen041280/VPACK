'use client';

import {
  Box,
  Text,
  HStack,
  VStack,
  Icon,
  useColorModeValue,
} from '@chakra-ui/react';
import { MdVideocam, MdSchedule } from 'react-icons/md';

interface EventData {
  event_id: number;
  tracking_codes_parsed: string[];
  camera_name: string;
  packing_time_start: number;
  packing_time_end: number;
  duration: number;
}

interface EventCardProps {
  event: EventData;
  index: number;
  onClick: (event: EventData) => void;
}

const EventCard: React.FC<EventCardProps> = ({ event, index, onClick }) => {
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const hoverBg = useColorModeValue('gray.50', 'gray.700');
  const hoverBorderColor = useColorModeValue('blue.300', 'blue.500');
  const textColor = useColorModeValue('gray.700', 'gray.200');
  const accentColor = useColorModeValue('blue.600', 'blue.400');

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

  return (
    <Box
      bg={cardBg}
      border="1px solid"
      borderColor={borderColor}
      borderRadius="lg"
      p={4}
      mb={3}
      cursor="pointer"
      transition="all 0.2s ease-in-out"
      _hover={{
        bg: hoverBg,
        borderColor: hoverBorderColor,
        transform: 'translateY(-1px)',
        shadow: 'md'
      }}
      onClick={() => onClick(event)}
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

      </VStack>
    </Box>
  );
};

export default EventCard;