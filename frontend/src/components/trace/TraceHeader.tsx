'use client';

import { useContext } from 'react';
import {
  Flex,
  Box,
  Input,
  Select,
  HStack,
  Menu,
  MenuButton,
  MenuList,
  MenuOptionGroup,
  MenuItemOption,
  Button,
  useColorModeValue
} from '@chakra-ui/react';
import { ChevronDownIcon } from '@chakra-ui/icons';
import { SidebarContext } from '@/contexts/SidebarContext';

interface TraceHeaderProps {
  fromDateTime: string;
  toDateTime: string;
  defaultDays: number;
  onFromDateTimeChange: (dateTime: string) => void;
  onToDateTimeChange: (dateTime: string) => void;
  onDefaultDaysChange: (days: number) => void;
  availableCameras: string[];
  selectedCameras: string[];
  onCameraToggle: (cameras: string[]) => void;
  isHeaderHidden: boolean;
  isHovering: boolean;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
}

const TraceHeader: React.FC<TraceHeaderProps> = ({
  fromDateTime,
  toDateTime,
  defaultDays,
  onFromDateTimeChange,
  onToDateTimeChange,
  onDefaultDaysChange,
  availableCameras,
  selectedCameras,
  onCameraToggle,
  isHeaderHidden,
  isHovering,
  onMouseEnter,
  onMouseLeave
}) => {
  const { toggleSidebar } = useContext(SidebarContext);

  const headerBg = useColorModeValue('white', 'navy.800');
  const borderColor = useColorModeValue('gray.200', 'whiteAlpha.200');
  const inputBg = useColorModeValue('gray.50', 'navy.700');
  const menuBg = useColorModeValue('white', 'navy.700');
  const menuItemHoverBg = useColorModeValue('gray.50', 'navy.600');

  // Generate days options from 1 to 30
  const defaultDaysOptions = Array.from({ length: 30 }, (_, i) => ({
    value: i + 1,
    label: `${i + 1} ${i === 0 ? 'Day' : 'Days'}`
  }));

  const shouldShowHeader = !isHeaderHidden || isHovering;

  return (
    <>
      {/* Invisible hover area when header is hidden */}
      {isHeaderHidden && (
        <Box
          position="fixed"
          top="0"
          left={toggleSidebar ? 'calc(95px + (100vw - 95px - 800px) / 2)' : 'calc(288px + (100vw - 288px - 800px) / 2)'}
          w="800px"
          height="10px"
          zIndex={60}
          bg="transparent"
          onMouseEnter={onMouseEnter}
          onMouseLeave={onMouseLeave}
        />
      )}

      <Flex
        position="fixed"
        top="0"
        left={toggleSidebar ? 'calc(95px + (100vw - 95px - 800px) / 2)' : 'calc(288px + (100vw - 288px - 800px) / 2)'}
        w="800px"
        h="60px"
        px="20px"
        align="center"
        zIndex={50}
        transform={`translateY(${shouldShowHeader ? '0' : '-100%'})`}
        transition="transform 0.3s ease-in-out, left 0.2s linear"
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
      >
        {/* DEFAULT DAYS - 25% */}
        <Box flex="0.25" pr="8px">
          <Select
            value={defaultDays}
            onChange={(e) => onDefaultDaysChange(Number(e.target.value))}
            w="100%"
            h="40px"
            variant="unstyled"
            fontSize="sm"
          >
            {defaultDaysOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </Box>

        {/* FROM DATETIME - 25% */}
        <Box flex="0.25" px="4px">
          <Input
            type="datetime-local"
            value={fromDateTime}
            onChange={(e) => onFromDateTimeChange(e.target.value)}
            w="100%"
            h="40px"
            variant="unstyled"
            fontSize="sm"
            placeholder="From"
          />
        </Box>

        {/* TO DATETIME - 25% */}
        <Box flex="0.25" px="4px">
          <Input
            type="datetime-local"
            value={toDateTime}
            onChange={(e) => onToDateTimeChange(e.target.value)}
            w="100%"
            h="40px"
            variant="unstyled"
            fontSize="sm"
            placeholder="To"
          />
        </Box>

        {/* CAMERAS - 25% */}
        <Box flex="0.25" px="4px">
          <Menu closeOnSelect={false}>
            <MenuButton
              as={Button}
              rightIcon={<ChevronDownIcon />}
              w="100%"
              h="40px"
              variant="unstyled"
              textAlign="left"
              fontSize="sm"
            >
              {selectedCameras.length === 0
                ? 'Camera'
                : selectedCameras.length === availableCameras.length
                ? 'All'
                : selectedCameras.length === 1
                ? selectedCameras[0]
                : 'Cameras...'
              }
            </MenuButton>

            <MenuList bg={menuBg} border="1px solid" borderColor={borderColor}>
              <MenuOptionGroup
                type="checkbox"
                value={selectedCameras}
                onChange={(values) => onCameraToggle(values as string[])}
              >
                <MenuItemOption
                  value="all"
                  fontSize="sm"
                  _hover={{ bg: menuItemHoverBg }}
                  onClick={() => {
                    if (selectedCameras.length === availableCameras.length) {
                      onCameraToggle([]);
                    } else {
                      onCameraToggle(availableCameras);
                    }
                  }}
                >
                  All Cameras
                </MenuItemOption>
                {availableCameras.map((camera) => (
                  <MenuItemOption
                    key={camera}
                    value={camera}
                    fontSize="sm"
                    _hover={{ bg: menuItemHoverBg }}
                  >
                    {camera}
                  </MenuItemOption>
                ))}
              </MenuOptionGroup>
            </MenuList>
          </Menu>
        </Box>
      </Flex>
    </>
  );
};

export default TraceHeader;