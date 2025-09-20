'use client';

import {
  Box,
  Text,
  VStack,
  HStack,
  Badge,
  useColorModeValue,
} from '@chakra-ui/react';
import EventCard from './EventCard';

interface EventData {
  event_id: number;
  tracking_codes_parsed: string[];
  camera_name: string;
  packing_time_start: number;
  packing_time_end: number;
  duration: number;
}

interface EventSearchResultsProps {
  searchInput: string;
  events: EventData[];
  onEventClick: (event: EventData) => void;
}

const EventSearchResults: React.FC<EventSearchResultsProps> = ({
  searchInput,
  events,
  onEventClick
}) => {
  const textColor = useColorModeValue('gray.700', 'gray.200');
  const accentColor = useColorModeValue('blue.600', 'blue.400');

  // Parse search input
  const searchedCodes = searchInput.split(',').map(code => code.trim()).filter(code => code.length > 0);

  // Get all found tracking codes from events
  const foundCodes = new Set<string>();
  events.forEach(event => {
    event.tracking_codes_parsed.forEach(code => foundCodes.add(code));
  });

  // Determine which codes were found vs not found
  const foundCodesList = searchedCodes.filter(code => foundCodes.has(code));
  const notFoundCodesList = searchedCodes.filter(code => !foundCodes.has(code));

  // Display truncated search input
  const displayInput = searchedCodes.length > 3
    ? `${searchedCodes.slice(0, 3).join(', ')}...`
    : searchInput;

  if (events.length === 0) {
    return (
      <VStack spacing={4} align="stretch">
        <Text fontSize="lg" fontWeight="bold" color={textColor}>
          🔍 Search Results for ({searchedCodes.length} codes): {displayInput}
        </Text>
        <Text color="red.500" fontSize="lg">
          ❌ No events found
        </Text>
        {searchedCodes.length > 0 && (
          <VStack spacing={2} align="flex-start">
            <Text fontSize="sm" fontWeight="bold" color={textColor}>Not Found:</Text>
            <HStack spacing={2} wrap="wrap">
              {searchedCodes.map(code => (
                <Badge key={code} colorScheme="red" variant="outline">
                  {code}
                </Badge>
              ))}
            </HStack>
          </VStack>
        )}
      </VStack>
    );
  }

  return (
    <VStack spacing={4} align="stretch">
      {/* Header */}
      <VStack spacing={2} align="flex-start">
        <Text fontSize="lg" fontWeight="bold" color={textColor}>
          🔍 Search Results for ({searchedCodes.length} codes): {displayInput}
        </Text>
        <Text fontSize="md" color={accentColor} fontWeight="medium">
          ✅ Found {events.length} event(s) for {foundCodesList.length}/{searchedCodes.length} codes
        </Text>

        {/* Found/Not Found Summary */}
        <VStack spacing={2} align="flex-start" w="100%">
          {foundCodesList.length > 0 && (
            <Box>
              <Text fontSize="sm" fontWeight="bold" color="green.600" mb={1}>
                Found ({foundCodesList.length}):
              </Text>
              <HStack spacing={2} wrap="wrap">
                {foundCodesList.map(code => (
                  <Badge key={code} colorScheme="green" variant="subtle">
                    {code}
                  </Badge>
                ))}
              </HStack>
            </Box>
          )}

          {notFoundCodesList.length > 0 && (
            <Box>
              <Text fontSize="sm" fontWeight="bold" color="red.600" mb={1}>
                Not Found ({notFoundCodesList.length}):
              </Text>
              <HStack spacing={2} wrap="wrap">
                {notFoundCodesList.map(code => (
                  <Badge key={code} colorScheme="red" variant="outline">
                    {code}
                  </Badge>
                ))}
              </HStack>
            </Box>
          )}
        </VStack>
      </VStack>

      {/* Event Cards - Auto-process all events */}
      <VStack spacing={0} align="stretch">
        {events.map((event, index) => (
          <EventCard
            key={event.event_id}
            event={event}
            index={index}
            onClick={onEventClick}
            autoProcess={true}
          />
        ))}
      </VStack>
    </VStack>
  );
};

export default EventSearchResults;